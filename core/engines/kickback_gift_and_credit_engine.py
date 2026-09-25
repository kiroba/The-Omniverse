"""
The KickBack Expanded 100-Gift Catalog & Live Gift Notification Engine
Repository: kiroba/Continuity-Engine & kiroba/The-Omni-Hub
"""

import time
import uuid
import json
import hashlib
from typing import Dict, Any, Optional, Tuple, List

# Updated Platform Access Membership Fees (Paid directly to Platform Owner)
PLATFORM_ACCESS_FEES = {
    "COMMON": 0.00,       # $0/mo
    "CREATOR": 15.00,     # $15/mo
    "INFLUENCER": 10.00,  # $10/mo
    "EDUCATOR": 5.00,     # $5/mo (Accredited 50% discount)
}

# Preloaded Credit Bundles (OmniCredits: Base 100 credits = $1.00 USD)
CREDIT_BUNDLES = {
    "BUNDLE_5":   {"price_usd": 5.00,   "base_credits": 500,   "bonus_percent": 5,  "total_credits": 525},
    "BUNDLE_10":  {"price_usd": 10.00,  "base_credits": 1000,  "bonus_percent": 10, "total_credits": 1100},
    "BUNDLE_25":  {"price_usd": 25.00,  "base_credits": 2500,  "bonus_percent": 15, "total_credits": 2875},
    "BUNDLE_50":  {"price_usd": 50.00,  "base_credits": 5000,  "bonus_percent": 20, "total_credits": 6000},
    "BUNDLE_100": {"price_usd": 100.00, "base_credits": 10000, "bonus_percent": 25, "total_credits": 12500},
}

def _generate_100_gift_catalog() -> Dict[str, Dict[str, Any]]:
    """
    Generates a structured 100-gift catalog:
      - 70 Universal Gifts (COMMON tier access): Ranging $1 to $100 accessible to ALL users.
      - 10 Creator Exclusive Gifts: Ranging $1 to $100.
      - 10 Influencer Exclusive Gifts: Ranging $1 to $100.
      - 10 Educator Exclusive Gifts: Ranging $1 to $100.
    Total = 100 distinct gift types.
    """
    catalog = {}

    # 1. 70 Universal Gifts ($1 - $100)
    universal_names = [
        "Coffee Cup", "High Five", "Party Sparkler", "Thumbs Up", "Heart Badge",
        "Panda Hug", "Silver Crown", "Magic Wand", "Golden Key", "Firework Rocket",
        "Rainbow Arch", "Neon Sign", "Diamond Gem", "Super Star", "Treasure Chest",
        "Crystal Ball", "Dragon Scale", "Phoenix Feather", "Cosmic Comet", "Golden Apple",
        "Space Rover", "Cyber Blade", "Quantum Core", "Hoverboard", "Solar Flare",
        "Laser Cannon", "Hyper Drive", "Astral Portal", "Plasma Shield", "Infinity Ring",
        "Galactic Map", "Time Capsule", "Starlight Orb", "Celestial Compass", "Nebula Cloud",
        "Vortex Crystal", "Supernova Blast", "Titan Shield", "Aether Gem", "Chrono Watch",
        "Titanium Core", "Aura Sphere", "Zenith Crown", "Apex Trophy", "Eclipse Ring",
        "Pulsar Beacon", "Orbital Station", "Quantum Engine", "Void Crystal", "Genesis Cube",
        "Omega Emblem", "Alpha Scepter", "Radiant Diamond", "Eternal Flame", "Luminous Pearl",
        "Stellar Torch", "Cosmic Scepter", "Astral Crown", "Infinite Horizon", "Singularity Orb",
        "Dark Matter Core", "Hyperion Prism", "Celestial Throne", "Galaxy Portal", "Aether Citadel",
        "Omni Catalyst", "Matrix Key", "Vector Beacon", "Cyber Spire", "Grand Apex Monument"
    ]

    for i in range(1, 71):
        name = universal_names[i - 1] if i - 1 < len(universal_names) else f"Universal Gift #{i}"
        price = float(i if i <= 50 else 50 + (i - 50) * 2.5) # Ranging $1 to $100
        price = round(price, 2)
        gift_id = f"GIFT_UNIV_{i:03d}"
        catalog[gift_id] = {
            "id": gift_id,
            "name": name,
            "price_usd": price,
            "credits": int(price * 100),
            "required_tier": "COMMON",
            "category": "UNIVERSAL"
        }

    # 2. 10 Creator Exclusive Gifts ($1 - $100)
    creator_names = [
        "Creator Mic", "Studio Light", "Gold Play Button", "Director Chair", "4K Camera",
        "Pro Synthesizer", "Vinyl Master", "Hologram Stage", "Producer Desk", "Masterpiece Frame"
    ]
    creator_prices = [2.00, 5.00, 12.00, 20.00, 35.00, 50.00, 65.00, 80.00, 90.00, 100.00]
    for idx, (name, price) in enumerate(zip(creator_names, creator_prices), 1):
        gift_id = f"GIFT_CREATOR_{idx:02d}"
        catalog[gift_id] = {
            "id": gift_id,
            "name": name,
            "price_usd": price,
            "credits": int(price * 100),
            "required_tier": "CREATOR",
            "category": "CREATOR_EXCLUSIVE"
        }

    # 3. 10 Influencer Exclusive Gifts ($1 - $100)
    influencer_names = [
        "VIP Pass", "Red Carpet", "Neon Spotlight", "Cyber Supercar", "Hollywood Star",
        "Golden Throne", "Fashion Runway", "Yacht Party", "Private Jet", "Met Gala Crown"
    ]
    influencer_prices = [3.00, 8.00, 15.00, 25.00, 40.00, 55.00, 70.00, 85.00, 95.00, 100.00]
    for idx, (name, price) in enumerate(zip(influencer_names, influencer_prices), 1):
        gift_id = f"GIFT_INFLUENCER_{idx:02d}"
        catalog[gift_id] = {
            "id": gift_id,
            "name": name,
            "price_usd": price,
            "credits": int(price * 100),
            "required_tier": "INFLUENCER",
            "category": "INFLUENCER_EXCLUSIVE"
        }

    # 4. 10 Educator Exclusive Gifts ($1 - $100)
    educator_names = [
        "Wisdom Scroll", "Graduation Cap", "Honor Quill", "Academy Podium", "Library Key",
        "Research Telescope", "Scholar Globe", "Universal Encyclopedia", "Observatory Tower", "Galaxy Castle"
    ]
    educator_prices = [1.50, 6.00, 10.00, 18.00, 30.00, 45.00, 60.00, 75.00, 88.00, 100.00]
    for idx, (name, price) in enumerate(zip(educator_names, educator_prices), 1):
        gift_id = f"GIFT_EDUCATOR_{idx:02d}"
        catalog[gift_id] = {
            "id": gift_id,
            "name": name,
            "price_usd": price,
            "credits": int(price * 100),
            "required_tier": "EDUCATOR",
            "category": "EDUCATOR_EXCLUSIVE"
        }

    return catalog

GIFT_CATALOG = _generate_100_gift_catalog()
TIER_HIERARCHY = {"COMMON": 0, "CREATOR": 1, "INFLUENCER": 2, "EDUCATOR": 3}
GIFT_PLATFORM_FEE_PERCENT = 0.02  # 2% Platform Fee

class KickBackGiftEngine:
    """
    Handles gift purchases across the expanded 100-gift catalog, tier gating,
    2% platform fee accounting, and Common-user monetization deferral.
    """

    @staticmethod
    def get_catalog() -> Dict[str, Dict[str, Any]]:
        return GIFT_CATALOG

    @staticmethod
    def get_catalog_by_category(category: str) -> List[Dict[str, Any]]:
        return [g for g in GIFT_CATALOG.values() if g["category"] == category.upper()]

    @staticmethod
    def calculate_gift_split(gift_id: str) -> Dict[str, Any]:
        if gift_id not in GIFT_CATALOG:
            raise ValueError(f"Gift '{gift_id}' not found in 100-gift catalog.")

        gift = GIFT_CATALOG[gift_id]
        gross_usd = gift["price_usd"]
        platform_fee_usd = round(gross_usd * GIFT_PLATFORM_FEE_PERCENT, 2)
        recipient_net_usd = round(gross_usd - platform_fee_usd, 2)

        return {
            "gift_id": gift_id,
            "gift_name": gift["name"],
            "required_tier": gift["required_tier"],
            "category": gift["category"],
            "gross_usd": gross_usd,
            "credits_value": gift["credits"],
            "platform_fee_percent": GIFT_PLATFORM_FEE_PERCENT * 100,
            "platform_fee_usd": platform_fee_usd,
            "recipient_net_usd": recipient_net_usd
        }

    @staticmethod
    def send_gift(
        sender_pubkey: str,
        sender_tier: str,
        recipient_pubkey: str,
        recipient_tier: str,
        gift_id: str,
        app_id: str = "THE_KICKBACK_MOBILE",
        prev_hash: str = "0" * 64
    ) -> Dict[str, Any]:
        if gift_id not in GIFT_CATALOG:
            raise ValueError(f"Invalid gift ID: {gift_id}")

        gift = GIFT_CATALOG[gift_id]
        required_tier = gift["required_tier"]

        # Universal gifts (COMMON tier) are accessible to ALL senders regardless of price ($1-$100)
        # Role-exclusive gifts require sender tier rank >= required tier
        if required_tier != "COMMON":
            if TIER_HIERARCHY[sender_tier.upper()] < TIER_HIERARCHY[required_tier]:
                raise ValueError(
                    f"Gift '{gift['name']}' (${gift['price_usd']:.2f}) is exclusive to {required_tier} tier access or higher. "
                    f"Sender is currently on {sender_tier} tier."
                )

        splits = KickBackGiftEngine.calculate_gift_split(gift_id)
        now_ms = int(time.time() * 1000)
        event_id = str(uuid.uuid4())

        is_recipient_common = (recipient_tier.upper() == "COMMON")
        monetization_status = "PENDING_UPGRADE_LOCK" if is_recipient_common else "AVAILABLE_FOR_CASHOUT"

        payload = {
            "gift_event_id": event_id,
            "app_id": app_id,
            "sender_pubkey": sender_pubkey,
            "sender_tier": sender_tier.upper(),
            "recipient_pubkey": recipient_pubkey,
            "recipient_tier": recipient_tier.upper(),
            "gift_id": gift_id,
            "gift_name": gift["name"],
            "category": gift["category"],
            "credits_spent": gift["credits"],
            "gross_usd": gift["price_usd"],
            "accounting_split": {
                "platform_fee_percent": 2.0,
                "platform_fee_usd": splits["platform_fee_usd"],
                "recipient_net_usd": splits["recipient_net_usd"],
                "monetization_status": monetization_status
            }
        }

        canonical_payload = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        hash_input = f"{prev_hash}:{now_ms}:{sender_pubkey}:GIFT_TRANSACTION_EVENT:{canonical_payload}"
        current_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

        return {
            "event_id": event_id,
            "timestamp": now_ms,
            "author_pubkey": sender_pubkey,
            "event_type": "GIFT_TRANSACTION_EVENT",
            "payload": payload,
            "prev_hash": prev_hash,
            "current_hash": current_hash
        }


class LiveGiftNotificationEngine:
    """
    Real-Time Live Gift Notification System for The KickBack & The-Omni-Hub P2P Mesh.
    Constructs real-time overlay notification events, animation visual metadata, and audio triggers.
    """

    @staticmethod
    def determine_visual_and_audio_effects(price_usd: float, category: str) -> Dict[str, Any]:
        """
        Maps gift price and tier category to live screen overlay animations and sound triggers.
        """
        if price_usd >= 75.00:
            overlay = "3D_GALACTIC_SUPERNOVA_OVERLAY"
            sound = "EPIC_ROYAL_FANFARE"
            duration_sec = 10
        elif price_usd >= 35.00:
            overlay = "NEON_SPOTLIGHT_BURST_3D"
            sound = "CELEBRATION_TRUMPET"
            duration_sec = 7
        elif price_usd >= 15.00:
            overlay = "GOLDEN_SHOWER_PARTICLES"
            sound = "CHIME_CASCADE_HIGH"
            duration_sec = 5
        else:
            overlay = "FLOAT_SPARKLE_BANNER"
            sound = "POP_BELL_SINGLE"
            duration_sec = 3

        return {
            "overlay_animation": overlay,
            "sound_effect": sound,
            "display_duration_sec": duration_sec,
            "banner_theme": category.lower()
        }

    @staticmethod
    def create_live_gift_notification(
        gift_event: Dict[str, Any],
        sender_username: str,
        recipient_username: str
    ) -> Dict[str, Any]:
        """
        Transforms a signed GIFT_TRANSACTION_EVENT into a broadcastable LIVE_GIFT_NOTIFICATION event.
        """
        payload = gift_event["payload"]
        price_usd = payload["gross_usd"]
        category = payload["category"]
        effects = LiveGiftNotificationEngine.determine_visual_and_audio_effects(price_usd, category)

        notification_id = str(uuid.uuid4())
        now_ms = int(time.time() * 1000)

        notif_payload = {
            "notification_id": notification_id,
            "gift_event_id": gift_event["event_id"],
            "app_id": payload["app_id"],
            "sender_pubkey": payload["sender_pubkey"],
            "sender_username": sender_username,
            "sender_tier": payload["sender_tier"],
            "recipient_pubkey": payload["recipient_pubkey"],
            "recipient_username": recipient_username,
            "gift_id": payload["gift_id"],
            "gift_name": payload["gift_name"],
            "gross_usd": price_usd,
            "credits_spent": payload["credits_spent"],
            "recipient_net_usd": payload["accounting_split"]["recipient_net_usd"],
            "visual_effects": effects,
            "broadcast_timestamp": now_ms
        }

        return {
            "event_id": notification_id,
            "timestamp": now_ms,
            "event_type": "LIVE_GIFT_NOTIFICATION",
            "payload": notif_payload
        }
