"""Flet control panel (issue #8): runs on Flet 1.0.x and really talks to the daemon.

Run: python -m unittest tests/test_flet_panel.py -v
Starts one real daemon (patched copy on free ports, temp HOME/cwd) and drives the panel's
DaemonClient against it. The UI test builds the view on a fake page (skipped without Flet).
"""
import importlib.util
import os
import re
import shutil
import site
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADMIN = ROOT / "Admin"
PANEL = ROOT / "backend_services" / "omni-ipc-daemon" / "omni_flet_desktop_control_panel.py"

spec = importlib.util.spec_from_file_location("omni_flet_panel", PANEL)
panel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(panel)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class FakePage:
    def __init__(self):
        self.controls, self.updates = [], 0

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self):
        self.updates += 1


class PanelAgainstLiveDaemon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_flet_test_"))
        code = cls.tmp / "code"
        code.mkdir()
        for f in ("omni_live_daemon_server.py", "omni_signing.py", "omni_negentropy.py"):
            shutil.copy(ADMIN / f, code / f)
        cls.ports = {"TELEMETRY_PORT": free_port(), "CONTINUITY_IPC_PORT": free_port(),
                     "P2P_SYNC_PORT": free_port(), "UDP_DISCOVERY_PORT": free_port()}
        src = (code / "omni_live_daemon_server.py").read_text(encoding="utf-8")
        for const, port in cls.ports.items():   # works with or without OMNI_*_PORT env support
            src = re.sub(rf"^{const} = .+$", f"{const} = {port}", src, count=1, flags=re.M)
        (code / "omni_live_daemon_server.py").write_text(src, encoding="utf-8")
        env = dict(os.environ, HOME=str(cls.tmp), USERPROFILE=str(cls.tmp), NO_PROXY="*",
                   OMNI_MESH_ID="flet-test", OMNI_CATCHUP_INTERVAL="0", PYTHONUTF8="1",
                   PYTHONPATH=os.pathsep.join([site.getusersitepackages(), str(code)]))
        for k in ("OMNI_HUB_REMOTE", "OMNI_TRUSTED_KEYS_FILE", "OMNI_SYNC_PEERS"):
            env.pop(k, None)
        cls.log = open(cls.tmp / "daemon.log", "wb")
        cls.proc = subprocess.Popen([sys.executable, str(code / "omni_live_daemon_server.py")],
                                    cwd=str(cls.tmp), env=env, stdout=cls.log, stderr=subprocess.STDOUT)
        cls.client = panel.DaemonClient("127.0.0.1", ipc_port=cls.ports["CONTINUITY_IPC_PORT"],
                                        telemetry_port=cls.ports["TELEMETRY_PORT"])
        deadline = time.time() + 20
        while time.time() < deadline and cls.client.health()[0] != 200:
            if cls.proc.poll() is not None:
                raise RuntimeError((cls.tmp / "daemon.log").read_text(errors="replace"))
            time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.log.close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_health(self):
        st, body = self.client.health()
        self.assertEqual(st, 200)
        self.assertEqual(body["mesh_id"], "flet-test")
        self.assertTrue(panel.describe_health(st, body).startswith("Online"))

    def test_post_then_feed_shows_verified_event(self):
        st, body = self.client.append("CREATOR_POST_PUBLISHED", {"title": "from panel test"})
        self.assertEqual(st, 200, body)
        st, feed = self.client.feed(10)
        self.assertEqual(st, 200)
        ev = next(e for e in feed["events"] if e["event_id"] == body["event_id"])
        self.assertTrue(ev["verified"])
        self.assertIn("[Verified]", panel.describe_event(ev))

    def test_offline_daemon_reported(self):
        c = panel.DaemonClient("127.0.0.1", ipc_port=free_port(), telemetry_port=free_port(), timeout=1)
        st, body = c.health()
        self.assertEqual(st, 0)
        self.assertIn("offline", panel.describe_health(st, body))

    def test_remote_hub_sends_bearer_and_blocks_post(self):
        c = panel.DaemonClient("100.64.0.9", token="abc", timeout=0.5)
        self.assertTrue(c.is_remote)
        st, body = c.append("X", {})
        self.assertEqual(st, 0)
        self.assertIn("only allowed", body["message"])

    @unittest.skipIf(panel.ft is None, "flet not installed")
    def test_view_builds_on_flet_1_and_lists_events(self):
        ports = self.ports

        def factory(host, token):
            return panel.DaemonClient(host, token, ipc_port=ports["CONTINUITY_IPC_PORT"],
                                      telemetry_port=ports["TELEMETRY_PORT"])
        page = FakePage()
        ui = panel.build_view(page, client_factory=factory, poll_seconds=0)
        self.assertTrue(page.controls)
        self.assertTrue(ui["status"].value.startswith("Online"), ui["status"].value)
        ui["post_field"].value = "hello from the UI test"
        ui["post"]()
        texts = [c.value for c in ui["events"].controls]
        self.assertTrue(any("hello from the UI test" in t for t in texts), texts)
        self.assertFalse(ui["post_button"].disabled)


class NoRemovedFletApis(unittest.TestCase):
    def test_source_avoids_removed_apis(self):
        src = PANEL.read_text(encoding="utf-8")
        for removed in ("ft.app(", "ElevatedButton", "SizedBox", "9200"):
            self.assertNotIn(removed, src.split('"""', 2)[-1], removed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
