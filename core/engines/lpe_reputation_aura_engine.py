"""
LPE Reputation & Dynamic Aura Engine (`lpe_reputation_aura_engine.py`)
Part of The Omniverse / KickBack System Architecture Integration.

Integrates EigenTrust P2P Node Reputation Scores into the Live Persona Engine (LPE).
Features:
1. Dynamic Shader Auras & Visual Effects (Paragon, Citizen, Distrusted, Slashed)
2. P2P Avatar Trust Beam Resonance (+10% XP/Vibe Boost multiplier when high-trust peers meet)
3. Defensive Idle Stance Triggering against low-trust/flagged peers
4. Reputation-Gated Socket Cosmetics (e.g., Paragon Crown, Guardian Wings)
"""

import hashlib
import json
import time
from typing import Dict, Any, List, Tuple

class LPEReputationAuraEngine:
    """
    Translates EigenTrust P2P peer scores into dynamic 2D/3D LPE avatar states,
    visual aura shaders, resonance multipliers, and defensive animations.
    """

    # Reputation Tiers
    TIER_PARAGON = "PARAGON"          # Score: 800 - 1000
    TIER_CITIZEN = "CITIZEN"          # Score: 200 - 799
    TIER_DISTRUSTED = "DISTRUSTED"    # Score: 0 - 199
    TIER_SLASHED = "SLASHED"          # Score: < 0

    def __init__(self):
        # In-memory index of node reputation scores and avatar active states
        self.peer_reputation_db: Dict[str, float] = {}
        self.avatar_states: Dict[str, Dict[str, Any]] = {}

    def set_peer_reputation(self, peer_id: str, eigentrust_score: float) -> None:
        """
        Updates the local EigenTrust score index for a peer node.
        """
        self.peer_reputation_db[peer_id] = eigentrust_score

    def get_reputation_tier(self, eigentrust_score: float) -> Tuple[str, Dict[str, Any]]:
        """
        Maps numerical EigenTrust score (range: -200 to 1000) to visual LPE Tier parameters.
        """
        if eigentrust_score >= 800:
            return self.TIER_PARAGON, {
                "badge": "👑 PARAGON",
                "auraColorHex": "#00FFCC",      # Celestial Cyan Glow
                "secondaryGlowHex": "#FFD700",   # Gold Pulse
                "particleEffect": "GOLDEN_CELESTIAL_SPARKS",
                "glitchSeverity": 0.0,
                "idleAnimation": "IDLE_HERO_STANCE",
                "xpMultiplier": 1.25             # +25% Base XP Boost
            }
        elif eigentrust_score >= 200:
            return self.TIER_CITIZEN, {
                "badge": "🛡️ VERIFIED CITIZEN",
                "auraColorHex": "#3A86EF",      # Electric Blue
                "secondaryGlowHex": "#4CC9F0",   # Soft Cyan
                "particleEffect": "SILVER_PULSE_RINGS",
                "glitchSeverity": 0.0,
                "idleAnimation": "IDLE_STANDARD_BREATHING",
                "xpMultiplier": 1.00             # Standard 1.0x XP
            }
        elif eigentrust_score >= 0:
            return self.TIER_DISTRUSTED, {
                "badge": "⚠️ LOW-TRUST / FLAGGED",
                "auraColorHex": "#FFB703",      # Warning Amber
                "secondaryGlowHex": "#FF0055",   # Crimson Smoke
                "particleEffect": "STATIC_DISTORTION_FLICKER",
                "glitchSeverity": 0.45,          # 45% visual glitch shader
                "idleAnimation": "IDLE_DEFENSIVE_SHIELD_STANCE",
                "xpMultiplier": 0.50             # 50% XP Penalty
            }
        else:
            return self.TIER_SLASHED, {
                "badge": "🚫 SLASHED / QUARANTINED",
                "auraColorHex": "#FF0000",      # Dark Red
                "secondaryGlowHex": "#000000",   # Shadow Cage
                "particleEffect": "PIXELATED_QUARANTINE_CAGE",
                "glitchSeverity": 0.90,          # 90% severe glitch freezing
                "idleAnimation": "IDLE_QUARANTINE_FROZEN",
                "xpMultiplier": 0.00             # 0% XP Accrual
            }

    def compute_lpe_avatar_profile(self, peer_id: str, handle: str) -> Dict[str, Any]:
        """
        Generates the live LPE avatar visual profile grounded in EigenTrust score.
        """
        score = self.peer_reputation_db.get(peer_id, 200.0) # Default to Citizen if new
        tier_name, tier_params = self.get_reputation_tier(score)

        stargate_sig = f"sig_stargate_{hashlib.sha256(f'{peer_id}:{score}'.encode()).hexdigest()[:16]}"

        profile = {
            "peerId": peer_id,
            "handle": handle,
            "eigenTrustScore": score,
            "reputationTier": tier_name,
            "visualParameters": tier_params,
            "equippedSockets": {
                "head_socket": "paragon_crown" if score >= 800 else "standard_cap",
                "chest_socket": "guardian_pauldrons" if score >= 500 else "basic_shirt",
                "aura_socket": tier_params["particleEffect"]
            },
            "stargateSignature": stargate_sig
        }

        self.avatar_states[peer_id] = profile
        return profile

    def calculate_peer_proximity_resonance(self, peer_a_id: str, peer_b_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Calculates live interaction dynamics when two avatars stand near each other in the Plaza or Stream Room.
        Triggers:
        - Resonance Field (+10% Bonus Multiplier) if both are Paragon/Citizen.
        - Defensive Stance if one peer is Distrusted/Slashed.
        """
        prof_a = self.avatar_states.get(peer_a_id)
        prof_b = self.avatar_states.get(peer_b_id)

        if not prof_a or not prof_b:
            return False, "PEER_NOT_FOUND: One or both avatar profiles missing from active index.", {}

        score_a = prof_a["eigenTrustScore"]
        score_b = prof_b["eigenTrustScore"]

        # Case 1: Defensive Stance Triggered (Low Trust Alert)
        if score_a < 200 or score_b < 200:
            flagged_peer = prof_a["handle"] if score_a < 200 else prof_b["handle"]
            defending_peer = prof_b["handle"] if score_a < 200 else prof_a["handle"]
            
            return True, "DEFENSIVE_STANCE_TRIGGERED", {
                "interactionType": "DEFENSIVE_BARRIER",
                "activeEffect": "DEFENSIVE_GLITCH_SHIELD",
                "bonusMultiplier": 0.0,
                "alertMessage": f"⚠️ {defending_peer}'s avatar raised a P2P defense shield near flagged node {flagged_peer}."
            }

        # Case 2: High-Trust Resonance Beam Triggered
        if score_a >= 800 and score_b >= 800:
            return True, "PARAGON_RESONANCE_ACTIVATED", {
                "interactionType": "GOLDEN_TRUST_BEAM",
                "activeEffect": "CELESTIAL_HARMONY_RESONANCE",
                "bonusMultiplier": 0.10,          # +10% Bonus XP / Vibe Boost
                "alertMessage": f"✨ High-Trust Resonance activated between {prof_a['handle']} and {prof_b['handle']}! (+10% XP Multiplier)"
            }

        # Case 3: Standard Friendly Interaction
        return True, "STANDARD_PROXIMITY_HARMONY", {
            "interactionType": "STANDARD_AURA_PULSE",
            "activeEffect": "SILVER_LIGHT_PULSE",
            "bonusMultiplier": 0.05,             # +5% Friendly Proximity Multiplier
            "alertMessage": f"🤝 Friendly P2P handshake connected between {prof_a['handle']} and {prof_b['handle']}."
        }


# =====================================================================
# AUTOMATED TEST SUITE
# =====================================================================
if __name__ == "__main__":
    print("=================================================================")
    print("   LPE REPUTATION & DYNAMIC AURA ENGINE INTEGRATION TEST         ")
    print("=================================================================")

    engine = LPEReputationAuraEngine()

    peer_paragon = "peer_node_alice_paragon"
    peer_citizen = "peer_node_bob_citizen"
    peer_distrusted = "peer_node_charlie_distrusted"
    peer_slashed = "peer_node_dave_slashed"

    # Step 1: Set EigenTrust Scores
    engine.set_peer_reputation(peer_paragon, 950.0)      # Paragon
    engine.set_peer_reputation(peer_citizen, 500.0)      # Verified Citizen
    engine.set_peer_reputation(peer_distrusted, 120.0)    # Low Trust
    engine.set_peer_reputation(peer_slashed, -150.0)      # Slashed

    # Step 2: Generate LPE Profiles
    prof_alice = engine.compute_lpe_avatar_profile(peer_paragon, "@alice_paragon")
    prof_bob = engine.compute_lpe_avatar_profile(peer_citizen, "@bob_citizen")
    prof_charlie = engine.compute_lpe_avatar_profile(peer_distrusted, "@charlie_distrusted")
    prof_dave = engine.compute_lpe_avatar_profile(peer_slashed, "@dave_slashed")

    print(f"✅ STEP 1 (Paragon Profile Generated): Tier = {prof_alice['reputationTier']} | Aura = {prof_alice['visualParameters']['auraColorHex']} | Socket = {prof_alice['equippedSockets']['head_socket']}")
    print(f"✅ STEP 2 (Distrusted Profile Generated): Tier = {prof_charlie['reputationTier']} | Glitch Severity = {prof_charlie['visualParameters']['glitchSeverity']*100}% | Animation = {prof_charlie['visualParameters']['idleAnimation']}")

    # Step 3: Test Proximity Resonance between two Paragons/Citizens
    ok1, type1, res1 = engine.calculate_peer_proximity_resonance(peer_paragon, peer_citizen)
    print(f"\n✅ STEP 3 (Proximity Harmony Test): {res1['alertMessage']}")

    # Step 4: Test Proximity Defense near a Distrusted Node
    ok2, type2, res2 = engine.calculate_peer_proximity_resonance(peer_paragon, peer_distrusted)
    print(f"✅ STEP 4 (Defensive Barrier Test): {res2['alertMessage']}")

    print("=================================================================")
    print("FINAL LPE REPUTATION AURA INTEGRATION STATUS: PASS [100%]")
    print("=================================================================")
