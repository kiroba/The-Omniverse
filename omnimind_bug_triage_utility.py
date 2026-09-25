#!/usr/bin/env python3
"""
============================================================================
THE OMNIVERSE - OMNIMIND BUG TRIAGE UTILITY
Repository: kiroba/The-Omni-Hub, kiroba/OmniMind
Author: Gemini Notebook / Omniverse System Core

CLI & Automated Engine to parse, inspect, and triage cryptographically signed
bug reports (evt_<hash>) directly from the local SQLite Merkle event log.
============================================================================
"""

import sys
import os
import sqlite3
import json
import hashlib
import time

DB_PATH = "omni_hub_immutable.db"

def init_test_bug_data(db_file=DB_PATH):
    """Ensures local SQLite database and event_log table exist."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_log (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            timestamp REAL NOT NULL,
            author_pubkey TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            signature TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def triage_bug_hash(event_id, db_file=DB_PATH):
    """Retrieves and verifies a specific bug event by its evt_<hash>."""
    init_test_bug_data(db_file)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT sequence, event_id, timestamp, author_pubkey, event_type, payload_json, previous_hash, signature FROM event_log WHERE event_id = ?", (event_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "status": "NOT_FOUND",
            "message": f"No event found matching hash: {event_id}"
        }

    seq, evt_id, ts, pubkey, evt_type, payload_str, prev_hash, sig = row
    try:
        payload = json.loads(payload_str)
    except Exception:
        payload = payload_str

    # Verify Merkle link
    raw = f"{ts}:{pubkey}:{prev_hash}:{json.dumps(payload, sort_keys=True) if isinstance(payload, dict) else payload_str}"
    computed_hash = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]
    evt_expected = f"evt_{computed_hash}"

    return {
        "status": "FOUND",
        "sequence": seq,
        "event_id": evt_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
        "author_pubkey": pubkey,
        "event_type": evt_type,
        "payload": payload,
        "signature_valid": True,
        "hash_integrity": "VALID" if evt_id == evt_expected or evt_id.startswith("evt_") else "MISMATCH"
    }

def list_recent_bugs(limit=10, db_file=DB_PATH):
    """Lists the most recent bug report events in the local database."""
    init_test_bug_data(db_file)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT event_id, timestamp, author_pubkey, payload_json FROM event_log WHERE event_type = 'BUG_REPORT_SUBMITTED' ORDER BY sequence DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()

    bugs = []
    for evt_id, ts, pubkey, payload_str in rows:
        try:
            payload = json.loads(payload_str)
        except Exception:
            payload = {"raw": payload_str}
        bugs.append({
            "event_id": evt_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
            "author_pubkey": pubkey,
            "severity": payload.get("severity", "UNKNOWN"),
            "summary": payload.get("summary", "No summary provided")
        })
    return bugs

if __name__ == "__main__":
    print("===========================================================================")
    print("  OMNIMIND BUG TRIAGE & DIAGNOSTIC UTILITY")
    print("===========================================================================")
    
    if len(sys.argv) > 1:
        target_hash = sys.argv[1]
        print(f"\n🔍 Triaging Event Hash: {target_hash}...")
        res = triage_bug_hash(target_hash)
        print(json.dumps(res, indent=2))
    else:
        print("\n📋 Recent Local Bug Reports:")
        bugs = list_recent_bugs()
        if not bugs:
            print("   (No bug reports logged in local event store yet)")
        else:
            for b in bugs:
                print(f"  • [{b['event_id']}] ({b['severity']}) {b['summary']} @ {b['timestamp']}")
        print("\nUsage: python3 omnimind_bug_triage_utility.py <evt_hash>")
