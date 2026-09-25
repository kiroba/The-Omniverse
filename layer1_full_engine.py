import sqlite3
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

GENESIS_PREV_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

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
        """Computes SHA-256 hash over canonical representation of event fields."""
        canonical_payload = json.dumps(self.payload, sort_keys=True, separators=(',', ':'))
        hash_input = f"{self.prev_hash}:{self.timestamp}:{self.author_pubkey}:{self.event_type}:{canonical_payload}"
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()


class Layer1Engine:
    """
    Complete Layer 1 Local Engine:
    - Base: Append-only Merkle event log with Ed25519 signatures
    - Subsystem 2: CQRS Materialized Read Store (profiles_view, feed_items_view, world_state_view)
    - Subsystem 3: Transactional Outbox & Network Sync Cursor Engine (outbox queue & peer cursor tracking)
    """
    def __init__(self, db_path: str = "layer1_engine.db", private_key: Optional[ed25519.Ed25519PrivateKey] = None):
        self.db_path = db_path
        self.private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self.pubkey_hex = self.private_key.public_key().public_bytes_raw().hex()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            # --- Base Merkle Log ---
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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_event_hash ON event_log(current_hash);")

            # --- Subsystem 2: Materialized Read Views (CQRS) ---
            conn.execute("""
                CREATE TABLE IF NOT EXISTS profiles_view (
                    pubkey TEXT PRIMARY KEY,
                    username TEXT,
                    bio TEXT,
                    avatar_url TEXT,
                    last_updated_at INTEGER NOT NULL,
                    last_event_id TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feed_items_view (
                    post_id TEXT PRIMARY KEY,
                    author_pubkey TEXT NOT NULL,
                    content TEXT NOT NULL,
                    media_url TEXT,
                    created_at INTEGER NOT NULL,
                    event_id TEXT NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feed_created ON feed_items_view(created_at DESC);")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS world_state_view (
                    world_id TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    last_updated_at INTEGER NOT NULL,
                    last_event_id TEXT NOT NULL,
                    PRIMARY KEY (world_id, entity_id)
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS projection_cursor (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_projected_seq INTEGER NOT NULL DEFAULT 0
                );
            """)
            conn.execute("INSERT OR IGNORE INTO projection_cursor (id, last_projected_seq) VALUES (1, 0);")

            # --- Subsystem 3: Transactional Outbox & Sync Cursors ---
            conn.execute("""
                CREATE TABLE IF NOT EXISTS outbox (
                    outbox_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sequence_id INTEGER UNIQUE NOT NULL,
                    event_id TEXT UNIQUE NOT NULL,
                    status TEXT CHECK(status IN ('PENDING', 'IN_FLIGHT', 'ACKNOWLEDGED', 'FAILED')) DEFAULT 'PENDING',
                    retry_count INTEGER DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    FOREIGN KEY (sequence_id) REFERENCES event_log(sequence_id)
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status, sequence_id);")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS peer_cursors (
                    peer_id TEXT PRIMARY KEY,
                    last_acked_seq INTEGER NOT NULL DEFAULT 0,
                    last_seen_at INTEGER NOT NULL
                );
            """)

    # -------------------------------------------------------------------------
    # Base Layer 1: Merkle Event Logging & Outbox Staging
    # -------------------------------------------------------------------------
    def get_latest_hash(self) -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT current_hash FROM event_log ORDER BY sequence_id DESC LIMIT 1;")
            row = cursor.fetchone()
            return row['current_hash'] if row else GENESIS_PREV_HASH

    def append_event(self, event_type: str, payload: Dict[str, Any]) -> EventEnvelope:
        """
        Appends an event to the Merkle log and transactionally stages it
        into Subsystem 3's Outbox for downstream P2P broadcast.
        """
        now = int(time.time() * 1000)
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

            # Atomic insert into event_log + outbox staging
            cursor.execute("""
                INSERT INTO event_log (event_id, timestamp, author_pubkey, event_type, payload, prev_hash, current_hash, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (envelope.event_id, envelope.timestamp, envelope.author_pubkey, envelope.event_type,
                  json.dumps(envelope.payload, sort_keys=True), envelope.prev_hash, envelope.current_hash, envelope.signature))

            seq_id = cursor.lastrowid

            # Subsystem 3: Transactional Outbox Staging
            cursor.execute("""
                INSERT INTO outbox (sequence_id, event_id, status, created_at, updated_at)
                VALUES (?, ?, 'PENDING', ?, ?);
            """, (seq_id, envelope.event_id, now, now))

            conn.commit()

        # Run projection sync right after append
        self.project_events()
        return envelope

    # -------------------------------------------------------------------------
    # Subsystem 2: Materialized Read Store (CQRS Projection Engine)
    # -------------------------------------------------------------------------
    def project_events(self) -> int:
        """
        Reads unprojected events from event_log and materializes them into
        read views for The KickBack UI, Continuity profiles, and OmniMind state.
        Returns the count of events projected in this run.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT last_projected_seq FROM projection_cursor WHERE id = 1;")
            last_seq = cursor.fetchone()['last_projected_seq']

            cursor.execute("""
                SELECT sequence_id, event_id, timestamp, author_pubkey, event_type, payload
                FROM event_log
                WHERE sequence_id > ?
                ORDER BY sequence_id ASC;
            """, (last_seq,))
            events = cursor.fetchall()

            if not events:
                return 0

            new_last_seq = last_seq
            for row in events:
                seq = row['sequence_id']
                event_type = row['event_type']
                pubkey = row['author_pubkey']
                event_id = row['event_id']
                ts = row['timestamp']
                payload = json.loads(row['payload'])

                if event_type == "USER_PROFILE_UPDATE":
                    cursor.execute("""
                        INSERT INTO profiles_view (pubkey, username, bio, avatar_url, last_updated_at, last_event_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(pubkey) DO UPDATE SET
                            username = excluded.username,
                            bio = excluded.bio,
                            avatar_url = excluded.avatar_url,
                            last_updated_at = excluded.last_updated_at,
                            last_event_id = excluded.last_event_id;
                    """, (pubkey, payload.get("username", ""), payload.get("bio", ""),
                          payload.get("avatar_url", ""), ts, event_id))

                elif event_type == "NEWSFEED_POST":
                    post_id = payload.get("post_id", event_id)
                    cursor.execute("""
                        INSERT INTO feed_items_view (post_id, author_pubkey, content, media_url, created_at, event_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(post_id) DO UPDATE SET
                            content = excluded.content,
                            media_url = excluded.media_url;
                    """, (post_id, pubkey, payload.get("content", ""), payload.get("media_url", ""), ts, event_id))

                elif event_type == "AGENT_WORLD_ACTION":
                    world_id = payload.get("world_id", "default_world")
                    entity_id = payload.get("entity_id", str(uuid.uuid4()))
                    entity_type = payload.get("entity_type", "action")
                    cursor.execute("""
                        INSERT INTO world_state_view (world_id, entity_id, entity_type, state_json, last_updated_at, last_event_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(world_id, entity_id) DO UPDATE SET
                            entity_type = excluded.entity_type,
                            state_json = excluded.state_json,
                            last_updated_at = excluded.last_updated_at,
                            last_event_id = excluded.last_event_id;
                    """, (world_id, entity_id, entity_type, json.dumps(payload), ts, event_id))

                new_last_seq = seq

            cursor.execute("UPDATE projection_cursor SET last_projected_seq = ? WHERE id = 1;", (new_last_seq,))
            conn.commit()
            return len(events)

    # --- CQRS Read API for UI Consumption ---
    def get_profile(self, pubkey: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profiles_view WHERE pubkey = ?;", (pubkey,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_kickback_feed(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Used directly by The KickBack UI for fast visual feed rendering."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.*, p.username, p.avatar_url
                FROM feed_items_view f
                LEFT JOIN profiles_view p ON f.author_pubkey = p.pubkey
                ORDER BY f.created_at DESC
                LIMIT ?;
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_world_state(self, world_id: str) -> List[Dict[str, Any]]:
        """Used by OmniMind agent to view current materialized world entities."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM world_state_view WHERE world_id = ?;", (world_id,))
            return [dict(r) for r in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Subsystem 3: Transactional Outbox & Network Sync Cursor Engine
    # -------------------------------------------------------------------------
    def get_pending_outbox_for_peer(self, peer_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves unbroadcasted Merkle events from outbox for a specific peer
        based on that peer's last acknowledged sequence cursor.
        Used by The-Omni-Hub for P2P GossipSub transmission.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Fetch peer's last acked sequence
            cursor.execute("SELECT last_acked_seq FROM peer_cursors WHERE peer_id = ?;", (peer_id,))
            row = cursor.fetchone()
            last_acked = row['last_acked_seq'] if row else 0

            cursor.execute("""
                SELECT e.sequence_id, e.event_id, e.timestamp, e.author_pubkey,
                       e.event_type, e.payload, e.prev_hash, e.current_hash, e.signature,
                       o.status AS outbox_status
                FROM event_log e
                JOIN outbox o ON e.sequence_id = o.sequence_id
                WHERE e.sequence_id > ?
                ORDER BY e.sequence_id ASC
                LIMIT ?;
            """, (last_acked, limit))

            outbound_events = []
            for r in cursor.fetchall():
                d = dict(r)
                d['payload'] = json.loads(d['payload'])
                outbound_events.append(d)

            return outbound_events

    def mark_outbox_in_flight(self, sequence_ids: List[int]):
        """Marks pending events as IN_FLIGHT during network broadcast."""
        now = int(time.time() * 1000)
        with self._get_connection() as conn:
            conn.executemany("""
                UPDATE outbox SET status = 'IN_FLIGHT', updated_at = ? WHERE sequence_id = ?;
            """, [(now, seq) for seq in sequence_ids])
            conn.commit()

    def acknowledge_peer_sync(self, peer_id: str, last_acked_seq: int):
        """
        Updates a peer's sync cursor and updates outbox status to ACKNOWLEDGED
        if all known active peers have acknowledged up to or beyond that sequence.
        """
        now = int(time.time() * 1000)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Upsert peer cursor
            cursor.execute("""
                INSERT INTO peer_cursors (peer_id, last_acked_seq, last_seen_at)
                VALUES (?, ?, ?)
                ON CONFLICT(peer_id) DO UPDATE SET
                    last_acked_seq = MAX(last_acked_seq, excluded.last_acked_seq),
                    last_seen_at = excluded.last_seen_at;
            """, (peer_id, last_acked_seq, now))

            # Find minimum last_acked_seq across all known peers
            cursor.execute("SELECT MIN(last_acked_seq) AS min_seq FROM peer_cursors;")
            min_seq_row = cursor.fetchone()
            min_seq = min_seq_row['min_seq'] if (min_seq_row and min_seq_row['min_seq'] is not None) else last_acked_seq

            # Mark events up to min_seq as fully ACKNOWLEDGED in outbox
            cursor.execute("""
                UPDATE outbox
                SET status = 'ACKNOWLEDGED', updated_at = ?
                WHERE sequence_id <= ? AND status != 'ACKNOWLEDGED';
            """, (now, min_seq))

            conn.commit()

    def get_outbox_stats(self) -> Dict[str, int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, COUNT(*) as cnt FROM outbox GROUP BY status;
            """)
            stats = {row['status']: row['cnt'] for row in cursor.fetchall()}
            for status in ['PENDING', 'IN_FLIGHT', 'ACKNOWLEDGED', 'FAILED']:
                stats.setdefault(status, 0)
            return stats

    def verify_chain(self) -> Tuple[bool, str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM event_log ORDER BY sequence_id ASC;")
            rows = cursor.fetchall()
            expected_prev = GENESIS_PREV_HASH

            for idx, row in enumerate(rows):
                seq = row['sequence_id']
                envelope = EventEnvelope(row['event_id'], row['timestamp'], row['author_pubkey'], row['event_type'],
                                         json.loads(row['payload']), row['prev_hash'], row['current_hash'], row['signature'])

                if envelope.prev_hash != expected_prev:
                    return False, f"Broken chain link at sequence {seq}"
                if envelope.compute_hash() != envelope.current_hash:
                    return False, f"Hash mismatch at sequence {seq}"

                try:
                    pubkey = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(envelope.author_pubkey))
                    pubkey.verify(bytes.fromhex(envelope.signature), envelope.current_hash.encode('utf-8'))
                except InvalidSignature:
                    return False, f"Invalid signature at sequence {seq}"

                expected_prev = envelope.current_hash

            return True, f"Verified {len(rows)} events successfully."
