#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE UNIVERSAL DESKTOP 1-CLICK LAUNCHER
==============================================================================
Starts the P2P Mesh Relay Daemon on 127.0.0.1:9200 and launches the 
Flet Material 3 Desktop Control Panel in a single command.
==============================================================================
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path

def launch_desktop():
    print("==================================================================")
    print("OMNIVERSE UNIVERSAL DESKTOP 1-CLICK LAUNCHER")
    print("==================================================================")
    
    base_dir = Path.cwd().resolve()
    print(f"[INFO] Operating System: {sys.platform}")
    print(f"[INFO] Base Directory: {base_dir}")
    
    # 1. Locate P2P Relay Daemon Script
    daemon_script = None
    for p in [base_dir / "run_desktop_daemon.py", base_dir / "backend" / "localsend_chunk_receiver.py", base_dir / "p2p_mesh_health_monitor.py"]:
        if p.exists():
            daemon_script = p
            break
            
    # 2. Locate Flet Desktop GUI Control Panel
    gui_script = None
    for p in [base_dir / "omni_flet_desktop_control_panel.py", base_dir / "backend" / "omni_flet_desktop_control_panel.py"]:
        if p.exists():
            gui_script = p
            break
            
    daemon_proc = None
    if daemon_script:
        print(f"[INFO] Starting P2P Mesh Relay Daemon: {daemon_script.name}...")
        daemon_proc = subprocess.Popen([sys.executable, str(daemon_script)])
        time.sleep(1.5)
    else:
        print("[!] Note: Running standalone GUI mode (Daemon script not detected in root)")
        
    print("==================================================================")
    print("LAUNCHING DESKTOP CONTROL PANEL...")
    print("==================================================================")
    
    try:
        if gui_script:
            subprocess.run([sys.executable, str(gui_script)])
        else:
            print("[INFO] Flet GUI not found locally. Running native Flutter Desktop...")
            flutter_dir = base_dir / "omni_core_engines_standalone" / "mobile"
            if flutter_dir.exists():
                plat = "windows" if sys.platform == "win32" else ("macos" if sys.platform == "darwin" else "linux")
                subprocess.run(["flutter", "run", "-d", plat], cwd=flutter_dir)
            else:
                print("[!] Error: Could not locate desktop GUI or Flutter desktop directory.")
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down desktop processes...")
    finally:
        if daemon_proc:
            print("[INFO] Terminating background daemon process...")
            daemon_proc.terminate()
            
    print("==================================================================")
    print("DESKTOP LAUNCHER SHUTDOWN COMPLETE")
    print("==================================================================")

if __name__ == "__main__":
    launch_desktop()
