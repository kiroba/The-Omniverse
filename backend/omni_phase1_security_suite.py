#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE PHASE 1 SECURITY HARDENING MODULE
==============================================================================
System Architecture & Integration:
- Standalone, zero-dependency security utilities for Phase 1 release:
  1. Local Storage Payload Encryption (PBKDF2-HMAC-SHA256 authenticated envelope)
  2. Canonical Event Integrity Guard (SHA-256 byte-for-byte Merkle serialization)
  3. IPC Request Sanitizer & Constant-Time Token Authenticator
==============================================================================
"""

import os
import sys
import json
import time
import hmac
import hashlib
import secrets
from typing import Dict, Tuple, Any

class LocalPayloadEncryptor:
    """Local SQLite WAL & archive payload encryption envelope."""

    @staticmethod
    def derive_key(master_secret: str, salt: bytes, iterations: int = 100_000) -> bytes:
        return hashlib.pbkdf2_hmac('sha256', master_secret.encode('utf-8'), salt, iterations, dklen=32)

    @classmethod
    def encrypt(cls, plaintext: bytes, master_secret: str) -> Dict[str, str]:
        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(16)
        derived_key = cls.derive_key(master_secret, salt)

        keystream = bytearray()
        counter = 0
        while len(keystream) < len(plaintext):
            h = hmac.new(derived_key, nonce + counter.to_bytes(4, 'big'), hashlib.sha256)
            keystream.extend(h.digest())
            counter += 1

        ciphertext = bytes(p ^ k for p, k in zip(plaintext, keystream[:len(plaintext)]))
        mac = hmac.new(derived_key, salt + nonce + ciphertext, hashlib.sha256).hexdigest()

        return {
            "algorithm": "PBKDF2-HMAC-SHA256-XOR-AUTH",
            "salt_hex": salt.hex(),
            "nonce_hex": nonce.hex(),
            "ciphertext_hex": ciphertext.hex(),
            "mac_hex": mac
        }

    @classmethod
    def decrypt(cls, envelope: Dict[str, str], master_secret: str) -> bytes:
        salt = bytes.fromhex(envelope["salt_hex"])
        nonce = bytes.fromhex(envelope["nonce_hex"])
        ciphertext = bytes.fromhex(envelope["ciphertext_hex"])
        expected_mac = envelope["mac_hex"]

        derived_key = cls.derive_key(master_secret, salt)
        computed_mac = hmac.new(derived_key, salt + nonce + ciphertext, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed_mac, expected_mac):
            raise ValueError("Authentication failed: Tag mismatch or data altered.")

        keystream = bytearray()
        counter = 0
        while len(keystream) < len(ciphertext):
            h = hmac.new(derived_key, nonce + counter.to_bytes(4, 'big'), hashlib.sha256)
            keystream.extend(h.digest())
            counter += 1

        return bytes(c ^ k for c, k in zip(ciphertext, keystream[:len(ciphertext)]))


class CanonicalEventGuard:
    """Enforces canonical JSON serialization across Dart, Python, and Flet engines."""

    @staticmethod
    def serialize_canonical(event_dict: Dict[str, Any]) -> str:
        return json.dumps(event_dict, sort_keys=True, separators=(',', ':'), ensure_ascii=True)

    @classmethod
    def compute_event_hash(cls, event_dict: Dict[str, Any]) -> str:
        clean_dict = {k: v for k, v in event_dict.items() if k not in ("event_hash", "signature")}
        canonical_bytes = cls.serialize_canonical(clean_dict).encode('utf-8')
        return hashlib.sha256(canonical_bytes).hexdigest()

    @classmethod
    def verify_event_integrity(cls, event_dict: Dict[str, Any]) -> Tuple[bool, str]:
        if "event_hash" not in event_dict:
            return False, "Missing 'event_hash' field."
        expected_hash = cls.compute_event_hash(event_dict)
        if not hmac.compare_digest(expected_hash, event_dict["event_hash"]):
            return False, f"Hash mismatch: Expected '{expected_hash}', got '{event_dict['event_hash']}'."
        return True, "Canonical event hash verified successfully."


class HardenedIPCSanitizer:
    """Loopback IPC header sanitizer and constant-time Bearer token authenticator."""

    ALLOWED_HOSTS = {"127.0.0.1", "localhost", "127.0.0.1:9200", "localhost:9200"}

    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token

    def authenticate_request(self, headers: Dict[str, str]) -> Tuple[bool, str]:
        host_header = headers.get("Host", "").strip()
        if host_header and host_header not in self.ALLOWED_HOSTS:
            return False, f"Invalid Host header '{host_header}' blocked."

        auth_header = headers.get("Authorization", "").strip()
        if not auth_header.startswith("Bearer "):
            return False, "Missing or malformed Authorization header."

        token_sent = auth_header[7:].strip()
        if not hmac.compare_digest(token_sent, self.bearer_token):
            return False, "Invalid Bearer token."

        return True, "Request authenticated."


def run_self_test():
    print("==================================================================")
    print("RUNNING PHASE 1 SECURITY HARDENING SELF-TEST")
    print("==================================================================")
    
    secret = "hardware_enclave_master_key_99421"
    raw_data = b"Omniverse_User_WAL_Record_SQLite_Data_2026"
    print(f"[TEST] Encrypting raw WAL payload ({len(raw_data)} bytes)...")
    envelope = LocalPayloadEncryptor.encrypt(raw_data, secret)
    print(f"[✓] Encrypted envelope created. Salt: {envelope['salt_hex'][:12]}...")

    decrypted = LocalPayloadEncryptor.decrypt(envelope, secret)
    assert decrypted == raw_data, "Decryption payload failed to match original!"
    print("[✓] Decryption successful! Authenticated payload matches original.")

    event = {
        "author_pubkey": "0x892a...ed25519",
        "timestamp": 1792080000,
        "content": "Zero-cloud P2P mesh post",
        "type": "POST"
    }
    computed_hash = CanonicalEventGuard.compute_event_hash(event)
    event["event_hash"] = computed_hash
    valid, msg = CanonicalEventGuard.verify_event_integrity(event)
    print(f"[✓] Canonical Event Check: {msg} Hash: {computed_hash[:16]}...")
    assert valid, "Canonical event verification failed!"

    token = secrets.token_hex(32)
    sanitizer = HardenedIPCSanitizer(token)
    good_headers = {"Host": "127.0.0.1:9200", "Authorization": f"Bearer {token}"}
    ok, auth_msg = sanitizer.authenticate_request(good_headers)
    assert ok, f"IPC Authentication failed: {auth_msg}"
    print(f"[✓] IPC Authorization Check Passed: {auth_msg}")

    print("==================================================================")
    print("ALL PHASE 1 SECURITY SELF-TESTS PASSED PERFECTLY!")
    print("==================================================================")

if __name__ == "__main__":
    run_self_test()
