#!/usr/bin/env python3
"""
=============================================================================
THE OMNIVERSE / THE KICKBACK - LIFEED MIGRATION & REFACTORING SUITE
=============================================================================
Automated Refactoring Tool: Replaces all legacy 'LiFeed' / 'lifeed' references 
with 'LiFeed' / 'lifeed' across source files, configurations, documentation, 
and file path names while preserving case-sensitivity and binary integrity.
=============================================================================
"""

import os
import sys
import argparse
import re
from typing import List, Tuple, Dict

# File extensions to include in refactoring scan
TEXT_FILE_EXTENSIONS = {
    '.py', '.dart', '.sh', '.md', '.json', '.yaml', '.yml', '.kt', '.java',
    '.js', '.ts', '.tsx', '.html', '.css', '.txt', '.sol', '.xml', '.gradle'
}

# Directories to ignore
IGNORE_DIRS = {
    '.git', '.idea', '.vscode', '.dart_tool', 'build', 'node_modules',
    '__pycache__', '.gradle', 'dist', 'out'
}

# Case replacement dictionary (order matters to catch specific constructs first)
REPLACEMENT_PAIRS: List[Tuple[str, str]] = [
    ("LiFeedToken", "LiFeedToken"),
    ("lifeed_token", "lifeed_token"),
    ("com.lifeed", "com.lifeed"),
    ("LiFeed", "LiFeed"),
    ("LiFeed", "LiFeed"),
    ("LIFEED", "LIFEED"),
    ("lifeed", "lifeed")
]


def is_text_file(filepath: str) -> bool:
    """Check if file should be processed based on extension and binary check."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in TEXT_FILE_EXTENSIONS:
        return True
    # For extensionless files or shell scripts
    if not ext:
        try:
            with open(filepath, 'tr', encoding='utf-8') as f:
                f.read(1024)
                return True
        except (UnicodeDecodeError, PermissionError):
            return False
    return False


def refactor_content(content: str) -> Tuple[str, int]:
    """Perform case-preserving replacement of LiFeed -> LiFeed."""
    total_replacements = 0
    modified_content = content

    for target, replacement in REPLACEMENT_PAIRS:
        count = len(re.findall(re.escape(target), modified_content))
        if count > 0:
            modified_content = re.sub(re.escape(target), replacement, modified_content)
            total_replacements += count

    return modified_content, total_replacements


def rename_path_if_needed(path: str, dry_run: bool = False) -> str:
    """Rename a file or directory if its name contains 'lifeed' or 'LiFeed'."""
    dirname, basename = os.path.split(path)
    new_basename = basename

    for target, replacement in REPLACEMENT_PAIRS:
        if target in new_basename:
            new_basename = new_basename.replace(target, replacement)

    if new_basename != basename:
        new_path = os.path.join(dirname, new_basename)
        if not dry_run:
            os.rename(path, new_path)
            print(f"  [RENAMED] {basename} -> {new_basename}")
        else:
            print(f"  [DRY RUN RENAME] {basename} -> {new_basename}")
        return new_path

    return path


def run_migration(target_root: str, dry_run: bool = False):
    """Walk directory tree, refactor file contents, and rename matching paths."""
    print("=============================================================================")
    print("🚀 STARTING LIFEED MIGRATION & REFACTORING SUITE")
    print(f"   Target Directory: {os.path.abspath(target_root)}")
    print(f"   Mode: {'DRY RUN (No changes written)' if dry_run else 'ACTIVE MIGRATION'}")
    print("=============================================================================\n")

    scanned_files = 0
    modified_files = 0
    total_text_replacements = 0
    renamed_paths = 0

    files_to_rename: List[str] = []

    for root, dirs, files in os.walk(target_root, topdown=True):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for filename in files:
            filepath = os.path.join(root, filename)
            scanned_files += 1

            # Check if filename contains 'lifeed' for later renaming
            if any(target in filename for target, _ in REPLACEMENT_PAIRS):
                files_to_rename.append(filepath)

            if not is_text_file(filepath):
                continue

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                new_content, count = refactor_content(content)

                if count > 0:
                    total_text_replacements += count
                    modified_files += 1
                    rel_path = os.path.relpath(filepath, target_root)
                    
                    if not dry_run:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"  [UPDATED] {rel_path} ({count} replacements)")
                    else:
                        print(f"  [DRY RUN MATCH] {rel_path} ({count} matches)")

            except Exception as e:
                print(f"  ⚠️ Error reading {filepath}: {e}")

    # Process file renaming (bottom-up to avoid invalidating paths)
    if files_to_rename:
        print("\n📁 Renaming Matching Files...")
        for filepath in files_to_rename:
            if os.path.exists(filepath):
                rename_path_if_needed(filepath, dry_run=dry_run)
                renamed_paths += 1

    print("\n=============================================================================")
    print("  LIFEED MIGRATION SUMMARY")
    print("=============================================================================")
    print(f"  Scanned Files:              {scanned_files}")
    print(f"  Modified Files:             {modified_files}")
    print(f"  Text Replacements Made:     {total_text_replacements}")
    print(f"  Renamed Files/Paths:        {renamed_paths}")
    print(f"  Status:                     {'🎉 MIGRATION COMPLETE' if not dry_run else '🔍 DRY RUN COMPLETED'}")
    print("=============================================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate all 'LiFeed' references to 'LiFeed'.")
    parser.add_argument("path", nargs="?", default=".", help="Root path of repository or directory to migrate (default: current directory)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate changes without writing to disk")
    args = parser.parse_args()

    run_migration(args.path, dry_run=args.dry_run)
