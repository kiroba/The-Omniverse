"""Daemon v8.16.0: signed app check-ins (consent version, app version, crash summary) feeding
/api/telemetry/summary.

Run: python3 -m unittest tests.test_app_telemetry
"""
import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daemon_harness import Daemon, Key, daemon_module, now_ms  # noqa: E402


def checkin(key: Key, app="kickback", version="0.1.10", platform="android", consent="1", accepted=True,
            crashes=None, ts=None, signer: Key = None, **extra) -> dict:
    c = {"type": "omni.app-checkin.v1", "pubkey": key.pub, "app": app, "app_version": version,
         "platform": platform, "consent_version": consent, "consent_accepted": accepted,
         "ts": ts if ts is not None else now_ms(), **extra}
    if crashes is not None:
        c["crashes"] = crashes
    raw = json.dumps(c, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return dict(c, sig=(signer or key).sign(raw))


class Unit(unittest.TestCase):
    def test_install_id_is_not_the_key(self):
        d = daemon_module()
        k = Key()
        iid = d.install_id(k.pub)
        self.assertEqual(len(iid), 20)
        self.assertNotIn(iid, k.pub)
        self.assertEqual(iid, d.install_id(k.pub))

    def test_validation(self):
        d = daemon_module()
        k = Key()
        d.validate_checkin(checkin(k, os_major=15, crashes={"count": 2, "last_kind": "StateError"}))
        for bad in (checkin(k, platform="toaster"), checkin(k, app="Kick Back"), checkin(k, device="Pixel 8"),
                    checkin(k, crashes={"count": 1, "last_kind": "Null check operator used on a null value"}),
                    checkin(k, crashes={"count": 5000}), checkin(k, os_major=150), checkin(k, accepted="yes")):
            with self.assertRaises(ValueError, msg=bad):
                d.validate_checkin(bad)
        with self.assertRaises(PermissionError):
            d.validate_checkin(checkin(k, signer=Key()))
        with self.assertRaises(PermissionError):
            d.validate_checkin(checkin(k, ts=now_ms() - 3_600_000))


class Live(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_app_tel_"))
        cls.d = Daemon(cls.tmp, "apptel").start()

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_checkins_feed_summary_without_keys(self):
        a, b, c = Key(), Key(), Key()
        self.assertEqual(self.d.post("/api/telemetry/app-checkin", checkin(a, os_major=15))[0], 200)
        self.assertEqual(self.d.post("/api/telemetry/app-checkin",
                                     checkin(b, version="0.1.9", crashes={"count": 3, "last_kind": "FlutterError"}))[0], 200)
        self.assertEqual(self.d.post("/api/telemetry/app-checkin",
                                     checkin(b, app="mesh_monitor", version="0.1.9", consent="1", accepted=True))[0], 200)
        self.assertEqual(self.d.post("/api/telemetry/app-checkin",
                                     checkin(c, platform="windows", consent=None, accepted=False))[0], 200)
        code, s = self.d.get("/api/telemetry/summary")
        self.assertEqual(code, 200, s)
        u = s["users"]["app_checkins"]
        self.assertEqual((u["installs"], u["active_24h"]), (3, 3))
        self.assertEqual(u["consent"]["accepted"], 2)
        self.assertEqual(u["consent"]["not_accepted"], 1)
        self.assertEqual(u["app_versions"]["kickback"], {"0.1.10": 2, "0.1.9": 1})
        self.assertEqual(u["app_versions"]["mesh_monitor"], {"0.1.9": 1})
        self.assertEqual(u["platforms"], {"android": 3, "windows": 1})
        cr = s["services"]["app_crashes"]
        self.assertEqual((cr["last_24h"], cr["last_7d"], cr["by_app"], cr["top_kinds"]),
                         (3, 3, {"kickback": 3}, {"FlutterError": 3}))
        text = json.dumps(s)
        for k in (a, b, c):
            self.assertNotIn(k.pub, text)
            self.assertNotIn(k.pub[:12], text)
        # Nor in the DB: only the salted install id is stored.
        conn = sqlite3.connect(str(self.d.db))
        dump = "\n".join(conn.iterdump())
        conn.close()
        self.assertNotIn(a.pub, dump)

    def test_upsert_and_rate_limit(self):
        k = Key()
        self.assertEqual(self.d.post("/api/telemetry/app-checkin", checkin(k, version="0.1.8"))[0], 200)
        self.assertEqual(self.d.post("/api/telemetry/app-checkin", checkin(k, version="0.1.10"))[0], 200)
        self.assertEqual(self.d.post("/api/telemetry/app-checkin", checkin(k, version="0.1.11"))[0], 429)
        conn = sqlite3.connect(str(self.d.db))
        n = conn.execute("SELECT COUNT(*), MAX(app_version) FROM app_checkins WHERE install = ?",
                         (daemon_module().install_id(k.pub),)).fetchone()
        conn.close()
        self.assertEqual(n, (1, "0.1.10"))

    def test_rejections(self):
        k = Key()
        self.assertEqual(self.d.post("/api/telemetry/app-checkin", checkin(k, signer=Key()))[0], 401)
        self.assertEqual(self.d.post("/api/telemetry/app-checkin", checkin(k, device_model="SM-G991"))[0], 400)
        self.assertEqual(self.d.post("/api/telemetry/app-checkin", checkin(k, ts=now_ms() + 3_600_000))[0], 401)


if __name__ == "__main__":
    unittest.main()
