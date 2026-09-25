"""
Layer 2 P2P CRDT Engine v2
"""
import hashlib
import json

class DeltaStateCRDT:
    def __init__(self):
        self.state = {}

    def merge(self, delta):
        self.state.update(delta)

class EventEnvelope:
    def __init__(self, event_id, timestamp, author_pubkey, author_type, event_type, payload, prev_hash, current_hash="", signature=""):
        self.event_id = event_id
        self.timestamp = timestamp
        self.author_pubkey = author_pubkey
        self.author_type = author_type
        self.event_type = event_type
        self.payload = payload
        self.prev_hash = prev_hash
        self.current_hash = current_hash
        self.signature = signature

    def compute_hash(self):
        data_str = f"{self.event_id}:{self.timestamp}:{self.author_pubkey}:{self.author_type}:{self.event_type}:{json.dumps(self.payload, sort_keys=True)}:{self.prev_hash}"
        return hashlib.sha256(data_str.encode()).hexdigest()

class OmniHubP2PPeer:
    def __init__(self, peer_id):
        self.peer_id = peer_id
        self.received_messages = []

    def receive_message(self, topic, envelope):
        self.received_messages.append((topic, envelope))

class P2PGossipNetwork:
    def __init__(self):
        self.peers = {}

    def register_peer(self, peer):
        self.peers[peer.peer_id] = peer

    def broadcast_gossip(self, sender_id, topic, envelope):
        delivered = 0
        for peer_id, peer in self.peers.items():
            if peer_id != sender_id:
                peer.receive_message(topic, envelope)
                delivered += 1
        return {"delivered": delivered, "topic": topic}
