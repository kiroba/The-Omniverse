"""
============================================================================
THE OMNIVERSE ROLE-BASED ENTITLEMENT & P2P MILESTONE UNLOCK ENGINE
Repository: kiroba/The-Omni-Hub, kiroba/Continuity-Engine
Author: Gemini Notebook / Omniverse System Core

Description:
  Hybrid Feature Entitlement Engine combining:
  1. DAY-1 BASELINE UNLOCKS: LPE 3D Plaza & The KickBack Core Feed
  2. ROLE-BASED LICENSING INJECTIONS: Instant feature unlocks for purchased
     roles (e.g., Educator, Store Owner, Venue Host, Creator Pro), bypassing
     global peer milestone locks for role dependencies.
  3. P2P SWARM MILESTONE CONSENSUS: Global swarm-wide feature unlocks when
     active peer counts cross milestone thresholds.
============================================================================
"""

import time
import uuid
import hashlib
from typing import Dict, List, Set, Any
from cryptography.hazmat.primitives.asymmetric import ed25519

# Day 1 Default Unlocked Modules in SuperApp
DAY_1_BASELINE_MODULES: Set[str] = {
    "MODULE_KICKBACK_CORE",   # Social feed, P2P messaging, live reactions
    "MODULE_LPE_3D_PLAZA",    # Live Persona Engine 3D World Plaza & Avatar customizer
}

# Role Definitions and their Required Feature Dependencies
ROLE_FEATURE_DEPENDENCIES: Dict[str, List[str]] = {
    "ROLE_COMMON_USER": [],
    "ROLE_CREATOR_PRO": [
        "MODULE_MESH_FUSION_PRO",       # Multi-camera WebRTC stream fusion
        "MODULE_CREATOR_PAYWALL",       # Tiered subscriptions & paid posts
    ],
    "ROLE_STORE_OWNER": [
        "MODULE_NEIGHBORHOOD_EATERY",   # Local eatery & store menu stream
        "MODULE_SPATIAL_ANCHORS",       # Local AR table & venue anchors
        "MODULE_STOREFRONT_MINI_APP",   # On-device catalog & instant checkout
    ],
    "ROLE_EDUCATOR": [
        "MODULE_EDUCATOR_STUDIO",       # Desktop broadcast studio
        "MODULE_ZK_EMAIL_VERIFIER",     # ZK email proof for educator discount
        "MODULE_COMPLIANCE_ENCLAVE",    # Student safety & compliance guardrails
    ],
    "ROLE_VENUE_HOST": [
        "MODULE_NEIGHBORHOOD_EATERY",   # Hyper-local neighborhood discovery
        "MODULE_SPATIAL_ANCHORS",       # AR spatial venue placement
        "MODULE_MESH_FUSION_PRO",       # Multi-angle venue broadcasting
    ]
}

# Global Swarm Milestone Unlocks (For All General Users)
MILESTONE_THRESHOLDS: Dict[str, int] = {
    "MODULE_SPATIAL_ANCHORS": 10000,
    "MODULE_NEIGHBORHOOD_EATERY": 25000,
    "MODULE_MESH_FUSION_PRO": 50000,
    "MODULE_STOREFRONT_MINI_APP": 75000,
}


class UserRoleEntitlementProfile:
    def __init__(self, user_pubkey: str):
        self.user_pubkey = user_pubkey
        self.purchased_roles: Set[str] = {"ROLE_COMMON_USER"}
        self.active_role_overrides: Set[str] = set()

    def purchase_role(self, role_id: str, payment_proof_hash: str) -> bool:
        if role_id not in ROLE_FEATURE_DEPENDENCIES:
            raise ValueError(f"Unknown role identifier: {role_id}")
        
        # Add purchased role and compute feature overrides
        self.purchased_roles.add(role_id)
        granted_features = ROLE_FEATURE_DEPENDENCIES[role_id]
        self.active_role_overrides.update(granted_features)
        return True


class OmniverseHybridEntitlementEngine:
    def __init__(self):
        self.global_peer_count: int = 0
        self.global_unlocked_milestones: Set[str] = set()

    def update_global_swarm_count(self, verified_peer_count: int):
        self.global_peer_count = verified_peer_count
        
        # Check global milestone thresholds
        for module_id, threshold in MILESTONE_THRESHOLDS.items():
            if verified_peer_count >= threshold:
                self.global_unlocked_milestones.add(module_id)

    def evaluate_user_unlocked_modules(self, user_profile: UserRoleEntitlementProfile) -> Dict[str, Any]:
        """
        Computes the complete active module feature set for a user:
        Active Modules = Day 1 Baseline UNION Global Milestones UNION Role Purchases
        """
        active_modules: Set[str] = set(DAY_1_BASELINE_MODULES)
        active_modules.update(self.global_unlocked_milestones)
        active_modules.update(user_profile.active_role_overrides)

        # Categorize granted features by source
        breakdown = {}
        for mod in active_modules:
            sources = []
            if mod in DAY_1_BASELINE_MODULES:
                sources.append("DAY_1_BASELINE")
            if mod in self.global_unlocked_milestones:
                sources.append("GLOBAL_SWARM_MILESTONE")
            if mod in user_profile.active_role_overrides:
                sources.append("PURCHASED_ROLE_INJECTION")
            breakdown[mod] = sources

        return {
            "user_pubkey": user_profile.user_pubkey,
            "purchased_roles": list(user_profile.purchased_roles),
            "global_peer_count": self.global_peer_count,
            "total_unlocked_count": len(active_modules),
            "active_modules": list(active_modules),
            "feature_breakdown": breakdown
        }


def run_hybrid_entitlement_test():
    print("\n=========================================================================")
    print("  OMNIVERSE HYBRID ROLE-BASED & SWARM MILESTONE ENTITLEMENT TEST")
    print("=========================================================================\n")

    engine = OmniverseHybridEntitlementEngine()
    user_alice = UserRoleEntitlementProfile(user_pubkey="pubkey_alice_001")

    # 1. Day 1 Launch Check (Initial peer count = 500)
    engine.update_global_swarm_count(500)
    res_day1 = engine.evaluate_user_unlocked_modules(user_alice)
    
    print("[-] [TEST 1] Day 1 Standard User Baseline (500 Peers, No Purchases):")
    print(f"    ↳ Active Modules: {res_day1['active_modules']}")
    assert "MODULE_KICKBACK_CORE" in res_day1['active_modules']
    assert "MODULE_LPE_3D_PLAZA" in res_day1['active_modules']
    assert "MODULE_NEIGHBORHOOD_EATERY" not in res_day1['active_modules']

    # 2. Alice Purchases ROLE_STORE_OWNER
    print("\n[-] [TEST 2] Alice Purchases 'ROLE_STORE_OWNER' (Global Peers = 500 < 25,000 Milestone):")
    user_alice.purchase_role("ROLE_STORE_OWNER", payment_proof_hash="hash_tx_992182")
    res_purchased = engine.evaluate_user_unlocked_modules(user_alice)
    
    print(f"    ↳ Unlocked Modules for Store Owner Alice:")
    for mod, sources in res_purchased['feature_breakdown'].items():
        print(f"      • {mod:<30}: Unlocked via {sources}")

    assert "MODULE_NEIGHBORHOOD_EATERY" in res_purchased['active_modules']
    assert "MODULE_STOREFRONT_MINI_APP" in res_purchased['active_modules']
    print("    ✅ SUCCESS: Role-based injection unlocked Neighborhood & Storefront features prior to global milestone!")

    # 3. Global Swarm Hits 30,000 Peers (Unlocks Neighborhood globally for all users)
    print("\n[-] [TEST 3] Global Swarm Crosses 30,000 Active Peers:")
    engine.update_global_swarm_count(30000)
    
    user_bob = UserRoleEntitlementProfile(user_pubkey="pubkey_bob_002") # Common User
    res_bob = engine.evaluate_user_unlocked_modules(user_bob)
    print(f"    ↳ Unlocked Modules for Common User Bob (No Purchases):")
    for mod, sources in res_bob['feature_breakdown'].items():
        print(f"      • {mod:<30}: Unlocked via {sources}")

    assert "MODULE_NEIGHBORHOOD_EATERY" in res_bob['active_modules']
    print("    ✅ SUCCESS: Global milestone unlocked Neighborhood feature for Common User Bob!")

    print("\n=========================================================================")
    print("  HYBRID ENTITLEMENT ENGINE TEST: ALL ASSERTIONS PASSED [100%]")
    print("=========================================================================\n")


if __name__ == "__main__":
    run_hybrid_entitlement_test()
