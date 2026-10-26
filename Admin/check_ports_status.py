import sys
import time
import json
import urllib.request

host = "127.0.0.1"
ports = [
    ("P2P Mesh Daemon Telemetry", 9100, "/api/v1/telemetry/node-health"),
    ("P2P Merkle Event Gateway", 5000, "/api/events/stats"),
    ("Crypto & Payment Gateway", 5001, "/api/v1/payments/health"),
    ("LPE Trait Normalizer", 5002, "/api/v1/lpe/health"),
    ("IPFS CAS Storage Engine", 5003, "/api/v1/cas/health"),
    ("BFT Patch Consensus Engine", 5004, "/api/v1/bft/health")
]

for name, port, path in ports:
    url = f"http://{host}:{port}{path}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=1.5) as res:
            data = json.loads(res.read().decode('utf-8'))
            print(f"[✓] {name:<30} : ONLINE | Status: {data.get('status', 'OK')}")
    except Exception as e:
        print(f"[!] {name:<30} : OFFLINE ({e})")
