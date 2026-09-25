"""
============================================================================
THE OMNIVERSE P2P MILESTONE CONSENSUS & MODULE UNLOCK ENGINE
Repository: kiroba/The-Omni-Hub, kiroba/Continuity-Engine
Author: Gemini Notebook / Omniverse System Core

Description:
  Calculates active user node count thresholds across local P2P Merkle
  state trees without centralized telemetry servers. When user milestones
  (e.g., 25,000 verified human nodes) are reached, it automatically triggers
  module feature flags to stream standalone showcase app features directly
  into The Omniverse SuperApp interface.
============================================================================
"""

import hashlib
import json
import time
import uuid
from typing import Dict, List, Any, Optional
from cryptography.hazmat.primitives.asymmetric import ed25519


class P2PMilestoneAttestation:
    """
    Represents a signed attestation from a peer node verifying active local swarm members.
    """
    def __init__(self, node_pubkey: str, active_peer_count: int, timestamp: int):
        self.node_pubkey = node_pubkey
        self.active_peer_count = active_peer_count
        self.timestamp = timestamp
        self.signature = ""

    def compute_hash(self) -> str:
        data = f"{self.node_pubkey}:{self.active_peer_count}:{self.timestamp}"
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def sign(self, private_key: ed25519.Ed25519PrivateKey):
        msg_hash = self.compute_hash()
        self.signature = private_key.sign(msg_hash.encode('utf-8')).hex()

    def verify(self) -> bool:
        if not self.signature:
            return False
        try:
            pub_bytes = bytes.fromhex(self.node_pubkey)
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            msg_hash = self.compute_hash()
            public_key.verify(bytes.fromhex(self.signature), msg_hash.encode('utf-8'))
            return True
        except Exception:
            return False


class MilestoneThresholdConfig:
    """
    Defines threshold milestones for unlocking module streams inside the SuperApp.
    """
    MILESTONES = {
        "MODULE_LPE_3D_PLAZA": {
            "required_peers": 5000,
            "description": "Unlocks 3D Avatar Plazas in SuperApp",
            "unlocked": False
        },
        "MODULE_NEIGHBORHOOD_EATERY": {
            "required_peers": 25000,
            "description": "Unlocks Local Neighborhood & Eatery Stream in SuperApp",
            "unlocked": False
        },
        "MODULE_MESH_FUSION_PRO": {
            "required_peers": 50000,
            "description": "Unlocks Multi-Angle WebRTC Camera Fusion in SuperApp",
            "unlocked": False
        }
    }


class P2PMilestoneConsensusEngine:
    """
    Evaluates peer node attestations across the GossipSub swarm to trigger
    decentralized feature unlocks in the SuperApp.
    """
    def __init__(self, local_node_id: str):
        self.local_node_id = local_node_id
        self.private_key = ed25519.Ed25519PrivateKey.generate()
        self.public_key_hex = self.private_key.public_key().public_bytes_raw().hex()
        self.attestations: Dict[str, P2PMilestoneAttestation] = {}
        self.unlocked_modules: Dict[str, bool] = {
            k: v["unlocked"] for k, v in MilestoneThresholdConfig.MILESTONES.items()
        }

    def generate_local_attestation(self, local_observed_peers: int) -> P2PMilestoneAttestation:
        att = P2PMilestoneAttestation(
            node_pubkey=self.public_key_hex,
            active_peer_count=local_observed_peers,
            timestamp=int(time.time())
        )
        att.sign(self.private_key)
        self.attestations[self.public_key_hex] = att
        return att

    def receive_peer_attestation(self, attestation: P2PMilestoneAttestation) -> bool:
        if not attestation.verify():
            print(f"[⚠️ REJECTED] Invalid signature from node {attestation.node_pubkey[:8]}...")
            return False

        self.attestations[attestation.node_pubkey] = attestation
        self._evaluate_milestone_consensus()
        return True

    def _evaluate_milestone_consensus(self):
        if not self.attestations:
            return

        # Calculate consensus active peer count (median or trimmed mean across peer attestations)
        counts = sorted([att.active_peer_count for att in self.attestations.values()])
        median_count = counts[len(counts) // 2]

        print(f"[-] [CONSENSUS EVAL] Swarm Nodes: {len(self.attestations)} | Median Active Peers: {median_count}")

        for module_key, config in MilestoneThresholdConfig.MILESTONES.items():
            if median_count >= config["required_peers"] and not self.unlocked_modules[module_key]:
                self.unlocked_modules[module_key] = True
                print(f"🎉 [MILESTONE UNLOCKED] {module_key}: {config['description']} (Threshold: {config['required_peers']} peers reached!)")

    def get_superapp_feature_flags(self) -> Dict[str, Any]:
        return {
            "node_id": self.local_node_id,
            "attested_peer_consensus": sorted([att.active_peer_count for att in self.attestations.values()])[len(self.attestations) // 2] if self.attestations else 0,
            "feature_flags": self.unlocked_modules
        }


def test_milestone_consensus():
    print("\n=========================================================================")
    print("  TESTING P2P MILESTONE CONSENSUS ENGINE & SUPERAPP UNLOCKS")
    print("=========================================================================\n")

    engine = P2PMilestoneConsensusEngine("local_superapp_node_01")

    # Generate 5 node attestations simulating growing swarm size
    nodes = [ed25519.Ed25519PrivateKey.generate() for _ in range(5)]
    
    # Test Stage 1: Below thresholds (1,200 peers)
    print("[-] Stage 1: Initial Swarm Launch (1,200 active peers)...")
    for priv in nodes:
        pub_hex = priv.public_key().public_bytes_raw().hex()
        att = P2PMilestoneAttestation(node_pubkey=pub_hex, active_peer_count=1200, timestamp=int(time.time()))
        att.sign(priv)
        engine.receive_peer_attestation(att)

    flags1 = engine.get_superapp_feature_flags()
    print(f"    ↳ SuperApp Flags Stage 1: {flags1['feature_flags']}\n")

    # Test Stage 2: Milestone 1 Reached (6,000 peers)
    print("[-] Stage 2: Swarm Expansion (6,000 active peers)...")
    for priv in nodes:
        pub_hex = priv.public_key().public_bytes_raw().hex()
        att = P2PMilestoneAttestation(node_pubkey=pub_hex, active_peer_count=6000, timestamp=int(time.time()))
        att.sign(priv)
        engine.receive_peer_attestation(att)

    flags2 = engine.get_superapp_feature_flags()
    print(f"    ↳ SuperApp Flags Stage 2: {flags2['feature_flags']}\n")

    # Test Stage 3: Milestone 2 Reached (28,000 peers - Unlocks Neighborhood Eatery)
    print("[-] Stage 3: Neighborhood Scale Reached (28,000 active peers)...")
    for priv in nodes:
        pub_hex = priv.public_key().public_bytes_raw().hex()
        att = P2PMilestoneAttestation(node_pubkey=pub_hex, active_peer_count=28000, timestamp=int(time.time()))
        att.sign(priv)
        engine.receive_peer_attestation(att)

    flags3 = engine.get_superapp_feature_flags()
    print(f"    ↳ SuperApp Flags Stage 3: {flags3['feature_flags']}\n")


if __name__ == "__main__":
    test_milestone_consensus()
