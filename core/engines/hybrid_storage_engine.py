import sqlite3
import json
import hashlib
import time
from typing import Dict, Any, List, Optional

class SimulatedRocksDBEngine:
    """
    Simulated Log-Structured Merge-Tree (LSM-Tree) Engine for RocksDB.
    Handles ultra-fast, non-blocking sequential appends of raw Merkle event blocks
    (event_hash -> raw_json_bytes) without locking DB tables.
    """
    def __init__(self):
        self.memtable: Dict[str, bytes] = {}
        self.sstables: Dict[str, bytes] = {}

    def put(self, key: str, value: bytes):
        self.memtable[key] = value

    def get(self, key: str) -> Optional[bytes]:
        if key in self.memtable:
            return self.memtable[key]
        return self.sstables.get(key, None)

    def flush_memtable_to_sstable(self):
        self.sstables.update(self.memtable)
        self.memtable.clear()

class HybridStorageEngine:
    """
    Hybrid CQRS Storage Engine combining RocksDB (LSM Ingestion & Merkle Log)
    with SQLite WAL Mode (Materialized Read Store & UI Projections).
    """
    def __init__(self, sqlite_db_path: str = ":memory:"):
        self.rocksdb = SimulatedRocksDBEngine()
        self.sqlite_conn = sqlite3.connect(sqlite_db_path)
        self._init_sqlite_wal_schema()

    def _init_sqlite_wal_schema(self):
        cursor = self.sqlite_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feed_posts (
                event_hash TEXT PRIMARY KEY,
                author_pubkey TEXT NOT NULL,
                universe_id TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                reaction_count INTEGER DEFAULT 0
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feed_timestamp ON feed_posts(timestamp DESC);")
        self.sqlite_conn.commit()

    def ingest_p2p_event(self, event_payload: Dict[str, Any]) -> str:
        canonical = json.dumps(event_payload, sort_keys=True)
        event_hash = "0x" + hashlib.sha256(canonical.encode('utf-8')).hexdigest()
        raw_bytes = canonical.encode('utf-8')
        self.rocksdb.put(event_hash, raw_bytes)
        return event_hash

    def sync_projection_worker(self, unprojected_hashes: List[str]):
        cursor = self.sqlite_conn.cursor()
        for event_hash in unprojected_hashes:
            raw_bytes = self.rocksdb.get(event_hash)
            if not raw_bytes:
                continue
            payload = json.loads(raw_bytes.decode('utf-8'))
            if payload.get("eventType") == "POST_CREATED":
                cursor.execute("""
                    INSERT OR REPLACE INTO feed_posts (event_hash, author_pubkey, universe_id, content, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    event_hash,
                    payload.get("authorPubkey", "unknown"),
                    payload.get("universeId", "com.kickback"),
                    payload.get("content", ""),
                    payload.get("timestamp", int(time.time()))
                ))
        self.sqlite_conn.commit()

    def query_ui_feed(self, limit: int = 10) -> List[Dict[str, Any]]:
        cursor = self.sqlite_conn.cursor()
        cursor.execute("""
            SELECT event_hash, author_pubkey, universe_id, content, timestamp, reaction_count
            FROM feed_posts
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [
            {
                "eventHash": r[0],
                "authorPubkey": r[1],
                "universeId": r[2],
                "content": r[3],
                "timestamp": r[4],
                "reactionCount": r[5]
            }
            for r in rows
        ]

if __name__ == "__main__":
    engine = HybridStorageEngine()
    hashes = []
    for i in range(100):
        sample_post = {
            "eventType": "POST_CREATED",
            "authorPubkey": f"ed25519_pk_user_{i % 5}",
            "universeId": "com.kickback",
            "content": f"High speed P2P feed event delta #{i} in KickBack Universe.",
            "timestamp": int(time.time()) + i
        }
        h = engine.ingest_p2p_event(sample_post)
        hashes.append(h)
    engine.rocksdb.flush_memtable_to_sstable()
    engine.sync_projection_worker(hashes)
    feed = engine.query_ui_feed(limit=5)
