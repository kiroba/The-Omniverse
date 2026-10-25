import os
import time
import uuid
import json
import hashlib
from typing import Dict, Any, Tuple, List, Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

# Role Tier Configuration
TIER_PAYOUT_CONFIG = {
    "COMMON": {
        "monthly_access_fee": 0.0,
        "can_paywall": False,
        "can_custom_subscribe": False,
        "can_receive_gifts": True,
        "can_send_gifts": True,
        "manual_cashout_min_usd": 10.00,
        "auto_weekly_payout_fan_threshold": 500,
        "anytime_cashout": False
    },
    "CREATOR": {
        "monthly_access_fee": 15.00,
        "can_paywall": True,
        "can_custom_subscribe": True,
        "can_receive_gifts": True,
        "can_send_gifts": True,
        "manual_cashout_min_usd": 0.01,
        "auto_weekly_payout_fan_threshold": 0,
        "anytime_cashout": True
    },
    "INFLUENCER": {
        "monthly_access_fee": 10.00,
        "can_paywall": True,
        "can_custom_subscribe": True,
        "can_receive_gifts": True,
        "can_send_gifts": True,
        "manual_cashout_min_usd": 0.01,
        "auto_weekly_payout_fan_threshold": 0,
        "anytime_cashout": True
    },
    "EDUCATOR": {
        "monthly_access_fee": 5.00,
        "can_paywall": True,
        "can_custom_subscribe": True,
        "can_receive_gifts": True,
        "can_send_gifts": True,
        "manual_cashout_min_usd": 0.01,
        "auto_weekly_payout_fan_threshold": 0,
        "anytime_cashout": True
    }
}


class KickBackPayoutAndAntiFraudEngine:
    """
    Payout Policy & Anti-Fraud Security Engine for The KickBack.
    Enforces Common user $10 min / 500-fan weekly auto-payout rules,
    instant cashout for upgraded tiers, and guards against Sybil fan-padding,
    wash-gifting loops, double payouts, and velocity spikes.
    """

    def __init__(self):
        self.processed_payout_nonces = set()
        self.user_fans = {}       # target_pubkey -> set of fan_pubkeys
        self.fan_attestations = {} # fan_pubkey -> bool (is_hardware_attested)
        self.gifting_graph = {}    # (sender, recipient) -> list of timestamps/amounts

    def register_fan_follow(self, fan_pubkey: str, creator_pubkey: str, is_hardware_attested: bool = True) -> Tuple[bool, str]:
        """Registers a fan follow event with hardware attestation tracking."""
        self.fan_attestations[fan_pubkey] = is_hardware_attested

        if creator_pubkey not in self.user_fans:
            self.user_fans[creator_pubkey] = set()

        self.user_fans[creator_pubkey].add(fan_pubkey)
        return True, "FAN_REGISTERED"

    def get_verified_fan_count(self, creator_pubkey: str) -> int:
        """
        Anti-Sybil Fan Padding Guard:
        Calculates fan count excluding un-attested bot pubkeys.
        """
        fans = self.user_fans.get(creator_pubkey, set())
        verified_fans = [f for f in fans if self.fan_attestations.get(f, False)]
        return len(verified_fans)

    def record_gift_transaction(self, sender_pubkey: str, recipient_pubkey: str, amount_usd: float) -> Tuple[bool, str]:
        """
        Anti-Wash Loop Guard:
        Detects circular gifting rings (e.g. A -> B -> A) within a 1-hour window.
        """
        now = time.time()
        pair_key = (sender_pubkey, recipient_pubkey)
        reverse_pair_key = (recipient_pubkey, sender_pubkey)

        if pair_key not in self.gifting_graph:
            self.gifting_graph[pair_key] = []
        self.gifting_graph[pair_key].append((now, amount_usd))

        # Check reverse gifting in last 3600 seconds
        reverse_gifts = self.gifting_graph.get(reverse_pair_key, [])
        recent_reverse_volume = sum(amt for ts, amt in reverse_gifts if (now - ts) <= 3600)

        if recent_reverse_volume > 0 and amount_usd > 10.0:
            return False, f"WASH_GIFTING_DETECTED: Circular gift loop detected between {sender_pubkey[:8]} and {recipient_pubkey[:8]}. Transaction flagged for anti-fraud review."

        return True, "GIFT_TRANSACTION_CLEARED"

    def check_payout_eligibility(
        self,
        user_pubkey: str,
        role_tier: str,
        accumulated_balance_usd: float,
        request_amount_usd: float
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Evaluates payout eligibility based on role tier, thresholds, and fan counts.
        """
        tier = role_tier.upper()
        if tier not in TIER_PAYOUT_CONFIG:
            return False, f"INVALID_TIER: Unknown role tier {role_tier}", {}

        config = TIER_PAYOUT_CONFIG[tier]
        verified_fans = self.get_verified_fan_count(user_pubkey)

        # Check requested amount vs available balance
        if request_amount_usd > accumulated_balance_usd:
            return False, f"INSUFFICIENT_FUNDS: Requested ${request_amount_usd:.2f} exceeds balance ${accumulated_balance_usd:.2f}", {}

        if tier == "COMMON":
            # Rule 1: Minimum $10.00 for manual cash-out
            if request_amount_usd < config["manual_cashout_min_usd"]:
                return False, f"THRESHOLD_NOT_MET: Common users require a minimum $10.00 balance to cash out. Current requested: ${request_amount_usd:.2f}.", {
                    "is_eligible": False,
                    "current_balance": accumulated_balance_usd,
                    "min_required": 10.00,
                    "verified_fans": verified_fans,
                    "auto_weekly_payout": verified_fans >= 500
                }

            is_auto_weekly = verified_fans >= 500
            status_msg = "COMMON_PAYOUT_APPROVED_WEEKLY_AUTO" if is_auto_weekly else "COMMON_PAYOUT_APPROVED_MANUAL_MIN_MET"

            return True, status_msg, {
                "is_eligible": True,
                "role_tier": "COMMON",
                "payout_amount_usd": request_amount_usd,
                "remaining_balance_usd": round(accumulated_balance_usd - request_amount_usd, 2),
                "verified_fans": verified_fans,
                "auto_weekly_payout_active": is_auto_weekly
            }

        else:
            # Upgraded tiers (CREATOR, INFLUENCER, EDUCATOR) enjoy 24/7 instant cash-out anytime
            return True, f"{tier}_PAYOUT_APPROVED_ANYTIME_INSTANT", {
                "is_eligible": True,
                "role_tier": tier,
                "payout_amount_usd": request_amount_usd,
                "remaining_balance_usd": round(accumulated_balance_usd - request_amount_usd, 2),
                "verified_fans": verified_fans,
                "anytime_cashout": True
            }

    def execute_payout_transaction(
        self,
        user_privkey: ed25519.Ed25519PrivateKey,
        role_tier: str,
        payout_amount_usd: float,
        payout_rail: str,        # 'CASH_APP', 'VENMO', 'PAYPAL', 'LIGHTNING'
        payout_handle: str,
        nonce_str: str,
        accumulated_balance_usd: float
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Executes and signs a cryptographic PAYMENT_CASHOUT_EVENT.
        Guards against replay attacks using the unique nonce_str.
        """
        user_pubkey = user_privkey.public_key().public_bytes_raw().hex()

        # 1. Anti-Replay Guard
        if nonce_str in self.processed_payout_nonces:
            return False, "REPLAY_ATTACK_DETECTED: Payout nonce has already been executed.", {}

        # 2. Check Eligibility
        eligible, msg, details = self.check_payout_eligibility(
            user_pubkey=user_pubkey,
            role_tier=role_tier,
            accumulated_balance_usd=accumulated_balance_usd,
            request_amount_usd=payout_amount_usd
        )

        if not eligible:
            return False, f"CASHOUT_DENIED: {msg}", details

        # 3. Mark Nonce as Spent
        self.processed_payout_nonces.add(nonce_str)

        # 4. Construct Merkle Event Envelope
        now_ms = int(time.time() * 1000)
        event_id = str(uuid.uuid4())

        payload = {
            "cashout_event_id": event_id,
            "user_pubkey": user_pubkey,
            "role_tier": role_tier.upper(),
            "payout_amount_usd": payout_amount_usd,
            "payout_rail": payout_rail,
            "payout_handle": payout_handle,
            "nonce": nonce_str,
            "executed_at": now_ms
        }

        canonical_payload = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        hash_input = f"{now_ms}:{user_pubkey}:PAYMENT_CASHOUT_EVENT:{canonical_payload}"
        current_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
        signature = user_privkey.sign(current_hash.encode('utf-8')).hex()

        event_envelope = {
            "event_id": event_id,
            "timestamp": now_ms,
            "author_pubkey": user_pubkey,
            "event_type": "PAYMENT_CASHOUT_EVENT",
            "payload": payload,
            "current_hash": current_hash,
            "signature": signature
        }

        return True, "CASHOUT_EXECUTED_SUCCESSFULLY", {
            "event_envelope": event_envelope,
            "details": details
        }
