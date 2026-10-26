#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE REALTIME TELEMETRY MONITOR APPLET [v2.0.0]
Live Terminal Telemetry Monitor for Mobile & Desktop CLI
==============================================================================
"""

import sys
import time
import json
import urllib.request
import urllib.error

HOST_IP = "127.0.0.1"
TELEMETRY_URL = f"http://{HOST_IP}:9100/api/v1/telemetry/node-health"
OMNIMIND_URL = f"http://{HOST_IP}:9100/api/omnimind/telemetry"
STATS_URL = f"http://{HOST_IP}:5000/api/events/stats"

def fetch_json(url: str, timeout=1.5):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'OmniTelemetryMonitor/2.0'})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception:
        return None

def render_dashboard():
    print("\n" * 3)
    node_data = fetch_json(TELEMETRY_URL)
    omnimind_data = fetch_json(OMNIMIND_URL)
    stats_data = fetch_json(STATS_URL)

    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    print("==================================================================")
    print(" OMNIVERSE REALTIME TELEMETRY MONITOR [v2.0.0]")
    print(f" Timestamp: {now_str}")
    print("==================================================================")

    if node_data:
        print(" [*] NODE STATUS:       ONLINE")
        print(f" [✓] Node ID:           {node_data.get('node_id', 'N/A')}")
        print(f" [✓] Daemon Version:    {node_data.get('version', 'N/A')}")
        print(f" [✓] Active Peers:      {node_data.get('active_peers', 0)} connected")
        print(f" [✓] Throughput Rx/Tx:  {node_data.get('rx_bytes_sec', 0.0)} B/s | {node_data.get('tx_bytes_sec', 0.0)} B/s")
        print(f" [✓] Daemon Uptime:     {node_data.get('uptime_seconds', 0)}s")
    else:
        print(" [*] NODE STATUS:       OFFLINE (Waiting for daemon)")

    print("------------------------------------------------------------------")
    print(" OMNIMIND AUTONOMOUS AGENT REALTIME TELEMETRY")
    print("------------------------------------------------------------------")

    if omnimind_data:
        print(f" [★] Agent ID:          {omnimind_data.get('agent_id', 'N/A')}")
        print(f" [★] Agent Status:      {omnimind_data.get('status', 'ACTIVE')}")
        print(f" [★] Live Current Action: {omnimind_data.get('current_action', 'IDLE')}")
        print(f" [★] Events Processed:  {omnimind_data.get('events_processed', 0)}")
        print(f" [★] Operating Mode:    {omnimind_data.get('mode', 'MOBILE_EDGE_DAEMON')}")
    else:
        print(" [!] OMNIMIND STATUS:   IDLE / WAITING FOR AGENT LOOP")

    print("------------------------------------------------------------------")
    print(" CONTINUITY MERKLE DAG DATABASE METRICS")
    print("------------------------------------------------------------------")

    if stats_data:
        print(f" [✓] Total Database Events: {stats_data.get('total_events', 0)}")
        print(f" [✓] Storage Mode:          {stats_data.get('db_mode', 'WAL')} (SQLite Write-Ahead Logging)")
        print(f" [✓] Latest Merkle Hash:    {stats_data.get('last_merkle_hash', 'GENESIS')[:24]}...")
    else:
        print(" [!] DB STATUS:            UNAVAILABLE")

    print("==================================================================")
    print(" Press Ctrl+C to exit monitor loop. Refreshing every 2s...")

def main():
    try:
        while True:
            render_dashboard()
            time.sleep(2.0)
    except KeyboardInterrupt:
        print("\n[✓] Telemetry monitor closed.")
        sys.exit(0)

if __name__ == "__main__":
    main()
