import sqlite3
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def compute_hash(self) -> str:
        """
        Computes SHA-256 hash over canonical representation of:
        prev_hash + timestamp + author_pubkey + event_type + canonical_payload_json
        """
        canonical_payload = json.dumps(self.payload, sort_keys=True, separators=(',', ':'))
        hash_input = f"{self.prev_hash}:{self.timestamp}:{self.author_pubkey}:{self.event_type}:{canonical_payload}"
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()


class LocalMerkleEventLog:
    """
    Append-Only Local Merkle Event Log using SQLite with Write-Ahead Logging (WAL)
    and Ed25519 cryptographic signing.
    """
    def __init__(self, db_path: str = ":memory:", private_key: Optional[ed25519.Ed25519PrivateKey] = None):
        self.db_path = db_path
        if private_key is None:
            self.private_key = ed25519.Ed25519PrivateKey.generate()
        else:
            self.private_key = private_key
        
        self.public_key = self.private_key.public_key()
        self.pubkey_bytes = self.public_key.public_bytes_raw()
        self.pubkey_hex = self.pubkey_bytes.hex()

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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_event_hash ON event_log(current_hash);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sequence ON event_log(sequence_id);")

    def get_latest_hash(self) -> str:
        """Retrieves current tip hash of local Merkle chain."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT current_hash FROM event_log ORDER BY sequence_id DESC LIMIT 1;")
            row = cursor.fetchone()
            if row:
                return row['current_hash']
            return GENESIS_PREV_HASH

    def append_event(self, event_type: str, payload: Dict[str, Any]) -> EventEnvelope:
        """
        Appends a new event payload to local Merkle event log.
        Calculates cryptographic SHA-256 hash chain and signs entry using Ed25519 key.
        """
        prev_hash = self.get_latest_hash()
        timestamp = int(time.time() * 1000)
        event_id = str(uuid.uuid4())

        # Build envelope shell to compute canonical hash
        envelope_shell = EventEnvelope(
            event_id=event_id,
            timestamp=timestamp,
            author_pubkey=self.pubkey_hex,
            event_type=event_type,
            payload=payload,
            prev_hash=prev_hash,
            current_hash="",
            signature=""
        )

        current_hash = envelope_shell.compute_hash()
        
        # Sign current_hash with Ed25519 private key
        sig_bytes = self.private_key.sign(current_hash.encode('utf-8'))
        signature_hex = sig_bytes.hex()

        envelope = EventEnvelope(
            event_id=event_id,
            timestamp=timestamp,
            author_pubkey=self.pubkey_hex,
            event_type=event_type,
            payload=payload,
            prev_hash=prev_hash,
            current_hash=current_hash,
            signature=signature_hex
        )

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO event_log 
                (event_id, timestamp, author_pubkey, event_type, payload, prev_hash, current_hash, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                envelope.event_id,
                envelope.timestamp,
                envelope.author_pubkey,
                envelope.event_type,
                json.dumps(envelope.payload, sort_keys=True),
                envelope.prev_hash,
                envelope.current_hash,
                envelope.signature
            ))

        return envelope

    def verify_chain(self) -> tuple[bool, str]:
        """
        Validates entire local event log for cryptographic integrity:
        1. Checks prev_hash linkage across sequential rows.
        2. Recalculates expected SHA-256 current_hash for each envelope.
        3. Verifies Ed25519 signatures using stored author public keys.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM event_log ORDER BY sequence_id ASC;")
            rows = cursor.fetchall()

            if not rows:
                return True, "Chain is empty."

            expected_prev_hash = GENESIS_PREV_HASH

            for idx, row in enumerate(rows):
                seq = row['sequence_id']
                payload_dict = json.loads(row['payload'])

                envelope = EventEnvelope(
                    event_id=row['event_id'],
                    timestamp=row['timestamp'],
                    author_pubkey=row['author_pubkey'],
                    event_type=row['event_type'],
                    payload=payload_dict,
                    prev_hash=row['prev_hash'],
                    current_hash=row['current_hash'],
                    signature=row['signature']
                )

                # 1. Verify previous hash link
                if envelope.prev_hash != expected_prev_hash:
                    return False, f"Broken chain link at sequence {seq}: prev_hash '{envelope.prev_hash}' != expected '{expected_prev_hash}'"

                # 2. Recalculate and check current hash
                computed_hash = envelope.compute_hash()
                if computed_hash != envelope.current_hash:
                    return False, f"Hash mismatch at sequence {seq}: stored '{envelope.current_hash}' != computed '{computed_hash}'"

                # 3. Verify Ed25519 signature
                try:
                    pubkey_bytes = bytes.fromhex(envelope.author_pubkey)
                    pubkey = ed25519.Ed25519PublicKey.from_public_bytes(pubkey_bytes)
                    pubkey.verify(bytes.fromhex(envelope.signature), envelope.current_hash.encode('utf-8'))
                except (InvalidSignature, ValueError) as e:
                    return False, f"Invalid signature at sequence {seq}: {e}"

                expected_prev_hash = envelope.current_hash

            return True, f"Successfully verified {len(rows)} event(s) in Merkle chain."

    def get_events(self, limit: int = 50) -> List[EventEnvelope]:
        """Fetches latest events for feed streaming."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM event_log ORDER BY sequence_id ASC LIMIT ?;", (limit,))
            rows = cursor.fetchall()

            events = []
            for row in rows:
                events.append(EventEnvelope(
                    event_id=row['event_id'],
                    timestamp=row['timestamp'],
                    author_pubkey=row['author_pubkey'],
                    event_type=row['event_type'],
                    payload=json.loads(row['payload']),
                    prev_hash=row['prev_hash'],
                    current_hash=row['current_hash'],
                    signature=row['signature']
                ))
            return events


# Demonstration / Integration Test
if __name__ == "__main__":
    print("--- Initializing Local Merkle Event Log ---")
    log_engine = LocalMerkleEventLog("scratch_merkle_test.db")

    # 1. Simulate Continuity-Engine creating user profile update
    print("\n1. Continuity-Engine logging 'USER_PROFILE_UPDATE'...")
    e1 = log_engine.append_event(
        event_type="USER_PROFILE_UPDATE",
        payload={
            "username": "kiroba",
            "bio": "Building the Omniverse ecosystem",
            "preferences": {"theme": "dark", "p2p_sync": True}
        }
    )
    print(f"   Event ID: {e1.event_id}")
    print(f"   Prev Hash: {e1.prev_hash[:16]}...")
    print(f"   Curr Hash: {e1.current_hash[:16]}...")

    # 2. Simulate OmniMind Autonomous Agent action
    print("\n2. OmniMind Agent logging 'AGENT_WORLD_ACTION'...")
    e2 = log_engine.append_event(
        event_type="AGENT_WORLD_ACTION",
        payload={
            "agent_id": "omnimind-v1-core",
            "action": "CONSTRUCT_TERRAIN",
            "coordinates": {"x": 102, "y": 405, "z": 12},
            "parameters": {"biome": "cyber_forest", "density": 0.85}
        }
    )
    print(f"   Event ID: {e2.event_id}")
    print(f"   Prev Hash: {e2.prev_hash[:16]}...")
    print(f"   Curr Hash: {e2.current_hash[:16]}...")

    # 3. Simulate Continuity-Engine / The KickBack post creation
    print("\n3. Continuity-Engine logging 'NEWSFEED_POST' for The KickBack...")
    e3 = log_engine.append_event(
        event_type="NEWSFEED_POST",
        payload={
            "author": "kiroba",
            "content": "Welcome to The KickBack! Broadcasted via The-Omni-Hub.",
            "tags": ["#omniverse", "#decentralized", "#p2p"]
        }
    )
    print(f"   Event ID: {e3.event_id}")
    print(f"   Prev Hash: {e3.prev_hash[:16]}...")
    print(f"   Curr Hash: {e3.current_hash[:16]}...")

    # 4. Verify Chain Integrity
    print("\n--- Verifying Chain Integrity ---")
    valid, msg = log_engine.verify_chain()
    print(f"Result: {valid} -> {msg}")

    # 5. Simulate Tampering Test
    print("\n--- Simulating Local Storage Tampering ---")
    conn = sqlite3.connect("scratch_merkle_test.db")
    conn.execute("UPDATE event_log SET payload = '{\"hacked\": true}' WHERE sequence_id = 2;")
    conn.commit()
    conn.close()

    valid_tampered, msg_tampered = log_engine.verify_chain()
    print(f"Tamper Verification Result: {valid_tampered} -> {msg_tampered}")

    # Clean up test DB file
    import os
    if os.path.exists("scratch_merkle_test.db"):
        os.remove("scratch_merkle_test.db")
