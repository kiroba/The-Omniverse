# The Omniverse: Standalone Planet Apps & Graphic Asset Specification

This document provides a comprehensive, structured breakdown of all 8 standalone planet applications, core subsystems, execution levels, and exact graphical asset requirements needed for UI/UX layouts, 2D/3D art pipelines, storefront banners, and in-game UI components across **The Omniverse** ecosystem.

---

## 🏗️ Architectural Execution Overview

All standalone mini-apps and background generation daemons execute natively on the **Edge Device Level**:
- **Standalone Mode:** Executes within dedicated **Flutter Dart Isolates** and local app storage sandboxes, generating and rendering assets on-device with $0 cloud infrastructure costs.
- **Omni-Hub Integrated Mode:** Connects to the local edge daemon (`127.0.0.1:9200`) over loopback IPC sockets, committing signed Merkle event envelopes into `omni_hub_immutable.db`.

---

## 📱 Standalone Planet Applications & Graphic Asset Matrix

### 1. Planet 01: The KickBack & Social Hub
* **Core Technology:** Flutter / Dart, Material You 3, Liquid UI Templates
* **Description:** Sovereign, 100% human-verified social feed, creator paywalls, live-stream reaction overlays, and decentralized store.
* **Graphical Asset Requirements:**
  - **App Launcher Icons:** `ic_launcher.png` (192x192, 512x512 PNG, vector adaptive mask).
  - **Feed Header & Store Banners:** 1200x630 PNG/WebP banner graphics (The KickBack Human Connection Showcase, Creator Studio Banner).
  - **User Profile & Feed Overlays:**
    - Live Persona Avatar Frame Overlays (512x512 transparent PNG).
    - Reaction Emotes & Micro-Gifs (128x128 transparent PNGs).
    - Verified Human Badge & Creator Tier Icons (Gold, Platinum, Educator, SW Enclave).
  - **Storefront Cards:** 400x250 PNG preview cards for digital tickets, memberships, and creator access passes.

---

### 2. Planet 02: 9x9 (Cubic Survival Maze)
* **Core Technology:** Native Flutter 3D Engine (`flutter_scene` Impeller / `FlutterPS` Raycaster)
* **Description:** Procedural 729-room (9x9x9) cubic maze escape with environmental hazards, scavenged item PvP/co-op, and Builder NPC repairs.
* **Graphical Asset Requirements:**
  - **3D Modular GLTF Models (`.glb` / `.gltf`):**
    - `planet02_wall_panel.glb`: Modular metallic cubic room wall segment.
    - `planet02_hatch_door.glb`: 6-directional opening hatch door frame (North, South, East, West, Up, Down).
    - `planet02_spike_trap.glb`, `laser_emitter.glb`, `gas_vent.glb`: Hazard trap models.
    - `terminal_kiosk.glb`: In-room terminal for hacking & scavenging.
  - **2D Touch Joystick & HUD UI:**
    - Virtual Dual-Touch Joysticks (WASD Movement Ring & Camera Look Pitch/Yaw Touch Pad).
    - Health Bar, Oxygen Level Gauge, & Hazard Warning Icons (Spikes, Lasers, Toxic Gas).
    - 3D Room Coordinate Radar (`X, Y, Z` HUD Display).
  - **Shaders & Particles (`.fmat` / `.glsl`):**
    - `laser_glow.fmat`: Welding/laser beam shader for Builder NPC cube repairs.
    - `hologram_grid.fmat`: Holographic door hatch indicator.

---

### 3. Planet 03: Janken & Plaza Builder
* **Core Technology:** Jetpack Compose / Flutter, Adaptive Markov Chain AI Engine
* **Description:** Modern, privacy-first RPSLS game with adaptive Markov AI, integrated with Plaza Builder & Information NPCs.
* **Graphical Asset Requirements:**
  - **Gesture Icons (256x256 Transparent PNGs):**
    - Rock, Paper, Scissors, Lizard, Spock vector hand glyphs.
  - **Plaza Builder NPC Assets:**
    - 2D Character Sprites / 3D Avatar Models for `BUILDER_NPC` and `INFO_NPC`.
    - Repair Tool Icons: Welding Torch, Laser Cutter, Structural Hologram Grid.
  - **UI Context Modals:** Material 3 adaptive dialog cards, scoreboards, and lifetime statistical chart templates.

---

### 4. Planet 04: ImpostorMX (Social Deduction Lounge)
* **Core Technology:** Flutter, Knit Wi-Fi Aware & Bluetooth LE Mesh Sockets
* **Description:** Off-grid, serverless 4–8 player social deduction game with cryptographic role assignments and peer voting.
* **Graphical Asset Requirements:**
  - **Role Badges & Cards (512x512 PNG):**
    - Crewmate, Impostor, Ghost, and Inspector role artwork.
  - **In-Game Action UI:**
    - Emergency Meeting Button (Red Voxel Graphic & Press State).
    - Voting Screen UI Cards with player handles, avatars, and skip-vote button.
    - Sabotage & Task Progress Indicators.
  - **Victory/Defeat Splash Banners:** Full-screen vector banners ("Crewmate Victory", "Impostor Sabotage").

---

### 5. Planet 05: Asteroids Revenge (Arcade Shooter)
* **Core Technology:** Phaser 3 WebGL Canvas, TypeScript (`digitsensitive`)
* **Description:** High-score based endless space arcade shooter broadcasting game states over local GossipSub mesh channels.
* **Graphical Asset Requirements:**
  - **2D Sprite Sheets (`.png`):**
    - Player Ship (`ship_idle.png`, `ship_thruster_anim.png`).
    - Asteroid Variants: Small, Medium, Large, and Fragmented Rock Vector Sprites.
    - Projectile Sprites: Laser Bullets, Plasma Bombs, Particle Expansions.
  - **Background & WebGL Starfields:** Seamless tiled 1080p deep-space nebulae and starfield textures.
  - **Marquee High-Score Frame:** Arcade HUD overlay with vintage retro fonts and local leaderboard cards.

---

### 6. Planet 06: The Omni Puzzle Vault
* **Core Technology:** Pure Flutter Widget Suite
* **Description:** 300+ minimalist logic, sliding tile, maze, and pattern-matching puzzle games.
* **Graphical Asset Requirements:**
  - **Minimalist Tile Textures:** Clean geometric tile sets (Nordic Minimalist, Cyber Neon, Dark Slate).
  - **Milestone Trophy Rings:** High-resolution 3D/2D badge graphics (e.g., *"Mind Bender Ring"*, *"Vault Breaker Badge"*).
  - **Puzzle Grid UI:** Adaptive layout frames for 3x3, 4x4, 5x5, and hex grids.

---

### 7. Planet 07: Spades Card Lounge & Off-Grid Table Arena
* **Core Technology:** Flutter / Phaser 2D, `spadille` Functional Rule Engine
* **Description:** Serverless 4-player Spades card game with shared deck shuffling, Markov AI bot seat filling, and partnership scoring.
* **Graphical Asset Requirements:**
  - **52-Card Deck Vector Spritesheets (2D PNG / SVG):**
    - Standard Classic Deck & Cyberpunk Neon Deck variants.
    - Card Back Designs (Celestial Cyan Logo, Obsidian Gold).
  - **Table Felt & Felt Backgrounds:** High-res 4K felt table textures (Emerald Green, Midnight Blue, Charcoal Red).
  - **Bidding & Trick Modals:**
    - Bidding Dial / Selector Wheel (1–13 Bids, Nil, Blind Nil).
    - Trick Winner Animation & Particle Scoreboard.
    - *"Spades Ace Ring"* Trophy Graphic.

---

### 8. Idle World Plaza Skilling & LPE Avatar Store
* **Core Technology:** Flutter, HashLips Art Engine, Continuity-Engine
* **Description:** Offline crafting, skilling, and dynamic persona cosmetics marketplace fed by continuous background asset generation.
* **Graphical Asset Requirements:**
  - **2D Transparent Layer Traits (512x512 PNG with `#rarity` naming):**
    - `/layers/Background/`: `neon_grid#40.png`, `obsidian_void#20.png`.
    - `/layers/BaseBody/`: `human_skin#60.png`, `android_frame#10.png`.
    - `/layers/Torso/`: `jacket_cyber#30.png`, `armor_heavy#15.png`.
    - `/layers/Headwear/`: `helm_visor#20.png`, `cap_retro#50.png`.
    - `/layers/AuraGlow/`: `cyan_eigen_glow#10.png`.
  - **Storefront Banner & Category Icons:**
    - Dynamic rotation banner (1080x400 PNG).
    - Category Filter Icons: Crafting, Mining, Weapons, Armor, Rings, Pets.

---

### 9. Phaser 2D/3D Real-Time Arcade Marquee & Spectator Canvas
* **Core Technology:** Phaser 3, Rex UI WebGL Shaders, `enable3d` Isometric Physics
* **Description:** Real-time spectator visualizer, EigenTrust aura glows, and isometric 3D arcade floor.
* **Graphical Asset Requirements:**
  - **Arcade Cabinet 3D Models (`.glb`):**
    - Arcade Cabinet Shells for 9x9, Asteroids, Spades, and Social Deduction.
  - **Aura Shaders (`.fmat` / Rex WebGL Pipelines):**
    - Celestial Cyan (`#00FFCC`) high-reputation aura ring.
    - Crimson Warning (`#FF3366`) low-reputation / quarantined aura.
  - **Spectator UI Modals:**
    - Drop-In, Spectate, and Tip OmniCredits floating buttons.

---

## 🛠️ Developer Action Plan & Drop-Zone Workflow

To auto-import and index assets for any planet, place your raw exported graphics into the central drop-zone:

```bash
# Directory path for dropping raw assets:
/workspace/scratch/omni_assets_workspace/raw_imports/

# Run the universal classifier & auto-import tool:
python3 omni_asset_auto_import_tool.py
```

All imported files will be automatically classified, placed into their designated planet folders, and indexed in `pubspec_assets_snippet.yaml` and `asset_manifest.json`.
