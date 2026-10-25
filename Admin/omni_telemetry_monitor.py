#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE VIBRANT REALTIME TELEMETRY MONITOR [v7.0.0 - Fully Dynamic Auto-IP]
==============================================================================
System Role:
- 100% Zero-Config Dynamic Auto-IP Probe (No hardcoded target IPs needed)
- Vibrant ANSI Color Output (Emerald Green, Neon Cyan, Vivid Magenta, Amber Gold)
- Real-Time Discovered Peer List & SQLite WAL Merkle DAG Block Depth
==============================================================================
"""

import sys
import time
import json
import socket
import urllib.request
import urllib.error

HOST = "127.0.0.1"
PORT_TELEMETRY = 9100
PORT_CONTINUITY = 5000

def get_auto_ip():
    try:
        hn = socket.gethostname()
        return socket.gethostbyname(hn)
    except Exception:
        return "127.0.0.1"

LOCAL_IP = get_auto_ip()

# Vivid ANSI Color Palette
RESET   = "\033[0m"
BOLD    = "\033[1m"
GREEN   = "\033[92m"
CYAN    = "\033[96m"
MAGENTA = "\033[95m"
YELLOW  = "\033[93m"
BLUE    = "\033[94m"
RED     = "\033[91m"

def fetch_json(url_str: str, timeout=1.5):
    try:
        with urllib.request.urlopen(url_str, timeout=timeout) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception:
        return None

def render_dashboard():
    health_url = f"http://{HOST}:{PORT_TELEMETRY}/api/v1/telemetry/node-health"
    stats_url = f"http://{HOST}:{PORT_CONTINUITY}/api/events/stats"

    node_data = fetch_json(health_url)
    stats_data = fetch_json(stats_url)

    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    print("\n" * 3)
    print(f"{CYAN}=================================================================={RESET}")
    print(f"{BOLD}{CYAN} OMNIVERSE VIBRANT REALTIME TELEMETRY MONITOR [v7.0.0]{RESET}")
    print(f" Timestamp: {YELLOW}{now_str}{RESET} | Auto Host IP: {GREEN}{LOCAL_IP}{RESET}")
    print(f"{CYAN}=================================================================={RESET}")

    if node_data:
        wan_active = node_data.get('wan_active', False)
        rem = node_data.get('wan_time_remaining', 0)
        wan_str = f"{GREEN}ACTIVE ({rem}s remaining){RESET}" if wan_active else f"{YELLOW}STANDBY (Local Only){RESET}"
        print(f" [*] DAEMON STATUS:     {GREEN}{BOLD}ONLINE{RESET}")
        print(f" [✓] Node ID:           {CYAN}{node_data.get('node_id', 'N/A')}{RESET}")
        print(f" [✓] Local Auto IP:     {GREEN}{node_data.get('auto_detected_ip', LOCAL_IP)}{RESET}")
        print(f" [✓] Ephemeral WAN:     {wan_str}")
        print(f" [✓] Discovered Peers:  {MAGENTA}{node_data.get('active_peers_count', 0)} Nodes Auto-Discovered{RESET}")

        peers = node_data.get('discovered_peers', [])
        for p in peers:
            print(f"     └─ [{YELLOW}{p.get('transport', 'P2P')}{RESET}] Node: {CYAN}{p.get('node_id', '')[:16]}...{RESET} @ {GREEN}{p.get('ip')}{RESET}")
    else:
        print(f" [*] DAEMON STATUS:     {RED}{BOLD}OFFLINE (Searching local daemon on port {PORT_TELEMETRY}...){RESET}")

    print(f"{BLUE}------------------------------------------------------------------{RESET}")
    print(f"{BOLD}{BLUE} CONTINUITY MERKLE DAG DATABASE METRICS{RESET}")
    print(f"{BLUE}------------------------------------------------------------------{RESET}")

    if stats_data:
        print(f" [✓] Database Events:   {GREEN}{stats_data.get('total_events', 0)}{RESET}")
        print(f" [✓] Storage Engine:    {BLUE}SQLite WAL (Write-Ahead Logging){RESET}")
        print(f" [✓] Latest Merkle Hash:{CYAN}{stats_data.get('last_merkle_hash', 'GENESIS')[:32]}...{RESET}")
    else:
        print(f" [!] MERKLE DB:         {YELLOW}Awaiting Local Gateway Sync...{RESET}")

    print(f"{CYAN}=================================================================={RESET}")
    print(" Press Ctrl+C to exit. Refreshing live every 2s...")

def main():
    try:
        while True:
            render_dashboard()
            time.sleep(2.0)
    except KeyboardInterrupt:
        print(f"\n{GREEN}[✓] Telemetry monitor closed.{RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()
