"""Daemon v8.17.1 fixes found while writing API_REFERENCE.md:
1. GET :9100/api/omnimind/telemetry wrote its body twice (bytes past Content-Length).
2. /api/events/stats, /api/events/list and /api/v1/telemetry/node-health 404'd on any query string.
Run: python3 -m unittest tests.test_api_ref_fixes
"""
import json
import shutil
import socket
import tempfile
import unittest
from pathlib import Path

from tests.daemon_harness import Daemon, http
from tests.daemon_version import DAEMON_VERSION


def raw_get(port: int, path: str, timeout=10):
    """GET over a bare socket, read to EOF (the handler speaks HTTP/1.0 and closes), so any bytes
    written after the declared body are visible. Returns (status, headers dict, body bytes)."""
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as s:
        s.sendall(f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n".encode())
        data = b""
        while True:
            part = s.recv(65536)
            if not part:
                break
            data += part
    head, _, body = data.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    headers = {k.strip().lower(): v.strip() for k, _, v in (l.partition(":") for l in lines[1:])}
    return int(lines[0].split(" ")[1]), headers, body


class ApiRefFixesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_apiref_"))
        cls.d = Daemon(cls.tmp, "apiref").start()
        cls.tel_port = cls.d.ports["OMNI_TELEMETRY_PORT"]

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_version(self):
        self.assertEqual(self.d.version, DAEMON_VERSION)

    def test_omnimind_telemetry_body_written_once(self):
        code, _ = http(f"{self.d.tel}/api/omnimind/telemetry", {"cpu_percent": 12.5, "mem_mb": 210})
        self.assertEqual(code, 200)
        status, headers, body = raw_get(self.tel_port, "/api/omnimind/telemetry")
        self.assertEqual(status, 200)
        self.assertEqual(int(headers["content-length"]), len(body))
        obj = json.loads(body.decode("utf-8"))   # raises on a doubled body ("Extra data")
        self.assertIsInstance(obj, dict)
        self.assertEqual(obj["cpu_percent"], 12.5)
        self.assertIn("age_seconds", obj)

    def test_query_string_ignored(self):
        for base, path in ((self.d.ipc, "/api/events/stats"), (self.d.ipc, "/api/events/list"),
                           (self.d.tel, "/api/v1/telemetry/node-health")):
            with self.subTest(path=path):
                code, body = http(f"{base}{path}?x=1")
                self.assertEqual(code, 200, body)
                self.assertNotIn("raw", body)


if __name__ == "__main__":
    unittest.main()
