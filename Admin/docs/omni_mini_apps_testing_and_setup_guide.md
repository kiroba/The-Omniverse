# 🛠️ **The Omniverse & The-Omni-Hub — Standalone Mini-Apps Setup & Testing Guide**

> **Version:** `v1.0.0-testing-harness`  
> **Architecture:** Modular Standalone Planet & Mini-App Isolate Standard  
> **Runtime Target:** Android (Termux / Standalone APKs), Desktop Studio, & Local Loopback Sockets (`127.0.0.1:9200–9208`)  
> **Security Standard:** POSIX Hardened, HMAC Bearer Auth, SQLite WAL DAG Logging  

---

## 🌟 **1. Executive Architecture Overview**

To ensure rapid, zero-friction testing for a **solo developer + AI co-pilot**, every planet and game subsystem in **The Omniverse** is engineered as an **isolated, standalone mini-app**. 

Each mini-app can be built, executed, and debugged independently on local loopback ports without requiring central cloud servers, external API keys, or complex app store compilation pipelines. When running in production, **`standalone_planet_adapter_engine.py`** seamlessly bridges all mini-apps into **The-Omni-Hub** gateway superapp.

---

## 📊 **2. Mini-App Architecture & Port Allocation Matrix**

```text
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                    STANDALONE MINI-APP TEST SUITE MATRIX                                  │
├───────────────────┬───────────────────┬──────────────────────┬────────────────────────────┤
│ Mini-App Identifier│ Technology Stack  │ Local Loopback Port  │ Core Focus & System Role   │
├───────────────────┼───────────────────┼──────────────────────┼────────────────────────────┤
│ **1. Planet 02**  │ Unity 6000 / URP  │ `127.0.0.1:9202`     │ 3D Cube Survival Maze &    │
│    (`9x9`)        │ & FlutterPS Math  │                      │ Raycast FPS Camera Engine  │
├───────────────────┼───────────────────┼──────────────────────┼────────────────────────────┤
│ **2. Planet 03**  │ Python / Pure Dart│ `127.0.0.1:9203`     │ Adaptive Markov Chain AI   │
│    (`Janken AI`)  │ Markov Matrix     │                      │ for Builder & Info NPCs    │
├───────────────────┼───────────────────┼──────────────────────┼────────────────────────────┤
│ **3. Planet 04**  │ Flutter / Knit    │ `127.0.0.1:9204`     │ Rebranded Social Deduction │
│    (`ImpostorMX`) │ Wi-Fi/BLE Mesh    │                      │ & Off-Grid Voting Engine   │
├───────────────────┼───────────────────┼──────────────────────┼────────────────────────────┤
│ **4. Planet 05**  │ Phaser 3 WebGL /  │ `127.0.0.1:9205`     │ Endless Arcade Shooter &   │
│    (`Asteroids`)  │ Canvas 2D         │                      │ GossipSub High-Scores      │
├───────────────────┼───────────────────┼──────────────────────┼────────────────────────────┤
│ **5. Planet 06**  │ Pure Flutter      │ `127.0.0.1:9206`     │ 300+ Minimalist Puzzle     │
│    (`Puzzle Vault`)│ CustomPainters   │                      │ Modules & Ring Challenges  │
├───────────────────┼───────────────────┼──────────────────────┼────────────────────────────┤
│ **6. Planet 07**  │ TypeScript / JS   │ `127.0.0.1:9207`     │ 4-Player Spades Logic,     │
│    (`Spades`)     │ `spadille` Engine │                      │ Shared Deck, & AI Fillers  │
├───────────────────┼───────────────────┼──────────────────────┼────────────────────────────┤
│ **7. Idle Plaza** │ Python / SQLite   │ `127.0.0.1:9208`     │ Idle Skilling & Crafting   │
│    (`IdleFantasy`)│ Merkle Deltas     │                      │ Offline XP Progression     │
├───────────────────┼───────────────────┼──────────────────────┼────────────────────────────┤
│ **8. Marquee**    │ Phaser 3 / TypeScript│ `127.0.0.1:9200`    │ Real-Time 2D/3D Spectator  │
│    (`Arcade Canvas`)│ `rex-notes` / `enable3d`│                 │ Arcade Marquee Visualizer  │
└───────────────────┴───────────────────┴──────────────────────┴────────────────────────────┘
```

---

## 🚀 **3. Individual Mini-App Setup & Testing Instructions**

### 🎮 **Mini-App 1: Planet 02 — `9x9` 3D Cube Survival Maze**
* **Source Repositories:** `hactikgamesstudio/9x9`, `msant77/FlutterPS`, `bdero/flutter_scene`
* **Setup & Testing:**
  1. Boot as standalone executable or Flutter widget:
     ```bash
     python3 core/engines/standalone_planet_adapter_engine.py --planet=planet_02_9x9 --port=9202
     ```
  2. The unit test verifies 3D raycast vector transformations for pitch/yaw touch camera controls and 9x9x9 room wall collision boundaries.
  3. Verify that exiting room `(4,4,4)` generates a signed Merkle event envelope in `omni_hub_immutable.db`.

---

### 🤖 **Mini-App 2: Planet 03 — `Janken` Markov Chain AI Engine**
* **Source Repository:** `attenomy/janken`
* **Setup & Testing:**
  1. Test the pure Python/Dart Markov probability matrix:
     ```bash
     python3 -c "from omni_mini_app_harness_suite import OmniMiniAppHarness; h = OmniMiniAppHarness(); h.test_planet_03_janken_markov()"
     ```
  2. Evaluates state transitions (e.g., `PLACE_WALL` $\rightarrow$ `PLACE_DOOR` with 65% probability).
  3. Verifies that Builder and Information/Guide Plaza NPCs operate with zero latency without calling external LLMs.

---

### 🕵️ **Mini-App 3: Planet 04 — `ImpostorMX` Off-Grid Social Deduction Mesh**
* **Source Repositories:** `retired64/ImpostorMX`, `getknit/knit`
* **Setup & Testing:**
  1. Launch the off-grid voting test isolate:
     ```bash
     python3 core/engines/standalone_planet_adapter_engine.py --planet=planet_04_social_deduction --port=9204
     ```
  2. Simulates cryptographic seed role assignment (Crewmate vs. Impostor) across 4 local P2P nodes.
  3. Tests peer voting synchronization over **Knit Wi-Fi Aware / Bluetooth LE mesh sockets**.

---

### 🚀 **Mini-App 4: Planet 05 — `Asteroids Revenge` Arcade Shooter**
* **Source Repositories:** `mlm-games/asteroids-revenge`, `phaserjs/phaser`
* **Setup & Testing:**
  1. Open the local Phaser WebGL canvas in Chrome/Termux browser:
     ```bash
     http://127.0.0.1:9200/web/asteroids_arcade_isolate.html
     ```
  2. Test high-score telemetry signing upon wave completion.
  3. Verifies that high scores broadcast over local GossipSub to update nearby peer leaderboards.

---

### 🧩 **Mini-App 5: Planet 06 — `The Omni Puzzle Vault`**
* **Source Repositories:** `sidhant947/Puzzle`, `samarthagarwal/FlutterScreens`
* **Setup & Testing:**
  1. Run the pure Flutter widget test page:
     ```bash
     flutter test test/puzzle_vault_widget_test.dart
     ```
  2. Verifies move-counter logic and optimal solution validation.
  3. Triggers **OmniMind** to award the *"Mind Bender Ring"* upon completing target puzzle tiers.

---

### ♠️ **Mini-App 6: Planet 07 — `Spades Card Lounge`**
* **Source Repositories:** `Metamess/Spades`, `marcoonroad/spadille`
* **Setup & Testing:**
  1. Execute the `spadille` functional rule evaluation engine:
     ```bash
     python3 -c "from omni_mini_app_harness_suite import OmniMiniAppHarness; h = OmniMiniAppHarness(); h.test_planet_07_spades_lounge()"
     ```
  2. Validates trick winner determination (Spades permanent trump), lead-suit enforcement, and partnership scoring.
  3. Confirms that missing human seats are populated by Markov AI bots.

---

### ⚒️ **Mini-App 7: `Idle World Plaza` Skilling Engine**
* **Source Repository:** `tristinbaker/IdleFantasy`
* **Setup & Testing:**
  1. Test offline skilling calculation:
     ```bash
     python3 -c "from omni_mini_app_harness_suite import OmniMiniAppHarness; h = OmniMiniAppHarness(); h.test_idle_plaza_skilling()"
     ```
  2. Calculates offline XP and credit generation using signed timestamp deltas in SQLite.

---

### 🎪 **Mini-App 8: `Phaser 2D/3D Real-Time Arcade Marquee Canvas`**
* **Source Repositories:** `digitsensitive/phaser3-typescript`, `rexrainbow/phaser3-rex-notes`, `enable3d`
* **Setup & Testing:**
  1. Boot the live player marquee spectator visualizer:
     ```bash
     http://127.0.0.1:9200/web/arcade_marquee_visualizer.html
     ```
  2. Renders animated 2D/3D avatar sprites for active players across all 7 planets in real time.
  3. Displays EigenTrust cyan (`#00FFCC`) aura shaders around high-trust avatars.

---

## ⚡ **4. Master Automation Test Runner**

To verify all 8 mini-app isolates in a single command, run the master Python test harness:

```bash
python3 /workspace/scratch/omni_mini_app_harness_suite.py
```

### **Expected Output:**
```json
{
  "total_mini_apps": 8,
  "passed": 8,
  "results": {
    "planet_02_9x9": { "status": "ISOLATE_ONLINE" },
    "planet_03_janken_markov": { "status": "ISOLATE_ONLINE" },
    "planet_04_social_deduction": { "status": "ISOLATE_ONLINE" },
    "planet_05_asteroids": { "status": "ISOLATE_ONLINE" },
    "planet_06_puzzle_vault": { "status": "ISOLATE_ONLINE" },
    "planet_07_spades_lounge": { "status": "ISOLATE_ONLINE" },
    "idle_plaza_skilling": { "status": "ISOLATE_ONLINE" },
    "phaser_arcade_marquee": { "status": "ISOLATE_ONLINE" }
  }
}
```

---

## 🛠️ **5. Step-by-Step Night Testing Workflow**

1. **Terminal 1 (Master Daemon):** Run `python3 omni_structural_hardening_suite.py` to enforce POSIX limits, HMAC auth, and SQLite WAL pragmas.
2. **Terminal 2 (Harness Test):** Run `python3 omni_mini_app_harness_suite.py` to confirm all 8 isolates are functioning cleanly on loopback.
3. **Terminal 3 (UI / Gateway):** Launch **The-Omni-Hub** gateway launcher UI (`omni_hub_gateway_launcher_ui.dart`) or open the Phaser Marquee Canvas to observe real-time player telemetry across all mini-apps!

---

🎉 **You are all set for an exceptionally productive testing session!**
