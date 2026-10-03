#!/usr/bin/env python3
"""
=============================================================================
🕹 THE OMNIVERSE CORE ENGINES EASTER EGG :: TERMINAL ANSI ANIMATOR
=============================================================================
A secret, lightweight Easter egg runner that renders a real-time ASCII/ANSI
visualizer of all core engines doing their processes natively on edge devices.
=============================================================================
"""

import os
import sys
import time
import math

# ANSI Escape Sequences
CYAN = "\033[96m"
MAGENTA = "\033[95m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"
CLEAR_SCREEN = "\033[H\033[2J"

def render_ascii_cube(angle):
    """Renders a wireframe 3D Cube using ASCII characters."""
    vertices = [
        [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
        [-1, -1, 1],  [1, -1, 1],  [1, 1, 1],  [-1, 1, 1]
    ]
    edges = [
        (0,1), (1,2), (2,3), (3,0),
        (4,5), (5,6), (6,7), (7,4),
        (0,4), (1,5), (2,6), (3,7)
    ]
    
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    grid = [[" " for _ in range(24)] for _ in range(11)]
    
    center_x, center_y = 12, 5
    scale_x, scale_y = 7, 3.5
    
    proj = []
    for vx, vy, vz in vertices:
        rx = vx * cos_a - vz * sin_a
        rz = vx * sin_a + vz * cos_a
        ry = vy * cos_a - rz * sin_a
        rz_final = vy * sin_a + rz * cos_a + 3.0
        
        px = int(center_x + (rx / rz_final) * scale_x)
        py = int(center_y + (ry / rz_final) * scale_y)
        px = max(0, min(23, px))
        py = max(0, min(10, py))
        proj.append((px, py))
        grid[py][px] = "✦"

    for e1, e2 in edges:
        x1, y1 = proj[e1]
        x2, y2 = proj[e2]
        steps = max(abs(x2 - x1), abs(y2 - y1), 1)
        for s in range(steps + 1):
            cx = int(x1 + (x2 - x1) * (s / steps))
            cy = int(y1 + (y2 - y1) * (s / steps))
            if 0 <= cx < 24 and 0 <= cy < 11:
                if grid[cy][cx] == " ":
                    grid[cy][cx] = "•"

    return ["".join(row) for row in grid]

def run_easter_egg_loop(max_frames=60):
    print(f"{CLEAR_SCREEN}")
    try:
        for frame in range(max_frames):
            angle = (frame / 20.0) * math.pi
            cube_lines = render_ascii_cube(angle)
            
            hash_hex = f"0x{(frame * 0xA3F12 + 0x7B12) & 0xFFFFFFFF:08X}"
            states = ["PLACE_WALL", "REPAIR_HATCH", "INSPECT_CUBE", "SCAN_HAZARD"]
            curr_state = states[frame % len(states)]
            next_state = states[(frame + 1) % len(states)]
            
            output = []
            output.append(f"{CLEAR_SCREEN}")
            output.append(f"{BOLD}{CYAN}╔═══════════════════════════════════════════════════════════════════════════╗{RESET}")
            output.append(f"{BOLD}{CYAN}║  🕹 THE OMNIVERSE :: CORE ENGINES EASTER EGG PROCESS MONITOR              ║{RESET}")
            output.append(f"{BOLD}{CYAN}╠═══════════════════════════════════════════════════════════════════════════╣{RESET}")
            
            # Line-by-line assembly (Left: 9x9 Raycast 3D Cube | Right: Knit P2P & Merkle)
            output.append(f"║ {BOLD}{GREEN}[ ENGINE 01: 9x9 RAYCAST 3D CUBE ]{RESET}   │ {BOLD}{MAGENTA}[ ENGINE 02: KNIT P2P MESH & MERKLE ]{RESET}  ║")
            
            right_info = [
                f"• Active Peer Nodes: {GREEN}4 (Wi-Fi Aware + BLE){RESET}",
                f"• Local Merkle Root: {YELLOW}{hash_hex}{RESET}",
                f"• GossipSub Relays : {CYAN}{14 + frame * 2} pkts/sec{RESET}",
                f"• CRDT Consensus   : {GREEN}IN_SYNC (0ms drift){RESET}",
                f"• Local SQLite WAL : {GREEN}127.0.0.1:9200 ACTIVE{RESET}",
                f"─────────────────────────────────────",
                f"{BOLD}{YELLOW}[ ENGINE 03: MARKOV AI BUILDER ]{RESET}",
                f"• State: {CYAN}{curr_state:<12}{RESET} -> {GREEN}{next_state}{RESET}",
                f"• AI Confidence: {GREEN}{0.65 + (frame%5)*0.05:.2f}{RESET} (Sub-1ms CPU)",
                f"• LPE Trait DNA: {MAGENTA}DNA-{(frame*1337+8888):06d}-LPE{RESET}",
                f"• Spadille Rule: {CYAN}Lead '10_S' -> K_S Win{RESET}"
            ]

            for i in range(11):
                left_part = cube_lines[i] if i < len(cube_lines) else " "*24
                right_part = right_info[i] if i < len(right_info) else ""
                # Pad to align boxes
                output.append(f"║  {CYAN}{left_part:<26}{RESET} │ {right_part:<46} ║")

            output.append(f"{BOLD}{CYAN}╠═══════════════════════════════════════════════════════════════════════════╣{RESET}")
            progress_bar = "█" * (int((frame / max_frames) * 40))
            output.append(f"║ FRAME [{frame+1:02d}/{max_frames:02d}] [{GREEN}{progress_bar:<40}{RESET}] STATUS: {GREEN}EDGE OK{RESET} ║")
            output.append(f"{BOLD}{CYAN}╚═══════════════════════════════════════════════════════════════════════════╝{RESET}")
            
            print("\n".join(output))
            time.sleep(0.1)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}Easter egg animation stopped by user.{RESET}")

if __name__ == "__main__":
    run_easter_egg_loop()
