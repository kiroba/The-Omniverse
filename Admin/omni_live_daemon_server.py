#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE LIVE LOCAL DAEMON ENGINE [v8.5.0 - Hardened Mesh Spine]
==============================================================================
Architecture:
- Port 9100 (127.0.0.1): Node Health Telemetry & Agent Cache
- Port 5000 (127.0.0.1): Local IPC Event Gateway (loopback-only bind; GET /api/events/feed lists events)
- Port 5005 (0.0.0.0): P2P Network Sync Gateway (Signed Envelopes, Hash Verified)
- Port 9101 (0.0.0.0): UDP Subnet Discovery Broadcaster/Listener (Advertises 5005)
Mesh name (OMNI_MESH_ID, default "dev"): beacons and /p2p/sync requests carry it; other meshes are ignored/403.
==============================================================================
"""

import os
import re
import sys
import time
import json
import sqlite3
import hashlib
from omni_signing import (load_or_create_key, pubkey_hex, sign_event, verify_event,
                          canonical_event_bytes, now_ms, load_trusted_keys, is_trusted,
                          TRUSTED_KEYS_ENV)
import threading
import socket
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

VERSION = "8.6.0"
TELEMETRY_PORT = 9100
CONTINUITY_IPC_PORT = 5000
P2P_SYNC_PORT = 5005
UDP_DISCOVERY_PORT = 9101
OMNIMIND_MAX_PAYLOAD = 64 * 1024
OMNIMIND_STALE_SECONDS = 15.0

IPC_HOST = "127.0.0.1"
P2P_HOST = "0.0.0.0"
MAX_PAYLOAD_SIZE = 5 * 1024 * 1024  # 5 MB Strict Cap
# Set OMNI_LEGACY_FLOAT_TS=1 while any peer still runs a pre-8.5.1 daemon: those peers only
# understand float "timestamp", so events this node stamps itself would 401 there.
LEGACY_FLOAT_TS = os.environ.get("OMNI_LEGACY_FLOAT_TS", "").strip() in ("1", "true", "yes")

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

def process_and_store_event(data: dict, origin_peer: str = None) -> tuple[dict, int]:
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

    db_path = Path.cwd() / "continuity_events.db"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    # Get event_id of latest DB row for true Merkle chaining
    c.execute("SELECT event_id FROM events ORDER BY id DESC LIMIT 1;")
    last_row = c.fetchone()
    expected_prev_hash = last_row[0] if last_row else ("0x" + "0" * 64)

    provided_prev_hash = data.get("previous_hash")
    prev_hash = provided_prev_hash if provided_prev_hash else expected_prev_hash

    # Compute deterministic canonical hash ID
    computed_event_id = compute_canonical_event_id(action, author, payload_obj, prev_hash, timestamp, ts_ms)
    provided_event_id = data.get("event_id")

    # Hash re-verification check
    if provided_event_id and provided_event_id != computed_event_id:
        conn.close()
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
            conn.close()
            return {"status": "ERROR", "message": "Invalid or missing signature"}, 401
        # Valid signature is not enough when an allowlist is configured: the key must be on it.
        if not is_trusted(author, STATE.trusted_keys):
            conn.close()
            return {"status": "ERROR", "message": "Author key is not in this node's trusted-keys allowlist"}, 403

    # Deduplication check
    with STATE.lock:
        if event_id in STATE.seen_event_ids:
            conn.close()
            return {"status": "SUCCESS", "event_id": event_id, "result": "ALREADY_EXISTS"}, 200

    c.execute("SELECT id FROM events WHERE event_id = ?;", (event_id,))
    if c.fetchone():
        with STATE.lock:
            STATE.seen_event_ids.add(event_id)
        conn.close()
        return {"status": "SUCCESS", "event_id": event_id, "result": "ALREADY_EXISTS"}, 200

    # Insert verified event
    c.execute("""
        INSERT INTO events (event_id, action, author_pubkey, previous_hash, timestamp, payload_json, signature, ts_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (event_id, action, author, prev_hash, timestamp, json.dumps(payload_obj), signature, ts_ms))
    conn.commit()
    conn.close()

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

    # Relay to active P2P peers (skipping origin sender)
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
        if origin_peer and (peer_ip == origin_peer or f"{peer_ip}:{P2P_SYNC_PORT}" == origin_peer):
            continue  # Skip relaying back to sender!

        url = f"http://{peer_ip}:{P2P_SYNC_PORT}/p2p/sync"
        try:
            req = urllib.request.Request(url, data=json_bytes, method='POST',
                                         headers={'Content-Type': 'application/json', MESH_HEADER: STATE.mesh_id})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                pass
        except Exception:
            pass

def udp_discovery_broadcaster():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    while True:
        try:
            payload = json.dumps({
                "type": "OMNI_P2P_BEACON",
                "node_id": STATE.node_id,
                "mesh_id": STATE.mesh_id,
                "ip": LOCAL_IP,
                "port": P2P_SYNC_PORT,  # Advertises 5005
                "transport": "UDP_LAN"
            }).encode('utf-8')
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
    peer_port = int(msg.get("port", P2P_SYNC_PORT))
    with STATE.lock:
        STATE.active_peers[peer_ip] = {"ip": peer_ip, "port": peer_port, "last_seen": time.time()}
    return True

def udp_discovery_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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

def _is_loopback(ip: str) -> bool:
    return ip in ("127.0.0.1", "::1", "::ffff:127.0.0.1") or ip.startswith("127.")


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
                "uptime_seconds": uptime
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

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path == "/api/events/feed":
            # The IPC server only binds 127.0.0.1; this check keeps the feed loopback-only even if
            # someone rebinds IPC_HOST.
            if not _is_loopback(self.client_address[0]):
                self._send_json(403, {"status": "ERROR", "message": "loopback only"})
                return
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
        if self.path == "/api/events/append":
            content_len = int(self.headers.get("Content-Length", 0))
            if content_len > MAX_PAYLOAD_SIZE:
                self.send_error(413, "Payload Too Large (Max 5MB)")
                return

            post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
            try:
                data = json.loads(post_body)
                resp_data, status_code = process_and_store_event(data, origin_peer=None)
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

    def do_POST(self):
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
    print(f"[✓] P2P Sync Server Bound: http://{P2P_HOST}:{P2P_SYNC_PORT}/p2p/sync")
    print(f"[✓] UDP Subnet Discovery: Listening on port {UDP_DISCOVERY_PORT}...")
    if STATE.trusted_keys is None:
        print(f"[!] WARNING: {TRUSTED_KEYS_ENV} not set: ANY validly signed peer event is accepted.")
    else:
        print(f"[✓] Trusted-keys allowlist: {len(STATE.trusted_keys)} key(s); others get 403")
    print(f"[✓] Event time format: {'legacy float timestamp' if LEGACY_FLOAT_TS else 'int-ms ts'} for events this node stamps")
    print("------------------------------------------------------------------")

    t1 = threading.Thread(target=udp_discovery_broadcaster, daemon=True)
    t2 = threading.Thread(target=udp_discovery_listener, daemon=True)
    t3 = threading.Thread(target=lambda: ThreadingHTTPServer((IPC_HOST, TELEMETRY_PORT), TelemetryHandler).serve_forever(), daemon=True)
    t4 = threading.Thread(target=lambda: ThreadingHTTPServer((IPC_HOST, CONTINUITY_IPC_PORT), ContinuityIPCHandler).serve_forever(), daemon=True)
    t5 = threading.Thread(target=lambda: ThreadingHTTPServer((P2P_HOST, P2P_SYNC_PORT), P2PSyncHandler).serve_forever(), daemon=True)

    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t5.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[✓] Live daemon shut down cleanly.")
        sys.exit(0)

if __name__ == "__main__":
    main()
