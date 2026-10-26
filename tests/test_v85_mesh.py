import os
import sys
import time
import json
import subprocess
import urllib.request
import urllib.error

host = "127.0.0.1"

def http_get(port: int, path: str) -> dict:
    url = f"http://{host}:{port}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=2.0) as res:
        return json.loads(res.read().decode('utf-8'))

def http_post(port: int, path: str, payload: dict, headers: dict = None) -> tuple[dict, int]:
    url = f"http://{host}:{port}{path}"
    body = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    req_headers = {'Content-Type': 'application/json'}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=body, headers=req_headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=2.0) as res:
            return json.loads(res.read().decode('utf-8')), res.status
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        try:
            return json.loads(err_body), e.code
        except Exception:
            return {"error": err_body}, e.code

def run_test():
    print("======================================================================")
    print("STARTING OMNIVERSE v8.5.0 HARDENED MESH & SECURITY INTEGRATION TEST")
    print("======================================================================")

    # Launch daemon
    daemon_proc = subprocess.Popen([sys.executable, "/workspace/scratch/omni_live_daemon_server.py"])
    pay_proc = subprocess.Popen([sys.executable, "/workspace/scratch/omni_crypto_payment_gateway.py"])
    lpe_proc = subprocess.Popen([sys.executable, "/workspace/scratch/lpe_trait_normalizer.py"])
    cas_proc = subprocess.Popen([sys.executable, "/workspace/scratch/omni_ipfs_cas_streaming_engine.py"])
    bft_proc = subprocess.Popen([sys.executable, "/workspace/scratch/omni_bft_patch_consensus_engine.py"])

    print("[*] Background microservices launched. Waiting 3s for port bindings...")
    time.sleep(3.0)

    try:
        # Test 1: Telemetry Health
        print("\n--- Test 1: Telemetry Health (:9100) ---")
        health = http_get(9100, "/api/v1/telemetry/node-health")
        print(f"Status: {health.get('status')} | Node ID: {health.get('node_id')} | P2P Sync Port: {health.get('p2p_sync_port')}")
        assert health.get('p2p_sync_port') == 5005, "P2P Sync Port should be 5005"

        # Test 2: P2P Sync Receiver on :5005 with Canonical Hash Verification
        print("\n--- Test 2: P2P Sync Receiver on :5005 ---")
        now = 1700000100.0
        canonical_struct = {
            "action": "TEST_P2P_MESH_EVENT",
            "author_pubkey": "0xnode_alpha_123",
            "payload": {"msg": "Hello P2P Mesh"},
            "previous_hash": "0xgenesis_000",
            "timestamp": now
        }
        import hashlib
        canonical_bytes = json.dumps(canonical_struct, sort_keys=True, separators=(',', ':')).encode('utf-8')
        computed_hash = "0x" + hashlib.sha256(canonical_bytes).hexdigest()

        sync_payload = {
            "event_id": computed_hash,
            "action": "TEST_P2P_MESH_EVENT",
            "author_pubkey": "0xnode_alpha_123",
            "payload": {"msg": "Hello P2P Mesh"},
            "previous_hash": "0xgenesis_000",
            "timestamp": now
        }

        res, code = http_post(5005, "/p2p/sync", sync_payload)
        print(f"P2P Sync Response: {res} (Code: {code})")
        assert code == 200, f"Expected 200, got {code}"
        assert res.get('event_id') == computed_hash, "Event ID mismatch"

        # Test 3: Duplicate Event Deduplication on :5005
        print("\n--- Test 3: Duplicate Event Deduplication ---")
        res_dup, code_dup = http_post(5005, "/p2p/sync", sync_payload)
        print(f"Duplicate Sync Response: {res_dup} (Code: {code_dup})")
        assert res_dup.get('result') == 'ALREADY_EXISTS', "Should detect existing event"

        # Test 4: Tampered Hash Rejection on :5005
        print("\n--- Test 4: Tampered Hash Rejection ---")
        tampered_payload = dict(sync_payload)
        tampered_payload["event_id"] = "0x" + "f" * 64
        tampered_payload["timestamp"] = now + 50.0  # Hash changed!
        res_tamp, code_tamp = http_post(5005, "/p2p/sync", tampered_payload)
        print(f"Tampered Hash Response: {res_tamp} (Code: {code_tamp})")
        assert code_tamp == 400, "Should reject hash mismatch with 400"

        # Test 5: Payments Gateway Positive Cents & Unauthorized Confirmation Check
        print("\n--- Test 5: Payments Gateway Security (:5001) ---")
        intent_res, intent_code = http_post(5001, "/api/v1/payments/create-intent", {
            "user_pubkey": "0xuser_test_pay",
            "amount_cents": 1500,  # $15.00 USD as positive integer cents
            "currency": "USD"
        })
        print(f"Create Intent Response: {intent_res} (Code: {intent_code})")
        assert intent_code == 200
        intent_id = intent_res.get("intent_id")

        # Confirm without secret (should be 401 Unauthorized)
        unauth_res, unauth_code = http_post(5001, "/api/v1/payments/confirm", {
            "intent_id": intent_id
        })
        print(f"Unauthorized Confirm Response: {unauth_res} (Code: {unauth_code})")
        assert unauth_code == 401, "Confirm without secret must return 401 Unauthorized"

        # Confirm with valid secret
        confirm_res, confirm_code = http_post(5001, "/api/v1/payments/confirm", {
            "intent_id": intent_id
        }, headers={"X-Webhook-Secret": "omni_hw_sec_key_2026_99x"})
        print(f"Authorized Confirm Response: {confirm_res} (Code: {confirm_code})")
        assert confirm_code == 200, "Confirm with secret should succeed"
        assert confirm_res.get("total_xp_balance") == 1500

        # Reject negative or zero amounts
        zero_res, zero_code = http_post(5001, "/api/v1/payments/create-intent", {
            "user_pubkey": "0xuser_test_pay",
            "amount_cents": -500
        })
        print(f"Negative Amount Intent Response: {zero_res} (Code: {zero_code})")
        assert zero_code == 400, "Negative amount should be rejected with 400"

        # Test 6: LPE Normalizer Health (:5002)
        print("\n--- Test 6: LPE Trait Normalizer Health (:5002) ---")
        lpe_health = http_get(5002, "/api/v1/lpe/health")
        print(f"LPE Health: {lpe_health}")
        assert lpe_health.get('status') == 'ONLINE'

        # Test 7: IPFS CAS Streaming (:5003)
        print("\n--- Test 7: IPFS CAS Streaming (:5003) ---")
        cas_health = http_get(5003, "/api/v1/cas/health")
        print(f"CAS Health: {cas_health}")
        assert cas_health.get('status') == 'ONLINE'

        # Test 8: BFT Patch Consensus (:5004)
        print("\n--- Test 8: BFT Patch Consensus (:5004) ---")
        bft_health = http_get(5004, "/api/v1/bft/health")
        print(f"BFT Health: {bft_health}")
        assert bft_health.get('status') == 'ONLINE'

        print("\n======================================================================")
        print("ALL 8 HARDENED SECURITY & P2P MESH TESTS PASSED CLEANLY!")
        print("======================================================================")

    finally:
        daemon_proc.terminate()
        pay_proc.terminate()
        lpe_proc.terminate()
        cas_proc.terminate()
        bft_proc.terminate()

if __name__ == "__main__":
    run_test()
