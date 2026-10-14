#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE MOBILE MESH MONITOR STANDALONE APP BUILDER
==============================================================================
Dynamic Path Resolution for GitHub Actions, Windows, Linux, and Mobile Termux.
==============================================================================
"""

import os
import sys
import shutil
from pathlib import Path

def find_repo_root() -> Path:
    """Dynamically resolves the repository root directory across environments."""
    current = Path(__file__).parent.resolve()
    if (current / ".git").exists() or (current / ".github").exists():
        return current
    if (current.parent / ".git").exists() or (current.parent / ".github").exists():
        return current.parent
    
    cwd = Path.cwd().resolve()
    if (cwd / ".git").exists() or (cwd / ".github").exists():
        return cwd
    return cwd

def build_standalone_monitor_app(base_dir: Path = None):
    if base_dir is None:
        base_dir = find_repo_root()
        
    print("==================================================================")
    print(f"BUILDING MOBILE MESH MONITOR STANDALONE APP at: {base_dir}")
    print("==================================================================")

    target_dir = base_dir / "omni_mobile_mesh_monitor_app"
    mobile_lib = target_dir / "mobile" / "lib"
    
    mobile_lib.mkdir(parents=True, exist_ok=True)
    
    source_ui = None
    for candidate in [
        base_dir / "omni_mobile_mesh_monitor_ui.dart",
        base_dir / "mobile" / "lib" / "omni_mobile_mesh_monitor_ui.dart",
        base_dir / "core" / "engines" / "omni_mobile_mesh_monitor_ui.dart",
    ]:
        if candidate.exists():
            source_ui = candidate
            break

    if source_ui and source_ui.exists():
        shutil.copy(source_ui, mobile_lib / "main.dart")
        print(f"[✓] Copied Monitor UI from {source_ui.name} -> mobile/lib/main.dart")
    else:
        print("[!] Warning: omni_mobile_mesh_monitor_ui.dart not found; creating stub main.dart")
        with open(mobile_lib / "main.dart", "w") as f:
            f.write("// Omni Mobile Mesh Monitor Application\n")

    pubspec_content = """name: omni_mobile_mesh_monitor_app
description: "Standalone Mobile Mesh Health & P2P Node Telemetry App"
publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.6

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0

flutter:
  uses-material-design: true
"""
    with open(target_dir / "mobile" / "pubspec.yaml", "w") as f:
        f.write(pubspec_content)

    print("[✓] pubspec.yaml generated successfully!")
    print("==================================================================")
    print("BUILD COMPLETE at:", target_dir)
    print("==================================================================")

if __name__ == "__main__":
    build_standalone_monitor_app()
