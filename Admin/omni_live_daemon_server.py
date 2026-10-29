#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE LIVE LOCAL DAEMON ENGINE [v8.9.0 - Hardened Mesh Spine]
==============================================================================
Architecture:
- Port 9100 (127.0.0.1): Node Health Telemetry & Agent Cache
- Port 5000 (127.0.0.1): Local IPC Event Gateway (loopback-only bind; GET /api/events/feed lists events)
- Port 5005 (0.0.0.0): P2P Network Sync Gateway (Signed Envelopes, Hash Verified)
- Port 9101 (0.0.0.0): UDP Subnet Discovery Broadcaster/Listener (Advertises 5005)
Mesh name (OMNI_MESH_ID, default "dev"): beacons and /p2p/sync requests carry it; other meshes are ignored/403.
Remote hub (opt-in, v8.7.0): OMNI_HUB_REMOTE=1 + OMNI_HUB_BIND=<ip> also serves the app endpoints
(feed, append, stats, node-health) on that address. Non-loopback requests need
"Authorization: Bearer <token>" (token in ~/.omni/hub_token) and remote posts must carry the phone's
own Ed25519 signature. See Admin/docs/REMOTE_HUB.md.
Catch-up sync (v8.8.0): on startup, when a new peer is discovered and every OMNI_CATCHUP_INTERVAL
seconds, the node reconciles its event set with its peers (negentropy v1 range-based set
reconciliation over POST /p2p/reconcile on :5005), fetches only the events it lacks (POST
/p2p/events) and pushes the ones the peer lacks (POST /p2p/sync). Fetched events go through the same
hash/signature/allowlist checks as /p2p/sync. See Admin/docs/CATCHUP_SYNC.md.
Windows (v8.8.1): console output is forced to UTF-8 (redirected output can't crash on the banner),
~/.omni and hub_token get an owner-only ACL via icacls, and the TCP ports are bound with
SO_EXCLUSIVEADDRUSE so a second daemon fails fast instead of sharing them.
Bug reports (v8.9.0): POST :5000/api/bugs/report stores a tester's report (JSON, max 8 KB, required
"what_happened") as a node-signed chain event with action "bug_report"; GET :5000/api/bugs/list
(loopback only) lists them newest first. The POST is also allowed in remote hub mode with the bearer
token. Admin/omnimind_bug_triage_utility.py verifies and groups them. See Admin/docs/BUG_REPORTS.md.
==============================================================================
"""

import os
import re
import sys
import time
import json
import sqlite3
import hashlib
import hmac
import secrets
import subprocess
from omni_signing import (load_or_create_key, pubkey_hex, sign_event, verify_event,
                          canonical_event_bytes, now_ms, load_trusted_keys, is_trusted,
                          TRUSTED_KEYS_ENV)
import omni_negentropy as neg
import threading
import socket
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

VERSION = "8.9.0"
def _env_port(name: str, default: int) -> int:
    """Port override (e.g. to run two nodes on one machine for tests). Bad values fall back."""
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw.isdigit() and 0 < int(raw) < 65536 else default

TELEMETRY_PORT = _env_port("OMNI_TELEMETRY_PORT", 9100)
CONTINUITY_IPC_PORT = _env_port("OMNI_IPC_PORT", 5000)
P2P_SYNC_PORT = _env_port("OMNI_P2P_PORT", 5005)
UDP_DISCOVERY_PORT = _env_port("OMNI_UDP_PORT", 9101)
OMNIMIND_MAX_PAYLOAD = 64 * 1024
OMNIMIND_STALE_SECONDS = 15.0

IPC_HOST = "127.0.0.1"
P2P_HOST = "0.0.0.0"
MAX_PAYLOAD_SIZE = 5 * 1024 * 1024  # 5 MB Strict Cap
# Set OMNI_LEGACY_FLOAT_TS=1 while any peer still runs a pre-8.5.1 daemon: those peers only
# understand float "timestamp", so events this node stamps itself would 401 there.
LEGACY_FLOAT_TS = os.environ.get("OMNI_LEGACY_FLOAT_TS", "").strip() in ("1", "true", "yes")
# Events stamped further ahead than this are rejected (clock skew allowance). OMNI_MAX_FUTURE_SKEW_S.
try:
    MAX_FUTURE_SKEW_S = float(os.environ.get("OMNI_MAX_FUTURE_SKEW_S", "600"))
except ValueError:
    MAX_FUTURE_SKEW_S = 600.0
DB_WRITE_LOCK = threading.Lock()   # serializes read-head + insert (see process_and_store_event)

# Mesh name: keeps dev and production meshes apart (defense in depth next to the trusted-keys
# allowlist). It travels in UDP beacons and in the X-Omni-Mesh header on /p2p/sync. It is NOT part
# of the signed canonical event, so signatures and the Dart interop vectors are unchanged.
MESH_ID_ENV = "OMNI_MESH_ID"
MESH_HEADER = "X-Omni-Mesh"
DEFAULT_MESH_ID = "dev"
_MESH_ID_RE = re.compile(r"[a-z0-9-]{1,32}")

def load_mesh_id(value=None) -> str:
    """Returns the mesh id from `value` or $OMNI_MESH_ID (unset/empty -> "dev").
    Raises ValueError unless it is 1-32 chars of [a-z0-9-]."""
    if value is None:
        value = os.environ.get(MESH_ID_ENV, "")
    value = value.strip()
    if not value:
        return DEFAULT_MESH_ID
    if not _MESH_ID_RE.fullmatch(value):
        raise ValueError(f"{MESH_ID_ENV}={value!r} is invalid: use 1-32 chars of a-z, 0-9 and '-'")
    return value

# --- Remote hub (opt-in) --------------------------------------------------------------------------
# Off by default: :9100 and :5000 stay on 127.0.0.1 exactly as before. With OMNI_HUB_REMOTE=1 the app
# endpoints also listen on OMNI_HUB_BIND (e.g. the phone's Tailscale 100.x IP, or 0.0.0.0), and every
# non-loopback request must send "Authorization: Bearer <token>".
HUB_REMOTE_ENV = "OMNI_HUB_REMOTE"
HUB_BIND_ENV = "OMNI_HUB_BIND"
HUB_TOKEN_FILE_ENV = "OMNI_HUB_TOKEN_FILE"
HUB_REMOTE = os.environ.get(HUB_REMOTE_ENV, "").strip().lower() in ("1", "true", "yes")
HUB_BIND = os.environ.get(HUB_BIND_ENV, "").strip() or "127.0.0.1"
# Paths a remote (authenticated) app may use. Everything else stays loopback-only
# (e.g. POST /api/omnimind/telemetry, the local agent's cache).
REMOTE_GET_PATHS = {"/api/events/feed", "/api/events/stats", "/api/events/list", "/api/v1/telemetry/node-health"}
REMOTE_POST_PATHS = {"/api/events/append", "/api/bugs/report"}
_APP_ENVELOPE_KEYS = ("app_event_id", "app_author_pubkey", "app_signature", "app_previous_hash",
                      "app_ts", "app_timestamp")

# Catch-up sync (v8.8.0). Peers come from UDP discovery (same mesh) plus OMNI_SYNC_PEERS, a
# comma-separated list of host:port P2P endpoints (needed over Tailscale, where beacons don't reach).
SYNC_PEERS_ENV = "OMNI_SYNC_PEERS"
CATCHUP_INTERVAL_ENV = "OMNI_CATCHUP_INTERVAL"            # seconds between periodic runs; 0 = off
CATCHUP_STARTUP_DELAY_ENV = "OMNI_CATCHUP_STARTUP_DELAY"  # seconds after start before the first run
CATCHUP_PUSH_ENV = "OMNI_CATCHUP_PUSH"                    # 0 = only pull; default pushes too
RECONCILE_MAX_ROUNDS = 32
FETCH_BATCH = 200
FETCH_MAX_RESPONSE = 4 * 1024 * 1024
_EVENT_ID_RE = re.compile(r"0x[0-9a-f]{64}")
_PEER_HOST_RE = re.compile(r"[A-Za-z0-9.\-:\[\]]{1,255}")

def _env_float(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.environ.get(name, "").strip() or default))
    except ValueError:
        return default

def parse_sync_peers(value=None) -> list:
    """OMNI_SYNC_PEERS="100.64.0.7:5005,laptop.tailnet.ts.net" -> [("100.64.0.7", 5005), ...].
    Port defaults to 5005. Raises ValueError on a malformed entry (never silently drops a peer)."""
    if value is None:
        value = os.environ.get(SYNC_PEERS_ENV, "")
    peers = []
    for raw in value.split(","):
        entry = raw.strip()
        if not entry:
            continue
        host, port = entry, P2P_SYNC_PORT
        if entry.count(":") == 1:
            host, _, port_s = entry.partition(":")
            if not port_s.isdigit() or not 0 < int(port_s) < 65536:
                raise ValueError(f"{SYNC_PEERS_ENV}: bad port in {entry!r}")
            port = int(port_s)
        if not _PEER_HOST_RE.fullmatch(host):
            raise ValueError(f"{SYNC_PEERS_ENV}: bad host in {entry!r}")
        peers.append((host, port))
    return peers

def hub_token_path() -> Path:
    override = os.environ.get(HUB_TOKEN_FILE_ENV, "").strip()
    return Path(override) if override else Path.home() / ".omni" / "hub_token"

IS_WINDOWS = os.name == "nt"

def force_utf8_console(streams=None):
    """Makes stdout/stderr UTF-8 with errors='replace' so the [✓] banner can't raise
    UnicodeEncodeError when Windows redirects output to a cp1252 file or pipe."""
    for stream in (streams if streams is not None else (sys.stdout, sys.stderr)):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass

def _windows_owner_sid() -> str:
    """Current user's SID, e.g. S-1-5-21-..., from `whoami /user`."""
    out = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"], capture_output=True,
                         text=True, check=True, timeout=10).stdout
    sid = out.strip().split(",")[-1].strip().strip('"')
    if not sid.startswith("S-1-"):
        raise OSError(f"could not read the current user's SID from whoami: {out!r}")
    return sid

def restrict_to_owner(path: Path, is_dir: bool = False, windows: bool = None):
    """Owner-only access. POSIX: chmod 700/600. Windows: chmod is a no-op there, so drop
    inherited ACEs and grant Full Control to the current user's SID only (icacls)."""
    windows = IS_WINDOWS if windows is None else windows
    if not windows:
        os.chmod(path, 0o700 if is_dir else 0o600)
        return
    grant = f"*{_windows_owner_sid()}:" + ("(OI)(CI)F" if is_dir else "F")
    subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", grant],
                   capture_output=True, text=True, check=True, timeout=15)

def load_or_create_hub_token(path: Path = None) -> str:
    """Returns the persisted remote-hub token, creating it owner-only on first use.
    Permissions are re-tightened on every start, so a token copied in loosely gets locked down."""
    path = path or hub_token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        restrict_to_owner(path.parent, is_dir=True)   # first, so a new file inherits owner-only
    except (OSError, subprocess.SubprocessError) as e:
        print(f"[!] Could not restrict {path.parent} to the current user: {e}", flush=True)
    tok = None
    if path.exists():
        tok = path.read_text(encoding="utf-8").strip()
        if len(tok) < 32:
            tok = None
    if tok is None:
        tok = secrets.token_urlsafe(32)
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(tok + "\n")
    try:
        restrict_to_owner(path)
    except (OSError, subprocess.SubprocessError) as e:
        if not IS_WINDOWS:
            raise
        print(f"[!] WARNING: could not lock {path} to the current user ({e}). "
              f"Run: icacls \"{path}\" /inheritance:r /grant:r \"%USERNAME%:F\"", flush=True)
    return tok

class OmniHTTPServer(ThreadingHTTPServer):
    """One daemon per port. On Windows SO_REUSEADDR lets a second process bind a port that is
    already listening, so it is off there and SO_EXCLUSIVEADDRUSE is set instead. On POSIX
    SO_REUSEADDR only skips TIME_WAIT (fast restart) and a second bind still fails, so keep it."""
    allow_reuse_address = not IS_WINDOWS

    def server_bind(self):
        if IS_WINDOWS and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

def bind_server(host: str, port: int, handler):
    """Binds or exits with a plain message when another process (usually a second daemon) has the port."""
    try:
        return OmniHTTPServer((host, port), handler)
    except OSError as e:
        print(f"[X] Port {host}:{port} is already in use ({e}). Is another Omniverse daemon running? "
              f"Stop it first; only one daemon per machine.", flush=True)
        sys.exit(2)

def check_bearer(header_value, token) -> bool:
    """Constant-time check of an "Authorization: Bearer <token>" header."""
    if not token or not header_value:
        return False
    scheme, _, presented = str(header_value).strip().partition(" ")
    if scheme.lower() != "bearer":
        return False
    return hmac.compare_digest(presented.strip().encode("utf-8"), token.encode("utf-8"))

def unwrap_remote_event(data: dict) -> dict:
    """A remote app's post as the event the PHONE signed. Accepts either the signed event itself
    (author_pubkey + signature at top level) or the shape OmniHubClient.appendEvent sends today
    (the app's envelope inside payload as app_*). The daemon never signs on the remote app's behalf."""
    if not isinstance(data, dict):
        raise ValueError("body must be a JSON object")
    if data.get("author_pubkey") and data.get("signature"):
        return data
    payload = data.get("payload")
    if not isinstance(payload, dict) or not payload.get("app_author_pubkey") or not payload.get("app_signature"):
        raise ValueError("remote posts must carry the phone's own signature "
                         "(author_pubkey + signature, or payload.app_author_pubkey + payload.app_signature)")
    inner = {k: v for k, v in payload.items() if k not in _APP_ENVELOPE_KEYS}
    event = {"action": data.get("action", "USER_ACTION"), "author_pubkey": payload["app_author_pubkey"],
             "payload": inner, "previous_hash": payload.get("app_previous_hash"),
             "signature": payload["app_signature"]}
    if "app_ts" in payload:
        event["ts"] = payload["app_ts"]
    elif "app_timestamp" in payload:
        event["timestamp"] = payload["app_timestamp"]
    if payload.get("app_event_id"):
        event["event_id"] = payload["app_event_id"]
    return event

def hub_listen_hosts(remote: bool = None, bind: str = None) -> list:
    """Addresses :9100/:5000 bind to. Default: loopback only. 0.0.0.0 already covers loopback."""
    remote = HUB_REMOTE if remote is None else remote
    bind = HUB_BIND if bind is None else bind
    if not remote or bind in ("127.0.0.1", "localhost", ""):
        return ["127.0.0.1"]
    if bind == "0.0.0.0":
        return ["0.0.0.0"]
    return ["127.0.0.1", bind]

def tailscale_ip():
    """This device's Tailscale 100.x address if Tailscale is up (no packet is sent)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("100.100.100.100", 53))   # Tailscale's MagicDNS address routes via the tailnet
        ip = s.getsockname()[0]
        s.close()
        return ip if ip.startswith("100.") else None
    except Exception:
        return None

class EngineState:
    def __init__(self):
        try:
            self.mesh_id = load_mesh_id()   # refuse to start on a bad value, never fall back silently
        except ValueError as e:
            sys.stderr.write(f"[x] FATAL: {e}\n")
            raise SystemExit(2)
        self.mesh_logged = set()  # (peer_ip, their_mesh) pairs already logged as rejected
        self.signing_key = load_or_create_key()          # same key every restart
        self.node_id = pubkey_hex(self.signing_key)       # node id = public key
        self.start_time = time.time()
        self.seen_event_ids = set()
        self.omnimind_telemetry = None   # latest OmniMind agent payload
        self.omnimind_received_at = 0.0
        self.active_peers = {}  # {peer_ip: {"ip": peer_ip, "port": 5005, "last_seen": time.time()}}
        self.rx_bytes = 0
        self.tx_bytes = 0
        self.lock = threading.Lock()
        # None = no allowlist (any valid signature accepted). Raises on a bad/missing file.
        self.trusted_keys = load_trusted_keys()
        if self.trusted_keys is not None:
            self.trusted_keys = self.trusted_keys | {self.node_id}  # our own relayed events
        self.hub_token = load_or_create_hub_token() if HUB_REMOTE else None
        try:
            self.sync_peers = parse_sync_peers()
        except ValueError as e:
            sys.stderr.write(f"[x] FATAL: {e}\n")
            raise SystemExit(2)
        self.catchup_lock = threading.Lock()   # one catch-up run at a time
        self.catchup_wake = threading.Event()  # set when a new peer shows up
        self.last_catchup = None               # summary of the last run, shown in node-health

STATE = EngineState()

def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()

def init_db() -> Path:
    db_path = Path.cwd() / "continuity_events.db"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            action TEXT NOT NULL,
            author_pubkey TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            timestamp REAL NOT NULL,
            payload_json TEXT DEFAULT '{}',
            signature TEXT
        );
    """)
    # Migration check for payload_json column
    c.execute("PRAGMA table_info(events);")
    columns = [col[1] for col in c.fetchall()]
    if "payload_json" not in columns:
        c.execute("ALTER TABLE events ADD COLUMN payload_json TEXT DEFAULT '{}';")
        conn.commit()
    if "signature" not in columns:
        c.execute("ALTER TABLE events ADD COLUMN signature TEXT;")
        conn.commit()
    if "ts_ms" not in columns:  # exact signed int-ms time; NULL for legacy float events
        c.execute("ALTER TABLE events ADD COLUMN ts_ms INTEGER;")
        conn.commit()

    # Load seen event_ids into memory for fast deduplication
    c.execute("SELECT event_id FROM events;")
    for row in c.fetchall():
        if row[0]:
            STATE.seen_event_ids.add(row[0])

    # Ensure Genesis event exists
    c.execute("SELECT COUNT(*) FROM events;")
    if c.fetchone()[0] == 0:
        genesis_time = 1700000000.0
        genesis_hash = "0x" + "0" * 64
        c.execute("""
            INSERT INTO events (event_id, action, author_pubkey, previous_hash, timestamp, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("0xgenesis_000", "GENESIS_NODE_INIT", STATE.node_id, genesis_hash, genesis_time, json.dumps({"system": "Genesis Node Init"})))
        STATE.seen_event_ids.add("0xgenesis_000")
        conn.commit()
    conn.close()
    return db_path

def compute_canonical_event_id(action: str, author_pubkey: str, payload_obj: dict, previous_hash: str, timestamp: float = None, ts_ms: int = None) -> str:
    """Legacy events hash with float "timestamp"; new events hash with int-ms "ts" (see omni_signing)."""
    struct = {"action": action, "author_pubkey": author_pubkey, "payload": payload_obj,
              "previous_hash": previous_hash}
    if ts_ms is not None:
        struct["ts"] = ts_ms
    else:
        struct["timestamp"] = timestamp
    return "0x" + hashlib.sha256(canonical_event_bytes(struct)).hexdigest()

def resolve_event_time(data: dict, is_local: bool) -> tuple:
    """Returns (time_fields, timestamp_seconds_for_db, ts_ms_or_None). Raises ValueError on bad input.

    - "ts" present: must be an integer (ms). Kept as-is, it is part of the signed bytes.
    - "timestamp" present: legacy float seconds, kept as before.
    - neither: remote events are rejected; local events get a fresh int-ms ts
      (float seconds instead when OMNI_LEGACY_FLOAT_TS=1).
    """
    if "ts" in data and "timestamp" in data:
        raise ValueError("send exactly one of 'ts' (int ms) or 'timestamp' (float s)")
    if "ts" in data:
        ts = data["ts"]
        if not isinstance(ts, int) or isinstance(ts, bool) or ts < 0:
            raise ValueError("'ts' must be a non-negative integer number of milliseconds")
        return {"ts": ts}, ts / 1000.0, ts
    if "timestamp" in data:
        try:
            timestamp = float(data["timestamp"])
        except (ValueError, TypeError):
            if not is_local:
                raise ValueError("'timestamp' is not a number")
            timestamp = time.time()
        return {"timestamp": timestamp}, timestamp, None
    if not is_local:
        raise ValueError("peer event has no 'ts' or 'timestamp'")
    if LEGACY_FLOAT_TS:
        timestamp = time.time()
        return {"timestamp": timestamp}, timestamp, None
    ts = now_ms()
    return {"ts": ts}, ts / 1000.0, ts

def _chain_and_insert(c, data, action, author, payload_obj, time_fields, timestamp, ts_ms, origin_peer):
    """Runs inside process_and_store_event's write transaction. Returns (response, status); a stored
    event's response carries _event_id/_prev_hash/_signature for the caller to pop."""
    c.execute("SELECT event_id FROM events ORDER BY id DESC LIMIT 1;")
    last_row = c.fetchone()
    expected_prev_hash = last_row[0] if last_row else ("0x" + "0" * 64)

    provided_prev_hash = data.get("previous_hash")
    prev_hash = provided_prev_hash if provided_prev_hash else expected_prev_hash

    computed_event_id = compute_canonical_event_id(action, author, payload_obj, prev_hash, timestamp, ts_ms)
    provided_event_id = data.get("event_id")
    if provided_event_id and provided_event_id != computed_event_id:
        return {"status": "ERROR", "message": f"Event hash mismatch. Computed: {computed_event_id}, Provided: {provided_event_id}"}, 400
    event_id = computed_event_id

    # --- Ed25519: remote events must be signed by their author; local events get signed by us ---
    unsigned = {"action": action, "author_pubkey": author, "payload": payload_obj,
                "previous_hash": prev_hash, **time_fields}
    if origin_peer is None:
        signature = sign_event(STATE.signing_key, unsigned)
    else:
        signature = str(data.get("signature", ""))
        if not verify_event(dict(unsigned, signature=signature)):
            return {"status": "ERROR", "message": "Invalid or missing signature"}, 401
        if not is_trusted(author, STATE.trusted_keys):
            return {"status": "ERROR", "message": "Author key is not in this node's trusted-keys allowlist"}, 403

    with STATE.lock:
        if event_id in STATE.seen_event_ids:
            return {"status": "SUCCESS", "event_id": event_id, "result": "ALREADY_EXISTS"}, 200
    c.execute("SELECT id FROM events WHERE event_id = ?;", (event_id,))
    if c.fetchone():
        with STATE.lock:
            STATE.seen_event_ids.add(event_id)
        return {"status": "SUCCESS", "event_id": event_id, "result": "ALREADY_EXISTS"}, 200

    c.execute("""
        INSERT INTO events (event_id, action, author_pubkey, previous_hash, timestamp, payload_json, signature, ts_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (event_id, action, author, prev_hash, timestamp, json.dumps(payload_obj), signature, ts_ms))
    return {"status": "SUCCESS", "_event_id": event_id, "_prev_hash": prev_hash, "_signature": signature}, 200

def process_and_store_event(data: dict, origin_peer: str = None, relay: bool = True) -> tuple[dict, int]:
    action = str(data.get("action", "USER_ACTION")).strip()
    if origin_peer is None:
        author = STATE.node_id   # local app: this node is the author, never trust a client-supplied name
    else:
        author = str(data.get("author_pubkey", "")).strip()
    payload_obj = data.get("payload", {})
    if not isinstance(payload_obj, dict):
        payload_obj = {}

    # Time field: int-ms "ts" (new) or float "timestamp" (legacy); exactly what was signed
    try:
        time_fields, timestamp, ts_ms = resolve_event_time(data, is_local=origin_peer is None)
    except ValueError as e:
        return {"status": "ERROR", "message": str(e)}, 400

    # Replay of an already-stored event is a no-op (content-addressed event_id dedup below). Old events
    # are fine (catch-up needs them), but far-future ones are rejected so a peer can't pin the head.
    if timestamp > time.time() + MAX_FUTURE_SKEW_S:
        return {"status": "ERROR", "message": f"Event time is more than {int(MAX_FUTURE_SKEW_S)}s in the future"}, 400

    db_path = Path.cwd() / "continuity_events.db"
    # Read-head + insert is one critical section: without it two concurrent appends both chain onto
    # the same head and fork the log (issue #7). The thread lock covers this process; BEGIN IMMEDIATE
    # takes SQLite's write lock so a second process on the same DB can't interleave either.
    with DB_WRITE_LOCK:
        conn = sqlite3.connect(str(db_path), timeout=10.0, isolation_level=None)
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE;")
            result = _chain_and_insert(c, data, action, author, payload_obj, time_fields, timestamp,
                                       ts_ms, origin_peer)
            if result[1] == 200 and result[0].get("result") != "ALREADY_EXISTS":
                c.execute("COMMIT;")
            else:
                c.execute("ROLLBACK;")
        except Exception:
            try:
                conn.execute("ROLLBACK;")
            except sqlite3.Error:
                pass
            raise
        finally:
            conn.close()
    resp, status = result
    if status != 200 or resp.get("result") == "ALREADY_EXISTS":
        return resp, status
    event_id, prev_hash, signature = resp.pop("_event_id"), resp.pop("_prev_hash"), resp.pop("_signature")

    with STATE.lock:
        STATE.seen_event_ids.add(event_id)

    event_envelope = {
        "event_id": event_id,
        "action": action,
        "author_pubkey": author,
        "previous_hash": prev_hash,
        **time_fields,  # "ts" or "timestamp", never both: peers verify exactly what was signed
        "payload": payload_obj,
        "signature": signature
    }

    # Relay to active P2P peers (skipping origin sender). Catch-up passes relay=False: every peer
    # reconciles for itself, so re-relaying a backlog would only multiply traffic.
    if relay:
        threading.Thread(target=relay_event_to_peers, args=(event_envelope, origin_peer), daemon=True).start()

    return {"status": "SUCCESS", "event_id": event_id, "merkle_hash": prev_hash, **time_fields}, 200

def relay_event_to_peers(event_envelope: dict, origin_peer: str = None):
    with STATE.lock:
        peers = list(STATE.active_peers.values())

    json_bytes = json.dumps(event_envelope, sort_keys=True, separators=(',', ':')).encode('utf-8')
    for peer in peers:
        peer_ip = peer.get("ip")
        if not peer_ip or peer_ip == LOCAL_IP or peer_ip == "127.0.0.1":
            continue
        peer_port = int(peer.get("port") or P2P_SYNC_PORT)   # the port the peer advertised
        if origin_peer and (peer_ip == origin_peer or f"{peer_ip}:{peer_port}" == origin_peer):
            continue  # Skip relaying back to sender!

        url = f"http://{peer_ip}:{peer_port}/p2p/sync"
        try:
            req = urllib.request.Request(url, data=json_bytes, method='POST',
                                         headers={'Content-Type': 'application/json', MESH_HEADER: STATE.mesh_id})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                pass
        except Exception:
            pass

BEACON_DOMAIN = b"OMNI_BEACON_V1\n"   # domain-separates beacon signatures from event signatures
BEACON_MAX_AGE_MS = 60_000
REQUIRE_SIGNED_BEACONS = os.environ.get("OMNI_REQUIRE_SIGNED_BEACONS", "").strip() in ("1", "true", "yes")

def _beacon_bytes(msg: dict) -> bytes:
    body = {k: v for k, v in msg.items() if k != "sig"}
    return BEACON_DOMAIN + json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

def _log_beacon_reject_once(peer_ip: str, reason: str):
    key = (peer_ip, "beacon:" + reason)
    with STATE.lock:
        if key in STATE.mesh_logged:
            return
        if len(STATE.mesh_logged) >= 1024:
            STATE.mesh_logged.clear()
        STATE.mesh_logged.add(key)
    print(f"[!] UDP discovery: ignoring {peer_ip}: {reason}", flush=True)

def build_beacon() -> dict:
    """UDP 9101 beacon, signed with this node's Ed25519 key (node_id is the public key)."""
    msg = {"type": "OMNI_P2P_BEACON", "node_id": STATE.node_id, "mesh_id": STATE.mesh_id,
           "ip": LOCAL_IP, "port": P2P_SYNC_PORT, "transport": "UDP_LAN", "ts": now_ms()}
    msg["sig"] = STATE.signing_key.sign(_beacon_bytes(msg)).hex()
    return msg

def beacon_signature_ok(msg: dict) -> bool:
    """Signed beacon: valid Ed25519 sig by node_id over the beacon, and ts within 60 s of now
    (stops a captured beacon being replayed later)."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    ts = msg.get("ts")
    if not isinstance(ts, int) or isinstance(ts, bool) or abs(now_ms() - ts) > BEACON_MAX_AGE_MS:
        return False
    try:
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(str(msg.get("node_id", ""))))
        pub.verify(bytes.fromhex(str(msg.get("sig", ""))), _beacon_bytes(msg))
        return True
    except (ValueError, TypeError, InvalidSignature):
        return False

def beacon_allowed(msg: dict, peer_ip: str) -> bool:
    """Signed beacons must verify (and, with an allowlist, come from a trusted key). Unsigned beacons
    (pre-8.9 daemons) are accepted only when there is no allowlist and OMNI_REQUIRE_SIGNED_BEACONS is off."""
    if "sig" in msg:
        if not beacon_signature_ok(msg):
            _log_beacon_reject_once(peer_ip, "bad-or-stale-beacon-signature")
            return False
        if not is_trusted(str(msg.get("node_id", "")), STATE.trusted_keys):
            _log_beacon_reject_once(peer_ip, "untrusted-beacon-key")
            return False
        return True
    if REQUIRE_SIGNED_BEACONS or STATE.trusted_keys is not None:
        _log_beacon_reject_once(peer_ip, "unsigned-beacon")
        return False
    return True

def udp_discovery_broadcaster():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    while True:
        try:
            payload = json.dumps(build_beacon()).encode('utf-8')
            sock.sendto(payload, ('<broadcast>', UDP_DISCOVERY_PORT))
        except Exception:
            pass
        time.sleep(3.0)

def log_mesh_reject_once(peer_ip: str, their_mesh, where: str):
    key = (peer_ip, their_mesh)
    with STATE.lock:
        if key in STATE.mesh_logged:
            return
        if len(STATE.mesh_logged) >= 1024:  # bound memory if a LAN host sprays random mesh ids
            STATE.mesh_logged.clear()
        STATE.mesh_logged.add(key)
    shown = repr(their_mesh)[:40] if their_mesh is not None else "missing"
    print(f"[!] {where}: ignoring {peer_ip}: mesh {shown} != ours ({STATE.mesh_id})", flush=True)

def handle_discovery_packet(msg: dict, peer_ip: str) -> bool:
    """Adds the sender to active_peers if it is a beacon from another node on our mesh. Returns True if added."""
    if not isinstance(msg, dict) or msg.get("type") != "OMNI_P2P_BEACON" or msg.get("node_id") == STATE.node_id:
        return False
    their_mesh = msg.get("mesh_id")
    if their_mesh != STATE.mesh_id:
        with STATE.lock:
            STATE.active_peers.pop(peer_ip, None)  # a peer that moved to another mesh is dropped
        log_mesh_reject_once(peer_ip, their_mesh, "UDP discovery")
        return False
    if not beacon_allowed(msg, peer_ip):
        return False
    peer_port = int(msg.get("port", P2P_SYNC_PORT))
    with STATE.lock:
        old = STATE.active_peers.get(peer_ip)
        is_new = old is None or time.time() - old["last_seen"] >= 15.0   # new or back after a gap
        STATE.active_peers[peer_ip] = {"ip": peer_ip, "port": peer_port, "last_seen": time.time()}
    if is_new:
        STATE.catchup_wake.set()   # (re)connected peer: reconcile with it soon
    return True

def udp_discovery_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if not IS_WINDOWS:   # on Windows this would let a second daemon share 9101
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(('0.0.0.0', UDP_DISCOVERY_PORT))
    except Exception:
        return

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            msg = json.loads(data.decode('utf-8'))
            handle_discovery_packet(msg, addr[0])
        except Exception:
            pass

# --- Event feed (GET :5000/api/events/feed) -------------------------------------------------------
FEED_DEFAULT_LIMIT = 50
FEED_MAX_LIMIT = 200
_FEED_TYPE_RE = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
_FEED_ARGS = {"limit", "before", "since", "type"}

def _feed_int(params: dict, name: str):
    vals = params.get(name)
    if not vals:
        return None
    v = vals[-1].strip()
    if not re.fullmatch(r"\d{1,18}", v):
        raise ValueError(f"'{name}' must be a non-negative integer")
    return int(v)

def parse_feed_query(query: str) -> dict:
    """Parses ?limit=&before=&since=&type= . Raises ValueError on bad input.
    limit: default 50, clamped to 1..200. before/since: event row ids (the cursor). type: action name."""
    params = urllib.parse.parse_qs(query or "", keep_blank_values=True)
    unknown = set(params) - _FEED_ARGS
    if unknown:
        raise ValueError(f"unknown parameter(s): {', '.join(sorted(unknown))}")
    limit = _feed_int(params, "limit")
    limit = FEED_DEFAULT_LIMIT if limit is None else max(1, min(limit, FEED_MAX_LIMIT))
    before = _feed_int(params, "before")
    since = _feed_int(params, "since")
    etype = None
    if params.get("type"):
        etype = params["type"][-1].strip()
        if etype and not _FEED_TYPE_RE.fullmatch(etype):
            raise ValueError("'type' must be 1-64 chars of A-Z a-z 0-9 _ . : -")
        etype = etype or None
    return {"limit": limit, "before": before, "since": since, "type": etype}

def _row_to_feed_event(row) -> dict:
    rowid, event_id, action, author, prev_hash, timestamp, payload_json, signature, ts_ms = row
    try:
        payload = json.loads(payload_json or "{}")
        if not isinstance(payload, dict):
            payload = {}
    except ValueError:
        payload = {}
    # Exactly the time field that was signed: int-ms "ts" for new events, float "timestamp" for legacy.
    time_fields = {"ts": int(ts_ms)} if ts_ms is not None else {"timestamp": timestamp}
    verified = False
    if signature:
        try:
            verified = bool(verify_event({"action": action, "author_pubkey": author, "payload": payload,
                                          "previous_hash": prev_hash, **time_fields, "signature": signature}))
        except Exception:
            verified = False
    return {
        "id": rowid,
        "event_id": event_id,
        "type": action,
        "action": action,
        "author_pubkey": author,
        "origin": "local" if author == STATE.node_id else "remote",
        **time_fields,
        "ts_ms": int(ts_ms) if ts_ms is not None else int(round(float(timestamp) * 1000)),
        "payload": payload,           # includes app_* fields (the app's own signed envelope) when present
        "previous_hash": prev_hash,
        "signature": signature,
        "verified": verified,         # node/author Ed25519 signature re-checked at read time
    }

def list_feed_events(limit: int = FEED_DEFAULT_LIMIT, before: int = None, since: int = None,
                     etype: str = None, db_path: Path = None) -> dict:
    """Newest-first page of stored events (local and those received via /p2p/sync).
    Ordered by row id (arrival order on this node), so the cursor is stable while new events arrive.
    Next page: ?before=<next_before>. Poll for new events: ?since=<latest_id>."""
    limit = max(1, min(int(limit), FEED_MAX_LIMIT))
    db_path = db_path or (Path.cwd() / "continuity_events.db")
    base = {"status": "OK", "node_id": STATE.node_id, "mesh_id": STATE.mesh_id, "version": VERSION,
            "limit": limit, "events": [], "count": 0, "has_more": False, "next_before": None, "latest_id": 0}
    if not db_path.exists():
        return base
    where, args = [], []
    if before is not None:
        where.append("id < ?"); args.append(before)
    if since is not None:
        where.append("id > ?"); args.append(since)
    if etype:
        where.append("action = ?"); args.append(etype)
    sql = ("SELECT id, event_id, action, author_pubkey, previous_hash, timestamp, payload_json, signature, ts_ms "
           "FROM events" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id DESC LIMIT ?")
    conn = sqlite3.connect(str(db_path))
    try:
        c = conn.cursor()
        c.execute(sql, (*args, limit + 1))
        rows = c.fetchall()
        c.execute("SELECT COALESCE(MAX(id), 0) FROM events;")
        latest_id = c.fetchone()[0]
    finally:
        conn.close()
    has_more = len(rows) > limit
    rows = rows[:limit]
    events = [_row_to_feed_event(r) for r in rows]
    base.update(events=events, count=len(events), has_more=has_more, latest_id=latest_id,
                next_before=(events[-1]["id"] if has_more and events else None))
    return base

# --- Bug reports (v8.9.0): POST /api/bugs/report, GET /api/bugs/list -----------------------------
BUG_REPORT_ACTION = "bug_report"
BUG_REPORT_MAX_BYTES = 8 * 1024
BUG_REPORT_SCHEMA = 1
# field -> max length (characters). Only these keys are accepted; "what_happened" is required.
BUG_REPORT_FIELDS = {"what_happened": 4000, "title": 200, "app": 64, "app_version": 32, "device": 120,
                     "android_version": 32, "network": 64, "steps": 4000, "expected": 2000}
BUG_REPORT_REQUIRED = ("what_happened",)
_BUG_LIST_ARGS = {"limit"}

def validate_bug_report(data) -> dict:
    """The stored payload for a bug report body, or ValueError. Strings only, trimmed, length-capped;
    unknown keys are rejected so nothing unexpected (tokens, seeds, message contents) is stored."""
    if not isinstance(data, dict):
        raise ValueError("body must be a JSON object")
    unknown = set(data) - set(BUG_REPORT_FIELDS)
    if unknown:
        raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")
    clean = {}
    for key, max_len in BUG_REPORT_FIELDS.items():
        if key not in data or data[key] is None:
            continue
        val = data[key]
        if not isinstance(val, str):
            raise ValueError(f"'{key}' must be a string")
        val = "".join(ch for ch in val if ch in "\n\t" or ch >= " ").strip()
        if len(val) > max_len:
            raise ValueError(f"'{key}' is longer than {max_len} characters")
        if val:
            clean[key] = val
    for key in BUG_REPORT_REQUIRED:
        if not clean.get(key):
            raise ValueError(f"'{key}' is required")
    return clean

def store_bug_report(data, via: str = "loopback") -> tuple:
    """Validates and appends a bug report as a normal node-signed chain event (the same
    process_and_store_event path as a local /api/events/append). Not relayed to peers on arrival."""
    try:
        payload = validate_bug_report(data)
    except ValueError as e:
        return {"status": "ERROR", "message": str(e)}, 400
    payload["schema"] = BUG_REPORT_SCHEMA
    payload["received_via"] = via
    resp, status = process_and_store_event({"action": BUG_REPORT_ACTION, "payload": payload},
                                           origin_peer=None, relay=False)
    if status == 200:
        resp = {"status": "SUCCESS", "event_id": resp.get("event_id"),
                **({"result": resp["result"]} if resp.get("result") else {})}
    return resp, status

def parse_bug_list_query(query: str) -> int:
    params = urllib.parse.parse_qs(query or "", keep_blank_values=True)
    unknown = set(params) - _BUG_LIST_ARGS
    if unknown:
        raise ValueError(f"unknown parameter(s): {', '.join(sorted(unknown))}")
    limit = _feed_int(params, "limit")
    return FEED_DEFAULT_LIMIT if limit is None else max(1, min(limit, FEED_MAX_LIMIT))

def list_bug_reports(limit: int = FEED_DEFAULT_LIMIT, db_path: Path = None) -> dict:
    page = list_feed_events(limit, etype=BUG_REPORT_ACTION, db_path=db_path)
    reports = [{"id": e["id"], "event_id": e["event_id"], "ts_ms": e["ts_ms"], "verified": e["verified"],
                "author_pubkey": e["author_pubkey"], "report": e["payload"]} for e in page["events"]]
    return {"status": "OK", "node_id": page["node_id"], "version": VERSION, "limit": page["limit"],
            "count": len(reports), "has_more": page["has_more"], "reports": reports}

# --- Catch-up sync (v8.8.0): negentropy range-based set reconciliation ---------------------------

def _db_path() -> Path:
    return Path.cwd() / "continuity_events.db"

def reconcile_item_ts(timestamp, ts_ms) -> int:
    """Negentropy timestamp for an event: whole seconds of the signed time (see omni_negentropy)."""
    if ts_ms is not None:
        return max(0, int(ts_ms) // 1000)
    return max(0, int(float(timestamp)))

def load_reconcile_items(db_path: Path = None) -> list:
    """(timestamp_s, 32-byte id) for every signed event whose id is a content hash. The unsigned
    per-node genesis row and malformed ids are left out: they can never verify on another node."""
    db_path = db_path or _db_path()
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute("SELECT event_id, timestamp, ts_ms FROM events "
                            "WHERE signature IS NOT NULL AND signature != '';").fetchall()
    finally:
        conn.close()
    items = []
    for event_id, timestamp, ts_ms in rows:
        if isinstance(event_id, str) and _EVENT_ID_RE.fullmatch(event_id):
            items.append((reconcile_item_ts(timestamp, ts_ms), bytes.fromhex(event_id[2:])))
    return items

def load_event_envelopes(event_ids, db_path: Path = None) -> list:
    """Stored events as /p2p/sync envelopes (exactly the signed time field), in the order given.
    Served as stored: the RECEIVER re-verifies everything, so nothing here is trusted."""
    db_path = db_path or _db_path()
    wanted = [e for e in event_ids if isinstance(e, str) and _EVENT_ID_RE.fullmatch(e)]
    if not wanted or not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    found = {}
    try:
        for i in range(0, len(wanted), 500):
            chunk = wanted[i:i + 500]
            q = ("SELECT event_id, action, author_pubkey, previous_hash, timestamp, payload_json, signature, ts_ms "
                 "FROM events WHERE event_id IN (%s);" % ",".join("?" * len(chunk)))
            for row in conn.execute(q, chunk):
                found[row[0]] = row
    finally:
        conn.close()
    out = []
    for e in wanted:
        row = found.get(e)
        if not row or not row[6]:
            continue
        event_id, action, author, prev_hash, timestamp, payload_json, signature, ts_ms = row
        try:
            payload = json.loads(payload_json or "{}")
        except ValueError:
            payload = {}
        time_fields = {"ts": int(ts_ms)} if ts_ms is not None else {"timestamp": timestamp}
        out.append({"event_id": event_id, "action": action, "author_pubkey": author,
                    "previous_hash": prev_hash, **time_fields, "payload": payload, "signature": signature})
    return out

def catchup_peers() -> list:
    """(host, port) pairs to reconcile with: OMNI_SYNC_PEERS plus fresh same-mesh discovery peers."""
    peers = list(STATE.sync_peers)
    now = time.time()
    with STATE.lock:
        found = [(p["ip"], int(p.get("port", P2P_SYNC_PORT))) for p in STATE.active_peers.values()
                 if now - p["last_seen"] < 15.0]
    for host, port in found:
        if host in (LOCAL_IP, "127.0.0.1"):
            continue
        if (host, port) not in peers:
            peers.append((host, port))
    return peers

def _resolve(host: str) -> set:
    try:
        return {ai[4][0] for ai in socket.getaddrinfo(host, None)}
    except Exception:
        return set()

def catchup_peer_allowed(ip: str) -> bool:
    """Who may call /p2p/reconcile and /p2p/events: loopback, a same-mesh peer this node discovered,
    or a host listed in OMNI_SYNC_PEERS. That is the set relay_event_to_peers already pushes every
    new event to, so catch-up serves nothing to anyone who wouldn't get it from live relay anyway."""
    if _is_loopback(ip):
        return True
    with STATE.lock:
        p = STATE.active_peers.get(ip)
        if p and time.time() - p["last_seen"] < 15.0:
            return True
    for host, _ in STATE.sync_peers:
        if ip == host or ip in _resolve(host):
            return True
    return False

def _peer_post(host: str, port: int, path: str, obj: dict, timeout: float = 10.0) -> tuple:
    body = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(f"http://{host}:{port}{path}", data=body, method="POST",
                                 headers={"Content-Type": "application/json", MESH_HEADER: STATE.mesh_id})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw), len(body) + len(raw)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw), len(body) + len(raw)
        except ValueError:
            return e.code, {}, len(body) + len(raw)

def reconcile_with_peer(host: str, port: int) -> dict:
    """Client side of one catch-up: reconcile, pull what we lack (verified), push what they lack."""
    t0 = time.time()
    stats = {"peer": f"{host}:{port}", "rounds": 0, "bytes": 0, "need": 0, "have": 0, "stored": 0,
             "already": 0, "rejected": 0, "missing": 0, "pushed": 0, "push_failed": 0, "error": None}
    try:
        ne = neg.Negentropy(neg.Storage(load_reconcile_items()))
        msg = ne.initiate()
        have, need = [], []
        while msg is not None:
            stats["rounds"] += 1
            if stats["rounds"] > RECONCILE_MAX_ROUNDS:
                raise RuntimeError("reconcile did not converge")
            code, resp, n = _peer_post(host, port, "/p2p/reconcile", {"negentropy": msg.hex()})
            stats["bytes"] += n
            if code != 200 or not isinstance(resp.get("negentropy"), str):
                raise RuntimeError(f"/p2p/reconcile answered {code}: {resp.get('message', '')}"[:200])
            msg, h, nd = ne.reconcile(bytes.fromhex(resp["negentropy"]))
            have += h
            need += nd
        need_ids = ["0x" + i.hex() for i in need]
        have_ids = ["0x" + i.hex() for i in have]
        stats["need"], stats["have"] = len(need_ids), len(have_ids)

        # Pull: fetch only the missing events, then verify each exactly like /p2p/sync does.
        pending = list(need_ids)
        while pending:
            batch, pending = pending[:FETCH_BATCH], pending[FETCH_BATCH:]
            code, resp, n = _peer_post(host, port, "/p2p/events", {"ids": batch}, timeout=30.0)
            stats["bytes"] += n
            if code != 200 or not isinstance(resp.get("events"), list):
                raise RuntimeError(f"/p2p/events answered {code}: {resp.get('message', '')}"[:200])
            asked = set(batch)
            got = set()
            for env in resp["events"]:
                eid = env.get("event_id") if isinstance(env, dict) else None
                if eid not in asked or eid in got:
                    stats["rejected"] += 1      # unrequested or duplicate: never stored
                    continue
                got.add(eid)
                result, status = process_and_store_event(env, origin_peer=host, relay=False)
                if status != 200:
                    stats["rejected"] += 1
                    print(f"[!] Catch-up from {host}:{port}: rejected {eid[:18]}... ({status}: {result.get('message', '')[:80]})", flush=True)
                elif result.get("result") == "ALREADY_EXISTS":
                    stats["already"] += 1
                else:
                    stats["stored"] += 1
            rest = [e for e in batch if e not in got]
            if resp.get("truncated") and rest and len(got) > 0:
                pending = rest + pending     # response hit the size cap: ask again for the rest
            else:
                stats["missing"] += len(rest)

        # Push: send what the peer lacks through its normal /p2p/sync (it verifies them itself).
        if os.environ.get(CATCHUP_PUSH_ENV, "1").strip().lower() not in ("0", "false", "no"):
            for env in load_event_envelopes(have_ids):
                code, _, n = _peer_post(host, port, "/p2p/sync", env)
                stats["bytes"] += n
                if code == 200:
                    stats["pushed"] += 1
                else:
                    stats["push_failed"] += 1
    except Exception as e:
        stats["error"] = str(e)[:200]
    stats["duration_ms"] = int((time.time() - t0) * 1000)
    return stats

def run_catchup(wait: bool = False) -> dict:
    """One catch-up pass over every known peer. Returns {"peers": [stats...]} (or skipped)."""
    if not STATE.catchup_lock.acquire(blocking=wait, timeout=60 if wait else -1):
        return {"status": "SKIPPED", "message": "a catch-up run is already in progress"}
    try:
        results = [reconcile_with_peer(h, p) for h, p in catchup_peers()]
        summary = {"status": "OK", "at": int(time.time()), "peers": results}
        STATE.last_catchup = summary
        for r in results:
            if r["error"] or r["need"] or r["have"]:
                print(f"[✓] Catch-up {r['peer']}: rounds={r['rounds']} need={r['need']} stored={r['stored']} "
                      f"rejected={r['rejected']} pushed={r['pushed']} error={r['error']}", flush=True)
        return summary
    finally:
        STATE.catchup_lock.release()

def catchup_loop():
    """Startup run (the 'reconnect' case), then whenever a new peer appears or the interval passes."""
    time.sleep(_env_float(CATCHUP_STARTUP_DELAY_ENV, 5.0))
    interval = _env_float(CATCHUP_INTERVAL_ENV, 60.0)
    while True:
        try:
            run_catchup()
        except Exception as e:
            print(f"[!] Catch-up failed: {e}", flush=True)
        STATE.catchup_wake.clear()
        STATE.catchup_wake.wait(interval if interval > 0 else None)
        time.sleep(1.0)   # let a burst of beacons settle

def answer_reconcile(data: dict) -> tuple:
    """Server side of /p2p/reconcile: stateless, one negentropy message in, one out."""
    msg_hex = data.get("negentropy") if isinstance(data, dict) else None
    if not isinstance(msg_hex, str):
        return {"status": "ERROR", "message": "expected {\"negentropy\": \"<hex message>\"}"}, 400
    try:
        out, _, _ = neg.Negentropy(neg.Storage(load_reconcile_items())).reconcile(bytes.fromhex(msg_hex))
    except ValueError as e:
        return {"status": "ERROR", "message": f"bad negentropy message: {e}"}, 400
    return {"status": "OK", "negentropy": out.hex()}, 200

def answer_events(data: dict) -> tuple:
    """Server side of /p2p/events: the stored envelopes for the requested ids (max FETCH_BATCH)."""
    ids = data.get("ids") if isinstance(data, dict) else None
    if not isinstance(ids, list) or len(ids) > FETCH_BATCH:
        return {"status": "ERROR", "message": f"expected {{\"ids\": [...]}} with at most {FETCH_BATCH} ids"}, 400
    events, size, truncated = [], 0, False
    for env in load_event_envelopes(ids):
        n = len(json.dumps(env))
        if events and size + n > FETCH_MAX_RESPONSE:
            truncated = True
            break
        events.append(env)
        size += n
    return {"status": "OK", "events": events, "truncated": truncated}, 200

def _is_loopback(ip: str) -> bool:
    return ip in ("127.0.0.1", "::1", "::ffff:127.0.0.1") or ip.startswith("127.")

def remote_gate(handler, method: str, path: str) -> bool:
    """True if the request may proceed. Loopback: always (unchanged behavior). Non-loopback: only
    with remote hub enabled, an allowed path and a valid bearer token; otherwise sends 403/401."""
    if _is_loopback(handler.client_address[0]):
        return True
    allowed = REMOTE_POST_PATHS if method == "POST" else REMOTE_GET_PATHS
    if not HUB_REMOTE or STATE.hub_token is None or path not in allowed:
        _deny(handler, 403, "loopback only")
        return False
    if not check_bearer(handler.headers.get("Authorization"), STATE.hub_token):
        _deny(handler, 401, "missing or invalid bearer token")
        return False
    return True

def _deny(handler, code: int, message: str):
    try:  # drain a small body so the client reads the answer instead of a reset
        n = min(int(handler.headers.get("Content-Length", 0) or 0), 65536)
        if n > 0:
            handler.rfile.read(n)
    except Exception:
        pass
    body = json.dumps({"status": "ERROR", "message": message}).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    if code == 401:
        handler.send_header("WWW-Authenticate", 'Bearer realm="omni-hub"')
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    try:
        handler.wfile.write(body)
    except Exception:
        pass


class TelemetryHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        if not remote_gate(self, "GET", self.path.partition("?")[0]):
            return
        if self.path == "/api/v1/telemetry/node-health":
            with STATE.lock:
                now = time.time()
                STATE.active_peers = {k: v for k, v in STATE.active_peers.items() if now - v["last_seen"] < 15.0}
                active_count = len(STATE.active_peers)
                peer_ips = list(STATE.active_peers.keys())
                uptime = round(now - STATE.start_time, 1)

            resp_data = {
                "status": "ONLINE",
                "version": VERSION,
                "node_id": STATE.node_id,
                "mesh_id": STATE.mesh_id,
                "local_ip": LOCAL_IP,
                "p2p_sync_port": P2P_SYNC_PORT,
                "active_peers": active_count,
                "peer_ips": peer_ips,
                "uptime_seconds": uptime,
                "catchup": STATE.last_catchup,
            }
            body = json.dumps(resp_data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/omnimind/telemetry":
            with STATE.lock:
                fresh = STATE.omnimind_telemetry is not None and time.time() - STATE.omnimind_received_at < OMNIMIND_STALE_SECONDS
                payload = dict(STATE.omnimind_telemetry) if fresh else None
            if not payload:
                self.send_error(404, "No live OmniMind agent")
                return
            payload["age_seconds"] = round(time.time() - STATE.omnimind_received_at, 1)
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            try:
                self.wfile.write(body)
            except Exception:
                pass
        else:
            self.send_error(404, "Endpoint Not Found")

    def do_POST(self):
        # Loopback-only cache for the decoupled OmniMind agent (omnimind_agent_telemetry_engine.py).
        if not remote_gate(self, "POST", self.path):
            return
        if self.path != "/api/omnimind/telemetry":
            self.send_error(404, "Endpoint Not Found")
            return
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len <= 0 or content_len > OMNIMIND_MAX_PAYLOAD:
            self.send_error(413, "Telemetry payload missing or too large (max 64KB)")
            return
        try:
            data = json.loads(self.rfile.read(content_len).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("payload must be a JSON object")
        except Exception as e:
            self.send_error(400, f"Bad Request: {e}")
            return
        with STATE.lock:
            STATE.omnimind_telemetry = data
            STATE.omnimind_received_at = time.time()
        body = b'{"status":"CACHED"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

class ContinuityIPCHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def _send_json(self, status_code: int, obj: dict):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_bug_report(self):
        try:
            content_len = int(self.headers.get("Content-Length", "") or -1)
        except ValueError:
            content_len = -1
        if content_len < 0:
            _deny(self, 411, "Content-Length required")
            return
        if content_len > BUG_REPORT_MAX_BYTES:
            _deny(self, 413, f"bug report too large (max {BUG_REPORT_MAX_BYTES} bytes)")
            return
        try:
            data = json.loads(self.rfile.read(content_len).decode("utf-8") if content_len else "")
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, {"status": "ERROR", "message": "body must be valid UTF-8 JSON"})
            return
        via = "loopback" if _is_loopback(self.client_address[0]) else "remote_hub"
        try:
            resp, status = store_bug_report(data, via=via)
        except Exception as e:
            resp, status = {"status": "ERROR", "message": f"could not store bug report: {e}"}, 500
        self._send_json(status, resp)

    def do_GET(self):
        path, _, query = self.path.partition("?")
        # Loopback: open as before. Non-loopback: remote hub on + bearer token, else 403/401.
        if not remote_gate(self, "GET", path):
            return
        if path == "/api/events/feed":
            try:
                q = parse_feed_query(query)
            except ValueError as e:
                self._send_json(400, {"status": "ERROR", "message": str(e)})
                return
            try:
                resp = list_feed_events(q["limit"], q["before"], q["since"], q["type"])
            except Exception as e:
                self._send_json(500, {"status": "ERROR", "message": f"feed read failed: {e}"})
                return
            self._send_json(200, resp)
            return
        if path == "/api/bugs/list":
            # Loopback only: not in REMOTE_GET_PATHS, so remote_gate already refused other callers.
            try:
                limit = parse_bug_list_query(query)
            except ValueError as e:
                self._send_json(400, {"status": "ERROR", "message": str(e)})
                return
            try:
                self._send_json(200, list_bug_reports(limit))
            except Exception as e:
                self._send_json(500, {"status": "ERROR", "message": f"bug list read failed: {e}"})
            return
        if self.path in ["/api/events/stats", "/api/events/list"]:
            db_path = Path.cwd() / "continuity_events.db"
            count = 0
            last_hash = "0x" + "0" * 64
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*) FROM events;")
                    count = c.fetchone()[0]
                    c.execute("SELECT event_id FROM events ORDER BY id DESC LIMIT 1;")
                    row = c.fetchone()
                    if row and row[0]:
                        last_hash = row[0]
                    conn.close()
                except Exception:
                    pass

            resp_data = {
                "status": "OK",
                "db_mode": "WAL",
                "total_events": count,
                "last_merkle_hash": last_hash,
                "node_id": STATE.node_id
            }
            body = json.dumps(resp_data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except Exception:
                pass
        else:
            self.send_error(404, "Endpoint Not Found")

    def do_POST(self):
        if not remote_gate(self, "POST", self.path):
            return
        if self.path == "/api/sync/catchup":
            # Loopback-only (never in REMOTE_POST_PATHS): run a catch-up pass now and report it.
            try:
                n = min(int(self.headers.get("Content-Length", 0) or 0), 65536)
                if n > 0:
                    self.rfile.read(n)
            except ValueError:
                pass
            self._send_json(200, run_catchup(wait=True))
            return
        if self.path == "/api/bugs/report":
            self._handle_bug_report()
            return
        if self.path == "/api/events/append":
            content_len = int(self.headers.get("Content-Length", 0))
            if content_len > MAX_PAYLOAD_SIZE:
                self.send_error(413, "Payload Too Large (Max 5MB)")
                return

            post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
            try:
                data = json.loads(post_body)
                if _is_loopback(self.client_address[0]):
                    resp_data, status_code = process_and_store_event(data, origin_peer=None)
                else:
                    # Remote app (token already checked): store the event the PHONE signed, verified
                    # exactly like a peer event. The node key never signs for a remote app.
                    try:
                        event = unwrap_remote_event(data)
                    except ValueError as e:
                        resp_data, status_code = {"status": "ERROR", "message": str(e)}, 400
                    else:
                        resp_data, status_code = process_and_store_event(event, origin_peer=self.client_address[0])
                body = json.dumps(resp_data).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except Exception:
                    pass
            except Exception as e:
                self.send_error(400, f"Bad Request: {e}")
        else:
            self.send_error(404, "Endpoint Not Found")

class P2PSyncHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def reject_mesh(self, their_mesh):
        """403 before any parsing/verification/storage. The body is drained unread (capped) so the
        client gets the response instead of a connection reset."""
        log_mesh_reject_once(self.client_address[0], their_mesh, "P2P sync")
        try:
            remaining = min(int(self.headers.get("Content-Length", 0) or 0), MAX_PAYLOAD_SIZE)
        except ValueError:
            remaining = 0
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, 65536))
            if not chunk:
                break
            remaining -= len(chunk)
        body = json.dumps({"status": "ERROR",
                           "message": f"Mesh mismatch or missing {MESH_HEADER} header"}).encode("utf-8")
        self.send_response(403)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_reply(self, status_code: int, obj: dict):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def do_POST(self):
        if self.path in ("/p2p/reconcile", "/p2p/events"):
            # Catch-up sync (v8.8.0). Mesh first (403, unread), then only loopback / known peers (403):
            # the same hosts live relay already pushes every event to. Nothing here writes to the DB.
            their_mesh = self.headers.get(MESH_HEADER)
            if their_mesh is None or their_mesh.strip() != STATE.mesh_id:
                self.reject_mesh(their_mesh)
                return
            if not catchup_peer_allowed(self.client_address[0]):
                _deny(self, 403, "catch-up is only served to known peers on this mesh")
                return
            try:
                content_len = int(self.headers.get("Content-Length", 0) or 0)
            except ValueError:
                content_len = -1
            if content_len <= 0 or content_len > MAX_PAYLOAD_SIZE:
                _deny(self, 413, "body missing or too large (max 5MB)")
                return
            try:
                data = json.loads(self.rfile.read(content_len).decode("utf-8"))
            except Exception as e:
                self._json_reply(400, {"status": "ERROR", "message": f"Bad Request: {e}"})
                return
            handler = answer_reconcile if self.path == "/p2p/reconcile" else answer_events
            try:
                resp_data, status_code = handler(data)
            except Exception as e:
                resp_data, status_code = {"status": "ERROR", "message": f"catch-up failed: {e}"}, 500
            self._json_reply(status_code, resp_data)
            return
        if self.path == "/p2p/sync":
            their_mesh = self.headers.get(MESH_HEADER)
            if their_mesh is None or their_mesh.strip() != STATE.mesh_id:
                self.reject_mesh(their_mesh)
                return
            content_len = int(self.headers.get("Content-Length", 0))
            if content_len > MAX_PAYLOAD_SIZE:
                self.send_error(413, "Payload Too Large (Max 5MB)")
                return

            post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
            origin_ip = self.client_address[0]

            try:
                data = json.loads(post_body)
                resp_data, status_code = process_and_store_event(data, origin_peer=origin_ip)
                body = json.dumps(resp_data).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except Exception:
                    pass
            except Exception as e:
                self.send_error(400, f"Bad Request: {e}")
        else:
            self.send_error(404, "Endpoint Not Found")

def main():
    force_utf8_console()
    db_file = init_db()
    print("==================================================================")
    print(f"OMNIVERSE LIVE LOCAL DAEMON ENGINE [v{VERSION} - Hardened Spine]")
    print("==================================================================")
    print(f"[✓] Node ID Initialized:  {STATE.node_id}")
    print(f"[✓] Mesh ID ({MESH_ID_ENV}):  {STATE.mesh_id}  (peers on other meshes are ignored / 403)")
    print(f"[✓] Local Subnet IP:      {LOCAL_IP}")
    print(f"[✓] SQLite WAL Event DB:  {db_file}")
    print(f"[✓] Telemetry API Bound:  http://{IPC_HOST}:{TELEMETRY_PORT}/api/v1/telemetry/node-health")
    print(f"[✓] Local IPC Event API:  http://{IPC_HOST}:{CONTINUITY_IPC_PORT}/api/events/append")
    print(f"[✓] Local IPC Event Feed: http://{IPC_HOST}:{CONTINUITY_IPC_PORT}/api/events/feed?limit=50")
    print(f"[✓] Bug Reports:          POST http://{IPC_HOST}:{CONTINUITY_IPC_PORT}/api/bugs/report  (list: GET /api/bugs/list)")
    print(f"[✓] P2P Sync Server Bound: http://{P2P_HOST}:{P2P_SYNC_PORT}/p2p/sync")
    print(f"[✓] UDP Subnet Discovery: Listening on port {UDP_DISCOVERY_PORT}...")
    if STATE.trusted_keys is None:
        print(f"[!] WARNING: {TRUSTED_KEYS_ENV} not set: ANY validly signed peer event is accepted.")
    else:
        print(f"[✓] Trusted-keys allowlist: {len(STATE.trusted_keys)} key(s); others get 403")
    if HUB_REMOTE:
        hosts = hub_listen_hosts()
        addrs = [HUB_BIND] if HUB_BIND != "0.0.0.0" else [a for a in (tailscale_ip(), LOCAL_IP) if a and a != "127.0.0.1"]
        print(f"[✓] REMOTE HUB ON ({HUB_REMOTE_ENV}=1): app endpoints listen on {', '.join(hosts)}")
        for a in dict.fromkeys(addrs):
            tag = "  (Tailscale)" if a.startswith("100.") else ""
            print(f"    -> http://{a}:{CONTINUITY_IPC_PORT}/api/events/feed  +  http://{a}:{TELEMETRY_PORT}/api/v1/telemetry/node-health{tag}")
        print(f"[✓] Remote hub token ({hub_token_path()}): {STATE.hub_token}")
        print("    Remote requests need 'Authorization: Bearer <token>'; remote posts must be signed by the phone.")
    else:
        print(f"[✓] Remote hub: off (set {HUB_REMOTE_ENV}=1 and {HUB_BIND_ENV}=<ip> to serve another phone)")
    peers_txt = ", ".join(f"{h}:{p}" for h, p in STATE.sync_peers) or "none (discovery only)"
    interval = _env_float(CATCHUP_INTERVAL_ENV, 60.0)
    print(f"[✓] Catch-up sync (negentropy v1): /p2p/reconcile + /p2p/events; static peers ({SYNC_PEERS_ENV}): {peers_txt}; "
          f"every {int(interval)}s" if interval > 0 else "[✓] Catch-up sync: startup + new peers only (interval 0)")
    print(f"[✓] Event time format: {'legacy float timestamp' if LEGACY_FLOAT_TS else 'int-ms ts'} for events this node stamps")
    print("------------------------------------------------------------------", flush=True)  # show in daemon.log now

    t1 = threading.Thread(target=udp_discovery_broadcaster, daemon=True)
    t2 = threading.Thread(target=udp_discovery_listener, daemon=True)
    t3 = threading.Thread(target=catchup_loop, daemon=True)
    # Bind in the main thread so a bad OMNI_HUB_BIND fails loudly instead of in a dead thread.
    servers = []
    for host in hub_listen_hosts():
        servers.append(bind_server(host, TELEMETRY_PORT, TelemetryHandler))
        servers.append(bind_server(host, CONTINUITY_IPC_PORT, ContinuityIPCHandler))
    servers.append(bind_server(P2P_HOST, P2P_SYNC_PORT, P2PSyncHandler))

    t1.start()
    t2.start()
    for srv in servers:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    t3.start()   # after the servers are up, so peers can reconcile back with us

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[✓] Live daemon shut down cleanly.")
        sys.exit(0)

if __name__ == "__main__":
    main()
