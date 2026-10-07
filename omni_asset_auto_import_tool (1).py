#!/usr/bin/env python3
"""
===============================================================================
OMNIVERSE UNIVERSAL ASSET AUTO-IMPORT & MANAGEMENT TOOL
===============================================================================
System Design Architecture:
- Creates standardized, modular asset directory hierarchies across all 8 planets.
- Monitors / Processes a central 'raw_imports/' drop-zone directory.
- Auto-classifies raw 3D models (.glb, .gltf), 2D textures (.png, .jpg),
  audio clips (.wav, .ogg), shaders (.fmat, .glsl), and LPE cosmetic traits.
- Generates/updates JSON asset manifests per planet and syncs Flutter pubspec.yaml.
===============================================================================
"""

import os
import sys
import shutil
import json
import re
import hashlib
from pathlib import Path

# Base workspace directory configuration
BASE_DIR = Path("/workspace/scratch/omni_assets_workspace")
RAW_IMPORTS_DIR = BASE_DIR / "raw_imports"
ASSETS_DIR = BASE_DIR / "assets"

# Planet & Subsystem Directory Definitions
PLANET_CONFIGS = {
    "planet_02_9x9": {
        "name": "Planet 02: 9x9 3D Cube Maze",
        "subdirs": ["models", "textures", "shaders", "audio"],
        "keywords": ["9x9", "cube", "maze", "wall", "hatch", "spike", "laser"]
    },
    "planet_03_janken": {
        "name": "Planet 03: Janken Markov AI Plaza",
        "subdirs": ["models", "ui", "markov_rules"],
        "keywords": ["janken", "rps", "markov", "npc", "builder_bot"]
    },
    "planet_04_social_deduction": {
        "name": "Planet 04: ImpostorMX Social Deduction",
        "subdirs": ["models", "ui", "audio"],
        "keywords": ["impostor", "crewmate", "sabotage", "vote", "meeting"]
    },
    "planet_05_asteroids": {
        "name": "Planet 05: Asteroids Arcade Arena",
        "subdirs": ["sprites", "audio", "shaders"],
        "keywords": ["asteroid", "ship", "laser", "arcade", "bullet"]
    },
    "planet_06_puzzle_vault": {
        "name": "Planet 06: The Omni Puzzle Vault",
        "subdirs": ["ui", "puzzles", "icons"],
        "keywords": ["puzzle", "tile", "sliding", "ring", "vault"]
    },
    "planet_07_spades": {
        "name": "Planet 07: Spades Card Lounge",
        "subdirs": ["cards", "tables", "audio"],
        "keywords": ["card", "spade", "deck", "trick", "table"]
    },
    "idle_plaza": {
        "name": "LPE Idle Plaza & Avatar Cosmetics",
        "subdirs": ["layers/Headwear", "layers/Torso", "layers/Legs", "layers/Accessories", "3d_models"],
        "keywords": ["avatar", "hat", "shirt", "jacket", "lpe", "cosmetic", "trait"]
    },
    "phaser_marquee": {
        "name": "Phaser 2D/3D Arcade Marquee Canvas",
        "subdirs": ["sprites", "shaders", "cabinets"],
        "keywords": ["marquee", "cabinet", "aura", "glow", "spectator"]
    }
}

def init_directory_structure():
    """Builds the modular directory tree across all planets and drop-zones."""
    print("📁 Initializing Universal Asset Directory Hierarchy...")
    os.makedirs(RAW_IMPORTS_DIR, exist_ok=True)
    
    for planet_key, config in PLANET_CONFIGS.items():
        planet_root = ASSETS_DIR / planet_key
        os.makedirs(planet_root, exist_ok=True)
        for subdir in config["subdirs"]:
            os.makedirs(planet_root / subdir, exist_ok=True)
            
    print(f"  ✓ Created asset roots in: {ASSETS_DIR}")
    print(f"  ✓ Drop-zone ready at: {RAW_IMPORTS_DIR}")

def classify_file(filename):
    """Categorizes an incoming file into the correct target planet and subdirectory based on extension and keywords."""
    filename_lower = filename.lower()
    ext = Path(filename).suffix.lower()
    
    # Identify target planet via keyword matching
    target_planet = "planet_02_9x9"  # Default fallback
    for p_key, p_cfg in PLANET_CONFIGS.items():
        if any(kw in filename_lower for kw in p_cfg["keywords"]):
            target_planet = p_key
            break
            
    # Identify target subdirectory based on file extension
    target_subdir = "models"
    if ext in [".glb", ".gltf", ".obj", ".fbx"]:
        target_subdir = "3d_models" if target_planet == "idle_plaza" else "models"
    elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
        if "layer" in filename_lower or target_planet == "idle_plaza":
            if "hat" in filename_lower or "head" in filename_lower:
                target_subdir = "layers/Headwear"
            elif "shirt" in filename_lower or "torso" in filename_lower or "jacket" in filename_lower:
                target_subdir = "layers/Torso"
            elif "pant" in filename_lower or "leg" in filename_lower:
                target_subdir = "layers/Legs"
            else:
                target_subdir = "layers/Accessories"
        elif ext == ".png" and ("card" in filename_lower or target_planet == "planet_07_spades"):
            target_subdir = "cards"
        elif target_planet in ["planet_05_asteroids", "phaser_marquee"]:
            target_subdir = "sprites"
        else:
            target_subdir = "textures"
    elif ext in [".fmat", ".glsl", ".frag", ".vert"]:
        target_subdir = "shaders"
    elif ext in [".wav", ".ogg", ".mp3"]:
        target_subdir = "audio"
    elif ext in [".json", ".yaml"]:
        target_subdir = "puzzles" if target_planet == "planet_06_puzzle_vault" else "ui"
        
    return target_planet, target_subdir

def process_raw_imports():
    """Scans raw_imports/, moves files to designated planet folders, and generates asset manifests."""
    print("\n🔄 Scanning Drop-Zone ('raw_imports/')...")
    raw_files = [f for f in os.listdir(RAW_IMPORTS_DIR) if os.path.isfile(RAW_IMPORTS_DIR / f)]
    
    if not raw_files:
        print("  ℹ No new files in drop-zone. Placing sample placeholder assets for verification...")
        sample_files = {
            "9x9_door_hatch.glb": b"GLTF_BINARY_HEADER_SAMPLE_3D_MODEL",
            "spades_card_ace.png": b"PNG_HEADER_SAMPLE_2D_CARD_TEXTURE",
            "avatar_hat_helm#20.png": b"PNG_HEADER_SAMPLE_COSMETIC_LAYER",
            "laser_glow.fmat": b"IMPELLER_SHADER_MATERIAL_SPEC",
            "asteroid_bullet.wav": b"RIFF_WAV_HEADER_SAMPLE_AUDIO"
        }
        for name, content in sample_files.items():
            with open(RAW_IMPORTS_DIR / name, "wb") as f:
                f.write(content)
        raw_files = list(sample_files.keys())

    processed_count = 0
    import_log = []

    for fname in raw_files:
        src_path = RAW_IMPORTS_DIR / fname
        planet_key, subdir = classify_file(fname)
        
        dest_dir = ASSETS_DIR / planet_key / subdir
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = dest_dir / fname
        
        shutil.move(src_path, dest_path)
        processed_count += 1
        
        import_log.append({
            "file": fname,
            "target_planet": planet_key,
            "target_subdir": subdir,
            "path": str(dest_path.relative_to(BASE_DIR))
        })
        print(f"  ✓ Imported: '{fname}' ──> [{planet_key}/{subdir}]")

    # Generate asset manifest per planet
    print("\n📑 Updating Planet Asset Manifests (JSON)...")
    for planet_key in PLANET_CONFIGS.keys():
        planet_root = ASSETS_DIR / planet_key
        manifest_path = planet_root / "asset_manifest.json"
        
        file_list = []
        for root, _, files in os.walk(planet_root):
            for file in files:
                if file != "asset_manifest.json":
                    rel_path = str(Path(root) / file)
                    file_list.append(rel_path)
                    
        manifest_data = {
            "planet_id": planet_key,
            "total_assets": len(file_list),
            "files": file_list
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

    return processed_count, import_log

def generate_pubspec_assets_snippet():
    """Generates the pubspec.yaml asset imports block for Flutter integration."""
    snippet = ["# Auto-Generated Omniverse Asset Import Block for pubspec.yaml", "flutter:", "  assets:"]
    for planet_key in PLANET_CONFIGS.keys():
        snippet.append(f"    - assets/planets/{planet_key}/")
        for subdir in PLANET_CONFIGS[planet_key]["subdirs"]:
            snippet.append(f"    - assets/planets/{planet_key}/{subdir}/")
    return "\n".join(snippet)

def main():
    print("=============================================================================")
    print("🚀 OMNIVERSE UNIVERSAL ASSET AUTO-IMPORT & MANAGEMENT TOOL")
    print("=============================================================================")
    init_directory_structure()
    count, log = process_raw_imports()
    pubspec_snippet = generate_pubspec_assets_snippet()
    
    # Save pubspec snippet
    with open(BASE_DIR / "pubspec_assets_snippet.yaml", "w", encoding="utf-8") as f:
        f.write(pubspec_snippet)
        
    summary = {
        "status": "ASSETS_PROCESSED_AND_INDEXED",
        "processed_files": count,
        "import_log": log,
        "pubspec_snippet_generated": True
    }
    print("\n" + json.dumps(summary, indent=2))
    print("=============================================================================")
    print("✅ ASSET AUTO-IMPORT COMPLETE! ALL PLANETS INDEXED.")
    print("=============================================================================")

if __name__ == "__main__":
    main()
