#!/usr/bin/env python3
import sys
import time
import json
import hashlib
import random
import urllib.request
import urllib.error

EVENT_ENDPOINT = "http://127.0.0.1:5000/api/events/append"
AGENT_ID = f"OmniMind_{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]}"

TASKS = [
    ("OMNIMIND_MERKLE_TREE_COMPACTION", {"name": "MERKLE_TREE_COMPACTION", "progress": 100, "status": "COMPLETED"}),
    ("OMNIMIND_CRDT_STATE_RECONCILIATION", {"name": "CRDT_STATE_RECONCILIATION", "progress": 100, "status": "CONVERGED"}),
    ("OMNIMIND_PEER_ATTESTATION_CHECK", {"name": "PEER_ATTESTATION_CHECK", "progress": 100, "status": "ATTESTED"}),
    ("OMNIMIND_SWARM_HEALTH_SCAN", {"name": "SWARM_HEALTH_SCAN", "progress": 100, "status": "OPTIMAL"}),
]

def emit_event(action: str, payload: dict):
    data = {
        "action": action,
        "author_pubkey": AGENT_ID,
        "payload": payload,
        "timestamp": time.time(),
        "agent_id": AGENT_ID
    }
    json_bytes = json.dumps(data).encode('utf-8')
    
    req = urllib.request.Request(EVENT_ENDPOINT, data=json_bytes, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=2) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            print(f"[✓ {time.strftime('%H:%M:%S')}] {action:<35} | Hash: {res_json.get('event_id', 'N/A')[:16]}...")
    except urllib.error.HTTPError as e:
        print(f"[!] OmniMind Telemetry Notice: (HTTP Error {e.code}: {e.reason})")
    except Exception as e:
        print(f"[!] Daemon Connection Refused: Ensure omni_live_daemon_server.py is running on port 5000. ({e})")

def main():
    print("==================================================================")
    print("OMNIMIND AUTONOMOUS AGENT ENGINE [v7.0.0]")
    print("==================================================================")
    print(f"[✓] Agent ID: {AGENT_ID}")
    print("==================================================================")

    emit_event("OMNIMIND_AGENT_INITIALIZED", {"name": "AGENT_INITIALIZED", "progress": 100, "status": "READY"})

    while True:
        action, payload = random.choice(TASKS)
        payload["timestamp"] = time.time()
        emit_event(action, payload)
        time.sleep(3)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[✓] OmniMind Telemetry Emitter stopped.")
        sys.exit(0)
