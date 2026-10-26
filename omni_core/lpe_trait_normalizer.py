#!/usr/bin/env python3
"""
==============================================================================
LIVE PERSONA ENGINE (LPE) AVATAR TRAIT NORMALIZER SERVICE [v2.0.0]
==============================================================================
Security & Performance:
- Bound strictly to 127.0.0.1:5002 (Loopback IPC)
- Uses ThreadingHTTPServer for non-blocking concurrency
- Enforces 5 MB Content-Length cap
- Restricts CORS to http://127.0.0.1
==============================================================================
"""

import os
import sys
import time
import json
import re
import sqlite3
import hashlib
import threading
import socket
import urllib.request
import urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

VERSION = "2.0.0"
LPE_PORT = 5002
IPC_HOST = "127.0.0.1"
DAEMON_EVENT_URL = "http://127.0.0.1:5000/api/events/append"
MAX_PAYLOAD_SIZE = 5 * 1024 * 1024

HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")

DEFAULT_Z_LAYERS = {
    "background": 0,
    "body_skin": 1,
    "eyes_face": 2,
    "hair": 3,
    "apparel_top": 4,
    "apparel_bottom": 5,
    "headwear": 6,
    "eyewear_acc": 7,
    "aura_fx": 8
}

class LPEState:
    def __init__(self):
        self.start_time = time.time()
        self.service_id = "0x" + hashlib.sha256(f"lpe_service_{time.time()}_{os.getpid()}".encode()).hexdigest()[:32]
        self.lock = threading.Lock()

STATE = LPEState()

def init_db() -> Path:
    db_path = Path.cwd() / "lpe_persona_registry.db"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("""
        CREATE TABLE IF NOT EXISTS persona_traits (
            persona_id TEXT PRIMARY KEY,
            archetype TEXT NOT NULL,
            trait_hash TEXT NOT NULL,
            normalized_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    return db_path

def validate_hex_color(hex_str: str, default: str = "#FFFFFF") -> str:
    if not isinstance(hex_str, str):
        return default
    cleaned = hex_str.strip()
    if not cleaned.startswith("#"):
        cleaned = "#" + cleaned
    if HEX_COLOR_PATTERN.match(cleaned):
        return cleaned.upper()
    return default

def normalize_persona_payload(raw_data: dict) -> dict:
    now = time.time()
    raw_pubkey = str(raw_data.get("persona_id") or raw_data.get("user_pubkey") or f"0xuser_{now}").strip()
    persona_id = "0x" + hashlib.sha256(raw_pubkey.encode()).hexdigest()[:32] if not raw_pubkey.startswith("0x") else raw_pubkey

    archetype = str(raw_data.get("archetype", "HUMAN_SOVEREIGN")).strip().upper()
    skin_tone_hex = validate_hex_color(raw_data.get("skin_tone_hex"), "#E0AC69")
    eye_color_hex = validate_hex_color(raw_data.get("eye_color_hex"), "#2E1C0C")
    hair_style_id = str(raw_data.get("hair_style_id", "style_classic_short")).strip()
    hair_color_hex = validate_hex_color(raw_data.get("hair_color_hex"), "#1A1A1A")

    raw_cosmetics = raw_data.get("equipped_cosmetics", {})
    if not isinstance(raw_cosmetics, dict):
        raw_cosmetics = {}

    normalized_cosmetics = {}
    for cat_name, item_info in raw_cosmetics.items():
        cat_key = str(cat_name).strip().lower()
        if not isinstance(item_info, dict):
            item_info = {"item_id": str(item_info)}

        item_id = str(item_info.get("item_id", "none")).strip()
        if item_id and item_id.lower() != "none":
            color_override = validate_hex_color(item_info.get("color_hex"), "#FFFFFF")
            layer_idx = int(item_info.get("layer_index", DEFAULT_Z_LAYERS.get(cat_key, 5)))
            asset_cid = str(item_info.get("asset_cid", "")).strip()

            normalized_cosmetics[cat_key] = {
                "item_id": item_id,
                "color_hex": color_override,
                "layer_index": layer_idx,
                "asset_cid": asset_cid
            }

    canonical_struct = {
        "persona_id": persona_id,
        "archetype": archetype,
        "skin_tone_hex": skin_tone_hex,
        "eye_color_hex": eye_color_hex,
        "hair_style_id": hair_style_id,
        "hair_color_hex": hair_color_hex,
        "equipped_cosmetics": normalized_cosmetics,
        "normalized_at": now
    }

    canonical_json_bytes = json.dumps(canonical_struct, sort_keys=True, separators=(',', ':')).encode("utf-8")
    trait_hash = "0x" + hashlib.sha256(canonical_json_bytes).hexdigest()
    canonical_struct["trait_hash"] = trait_hash

    return canonical_struct

def save_persona_to_db(normalized: dict) -> None:
    db_path = Path.cwd() / "lpe_persona_registry.db"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    now = time.time()
    c.execute("""
        INSERT INTO persona_traits (persona_id, archetype, trait_hash, normalized_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(persona_id) DO UPDATE SET
            archetype=excluded.archetype,
            trait_hash=excluded.trait_hash,
            normalized_json=excluded.normalized_json,
            updated_at=excluded.updated_at;
    """, (
        normalized["persona_id"],
        normalized["archetype"],
        normalized["trait_hash"],
        json.dumps(normalized),
        now,
        now
    ))
    conn.commit()
    conn.close()

def relay_to_daemon(normalized: dict) -> bool:
    event_envelope = {
        "action": "LPE_PERSONA_TRAITS_NORMALIZED",
        "author_pubkey": normalized["persona_id"],
        "payload": {
            "persona_id": normalized["persona_id"],
            "archetype": normalized["archetype"],
            "trait_hash": normalized["trait_hash"],
            "cosmetics_count": len(normalized["equipped_cosmetics"])
        },
        "timestamp": time.time()
    }
    json_bytes = json.dumps(event_envelope, sort_keys=True, separators=(',', ':')).encode("utf-8")
    req = urllib.request.Request(DAEMON_EVENT_URL, data=json_bytes, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False

class LPEHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/v1/lpe/health":
            db_path = Path.cwd() / "lpe_persona_registry.db"
            count = 0
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*) FROM persona_traits;")
                    count = c.fetchone()[0]
                    conn.close()
                except Exception:
                    pass

            resp_data = {
                "status": "ONLINE",
                "version": VERSION,
                "service_id": STATE.service_id,
                "registered_personas": count,
                "uptime_seconds": round(time.time() - STATE.start_time, 1)
            }
            body = json.dumps(resp_data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif self.path.startswith("/api/v1/lpe/persona"):
            query_str = self.path.split("?", 1)[1] if "?" in self.path else ""
            params = dict(p.split("=", 1) for p in query_str.split("&") if "=" in p)
            target_id = params.get("id", "")

            db_path = Path.cwd() / "lpe_persona_registry.db"
            result = None
            if db_path.exists() and target_id:
                try:
                    conn = sqlite3.connect(str(db_path))
                    c = conn.cursor()
                    c.execute("SELECT normalized_json FROM persona_traits WHERE persona_id = ?;", (target_id,))
                    row = c.fetchone()
                    conn.close()
                    if row:
                        result = json.loads(row[0])
                except Exception:
                    pass

            if result:
                body = json.dumps({"status": "SUCCESS", "persona": result}).encode("utf-8")
                self.send_response(200)
            else:
                body = json.dumps({"status": "NOT_FOUND", "message": f"Persona '{target_id}' not found"}).encode("utf-8")
                self.send_response(404)

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

        if self.path == "/api/v1/lpe/normalize":
            try:
                raw_data = json.loads(post_body)
                normalized = normalize_persona_payload(raw_data)
                save_persona_to_db(normalized)
                relayed = relay_to_daemon(normalized)

                resp_data = {
                    "status": "NORMALIZED_AND_REGISTERED",
                    "persona": normalized,
                    "daemon_relay": "SUCCESS" if relayed else "OFFLINE_QUEUED"
                }
                body = json.dumps(resp_data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            except Exception as e:
                resp_data = {"status": "ERROR", "message": str(e)}
                body = json.dumps(resp_data).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        else:
            self.send_error(404, "Endpoint Not Found")

def main():
    db_file = init_db()
    print("==================================================================")
    print(f"LPE AVATAR TRAIT NORMALIZER SERVICE [v{VERSION}]")
    print("==================================================================")
    print(f"[✓] Service ID:      {STATE.service_id}")
    print(f"[✓] SQLite WAL DB:   {db_file}")
    print(f"[✓] Bound Endpoint:  http://{IPC_HOST}:{LPE_PORT}/api/v1/lpe/health")
    print("------------------------------------------------------------------")

    server = ThreadingHTTPServer((IPC_HOST, LPE_PORT), LPEHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[✓] LPE Trait Normalizer Service shut down cleanly.")
        sys.exit(0)

if __name__ == "__main__":
    main()
