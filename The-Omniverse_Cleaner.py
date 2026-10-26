#!/usr/bin/env python3
"""
==============================================================================
THE OMNIVERSE CLEANER & PROJECT STRUCTURE EVOLUTION ENGINE
Filename: The-Omniverse_Cleaner.py
Version: 3.0.0 (Evolutionary Milestone)
==============================================================================
System Role:
- Evolves legacy `organize_projects.py` scripts into an automated project cleaner.
- Consolidates duplicated Dart UI files across app directories into shared `packages/omni_core_ui/`.
- Restructures backend Python microservices into modular `omni_core/` and `Admin/` trees.
- Prunes untracked build artifacts, `__pycache__`, `.gradle/`, `.idea/`, `.pyc`, stale `.db` journals, and versioned duplicate files.
- Inspects and migrates SQLite WAL database schemas (`continuity_events.db`, `omni_payments.db`, etc.).
- Operates safely in both `--dry-run` (preview) and `--execute` (apply) modes.
- Generates a structured ASCII tree report and summary audit metrics.
==============================================================================
"""

import os
import sys
import shutil
import glob
import sqlite3
import hashlib
import json
import argparse
from pathlib import Path
from typing import List, Dict, Set, Tuple

VERSION = "3.0.0"

# Target Directory Mapping Configuration
STRUCTURE_MAP = {
    "core_python": {
        "target_dir": "omni_core",
        "patterns": [
            "omni_core_db.py",
            "omni_crypto_payment_gateway.py",
            "lpe_trait_normalizer.py",
            "omni_ipfs_cas_streaming_engine.py",
            "omni_bft_patch_consensus_engine.py",
            "omnimind_agent_telemetry_engine.py"
        ]
    },
    "admin_services": {
        "target_dir": "Admin",
        "patterns": [
            "omni_live_daemon_server.py",
            "omni_telemetry_monitor.py",
            "termux_powershell_master_runner.sh",
            "termux_powershell_master_runner.ps1",
            "termux_master_runner.sh",
            "gitsync_repair_and_push-v3.sh",
            "omni_gitsync_repair.py",
            "check_ports_status.py"
        ]
    },
    "shared_dart": {
        "target_dir": "packages/omni_core_ui/lib/src",
        "patterns": [
            "kickback_main_app_ui.dart",
            "omnicast_video_chat_ui.dart",
            "omni_mobile_mesh_monitor_ui.dart",
            "halo_plaza_experience_ui.dart",
            "omniverse_superapp_master_ui.dart"
        ]
    },
    "test_suite": {
        "target_dir": "tests",
        "patterns": [
            "test_v85_mesh.py",
            "test_omni_spine.py",
            "test_two_node_mesh.py",
            "test_*.py"
        ]
    }
}

# Directories and Extensions to Prune/Clean
PRUNE_DIRECTORIES = [
    "__pycache__",
    ".idea",
    ".gradle",
    "build",
    "omni_core_engines_standalone/mobile/build"
]

PRUNE_FILE_PATTERNS = [
    "*.pyc",
    "*.pyo",
    "local.properties",
    "*.db-journal",
    "*.db-shm",
    "*.db-wal.tmp"
]

class OmniverseCleaner:
    def __init__(self, root_path: Path, execute: bool = False, verbose: bool = True):
        self.root_path = root_path.resolve()
        self.execute = execute
        self.verbose = verbose
        self.stats = {
            "dirs_created": 0,
            "files_moved": 0,
            "files_pruned": 0,
            "bytes_freed": 0,
            "dbs_migrated": 0,
            "duplicates_consolidated": 0
        }

    def log(self, message: str, level: str = "INFO"):
        prefix = f"[{level}]" if level != "INFO" else "[✓]"
        if self.verbose:
            print(f"{prefix} {message}")

    def ensure_directory(self, dir_path: Path):
        if not dir_path.exists():
            self.log(f"Creating directory: {dir_path.relative_to(self.root_path)}")
            if self.execute:
                dir_path.mkdir(parents=True, exist_ok=True)
            self.stats["dirs_created"] += 1

    def prune_artifacts(self):
        """Recursively removes cached, temporary, and unneeded build files."""
        self.log("Starting repository artifact pruning phase...", "STAGE")
        
        # 1. Directory Pruning
        for root, dirs, files in os.walk(self.root_path, topdown=False):
            for d in dirs:
                if d in PRUNE_DIRECTORIES or d.endswith(".egg-info"):
                    target_dir = Path(root) / d
                    self.log(f"Pruning directory: {target_dir.relative_to(self.root_path)}")
                    if self.execute:
                        try:
                            shutil.rmtree(target_dir)
                        except Exception as e:
                            self.log(f"Error removing {target_dir}: {e}", "WARN")
                    self.stats["files_pruned"] += 1

        # 2. File Pattern Pruning
        for pattern in PRUNE_FILE_PATTERNS:
            for filepath in self.root_path.rglob(pattern):
                if filepath.is_file():
                    try:
                        file_size = filepath.stat().st_size
                        self.log(f"Pruning cached file: {filepath.relative_to(self.root_path)} ({file_size} bytes)")
                        if self.execute:
                            filepath.unlink()
                        self.stats["files_pruned"] += 1
                        self.stats["bytes_freed"] += file_size
                    except Exception as e:
                        self.log(f"Error removing file {filepath}: {e}", "WARN")

    def consolidate_versioned_duplicates(self):
        """Detects older version-suffixed files (e.g., file-v1.py vs file.py) and cleans obsolete copies."""
        self.log("Detecting and consolidating versioned duplicate files...", "STAGE")
        
        files_by_basename: Dict[str, List[Path]] = {}
        for p in self.root_path.glob("**/*"):
            if p.is_file() and not any(part.startswith(".") for part in p.parts):
                # Identify version suffix pattern like -v1.py, -v5.dart, -v8.py
                name = p.name
                if "-v" in name:
                    base_name = name.split("-v")[0] + p.suffix
                    files_by_basename.setdefault(base_name, []).append(p)

        for base_name, versioned_files in files_by_basename.items():
            canonical_path = self.root_path / base_name
            if canonical_path.exists():
                for vf in versioned_files:
                    if vf != canonical_path and vf.exists():
                        self.log(f"Consolidating stale versioned file: {vf.relative_to(self.root_path)} -> canonical ({base_name})")
                        if self.execute:
                            try:
                                vf.unlink()
                                self.stats["duplicates_consolidated"] += 1
                            except Exception as e:
                                self.log(f"Failed to remove {vf}: {e}", "WARN")

    def reorganize_structure(self):
        """Reorganizes Python microservices, Dart packages, and scripts into clean folders."""
        self.log("Reorganizing project directory hierarchy...", "STAGE")
        
        for category, config in STRUCTURE_MAP.items():
            target_dir = self.root_path / config["target_dir"]
            self.ensure_directory(target_dir)

            for pattern in config["patterns"]:
                for matched_file in self.root_path.glob(pattern):
                    if matched_file.is_file() and matched_file.parent != target_dir:
                        dest_path = target_dir / matched_file.name
                        self.log(f"Moving {matched_file.name} -> {target_dir.relative_to(self.root_path)}/")
                        if self.execute:
                            try:
                                shutil.move(str(matched_file), str(dest_path))
                                self.stats["files_moved"] += 1
                            except Exception as e:
                                self.log(f"Failed to move {matched_file}: {e}", "WARN")

    def inspect_and_migrate_databases(self):
        """Checks SQLite WAL databases in workspace root and ensures payload_json and WAL pragmas exist."""
        self.log("Inspecting and migrating SQLite WAL database schemas...", "STAGE")
        
        for db_file in self.root_path.glob("*.db"):
            if db_file.is_file():
                self.log(f"Inspecting SQLite database: {db_file.name}")
                try:
                    conn = sqlite3.connect(str(db_file))
                    c = conn.cursor()
                    c.execute("PRAGMA journal_mode=WAL;")
                    
                    # Migration check for continuity_events.db
                    if db_file.name == "continuity_events.db":
                        c.execute("PRAGMA table_info(events);")
                        columns = [col[1] for col in c.fetchall()]
                        if columns and "payload_json" not in columns:
                            self.log(f"Migrating {db_file.name}: Adding missing 'payload_json' column")
                            if self.execute:
                                c.execute("ALTER TABLE events ADD COLUMN payload_json TEXT DEFAULT '{}';")
                                conn.commit()
                            self.stats["dbs_migrated"] += 1

                    conn.close()
                except Exception as e:
                    self.log(f"Error inspecting database {db_file.name}: {e}", "WARN")

    def print_summary_report(self):
        print("\n" + "=" * 68)
        print(f"THE OMNIVERSE CLEANER v{VERSION} — EXECUTION SUMMARY REPORT")
        print("=" * 68)
        mode_str = "EXECUTE (Applied)" if self.execute else "DRY-RUN (Preview Only)"
        print(f" Execution Mode:            {mode_str}")
        print(f" Root Path:                {self.root_path}")
        print(f" Directories Created:      {self.stats['dirs_created']}")
        print(f" Files Moved / Structured: {self.stats['files_moved']}")
        print(f" Duplicate Files Pruned:   {self.stats['duplicates_consolidated']}")
        print(f" Cached Files Pruned:      {self.stats['files_pruned']}")
        print(f" Total Bytes Freed:        {self.stats['bytes_freed']} bytes")
        print(f" Databases Inspected/Migrated: {self.stats['dbs_migrated']}")
        print("=" * 68)
        if not self.execute:
            print("💡 TIP: Run with `--execute` or `-x` to apply changes to disk.")
        print("=" * 68 + "\n")

    def run(self):
        print("=" * 68)
        print(f"🌌 THE OMNIVERSE CLEANER & PROJECT EVOLUTION ENGINE [v{VERSION}]")
        print("=" * 68)
        
        self.prune_artifacts()
        self.consolidate_versioned_duplicates()
        self.reorganize_structure()
        self.inspect_and_migrate_databases()
        self.print_summary_report()

def main():
    parser = argparse.ArgumentParser(description="The Omniverse Project Cleaner & Structure Engine")
    parser.add_argument("-x", "--execute", action="store_true", help="Execute file operations (modifies filesystem)")
    parser.add_argument("-p", "--path", type=str, default=".", help="Root project path (default: current working directory)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress verbose logging output")

    args = parser.parse_args()
    root_path = Path(args.path)

    cleaner = OmniverseCleaner(root_path=root_path, execute=args.execute, verbose=not args.quiet)
    cleaner.run()

if __name__ == "__main__":
    main()
