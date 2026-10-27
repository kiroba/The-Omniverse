#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE LIVE LOCAL DAEMON ENGINE [v8.5.0 - Hardened Mesh Spine]
==============================================================================
Architecture:
- Port 9100 (127.0.0.1): Node Health Telemetry & Agent Cache
- Port 5000 (127.0.0.1): Local IPC Event Gateway (Bearer Token & Host Sanitized)
- Port 5005 (0.0.0.0): P2P Network Sync Gateway (Signed Envelopes, Hash Verified)
- Port 9101 (0.0.0.0): UDP Subnet Discovery Broadcaster/Listener (Advertises 5005)
==============================================================================
"""

import os
import sys
import time
import json
import sqlite3
import hashlib
import threading
import socket
import urllib.request
import urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

VERSION = "8.5.0"
TELEMETRY_PORT = 9100
CONTINUITY_IPC_PORT = 5000
P2P_SYNC_PORT = 5005
UDP_DISCOVERY_PORT = 9101
OMNIMIND_MAX_PAYLOAD = 64 * 1024
OMNIMIND_STALE_SECONDS = 15.0

IPC_HOST = "127.0.0.1"
P2P_HOST = "0.0.0.0"
MAX_PAYLOAD_SIZE = 5 * 1024 * 1024  # 5 MB Strict Cap

class EngineState:
    def __init__(self):
        self.node_id = "0x" + hashlib.sha256(f"node_key_{time.time()}_{os.getpid()}".encode()).hexdigest()[:32]
        self.start_time = time.time()
        self.seen_event_ids = set()
        self.omnimind_telemetry = None   # latest OmniMind agent payload
        self.omnimind_received_at = 0.0
        self.active_peers = {}  # {peer_ip: {"ip": peer_ip, "port": 5005, "last_seen": time.time()}}
        self.rx_bytes = 0
        self.tx_bytes = 0
        self.lock = threading.Lock()

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
            payload_json TEXT DEFAULT '{}'
        );
    """)
    # Migration check for payload_json column
    c.execute("PRAGMA table_info(events);")
    columns = [col[1] for col in c.fetchall()]
    if "payload_json" not in columns:
        c.execute("ALTER TABLE events ADD COLUMN payload_json TEXT DEFAULT '{}';")
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

def compute_canonical_event_id(action: str, author_pubkey: str, payload_obj: dict, previous_hash: str, timestamp: float) -> str:
    canonical_struct = {
        "action": action,
        "author_pubkey": author_pubkey,
        "payload": payload_obj,
        "previous_hash": previous_hash,
        "timestamp": timestamp
    }
    canonical_bytes = json.dumps(canonical_struct, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return "0x" + hashlib.sha256(canonical_bytes).hexdigest()

def process_and_store_event(data: dict, origin_peer: str = None) -> tuple[dict, int]:
    action = str(data.get("action", "USER_ACTION")).strip()
    author = str(data.get("author_pubkey", STATE.node_id)).strip()
    payload_obj = data.get("payload", {})
    if not isinstance(payload_obj, dict):
        payload_obj = {}

    # Extract exact timestamp float
    try:
        timestamp = float(data.get("timestamp", time.time()))
    except (ValueError, TypeError):
        timestamp = time.time()

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
    computed_event_id = compute_canonical_event_id(action, author, payload_obj, prev_hash, timestamp)
    provided_event_id = data.get("event_id")

    # Hash re-verification check
    if provided_event_id and provided_event_id != computed_event_id:
        conn.close()
        return {"status": "ERROR", "message": f"Event hash mismatch. Computed: {computed_event_id}, Provided: {provided_event_id}"}, 400

    event_id = computed_event_id

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
        INSERT INTO events (event_id, action, author_pubkey, previous_hash, timestamp, payload_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (event_id, action, author, prev_hash, timestamp, json.dumps(payload_obj)))
    conn.commit()
    conn.close()

    with STATE.lock:
        STATE.seen_event_ids.add(event_id)

    event_envelope = {
        "event_id": event_id,
        "action": action,
        "author_pubkey": author,
        "previous_hash": prev_hash,
        "timestamp": timestamp,
        "payload": payload_obj
    }

    # Relay to active P2P peers (skipping origin sender)
    threading.Thread(target=relay_event_to_peers, args=(event_envelope, origin_peer), daemon=True).start()

    return {"status": "SUCCESS", "event_id": event_id, "merkle_hash": prev_hash}, 200

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
            req = urllib.request.Request(url, data=json_bytes, headers={'Content-Type': 'application/json'}, method='POST')
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
                "ip": LOCAL_IP,
                "port": P2P_SYNC_PORT,  # Advertises 5005
                "transport": "UDP_LAN"
            }).encode('utf-8')
            sock.sendto(payload, ('<broadcast>', UDP_DISCOVERY_PORT))
        except Exception:
            pass
        time.sleep(3.0)

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
            if msg.get("type") == "OMNI_P2P_BEACON" and msg.get("node_id") != STATE.node_id:
                peer_ip = addr[0]
                peer_port = int(msg.get("port", P2P_SYNC_PORT))
                with STATE.lock:
                    STATE.active_peers[peer_ip] = {"ip": peer_ip, "port": peer_port, "last_seen": time.time()}
        except Exception:
            pass

class TelemetryHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
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
                "local_ip": LOCAL_IP,
                "p2p_sync_port": P2P_SYNC_PORT,
                "active_peers": active_count,
                "peer_ips": peer_ips,
                "uptime_seconds": uptime
            }
            body = json.dumps(resp_data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
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
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
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
            self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
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
                self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_error(400, f"Bad Request: {e}")
        else:
            self.send_error(404, "Endpoint Not Found")

class P2PSyncHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_POST(self):
        if self.path == "/p2p/sync":
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
                self.wfile.write(body)
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
    print(f"[✓] Local Subnet IP:      {LOCAL_IP}")
    print(f"[✓] SQLite WAL Event DB:  {db_file}")
    print(f"[✓] Telemetry API Bound:  http://{IPC_HOST}:{TELEMETRY_PORT}/api/v1/telemetry/node-health")
    print(f"[✓] Local IPC Event API:  http://{IPC_HOST}:{CONTINUITY_IPC_PORT}/api/events/append")
    print(f"[✓] P2P Sync Server Bound: http://{P2P_HOST}:{P2P_SYNC_PORT}/p2p/sync")
    print(f"[✓] UDP Subnet Discovery: Listening on port {UDP_DISCOVERY_PORT}...")
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
