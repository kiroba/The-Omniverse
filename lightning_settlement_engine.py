import os
import time
import uuid
import json
import hashlib
import hmac
from typing import Dict, Any, Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import ed25519

class LightningSettlementEngine:
    """
    P2P Lightning Network Payment Settlement & Zero-Trust Key Release Engine
    for The KickBack & The-Omni-Hub.
    """
    @staticmethod
    def generate_invoice(
        payer_pubkey: str,
        recipient_pubkey: str,
        amount_sats: int,
        role_tier: str = "CREATOR",
        memo: str = "KickBack Subscription"
    ) -> Tuple[Dict[str, Any], bytes]:
        """
        Generates a Lightning invoice simulation with a secret 32-byte preimage R
        and Payment Hash H = SHA256(R).
        Returns (invoice_dict, preimage_bytes).
        """
        preimage = os.urandom(32)
        payment_hash = hashlib.sha256(preimage).hexdigest()
        invoice_id = f"lnbc_{payment_hash[:16]}"
        
        invoice = {
            "invoice_id": invoice_id,
            "payer_pubkey": payer_pubkey,
            "recipient_pubkey": recipient_pubkey,
            "amount_sats": amount_sats,
            "role_tier": role_tier,
            "payment_hash": payment_hash,
            "memo": memo,
            "created_at": int(time.time()),
            "expires_at": int(time.time()) + 3600  # 1 hour invoice TTL
        }
        return invoice, preimage

    @staticmethod
    def verify_payment_preimage(preimage: bytes, expected_payment_hash: str) -> bool:
        """Verifies that SHA256(preimage) matches expected payment_hash."""
        computed_hash = hashlib.sha256(preimage).hexdigest()
        return hmac.compare_digest(computed_hash, expected_payment_hash)

    @staticmethod
    def encrypt_paywall_key(post_key: bytes, preimage: bytes) -> Dict[str, str]:
        """
        Zero-Trust Key Release Protocol:
        Encrypts the symmetric content key (post_key) using an AES-GCM key derived
        from the secret preimage R.
        Key Derivation: K_derived = HMAC-SHA256(preimage, b"KICKBACK_PAYWALL_KEY_RELEASE")
        """
        derived_key = hmac.new(preimage, b"KICKBACK_PAYWALL_KEY_RELEASE", hashlib.sha256).digest()
        aesgcm = AESGCM(derived_key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, post_key, None)
        return {
            "ciphertext": ciphertext.hex(),
            "nonce": nonce.hex()
        }

    @staticmethod
    def decrypt_paywall_key(encrypted_key_data: Dict[str, str], preimage: bytes) -> bytes:
        """
        Decrypts the symmetric content key using the secret preimage R
        revealed upon Lightning payment settlement.
        """
        ciphertext = bytes.fromhex(encrypted_key_data["ciphertext"])
        nonce = bytes.fromhex(encrypted_key_data["nonce"])
        derived_key = hmac.new(preimage, b"KICKBACK_PAYWALL_KEY_RELEASE", hashlib.sha256).digest()
        aesgcm = AESGCM(derived_key)
        return aesgcm.decrypt(nonce, ciphertext, None)

    @staticmethod
    def create_verified_payment_accounting_event(
        payer_privkey: ed25519.Ed25519PrivateKey,
        recipient_pubkey: str,
        role_tier: str,
        gross_amount_usd: float,
        payment_hash: str,
        preimage_hex: str,
        prev_hash: str = "0" * 64
    ) -> Dict[str, Any]:
        """
        Constructs and cryptographically signs a PAYMENT_ACCOUNTING_EVENT envelope
        for Layer 1 Merkle log storage and P2P audit.
        """
        payer_pubkey = payer_privkey.public_key().public_bytes_raw().hex()
        now_ms = int(time.time() * 1000)
        event_id = str(uuid.uuid4())

        # Platform Fee Schedule by Role Tier
        fee_schedule = {
            "COMMON": 0.20,
            "CREATOR": 0.18,
            "INFLUENCER": 0.15,
            "EDUCATOR": 0.10
        }
        platform_rate = fee_schedule.get(role_tier, 0.20)
        platform_fee = round(gross_amount_usd * platform_rate, 2)
        creator_payout = round(gross_amount_usd - platform_fee, 2)

        payload = {
            "payment_event_id": event_id,
            "payer_pubkey": payer_pubkey,
            "recipient_pubkey": recipient_pubkey,
            "payment_type": "SUBSCRIBER_MONTHLY",
            "role_tier": role_tier,
            "gross_amount_usd": gross_amount_usd,
            "payment_rail": "LIGHTNING_NETWORK",
            "payment_hash": payment_hash,
            "preimage_proof": preimage_hex,
            "accounting_split": {
                "role_tier": role_tier,
                "gross_amount_usd": gross_amount_usd,
                "platform_fee_percent": platform_rate * 100,
                "platform_fee_usd": platform_fee,
                "creator_payout_percent": (1 - platform_rate) * 100,
                "creator_payout_usd": creator_payout
            },
            "valid_until_timestamp": now_ms + (30 * 24 * 3600 * 1000)  # 30-day validity TTL
        }

        canonical_payload = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        hash_input = f"{prev_hash}:{now_ms}:{payer_pubkey}:PAYMENT_ACCOUNTING_EVENT:{canonical_payload}"
        current_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
        signature = payer_privkey.sign(current_hash.encode('utf-8')).hex()

        return {
            "event_id": event_id,
            "timestamp": now_ms,
            "author_pubkey": payer_pubkey,
            "author_type": "HUMAN_USER",
            "event_type": "PAYMENT_ACCOUNTING_EVENT",
            "payload": payload,
            "prev_hash": prev_hash,
            "current_hash": current_hash,
            "signature": signature
        }

    @staticmethod
    def verify_payment_accounting_event(event_envelope: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Audits and verifies a PAYMENT_ACCOUNTING_EVENT envelope on any P2P node.
        Checks Ed25519 signature, SHA256 current hash, preimage proof, and accounting math.
        """
        try:
            # 1. Verify Ed25519 signature
            author_pubkey = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(event_envelope["author_pubkey"]))
            author_pubkey.verify(bytes.fromhex(event_envelope["signature"]), event_envelope["current_hash"].encode('utf-8'))

            # 2. Verify Canonical Hash
            canonical_payload = json.dumps(event_envelope["payload"], sort_keys=True, separators=(',', ':'))
            hash_input = f"{event_envelope['prev_hash']}:{event_envelope['timestamp']}:{event_envelope['author_pubkey']}:PAYMENT_ACCOUNTING_EVENT:{canonical_payload}"
            computed_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
            if computed_hash != event_envelope["current_hash"]:
                return False, "HASH_MISMATCH: Computed hash does not match event envelope."

            # 3. Verify Preimage Proof vs Payment Hash
            payload = event_envelope["payload"]
            preimage_bytes = bytes.fromhex(payload["preimage_proof"])
            if not LightningSettlementEngine.verify_payment_preimage(preimage_bytes, payload["payment_hash"]):
                return False, "PREIMAGE_INVALID: Payment preimage does not match payment hash."

            # 4. Verify Accounting Split Math
            split = payload["accounting_split"]
            expected_gross = payload["gross_amount_usd"]
            if round(split["platform_fee_usd"] + split["creator_payout_usd"], 2) != expected_gross:
                return False, "ACCOUNTING_MATH_ERROR: Platform fee + Creator payout does not sum to gross amount."

            return True, "PAYMENT_ACCOUNTING_EVENT_VERIFIED"
        except Exception as e:
            return False, f"VERIFICATION_FAILED: {str(e)}"
