#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE CORE ENGINES STANDALONE APP BUILDER (V4)
==============================================================================
System Design Architecture:
- Integrates all core engine runners, local IPC gateway (127.0.0.1:9200),
  Socioboard 5.0 B2B Enterprise Gateway, and Windows Back Button Navigation.
- Embeds KickBack Main App UI v4, Halo Plaza Experience UI v4, and OmniPhaser
  2D Creator Studio UI into the Flutter application structure.
- Integrates LocalSend REST Chunk Receiver and OmniMod Compiler into the
  Python backend services.
- Packages pre-compiled `.omnimod` starter templates for 5 industries into
  `mobile/assets/mods/` for immediate pre-launch showcase testing.
==============================================================================
"""

import os
import sys
import shutil
import json
from pathlib import Path

def build_v4_standalone_app(base_dir: Path):
    print("==================================================================")
    print("BUILDING OMNIVERSE CORE ENGINES STANDALONE APP (V4)")
    print("==================================================================")
    
    target_dir = base_dir / "omni_core_engines_standalone"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    
    target_dir.mkdir(parents=True, exist_ok=True)
    mobile_lib = target_dir / "mobile" / "lib"
    mobile_assets = target_dir / "mobile" / "assets" / "mods"
    backend_dir = target_dir / "backend"
    
    mobile_lib.mkdir(parents=True, exist_ok=True)
    mobile_assets.mkdir(parents=True, exist_ok=True)
    backend_dir.mkdir(parents=True, exist_ok=True)
    
    artifacts = Path("/workspace/artifacts")
    
    # 1. Copy UI Files
    shutil.copy(artifacts / "kickback_main_app_ui-v4.dart", mobile_lib / "main.dart")
    shutil.copy(artifacts / "halo_plaza_experience_ui-v4.dart", mobile_lib / "halo_plaza_experience_ui.dart")
    shutil.copy(artifacts / "omni_phaser_studio_ui.dart", mobile_lib / "omni_phaser_studio_ui.dart")
    
    print("[✓] UI Files copied: main.dart (v4), halo_plaza_experience_ui.dart (v4), omni_phaser_studio_ui.dart")
    
    # 2. Copy Backend Services
    shutil.copy(artifacts / "localsend_chunk_receiver.py", backend_dir / "localsend_chunk_receiver.py")
    shutil.copy(artifacts / "omni_mod_compiler.py", backend_dir / "omni_mod_compiler.py")
    shutil.copy(artifacts / "omni_mod_starter_templates.json", backend_dir / "omni_mod_starter_templates.json")
    
    print("[✓] Backend Services copied: LocalSend Receiver, OmniMod Compiler, Starter Templates")
    
    # 3. Generate Compiled Showcase Mods in Assets
    scratch = Path("/workspace/scratch")
    showcase_mods_dir = scratch / "compiled_showcase_mods"
    if showcase_mods_dir.exists():
        for mod_file in showcase_mods_dir.glob("*.omnimod"):
            shutil.copy(mod_file, mobile_assets / mod_file.name)
            print(f"[✓] Showcase Mod packaged into assets: {mod_file.name}")

    # 4. Create master pubspec.yaml
    pubspec_content = """name: omni_core_engines_standalone
description: "The KickBack & Omniverse Core Engines Mobile & Desktop Application (V4)"
publish_to: 'none'
version: 4.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  flutter_inappwebview: ^6.0.0
  cupertino_icons: ^1.0.6

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0

flutter:
  uses-material-design: true
  assets:
    - assets/mods/
"""
    with open(target_dir / "mobile" / "pubspec.yaml", "w") as f:
        f.write(pubspec_content)

    print("[✓] pubspec.yaml generated successfully!")
    print("==================================================================")
    print("STANDALONE V4 BUILD COMPLETE at:", target_dir)
    print("==================================================================")

if __name__ == "__main__":
    build_v4_standalone_app(Path("/workspace"))
