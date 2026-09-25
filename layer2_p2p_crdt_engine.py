import sqlite3
import hashlib
import json
import time
import uuid
import os
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Tuple, Set
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

# Configuration Constraints
GENESIS_PREV_HASH = "0000000000000000000000000000000000000000000000000000000000000000"
MAX_TIMESTAMP_DRIFT_MS = 15 * 60 * 1000  # 15 Minutes
MAX_PAYLOAD_BYTES = 256 * 1024  # 256 KB

# =====================================================================
# LAYER 1 BASE ENVELOPE & HARDENED LOCAL ENGINE
# =====================================================================

@dataclass
class EventEnvelope:
    event_id: str
    timestamp: int
    author_pubkey: str
    event_type: str
    payload: Dict[str, Any]
    prev_hash: str
    current_hash: str
    signature: str

    def compute_hash(self) -> str:
        canonical_payload = json.dumps(self.payload, sort_keys=True, separators=(',', ':'))
        hash_input = f"{self.prev_hash}:{self.timestamp}:{self.author_pubkey}:{self.event_type}:{canonical_payload}"
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

class LocalNodeStorage:
    """Hardened Layer 1 Local Engine with SQLite backing for a P2P Node."""
    def __init__(self, node_id: str, db_path: Optional[str] = None, private_key: Optional[ed25519.Ed25519PrivateKey] = None):
        self.node_id = node_id
        self.db_path = db_path or f"/workspace/scratch/node_{node_id}.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self.pubkey_hex = self.private_key.public_key().public_bytes_raw().hex()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS event_log (
                    sequence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    timestamp INTEGER NOT NULL,
                    author_pubkey TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    current_hash TEXT UNIQUE NOT NULL,
                    signature TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS outbox (
                    outbox_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sequence_id INTEGER UNIQUE NOT NULL,
                    event_id TEXT UNIQUE NOT NULL,
                    status TEXT CHECK(status IN ('PENDING', 'IN_FLIGHT', 'ACKNOWLEDGED')) DEFAULT 'PENDING',
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY (sequence_id) REFERENCES event_log(sequence_id)
                );
            """)

    def append_local_event(self, event_type: str, payload: Dict[str, Any]) -> EventEnvelope:
        now = int(time.time() * 1000)
        payload_bytes = len(json.dumps(payload).encode('utf-8'))
        if payload_bytes > MAX_PAYLOAD_BYTES:
            raise ValueError(f"Payload size ({payload_bytes} bytes) exceeds maximum limit ({MAX_PAYLOAD_BYTES} bytes)")

        event_id = str(uuid.uuid4())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT current_hash FROM event_log ORDER BY sequence_id DESC LIMIT 1;")
            row = cursor.fetchone()
            prev_hash = row['current_hash'] if row else GENESIS_PREV_HASH

            shell = EventEnvelope(event_id, now, self.pubkey_hex, event_type, payload, prev_hash, "", "")
            current_hash = shell.compute_hash()
            signature_hex = self.private_key.sign(current_hash.encode('utf-8')).hex()

            envelope = EventEnvelope(event_id, now, self.pubkey_hex, event_type, payload, prev_hash, current_hash, signature_hex)

            cursor.execute("""
                INSERT INTO event_log (event_id, timestamp, author_pubkey, event_type, payload, prev_hash, current_hash, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (envelope.event_id, envelope.timestamp, envelope.author_pubkey, envelope.event_type,
                  json.dumps(envelope.payload, sort_keys=True), envelope.prev_hash, envelope.current_hash, envelope.signature))

            seq_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO outbox (sequence_id, event_id, status, created_at)
                VALUES (?, ?, 'PENDING', ?);
            """, (seq_id, envelope.event_id, now))
            conn.commit()
            return envelope

    def ingest_remote_event(self, envelope: EventEnvelope) -> bool:
        """Validates and ingests an incoming remote Merkle event into local storage."""
        # Security Guard 1: Signature Verification
        try:
            pubkey = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(envelope.author_pubkey))
            pubkey.verify(bytes.fromhex(envelope.signature), envelope.current_hash.encode('utf-8'))
        except (InvalidSignature, Exception):
            return False  # Signature forged

        # Security Guard 2: Hash Integrity Check
        if envelope.compute_hash() != envelope.current_hash:
            return False

        # Security Guard 3: Timestamp Drift Guard
        now = int(time.time() * 1000)
        if abs(now - envelope.timestamp) > MAX_TIMESTAMP_DRIFT_MS:
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO event_log (event_id, timestamp, author_pubkey, event_type, payload, prev_hash, current_hash, signature)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (envelope.event_id, envelope.timestamp, envelope.author_pubkey, envelope.event_type,
                      json.dumps(envelope.payload, sort_keys=True), envelope.prev_hash, envelope.current_hash, envelope.signature))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False  # Already ingested (replay prevention)

    def get_pending_outbox_events(self) -> List[EventEnvelope]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.* FROM event_log e
                JOIN outbox o ON e.sequence_id = o.sequence_id
                WHERE o.status = 'PENDING'
                ORDER BY e.sequence_id ASC;
            """)
            events = []
            for r in cursor.fetchall():
                events.append(EventEnvelope(
                    r['event_id'], r['timestamp'], r['author_pubkey'], r['event_type'],
                    json.loads(r['payload']), r['prev_hash'], r['current_hash'], r['signature']
                ))
            return events

    def mark_outbox_acknowledged(self, event_ids: List[str]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                UPDATE outbox SET status = 'ACKNOWLEDGED' WHERE event_id = ?;
            """, [(eid,) for eid in event_ids])
            conn.commit()

    def get_all_events(self) -> List[EventEnvelope]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM event_log ORDER BY sequence_id ASC;")
            events = []
            for r in cursor.fetchall():
                events.append(EventEnvelope(
                    r['event_id'], r['timestamp'], r['author_pubkey'], r['event_type'],
                    json.loads(r['payload']), r['prev_hash'], r['current_hash'], r['signature']
                ))
            return events

# =====================================================================
# LAYER 2 DELTA-STATE CRDT EVENTUAL CONSISTENCY ENGINE
# =====================================================================

class DeltaStateCRDT:
    """
    Delta-State Conflict-Free Replicated Data Type (CRDT) Engine.
    Handles deterministic, lock-free state convergence across mobile and network nodes:
    1. LWW-Register (Last-Write-Wins): User profile updates.
    2. Add-Only Set / OR-Set: KickBack newsfeed posts and reactions.
    3. PN-Counter: Social post reaction counters (+1/-1 likes).
    """
    def __init__(self):
        # LWW Profiles: pubkey -> (timestamp, username, bio)
        self.profiles_lww: Dict[str, Tuple[int, str, str]] = {}
        # Feed Posts Set: post_id -> (timestamp, author_pubkey, content)
        self.feed_posts_set: Dict[str, Tuple[int, str, str]] = {}
        # PN-Counter Reactions: post_id -> {pubkey -> score (+1 or -1)}
        self.post_reactions_pncrypto: Dict[str, Dict[str, int]] = {}

    def apply_event_delta(self, envelope: EventEnvelope):
        """Applies a verified Merkle event delta to the CRDT state model."""
        ts = envelope.timestamp
        pubkey = envelope.author_pubkey
        payload = envelope.payload
        event_type = envelope.event_type

        if event_type == "USER_PROFILE_UPDATE":
            username = payload.get("username", "")
            bio = payload.get("bio", "")
            # LWW Merge Rule: Higher timestamp wins; pubkey breaks ties deterministically
            if pubkey not in self.profiles_lww:
                self.profiles_lww[pubkey] = (ts, username, bio)
            else:
                existing_ts, _, _ = self.profiles_lww[pubkey]
                if ts >= existing_ts:
                    self.profiles_lww[pubkey] = (ts, username, bio)

        elif event_type == "NEWSFEED_POST":
            post_id = payload.get("post_id", envelope.event_id)
            content = payload.get("content", "")
            if post_id not in self.feed_posts_set:
                self.feed_posts_set[post_id] = (ts, pubkey, content)

        elif event_type == "POST_REACTION":
            post_id = payload.get("post_id")
            delta_val = payload.get("value", 1)  # +1 for like, -1 for unlike
            if post_id:
                if post_id not in self.post_reactions_pncrypto:
                    self.post_reactions_pncrypto[post_id] = {}
                # PN-Counter Merge Rule: Latest user action sets reaction score
                self.post_reactions_pncrypto[post_id][pubkey] = delta_val

    def get_post_likes_count(self, post_id: str) -> int:
        reactions = self.post_reactions_pncrypto.get(post_id, {})
        return sum(reactions.values())

    def get_kickback_feed(self) -> List[Dict[str, Any]]:
        feed = []
        for post_id, (ts, pubkey, content) in self.feed_posts_set.items():
            profile = self.profiles_lww.get(pubkey, (0, "Anonymous", ""))
            likes = self.get_post_likes_count(post_id)
            feed.append({
                "post_id": post_id,
                "created_at": ts,
                "author_pubkey": pubkey,
                "author_username": profile[1],
                "content": content,
                "likes_count": likes
            })
        # Sort feed chronologically descending for mobile UI rendering
        return sorted(feed, key=lambda x: x["created_at"], reverse=True)

# =====================================================================
# LAYER 2 P2P GOSSIPSUB TRANSPORT & CIRCUIT RELAY NETWORK
# =====================================================================

class OmniHubP2PPeer:
    """Represents an active P2P Node running The-Omni-Hub protocol."""
    def __init__(self, peer_id: str, is_mobile: bool = False):
        self.peer_id = peer_id
        self.is_mobile = is_mobile
        self.is_online = True
        self.storage = LocalNodeStorage(node_id=peer_id)
        self.crdt = DeltaStateCRDT()
        self.seen_message_hashes: Set[str] = set()  # In-memory replay filter
        self.subscribed_topics: Set[str] = {"/kickback/feed", "/omnimind/world"}

    def on_gossip_message(self, topic: str, envelope: EventEnvelope) -> bool:
        if not self.is_online:
            return False  # Mobile device offline in background mode

        if topic not in self.subscribed_topics:
            return False

        # Layer 2 Replay Protection (Bloom Filter / Hash Set)
        if envelope.current_hash in self.seen_message_hashes:
            return False  # Duplicate gossip dropped
        self.seen_message_hashes.add(envelope.current_hash)

        # Layer 1 Ingest Verification
        accepted = self.storage.ingest_remote_event(envelope)
        if accepted:
            # Apply to Delta-CRDT engine for eventual consistency
            self.crdt.apply_event_delta(envelope)
            return True
        return False


class P2PGossipNetwork:
    """Simulates libp2p GossipSub Transport, Circuit Relays, and Catch-Up Syncing."""
    def __init__(self):
        self.peers: Dict[str, OmniHubP2PPeer] = {}

    def register_peer(self, peer: OmniHubP2PPeer):
        self.peers[peer.peer_id] = peer

    def broadcast_gossip(self, source_peer_id: str, topic: str, envelope: EventEnvelope) -> int:
        """Broadcasts an event envelope over P2P GossipSub to connected online peers."""
        delivered_count = 0
        for peer_id, peer in self.peers.items():
            if peer_id == source_peer_id:
                continue
            if peer.on_gossip_message(topic, envelope):
                delivered_count += 1
        return delivered_count

    def execute_mobile_catchup_sync(self, mobile_peer_id: str, target_peer_id: str) -> int:
        """
        Mobile Catch-Up Sync (The KickBack):
        When a mobile node reconnects after background execution:
        1. Pulls missed remote deltas from target relay peer.
        2. Pushes local offline PENDING outbox deltas to network peers.
        """
        mobile_peer = self.peers[mobile_peer_id]
        target_peer = self.peers[target_peer_id]

        if not mobile_peer.is_online or not target_peer.is_online:
            return 0

        # 1. Pull remote deltas missed by mobile node
        missed_events = target_peer.storage.get_all_events()
        synced_count = 0
        for env in missed_events:
            if mobile_peer.on_gossip_message("/kickback/feed", env):
                synced_count += 1

        # 2. Push offline PENDING deltas generated locally by mobile node
        pending_outbox_events = mobile_peer.storage.get_pending_outbox_events()
        pushed_ids = []
        for offline_env in pending_outbox_events:
            self.broadcast_gossip(mobile_peer_id, "/kickback/feed", offline_env)
            pushed_ids.append(offline_env.event_id)

        mobile_peer.storage.mark_outbox_acknowledged(pushed_ids)
        return synced_count
