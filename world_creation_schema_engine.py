"""
Continuity-Engine: World Creation Schema & Validation Engine
Repository: kiroba/Continuity-Engine
Target Application: KickBack Universe (com.kickback)

This module defines, validates, and generates cryptographically signed JSON-LD event
schemas for creating new Worlds (interactive rooms, message boards, forums, groups, and
communities) inside KickBack Universe.
"""

import json
import time
import hashlib
from typing import Dict, Any, List, Optional

# Standard JSON-LD Context for Continuity-Engine
CONTINUITY_WORLD_SCHEMA_CONTEXT = "https://schema.omni.hub/v1/world_creation.jsonld"

WORLD_TYPES = [
    "interactive_room",   # WebRTC video/audio stream stage
    "forum_board",        # Structured long-form discussion & Q&A
    "community_group",    # Subscriber circle with feed & paywalls
    "chat_lounge"         # Ephemeral real-time text/voice lounge
]

ROLE_TIERS = ["COMMON", "CREATOR", "INFLUENCER", "EDUCATOR"]

class WorldCreationSchemaEngine:
    def __init__(self, universe_id: str = "com.kickback"):
        self.universe_id = universe_id

    def build_world_creation_event(
        self,
        creator_pubkey: str,
        world_name: str,
        world_type: str,
        topic_category: str,
        visibility: str = "public",
        monetization_model: str = "free",
        required_tier: str = "COMMON",
        entry_fee_credits: int = 0,
        subscription_monthly_credits: int = 0,
        ttl_seconds: Optional[int] = None,
        snapshot_epoch_blocks: int = 1000,
        ephemeral_chat: bool = False,
        supported_media: Optional[List[str]] = None,
        previous_event_hash: str = "0x0000000000000000000000000000000000000000000000000000000000000000"
    ) -> Dict[str, Any]:
        """
        Constructs a complete Continuity-Engine WORLD_CREATED event envelope.
        """
        if world_type not in WORLD_TYPES:
            raise ValueError(f"Invalid world_type '{world_type}'. Must be one of {WORLD_TYPES}")
        if required_tier not in ROLE_TIERS:
            raise ValueError(f"Invalid required_tier '{required_tier}'. Must be one of {ROLE_TIERS}")

        if supported_media is None:
            supported_media = ["text", "voice", "video_webrtc", "3d_lottie_gifts"]

        timestamp = int(time.time())
        world_slug = world_name.lower().replace(" ", "_").replace("-", "_")
        world_id = f"world_{world_type}_{world_slug}_{int(timestamp)}"
        event_id = f"evt_world_create_{hashlib.sha256(f'{world_id}:{timestamp}'.encode()).hexdigest()[:16]}"

        world_configuration = {
            "worldName": world_name,
            "worldType": world_type,
            "topicCategory": topic_category,
            "accessControl": {
                "visibility": visibility,                     # public | private | invite_only
                "monetizationModel": monetization_model,      # free | paywalled_one_time | paywalled_subscription
                "requiredTier": required_tier,                # COMMON | CREATOR | INFLUENCER | EDUCATOR
                "entryFeeCredits": entry_fee_credits,
                "subscriptionMonthlyCredits": subscription_monthly_credits
            },
            "retentionPolicy": {
                "ttlSeconds": ttl_seconds,                    # None = Permanent, or integer seconds
                "snapshotEpochBlocks": snapshot_epoch_blocks, # Interval for Merkle SnapshotAnchorBlock
                "ephemeralChat": ephemeral_chat
            },
            "supportedMedia": supported_media,
            "moderation": {
                "humanOnlyPosting": True,                      # Strictly enforce Human-Only feed policy
                "autoModSensitivity": "standard",              # low | standard | strict
                "bannedUsers": [],
                "bannedGuests": []
            }
        }

        # Build payload for hashing & signing
        raw_payload = {
            "@context": CONTINUITY_WORLD_SCHEMA_CONTEXT,
            "eventId": event_id,
            "universeId": self.universe_id,
            "worldId": world_id,
            "eventType": "WORLD_CREATED",
            "timestamp": timestamp,
            "creatorPubkey": creator_pubkey,
            "worldConfiguration": world_configuration,
            "previousEventHash": previous_event_hash
        }

        # Compute payload hash
        payload_bytes = json.dumps(raw_payload, sort_keys=True).encode('utf-8')
        event_hash = hashlib.sha256(payload_bytes).hexdigest()
        raw_payload["eventHash"] = f"0x{event_hash}"

        # Placeholder signature simulating local device Secure Enclave Ed25519 signing
        raw_payload["signature"] = f"sig_ed25519_{hashlib.sha256((event_hash + creator_pubkey).encode()).hexdigest()}"

        return raw_payload

    def validate_event(self, event: Dict[str, Any]) -> bool:
        """
        Validates the event schema structure and hash integrity.
        """
        required_keys = ["@context", "eventId", "universeId", "worldId", "eventType", 
                         "timestamp", "creatorPubkey", "worldConfiguration", "eventHash", "signature"]
        for key in required_keys:
            if key not in event:
                print(f"Validation Error: Missing required key '{key}'")
                return False

        if event["universeId"] != self.universe_id:
            print(f"Validation Error: Universe ID mismatch ({event['universeId']} != {self.universe_id})")
            return False

        if event["eventType"] != "WORLD_CREATED":
            print(f"Validation Error: Invalid eventType '{event['eventType']}'")
            return False

        # Re-compute hash to verify tamper-proof state
        test_payload = {k: v for k, v in event.items() if k not in ["eventHash", "signature"]}
        payload_bytes = json.dumps(test_payload, sort_keys=True).encode('utf-8')
        expected_hash = f"0x{hashlib.sha256(payload_bytes).hexdigest()}"

        if event["eventHash"] != expected_hash:
            print(f"Validation Error: Event hash mismatch! Expected {expected_hash}, got {event['eventHash']}")
            return False

        return True

# Self-test block
if __name__ == "__main__":
    engine = WorldCreationSchemaEngine(universe_id="com.kickback")
    
    # Generate sample interactive room event
    sample_room_event = engine.build_world_creation_event(
        creator_pubkey="ed25519_pk_7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d",
        world_name="Creator Lounge & Live Stage",
        world_type="interactive_room",
        topic_category="community_gaming",
        visibility="public",
        monetization_model="paywalled_subscription",
        required_tier="CREATOR",
        entry_fee_credits=10,
        subscription_monthly_credits=100
    )

    print("=== GENERATED WORLD_CREATED EVENT ===")
    print(json.dumps(sample_room_event, indent=2))

    # Validate
    is_valid = engine.validate_event(sample_room_event)
    print(f"\nSCHEMA VALIDATION RESULT: {'PASS' if is_valid else 'FAIL'}")
