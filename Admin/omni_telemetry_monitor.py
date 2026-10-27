#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE REALTIME TELEMETRY MONITOR APPLET [v5.0.0 - Vibrant ANSI Color]
Live Terminal Telemetry Monitor for Mobile Termux & Desktop CLI
==============================================================================
"""

import os
import sys
import time
import json
import argparse
import urllib.request
import urllib.error

VERSION = "5.0.0"

# --- ANSI COLOR PALETTE ---
C_RESET   = "\033[0m"
C_BOLD    = "\033[1m"
C_CYAN    = "\033[38;5;51m"
C_GREEN   = "\033[38;5;48m"
C_MAGENTA = "\033[38;5;198m"
C_YELLOW  = "\033[38;5;220m"
C_BLUE    = "\033[38;5;39m"
C_RED     = "\033[38;5;196m"
C_GRAY    = "\033[38;5;244m"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def fetch_json(url: str, timeout=1.5):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': f'OmniTelemetryMonitor/{VERSION}'})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception:
        return None

def render_dashboard(host_ip: str):
    clear_screen()
    telemetry_url = f"http://{host_ip}:9100/api/v1/telemetry/node-health"
    omnimind_url  = f"http://{host_ip}:9100/api/omnimind/telemetry"
    stats_url     = f"http://{host_ip}:5000/api/events/stats"

    node_data     = fetch_json(telemetry_url)
    omnimind_data = fetch_json(omnimind_url)
    stats_data    = fetch_json(stats_url)

    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    print(f"{C_BOLD}{C_CYAN}=================================================================={C_RESET}")
    print(f"{C_BOLD}{C_CYAN} OMNIVERSE REALTIME TELEMETRY & OMNIMIND MONITOR [v{VERSION}]{C_RESET}")
    print(f"{C_GRAY} Target Host: {C_YELLOW}{host_ip:<15}{C_GRAY} | Timestamp: {C_YELLOW}{now_str}{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}=================================================================={C_RESET}")

    if node_data:
        status_badge = f"{C_BOLD}{C_GREEN}ONLINE{C_RESET}"
        print(f" [*] DAEMON STATUS:     {status_badge}")
        print(f" [{C_GREEN}✓{C_RESET}] Node ID:           {C_CYAN}{node_data.get('node_id', 'N/A')}{C_RESET}")
        print(f" [{C_GREEN}✓{C_RESET}] Daemon Version:    {node_data.get('version', 'N/A')}")
        print(f" [{C_GREEN}✓{C_RESET}] Active P2P Peers:   {C_GREEN}{node_data.get('active_peers', 0)} connected{C_RESET} {node_data.get('peer_ips', [])}")
        if 'rx_bytes_sec' in node_data:  # shown only once the daemon reports throughput
            print(f" [{C_GREEN}✓{C_RESET}] Throughput Rx/Tx:  {C_YELLOW}{node_data.get('rx_bytes_sec', 0.0)} B/s{C_RESET} | {C_YELLOW}{node_data.get('tx_bytes_sec', 0.0)} B/s{C_RESET}")
        print(f" [{C_GREEN}✓{C_RESET}] Daemon Uptime:     {C_YELLOW}{node_data.get('uptime_seconds', 0)}s{C_RESET}")
    else:
        status_badge = f"{C_BOLD}{C_RED}OFFLINE (Waiting for daemon...){C_RESET}"
        print(f" [*] DAEMON STATUS:     {status_badge}")

    print(f"{C_GRAY}------------------------------------------------------------------{C_RESET}")
    print(f"{C_BOLD}{C_MAGENTA} OMNIMIND AUTONOMOUS AGENT & ACTIVE TASK MONITOR{C_RESET}")
    print(f"{C_GRAY}------------------------------------------------------------------{C_RESET}")

    if omnimind_data:
        print(f" [{C_MAGENTA}★{C_RESET}] Agent ID:          {C_CYAN}{omnimind_data.get('agent_id', 'OmniMind_Core_Edge')}{C_RESET}")
        print(f" [{C_MAGENTA}★{C_RESET}] Agent Status:      {C_GREEN}{omnimind_data.get('status', 'ACTIVE')}{C_RESET}")
        print(f" [{C_MAGENTA}★{C_RESET}] Live Current Action: {C_MAGENTA}{omnimind_data.get('current_action') or omnimind_data.get('action', 'IDLE')}{C_RESET}")
        print(f" [{C_MAGENTA}★{C_RESET}] Events Processed:  {C_YELLOW}{omnimind_data.get('events_processed', 0)}{C_RESET}")
        integrity = omnimind_data.get('chain_integrity')
        if integrity:
            color = C_GREEN if integrity == "VERIFIED" else C_RED
            print(f" [{C_MAGENTA}★{C_RESET}] Chain Integrity:   {color}{integrity}{C_RESET} (last: {omnimind_data.get('last_verified_event', 'N/A')})")
        tasks = omnimind_data.get('tasks', [])
        if tasks:
            print(f" [{C_MAGENTA}★{C_RESET}] Active Tasks:")
            for t in tasks:
                t_name = t.get('name', 'TASK')
                t_stat = t.get('status', 'COMPLETED')
                t_prog = t.get('progress', 100)
                print(f"     └─ [{C_GREEN}{t_stat:<11}{C_RESET}] {t_name:<28} ({C_YELLOW}{t_prog}%{C_RESET})")
    else:
        print(f" [{C_RED}!{C_RESET}] OMNIMIND STATUS:   IDLE / WAITING FOR AGENT LOOP")

    print(f"{C_GRAY}------------------------------------------------------------------{C_RESET}")
    print(f"{C_BOLD}{C_BLUE} CONTINUITY MERKLE DAG DATABASE METRICS{C_RESET}")
    print(f"{C_GRAY}------------------------------------------------------------------{C_RESET}")

    if stats_data:
        print(f" [{C_BLUE}✓{C_RESET}] Total Database Events: {C_GREEN}{stats_data.get('total_events', 0)}{C_RESET}")
        print(f" [{C_BLUE}✓{C_RESET}] Storage Mode:          {C_CYAN}{stats_data.get('db_mode', 'WAL')}{C_RESET} (SQLite Write-Ahead Logging)")
        hash_val = stats_data.get('last_merkle_hash', '0x' + '0'*64)
        print(f" [{C_BLUE}✓{C_RESET}] Latest Merkle Hash:    {C_CYAN}{hash_val[:32]}...{C_RESET}")
    else:
        print(f" [{C_RED}!{C_RESET}] DB STATUS:            UNAVAILABLE")

    print(f"{C_BOLD}{C_CYAN}=================================================================={C_RESET}")
    print(f"{C_GRAY} Press Ctrl+C to exit monitor. Refreshing every 2s...{C_RESET}")

def main():
    parser = argparse.ArgumentParser(description="Omniverse Terminal Telemetry Monitor")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Target daemon IP (default: 127.0.0.1)")
    args = parser.parse_args()

    host_ip = args.host
    try:
        while True:
            render_dashboard(host_ip)
            time.sleep(2.0)
    except KeyboardInterrupt:
        print(f"\n{C_GREEN}[✓] Telemetry monitor closed cleanly.{C_RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()
