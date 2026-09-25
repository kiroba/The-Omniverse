"""
P2P Node Score Decay & Recovery Tuning Engine
The-Omni-Hub P2P GossipSub Mesh Transport
=================================================================
Simulates and validates peer node scoring, score decay rates,
slashing penalties, and dynamic score recovery mechanics for
GossipSub overlay routing in KickBack Universe.
"""

import time
import math
import json
from typing import Dict, List, Any

class P2PNodeScorer:
    def __init__(self):
        # GossipSub Scoring Weights & Thresholds
        self.W_TIME_IN_MESH = 0.2
        self.W_FIRST_DELIVERIES = 1.0
        self.W_MESH_DELIVERIES = 0.5
        self.W_INVALID_MESSAGES = -100.0  # Harsh slashing penalty
        self.W_ATTESTATION = 50.0         # Hardware Remote Attestation bonus

        self.DECAY_INTERVAL_SEC = 1.0     # 1 second epoch
        self.SCORE_DECAY_FACTOR = 0.70    # 30% decay of penalties per epoch
        self.GRAYLIST_THRESHOLD = -50.0
        self.BAN_THRESHOLD = -200.0
        self.MAX_SCORE = 100.0

    def compute_peer_score(self, peer_state: Dict[str, Any]) -> float:
        """Compute holistic peer score based on GossipSub parameters."""
        p_time = min(peer_state.get("time_in_mesh", 0) / 3600.0, 10.0) * self.W_TIME_IN_MESH
        p_first = min(peer_state.get("first_deliveries", 0), 100) * self.W_FIRST_DELIVERIES
        p_mesh = min(peer_state.get("mesh_deliveries", 0), 50) * self.W_MESH_DELIVERIES
        p_invalid = peer_state.get("invalid_messages", 0.0) * abs(self.W_INVALID_MESSAGES)
        p_attest = self.W_ATTESTATION if peer_state.get("attested", False) else -50.0

        raw_score = p_time + p_first + p_mesh - p_invalid + p_attest
        return max(min(raw_score, self.MAX_SCORE), self.BAN_THRESHOLD - 10.0)

    def apply_epoch_decay(self, peer_state: Dict[str, Any]) -> Dict[str, Any]:
        """Compute score for current epoch then decay delivery and penalty counters."""
        current_score = self.compute_peer_score(peer_state)
        peer_state["current_score"] = current_score

        if current_score <= self.BAN_THRESHOLD:
            peer_state["status"] = "BANNED"
        elif current_score <= self.GRAYLIST_THRESHOLD:
            peer_state["status"] = "GRAYLISTED"
        else:
            peer_state["status"] = "HEALTHY"

        # Apply state decay for next epoch
        peer_state["first_deliveries"] = float(peer_state.get("first_deliveries", 0) * 0.95)
        peer_state["mesh_deliveries"] = float(peer_state.get("mesh_deliveries", 0) * 0.95)
        peer_state["invalid_messages"] = float(peer_state.get("invalid_messages", 0.0) * self.SCORE_DECAY_FACTOR)
        peer_state["time_in_mesh"] = peer_state.get("time_in_mesh", 0) + self.DECAY_INTERVAL_SEC

        return peer_state

def run_p2p_score_decay_tuning_suite():
    scorer = P2PNodeScorer()
    
    print("=================================================================")
    print("      THE-OMNI-HUB: P2P NODE SCORE DECAY & RECOVERY SUITE        ")
    print("=================================================================")

    # Test 1: Healthy Node Steady State
    healthy_peer = {
        "peer_id": "12D3KooW_HealthyPeerAlpha",
        "time_in_mesh": 1200,
        "first_deliveries": 25,
        "mesh_deliveries": 40,
        "invalid_messages": 0.0,
        "attested": True
    }
    score_1 = scorer.compute_peer_score(healthy_peer)
    assert score_1 >= 50.0, f"Healthy peer score too low: {score_1}"
    print(f"✅ TEST 1 (Healthy Node Scoring): PASS [Score: {score_1:.2f} | Status: HEALTHY]")

    # Test 2: Transient Packet Corruption & Recovery Trajectory
    glitch_peer = {
        "peer_id": "12D3KooW_TransientGlitchPeer",
        "time_in_mesh": 600,
        "first_deliveries": 10,
        "mesh_deliveries": 15,
        "invalid_messages": 1.5, # 1.5 bad packets penalty -> raw score ~ -82.5 (GRAYLISTED)
        "attested": True
    }
    
    # Epoch 0: Glitch causes graylisting
    decayed_0 = scorer.apply_epoch_decay(glitch_peer)
    assert decayed_0["status"] == "GRAYLISTED", f"Expected GRAYLISTED, got {decayed_0['status']}"
    
    # Simulate 5 epochs of good behavior and decay of invalid message count
    for epoch in range(5):
        decayed_0["first_deliveries"] += 5
        decayed_0 = scorer.apply_epoch_decay(decayed_0)

    assert decayed_0["status"] == "HEALTHY", f"Peer failed to recover! Status: {decayed_0['status']}"
    print(f"✅ TEST 2 (Transient Glitch Recovery): PASS [Recovered to HEALTHY in 5 Epochs | Score: {decayed_0['current_score']:.2f}]")

    # Test 3: Malicious Bot Slashing & Unrecoverable Ban
    malicious_peer = {
        "peer_id": "12D3KooW_MaliciousSpamNode",
        "time_in_mesh": 10,
        "first_deliveries": 0,
        "mesh_deliveries": 0,
        "invalid_messages": 3.0, # 3 invalid packets -> -300 penalty -> BANNED
        "attested": False
    }
    banned_state = scorer.apply_epoch_decay(malicious_peer)
    assert banned_state["status"] == "BANNED", f"Expected BANNED, got {banned_state['status']}"
    print(f"✅ TEST 3 (Malicious Peer Immediate Ban): PASS [Score: {banned_state['current_score']:.2f} | Status: BANNED]")

    print("\n=================================================================")
    print("FINAL P2P NODE SCORE DECAY & RECOVERY STATUS: PASS")
    print("=================================================================")

if __name__ == "__main__":
    run_p2p_score_decay_tuning_suite()
