#!/usr/bin/env python3
"""
==============================================================================
MULTI-DESKTOP RELAY BFT PATCH CONSENSUS ENGINE [v2.0.0 - Hardened Loopback]
==============================================================================
Security & Behavior:
- Bound strictly to 127.0.0.1:5004 (Loopback IPC)
- Uses ThreadingHTTPServer for concurrent voting
- Enforces 5 MB Content-Length cap
- Calculates Byzantine Fault Tolerant (> 66.7%) consensus on code patch proposals
==============================================================================
"""

import os
import sys
import time
import json
import sqlite3
import hashlib
import threading
import urllib.request
import urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

VERSION = "2.0.0"
BFT_PORT = 5004
IPC_HOST = "127.0.0.1"
DAEMON_EVENT_URL = "http://127.0.0.1:5000/api/events/append"
BFT_THRESHOLD = 0.667  # 66.7% Consensus Approval
MAX_PAYLOAD_SIZE = 5 * 1024 * 1024

class BFTState:
    def __init__(self):
        self.start_time = time.time()
        self.node_id = "0x" + hashlib.sha256(f"bft_validator_{time.time()}_{os.getpid()}".encode()).hexdigest()[:32]
        self.lock = threading.Lock()

STATE = BFTState()

def init_db() -> Path:
    db_path = Path.cwd() / "omni_patch_consensus.db"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("""
        CREATE TABLE IF NOT EXISTS patch_proposals (
            patch_id TEXT PRIMARY KEY,
            patch_sha256 TEXT NOT NULL,
            proposer_node TEXT NOT NULL,
            patch_type TEXT NOT NULL,
            status TEXT NOT NULL,
            approval_votes INTEGER NOT NULL DEFAULT 1,
            rejection_votes INTEGER NOT NULL DEFAULT 0,
            total_validators INTEGER NOT NULL DEFAULT 3,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    return db_path

def propose_patch(raw_data: dict) -> tuple[dict, int]:
    proposer = str(raw_data.get("proposer_node", STATE.node_id)).strip()
    patch_content = str(raw_data.get("patch_content", "")).strip()
    patch_type = str(raw_data.get("patch_type", "BUG_FIX")).strip().upper()

    if not patch_content:
        return {"status": "ERROR", "message": "Missing patch_content"}, 400

    patch_sha256 = "0x" + hashlib.sha256(patch_content.encode("utf-8")).hexdigest()
    patch_id = f"patch_{hashlib.sha256(f'{patch_sha256}_{time.time()}'.encode()).hexdigest()[:16]}"

    db_path = Path.cwd() / "omni_patch_consensus.db"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    now = time.time()

    c.execute("""
        INSERT INTO patch_proposals (patch_id, patch_sha256, proposer_node, patch_type, status, approval_votes, rejection_votes, total_validators, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'VOTING_IN_PROGRESS', 1, 0, 3, ?, ?)
    """, (patch_id, patch_sha256, proposer, patch_type, now, now))
    conn.commit()
    conn.close()

    return {
        "status": "PROPOSED",
        "patch_id": patch_id,
        "patch_sha256": patch_sha256,
        "proposer_node": proposer,
        "current_status": "VOTING_IN_PROGRESS",
        "approval_ratio": 0.333
    }, 200

def vote_on_patch(raw_data: dict) -> tuple[dict, int]:
    patch_id = str(raw_data.get("patch_id", "")).strip()
    validator_node = str(raw_data.get("validator_node", STATE.node_id)).strip()
    approve = bool(raw_data.get("approve", True))

    if not patch_id:
        return {"status": "ERROR", "message": "Missing patch_id"}, 400

    db_path = Path.cwd() / "omni_patch_consensus.db"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    c.execute("SELECT patch_sha256, approval_votes, rejection_votes, total_validators, status FROM patch_proposals WHERE patch_id = ?;", (patch_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {"status": "ERROR", "message": f"Patch '{patch_id}' not found"}, 404

    patch_sha256, approvals, rejections, total_validators, current_status = row
    if current_status == "CONSENSUS_APPROVED":
        conn.close()
        return {"status": "SUCCESS", "patch_id": patch_id, "status": "ALREADY_APPROVED"}, 200

    now = time.time()
    if approve:
        approvals += 1
    else:
        rejections += 1

    ratio = approvals / max(1, total_validators)
    new_status = current_status

    if ratio >= BFT_THRESHOLD:
        new_status = "CONSENSUS_APPROVED"

    c.execute("""
        UPDATE patch_proposals
        SET approval_votes = ?, rejection_votes = ?, status = ?, updated_at = ?
        WHERE patch_id = ?;
    """, (approvals, rejections, new_status, now, patch_id))
    conn.commit()
    conn.close()

    relayed = False
    if new_status == "CONSENSUS_APPROVED":
        event_envelope = {
            "action": "BFT_PATCH_CONSENSUS_APPROVED",
            "author_pubkey": validator_node,
            "payload": {
                "patch_id": patch_id,
                "patch_sha256": patch_sha256,
                "approval_ratio": ratio
            },
            "timestamp": now
        }
        json_bytes = json.dumps(event_envelope, sort_keys=True, separators=(',', ':')).encode("utf-8")
        req = urllib.request.Request(DAEMON_EVENT_URL, data=json_bytes, headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                relayed = (resp.status == 200)
        except Exception:
            relayed = False

    return {
        "status": new_status,
        "patch_id": patch_id,
        "approval_votes": approvals,
        "approval_ratio": round(ratio, 3),
        "daemon_relay": "SUCCESS" if relayed else "LOCAL_SAVED"
    }, 200

class BFTHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/v1/bft/health":
            db_path = Path.cwd() / "omni_patch_consensus.db"
            count = 0
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*) FROM patch_proposals;")
                    count = c.fetchone()[0]
                    conn.close()
                except Exception:
                    pass

            resp_data = {
                "status": "ONLINE",
                "version": VERSION,
                "validator_node_id": STATE.node_id,
                "total_proposals": count,
                "bft_threshold": BFT_THRESHOLD,
                "uptime_seconds": round(time.time() - STATE.start_time, 1)
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
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len > MAX_PAYLOAD_SIZE:
            self.send_error(413, "Payload Too Large (Max 5MB)")
            return

        post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"

        if self.path == "/api/v1/bft/propose":
            try:
                data = json.loads(post_body)
                resp_data, status_code = propose_patch(data)
                body = json.dumps(resp_data).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_error(400, f"Bad Request: {e}")

        elif self.path == "/api/v1/bft/vote":
            try:
                data = json.loads(post_body)
                resp_data, status_code = vote_on_patch(data)
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

def main():
    db_file = init_db()
    print("==================================================================")
    print(f"MULTI-DESKTOP RELAY BFT PATCH CONSENSUS ENGINE [v{VERSION}]")
    print("==================================================================")
    print(f"[✓] Validator ID:   {STATE.node_id}")
    print(f"[✓] SQLite WAL DB:   {db_file}")
    print(f"[✓] Bound Endpoint:  http://{IPC_HOST}:{BFT_PORT}/api/v1/bft/health")
    print("------------------------------------------------------------------")

    server = ThreadingHTTPServer((IPC_HOST, BFT_PORT), BFTHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[✓] BFT Patch Consensus Engine shut down cleanly.")
        sys.exit(0)

if __name__ == "__main__":
    main()
