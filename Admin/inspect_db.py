import sqlite3
import os
from pathlib import Path

def inspect_events():
    db_path = Path("continuity_events.db")
    if not db_path.exists():
        db_path = Path("Admin") / "continuity_events.db"
    
    if not db_path.exists():
        print("Database 'continuity_events.db' not found in current directory.")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    query = "SELECT id, event_id, action, author_pubkey, previous_hash, datetime(timestamp, 'unixepoch') FROM events;"
    
    try:
        rows = cursor.execute(query).fetchall()
        if not rows:
            print("Database connected successfully, but 'events' table is currently empty.")
            return

        print(f"\n{'ID':<5} | {'EVENT ID':<20} | {'ACTION':<25} | {'TIMESTAMP':<20}")
        print("-" * 80)
        for row in rows:
            row_id = str(row[0])
            event_id = str(row[1])[:18] + "..." if len(str(row[1])) > 18 else str(row[1])
            action = str(row[2])
            timestamp = str(row[5]) if row[5] else "N/A"
            print(f"{row_id:<5} | {event_id:<20} | {action:<25} | {timestamp:<20}")
        print("-" * 80)
        print(f"Total Events Recorded: {len(rows)}\n")
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_events()
