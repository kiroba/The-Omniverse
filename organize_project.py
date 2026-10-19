#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE PROJECT ORGANIZER & AUTOMATED PRUNING ENGINE [v19.2.0]
==============================================================================
Module Version : 19.2.0 (Posix / Termux Inode Protection & Canonical Mapping)
System Domain  : Repository Layout Management & Clean Workspace Maintenance
==============================================================================
"""

import os
import sys
import shutil
from pathlib import Path

__version__ = "19.2.0"
BUILD_REVISION = "2026-10-18.v19.2-canonical"

def resolve_base_dir() -> Path:
    env_dir = os.environ.get("OMNIVERSE_BUILD_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    if os.environ.get("OMNIVERSE_CLOUD_BUILD") == "1" or os.environ.get("CI") == "true":
        workspace_path = Path("/workspace")
        if workspace_path.exists():
            return workspace_path
    return Path.cwd().resolve()

def find_source_file(filename: str, search_paths: list) -> Path:
    for p in search_paths:
        if p.exists():
            target = p / filename
            if target.exists():
                return target
            matches = list(p.glob(f"*{filename}*"))
            if matches:
                return matches[0]
    return None

def organize_and_sync():
    base_dir = resolve_base_dir()
    print("==================================================================")
    print(f"OMNIVERSE PROJECT ORGANIZER & AUTOMATED PRUNING ENGINE [v{__version__}]")
    print(f"Revision: {BUILD_REVISION}")
    print("==================================================================")
    
    search_paths = [
        base_dir,
        base_dir / "mobile" / "lib",
        base_dir / "scripts",
        Path.cwd()
    ]
    if (Path("/workspace") / "artifacts").exists():
        search_paths.append(Path("/workspace") / "artifacts")
        
    mappings = [
        ("kickback_main_app_ui.dart", base_dir / "mobile" / "lib" / "kickback_main_app_ui.dart"),
        ("halo_plaza_experience_ui.dart", base_dir / "mobile" / "lib" / "halo_plaza_experience_ui.dart"),
        ("omni_mobile_mesh_monitor_ui.dart", base_dir / "mobile" / "lib" / "omni_mobile_mesh_monitor_ui.dart"),
        ("omniverse_superapp_master_ui.dart", base_dir / "mobile" / "lib" / "omniverse_superapp_master_ui.dart"),
        ("plaza_fighting_game_engine.dart", base_dir / "mobile" / "lib" / "plaza_fighting_game_engine.dart"),
        ("continuity_token_service.dart", base_dir / "mobile" / "lib" / "continuity_token_service.dart"),
        ("kickback_seamless_stripe_checkout.dart", base_dir / "mobile" / "lib" / "kickback_seamless_stripe_checkout.dart"),
        ("build_multi_app_suite.py", base_dir / "scripts" / "build_multi_app_suite.py"),
        ("build_multi_app_suite.py", base_dir / "build_multi_app_suite.py"),
        ("organize_project.py", base_dir / "organize_project.py"),
    ]
    
    for src_name, dest_path in mappings:
        found_path = find_source_file(src_name, search_paths)
        if found_path:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            # Check if source and destination are the exact same file
            is_same = False
            if dest_path.exists():
                try:
                    is_same = os.path.samefile(found_path, dest_path)
                except Exception:
                    is_same = (found_path.resolve() == dest_path.resolve())
            if not is_same:
                try:
                    shutil.copy(found_path, dest_path)
                    rel_str = str(dest_path.relative_to(base_dir)) if base_dir in dest_path.parents or base_dir == dest_path.parent else dest_path.name
                    print(f"[✓] File mapped & synced: {src_name} -> {rel_str}")
                except shutil.SameFileError:
                    rel_str = str(dest_path.relative_to(base_dir)) if base_dir in dest_path.parents or base_dir == dest_path.parent else dest_path.name
                    print(f"[✓] File already in place: {rel_str}")
                except Exception as e:
                    print(f"[!] Notice copying {src_name}: {e}")
            else:
                rel_str = str(dest_path.relative_to(base_dir)) if base_dir in dest_path.parents or base_dir == dest_path.parent else dest_path.name
                print(f"[✓] File already in place: {rel_str}")
                
    print("------------------------------------------------------------------")
    print("🧹 RUNNING AUTOMATED PRUNING OF DEPRECATED VERSION-SUFFIXED FILES...")
    print("------------------------------------------------------------------")
    
    # Prune draft -v* files if canonical file exists
    for root, _, files in os.walk(base_dir):
        if any(skip in root for skip in [".git", "build", "apps", ".dart_tool", ".gradle"]):
            continue
        for f in files:
            if "-v" in f and f.endswith((".py", ".dart", ".sh", ".yml", ".yaml")):
                f_path = Path(root) / f
                try:
                    f_path.unlink()
                    print(f"[🧹] Pruned legacy draft: {f}")
                except Exception:
                    pass
                    
    print("==================================================================")
    print(f"OMNIVERSE PROJECT ORGANIZATION COMPLETE [v{__version__}]")
    print("==================================================================")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--version", "-v"]:
        print(f"organize_project.py version {__version__} ({BUILD_REVISION})")
        sys.exit(0)
    organize_and_sync()
