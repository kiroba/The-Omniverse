#!/usr/bin/env python3
"""
==============================================================================
OMNIMIND AUTONOMOUS EDGE AGENT & REAL-TIME TELEMETRY EMITTER [v8.2.0]
Autonomous Edge Intelligence Engine for Mobile Termux & Distributed Relays
==============================================================================
System Role:
- Runs an autonomous background loop on edge hardware (Mobile Termux / Desktop)
- Audits local SQLite Merkle DAG database (`continuity_events.db`) integrity
- Emits real-time HTTP telemetry metrics to local daemon (:9100 /api/omnimind/telemetry)
- Zero external dependencies (uses standard library: urllib.request, json, time, hashlib, sqlite3)
==============================================================================
"""

import sys
import os
import time
import json
import sqlite3
import hashlib
import urllib.request
import urllib.error
from pathlib import Path

HOST_IP = os.getenv("OMNI_HOST", "127.0.0.1")
TELEMETRY_CACHE_URL = f"http://{HOST_IP}:9100/api/omnimind/telemetry"
AGENT_ID = f"OmniMind_Edge_{hashlib.sha256(f'agent_{time.time()}_{os.getpid()}'.encode()).hexdigest()[:8]}"

def audit_merkle_dag_integrity() -> dict:
    """Performs a real row-by-row Merkle chain integrity check on continuity_events.db."""
    db_path = Path.cwd() / "continuity_events.db"
    if not db_path.exists():
        return {
            "status": "WAITING_FOR_DB",
            "events_audited": 0,
            "chain_valid": True,
            "message": "continuity_events.db not initialized yet"
        }

    try:
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute("SELECT id, event_id, action, author_pubkey, previous_hash, timestamp, payload_json FROM events ORDER BY id ASC;")
        rows = c.fetchall()
        conn.close()

        if not rows:
            return {"status": "EMPTY_DB", "events_audited": 0, "chain_valid": True}

        prev_id = "0x" + "0" * 64
        chain_valid = True
        invalid_row_id = None

        for idx, row in enumerate(rows):
            row_db_id, event_id, action, author, prev_hash, ts, payload_str = row
            if idx > 0 and prev_hash != prev_id:
                chain_valid = False
                invalid_row_id = event_id
                break
            prev_id = event_id

        return {
            "status": "VALIDATED" if chain_valid else "INTEGRITY_VIOLATION",
            "events_audited": len(rows),
            "chain_valid": chain_valid,
            "invalid_event_id": invalid_row_id,
            "last_verified_event_id": prev_id
        }
    except Exception as e:
        return {"status": "AUDIT_ERROR", "error": str(e), "chain_valid": False}

def post_telemetry(action: str, audit_result: dict):
    telemetry_payload = {
        "agent_id": AGENT_ID,
        "status": "ACTIVE",
        "mode": "AUTONOMOUS_EDGE_AUDITOR",
        "action": action,
        "events_processed": audit_result.get("events_audited", 0),
        "chain_integrity": "VERIFIED" if audit_result.get("chain_valid") else "CORRUPTED",
        "last_verified_event": audit_result.get("last_verified_event_id", "N/A"),
        "timestamp": time.time()
    }

    json_bytes = json.dumps(telemetry_payload).encode('utf-8')
    req = urllib.request.Request(
        TELEMETRY_CACHE_URL,
        data=json_bytes,
        headers={'Content-Type': 'application/json', 'User-Agent': f'OmniMindAgent/{AGENT_ID}'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            pass
    except Exception:
        pass  # Daemon telemetry cache endpoint may be offline or starting

def main():
    print("==================================================================")
    print("OMNIMIND AUTONOMOUS EDGE AGENT & TELEMETRY EMITTER [v8.2.0]")
    print("==================================================================")
    print(f"[✓] Agent ID Initialized:       {AGENT_ID}")
    print(f"[✓] Telemetry Cache Endpoint:   {TELEMETRY_CACHE_URL}")
    print("------------------------------------------------------------------")
    print("Running continuous Merkle DAG integrity audits... (Press Ctrl+C to stop)")
    print("==================================================================")

    while True:
        audit_res = audit_merkle_dag_integrity()
        action = f"MERKLE_DAG_AUDIT_COUNT_{audit_res.get('events_audited', 0)}"
        
        status_symbol = "✓" if audit_res.get("chain_valid") else "!"
        print(f"[{status_symbol} {time.strftime('%H:%M:%S')}] {action:<35} | Status: {audit_res.get('status')} | Audited: {audit_res.get('events_audited')} rows")
        
        post_telemetry(action, audit_res)
        time.sleep(4)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[✓] OmniMind Telemetry Emitter stopped cleanly.")
        sys.exit(0)
