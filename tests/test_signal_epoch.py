"""Daemon v8.17.0: OmniCast signal poll cursor survives a hub restart (per-run epoch).

Before: the mailbox cursor restarted at 0 on every hub start, so a phone still holding cursor=N
silently dropped the first N new messages ("seq <= since" = already received).

Run: python3 -m unittest tests.test_signal_epoch
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daemon_harness import daemon_module  # noqa: E402
from test_signal_mailbox import Daemon, Key, make_msg  # noqa: E402


class MailboxUnit(unittest.TestCase):
    def _msg(self, d, n, to="b" * 64):
        return {"to": to, "from": "a" * 64, "call_id": "c", "kind": "ice", "payload": "x", "ts": 1, "sig": f"{n:0128x}"}

    def test_stale_cursor_from_previous_run_is_ignored(self):
        d = daemon_module()
        old = d.SignalMailbox()
        for i in range(5):
            old.send(self._msg(d, i + 1))
        r = old.poll("b" * 64, "f" * 128, since=0)
        cursor, epoch = r["cursor"], r["epoch"]
        self.assertEqual((cursor, r["cursor_reset"]), (5, False))
        new = d.SignalMailbox()                 # hub restarted: seq back to 0, new epoch
        self.assertNotEqual(new.epoch, epoch)
        new.send(self._msg(d, 100))
        r = new.poll("b" * 64, "e" * 128, since=cursor, epoch=epoch)
        self.assertEqual((r["count"], r["cursor_reset"], r["cursor"]), (1, True, 1))
        # No epoch (old client), cursor beyond this run's seq: also reset.
        new.send(self._msg(d, 101))
        r = new.poll("b" * 64, "d" * 128, since=cursor)
        self.assertEqual((r["count"], r["cursor_reset"]), (1, True))

    def test_same_run_cursor_still_filters(self):
        d = daemon_module()
        mb = d.SignalMailbox()
        mb.send(self._msg(d, 1))
        mb.send(self._msg(d, 2))
        # The client says it already has seq 1 in this run: only seq 2 comes back.
        r = mb.poll("b" * 64, "c" * 128, since=1, epoch=mb.epoch)
        self.assertEqual(([m["seq"] for m in r["messages"]], r["cursor_reset"]), ([2], False))


class LiveRestart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_signal_epoch_"))
        cls.d = Daemon(cls.tmp, "epoch")
        cls.d.start()

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_message_after_restart_is_delivered_to_old_cursor(self):
        alice, bob = Key(), Key()
        for i in range(3):
            code, r = self.d.send(make_msg(alice, bob.pub, call_id=f"before-{i}"))
            self.assertEqual(code, 200, r)
        code, r = self.d.poll(bob)
        self.assertEqual((code, r["count"]), (200, 3), r)
        cursor, epoch = r["cursor"], r["epoch"]
        self.d.stop()
        self.d.start()
        code, r = self.d.send(make_msg(alice, bob.pub, kind="ring", call_id="after-restart"))
        self.assertEqual((code, r["seq"]), (200, 1), r)
        self.assertNotEqual(r["epoch"], epoch)
        code, r = self.d.poll(bob, since=cursor, extra={"epoch": epoch})
        self.assertEqual(code, 200, r)
        self.assertEqual(([m["call_id"] for m in r["messages"]], r["cursor_reset"]), (["after-restart"], True))
        code, r = self.d.poll(bob, since=0, extra={"epoch": "nothex"})
        self.assertEqual(code, 400, r)


if __name__ == "__main__":
    unittest.main()
