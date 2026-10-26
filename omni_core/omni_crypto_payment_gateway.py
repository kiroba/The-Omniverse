#!/usr/bin/env python3
"""
==============================================================================
OMNI CRYPTO & PAYMENT GATEWAY MICROSERVICE [v2.0.0 - Hardened Loopback]
==============================================================================
Security Rules:
- Bound strictly to 127.0.0.1:5001 (Loopback IPC only)
- Accepts payment amounts ONLY as positive 64-bit integers (amount_cents > 0)
- Settlement requires HMAC provider signature or loopback webhook secret authorization
- Zero free money: unknown public keys default strictly to 0 XP balance
==============================================================================
"""

import os
import sys
import time
import json
import sqlite3
import hashlib
import hmac
import threading
import socket
import urllib.request
import urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

VERSION = "2.0.0"
PAYMENT_PORT = 5001
IPC_HOST = "127.0.0.1"
DAEMON_EVENT_URL = "http://127.0.0.1:5000/api/events/append"
WEBHOOK_SECRET = "omni_hw_sec_key_2026_99x"
MAX_PAYLOAD_SIZE = 5 * 1024 * 1024

class PaymentGatewayState:
    def __init__(self):
        self.start_time = time.time()
        self.gateway_id = "0x" + hashlib.sha256(f"pay_gw_{time.time()}_{os.getpid()}".encode()).hexdigest()[:32]
        self.lock = threading.Lock()

STATE = PaymentGatewayState()

def init_db() -> Path:
    db_path = Path.cwd() / "omni_payments.db"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("""
        CREATE TABLE IF NOT EXISTS payment_intents (
            intent_id TEXT PRIMARY KEY,
            user_pubkey TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            currency TEXT NOT NULL,
            hmac_signature TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS xp_reward_balances (
            user_pubkey TEXT PRIMARY KEY,
            xp_balance INTEGER NOT NULL DEFAULT 0,
            merkle_leaf TEXT NOT NULL,
            updated_at REAL NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    return db_path

def compute_hmac_signature(intent_id: str, user_pubkey: str, amount_cents: int) -> str:
    msg = f"{intent_id}:{user_pubkey}:{amount_cents}".encode('utf-8')
    return hmac.new(WEBHOOK_SECRET.encode('utf-8'), msg, hashlib.sha256).hexdigest()

def create_checkout_intent(raw_data: dict) -> tuple[dict, int]:
    user_pubkey = str(raw_data.get("user_pubkey", "")).strip()
    if not user_pubkey:
        return {"status": "ERROR", "message": "Missing required field: user_pubkey"}, 400

    try:
        amount_cents = int(raw_data.get("amount_cents", 0))
    except (ValueError, TypeError):
        return {"status": "ERROR", "message": "Invalid amount_cents; must be a positive integer"}, 400

    if amount_cents <= 0:
        return {"status": "ERROR", "message": "Amount must be greater than zero cents (amount_cents > 0)"}, 400

    currency = str(raw_data.get("currency", "USD")).strip().upper()
    intent_id = f"intent_{hashlib.sha256(f'{user_pubkey}_{amount_cents}_{time.time()}'.encode()).hexdigest()[:24]}"
    hmac_sig = compute_hmac_signature(intent_id, user_pubkey, amount_cents)

    db_path = Path.cwd() / "omni_payments.db"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    now = time.time()
    c.execute("""
        INSERT INTO payment_intents (intent_id, user_pubkey, amount_cents, currency, hmac_signature, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'PENDING_CHECKOUT', ?, ?)
    """, (intent_id, user_pubkey, amount_cents, currency, hmac_sig, now, now))
    conn.commit()
    conn.close()

    return {
        "status": "PENDING_CHECKOUT",
        "intent_id": intent_id,
        "user_pubkey": user_pubkey,
        "amount_cents": amount_cents,
        "currency": currency,
        "hmac_signature": hmac_sig
    }, 200

def confirm_and_settle_payment(raw_data: dict, provided_secret: str) -> tuple[dict, int]:
    # Require Webhook/API secret verification to prevent unauthorized minting
    if provided_secret != WEBHOOK_SECRET:
        return {"status": "ERROR", "message": "Unauthorized: Invalid payment provider webhook secret"}, 401

    intent_id = str(raw_data.get("intent_id", "")).strip()
    if not intent_id:
        return {"status": "ERROR", "message": "Missing required field: intent_id"}, 400

    db_path = Path.cwd() / "omni_payments.db"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    c.execute("SELECT user_pubkey, amount_cents, hmac_signature, status FROM payment_intents WHERE intent_id = ?;", (intent_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {"status": "ERROR", "message": f"Payment intent '{intent_id}' not found"}, 404

    user_pubkey, amount_cents, stored_sig, current_status = row
    if current_status == "SETTLED":
        conn.close()
        return {"status": "ERROR", "message": "Payment intent is already SETTLED"}, 400

    # Verify HMAC integrity
    expected_sig = compute_hmac_signature(intent_id, user_pubkey, amount_cents)
    if not hmac.compare_digest(stored_sig, expected_sig):
        conn.close()
        return {"status": "ERROR", "message": "HMAC signature verification failed for checkout intent"}, 403

    now = time.time()

    # Update intent status
    c.execute("UPDATE payment_intents SET status = 'SETTLED', updated_at = ? WHERE intent_id = ?;", (now, intent_id))

    # Calculate XP reward (1 cent = 1 XP)
    reward_xp = amount_cents

    c.execute("SELECT xp_balance FROM xp_reward_balances WHERE user_pubkey = ?;", (user_pubkey,))
    bal_row = c.fetchone()
    current_xp = bal_row[0] if bal_row else 0
    new_xp = current_xp + reward_xp

    # Merkle leaf computation
    leaf_bytes = f"{user_pubkey}:{new_xp}:{now}".encode('utf-8')
    merkle_leaf = "0x" + hashlib.sha256(leaf_bytes).hexdigest()

    c.execute("""
        INSERT INTO xp_reward_balances (user_pubkey, xp_balance, merkle_leaf, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_pubkey) DO UPDATE SET
            xp_balance = excluded.xp_balance,
            merkle_leaf = excluded.merkle_leaf,
            updated_at = excluded.updated_at;
    """, (user_pubkey, new_xp, merkle_leaf, now))

    conn.commit()
    conn.close()

    # Relay settlement event to local daemon (:5000)
    event_envelope = {
        "action": "PAYMENT_SETTLED_AND_XP_AWARDED",
        "author_pubkey": user_pubkey,
        "payload": {
            "intent_id": intent_id,
            "amount_cents": amount_cents,
            "awarded_xp": reward_xp,
            "total_xp_balance": new_xp,
            "merkle_leaf": merkle_leaf
        },
        "timestamp": now
    }
    json_bytes = json.dumps(event_envelope, sort_keys=True, separators=(',', ':')).encode('utf-8')
    req = urllib.request.Request(DAEMON_EVENT_URL, data=json_bytes, headers={'Content-Type': 'application/json'}, method='POST')
    relayed = False
    try:
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            relayed = (resp.status == 200)
    except Exception:
        relayed = False

    return {
        "status": "SETTLED",
        "intent_id": intent_id,
        "user_pubkey": user_pubkey,
        "amount_cents": amount_cents,
        "total_xp_balance": new_xp,
        "merkle_leaf": merkle_leaf,
        "daemon_relay": "SUCCESS" if relayed else "LOCAL_SAVED"
    }, 200

def query_user_balance(user_pubkey: str) -> tuple[dict, int]:
    if not user_pubkey:
        return {"status": "ERROR", "message": "Missing user_pubkey"}, 400

    db_path = Path.cwd() / "omni_payments.db"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("SELECT xp_balance, merkle_leaf FROM xp_reward_balances WHERE user_pubkey = ?;", (user_pubkey,))
    row = c.fetchone()
    conn.close()

    if not row:
        # Zero free money default!
        return {"status": "SUCCESS", "user_pubkey": user_pubkey, "xp_balance": 0, "merkle_leaf": "0x" + "0" * 64}, 200

    return {"status": "SUCCESS", "user_pubkey": user_pubkey, "xp_balance": row[0], "merkle_leaf": row[1]}, 200

class PaymentHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Webhook-Secret")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/v1/payments/health":
            resp_data = {
                "status": "ONLINE",
                "version": VERSION,
                "gateway_id": STATE.gateway_id,
                "uptime_seconds": round(time.time() - STATE.start_time, 1)
            }
            body = json.dumps(resp_data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif self.path.startswith("/api/v1/crypto/balance"):
            query_str = self.path.split("?", 1)[1] if "?" in self.path else ""
            params = dict(p.split("=", 1) for p in query_str.split("&") if "=" in p)
            target_key = params.get("pubkey", "")
            resp_data, status_code = query_user_balance(target_key)
            body = json.dumps(resp_data).encode("utf-8")
            self.send_response(status_code)
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

        if self.path == "/api/v1/payments/create-intent":
            try:
                data = json.loads(post_body)
                resp_data, status_code = create_checkout_intent(data)
                body = json.dumps(resp_data).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_error(400, f"Bad Request: {e}")

        elif self.path == "/api/v1/payments/confirm":
            provided_secret = self.headers.get("X-Webhook-Secret", "")
            try:
                data = json.loads(post_body)
                resp_data, status_code = confirm_and_settle_payment(data, provided_secret)
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
    print(f"OMNI CRYPTO & PAYMENT GATEWAY MICROSERVICE [v{VERSION}]")
    print("==================================================================")
    print(f"[✓] Gateway ID:      {STATE.gateway_id}")
    print(f"[✓] SQLite WAL DB:   {db_file}")
    print(f"[✓] Bound Endpoint:  http://{IPC_HOST}:{PAYMENT_PORT}/api/v1/payments/health")
    print("------------------------------------------------------------------")

    server = ThreadingHTTPServer((IPC_HOST, PAYMENT_PORT), PaymentHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[✓] Payment Gateway Microservice shut down cleanly.")
        sys.exit(0)

if __name__ == "__main__":
    main()
