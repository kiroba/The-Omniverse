#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE LIVE LOCAL DAEMON ENGINE [v7.0.0]
Cross-Platform Background Service (Desktop Linux/macOS/Windows & Mobile Termux)
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
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

VERSION = "7.0.0"
TELEMETRY_PORT = 9100
CONTINUITY_PORT = 5000
HOST = "0.0.0.0"

class EngineState:
    def __init__(self):
        self.node_id = "0x" + hashlib.sha256(f"node_key_{time.time()}".encode()).hexdigest()[:32]
        self.rx_bytes = 1024
        self.tx_bytes = 512
        self.start_time = time.time()
        self.active_peers = {}
        self.omnimind_telemetry = {
            "agent_id": "OmniMind_Core_Edge",
            "status": "ACTIVE",
            "current_action": "IDLE",
            "events_processed": 0,
            "mode": "MOBILE_EDGE_DAEMON",
            "active_tasks": []
        }
        self.lock = threading.Lock()

STATE = EngineState()

def auto_detect_network_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP = auto_detect_network_ip()

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
    c.execute("SELECT COUNT(*) FROM events;")
    if c.fetchone()[0] == 0:
        genesis_hash = "0x" + "0" * 64
        c.execute("""
            INSERT INTO events (event_id, action, author_pubkey, previous_hash, timestamp, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("0xgenesis_000", "GENESIS_NODE_INIT", STATE.node_id, genesis_hash, time.time(), json.dumps({"system": "Genesis Node"})))
        conn.commit()
    conn.close()
    return db_path

class TelemetryHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        with STATE.lock:
            uptime = time.time() - STATE.start_time
            node_id = STATE.node_id
            peers = list(STATE.active_peers.keys())

        if self.path == "/api/v1/telemetry/node-health":
            resp_data = {
                "status": "ONLINE",
                "version": VERSION,
                "node_id": node_id,
                "local_ip": LOCAL_IP,
                "active_peers": len(peers),
                "peer_addresses": peers,
                "uptime_seconds": round(uptime, 1)
            }
            body = json.dumps(resp_data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/omnimind/telemetry":
            with STATE.lock:
                resp_data = dict(STATE.omnimind_telemetry)
            body = json.dumps(resp_data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404, "Endpoint Not Found")

    def do_POST(self):
        if self.path in ["/api/omnimind/telemetry", "/api/events/append"]:
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len).decode("utf-8")
            try:
                data = json.loads(post_body)
                with STATE.lock:
                    if "action" in data:
                        STATE.omnimind_telemetry["current_action"] = data["action"]
                    if "agent_id" in data:
                        STATE.omnimind_telemetry["agent_id"] = data["agent_id"]
                    if "payload" in data and isinstance(data["payload"], dict):
                        tasks = STATE.omnimind_telemetry.get("active_tasks", [])
                        tasks.insert(0, data["payload"])
                        STATE.omnimind_telemetry["active_tasks"] = tasks[:5]
                    STATE.omnimind_telemetry["events_processed"] += 1

                resp_data = {"status": "SUCCESS", "message": "Telemetry accepted"}
                body = json.dumps(resp_data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_error(400, f"Bad Request: {e}")
        else:
            self.send_error(404, "Endpoint Not Found")

class ContinuityHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/events/stats":
            db_path = Path.cwd() / "continuity_events.db"
            count = 0
            last_hash = "0x" + "0" * 64
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*), previous_hash FROM events ORDER BY id DESC LIMIT 1;")
                    row = c.fetchone()
                    conn.close()
                    if row and row[0] is not None:
                        count = row[0]
                        last_hash = row[1] if row[1] else last_hash
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
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404, "Endpoint Not Found")

    def do_POST(self):
        if self.path == "/api/events/append":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len).decode("utf-8")
            try:
                data = json.loads(post_body)
                action = data.get("action", "USER_ACTION")
                author = data.get("author_pubkey", STATE.node_id)
                payload_json = json.dumps(data.get("payload", {}))
                
                db_path = Path.cwd() / "continuity_events.db"
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                c.execute("SELECT previous_hash FROM events ORDER BY id DESC LIMIT 1;")
                prev = c.fetchone()
                prev_hash = prev[0] if prev and prev[0] else "0x" + "0" * 64
                
                new_event_id = "0x" + hashlib.sha256(f"{action}_{time.time()}_{prev_hash}".encode()).hexdigest()[:32]
                
                c.execute("""
                    INSERT INTO events (event_id, action, author_pubkey, previous_hash, timestamp, payload_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (new_event_id, action, author, prev_hash, time.time(), payload_json))
                conn.commit()
                conn.close()

                with STATE.lock:
                    STATE.omnimind_telemetry["current_action"] = action
                    STATE.omnimind_telemetry["events_processed"] += 1
                
                resp_data = {"status": "SUCCESS", "event_id": new_event_id, "merkle_hash": prev_hash}
                body = json.dumps(resp_data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_error(400, f"Bad Request: {e}")
        else:
            self.send_error(404, "Endpoint Not Found")

def main():
    db_file = init_db()
    print("==================================================================")
    print(f"OMNIVERSE LIVE LOCAL DAEMON ENGINE [v{VERSION}]")
    print("==================================================================")
    print(f"[✓] Node ID:          {STATE.node_id}")
    print(f"[✓] Local Subnet IP:  {LOCAL_IP}")
    print(f"[✓] Telemetry API:    http://{HOST}:{TELEMETRY_PORT}/api/v1/telemetry/node-health")
    print(f"[✓] Continuity API:   http://{HOST}:{CONTINUITY_PORT}/api/events/append")
    print("==================================================================")

    t1 = threading.Thread(target=lambda: HTTPServer((HOST, TELEMETRY_PORT), TelemetryHandler).serve_forever(), daemon=True)
    t2 = threading.Thread(target=lambda: HTTPServer((HOST, CONTINUITY_PORT), ContinuityHandler).serve_forever(), daemon=True)

    t1.start()
    t2.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    main()
