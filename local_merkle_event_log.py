"""
Local Merkle Event Log Engine for Layer 1
"""
import sqlite3
import json
import hashlib
import time

class EventLogEntry:
    def __init__(self, event_type, payload, prev_hash="0"*64):
        self.event_type = event_type
        self.payload = payload
        self.timestamp = time.time()
        self.prev_hash = prev_hash
        data_str = f"{event_type}:{json.dumps(payload, sort_keys=True)}:{self.timestamp}:{prev_hash}"
        self.current_hash = hashlib.sha256(data_str.encode()).hexdigest()

class LocalMerkleEventLog:
    def __init__(self, db_path=":memory:"):
        self.db_path = db_path
        self.events = []
        self._init_db()

    def _init_db(self):
        if self.db_path != ":memory:":
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    payload TEXT,
                    current_hash TEXT,
                    timestamp REAL
                )
            """)
            conn.commit()
            conn.close()

    def append_event(self, event_type, payload):
        prev_hash = self.events[-1].current_hash if self.events else "0"*64
        entry = EventLogEntry(event_type, payload, prev_hash)
        self.events.append(entry)

        if self.db_path != ":memory:":
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO event_log (event_type, payload, current_hash, timestamp)
                VALUES (?, ?, ?, ?)
            """, (event_type, json.dumps(payload), entry.current_hash, entry.timestamp))
            conn.commit()
            conn.close()

        return entry

    def get_events(self):
        return self.events
