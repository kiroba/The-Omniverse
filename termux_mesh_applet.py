#!/usr/bin/env python3
# ==============================================================================
# OMNIVERSE TERMUX REAL MESH MONITOR [v2.0.0]
# Policy: 100% Real Telemetry (Zero Mock Data)
# ==============================================================================
import os, sys, time, json, sqlite3, urllib.request
from pathlib import Path

VERSION = '2.0.0'
TELEMETRY_PORT = 9100
CONTINUITY_PORT = 5000
HOST = '127.0.0.1'

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'OmniTermux/2.0'})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None
    return None

def fetch_db_stats():
    paths = [Path.cwd() / 'omnicast_events.db', Path.cwd() / 'continuity_events.db']
    for p in paths:
        if p.exists():
            try:
                conn = sqlite3.connect(str(p))
                c = conn.cursor()
                c.execute('PRAGMA journal_mode;')
                jmode = c.fetchone()[0].upper()
                c.execute('SELECT ' + 'COUNT(*), previous_hash FROM events ORDER BY id DESC LIMIT 1;')
                row = c.fetchone()
                conn.close()
                if row:
                    return {'mode': jmode, 'count': row[0], 'last_hash': row[1] if row[1] else 'GENESIS', 'found': True}
            except Exception:
                pass
    return {'mode': 'N/A', 'count': 0, 'last_hash': 'NO_LOCAL_DB', 'found': False}

def main():
    try:
        while True:
            hub_url = 'http://' + HOST + f':{TELEMETRY_PORT}/api/v1/telemetry/node-health'
            cont_url = 'http://' + HOST + f':{CONTINUITY_PORT}/api/events/stats'
            hub = fetch_json(hub_url)
            cont = fetch_json(cont_url)
            db = fetch_db_stats()
            sys.stdout.write('\033[H\033[J')
            print('==================================================')
            print(f' OMNIVERSE REAL TELEMETRY MONITOR [v{VERSION}]')
            print(f' Timestamp: {time.strftime("%Y-%m-%d %H:%M:%S")}')
            print(' Policy: 100% Real Live Telemetry (No Mock Data)')
            print('==================================================')
            if hub or cont:
                print(' Status:             \033[92m● ONLINE (Daemon Active)\033[0m')
                nid = hub.get('node_id', '0xUNKNOWN') if hub else 'UNKNOWN'
                peers = hub.get('active_peers', 0) if hub else 0
                ch = hub.get('channels', []) if hub else []
                rx = hub.get('rx_bytes_sec', 0.0) if hub else 0.0
                tx = hub.get('tx_bytes_sec', 0.0) if hub else 0.0
                print(f' Node Public Key:    {nid[:18]}...')
                print(f' Active P2P Peers:   {peers} peer(s)')
                print(f' GossipSub Mesh:     {ch}')
                print(f' Throughput (Rx/Tx): Rx: {rx:.1f} B/s | Tx: {tx:.1f} B/s')
            else:
                print(' Status:             \033[91m○ OFFLINE (Daemon Not Running)\033[0m')
                print(' Local Daemons:      http://' + HOST + f':{TELEMETRY_PORT} (Unreachable)')
                print(' Active P2P Peers:   0 (Daemon Disconnected)')
                print(' GossipSub Mesh:     []')
                print(' Throughput (Rx/Tx): Rx: 0 B/s | Tx: 0 B/s')
            print('--------------------------------------------------')
            print(f' SQLite WAL State:   {db["mode"]} (Found: {db["found"]})')
            print(f' Local Event Count:  {db["count"]} events')
            print(f' Last Merkle Hash:   {db["last_hash"][:24]}...')
            print('==================================================')
            print(' [Press Ctrl+C to stop. Live refresh every 2s...]')
            time.sleep(2.0)
    except KeyboardInterrupt:
        print('\n[✓] Telemetry monitor stopped.')
        sys.exit(0)

if __name__ == '__main__':
    main()