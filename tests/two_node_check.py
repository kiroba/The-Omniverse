import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent.parent / 'Admin'))
"""Run against a daemon with the signing patch: python two_node_check.py [NODE_B_IP]
Check 5 only works when run on the same machine as the daemon."""
import json, urllib.request, sys
from pathlib import Path
from omni_signing import load_or_create_key, pubkey_hex, sign_event
def post(url, obj):
    req=urllib.request.Request(url, json.dumps(obj).encode(), {"Content-Type":"application/json"})
    try:
        r=urllib.request.urlopen(req, timeout=3); return r.status, r.read().decode()
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:120]
HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"   # Node B's LAN IP for a real two-laptop test
P2P=f"http://{HOST}:5005/p2p/sync"; IPC="http://127.0.0.1:5000/api/events/append"  # IPC is loopback-only by design
nodeB=load_or_create_key(Path("nodeA_test.key")); mal=load_or_create_key(Path("mallory_test.key"))
ev={"action":"CHAT","author_pubkey":pubkey_hex(nodeB),"payload":{"t":"hi"},"previous_hash":"0x"+"1"*64,"timestamp":1761590000.5}
good=dict(ev, signature=sign_event(nodeB, ev))
print("1 signed peer event     ->", post(P2P, good))
print("2 same event again      ->", post(P2P, good))
f=dict(ev, payload={"t":"forged"}); f["signature"]=sign_event(mal, f)
print("3 forged author         ->", post(P2P, f))
print("4 unsigned peer event   ->", post(P2P, {k:v for k,v in ev.items()} | {"payload":{"t":"nosig"}}))
print("5 local app append      ->", post(IPC, {"action":"LOCAL","author_pubkey":"pretend","payload":{"x":1}}))
