"""Windows safety (daemon v8.8.1, issue #40).

Run: python -m unittest tests/test_windows_safety.py -v   (no daemon needed)
- UTF-8 console: the [✓] banner can't crash when output is redirected to a cp1252 stream.
- hub_token: owner-only on POSIX (0600/0700) and an icacls owner-only ACL on Windows
  (the Windows path is checked by mocking whoami/icacls; a real Windows run is still needed).
- Ports: a second daemon can't bind a port that is already listening, and exits with a message.
"""
import importlib
import io
import os
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from unittest import mock

ADMIN = Path(__file__).resolve().parent.parent / "Admin"
sys.path.insert(0, str(ADMIN))

_TMP = Path(tempfile.mkdtemp(prefix="omni_windows_safety_test_"))
_REAL_HOME = os.environ.get("HOME", "")  # child python still needs its user site-packages
os.environ["HOME"] = str(_TMP)
os.environ["USERPROFILE"] = str(_TMP)
os.environ.pop("OMNI_TRUSTED_KEYS_FILE", None)
os.environ.pop("OMNI_HUB_REMOTE", None)
os.environ.pop("OMNI_HUB_TOKEN_FILE", None)
os.environ["OMNI_MESH_ID"] = "winsafe-test"
os.chdir(_TMP)

daemon = importlib.import_module("omni_live_daemon_server")  # noqa: E402

SID = "S-1-5-21-1111111111-2222222222-3333333333-1001"


class Utf8ConsoleTests(unittest.TestCase):
    def test_banner_survives_cp1252_stream(self):
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252")
        with self.assertRaises(UnicodeEncodeError):   # the issue #40 crash, before the fix
            stream.write("[✓] Node ID Initialized"); stream.flush()
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252")
        daemon.force_utf8_console([stream])
        stream.write("[✓] Node ID Initialized\n"); stream.flush()
        self.assertIn("[✓]".encode("utf-8"), raw.getvalue())

    def test_redirected_subprocess_does_not_crash(self):
        # Simulates Windows: a legacy console encoding and output redirected to a pipe.
        code = ("import sys; sys.path.insert(0, %r); import os; os.environ['OMNI_MESH_ID']='x'; "
                "import omni_live_daemon_server as d; d.force_utf8_console(); print('[\u2713] ok')") % str(ADMIN)
        env = dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONUTF8="0", HOME=_REAL_HOME)
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, env=env, cwd=str(_TMP), timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        self.assertIn("[✓] ok".encode("utf-8"), r.stdout)

    def test_streams_without_reconfigure_are_ignored(self):
        daemon.force_utf8_console([object()])   # e.g. a pythonw.exe None-ish stream: no exception


class HubTokenPermissionTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=_TMP)) / ".omni"
        self.path = self.dir / "hub_token"

    @unittest.skipIf(os.name == "nt", "POSIX modes")
    def test_posix_owner_only_and_retightened(self):
        tok = daemon.load_or_create_hub_token(self.path)
        self.assertGreaterEqual(len(tok), 32)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.dir.stat().st_mode), 0o700)
        os.chmod(self.path, 0o644)                       # loosened by hand / copied in
        self.assertEqual(daemon.load_or_create_hub_token(self.path), tok)   # same token kept
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)     # and locked again

    def _fake_run(self, calls):
        def run(cmd, **kw):
            calls.append(cmd)
            if cmd[0] == "whoami":
                return subprocess.CompletedProcess(cmd, 0, stdout=f'"desktop-pc\\keith","{SID}"\r\n', stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="processed 1 files", stderr="")
        return run

    def test_windows_uses_icacls_owner_only(self):
        calls = []
        with mock.patch.object(daemon, "IS_WINDOWS", True), \
             mock.patch.object(daemon.subprocess, "run", side_effect=self._fake_run(calls)):
            tok = daemon.load_or_create_hub_token(self.path)
        self.assertGreaterEqual(len(tok), 32)
        icacls = [c for c in calls if c[0] == "icacls"]
        self.assertEqual(icacls[0], ["icacls", str(self.dir), "/inheritance:r", "/grant:r", f"*{SID}:(OI)(CI)F"])
        self.assertEqual(icacls[1], ["icacls", str(self.path), "/inheritance:r", "/grant:r", f"*{SID}:F"])

    def test_windows_icacls_failure_warns_but_keeps_running(self):
        def run(cmd, **kw):
            raise subprocess.CalledProcessError(5, cmd)
        out = io.StringIO()
        with mock.patch.object(daemon, "IS_WINDOWS", True), \
             mock.patch.object(daemon.subprocess, "run", side_effect=run), \
             mock.patch("sys.stdout", out):
            tok = daemon.load_or_create_hub_token(self.path)
        self.assertGreaterEqual(len(tok), 32)
        self.assertIn("WARNING: could not lock", out.getvalue())

    def test_bad_whoami_output_is_an_error(self):
        with mock.patch.object(daemon.subprocess, "run",
                               return_value=subprocess.CompletedProcess([], 0, stdout="garbage", stderr="")):
            with self.assertRaises(OSError):
                daemon._windows_owner_sid()


class _Nop(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass


class SingleInstancePortTests(unittest.TestCase):
    def test_second_bind_on_same_port_exits(self):
        first = daemon.bind_server("127.0.0.1", 0, _Nop)
        port = first.server_address[1]
        try:
            out = io.StringIO()
            with mock.patch("sys.stdout", out), self.assertRaises(SystemExit) as cm:
                daemon.bind_server("127.0.0.1", port, _Nop)
            self.assertEqual(cm.exception.code, 2)
            self.assertIn("already in use", out.getvalue())
        finally:
            first.server_close()

    def test_windows_settings(self):
        if os.name == "nt":
            self.assertFalse(daemon.OmniHTTPServer.allow_reuse_address)
            srv = daemon.bind_server("127.0.0.1", 0, _Nop)
            try:
                self.assertEqual(srv.socket.getsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE), 1)
            finally:
                srv.server_close()
        else:
            self.assertTrue(daemon.OmniHTTPServer.allow_reuse_address)   # fast restart on POSIX

    def test_main_uses_bind_server(self):
        import inspect
        src = inspect.getsource(daemon.main)
        self.assertNotIn("ThreadingHTTPServer(", src)
        self.assertIn("force_utf8_console()", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
