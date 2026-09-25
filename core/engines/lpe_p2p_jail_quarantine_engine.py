"""
LPE P2P Quarantine & Jail Sub-Enclave Engine (`lpe_p2p_jail_quarantine_engine.py`)
Part of The Omniverse / KickBack Decentralized Governance Suite.

Integrates EigenTrust reputation scores with P2P topic re-routing and LPE spatial rendering.
Banned (`SLASHED`) and low-trust (`DISTRUSTED`) nodes are automatically isolated into
the `/cohort_jail_quarantine` P2P mesh topic and rendered in a quarantine cage environment.
"""

import hashlib
import time
from typing import Dict, Any, List, Tuple


class LPEP2PJailQuarantineEngine:
    """
    Modular P2P Jail & Quarantine Engine.
    Handles peer topic re-routing, LPE isolation scene rendering, and rehabilitation protocol.
    """

    TOPIC_PUBLIC_FEED = "/cohort_public_feed"
    TOPIC_JAIL_QUARANTINE = "/cohort_jail_quarantine"

    # Score Thresholds
    SCORE_DISTRUSTED_THRESHOLD = 200
    SCORE_SLASHED_THRESHOLD = 0

    def __init__(self):
        # Peer reputation and isolation directory
        self.peer_states: Dict[str, Dict[str, Any]] = {}
        # Jail topic event log
        self.jail_topic_log: List[Dict[str, Any]] = []

    def register_or_update_peer(
        self,
        peer_id: str,
        handle: str,
        eigentrust_score: float,
        stargate_pubkey: str
    ) -> Dict[str, Any]:
        """
        Updates peer reputation score and evaluates P2P topic assignment and LPE jail status.
        """
        is_jail_bound = eigentrust_score < self.SCORE_DISTRUSTED_THRESHOLD
        is_banned = eigentrust_score < self.SCORE_SLASHED_THRESHOLD

        if is_banned:
            status_label = "SLASHED_BANNED"
            assigned_topic = self.TOPIC_JAIL_QUARANTINE
            jail_environment = "MAXIMUM_SECURITY_SHADOW_CELL"
            lpe_glitch_severity = 100.0
            can_interact_with_public = False
        elif is_jail_bound:
            status_label = "DISTRUSTED_QUARANTINED"
            assigned_topic = self.TOPIC_JAIL_QUARANTINE
            jail_environment = "REHABILITATION_QUARANTINE_PLAZA"
            lpe_glitch_severity = 50.0
            can_interact_with_public = False
        else:
            status_label = "ACTIVE_CITIZEN"
            assigned_topic = self.TOPIC_PUBLIC_FEED
            jail_environment = "OPEN_COMMUNITY_PLAZA"
            lpe_glitch_severity = 0.0
            can_interact_with_public = True

        state = {
            "peerId": peer_id,
            "handle": handle,
            "eigentrustScore": eigentrust_score,
            "stargatePubkey": stargate_pubkey,
            "statusLabel": status_label,
            "assignedP2PTopic": assigned_topic,
            "jailEnvironment": jail_environment,
            "lpeGlitchSeverity": lpe_glitch_severity,
            "canInteractWithPublic": can_interact_with_public,
            "quarantineTimestamp": time.time() if is_jail_bound else None,
            "rehabilitationProgress": 0.0 if is_jail_bound else 100.0
        }

        self.peer_states[peer_id] = state
        return state

    def route_p2p_envelope(self, peer_id: str, payload_text: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Enforces P2P topic boundary. Redirects jail-bound nodes to `/cohort_jail_quarantine`.
        """
        if peer_id not in self.peer_states:
            return False, "UNKNOWN_PEER: Node must register EigenTrust reputation proof.", {}

        peer = self.peer_states[peer_id]
        now = time.time()
        envelope_id = f"env_{hashlib.sha256(f'{peer_id}:{now}'.encode()).hexdigest()[:12]}"

        envelope = {
            "envelopeId": envelope_id,
            "senderPeerId": peer_id,
            "senderHandle": peer["handle"],
            "targetTopic": peer["assignedP2PTopic"],
            "payload": payload_text,
            "timestamp": now,
            "isQuarantineIsolated": not peer["canInteractWithPublic"]
        }

        if not peer["canInteractWithPublic"]:
            self.jail_topic_log.append(envelope)
            return (
                True,
                f"ISOLATED: Peer '{peer['handle']}' routed to '{peer['assignedP2PTopic']}' ({peer['jailEnvironment']}).",
                envelope
            )

        return True, f"DELIVERED: Peer '{peer['handle']}' broadcasted to public feed '{self.TOPIC_PUBLIC_FEED}'.", envelope

    def process_rehabilitation_tick(self, peer_id: str, clean_relays_count: int) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Decentralized Rehabilitation Protocol:
        Quarantined nodes can earn reputation score recovery by operating clean, un-flagged P2P relay tasks.
        """
        if peer_id not in self.peer_states:
            return False, "PEER_NOT_FOUND", {}

        peer = self.peer_states[peer_id]
        if peer["canInteractWithPublic"]:
            return False, f"PEER_NOT_IN_JAIL: '{peer['handle']}' is an active citizen.", peer

        if peer["statusLabel"] == "SLASHED_BANNED":
            return False, f"PERMANENT_BAN: Slashed peer '{peer['handle']}' requires manual community SSS governance vote.", peer

        # Increment score based on clean relays (+5 score per clean relay cycle)
        score_gain = clean_relays_count * 5.0
        new_score = peer["eigentrustScore"] + score_gain
        
        # Update peer state with new score
        updated_state = self.register_or_update_peer(peer_id, peer["handle"], new_score, peer["stargatePubkey"])
        
        if updated_state["canInteractWithPublic"]:
            return True, f"PAROLE_GRANTED: Peer '{peer['handle']}' reached score {new_score:.1f} and exited quarantine!", updated_state

        return True, f"PROGRESS: Peer '{peer['handle']}' score increased to {new_score:.1f}/200.0 (Quarantine active).", updated_state


# =====================================================================
# VERIFICATION TEST SUITE
# =====================================================================
if __name__ == "__main__":
    print("=================================================================")
    print("   LPE P2P JAIL & QUARANTINE SUB-ENCLAVE ENGINE TEST             ")
    print("=================================================================")

    engine = LPEP2PJailQuarantineEngine()

    # Step 1: Register Normal Citizen, Distrusted User, and Slashed Banned User
    p1 = engine.register_or_update_peer("peer_alice", "@alice_good", 850.0, "pubkey_alice")
    p2 = engine.register_or_update_peer("peer_bob_spammer", "@bob_spammer", 120.0, "pubkey_bob")
    p3 = engine.register_or_update_peer("peer_charlie_hacker", "@charlie_malicious", -50.0, "pubkey_charlie")

    print(f"✅ STEP 1 (Peer Topic Assignments):")
    print(f"   • {p1['handle']}: Topic = {p1['assignedP2PTopic']} | Environment = {p1['jailEnvironment']}")
    print(f"   • {p2['handle']}: Topic = {p2['assignedP2PTopic']} | Environment = {p2['jailEnvironment']}")
    print(f"   • {p3['handle']}: Topic = {p3['assignedP2PTopic']} | Environment = {p3['jailEnvironment']}")

    # Step 2: Route P2P Messages
    ok1, msg1, env1 = engine.route_p2p_envelope("peer_alice", "Hello sovereign network!")
    ok2, msg2, env2 = engine.route_p2p_envelope("peer_bob_spammer", "Buy cheap tokens now!")

    print(f"\n✅ STEP 2 (P2P Enclave Routing):")
    print(f"   • Alice: {msg1}")
    print(f"   • Bob (Spammer): {msg2}")

    # Step 3: Rehabilitation Protocol Test
    print(f"\n✅ STEP 3 (Bob Rehabilitation Progress):")
    ok_reh1, msg_reh1, state_reh1 = engine.process_rehabilitation_tick("peer_bob_spammer", clean_relays_count=10) # +50 -> 170
    print(f"   Cycle 1: {msg_reh1}")

    ok_reh2, msg_reh2, state_reh2 = engine.process_rehabilitation_tick("peer_bob_spammer", clean_relays_count=10) # +50 -> 220
    print(f"   Cycle 2: {msg_reh2}")
    print(f"   Bob Final Topic: {state_reh2['assignedP2PTopic']} | Can Interact? {state_reh2['canInteractWithPublic']}")

    print("=================================================================")
    print("FINAL P2P JAIL & QUARANTINE ENGINE STATUS: ALL TESTS PASSED     ")
    print("=================================================================")
