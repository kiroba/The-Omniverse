#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE LIVE LOCAL DAEMON ENGINE [v8.16.0 - Hardened Mesh Spine]
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
Omni Credits TEST ledger (v8.10.0): closed-loop test credits (no cash value) stored as node-signed
"credit_entry" chain events; balances are replayed from those entries, never kept in a table. Each new
pubkey gets a one-time 1,000-credit welcome grant. GET :5000/api/credits/balance?pubkey=,
GET /api/credits/history?pubkey=&limit=, POST /api/credits/transfer, POST /api/credits/grant (admin).
All loopback only. Treasury fee: OMNI_TREASURY_FEE_BPS (default 0). See Admin/docs/CREDITS_LEDGER.md.
OmniCast signaling (v8.11.0): POST :5000/api/signal/send and GET /api/signal/poll are an in-memory
WebRTC signaling mailbox (offer/answer/ice/hangup/ring). Every message is Ed25519-signed by its sender,
ts within +/-120 s, max 16 KB, 64 queued per recipient, expires after 60 s, removed on delivery, never
stored in the event log or logged. Polls are signed by the recipient. GET /api/signal/ice-config returns
STUN plus time-limited TURN REST credentials (OMNI_TURN_URLS + OMNI_TURN_SECRET). Same gate as the
other hub endpoints (loopback, or bearer token in remote hub mode). See Admin/docs/OMNICAST_SIGNALING.md.
Telemetry summary (v8.12.0): GET :5000/api/telemetry/summary returns aggregate counts only (protocols,
security, finance, users, services) for the Mesh Monitor app. In-memory counters reset on restart; no
message contents, no keys beyond 12-char pubkey prefixes, no IPs. Same gate as the other hub endpoints.
See Admin/docs/TELEMETRY_SUMMARY.md.
Request bodies (v8.12.1): every :5000 POST accepts a Content-Length body or a "Transfer-Encoding: chunked"
body (what Dart's HttpClient sends when contentLength isn't set). Before this, a chunked append was read
as "{}" and stored as an EMPTY "USER_ACTION" event with status SUCCESS: every KickBack post ever sent to
a daemon arrived that way. /api/events/append now answers 400 for an empty body. See
Admin/docs/REQUEST_BODIES.md.
Profiles, contact cards, invites (v8.13.0): POST :5000/api/profile/update stores a profile event signed
by the PERSON's key (author = their pubkey, the hub only verifies; per-key rate limit); GET
/api/profile?pubkey= and /api/profile/list read the latest one per key. POST /api/contacts/verify
checks a signed contact card / "omni://contact?c=" QR; GET /api/hub/card is a node-signed "join this
hub" card (no token in it); POST /api/invites/create + GET /api/invites/redeem?code= map a short code
to a contact card for up to 7 days. All allowed in remote hub mode with the bearer token. See
Admin/docs/PROFILES_AND_CONTACTS.md.
Comments + reactions (v8.14.0): POST :5000/api/social/comment and /api/social/react take person-signed
events keyed to a post id (the app_event_id KickBack shows); GET /api/social/thread?post_id= returns the
comments and reaction counts, GET /api/social/counts?post_ids=a,b returns per-post counts for a feed.
Reactions toggle (latest signed ts per person+post+reaction wins). Remote hub allowed with the bearer
token. See Admin/docs/SOCIAL.md.
Signed credit transfers (v8.15.0): POST :5000/api/credits/send takes a transfer signed by the "from"
key (kinds transfer/purchase/tip, optional ref such as a post id, unique nonce, ts within 10 min). The
signature, nonce and ts are stored inside the ledger entry and re-verified on every replay; a reused
nonce is refused (identical retry -> ALREADY_APPLIED), so a signed transfer can't be spent twice on
this node. send/balance/history are allowed in remote hub mode; OMNI_CREDITS_REQUIRE_SIGNED=1 turns
off the unsigned loopback /api/credits/transfer. Still TEST credits, still one ledger per node. See
Admin/docs/CREDITS_LEDGER.md.
App check-ins (v8.16.0): POST :5000/api/telemetry/app-checkin takes a check-in signed by the app's key
(app, version, platform, consent version/accepted, crash count + exception type since the last one).
The hub keeps a salted key hash, never the key, IP or crash text; aggregates appear in
/api/telemetry/summary (users.app_checkins, services.app_crashes). Remote hub allowed. See
Admin/docs/APP_TELEMETRY.md.
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

VERSION = "8.16.0"
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
REMOTE_GET_PATHS = {"/api/events/feed", "/api/events/stats", "/api/events/list", "/api/v1/telemetry/node-health",
                    "/api/signal/poll", "/api/signal/ice-config", "/api/telemetry/summary",
                    "/api/profile", "/api/profile/list", "/api/hub/card", "/api/invites/redeem",
                    "/api/social/thread", "/api/social/counts", "/api/credits/balance", "/api/credits/history"}
REMOTE_POST_PATHS = {"/api/events/append", "/api/bugs/report", "/api/signal/send",
                     "/api/profile/update", "/api/contacts/verify", "/api/invites/create",
                     "/api/social/comment", "/api/social/react", "/api/credits/send",
                     "/api/telemetry/app-checkin"}
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

class TelemetryCounters:
    """In-memory, since-start counters and last-seen times for GET /api/telemetry/summary (v8.12.0).
    Numbers only: nothing here holds message contents, keys or addresses. Reset on restart."""

    def __init__(self):
        self.lock = threading.Lock()
        self.counts = {}
        self.last = {}     # name -> unix seconds of the last occurrence

    def inc(self, name: str, n: int = 1, touch: bool = True):
        with self.lock:
            self.counts[name] = self.counts.get(name, 0) + n
            if touch:
                self.last[name] = time.time()

    def touch(self, name: str):
        with self.lock:
            self.last[name] = time.time()

    def snapshot(self) -> tuple:
        with self.lock:
            return dict(self.counts), dict(self.last)

TELEMETRY = TelemetryCounters()

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
        self.udp_listener = "starting"         # "listening" / "bind failed: ..." (telemetry summary)

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
    """Stores one event (see _process_and_store_event) and counts the outcome for the telemetry summary.
    Local events are signed by this node; peer/remote events had their author signature verified."""
    resp, status = _process_and_store_event(data, origin_peer, relay)
    src = "local" if origin_peer is None else "peer"
    if status == 200:
        TELEMETRY.inc("events_duplicate" if resp.get("result") == "ALREADY_EXISTS" else f"events_stored_{src}")
    elif status == 401:
        TELEMETRY.inc("events_rejected_signature")
    elif status == 403:
        TELEMETRY.inc("events_rejected_untrusted")
    else:
        TELEMETRY.inc("events_rejected_invalid")
    return resp, status

def _process_and_store_event(data: dict, origin_peer: str = None, relay: bool = True) -> tuple[dict, int]:
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
            TELEMETRY.inc("relay_ok")
        except Exception:
            TELEMETRY.inc("relay_failed")

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
            TELEMETRY.inc("beacons_sent")
        except Exception:
            TELEMETRY.inc("beacons_send_failed")
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
        TELEMETRY.inc("beacons_rejected_mesh")
        return False
    if not beacon_allowed(msg, peer_ip):
        TELEMETRY.inc("beacons_rejected_signature")
        return False
    TELEMETRY.inc("beacons_accepted")
    peer_port = int(msg.get("port", P2P_SYNC_PORT))
    with STATE.lock:
        old = STATE.active_peers.get(peer_ip)
        is_new = old is None or time.time() - old["last_seen"] >= 15.0   # new or back after a gap
        STATE.active_peers[peer_ip] = {"ip": peer_ip, "port": peer_port, "last_seen": time.time(),
                                       "node_id": str(msg.get("node_id", ""))[:64],
                                       "signed": "sig" in msg}
    if is_new:
        STATE.catchup_wake.set()   # (re)connected peer: reconcile with it soon
    return True

def udp_discovery_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if not IS_WINDOWS:   # on Windows this would let a second daemon share 9101
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(('0.0.0.0', UDP_DISCOVERY_PORT))
    except Exception as e:
        STATE.udp_listener = f"bind failed: {type(e).__name__}"
        return
    STATE.udp_listener = "listening"

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

# --- User-signed app events (v8.13.0): the phone's key is the author, the hub only verifies -----------
# Profiles (and, from v8.14.0, comments/reactions) are events signed by the PERSON's Ed25519 key
# (StargateIdentity on the phone), stored exactly as signed with author_pubkey = that key, and relayed /
# caught up like any peer event. The hub never signs on a person's behalf. Envelope = the same canonical
# event the app already signs for posts: {"action","author_pubkey","previous_hash","ts","payload",
# "signature"[,"event_id"]} (see Admin/docs/SIGNED_EVENTS.md). previous_hash is the author's own chain
# head (the hub doesn't enforce per-author continuity). See Admin/docs/PROFILES_AND_CONTACTS.md.
USER_EVENT_MAX_BYTES = 16 * 1024
USER_EVENT_FIELDS = {"event_id", "action", "author_pubkey", "previous_hash", "ts", "payload", "signature"}
_HEX_HASH_RE = re.compile(r"0x[0-9a-f]{64}")
_USER_SIG_RE = re.compile(r"[0-9a-f]{128}")
USER_RATE_WINDOW_S = 60.0
try:
    USER_RATE_MAX = max(1, int(os.environ.get("OMNI_USER_RATE_MAX", "30")))   # writes per author per minute
except ValueError:
    USER_RATE_MAX = 30
RESERVED_USER_ACTIONS = {}   # action -> endpoint; /api/events/append refuses these (filled below)


class SlidingWindowLimiter:
    """Per-key sliding-window rate limit (spec Module 1.2 tier 3: max publication rate per pubkey)."""

    def __init__(self, max_events: int, window_s: float, clock=time.monotonic):
        self.max, self.window, self.clock = max_events, window_s, clock
        self.hits = {}
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self.clock()
        with self.lock:
            q = [t for t in self.hits.get(key, []) if now - t < self.window]
            if len(q) >= self.max:
                self.hits[key] = q
                return False
            q.append(now)
            self.hits[key] = q
            if len(self.hits) > 20_000:
                self.hits = {k: v for k, v in self.hits.items() if v and now - v[-1] < self.window}
            return True


USER_RATE = SlidingWindowLimiter(USER_RATE_MAX, USER_RATE_WINDOW_S)


def parse_user_event(data, validators: dict) -> dict:
    """The phone-signed event in a request body, schema-checked (not yet signature-checked).
    validators: action -> fn(payload) returning the payload or raising ValueError."""
    if not isinstance(data, dict):
        raise ValueError("body must be a JSON object (a signed event envelope)")
    unknown = set(data) - USER_EVENT_FIELDS
    if unknown:
        raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")
    action = data.get("action")
    if action not in validators:
        raise ValueError(f"'action' must be one of: {', '.join(sorted(validators))}")
    author = data.get("author_pubkey")
    if not isinstance(author, str) or not _PUBKEY_RE.fullmatch(author):
        raise ValueError("'author_pubkey' must be a 64-char lowercase hex Ed25519 public key")
    ts = data.get("ts")
    if not isinstance(ts, int) or isinstance(ts, bool) or ts < 0:
        raise ValueError("'ts' must be an integer (milliseconds since epoch)")
    prev = data.get("previous_hash")
    if not isinstance(prev, str) or not _HEX_HASH_RE.fullmatch(prev):
        raise ValueError("'previous_hash' must be 0x + 64 hex (the author's previous event id, or 0x00..00)")
    sig = data.get("signature")
    if not isinstance(sig, str) or not _USER_SIG_RE.fullmatch(sig):
        raise ValueError("'signature' must be a 128-char lowercase hex Ed25519 signature")
    if "event_id" in data and (not isinstance(data["event_id"], str) or not _HEX_HASH_RE.fullmatch(data["event_id"])):
        raise ValueError("'event_id' must be 0x + 64 hex")
    payload = validators[action](data.get("payload"))
    ev = {"action": action, "author_pubkey": author, "previous_hash": prev, "ts": ts,
          "payload": payload, "signature": sig}
    if "event_id" in data:
        ev["event_id"] = data["event_id"]
    return ev


def user_event_signature_ok(ev: dict) -> bool:
    try:
        return bool(verify_event({k: ev[k] for k in ("action", "author_pubkey", "previous_hash", "ts",
                                                     "payload", "signature")}))
    except Exception:
        return False


def store_user_event(data, validators: dict, via: str = "loopback") -> tuple:
    """Validate -> verify the author's signature -> per-author rate limit -> store as signed (relayed to
    peers like any peer event). Replays of a stored event answer ALREADY_EXISTS."""
    try:
        ev = parse_user_event(data, validators)
    except ValueError as e:
        return {"status": "ERROR", "message": str(e)}, 400
    if not user_event_signature_ok(ev):
        TELEMETRY.inc("user_events_rejected_signature")
        return {"status": "ERROR", "message": "bad signature: must be the author's Ed25519 signature over the "
                                              "canonical event (action, author_pubkey, payload, previous_hash, ts)"}, 401
    if not USER_RATE.allow(ev["author_pubkey"]):
        TELEMETRY.inc("user_events_rate_limited")
        return {"status": "ERROR", "message": f"rate limited: max {USER_RATE_MAX} writes per minute per key"}, 429
    resp, status = process_and_store_event(ev, origin_peer=f"app-{via}")
    if status == 200:
        TELEMETRY.inc(f"user_events_{ev['action']}")
        resp = dict(resp, author_pubkey=ev["author_pubkey"], action=ev["action"])
    return resp, status


def _query_args(query: str, allowed: set) -> dict:
    params = urllib.parse.parse_qs(query or "", keep_blank_values=True)
    unknown = set(params) - allowed
    if unknown:
        raise ValueError(f"unknown parameter(s): {', '.join(sorted(unknown))}")
    return params


def _user_rows(actions, where: str = "", args: tuple = (), db_path: Path = None) -> list:
    """Stored events of the given actions as dicts, oldest row first, each re-verified: the signature must
    check out and the author must not be this node (user events are signed by people, never the hub)."""
    db_path = db_path or _db_path()
    if not db_path.exists():
        return []
    marks = ",".join("?" for _ in actions)
    sql = ("SELECT id, event_id, action, author_pubkey, previous_hash, timestamp, payload_json, signature, ts_ms "
           f"FROM events WHERE action IN ({marks})" + (f" AND {where}" if where else "") + " ORDER BY id ASC")
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(sql, (*actions, *args)).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        e = _row_to_feed_event(r)
        if e["verified"] and "ts" in e and e["author_pubkey"] != STATE.node_id:
            out.append(e)
    return out


# --- Profiles: handle + display name signed by the person's key ------------------------------------
PROFILE_ACTION = "profile_update"
PROFILE_SCHEMA = 1
_HANDLE_RE = re.compile(r"[a-z0-9_]{3,20}")
PROFILE_TEXT_FIELDS = {"display_name": 48, "bio": 280, "avatar": 200}
_PROFILE_LIST_ARGS = {"limit", "q"}


def _clean_text(value, name: str, max_len: int, multiline: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"'{name}' must be a string")
    v = "".join(ch for ch in value if ch >= " " or (multiline and ch == "\n")).strip()
    if len(v) > max_len:
        raise ValueError(f"'{name}' is longer than {max_len} characters")
    return v


def validate_profile(p) -> dict:
    if not isinstance(p, dict):
        raise ValueError("payload must be an object")
    unknown = set(p) - {"schema", "handle", "omnicast"} - set(PROFILE_TEXT_FIELDS)
    if unknown:
        raise ValueError(f"unknown profile field(s): {', '.join(sorted(unknown))}")
    if p.get("schema") != PROFILE_SCHEMA:
        raise ValueError(f"'schema' must be {PROFILE_SCHEMA}")
    if not isinstance(p.get("handle"), str) or not _HANDLE_RE.fullmatch(p["handle"]):
        raise ValueError("'handle' must be 3-20 chars of a-z 0-9 _")
    for k, n in PROFILE_TEXT_FIELDS.items():
        if k in p and _clean_text(p[k], k, n, multiline=(k == "bio")) != p[k]:
            raise ValueError(f"'{k}' has control characters or surrounding spaces; send it trimmed")
    if "omnicast" in p and not isinstance(p["omnicast"], bool):
        raise ValueError("'omnicast' must be true or false (accepts OmniCast calls)")
    return p


def handle_display(handle: str, pubkey: str) -> str:
    """@handle.abcd: the 4-hex key suffix tells two people with the same handle apart. Handles are NOT
    unique (there is no global registry); the pubkey is the identity."""
    return f"@{handle}.{pubkey[:4]}"


def _profile_view(e: dict) -> dict:
    p = e["payload"]
    return {"pubkey": e["author_pubkey"], "handle": p["handle"], "handle_display": handle_display(p["handle"], e["author_pubkey"]),
            **{k: p[k] for k in ("display_name", "bio", "avatar", "omnicast") if k in p},
            "updated_ts_ms": e["ts"], "event_id": e["event_id"], "origin": e["origin"], "verified": True}


def latest_profiles(pubkey: str = None, db_path: Path = None) -> dict:
    """pubkey -> latest valid profile event (highest signed ts; ties by arrival)."""
    rows = _user_rows((PROFILE_ACTION,), "author_pubkey = ?" if pubkey else "", (pubkey,) if pubkey else (),
                      db_path)
    best = {}
    for e in rows:
        try:
            validate_profile(e["payload"])
        except ValueError:
            continue   # a peer can relay anything; invalid ones are ignored on read
        cur = best.get(e["author_pubkey"])
        if cur is None or e["ts"] >= cur["ts"]:
            best[e["author_pubkey"]] = e
    return best


def get_profile(query: str) -> tuple:
    try:
        params = _query_args(query, {"pubkey"})
        pk = credit_account((params.get("pubkey") or [""])[-1], allow_treasury=False)
    except ValueError as e:
        return {"status": "ERROR", "message": str(e)}, 400
    e = latest_profiles(pk).get(pk)
    if e is None:
        return {"status": "ERROR", "message": "no profile for that key on this hub", "pubkey": pk}, 404
    return {"status": "OK", "profile": _profile_view(e)}, 200


def list_profiles(query: str) -> tuple:
    try:
        params = _query_args(query, _PROFILE_LIST_ARGS)
        limit = _feed_int(params, "limit")
        q = (params.get("q") or [""])[-1].strip().lower().lstrip("@")
    except ValueError as e:
        return {"status": "ERROR", "message": str(e)}, 400
    limit = FEED_DEFAULT_LIMIT if limit is None else max(1, min(limit, FEED_MAX_LIMIT))
    views = [_profile_view(e) for e in latest_profiles().values()]
    if q:
        views = [v for v in views if v["handle"].startswith(q) or v["pubkey"].startswith(q)
                 or v.get("display_name", "").lower().startswith(q)]
    views.sort(key=lambda v: v["updated_ts_ms"], reverse=True)
    return {"status": "OK", "count": min(len(views), limit), "has_more": len(views) > limit,
            "profiles": views[:limit]}, 200


RESERVED_USER_ACTIONS[PROFILE_ACTION] = "/api/profile/update"

# --- Contact cards (QR), hub card, invite codes ---------------------------------------------------
# A contact card is a small JSON object the PERSON signs (domain-separated by "type"); a QR code holds
# "omni://contact?c=<base64url(card JSON)>". Contact lists themselves stay on the phone: the hub stores
# no social graph. Invite codes map a short code to a card for up to 7 days (SQLite side table, not the
# event log, not relayed).
CONTACT_CARD_TYPE = "omni.contact-card.v1"
HUB_CARD_TYPE = "omni.hub-card.v1"
CONTACT_CARD_FIELDS = {"type", "pubkey", "handle", "display_name", "hub", "ts", "sig"}
CONTACT_CARD_MAX_AGE_MS = 365 * 86_400_000
INVITE_TTL_DEFAULT_S = 24 * 3600
INVITE_TTL_MAX_S = 7 * 24 * 3600
INVITE_MAX_USES = 100
INVITE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"   # no 0/O/1/I/L
INVITE_CREATE_SKEW_MS = 600_000
_INVITE_CODE_RE = re.compile(r"[2-9A-HJKMNP-Z]{4}-?[2-9A-HJKMNP-Z]{4}")
INVITE_REDEEM_FAILS = SlidingWindowLimiter(20, 60.0)   # failed redeems per client per minute
INVITES_LOCK = threading.Lock()


def card_signing_bytes(card: dict) -> bytes:
    """Sorted-key compact JSON of every field except "sig", raw UTF-8 (same rule as OmniCast signaling)."""
    return json.dumps({k: v for k, v in card.items() if k != "sig"}, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _b64url_json(obj: dict) -> str:
    import base64
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_qr_payload(text: str, kind: str) -> dict:
    """'omni://<kind>?c=<base64url JSON>' -> the JSON object. Raises ValueError."""
    import base64
    prefix = f"omni://{kind}?c="
    if not isinstance(text, str) or not text.startswith(prefix) or len(text) > 4096:
        raise ValueError(f"QR text must start with {prefix}")
    b = text[len(prefix):]
    try:
        obj = json.loads(base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)).decode("utf-8"))
    except Exception:
        raise ValueError("QR payload is not base64url JSON")
    if not isinstance(obj, dict):
        raise ValueError("QR payload is not a JSON object")
    return obj


def verify_contact_card(card, now: int = None) -> dict:
    """The card if it is well-formed and signed by its own pubkey, else ValueError."""
    now = now_ms() if now is None else now
    if not isinstance(card, dict):
        raise ValueError("card must be a JSON object")
    unknown = set(card) - CONTACT_CARD_FIELDS
    if unknown:
        raise ValueError(f"unknown card field(s): {', '.join(sorted(unknown))}")
    if card.get("type") != CONTACT_CARD_TYPE:
        raise ValueError(f"'type' must be {CONTACT_CARD_TYPE}")
    pk = card.get("pubkey")
    if not isinstance(pk, str) or not _PUBKEY_RE.fullmatch(pk):
        raise ValueError("'pubkey' must be a 64-char lowercase hex Ed25519 public key")
    if not isinstance(card.get("handle"), str) or not _HANDLE_RE.fullmatch(card["handle"]):
        raise ValueError("'handle' must be 3-20 chars of a-z 0-9 _")
    if "display_name" in card:
        _clean_text(card["display_name"], "display_name", 48)
    if "hub" in card:
        hub = card["hub"]
        if (not isinstance(hub, dict) or set(hub) - {"host", "ipc_port"} or not isinstance(hub.get("host"), str)
                or not _PEER_HOST_RE.fullmatch(hub["host"])
                or not isinstance(hub.get("ipc_port", 5000), int) or not 0 < hub.get("ipc_port", 5000) < 65536):
            raise ValueError("'hub' must be {\"host\": <ip or name>, \"ipc_port\"?: <1-65535>}")
    ts = card.get("ts")
    if not isinstance(ts, int) or isinstance(ts, bool) or ts < 0:
        raise ValueError("'ts' must be an integer (milliseconds since epoch)")
    if ts > now + MAX_FUTURE_SKEW_S * 1000:
        raise ValueError("card 'ts' is in the future")
    if now - ts > CONTACT_CARD_MAX_AGE_MS:
        raise ValueError("card is older than a year; ask for a fresh one")
    sig = card.get("sig")
    if not isinstance(sig, str) or not _USER_SIG_RE.fullmatch(sig):
        raise ValueError("'sig' must be a 128-char lowercase hex Ed25519 signature")
    if not _ed25519_ok(pk, sig, card_signing_bytes(card)):
        raise ValueError("bad signature: the card must be signed by its own pubkey")
    return card


def contacts_verify(data) -> tuple:
    """Body: a contact card, or {"qr": "omni://contact?c=..."}."""
    try:
        if isinstance(data, dict) and set(data) == {"qr"}:
            data = decode_qr_payload(data["qr"], "contact")
        card = verify_contact_card(data)
    except ValueError as e:
        return {"status": "ERROR", "valid": False, "message": str(e)}, 400
    prof = latest_profiles(card["pubkey"]).get(card["pubkey"])
    return {"status": "OK", "valid": True, "card": card,
            "handle_display": handle_display(card["handle"], card["pubkey"]),
            "qr": "omni://contact?c=" + _b64url_json(card),
            "profile": _profile_view(prof) if prof else None}, 200


def hub_card() -> dict:
    """Node-signed card for a "join this hub" QR. Never carries the bearer token."""
    addrs = [h for h in hub_listen_hosts() if h not in ("0.0.0.0", "::")]
    ts_ip = tailscale_ip()
    if ts_ip and ts_ip not in addrs:
        addrs.append(ts_ip)
    card = {"type": HUB_CARD_TYPE, "node_id": STATE.node_id, "mesh_id": STATE.mesh_id, "version": VERSION,
            "ipc_port": CONTINUITY_IPC_PORT, "telemetry_port": TELEMETRY_PORT, "addresses": addrs,
            "remote_hub": bool(HUB_REMOTE), "ts": now_ms()}
    card["sig"] = STATE.signing_key.sign(card_signing_bytes(card)).hex()
    return {"status": "OK", "card": card, "qr": "omni://hub?c=" + _b64url_json(card),
            "note": "the bearer token is not in the card; copy ~/.omni/hub_token separately"}


def _invites_db():
    conn = sqlite3.connect(str(_db_path()), timeout=10.0)
    conn.execute("CREATE TABLE IF NOT EXISTS invites (code TEXT PRIMARY KEY, card_json TEXT NOT NULL, "
                 "pubkey TEXT NOT NULL, created_ms INTEGER NOT NULL, expires_ms INTEGER NOT NULL, "
                 "max_uses INTEGER NOT NULL, uses INTEGER NOT NULL DEFAULT 0)")
    return conn


def _norm_code(code) -> str:
    if not isinstance(code, str) or not _INVITE_CODE_RE.fullmatch(code.strip().upper()):
        raise ValueError("invite code must look like ABCD-EFGH")
    c = code.strip().upper().replace("-", "")
    return f"{c[:4]}-{c[4:]}"


def invites_create(data) -> tuple:
    """Body: {"card": <contact card, ts within 10 min>, "ttl_s"?: <=604800, "max_uses"?: 1-100}."""
    try:
        if not isinstance(data, dict) or set(data) - {"card", "ttl_s", "max_uses"}:
            raise ValueError("body must be {\"card\", \"ttl_s\"?, \"max_uses\"?}")
        now = now_ms()
        card = verify_contact_card(data.get("card"), now)
        if abs(now - card["ts"]) > INVITE_CREATE_SKEW_MS:
            raise ValueError("card 'ts' must be within 10 minutes of the hub clock (sign a fresh card)")
        ttl = data.get("ttl_s", INVITE_TTL_DEFAULT_S)
        uses = data.get("max_uses", 1)
        if not isinstance(ttl, int) or isinstance(ttl, bool) or not 60 <= ttl <= INVITE_TTL_MAX_S:
            raise ValueError(f"'ttl_s' must be 60-{INVITE_TTL_MAX_S}")
        if not isinstance(uses, int) or isinstance(uses, bool) or not 1 <= uses <= INVITE_MAX_USES:
            raise ValueError(f"'max_uses' must be 1-{INVITE_MAX_USES}")
    except ValueError as e:
        return {"status": "ERROR", "message": str(e)}, 400
    if not USER_RATE.allow("invite:" + card["pubkey"]):
        return {"status": "ERROR", "message": "rate limited: too many invites from this key"}, 429
    with INVITES_LOCK:
        conn = _invites_db()
        try:
            conn.execute("DELETE FROM invites WHERE expires_ms < ? OR uses >= max_uses", (now,))
            if conn.execute("SELECT COUNT(*) FROM invites WHERE pubkey = ?", (card["pubkey"],)).fetchone()[0] >= 20:
                return {"status": "ERROR", "message": "this key already has 20 live invites"}, 429
            for _ in range(10):
                raw = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(8))
                code = f"{raw[:4]}-{raw[4:]}"
                try:
                    conn.execute("INSERT INTO invites (code, card_json, pubkey, created_ms, expires_ms, max_uses) "
                                 "VALUES (?, ?, ?, ?, ?, ?)", (code, json.dumps(card), card["pubkey"], now,
                                                               now + ttl * 1000, uses))
                    conn.commit()
                    break
                except sqlite3.IntegrityError:
                    continue
            else:
                return {"status": "ERROR", "message": "could not allocate a code"}, 503
        finally:
            conn.close()
    TELEMETRY.inc("invites_created")
    return {"status": "OK", "code": code, "expires_ms": now + ttl * 1000, "max_uses": uses,
            "qr": f"omni://invite?code={code}"}, 200


def invites_redeem(query: str, client: str = "loopback") -> tuple:
    try:
        params = _query_args(query, {"code"})
        code = _norm_code((params.get("code") or [""])[-1])
    except ValueError as e:
        return {"status": "ERROR", "message": str(e)}, 400
    now = now_ms()
    with INVITES_LOCK:
        conn = _invites_db()
        try:
            row = conn.execute("SELECT card_json, expires_ms, max_uses, uses FROM invites WHERE code = ?",
                               (code,)).fetchone()
            if row and row[1] >= now and row[3] < row[2]:
                conn.execute("UPDATE invites SET uses = uses + 1 WHERE code = ?", (code,))
                conn.commit()
        finally:
            conn.close()
    if not row or row[1] < now or row[3] >= row[2]:
        if not INVITE_REDEEM_FAILS.allow(client):
            return {"status": "ERROR", "message": "too many failed invite codes; wait a minute"}, 429
        TELEMETRY.inc("invites_redeem_failed")
        return {"status": "ERROR", "message": "unknown, expired or used-up invite code"}, 404
    card = json.loads(row[0])
    TELEMETRY.inc("invites_redeemed")
    return {"status": "OK", "card": card, "handle_display": handle_display(card["handle"], card["pubkey"]),
            "uses_left": row[2] - row[3] - 1, "expires_ms": row[1]}, 200

# --- KickBack comments + reactions (v8.14.0): person-signed, keyed to a post id --------------------
# Spec: "every post, comment, and reaction" is signed (launch notes) and the feed has reaction overlays
# (spec Module 2). Both are person-signed events (same pattern as profiles). A post_id is the id the app
# shows for a post: its app_event_id (the phone-signed id, HubFeedEvent.dedupeKey) or, for a post with no
# app envelope, the node event id. The post does not have to be on this hub yet (it may arrive later by
# sync); answers say whether it is. See Admin/docs/SOCIAL.md.
COMMENT_ACTION = "kickback_comment"
REACTION_ACTION = "kickback_reaction"
POST_ACTION = "KICKBACK_POST"
SOCIAL_SCHEMA = 1
COMMENT_MAX_CHARS = 2000
REACTION_MAX_CHARS = 16
SOCIAL_COUNTS_MAX_IDS = 100


def _event_id_field(v, name: str) -> str:
    if not isinstance(v, str) or not _HEX_HASH_RE.fullmatch(v):
        raise ValueError(f"'{name}' must be 0x + 64 lowercase hex (an event id)")
    return v


def validate_comment(p) -> dict:
    if not isinstance(p, dict):
        raise ValueError("payload must be an object")
    unknown = set(p) - {"schema", "post_id", "text", "reply_to"}
    if unknown:
        raise ValueError(f"unknown comment field(s): {', '.join(sorted(unknown))}")
    if p.get("schema") != SOCIAL_SCHEMA:
        raise ValueError(f"'schema' must be {SOCIAL_SCHEMA}")
    _event_id_field(p.get("post_id"), "post_id")
    if "reply_to" in p:
        _event_id_field(p["reply_to"], "reply_to")
    text = p.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("'text' must be a non-empty string")
    if _clean_text(text, "text", COMMENT_MAX_CHARS, multiline=True) != text:
        raise ValueError("'text' has control characters or surrounding spaces; send it trimmed")
    return p


def validate_reaction(p) -> dict:
    if not isinstance(p, dict):
        raise ValueError("payload must be an object")
    if set(p) != {"schema", "post_id", "reaction", "on"}:
        raise ValueError("reaction payload fields are exactly schema, post_id, reaction, on")
    if p["schema"] != SOCIAL_SCHEMA:
        raise ValueError(f"'schema' must be {SOCIAL_SCHEMA}")
    _event_id_field(p["post_id"], "post_id")
    r = p["reaction"]
    if (not isinstance(r, str) or not 1 <= len(r) <= REACTION_MAX_CHARS
            or any(ch.isspace() or ch < " " for ch in r)):
        raise ValueError(f"'reaction' must be 1-{REACTION_MAX_CHARS} chars with no spaces (an emoji or short name)")
    if not isinstance(p["on"], bool):
        raise ValueError("'on' must be true (add) or false (remove)")
    return p


def _posts_known(post_ids, db_path: Path = None) -> dict:
    """post_id -> {"author_pubkey", "text", "ts_ms"} for the ids this hub holds a KICKBACK_POST for."""
    db_path = db_path or _db_path()
    ids = list(post_ids)
    if not ids or not db_path.exists():
        return {}
    marks = ",".join("?" for _ in ids)
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT event_id, author_pubkey, payload_json, timestamp, ts_ms FROM events WHERE action = ? AND "
            f"(event_id IN ({marks}) OR json_extract(payload_json, '$.app_event_id') IN ({marks}))",
            (POST_ACTION, *ids, *ids)).fetchall()
    finally:
        conn.close()
    out = {}
    for eid, author, pj, ts, ts_ms in rows:
        try:
            p = json.loads(pj or "{}")
        except ValueError:
            continue
        key = p.get("app_event_id") if p.get("app_event_id") in ids else eid
        out[key] = {"author_pubkey": p.get("app_author_pubkey") or author, "text": str(p.get("text", ""))[:280],
                    "ts_ms": int(ts_ms) if ts_ms is not None else int(round(float(ts) * 1000))}
    return out


def _social_rows(post_ids, db_path: Path = None):
    """(comments, reactions) person-signed and schema-valid, for the given post ids, oldest first."""
    ids = list(post_ids)
    marks = ",".join("?" for _ in ids)
    rows = _user_rows((COMMENT_ACTION, REACTION_ACTION), f"json_extract(payload_json, '$.post_id') IN ({marks})",
                      tuple(ids), db_path)
    comments, reactions = [], []
    for e in rows:
        try:
            if e["action"] == COMMENT_ACTION:
                validate_comment(e["payload"])
                comments.append(e)
            else:
                validate_reaction(e["payload"])
                reactions.append(e)
        except ValueError:
            continue
    return comments, reactions


def _reaction_state(reactions) -> dict:
    """(post_id, author, reaction) -> on, latest signed ts wins (ties: later arrival)."""
    state = {}
    for e in reactions:
        p = e["payload"]
        k = (p["post_id"], e["author_pubkey"], p["reaction"])
        cur = state.get(k)
        if cur is None or e["ts"] >= cur[0]:
            state[k] = (e["ts"], p["on"])
    return state


def _reaction_counts(state: dict, post_id: str, viewer: str = None) -> tuple:
    counts, mine = {}, []
    for (pid, author, r), (_ts, on) in state.items():
        if pid == post_id and on:
            counts[r] = counts.get(r, 0) + 1
            if viewer and author == viewer:
                mine.append(r)
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))), sorted(mine)


def social_thread(query: str) -> tuple:
    try:
        params = _query_args(query, {"post_id", "limit", "viewer"})
        post_id = _event_id_field((params.get("post_id") or [""])[-1], "post_id")
        limit = _feed_int(params, "limit")
        viewer = (params.get("viewer") or [None])[-1]
        if viewer is not None:
            viewer = credit_account(viewer, allow_treasury=False)
    except ValueError as e:
        return {"status": "ERROR", "message": str(e)}, 400
    limit = 200 if limit is None else max(1, min(limit, 500))
    comments, reactions = _social_rows([post_id])
    profiles = latest_profiles()
    def who(pk):
        prof = profiles.get(pk)
        return handle_display(prof["payload"]["handle"], pk) if prof else None
    out = [{"event_id": e["event_id"], "author_pubkey": e["author_pubkey"], "handle_display": who(e["author_pubkey"]),
            "text": e["payload"]["text"], "reply_to": e["payload"].get("reply_to"), "ts_ms": e["ts"],
            "origin": e["origin"], "verified": True} for e in comments]
    out.sort(key=lambda c: (c["ts_ms"], c["event_id"]))
    counts, mine = _reaction_counts(_reaction_state(reactions), post_id, viewer)
    post = _posts_known([post_id]).get(post_id)
    return {"status": "OK", "post_id": post_id, "post_known": post is not None, "post": post,
            "comment_count": len(out), "has_more": len(out) > limit, "comments": out[:limit],
            "reactions": counts, **({"my_reactions": mine} if viewer else {})}, 200


def social_counts(query: str) -> tuple:
    try:
        params = _query_args(query, {"post_ids", "viewer"})
        raw = (params.get("post_ids") or [""])[-1]
        ids = [x for x in (s.strip() for s in raw.split(",")) if x]
        if not ids:
            raise ValueError("'post_ids' is required (comma-separated event ids)")
        if len(ids) > SOCIAL_COUNTS_MAX_IDS:
            raise ValueError(f"at most {SOCIAL_COUNTS_MAX_IDS} post_ids per call")
        ids = list(dict.fromkeys(_event_id_field(i, "post_ids") for i in ids))
        viewer = (params.get("viewer") or [None])[-1]
        if viewer is not None:
            viewer = credit_account(viewer, allow_treasury=False)
    except ValueError as e:
        return {"status": "ERROR", "message": str(e)}, 400
    comments, reactions = _social_rows(ids)
    state = _reaction_state(reactions)
    per = {}
    for pid in ids:
        counts, mine = _reaction_counts(state, pid, viewer)
        per[pid] = {"comments": sum(1 for c in comments if c["payload"]["post_id"] == pid), "reactions": counts,
                    **({"my_reactions": mine} if viewer else {})}
    return {"status": "OK", "posts": per}, 200


RESERVED_USER_ACTIONS[COMMENT_ACTION] = "/api/social/comment"
RESERVED_USER_ACTIONS[REACTION_ACTION] = "/api/social/react"

# --- Omni Credits TEST ledger (v8.10.0): closed-loop, replayed from signed chain events -----------
# Every ledger entry is a node-signed chain event with action "credit_entry", appended through the
# same process_and_store_event path as /api/events/append (not relayed on arrival). There is no balance
# table: balances are derived by replaying this node's own credit_entry events in chain order, and
# every entry's hash and Ed25519 signature are re-checked on each replay. TEST credits only: no cash
# value, nothing is redeemable, and every endpoint is loopback only (see Admin/docs/CREDITS_LEDGER.md).
CREDIT_ACTION = "credit_entry"
CREDIT_TREASURY = "treasury"
CREDIT_KINDS = ("grant", "transfer", "purchase", "reset", "tip")
CREDIT_SIGNED_KINDS = ("transfer", "purchase", "tip")
CREDIT_TRANSFER_TYPE = "omni.credits.transfer.v1"
CREDIT_TRANSFER_FIELDS = {"type", "from", "to", "amount", "kind", "memo", "ref", "nonce", "ts", "sig"}
CREDIT_TRANSFER_WINDOW_MS = 600_000          # signed ts must be within 10 min of the hub clock
_CREDIT_NONCE_RE = re.compile(r"[0-9a-f]{16,64}")
_CREDIT_REF_RE = re.compile(r"[A-Za-z0-9_.:-]{1,80}")
CREDITS_REQUIRE_SIGNED = os.environ.get("OMNI_CREDITS_REQUIRE_SIGNED", "").strip().lower() in ("1", "true", "yes")
CREDIT_MAX_AMOUNT = 1_000_000
CREDIT_WELCOME_AMOUNT = 1000
CREDIT_WELCOME_MEMO = "welcome grant: 1,000 test credits, no cash value"
CREDIT_MEMO_MAX = 200
CREDIT_BODY_MAX_BYTES = 4 * 1024
CREDIT_FEE_BPS_ENV = "OMNI_TREASURY_FEE_BPS"
_PUBKEY_RE = re.compile(r"[0-9a-f]{64}")
_CREDIT_HISTORY_ARGS = {"pubkey", "limit"}
CREDITS_LOCK = threading.Lock()   # replay + overdraft check + append is one critical section

def treasury_fee_bps(value=None) -> int:
    """Treasury fee in basis points (0-10000) from $OMNI_TREASURY_FEE_BPS. Unset/bad -> 0."""
    raw = (os.environ.get(CREDIT_FEE_BPS_ENV, "") if value is None else str(value)).strip()
    return int(raw) if raw.isdigit() and int(raw) <= 10000 else 0

TREASURY_FEE_BPS = treasury_fee_bps()

class LedgerIntegrityError(Exception):
    def __init__(self, event_id: str, reason: str):
        super().__init__(f"credit entry {event_id} failed verification: {reason}")
        self.event_id, self.reason = event_id, reason

def credit_account(value, allow_treasury: bool = True) -> str:
    """A 64-hex Ed25519 pubkey (lower-cased) or "treasury". Raises ValueError."""
    if not isinstance(value, str):
        raise ValueError("account must be a 64-hex pubkey string")
    v = value.strip().lower()
    if allow_treasury and v == CREDIT_TREASURY:
        return v
    if not _PUBKEY_RE.fullmatch(v):
        raise ValueError("account must be a 64-hex Ed25519 pubkey" + (' or "treasury"' if allow_treasury else ""))
    return v

def credit_amount(value, name: str = "amount", allow_zero: bool = False) -> int:
    """Integer credits, 0 < n <= 1,000,000 (fee may be 0). Floats, strings and bools are rejected."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"'{name}' must be an integer number of credits")
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError(f"'{name}' must be greater than 0")
    if value > CREDIT_MAX_AMOUNT:
        raise ValueError(f"'{name}' is over the {CREDIT_MAX_AMOUNT:,} credit limit")
    return value

def credit_memo(value) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("'memo' must be a string")
    v = "".join(ch for ch in value if ch >= " ").strip()
    if len(v) > CREDIT_MEMO_MAX:
        raise ValueError(f"'memo' is longer than {CREDIT_MEMO_MAX} characters")
    return v

def validate_credit_payload(p) -> dict:
    """Schema check used both before append and on every replayed entry."""
    if not isinstance(p, dict):
        raise ValueError("payload is not an object")
    base = {"kind", "from", "to", "amount", "fee", "memo", "test_only"}
    if not base <= set(p) or set(p) - base - {"ref", "auth"}:
        raise ValueError("payload fields are not kind/from/to/amount/fee/memo/test_only[/ref/auth]")
    if p["kind"] not in CREDIT_KINDS:
        raise ValueError(f"unknown kind {p['kind']!r}")
    if p["test_only"] is not True:
        raise ValueError("test_only must be true")
    frm, to = credit_account(p["from"]), credit_account(p["to"])
    amount = credit_amount(p["amount"])
    fee = credit_amount(p["fee"], "fee", allow_zero=True)
    if fee > amount:
        raise ValueError("fee is larger than amount")
    if frm == to:
        raise ValueError("from and to are the same account")
    if p["kind"] == "grant" and (frm != CREDIT_TREASURY or to == CREDIT_TREASURY or fee):
        raise ValueError("a grant goes from treasury to a pubkey with no fee")
    if p["kind"] == "reset" and (frm == CREDIT_TREASURY or to != CREDIT_TREASURY or fee):
        raise ValueError("a reset returns a pubkey's balance to treasury with no fee")
    if p["kind"] in CREDIT_SIGNED_KINDS and frm == CREDIT_TREASURY:
        raise ValueError("transfers, purchases and tips must come from a pubkey")
    if p["kind"] == "tip" and ("ref" not in p or to == CREDIT_TREASURY):
        raise ValueError("a tip goes to a pubkey and names what it tips (ref, e.g. a post id)")
    if "ref" in p and (not isinstance(p["ref"], str) or not _CREDIT_REF_RE.fullmatch(p["ref"])):
        raise ValueError("'ref' must be 1-80 chars of A-Z a-z 0-9 _ . : -")
    credit_memo(p["memo"])
    if "auth" in p:
        verify_transfer_auth(p)
    return p

def credit_transfer_message(p: dict, auth: dict) -> dict:
    """The exact object the "from" key signed for a ledger entry (fee excluded: the hub sets it)."""
    msg = {"type": auth["type"], "from": p["from"], "to": p["to"], "amount": p["amount"], "kind": p["kind"],
           "memo": p["memo"], "nonce": auth["nonce"], "ts": auth["ts"]}
    if "ref" in p:
        msg["ref"] = p["ref"]
    return msg

def credit_signing_bytes(msg: dict) -> bytes:
    return json.dumps({k: v for k, v in msg.items() if k != "sig"}, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")

def verify_transfer_auth(p: dict):
    """Raises ValueError unless entry p carries the "from" key's valid signature over its own fields."""
    auth = p["auth"]
    if not isinstance(auth, dict) or set(auth) != {"type", "nonce", "ts", "sig"}:
        raise ValueError("auth must be exactly type/nonce/ts/sig")
    if auth["type"] != CREDIT_TRANSFER_TYPE:
        raise ValueError(f"auth type must be {CREDIT_TRANSFER_TYPE}")
    if not isinstance(auth["nonce"], str) or not _CREDIT_NONCE_RE.fullmatch(auth["nonce"]):
        raise ValueError("'nonce' must be 16-64 lowercase hex chars")
    if not isinstance(auth["ts"], int) or isinstance(auth["ts"], bool) or auth["ts"] < 0:
        raise ValueError("'ts' must be an integer (milliseconds)")
    if not isinstance(auth["sig"], str) or not _USER_SIG_RE.fullmatch(auth["sig"]):
        raise ValueError("'sig' must be a 128-char lowercase hex Ed25519 signature")
    if p["kind"] not in CREDIT_SIGNED_KINDS or p["from"] == CREDIT_TREASURY:
        raise ValueError("only transfers, purchases and tips from a pubkey are signed")
    if not _ed25519_ok(p["from"], auth["sig"], credit_signing_bytes(credit_transfer_message(p, auth))):
        raise ValueError("bad signature: must be by 'from' over type/from/to/amount/kind/memo/nonce/ts[/ref]")

def _verify_credit_row(row):
    """Returns the payload of a stored credit_entry row, or raises LedgerIntegrityError."""
    rowid, event_id, author, prev_hash, timestamp, payload_json, signature, ts_ms = row
    try:
        payload = json.loads(payload_json or "{}")
    except ValueError:
        raise LedgerIntegrityError(event_id, "payload is not JSON")
    time_fields = {"ts": int(ts_ms)} if ts_ms is not None else {"timestamp": timestamp}
    recomputed = compute_canonical_event_id(CREDIT_ACTION, author, payload, prev_hash, timestamp,
                                            int(ts_ms) if ts_ms is not None else None)
    if recomputed != event_id:
        raise LedgerIntegrityError(event_id, "content hash does not match event_id")
    if not signature or not verify_event({"action": CREDIT_ACTION, "author_pubkey": author, "payload": payload,
                                          "previous_hash": prev_hash, **time_fields, "signature": signature}):
        raise LedgerIntegrityError(event_id, "bad Ed25519 signature")
    try:
        validate_credit_payload(payload)
    except ValueError as e:
        raise LedgerIntegrityError(event_id, f"bad entry: {e}")
    return payload

def replay_credit_ledger(db_path: Path = None) -> dict:
    """Replays this node's credit_entry events in chain (row) order. Entries authored by any other key
    (e.g. a peer's copy arriving through sync) are ignored: each node's ledger is its own.
    Raises LedgerIntegrityError if any entry fails its hash, signature or schema check."""
    db_path = db_path or _db_path()
    balances, welcomed, entries = {}, set(), []
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute("SELECT id, event_id, author_pubkey, previous_hash, timestamp, payload_json, "
                                "signature, ts_ms FROM events WHERE action = ? AND author_pubkey = ? "
                                "ORDER BY id ASC", (CREDIT_ACTION, STATE.node_id)).fetchall()
        finally:
            conn.close()
        for row in rows:
            p = _verify_credit_row(row)
            frm, to, amount, fee = p["from"], p["to"], p["amount"], p["fee"]
            if frm != CREDIT_TREASURY:            # treasury grants are issuance, not a debit
                balances[frm] = balances.get(frm, 0) - amount
            balances[to] = balances.get(to, 0) + amount - fee
            if fee:
                balances[CREDIT_TREASURY] = balances.get(CREDIT_TREASURY, 0) + fee
            if p["kind"] == "grant" and p["memo"] == CREDIT_WELCOME_MEMO:
                welcomed.add(to)
            entries.append({"id": row[0], "event_id": row[1], "ts_ms": int(row[7]) if row[7] is not None
                            else int(round(float(row[4]) * 1000)), "verified": True, **p})
    for acct, bal in balances.items():   # cannot happen through the API; a valid-but-negative chain is corrupt
        if bal < 0 and acct != CREDIT_TREASURY:
            raise LedgerIntegrityError("-", f"replayed balance for {acct[:12]}... is negative")
    return {"balances": balances, "welcomed": welcomed, "entries": entries}

def _append_credit(kind: str, frm: str, to: str, amount: int, fee: int = 0, memo: str = "",
                   ref: str = None, auth: dict = None) -> tuple:
    payload = {"kind": kind, "from": frm, "to": to, "amount": amount, "fee": fee, "memo": memo, "test_only": True}
    if ref is not None:
        payload["ref"] = ref
    if auth is not None:
        payload["auth"] = auth
    payload = validate_credit_payload(payload)
    resp, status = process_and_store_event({"action": CREDIT_ACTION, "payload": payload},
                                           origin_peer=None, relay=False)
    if status == 200:
        resp = {"status": "SUCCESS", "event_id": resp.get("event_id"), "entry": payload}
    return resp, status

def _ensure_welcome_locked(pubkey: str, ledger: dict) -> dict:
    """Caller holds CREDITS_LOCK. Issues the one-time welcome grant; returns the (re)played ledger."""
    if pubkey == CREDIT_TREASURY or pubkey in ledger["welcomed"]:
        return ledger
    resp, status = _append_credit("grant", CREDIT_TREASURY, pubkey, CREDIT_WELCOME_AMOUNT, 0, CREDIT_WELCOME_MEMO)
    if status != 200:
        raise RuntimeError(f"welcome grant failed: {resp.get('message')}")
    return replay_credit_ledger()

def credits_balance(pubkey, grant_welcome: bool = True) -> tuple:
    """grant_welcome=False (remote hub lookups, v8.15.0): never writes; an unclaimed welcome grant is
    reported as welcome_pending and counted in "available" (it is issued on the key's first signed send)."""
    try:
        acct = credit_account(pubkey)
    except ValueError as e:
        return {"status": "ERROR", "message": str(e)}, 400
    with CREDITS_LOCK:
        ledger = replay_credit_ledger()
        if grant_welcome:
            ledger = _ensure_welcome_locked(acct, ledger)
    bal = ledger["balances"].get(acct, 0)
    pending = acct != CREDIT_TREASURY and acct not in ledger["welcomed"]
    return {"status": "OK", "pubkey": acct, "balance": bal, "test_only": True,
            "available": bal + (CREDIT_WELCOME_AMOUNT if pending else 0), "welcome_pending": pending,
            "note": "test credits, no cash value", "fee_bps": TREASURY_FEE_BPS,
            "entries_replayed": len(ledger["entries"]), "version": VERSION}, 200

def credits_history(query: str) -> tuple:
    params = urllib.parse.parse_qs(query or "", keep_blank_values=True)
    unknown = set(params) - _CREDIT_HISTORY_ARGS
    if unknown:
        return {"status": "ERROR", "message": f"unknown parameter(s): {', '.join(sorted(unknown))}"}, 400
    try:
        acct = credit_account((params.get("pubkey") or [""])[-1])
        limit = _feed_int(params, "limit")
    except ValueError as e:
        return {"status": "ERROR", "message": str(e)}, 400
    limit = FEED_DEFAULT_LIMIT if limit is None else max(1, min(limit, FEED_MAX_LIMIT))
    ledger = replay_credit_ledger()
    running, mine = 0, []
    for e in ledger["entries"]:
        delta = 0
        if acct == CREDIT_TREASURY:
            if e["to"] != CREDIT_TREASURY and not e["fee"]:
                continue                  # grants are issuance: they never debit the treasury
            delta = e["fee"] + (e["amount"] if e["to"] == CREDIT_TREASURY else 0)
        else:
            if acct not in (e["from"], e["to"]):
                continue
            if e["from"] == acct:
                delta -= e["amount"]
            if e["to"] == acct:
                delta += e["amount"] - e["fee"]
        running += delta
        mine.append(dict(e, delta=delta, balance_after=running))
    mine.reverse()   # newest first
    return {"status": "OK", "pubkey": acct, "balance": ledger["balances"].get(acct, 0), "test_only": True,
            "count": min(len(mine), limit), "has_more": len(mine) > limit, "entries": mine[:limit]}, 200

def credits_send(data) -> tuple:
    """Signed transfer (v8.15.0). Body: {"type": "omni.credits.transfer.v1", "from", "to", "amount",
    "kind": transfer|purchase|tip, "memo", "ref"?, "nonce", "ts", "sig"}; sig by "from" over every
    field except sig (sorted-key compact JSON, raw UTF-8). Node-local double-spend rules: one ledger,
    one lock; (from, nonce) can be applied once ever (identical retry -> ALREADY_APPLIED, same nonce with
    other content -> 409); amount <= balance."""
    if not isinstance(data, dict):
        return {"status": "ERROR", "message": "body must be a JSON object"}, 400
    try:
        unknown = set(data) - CREDIT_TRANSFER_FIELDS
        if unknown:
            raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")
        missing = {"type", "from", "to", "amount", "kind", "memo", "nonce", "ts", "sig"} - set(data)
        if missing:
            raise ValueError(f"missing field(s): {', '.join(sorted(missing))}")
        if data["kind"] not in CREDIT_SIGNED_KINDS:
            raise ValueError("'kind' must be transfer, purchase or tip")
        frm = credit_account(data["from"], allow_treasury=False)
        to = credit_account(data["to"])
        if frm != data["from"] or to != data["to"]:
            raise ValueError("pubkeys must be lowercase (they are part of the signed bytes)")
        amount = credit_amount(data["amount"])
        if credit_memo(data["memo"]) != data["memo"]:
            raise ValueError("'memo' must be trimmed with no control characters (it is signed as sent)")
        if frm == to:
            raise ValueError("from and to are the same account")
        auth = {"type": data["type"], "nonce": data["nonce"], "ts": data["ts"], "sig": data["sig"]}
        entry = {"kind": data["kind"], "from": frm, "to": to, "amount": amount, "fee": 0, "memo": data["memo"],
                 "test_only": True, "auth": auth, **({"ref": data["ref"]} if "ref" in data else {})}
        validate_credit_payload(entry)   # schema + tip/ref rules + the signature itself
        if abs(now_ms() - data["ts"]) > CREDIT_TRANSFER_WINDOW_MS:
            raise PermissionError("stale or future 'ts' (must be within 10 minutes of the hub clock)")
    except PermissionError as e:
        TELEMETRY.inc("credits_send_rejected")
        return {"status": "ERROR", "message": str(e)}, 401
    except ValueError as e:
        TELEMETRY.inc("credits_send_rejected")
        status = 401 if str(e).startswith("bad signature") else 400
        return {"status": "ERROR", "message": str(e)}, status
    fee = 0 if to == CREDIT_TREASURY else amount * TREASURY_FEE_BPS // 10000
    with CREDITS_LOCK:
        ledger = replay_credit_ledger()
        for e in ledger["entries"]:
            a = e.get("auth")
            if a and e["from"] == frm and a["nonce"] == auth["nonce"]:
                if a["sig"] == auth["sig"]:
                    return {"status": "SUCCESS", "result": "ALREADY_APPLIED", "event_id": e["event_id"],
                            "balance": ledger["balances"].get(frm, 0)}, 200
                TELEMETRY.inc("credits_send_double_spend")
                return {"status": "ERROR", "message": "nonce already used by another transfer from this key"}, 409
        ledger = _ensure_welcome_locked(frm, ledger)
        have = ledger["balances"].get(frm, 0)
        if amount > have:
            return {"status": "ERROR", "message": f"insufficient test credits: balance {have}, need {amount}",
                    "balance": have}, 409
        resp, status = _append_credit(data["kind"], frm, to, amount, fee, data["memo"],
                                      ref=data.get("ref"), auth=auth)
        if status == 200:
            resp["balance"] = have - amount
            TELEMETRY.inc("credits_send_ok")
    return resp, status

def credits_transfer(data) -> tuple:
    """Unsigned, loopback only (v8.10.0; refused when OMNI_CREDITS_REQUIRE_SIGNED=1). Body: {"from": pubkey, "to": pubkey|"treasury", "amount": int, "memo"?: str, "kind"?: transfer|purchase}.
    The Treasury fee (OMNI_TREASURY_FEE_BPS of amount, rounded down) comes out of what the recipient gets."""
    if CREDITS_REQUIRE_SIGNED:
        return {"status": "ERROR", "message": "unsigned transfers are off (OMNI_CREDITS_REQUIRE_SIGNED=1); "
                                              "use POST /api/credits/send"}, 403
    if not isinstance(data, dict):
        return {"status": "ERROR", "message": "body must be a JSON object"}, 400
    unknown = set(data) - {"from", "to", "amount", "memo", "kind"}
    if unknown:
        return {"status": "ERROR", "message": f"unknown field(s): {', '.join(sorted(unknown))}"}, 400
    try:
        kind = data.get("kind", "transfer")
        if kind not in ("transfer", "purchase"):
            raise ValueError("'kind' must be transfer or purchase")
        frm = credit_account(data.get("from"), allow_treasury=False)
        to = credit_account(data.get("to"))
        amount = credit_amount(data.get("amount"))
        memo = credit_memo(data.get("memo"))
        if frm == to:
            raise ValueError("from and to are the same account")
    except ValueError as e:
        return {"status": "ERROR", "message": str(e)}, 400
    fee = 0 if to == CREDIT_TREASURY else amount * TREASURY_FEE_BPS // 10000
    with CREDITS_LOCK:
        ledger = _ensure_welcome_locked(frm, replay_credit_ledger())
        have = ledger["balances"].get(frm, 0)
        if amount > have:
            return {"status": "ERROR", "message": f"insufficient test credits: balance {have}, need {amount}",
                    "balance": have}, 409
        resp, status = _append_credit(kind, frm, to, amount, fee, memo)
        if status == 200:
            resp["balance"] = have - amount
    return resp, status

def credits_grant(data) -> tuple:
    """Admin (loopback only). {"to": pubkey, "amount": int, "memo"?} grants from treasury;
    {"kind": "reset", "pubkey": pubkey, "memo"?} returns that pubkey's whole balance to treasury."""
    if not isinstance(data, dict):
        return {"status": "ERROR", "message": "body must be a JSON object"}, 400
    kind = data.get("kind", "grant")
    try:
        if kind == "grant":
            unknown = set(data) - {"kind", "to", "amount", "memo"}
            if unknown:
                raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")
            to = credit_account(data.get("to"), allow_treasury=False)
            amount = credit_amount(data.get("amount"))
            memo = credit_memo(data.get("memo")) or "admin test grant, no cash value"
            if memo == CREDIT_WELCOME_MEMO:
                raise ValueError("that memo is reserved for the welcome grant")
        elif kind == "reset":
            unknown = set(data) - {"kind", "pubkey", "memo"}
            if unknown:
                raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")
            acct = credit_account(data.get("pubkey"), allow_treasury=False)
            memo = credit_memo(data.get("memo")) or "test reset"
        else:
            raise ValueError("'kind' must be grant or reset")
    except ValueError as e:
        return {"status": "ERROR", "message": str(e)}, 400
    with CREDITS_LOCK:
        ledger = replay_credit_ledger()
        if kind == "grant":
            return _append_credit("grant", CREDIT_TREASURY, to, amount, 0, memo)
        have = ledger["balances"].get(acct, 0)
        if have <= 0:
            return {"status": "SUCCESS", "result": "NOTHING_TO_RESET", "balance": 0}, 200
        return _append_credit("reset", acct, CREDIT_TREASURY, have, 0, memo)

# --- OmniCast signaling mailbox (v8.11.0): short-lived, signed WebRTC signaling ---------------------
# A tiny store-and-forward mailbox so two phones that can only reach the hub (Tailscale node sharing)
# can swap WebRTC offer/answer/ICE. Memory only: never written to the event log or SQLite, never
# relayed to peers, gone after SIGNAL_TTL_S or on delivery, and gone on restart. Every message is
# Ed25519-signed by its sender over canonical fields and the signature is handed to the recipient, so
# the recipient can re-verify end to end (the hub can't alter an SDP without breaking it). Payloads
# are never logged. See Admin/docs/OMNICAST_SIGNALING.md.
SIGNAL_TTL_S = min(300.0, max(1.0, _env_float("OMNI_SIGNAL_TTL", 60.0)))  # undelivered messages expire (tests shorten it)
SIGNAL_TS_WINDOW_MS = 120_000           # request ts must be within +/-120 s of the hub clock
SIGNAL_MAX_BODY_BYTES = 16 * 1024       # whole POST body
SIGNAL_MAX_PAYLOAD_CHARS = 14 * 1024    # SDP / ICE JSON string inside it
SIGNAL_MAX_PER_RECIPIENT = 64           # queued, undelivered messages per recipient
SIGNAL_MAX_TOTAL = 4096                 # queued messages across all recipients
SIGNAL_MAX_LONG_POLL_S = 25.0
SIGNAL_MAX_WAITERS = 64                 # concurrent long-polls; beyond this a poll returns at once
SIGNAL_RATE_BURST = 40.0                # per-sender token bucket: burst of 40 sends ...
SIGNAL_RATE_PER_S = 10.0                # ... refilled at 10 per second (ICE trickle is bursty)
SIGNAL_SEEN_MAX = 50_000                # remembered signatures (replay guard)
SIGNAL_KINDS = ("offer", "answer", "ice", "hangup", "ring")
SIGNAL_SEND_TYPE = "omnicast.signal.v1"
SIGNAL_POLL_TYPE = "omnicast.poll.v1"
SIGNAL_ICE_TYPE = "omnicast.ice-config.v1"
SIGNAL_SEND_FIELDS = {"to", "from", "call_id", "kind", "payload", "ts", "sig"}
_SIGNAL_POLL_ARGS = {"to", "since", "ts", "sig", "wait"}
_SIGNAL_ICE_ARGS = {"pubkey", "ts", "sig"}
_PUBKEY_RE = re.compile(r"[0-9a-f]{64}")
_SIG_RE = re.compile(r"[0-9a-f]{128}")
_CALL_ID_RE = re.compile(r"[A-Za-z0-9_.:-]{1,64}")

TURN_URLS_ENV = "OMNI_TURN_URLS"        # e.g. "turn:100.101.102.103:3478?transport=udp,turn:100.101.102.103:3478?transport=tcp"
TURN_SECRET_ENV = "OMNI_TURN_SECRET"    # same value as the TURN server's shared secret (eturnal "secret")
STUN_URLS_ENV = "OMNI_STUN_URLS"        # optional override of the default public STUN server
TURN_TTL_ENV = "OMNI_TURN_TTL"          # seconds the TURN credential is valid (default 3600)
DEFAULT_STUN_URLS = ("stun:stun.l.google.com:19302",)
TURN_TTL_DEFAULT = 3600


class SignalError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def signal_send_bytes(msg: dict) -> bytes:
    """Bytes the sender signs for POST /api/signal/send (sorted-key compact JSON, raw UTF-8, int-ms ts)."""
    return json.dumps({"type": SIGNAL_SEND_TYPE, "to": msg["to"], "from": msg["from"],
                       "call_id": msg["call_id"], "kind": msg["kind"], "payload": msg["payload"],
                       "ts": msg["ts"]}, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")   # raw UTF-8, like Dart's jsonEncode


def signal_auth_bytes(kind_type: str, pubkey: str, ts: int) -> bytes:
    """Bytes a key owner signs to poll its mailbox (SIGNAL_POLL_TYPE, field "to") or fetch ICE config
    (SIGNAL_ICE_TYPE, field "pubkey")."""
    field = "to" if kind_type == SIGNAL_POLL_TYPE else "pubkey"
    return json.dumps({"type": kind_type, field: pubkey, "ts": ts},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _ed25519_ok(pubkey: str, sig: str, data: bytes) -> bool:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pubkey)).verify(bytes.fromhex(sig), data)
        return True
    except Exception:
        return False


def _signal_ts(value, now: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise SignalError(400, "'ts' must be an integer (milliseconds since epoch)")
    if abs(now - value) > SIGNAL_TS_WINDOW_MS:
        raise SignalError(401, "stale or future 'ts' (must be within 120 s of the hub clock)")
    return value


def _signal_pubkey(value, name: str) -> str:
    if not isinstance(value, str) or not _PUBKEY_RE.fullmatch(value):
        raise SignalError(400, f"'{name}' must be a 64-char lowercase hex Ed25519 public key")
    return value


def _signal_sig(value) -> str:
    if not isinstance(value, str) or not _SIG_RE.fullmatch(value):
        raise SignalError(400, "'sig' must be a 128-char lowercase hex Ed25519 signature")
    return value


def validate_signal_message(data, now: int = None) -> dict:
    """The message to queue for a POST /api/signal/send body, or SignalError. Field whitelist, types,
    sizes, ts window, then the sender's signature (checked last, after the cheap checks)."""
    now = now_ms() if now is None else now
    if not isinstance(data, dict):
        raise SignalError(400, "body must be a JSON object")
    unknown = set(data) - SIGNAL_SEND_FIELDS
    if unknown:
        raise SignalError(400, f"unknown field(s): {', '.join(sorted(unknown))}")
    missing = SIGNAL_SEND_FIELDS - set(data)
    if missing:
        raise SignalError(400, f"missing field(s): {', '.join(sorted(missing))}")
    msg = {"to": _signal_pubkey(data["to"], "to"), "from": _signal_pubkey(data["from"], "from")}
    if not isinstance(data["call_id"], str) or not _CALL_ID_RE.fullmatch(data["call_id"]):
        raise SignalError(400, "'call_id' must be 1-64 chars of A-Z a-z 0-9 _ . : -")
    if data["kind"] not in SIGNAL_KINDS:
        raise SignalError(400, f"'kind' must be one of: {', '.join(SIGNAL_KINDS)}")
    if not isinstance(data["payload"], str):
        raise SignalError(400, "'payload' must be a string (SDP, or ICE candidate JSON)")
    if len(data["payload"]) > SIGNAL_MAX_PAYLOAD_CHARS:
        raise SignalError(413, f"'payload' is longer than {SIGNAL_MAX_PAYLOAD_CHARS} characters")
    msg.update(call_id=data["call_id"], kind=data["kind"], payload=data["payload"])
    msg["ts"] = _signal_ts(data["ts"], now)
    msg["sig"] = _signal_sig(data["sig"])
    if not _ed25519_ok(msg["from"], msg["sig"], signal_send_bytes(msg)):
        raise SignalError(401, "bad signature (must be by 'from' over the canonical fields)")
    return msg


class SignalMailbox:
    """In-memory mailboxes keyed by recipient pubkey. Thread-safe; one Condition wakes long-polls."""

    def __init__(self, ttl: float = SIGNAL_TTL_S, clock=time.monotonic):
        self.ttl, self.clock = ttl, clock
        self.cond = threading.Condition()
        self.boxes = {}        # to -> list of queued messages (oldest first)
        self.total = 0
        self.seq = 0           # global, monotonically increasing message cursor
        self.seen = {}         # signature -> forget-after (monotonic): replay guard for send + poll
        self.buckets = {}      # sender pubkey -> [tokens, last_refill]
        self.waiters = 0

    def _purge_locked(self):
        now = self.clock()
        for to in list(self.boxes):
            q = [m for m in self.boxes[to] if m["expires"] > now]
            self.total -= len(self.boxes[to]) - len(q)
            if q:
                self.boxes[to] = q
            else:
                del self.boxes[to]
        if len(self.seen) > SIGNAL_SEEN_MAX // 2:
            self.seen = {s: t for s, t in self.seen.items() if t > now}
        if len(self.buckets) > 10_000:
            self.buckets = {k: b for k, b in self.buckets.items() if now - b[1] < 60}

    def _check_sig_locked(self, sig: str):
        """409 for a signature already used inside the ts window. Ed25519 is deterministic, so
        clients must use a fresh millisecond ts for every request."""
        if self.seen.get(sig, 0) > self.clock():
            raise SignalError(409, "replayed request (this signature was already used)")
        if len(self.seen) >= SIGNAL_SEEN_MAX:
            raise SignalError(503, "signaling replay cache full, try again shortly")

    def _mark_sig_locked(self, sig: str):
        self.seen[sig] = self.clock() + 2 * SIGNAL_TS_WINDOW_MS / 1000.0 + 1

    def _remember_sig_locked(self, sig: str):
        self._check_sig_locked(sig)
        self._mark_sig_locked(sig)

    def _take_token_locked(self, sender: str):
        now = self.clock()
        tokens, last = self.buckets.get(sender, [SIGNAL_RATE_BURST, now])
        tokens = min(SIGNAL_RATE_BURST, tokens + (now - last) * SIGNAL_RATE_PER_S)
        if tokens < 1.0:
            self.buckets[sender] = [tokens, now]
            raise SignalError(429, "rate limited: too many signaling messages from this sender")
        self.buckets[sender] = [tokens - 1.0, now]

    def send(self, msg: dict) -> dict:
        with self.cond:
            self._purge_locked()
            self._check_sig_locked(msg["sig"])
            self._take_token_locked(msg["from"])
            box = self.boxes.get(msg["to"], [])
            if len(box) >= SIGNAL_MAX_PER_RECIPIENT:
                raise SignalError(429, f"recipient mailbox full ({SIGNAL_MAX_PER_RECIPIENT} queued)")
            if self.total >= SIGNAL_MAX_TOTAL:
                raise SignalError(503, "signaling mailbox full, try again shortly")
            self._mark_sig_locked(msg["sig"])
            self.seq += 1
            self.boxes.setdefault(msg["to"], []).append(dict(msg, seq=self.seq, expires=self.clock() + self.ttl))
            self.total += 1
            self.cond.notify_all()
            return {"status": "QUEUED", "seq": self.seq, "expires_in": int(self.ttl)}

    def poll(self, to: str, auth_sig: str, since: int = 0, wait: float = 0.0) -> dict:
        """Removes and returns every queued message for `to` (seq > since); messages with
        seq <= since are dropped as already received. Long-polls up to `wait` seconds when empty."""
        with self.cond:
            self._purge_locked()
            self._remember_sig_locked(auth_sig)
            deadline = self.clock() + max(0.0, min(wait, SIGNAL_MAX_LONG_POLL_S))
            waiting = False
            try:
                while True:
                    box = self.boxes.pop(to, [])
                    self.total -= len(box)
                    out = [m for m in box if m["seq"] > since]
                    remaining = deadline - self.clock()
                    if out or remaining <= 0:
                        break
                    if not waiting:
                        if self.waiters >= SIGNAL_MAX_WAITERS:
                            break
                        self.waiters += 1
                        waiting = True
                    self.cond.wait(remaining)
                    self._purge_locked()
            finally:
                if waiting:
                    self.waiters -= 1
            msgs = [{k: m[k] for k in ("seq", "from", "to", "call_id", "kind", "payload", "ts", "sig")}
                    for m in out]
            cursor = max([since] + [m["seq"] for m in msgs])
            return {"status": "OK", "messages": msgs, "count": len(msgs), "cursor": cursor}

    def stats(self) -> dict:
        with self.cond:
            self._purge_locked()
            return {"queued": self.total, "recipients": len(self.boxes)}


SIGNAL_MAILBOX = SignalMailbox()


def _one(params: dict, name: str, required: bool = True):
    vals = params.get(name)
    if not vals:
        if required:
            raise SignalError(400, f"'{name}' is required")
        return None
    if len(vals) > 1:
        raise SignalError(400, f"'{name}' given more than once")
    return vals[0]


def _int_param(params: dict, name: str, required: bool = True):
    raw = _one(params, name, required)
    if raw is None:
        return None
    if not re.fullmatch(r"\d{1,16}", raw):
        raise SignalError(400, f"'{name}' must be a non-negative integer")
    return int(raw)


def verify_signal_auth(query: str, kind_type: str, key_field: str, allowed: set, now: int = None) -> tuple:
    """(params, pubkey, ts, sig) for a signed GET (poll / ice-config), or SignalError."""
    now = now_ms() if now is None else now
    params = urllib.parse.parse_qs(query or "", keep_blank_values=True)
    unknown = set(params) - allowed
    if unknown:
        raise SignalError(400, f"unknown parameter(s): {', '.join(sorted(unknown))}")
    pubkey = _signal_pubkey(_one(params, key_field), key_field)
    ts = _signal_ts(_int_param(params, "ts"), now)
    sig = _signal_sig(_one(params, "sig"))
    if not _ed25519_ok(pubkey, sig, signal_auth_bytes(kind_type, pubkey, ts)):
        raise SignalError(401, f"bad signature (must be by '{key_field}' over type, {key_field} and ts)")
    return params, pubkey, ts, sig


def signal_send(data) -> tuple:
    try:
        msg = validate_signal_message(data)
        resp = SIGNAL_MAILBOX.send(msg)
        TELEMETRY.inc("signal_sends_ok")
        return resp, 200
    except SignalError as e:
        TELEMETRY.inc("signal_sends_rejected")
        TELEMETRY.inc(f"signal_sends_rejected_{e.status}", touch=False)
        return {"status": "ERROR", "message": e.message}, e.status


def signal_poll(query: str) -> tuple:
    try:
        params, to, _ts, sig = verify_signal_auth(query, SIGNAL_POLL_TYPE, "to", _SIGNAL_POLL_ARGS)
        since = _int_param(params, "since", required=False) or 0
        wait = _int_param(params, "wait", required=False) or 0
        resp = SIGNAL_MAILBOX.poll(to, sig, since=since, wait=float(wait))
        TELEMETRY.inc("signal_polls_ok")
        if resp["count"]:
            TELEMETRY.inc("signal_delivered", resp["count"])
        return resp, 200
    except SignalError as e:
        TELEMETRY.inc("signal_polls_rejected")
        return {"status": "ERROR", "message": e.message}, e.status


def _split_urls(raw: str, schemes: tuple) -> list:
    urls = [u.strip() for u in (raw or "").split(",") if u.strip()]
    bad = [u for u in urls if not u.lower().startswith(schemes) or len(u) > 255 or any(c.isspace() for c in u)]
    if bad:
        raise ValueError(f"bad ICE url(s): {', '.join(bad)}")
    return urls


def turn_rest_credential(secret: str, pubkey: str, ttl: int, now_s: int = None) -> tuple:
    """coturn use-auth-secret / eturnal "secret" scheme (draft-uberti-behave-turn-rest-00):
    username = "<unix expiry>:<pubkey>", credential = base64(HMAC-SHA1(secret, username))."""
    import base64
    now_s = int(time.time()) if now_s is None else now_s
    username = f"{now_s + int(ttl)}:{pubkey}"
    mac = hmac.new(secret.encode("utf-8"), username.encode("utf-8"), hashlib.sha1).digest()
    return username, base64.b64encode(mac).decode("ascii")


def build_ice_config(pubkey: str, env=None) -> dict:
    """ICE servers for a client. The TURN secret never leaves the hub; only a derived, expiring
    credential does. No TURN env -> STUN only."""
    env = os.environ if env is None else env
    try:
        stun = _split_urls(env.get(STUN_URLS_ENV, ""), ("stun:",)) or list(DEFAULT_STUN_URLS)
    except ValueError:
        stun = list(DEFAULT_STUN_URLS)
    servers = [{"urls": stun}]
    resp = {"status": "OK", "ice_servers": servers, "turn": False, "ice_transport_policy": "all"}
    try:
        turn_urls = _split_urls(env.get(TURN_URLS_ENV, ""), ("turn:", "turns:"))
    except ValueError as e:
        resp["warning"] = f"{TURN_URLS_ENV} ignored: {e}"
        return resp
    secret = (env.get(TURN_SECRET_ENV) or "").strip()
    if not turn_urls:
        return resp
    if not secret:
        resp["warning"] = f"{TURN_URLS_ENV} is set but {TURN_SECRET_ENV} is not: TURN disabled"
        return resp
    try:
        ttl = int(env.get(TURN_TTL_ENV, "") or TURN_TTL_DEFAULT)
    except ValueError:
        ttl = TURN_TTL_DEFAULT
    ttl = max(60, min(ttl, 24 * 3600))
    username, credential = turn_rest_credential(secret, pubkey, ttl)
    servers.append({"urls": turn_urls, "username": username, "credential": credential})
    resp.update(turn=True, ttl=ttl, expires_at=int(username.split(":", 1)[0]),
                ice_transport_policy="relay")   # testers can only reach the hub, so relay is the path
    return resp


def signal_ice_config(query: str) -> tuple:
    try:
        _params, pubkey, _ts, sig = verify_signal_auth(query, SIGNAL_ICE_TYPE, "pubkey", _SIGNAL_ICE_ARGS)
        with SIGNAL_MAILBOX.cond:
            SIGNAL_MAILBOX._remember_sig_locked(sig)
        TELEMETRY.inc("signal_ice_config_ok")
        return build_ice_config(pubkey), 200
    except SignalError as e:
        TELEMETRY.inc("signal_ice_config_rejected")
        return {"status": "ERROR", "message": e.message}, e.status


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


# --- Telemetry summary (v8.12.0): GET :5000/api/telemetry/summary ----------------------------------
# Aggregates only, for the Mesh Monitor app. Since-start counters come from TELEMETRY (in memory,
# reset on restart); store-wide numbers are read from SQLite and cached for a few seconds so a
# monitor polling every 10-15 s costs almost nothing. Never included: message/SDP contents, event
# payloads, peer IPs, the hub token, or any full key (pubkeys are cut to 12-char prefixes).
TELEMETRY_SCHEMA = 1
TELEMETRY_DB_CACHE_S = min(60.0, _env_float("OMNI_TELEMETRY_CACHE_S", 5.0))   # tests set 0
_TELEMETRY_DB_CACHE = {"at": 0.0, "value": None}
_TELEMETRY_DB_LOCK = threading.Lock()
DAY_MS = 86_400_000

def _ago(ts):
    """Seconds since a unix time, or None."""
    return None if not ts else round(max(0.0, time.time() - ts), 1)

def _prefix(key) -> str:
    return str(key or "")[:12]

def _store_stats(db_path: Path = None) -> dict:
    """Event-store-wide aggregates (cached TELEMETRY_DB_CACHE_S). Users = distinct signing identities:
    event authors plus payload.app_author_pubkey (the phone key inside a local app's envelope),
    this node's own key excluded. Activity uses each event's signed time."""
    db_path = db_path or _db_path()
    with _TELEMETRY_DB_LOCK:
        cached = _TELEMETRY_DB_CACHE["value"]
        if cached is not None and time.time() - _TELEMETRY_DB_CACHE["at"] < TELEMETRY_DB_CACHE_S:
            return cached
        out = {"total_events": 0, "unsigned_rows": 0, "last_event_ms": None, "db_bytes": 0,
               "by_action": {}, "identities": 0, "active_24h": 0, "active_7d": 0, "bug_reports": 0,
               "first_seen_7d": 0}
        if db_path.exists():
            out["db_bytes"] = sum(f.stat().st_size for f in (db_path, Path(str(db_path) + "-wal"))
                                  if f.exists())
            conn = sqlite3.connect(str(db_path))
            try:
                c = conn.cursor()
                out["total_events"] = c.execute("SELECT COUNT(*) FROM events;").fetchone()[0]
                out["unsigned_rows"] = c.execute(
                    "SELECT COUNT(*) FROM events WHERE signature IS NULL OR signature = '';").fetchone()[0]
                for action, n in c.execute("SELECT action, COUNT(*) FROM events GROUP BY action;"):
                    out["by_action"][str(action)[:64]] = n
                out["bug_reports"] = out["by_action"].get(BUG_REPORT_ACTION, 0)
                last = {}   # identity -> latest signed time (ms)
                first = {}
                for author, payload_json, ts_ms, ts in c.execute(
                        "SELECT author_pubkey, payload_json, ts_ms, timestamp FROM events WHERE id > 0;"):
                    t = int(ts_ms) if ts_ms is not None else int(round(float(ts or 0) * 1000))
                    if out["last_event_ms"] is None or t > out["last_event_ms"]:
                        out["last_event_ms"] = t
                    ids = {author}
                    if payload_json and "app_author_pubkey" in payload_json:
                        try:
                            app_key = json.loads(payload_json).get("app_author_pubkey")
                            if isinstance(app_key, str):
                                ids.add(app_key)
                        except (ValueError, AttributeError):
                            pass
                    for k in ids:
                        if not k or k == STATE.node_id or not _PUBKEY_RE.fullmatch(str(k)):
                            continue
                        last[k] = max(last.get(k, 0), t)
                        first[k] = min(first.get(k, t), t)
            finally:
                conn.close()
            now = now_ms()
            out["identities"] = len(last)
            out["active_24h"] = sum(1 for t in last.values() if now - t <= DAY_MS)
            out["active_7d"] = sum(1 for t in last.values() if now - t <= 7 * DAY_MS)
            out["first_seen_7d"] = sum(1 for t in first.values() if now - t <= 7 * DAY_MS)
        _TELEMETRY_DB_CACHE.update(at=time.time(), value=out)
        return out

def _finance_summary() -> dict:
    """Totals from the TEST credits ledger (replayed and re-verified like /api/credits/*). No
    per-account balances or pubkeys leave the hub here."""
    base = {"state": "ok", "test_only": True, "note": "test credits, no cash value",
            "treasury_fee_bps": TREASURY_FEE_BPS}
    try:
        ledger = replay_credit_ledger()
    except LedgerIntegrityError as e:
        return dict(base, state="integrity_failed", integrity="FAILED", detail=e.reason[:120])
    except Exception as e:
        return dict(base, state="error", detail=f"{type(e).__name__}"[:80])
    entries = ledger["entries"]
    kinds = {k: 0 for k in CREDIT_KINDS}
    issued = moved = fees = 0
    for e in entries:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
        if e["kind"] == "grant":
            issued += e["amount"]
        elif e["kind"] in CREDIT_SIGNED_KINDS:
            moved += e["amount"]
        fees += e["fee"]
    accounts = [a for a in ledger["balances"] if a != CREDIT_TREASURY]
    return dict(base, integrity="VERIFIED", entries=len(entries), accounts=len(accounts),
                welcome_grants=len(ledger["welcomed"]), total_issued=issued, total_transferred=moved,
                fees_collected=fees, entries_by_kind=kinds,
                last_entry_ms=entries[-1]["ts_ms"] if entries else None)

# --- App check-ins (v8.16.0): consent version, app version, crash summary -> telemetry summary ------
# Fills the Mesh Monitor tiles that said "Not wired yet" (consent acceptances, app versions in the field,
# app crash rates). Privacy rules: the phone signs the check-in with its key so nobody can post for it,
# but the hub stores only a salted hash of the key (install id), never the key itself; no device model,
# no IP, no crash messages or stack traces: a crash is counted with an optional short kind
# ("FlutterError", "StateError"). Rows: installs not seen for 90 days and crash buckets older than
# 30 days are deleted; at most 10,000 installs. See Admin/docs/APP_TELEMETRY.md.
CHECKIN_TYPE = "omni.app-checkin.v1"
CHECKIN_FIELDS = {"type", "pubkey", "app", "app_version", "platform", "os_major", "consent_version",
                  "consent_accepted", "crashes", "ts", "sig"}
CHECKIN_PLATFORMS = ("android", "windows", "ios", "linux", "macos", "web")
CHECKIN_WINDOW_MS = 600_000
CHECKIN_MAX_INSTALLS = 10_000
CHECKIN_INSTALL_TTL_MS = 90 * 86_400_000
CRASH_BUCKET_TTL_MS = 30 * 86_400_000
_APP_ID_RE = re.compile(r"[a-z0-9_]{1,32}")
_APP_VERSION_RE = re.compile(r"[0-9A-Za-z.+-]{1,32}")
_CONSENT_VERSION_RE = re.compile(r"[0-9A-Za-z._-]{1,16}")
_CRASH_KIND_RE = re.compile(r"[A-Za-z0-9_.:]{1,64}")
CHECKIN_RATE = SlidingWindowLimiter(2, 60.0)     # per install: a check-in on start + one retry
CHECKIN_LOCK = threading.Lock()


def install_id(pubkey: str) -> str:
    """Salted, truncated hash of the app key: stable per install, not the key, not linkable to events
    without knowing the key."""
    return hashlib.sha256(b"omni-checkin-v1:" + bytes.fromhex(pubkey)).hexdigest()[:20]


def validate_checkin(data, now: int = None) -> dict:
    now = now_ms() if now is None else now
    if not isinstance(data, dict):
        raise ValueError("body must be a JSON object")
    unknown = set(data) - CHECKIN_FIELDS
    if unknown:
        raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))} (no device ids, names or messages)")
    if data.get("type") != CHECKIN_TYPE:
        raise ValueError(f"'type' must be {CHECKIN_TYPE}")
    pk = data.get("pubkey")
    if not isinstance(pk, str) or not _PUBKEY_RE.fullmatch(pk):
        raise ValueError("'pubkey' must be a 64-char lowercase hex Ed25519 public key")
    for name, rx in (("app", _APP_ID_RE), ("app_version", _APP_VERSION_RE)):
        if not isinstance(data.get(name), str) or not rx.fullmatch(data[name]):
            raise ValueError(f"'{name}' is missing or malformed")
    if data.get("platform") not in CHECKIN_PLATFORMS:
        raise ValueError(f"'platform' must be one of {', '.join(CHECKIN_PLATFORMS)}")
    if "os_major" in data and (not isinstance(data["os_major"], int) or isinstance(data["os_major"], bool)
                               or not 0 <= data["os_major"] <= 99):
        raise ValueError("'os_major' must be an integer 0-99 (e.g. Android 15 -> 15)")
    cv = data.get("consent_version")
    if cv is not None and (not isinstance(cv, str) or not _CONSENT_VERSION_RE.fullmatch(cv)):
        raise ValueError("'consent_version' must be null or 1-16 chars")
    if not isinstance(data.get("consent_accepted"), bool):
        raise ValueError("'consent_accepted' must be true or false")
    cr = data.get("crashes")
    if cr is not None:
        if not isinstance(cr, dict) or set(cr) - {"count", "last_kind"} or "count" not in cr:
            raise ValueError("'crashes' must be {\"count\": n, \"last_kind\"?: \"ExceptionType\"}")
        if not isinstance(cr["count"], int) or isinstance(cr["count"], bool) or not 0 <= cr["count"] <= 1000:
            raise ValueError("'crashes.count' must be 0-1000 (crashes since the last check-in)")
        if "last_kind" in cr and (not isinstance(cr["last_kind"], str) or not _CRASH_KIND_RE.fullmatch(cr["last_kind"])):
            raise ValueError("'crashes.last_kind' must be an exception type name only (no message, no stack)")
    ts = data.get("ts")
    if not isinstance(ts, int) or isinstance(ts, bool):
        raise ValueError("'ts' must be an integer (milliseconds)")
    sig = data.get("sig")
    if not isinstance(sig, str) or not _USER_SIG_RE.fullmatch(sig):
        raise ValueError("'sig' must be a 128-char lowercase hex Ed25519 signature")
    if abs(now - ts) > CHECKIN_WINDOW_MS:
        raise PermissionError("stale or future 'ts' (must be within 10 minutes of the hub clock)")
    if not _ed25519_ok(pk, sig, card_signing_bytes(data)):
        raise PermissionError("bad signature: must be by 'pubkey' over every field except sig")
    return data


def _checkins_db():
    conn = sqlite3.connect(str(_db_path()), timeout=10.0)
    conn.execute("CREATE TABLE IF NOT EXISTS app_checkins (install TEXT NOT NULL, app TEXT NOT NULL, "
                 "app_version TEXT NOT NULL, platform TEXT NOT NULL, os_major INTEGER, consent_version TEXT, "
                 "consent_accepted INTEGER NOT NULL, first_seen_ms INTEGER NOT NULL, last_seen_ms INTEGER NOT NULL, "
                 "PRIMARY KEY (install, app))")
    conn.execute("CREATE TABLE IF NOT EXISTS app_crashes (day TEXT NOT NULL, app TEXT NOT NULL, "
                 "app_version TEXT NOT NULL, kind TEXT NOT NULL, count INTEGER NOT NULL, "
                 "PRIMARY KEY (day, app, app_version, kind))")
    return conn


def app_checkin(data) -> tuple:
    try:
        c = validate_checkin(data)
    except PermissionError as e:
        TELEMETRY.inc("app_checkins_rejected")
        return {"status": "ERROR", "message": str(e)}, 401
    except ValueError as e:
        TELEMETRY.inc("app_checkins_rejected")
        return {"status": "ERROR", "message": str(e)}, 400
    inst = install_id(c["pubkey"])
    if not CHECKIN_RATE.allow(inst + ":" + c["app"]):
        return {"status": "ERROR", "message": "rate limited: one check-in per app start"}, 429
    now = now_ms()
    day = time.strftime("%Y-%m-%d", time.gmtime(now / 1000))
    crashes = (c.get("crashes") or {}).get("count", 0)
    with CHECKIN_LOCK:
        conn = _checkins_db()
        try:
            conn.execute("DELETE FROM app_checkins WHERE last_seen_ms < ?", (now - CHECKIN_INSTALL_TTL_MS,))
            cutoff = time.strftime("%Y-%m-%d", time.gmtime((now - CRASH_BUCKET_TTL_MS) / 1000))
            conn.execute("DELETE FROM app_crashes WHERE day < ?", (cutoff,))
            known = conn.execute("SELECT 1 FROM app_checkins WHERE install = ? AND app = ?", (inst, c["app"])).fetchone()
            if not known and conn.execute("SELECT COUNT(*) FROM app_checkins").fetchone()[0] >= CHECKIN_MAX_INSTALLS:
                return {"status": "ERROR", "message": "check-in table full"}, 503
            conn.execute("INSERT INTO app_checkins (install, app, app_version, platform, os_major, consent_version, "
                         "consent_accepted, first_seen_ms, last_seen_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                         "ON CONFLICT(install, app) DO UPDATE SET app_version = excluded.app_version, "
                         "platform = excluded.platform, os_major = excluded.os_major, "
                         "consent_version = excluded.consent_version, consent_accepted = excluded.consent_accepted, "
                         "last_seen_ms = excluded.last_seen_ms",
                         (inst, c["app"], c["app_version"], c["platform"], c.get("os_major"),
                          c.get("consent_version"), int(c["consent_accepted"]), now, now))
            if crashes:
                kind = (c.get("crashes") or {}).get("last_kind", "unknown")
                conn.execute("INSERT INTO app_crashes (day, app, app_version, kind, count) VALUES (?, ?, ?, ?, ?) "
                             "ON CONFLICT(day, app, app_version, kind) DO UPDATE SET count = count + excluded.count",
                             (day, c["app"], c["app_version"], kind, crashes))
            conn.commit()
        finally:
            conn.close()
    TELEMETRY.inc("app_checkins_ok")
    return {"status": "OK", "install_id": inst, "recorded": {"crashes": crashes}}, 200


def app_telemetry_summary(db_path: Path = None) -> tuple:
    """(users_part, services_part) for /api/telemetry/summary. Aggregates only."""
    db_path = db_path or _db_path()
    empty_u = {"installs": 0, "active_24h": 0, "active_7d": 0, "consent": {"accepted": 0, "not_accepted": 0,
               "by_version": {}}, "app_versions": {}, "platforms": {}, "basis": "signed app check-ins "
               "(POST /api/telemetry/app-checkin), one row per install+app, 90-day retention"}
    empty_s = {"last_24h": 0, "last_7d": 0, "by_app": {}, "top_kinds": {}, "basis": "crash counts reported in "
               "app check-ins (no messages or stacks), daily buckets, 30-day retention"}
    if not db_path.exists():
        return empty_u, empty_s
    now = now_ms()
    conn = sqlite3.connect(str(db_path))
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "app_checkins" not in tables:
            return empty_u, empty_s
        rows = conn.execute("SELECT install, app, app_version, platform, consent_version, consent_accepted, "
                            "last_seen_ms FROM app_checkins WHERE last_seen_ms >= ?",
                            (now - CHECKIN_INSTALL_TTL_MS,)).fetchall()
        crash_rows = conn.execute("SELECT day, app, kind, count FROM app_crashes").fetchall() \
            if "app_crashes" in tables else []
    finally:
        conn.close()
    u = json.loads(json.dumps(empty_u))
    installs = {r[0] for r in rows}
    u["installs"] = len(installs)
    u["active_24h"] = len({r[0] for r in rows if now - r[6] <= 86_400_000})
    u["active_7d"] = len({r[0] for r in rows if now - r[6] <= 7 * 86_400_000})
    latest = {}
    for r in rows:   # per install, the most recent check-in decides consent
        if r[0] not in latest or r[6] > latest[r[0]][6]:
            latest[r[0]] = r
    for r in latest.values():
        u["consent"]["accepted" if r[5] else "not_accepted"] += 1
        if r[4]:
            u["consent"]["by_version"][r[4]] = u["consent"]["by_version"].get(r[4], 0) + 1
    for r in rows:
        av = u["app_versions"].setdefault(r[1], {})
        av[r[2]] = av.get(r[2], 0) + 1
        u["platforms"][r[3]] = u["platforms"].get(r[3], 0) + 1
    s = json.loads(json.dumps(empty_s))
    today = time.strftime("%Y-%m-%d", time.gmtime(now / 1000))
    week = {time.strftime("%Y-%m-%d", time.gmtime((now - i * 86_400_000) / 1000)) for i in range(7)}
    for day, app, kind, n in crash_rows:
        if day in week:
            s["last_7d"] += n
            s["by_app"][app] = s["by_app"].get(app, 0) + n
            s["top_kinds"][kind] = s["top_kinds"].get(kind, 0) + n
        if day == today:
            s["last_24h"] += n
    s["top_kinds"] = dict(sorted(s["top_kinds"].items(), key=lambda kv: -kv[1])[:10])
    s["last_24h_note"] = "today's UTC bucket"
    return u, s

def build_telemetry_summary() -> dict:
    counts, last = TELEMETRY.snapshot()
    c = lambda k: counts.get(k, 0)
    now = time.time()
    with STATE.lock:
        peers = [p for p in STATE.active_peers.values() if now - p["last_seen"] < 15.0]
        peer_prefixes = sorted({_prefix(p.get("node_id")) for p in peers if p.get("node_id")})
        omnimind_age = (now - STATE.omnimind_received_at) if STATE.omnimind_telemetry is not None else None
        last_catchup = STATE.last_catchup
    sig = SIGNAL_MAILBOX.stats()
    turn_urls = os.environ.get(TURN_URLS_ENV, "").strip()
    turn_secret = os.environ.get(TURN_SECRET_ENV, "").strip()
    store = _store_stats()

    catchup = None
    if last_catchup and last_catchup.get("status") == "OK":
        runs = last_catchup.get("peers", [])
        catchup = {"at_ago_s": _ago(last_catchup.get("at")), "peers": len(runs),
                   "errors": sum(1 for r in runs if r.get("error")),
                   **{k: sum(int(r.get(k) or 0) for r in runs)
                      for k in ("need", "have", "stored", "rejected", "pushed", "push_failed", "rounds")}}
    p2p_last = max([last.get(k) or 0 for k in ("p2p_sync_requests", "events_stored_peer")] or [0]) or None

    protocols = [
        {"id": "tcp_api", "name": f"TCP app API (:{TELEMETRY_PORT} telemetry, :{CONTINUITY_IPC_PORT} events)", "state": "up",
         "listen": hub_listen_hosts(), "ports": [TELEMETRY_PORT, CONTINUITY_IPC_PORT],
         "remote_hub": HUB_REMOTE, "last_seen_ago_s": _ago(max(last.get("api_requests_loopback") or 0,
                                                               last.get("api_requests_remote") or 0) or None),
         "counts": {"loopback_requests": c("api_requests_loopback"), "remote_requests": c("api_requests_remote")}},
        {"id": "p2p_sync", "name": "P2P event sync (HTTP :%d /p2p/sync)" % P2P_SYNC_PORT, "state": "up",
         "listen": [P2P_HOST], "ports": [P2P_SYNC_PORT], "last_seen_ago_s": _ago(p2p_last),
         "counts": {"requests": c("p2p_sync_requests"), "events_from_peers": c("events_stored_peer"),
                    "relay_ok": c("relay_ok"), "relay_failed": c("relay_failed"),
                    "rejected_mesh": c("p2p_rejected_mesh")}},
        {"id": "udp_discovery", "name": "UDP LAN discovery beacons (:%d)" % UDP_DISCOVERY_PORT,
         "state": "up" if STATE.udp_listener == "listening" else "down", "detail": STATE.udp_listener,
         "ports": [UDP_DISCOVERY_PORT], "last_seen_ago_s": _ago(last.get("beacons_accepted")),
         "last_sent_ago_s": _ago(last.get("beacons_sent")), "active_peers": len(peers),
         "peer_pubkey_prefixes": peer_prefixes[:32], "require_signed": REQUIRE_SIGNED_BEACONS,
         "counts": {"sent": c("beacons_sent"), "accepted": c("beacons_accepted"),
                    "rejected_signature": c("beacons_rejected_signature"),
                    "rejected_mesh": c("beacons_rejected_mesh")}},
        {"id": "negentropy", "name": "Catch-up sync (negentropy v1)",
         "state": "idle" if catchup is None else ("degraded" if catchup["errors"] else "up"),
         "static_peers": len(STATE.sync_peers), "interval_s": _env_float(CATCHUP_INTERVAL_ENV, 60.0),
         "last_run": catchup,
         "last_seen_ago_s": _ago(max(last.get("catchup_served_reconcile") or 0,
                                     last_catchup.get("at") if last_catchup and last_catchup.get("at") else 0) or None),
         "counts": {"served_reconcile": c("catchup_served_reconcile"), "served_events": c("catchup_served_events"),
                    "denied_unknown_peer": c("catchup_denied_unknown_peer")}},
        {"id": "signaling", "name": "OmniCast signaling mailbox (memory only)", "state": "up",
         "queued": sig["queued"], "recipients": sig["recipients"], "ttl_s": int(SIGNAL_TTL_S),
         "last_seen_ago_s": _ago(max(last.get("signal_sends_ok") or 0, last.get("signal_polls_ok") or 0) or None),
         "counts": {"sends_ok": c("signal_sends_ok"), "sends_rejected": c("signal_sends_rejected"),
                    "polls_ok": c("signal_polls_ok"), "delivered": c("signal_delivered"),
                    "ice_config_ok": c("signal_ice_config_ok")}},
        {"id": "turn", "name": "TURN relay credentials (ice-config)",
         "state": "configured" if (turn_urls and turn_secret) else "off",
         "configured": bool(turn_urls and turn_secret),
         "detail": None if (turn_urls and turn_secret) else (
             f"{TURN_URLS_ENV} set but {TURN_SECRET_ENV} missing" if turn_urls else "STUN only"),
         "last_seen_ago_s": _ago(last.get("signal_ice_config_ok"))},
    ]

    hub_token_age = None
    if HUB_REMOTE:
        try:
            hub_token_age = round(now - hub_token_path().stat().st_mtime, 1)
        except OSError:
            hub_token_age = None
    rejected_sig_by_code = {k.rsplit("_", 1)[1]: v for k, v in counts.items()
                            if k.startswith("signal_sends_rejected_")}
    security = {
        "events_stored_local_signed": c("events_stored_local"),
        "events_verified_from_peers": c("events_stored_peer"),
        "events_rejected_signature": c("events_rejected_signature"),
        "events_rejected_untrusted": c("events_rejected_untrusted"),
        "events_rejected_invalid": c("events_rejected_invalid"),
        "events_duplicate": c("events_duplicate"),
        "last_signature_reject_ago_s": _ago(last.get("events_rejected_signature")),
        "signal_sends_rejected": c("signal_sends_rejected"),
        "signal_sends_rejected_by_status": rejected_sig_by_code,
        "signal_polls_rejected": c("signal_polls_rejected"),
        "beacons_rejected_signature": c("beacons_rejected_signature"),
        "bearer_auth_failures": c("bearer_auth_failures"),
        "last_bearer_failure_ago_s": _ago(last.get("bearer_auth_failures")),
        "remote_denied_loopback_only": c("api_denied_loopback_only"),
        "trusted_keys_allowlist": None if STATE.trusted_keys is None else len(STATE.trusted_keys),
        "remote_hub": HUB_REMOTE,
        "hub_token_age_s": hub_token_age,
        "unsigned_rows_in_store": store["unsigned_rows"],
    }
    users = {
        "identities_seen": store["identities"], "active_24h": store["active_24h"],
        "active_7d": store["active_7d"], "new_7d": store["first_seen_7d"],
        "bug_reports": store["bug_reports"],
        "basis": "distinct signing pubkeys in stored events (author or app_author_pubkey), "
                 "this node excluded; activity by signed event time",
    }
    try:
        users["app_checkins"], app_crashes = app_telemetry_summary()
    except Exception as e:
        users["app_checkins"], app_crashes = {"state": "error", "detail": type(e).__name__}, {"state": "error"}
    services = {
        "app_crashes": app_crashes,
        "daemon_version": VERSION, "uptime_seconds": round(now - STATE.start_time, 1),
        "node_id_prefix": _prefix(STATE.node_id), "mesh_id": STATE.mesh_id,
        "event_store": {"total_events": store["total_events"], "db_bytes": store["db_bytes"],
                        "last_event_ago_s": None if store["last_event_ms"] is None
                        else round(max(0, now_ms() - store["last_event_ms"]) / 1000.0, 1),
                        "events_by_action": dict(sorted(store["by_action"].items(),
                                                        key=lambda kv: -kv[1])[:20])},
        "omnimind_agent": {"live": omnimind_age is not None and omnimind_age < OMNIMIND_STALE_SECONDS,
                           "last_report_ago_s": None if omnimind_age is None else round(omnimind_age, 1)},
    }
    return {"status": "OK", "schema": TELEMETRY_SCHEMA, "version": VERSION, "generated_at_ms": now_ms(),
            "counters_since_ms": int(STATE.start_time * 1000),
            "counters_note": "since-start counters are in memory and reset when the daemon restarts",
            "protocols": protocols, "security": security, "finance": _finance_summary(),
            "users": users, "services": services}

class BodyError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def read_request_body(handler, max_bytes: int) -> bytes:
    """The raw request body, from Content-Length or "Transfer-Encoding: chunked" (RFC 9112 7.1).
    No body at all -> b"". Raises BodyError(413) past max_bytes and BodyError(400) for a malformed
    length or chunk framing. Trailers after the last chunk are read and ignored."""
    te = (handler.headers.get("Transfer-Encoding") or "").strip().lower()
    if te:
        if te.split(",")[-1].strip() != "chunked":
            raise BodyError(400, f"unsupported Transfer-Encoding: {te}")
        out = bytearray()
        while True:
            line = handler.rfile.readline(1024)
            if not line.endswith(b"\n"):
                raise BodyError(400, "malformed chunk size line")
            size_txt = line.split(b";", 1)[0].strip()
            if not re.fullmatch(rb"[0-9A-Fa-f]{1,8}", size_txt):
                raise BodyError(400, "malformed chunk size")
            size = int(size_txt, 16)
            if size == 0:
                for _ in range(64):   # optional trailer fields, then the empty line
                    t = handler.rfile.readline(8192)
                    if t in (b"\r\n", b"\n", b""):
                        break
                return bytes(out)
            if len(out) + size > max_bytes:
                raise BodyError(413, f"body too large (max {max_bytes} bytes)")
            chunk = handler.rfile.read(size)
            if len(chunk) != size or handler.rfile.readline(8) not in (b"\r\n", b"\n"):
                raise BodyError(400, "truncated chunk")
            out += chunk
    raw = handler.headers.get("Content-Length")
    if raw is None or raw.strip() == "":
        return b""
    try:
        n = int(raw.strip())
    except ValueError:
        raise BodyError(400, "Content-Length is not a number")
    if n < 0:
        raise BodyError(400, "Content-Length is negative")
    if n > max_bytes:
        raise BodyError(413, f"body too large (max {max_bytes} bytes)")
    data = handler.rfile.read(n) if n else b""
    if len(data) != n:
        raise BodyError(400, "body shorter than Content-Length")
    return data


def read_json_body(handler, max_bytes: int, allow_empty: bool = False):
    """Parsed JSON body. Raises BodyError (400 empty/invalid, 413 too large)."""
    raw = read_request_body(handler, max_bytes)
    if not raw.strip():
        if allow_empty:
            return None
        raise BodyError(400, "empty request body: send a JSON object (Content-Length or chunked)")
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise BodyError(400, "body must be valid UTF-8 JSON")


def _is_loopback(ip: str) -> bool:
    return ip in ("127.0.0.1", "::1", "::ffff:127.0.0.1") or ip.startswith("127.")

def remote_gate(handler, method: str, path: str) -> bool:
    """True if the request may proceed. Loopback: always (unchanged behavior). Non-loopback: only
    with remote hub enabled, an allowed path and a valid bearer token; otherwise sends 403/401."""
    if _is_loopback(handler.client_address[0]):
        TELEMETRY.inc("api_requests_loopback")
        return True
    allowed = REMOTE_POST_PATHS if method == "POST" else REMOTE_GET_PATHS
    if not HUB_REMOTE or STATE.hub_token is None or path not in allowed:
        TELEMETRY.inc("api_denied_loopback_only")
        _deny(handler, 403, "loopback only")
        return False
    if not check_bearer(handler.headers.get("Authorization"), STATE.hub_token):
        TELEMETRY.inc("bearer_auth_failures")
        _deny(handler, 401, "missing or invalid bearer token")
        return False
    TELEMETRY.inc("api_requests_remote")
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

def _via(handler) -> str:
    return "loopback" if _is_loopback(handler.client_address[0]) else "remote_hub"

# Routes added from v8.13.0 on: path -> fn(handler, query) / (max_bytes, fn(handler, body)).
# Same gate as every other :5000 path (remote_gate: loopback, or REMOTE_*_PATHS + bearer token).
USER_GET_ROUTES = {
    "/api/profile": lambda h, q: get_profile(q),
    "/api/profile/list": lambda h, q: list_profiles(q),
    "/api/hub/card": lambda h, q: (hub_card(), 200) if not q else ({"status": "ERROR", "message": "no parameters accepted"}, 400),
    "/api/invites/redeem": lambda h, q: invites_redeem(q, h.client_address[0]),
    "/api/social/thread": lambda h, q: social_thread(q),
    "/api/social/counts": lambda h, q: social_counts(q),
}
USER_POST_ROUTES = {
    "/api/profile/update": (USER_EVENT_MAX_BYTES, lambda h, d: store_user_event(d, {PROFILE_ACTION: validate_profile}, _via(h))),
    "/api/contacts/verify": (8 * 1024, lambda h, d: contacts_verify(d)),
    "/api/invites/create": (8 * 1024, lambda h, d: invites_create(d)),
    "/api/social/comment": (USER_EVENT_MAX_BYTES, lambda h, d: store_user_event(d, {COMMENT_ACTION: validate_comment}, _via(h))),
    "/api/social/react": (USER_EVENT_MAX_BYTES, lambda h, d: store_user_event(d, {REACTION_ACTION: validate_reaction}, _via(h))),
    "/api/telemetry/app-checkin": (4 * 1024, lambda h, d: app_checkin(d)),
}


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
        data, ok = self._read_small_json(BUG_REPORT_MAX_BYTES)
        if not ok:
            return
        via = "loopback" if _is_loopback(self.client_address[0]) else "remote_hub"
        try:
            resp, status = store_bug_report(data, via=via)
        except Exception as e:
            resp, status = {"status": "ERROR", "message": f"could not store bug report: {e}"}, 500
        self._send_json(status, resp)

    def _read_small_json(self, max_bytes: int):
        """(data, ok). Content-Length or chunked body (v8.12.1). Sends the error itself when not ok:
        411 when there is no body at all (same answer as before for a missing Content-Length),
        413 too large, 400 malformed."""
        try:
            raw = read_request_body(self, max_bytes)
        except BodyError as e:
            if e.status == 413:
                self.close_connection = True   # rest of the oversized body is never read
            self._send_json(e.status, {"status": "ERROR", "message": e.message})
            return None, False
        if not raw.strip():
            self._send_json(411, {"status": "ERROR", "message": "request body required (Content-Length or chunked)"})
            return None, False
        try:
            return json.loads(raw.decode("utf-8")), True
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, {"status": "ERROR", "message": "body must be valid UTF-8 JSON"})
            return None, False

    def _credits_call(self, fn, *args):
        """Runs a credits function and maps ledger tamper/corruption to 409. Non-loopback callers only get
        here on /api/credits/send, /balance and /history (remote hub + bearer token, v8.15.0);
        /api/credits/transfer and /grant are not in REMOTE_*_PATHS, so remote_gate refused them."""
        try:
            resp, status = fn(*args)
        except LedgerIntegrityError as e:
            resp, status = {"status": "ERROR", "message": str(e), "integrity": "FAILED",
                            "event_id": e.event_id}, 409
        except Exception as e:
            resp, status = {"status": "ERROR", "message": f"credits ledger error: {e}"}, 500
        self._send_json(status, resp)

    def do_GET(self):
        path, _, query = self.path.partition("?")
        # Loopback: open as before. Non-loopback: remote hub on + bearer token, else 403/401.
        if not remote_gate(self, "GET", path):
            return
        if path == "/api/credits/balance":
            params = urllib.parse.parse_qs(query or "", keep_blank_values=True)
            self._credits_call(credits_balance, (params.get("pubkey") or [""])[-1],
                               _is_loopback(self.client_address[0]))
            return
        if path == "/api/credits/history":
            self._credits_call(credits_history, query)
            return
        if path == "/api/signal/poll":
            resp, status = signal_poll(query)
            self._send_json(status, resp)
            return
        if path == "/api/signal/ice-config":
            resp, status = signal_ice_config(query)
            self._send_json(status, resp)
            return
        if path in USER_GET_ROUTES:
            try:
                resp, status = USER_GET_ROUTES[path](self, query)
            except Exception as e:
                resp, status = {"status": "ERROR", "message": f"{path} failed: {type(e).__name__}: {e}"}, 500
            self._send_json(status, resp)
            return
        if path == "/api/telemetry/summary":
            if query:
                self._send_json(400, {"status": "ERROR", "message": "no parameters accepted"})
                return
            try:
                self._send_json(200, build_telemetry_summary())
            except Exception as e:
                self._send_json(500, {"status": "ERROR", "message": f"telemetry summary failed: {type(e).__name__}"})
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
        if self.path == "/api/signal/send":
            data, ok = self._read_small_json(SIGNAL_MAX_BODY_BYTES)
            if ok:
                resp, status = signal_send(data)
                self._send_json(status, resp)
            return
        if self.path in USER_POST_ROUTES:
            max_bytes, fn = USER_POST_ROUTES[self.path]
            data, ok = self._read_small_json(max_bytes)
            if ok:
                try:
                    resp, status = fn(self, data)
                except Exception as e:
                    resp, status = {"status": "ERROR", "message": f"{self.path} failed: {type(e).__name__}: {e}"}, 500
                self._send_json(status, resp)
            return
        if self.path == "/api/credits/send":
            data, ok = self._read_small_json(CREDIT_BODY_MAX_BYTES)
            if ok:
                self._credits_call(credits_send, data)
            return
        if self.path in ("/api/credits/transfer", "/api/credits/grant"):
            data, ok = self._read_small_json(CREDIT_BODY_MAX_BYTES)
            if ok:
                self._credits_call(credits_transfer if self.path.endswith("transfer") else credits_grant, data)
            return
        if self.path == "/api/events/append":
            # v8.12.1: Content-Length or chunked; an empty body is refused instead of being stored
            # as an empty USER_ACTION event (the KickBack "posts never show up" bug).
            try:
                data = read_json_body(self, MAX_PAYLOAD_SIZE)
            except BodyError as e:
                if e.status == 413:
                    self.close_connection = True
                TELEMETRY.inc("append_rejected_body")
                self._send_json(e.status, {"status": "ERROR", "message": e.message})
                return
            if not isinstance(data, dict) or not data:
                TELEMETRY.inc("append_rejected_body")
                self._send_json(400, {"status": "ERROR", "message": "body must be a non-empty JSON object"})
                return
            try:
                if str(data.get("action", "")).strip() == CREDIT_ACTION:
                    # Ledger entries only come from /api/credits/*, where overdraft checks run.
                    resp_data, status_code = {"status": "ERROR", "message":
                                              "credit_entry events can only be written via /api/credits/*"}, 403
                elif str(data.get("action", "")).strip() in RESERVED_USER_ACTIONS:
                    # Schema-checked, person-signed types have their own endpoint (v8.13.0+).
                    act = str(data.get("action", "")).strip()
                    resp_data, status_code = {"status": "ERROR", "message":
                                              f"{act} events can only be written via {RESERVED_USER_ACTIONS[act]}"}, 403
                elif _is_loopback(self.client_address[0]):
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
        TELEMETRY.inc("p2p_rejected_mesh")
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
                TELEMETRY.inc("catchup_denied_unknown_peer")
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
            TELEMETRY.inc("catchup_served_reconcile" if self.path == "/p2p/reconcile" else "catchup_served_events")
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
            TELEMETRY.inc("p2p_sync_requests")

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
    print(f"[✓] Omni Credits (TEST):  GET http://{IPC_HOST}:{CONTINUITY_IPC_PORT}/api/credits/balance?pubkey=  "
          f"(loopback only, fee {TREASURY_FEE_BPS} bps)")
    turn_on = bool(os.environ.get(TURN_URLS_ENV, "").strip() and os.environ.get(TURN_SECRET_ENV, "").strip())
    print(f"[✓] OmniCast signaling:   POST http://{IPC_HOST}:{CONTINUITY_IPC_PORT}/api/signal/send  (poll: GET /api/signal/poll; "
          f"memory only, {int(SIGNAL_TTL_S)}s TTL; ICE: {'STUN + TURN' if turn_on else 'STUN only (set OMNI_TURN_URLS + OMNI_TURN_SECRET for TURN)'})")
    print(f"[✓] Telemetry summary:    GET http://{IPC_HOST}:{CONTINUITY_IPC_PORT}/api/telemetry/summary  (aggregates only)")
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
