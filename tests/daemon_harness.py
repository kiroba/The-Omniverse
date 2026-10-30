"""Shared harness for the v8.12.1+ daemon tests: one real daemon subprocess on free temp ports with
HOME and cwd in temp dirs (same pattern as tests/test_credits_ledger.py), plus small HTTP and Ed25519
helpers. Run any suite that uses it with: python3 -m unittest tests.<name>
"""
import http.client as httpclient
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADMIN = ROOT / "Admin"
if str(ADMIN) not in sys.path:
    sys.path.insert(0, str(ADMIN))

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_PYPATH = os.pathsep.join(p for p in [os.environ.get("PYTHONPATH", ""), str(ADMIN)] if p)


def free_port(kind=socket.SOCK_STREAM) -> int:
    with socket.socket(socket.AF_INET, kind) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def http(url, data=None, raw=None, timeout=15, headers=None, method=None):
    """(status, json-or-{"raw":...}). data -> JSON body with Content-Length (urllib)."""
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    h = dict(headers or {})
    if body is not None:
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=h,
                                 method=method or ("POST" if body is not None else "GET"))
    try:
        with _OPENER.open(req, timeout=timeout) as r:
            txt = r.read()
            return r.status, (json.loads(txt) if txt else {})
    except urllib.error.HTTPError as e:
        txt = e.read()
        try:
            return e.code, json.loads(txt)
        except ValueError:
            return e.code, {"raw": txt[:200]}


def post_chunked(port: int, path: str, obj=None, raw_chunks=None, timeout=15, headers=None):
    """POST with "Transfer-Encoding: chunked" and no Content-Length, the way Dart's HttpClient
    sends req.write(...) bodies. raw_chunks: list of bytes to send as separate chunks."""
    conn = httpclient.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        chunks = raw_chunks if raw_chunks is not None else [json.dumps(obj).encode("utf-8")]
        h = {"Content-Type": "application/json", **(headers or {})}
        conn.request("POST", path, body=iter(chunks), headers=h, encode_chunked=True)
        r = conn.getresponse()
        txt = r.read()
        try:
            return r.status, json.loads(txt) if txt else {}
        except ValueError:
            return r.status, {"raw": txt[:200]}
    finally:
        conn.close()


def post_raw(port: int, request_bytes: bytes, timeout=10) -> int:
    """Sends exact request bytes (for malformed framing) and returns the status code."""
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as s:
        s.sendall(request_bytes)
        data = b""
        while b"\r\n" not in data:
            part = s.recv(4096)
            if not part:
                break
            data += part
    return int(data.split(b" ")[1]) if data.startswith(b"HTTP/") else 0


class Key:
    """An Ed25519 identity like a phone's StargateIdentity (64-hex pubkey, 128-hex sigs)."""

    def __init__(self, seed: bytes = None):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        self.sk = Ed25519PrivateKey.from_private_bytes(seed) if seed else Ed25519PrivateKey.generate()
        self.pub = self.sk.public_key().public_bytes(serialization.Encoding.Raw,
                                                     serialization.PublicFormat.Raw).hex()

    def sign(self, data: bytes) -> str:
        return self.sk.sign(data).hex()

    def sign_event(self, ev: dict) -> dict:
        """A complete signed event envelope (omni_signing canonical form), like LocalEventStore.append."""
        import omni_signing as sig
        import hashlib
        unsigned = {k: ev[k] for k in ("action", "author_pubkey", "payload", "previous_hash") if k in ev}
        unsigned.update({k: ev[k] for k in ("ts", "timestamp") if k in ev})
        eid = "0x" + hashlib.sha256(sig.canonical_event_bytes(unsigned)).hexdigest()
        return dict(unsigned, event_id=eid, signature=self.sign(sig.canonical_event_bytes(unsigned)))


def now_ms() -> int:
    return int(time.time() * 1000)


class Daemon:
    def __init__(self, root: Path, name: str, env: dict = None, remote: bool = False):
        self.home, self.cwd = root / f"home_{name}", root / f"run_{name}"
        self.home.mkdir(parents=True)
        self.cwd.mkdir(parents=True)
        self.ports = {"OMNI_TELEMETRY_PORT": free_port(), "OMNI_IPC_PORT": free_port(),
                      "OMNI_P2P_PORT": free_port(), "OMNI_UDP_PORT": free_port(socket.SOCK_DGRAM)}
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home), PYTHONPATH=_PYPATH,
                        OMNI_MESH_ID=f"t-{name}"[:32].lower(), OMNI_CATCHUP_INTERVAL="0",
                        OMNI_CATCHUP_STARTUP_DELAY="3600", NO_PROXY="*", OMNI_TELEMETRY_CACHE_S="0",
                        **{k: str(v) for k, v in self.ports.items()})
        for k in ("OMNI_TRUSTED_KEYS_FILE", "OMNI_LEGACY_FLOAT_TS", "OMNI_SYNC_PEERS", "OMNI_HUB_TOKEN_FILE",
                  "OMNI_HUB_REMOTE", "OMNI_HUB_BIND", "OMNI_TREASURY_FEE_BPS"):
            self.env.pop(k, None)
        if remote:
            self.env.update(OMNI_HUB_REMOTE="1", OMNI_HUB_BIND="0.0.0.0")
        self.env.update(env or {})
        self.ipc_port = self.ports["OMNI_IPC_PORT"]
        self.ipc = f"http://127.0.0.1:{self.ipc_port}"
        self.tel = f"http://127.0.0.1:{self.ports['OMNI_TELEMETRY_PORT']}"
        self.db = self.cwd / "continuity_events.db"
        self.proc = None

    def start(self):
        self.log = open(self.cwd / "daemon.log", "a")
        self.proc = subprocess.Popen([sys.executable, str(ADMIN / "omni_live_daemon_server.py")], cwd=self.cwd,
                                     env=self.env, stdout=self.log, stderr=subprocess.STDOUT)
        deadline = time.time() + 20
        while time.time() < deadline:
            if self.proc.poll() is not None:
                break
            try:
                code, body = http(f"{self.tel}/api/v1/telemetry/node-health", timeout=2)
                if code == 200:
                    self.node_id, self.version = body["node_id"], body["version"]
                    return self
            except Exception:
                pass
            time.sleep(0.2)
        self.stop()
        raise AssertionError("daemon did not start:\n" + (self.cwd / "daemon.log").read_text()[-3000:])

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if getattr(self, "log", None):
            self.log.close()

    def restart(self):
        self.stop()
        return self.start()

    def get(self, path, params=None, **kw):
        q = ("?" + urllib.parse.urlencode(params)) if params else ""
        return http(f"{self.ipc}{path}{q}", **kw)

    def post(self, path, obj, **kw):
        return http(f"{self.ipc}{path}", obj, **kw)

    def event_count(self) -> int:
        return self.get("/api/events/stats")[1]["total_events"]


_DAEMON_MODULE = None


def daemon_module():
    """Imports Admin/omni_live_daemon_server.py in-process for unit tests of its pure functions.
    Importing it creates a node key under ~/.omniverse, so HOME points at a temp dir while it loads."""
    global _DAEMON_MODULE
    if _DAEMON_MODULE is None:
        import importlib
        import tempfile
        saved = os.environ.get("HOME")
        os.environ["HOME"] = tempfile.mkdtemp(prefix="omni_import_home_")
        try:
            for m in ("omni_signing", "omni_live_daemon_server"):
                sys.modules.pop(m, None)
            _DAEMON_MODULE = importlib.import_module("omni_live_daemon_server")
        finally:
            if saved is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = saved
    return _DAEMON_MODULE
