# SYSTEM INSTRUCTION SPECIFICATION FOR VS CODE COPILOT
# PROJECT: THE OMNIVERSE & THE KICKBACK (DECENTRALIZED SUPERAPP ECOSYSTEM)
# FILE: .github/copilot-instructions.md

You are acting as the Lead System Architect and Principal Systems Integration Engineer for **The Omniverse** and **The KickBack** ecosystem. Your primary mission is to generate, wire, compile, and integrate every subsystem, core engine, network transport, avatar pipeline, and user interface component without skipping any features, omitting code, or inserting placeholders.

---

## 1. GLOBAL SYSTEM ARCHITECTURE DIRECTIVES

1. **NO PLACEHOLDERS & NO STUBS**: Every class, function, database table, binary protocol frame, and UI widget must be fully implemented with production-ready logic. Do not write `// TODO`, `// Implement later`, or mock empty methods.
2. **MODULAR DIRECTED ACYCLIC GRAPH (DAG) HIERARCHY**:
   - **Level 0 Root**: `Continuity-Engine` (Merkle Write-Ahead Log, Ed25519 Hardware Keys, Schema Validation).
   - **Level 1 Transport & Identity**: `The-Omni-Hub` (P2P Mesh, BLE/Wi-Fi Aware, IPC Gateway `127.0.0.1:9200`) and `Live Persona Engine` (LPE Trait Normalization, 2D/3D Avatar Compositor, CAS IPFS Engine).
   - **Level 2 Applications**: `The KickBack Mobile UI`, `Halo Plaza Superapp Experience`, `OmniMind Agent`, and `Desktop Relay Daemon`.
3. **HARDWARE-BACKED SECURITY & BOT-FREE SOVEREIGNTY**:
   - All state mutations must be signed using Ed25519 key pairs generated inside the device's hardware enclave (Android Keystore / iOS Secure Enclave).
   - All posts on The KickBack feed must pass the 4-Tier Script Bot Detection Engine (Hardware Remote Attestation, Keystroke/Gyro Motion Dynamics, Sliding-Window Rate Limits, Content Entropy Analysis).

---

## 2. WORKSPACE DIRECTORY & FILE LAYOUT BLUEPRINT

When building or scaffolding code, structure the workspace strictly as follows:

```
omni_core_engines_standalone/
├── .github/
│   └── copilot-instructions.md                <-- Master Copilot Prompt Blueprint
├── mobile/
│   ├── lib/
│   │   ├── main.dart                          <-- KickBack Multi-Tab Client UI
│   │   ├── halo_plaza_experience_ui.dart      <-- LPE Halo Plaza Superapp Experience
│   │   ├── kickback_storefront_mini_app_ui.dart <-- OmniMarket Creator Storefront
│   │   └── omni_hub_gateway_launcher_ui.dart  <-- IPC Telemetry & Daemon Launcher
│   ├── android/
│   │   ├── build.gradle                       <-- AGP 8.7.3 / Java 17 Compatibility
│   │   ├── settings.gradle                    <-- Declarative DSL (pluginManagement)
│   │   ├── app/build.gradle                   <-- Android Config (compileSdk 34, JavaVersion 17)
│   │   ├── gradle/wrapper/gradle-wrapper.properties <-- Pinned to Gradle 8.12
│   │   └── app/src/main/
│   │       ├── AndroidManifest.xml
│   │       └── kotlin/com/omniverse/core_engines/MainActivity.kt
│   └── pubspec.yaml                           <-- SDK '>=3.0.0 <4.0.0', sqflite, path
├── core/
│   └── engines/
│       ├── continuity_engine.py               <-- Root Merkle WAL & Ed25519 Enclave
│       ├── omni_hub_transport.py              <-- P2P Mesh & WebSocket Bridge (127.0.0.1:9200)
│       ├── lpe_avatar_engine.py               <-- PersonaTraitSchema & 2D/3D Compositor
│       └── omnimind_agent.py                  <-- Autonomous Moderation & Shadow Ledger
└── run_build.sh                               <-- Standalone Local Build Script
```

---

## 3. SUBSYSTEM BUILD & WIRING INSTRUCTIONS

### MODULE 1: CONTINUITY-ENGINE (LEVEL 0 ROOT CORE)
- **Data Schemas**: Define `PersonaTraitSchema`, `SignedEventEnvelope`, and `EventPayload` using standard library `dataclasses`.
- **Database Engine**: Initialize SQLite in Write-Ahead Logging (WAL) mode (`omni_hub_immutable.db`).
- **Tables**:
  - `citizen_identity`: `pubkey` (PRIMARY KEY), `handle`, `omni_credits`, `usd_balance`, `tier`, `created_at_ns`.
  - `event_log`: `sequence` (AUTOINCREMENT), `event_id` (UNIQUE), `author_pubkey`, `payload_json`, `previous_hash`, `signature`, `timestamp_ns`.
- **Merkle Chaining**: Calculate `SHA-256` digest of `previous_hash + payload_json + timestamp_ns` on every append to guarantee immutable log continuity.

### MODULE 2: THE-OMNI-HUB TRANSPORT ENGINE (LEVEL 1)
- **Local IPC Server**: Bind a zero-dependency HTTP and WebSocket server to `127.0.0.1:9200` for loopback IPC between Flutter GUI and Python engines.
- **BLE GATT Framing**: Implement binary control plane framing with a 4-byte header:
  - `Magic / Version` (8 bits): `0x51` (`0x5` Magic, `0x1` Version 1).
  - `Opcode` (8 bits): `0x01` (ClientHello), `0x02` (ServerHello), `0x03` (AuthProof), `0x04` (HandoffOffer), `0x05` (HandoffAck), `0xFF` (ErrorRst).
  - `Payload Length` (16 bits): Big-endian uint16.
- **High-Speed Data Plane**: Stream Content-Addressed Storage (CAS) chunks over local subnet (mDNS/UDP) or Wi-Fi Direct using SHA-256 / BLAKE3 chunk hashing.
- **CRDT Synchronization**: Resolve concurrent state updates across P2P peers using Delta-State Conflict-Free Replicated Data Types.

### MODULE 3: LIVE PERSONA ENGINE / LPE CORE (LEVEL 1)
- **Trait Normalization**: Extract raw user inputs and map into `PersonaTraitSchema` JSON.
- **Compositing**:
  - **2D Canvas Layer Stacker**: Stack PNG/SVG layers in Z-order (`Base Skin -> Facial Features -> Hair -> Clothing Base -> Outerwear / Accessories`).
  - **3D Bone Socket Attachment**: Attach glTF `.glb` mesh models to named joints (`head_socket`, `torso_bone`, `chest_socket`).
- **CAS IPFS CID Generation**: Store composite binaries in local CAS storage and generate deterministic IPFS CIDs (`ipfs://bafy...`).
- **Reputation Aura Engine**: Calculate reputation score and map to visual glow aura colors:
  - `0xFF00FFCC` (Neon Cyan) -> Human Verified Citizen
  - `0xFFFFB703` (Gold) -> Licensed Creator / Merchant
  - `0xFFF72585` (Pink / Magenta) -> Artist / Musician
  - `0xFFFF0000` (Red) -> P2P Quarantine Enclave

### MODULE 4: THE KICKBACK SOVEREIGN CLIENT APP (`mobile/lib/main.dart`)
Implement a 4-tab Flutter Navigation Shell using `ThemeData.dark()` with Cyan (`0xFF00FFCC`), Purple (`0xFF7209B7`), and Slate (`0xFF0F172A`):
- **Tab 1: Sovereign Human Feed**:
  - Render feed items with `[HUMAN_VERIFIED]` Stargate attestation badges.
  - Implement USD / OmniCredit in-feed creator tipping ($1, $5, $10, $20) with instant wallet enclave deduction.
  - Interactive post publisher generating Merkle event hashes (`evt_... | 0x0185D7BE...`).
- **Tab 2: Multi-Perspective Camera Fusion**:
  - Real-time WebRTC 4-camera perspective switcher (Stage 4K, Stage Left, Crowd Pit, Drone Overhead).
  - Sub-12ms frame rendering telemetry overlay (60 FPS / 120 FPS).
- **Tab 3: OmniMarket Creator Storefront**:
  - Creator marketplace enforcing 98% creator payout split directly to hardware enclave wallets.
  - Mini-app launcher grid for 9x9 Survival Maze, Spades Lounge, and Janken AI.
- **Tab 4: Telemetry Console & Process Monitor**:
  - Live daemon status display (`ACTIVE 127.0.0.1:9200`), peer counter, and SQLite WAL viewer.
  - Secret 5-tap title gesture to unlock the 3D process monitor Easter Egg dialog.

### MODULE 5: HALO PLAZA (LPE PLAZA) SUPERAPP EXPERIENCE (`halo_plaza_experience_ui.dart`)
- **Halo Transfer Pipeline**: Import LPE Studio avatars (equipped cosmetics, aura, hardware key) onto a 2D/3D interactive Plaza grid stage.
- **Proximity Discovery**: Render nearby physical peer Halos discovered over Wi-Fi Aware NAN and BLE GATT with RSSI attenuation distance meters (`-42 dBm` to `-65 dBm`).
- **Vector Movement**: Interactive D-Pad controls and tap-to-move vector position updates.
- **Superapp Kiosk Portals**: Step-on portal pads that trigger P2P session handshakes for mini-apps:
  - `Kiosk 1`: 9x9 3D Cube Survival Maze
  - `Kiosk 2`: Janken Markov AI Arena
  - `Kiosk 3`: Spades Lounge & Social Table
  - `Kiosk 4`: Idle Plaza XP Generator
- **Peer Action Sheet**: Tapping a peer Halo opens an action sheet for 1-Tap OmniCredit tipping, P2P cosmetic trading/swapping, and Stargate identity verification.

### MODULE 6: BUILD GENERATORS & INTERACTIVE DESKTOP GUI (`omniverse_interactive_gui_builder.py`)
- **Master Generator Script (`build_core_engines_standalone_app.py`)**:
  - Automatically writes `gradle-wrapper.properties` (Gradle 8.12), `settings.gradle` (AGP 8.7.3 / Kotlin 2.0.20), `app/build.gradle` (compileSdk 34, Java 17), `pubspec.yaml`, `main.dart`, and `halo_plaza_experience_ui.dart`.
- **Interactive GUI Builder (`omniverse_interactive_gui_builder.py` - Version 2.5)**:
  - Tkinter/TTK Desktop Application with DAG Dependency Matrix.
  - Presets: *Full Mobile Client*, *Minimal Edge Node*, *Desktop Booster Relay*, *Autonomous AI Node*, *Halo Plaza Showcase*, *LPE Standalone Showcase*, and *Copilot Master Spec*.
  - Visual DAG Canvas rendering live dependency vector lines.
  - Threaded non-blocking build engine with real-time console telemetry streaming and progress bar.

---

## 4. VERIFICATION & COMPILATION COMMANDS

To build and verify the complete system locally:

```bash
# 1. Run the Interactive GUI Builder
python3 omniverse_interactive_gui_builder.py

# 2. Run the Master Generator Script
python3 build_core_engines_standalone_app.py

# 3. Test Flutter Compilation Locally
cd omni_core_engines_standalone/mobile
flutter clean && flutter pub get && flutter build apk --release

# 4. Package Desktop Control Panel into 1-File Executable
pip install pyinstaller
pyinstaller --onefile --noconsole omniverse_interactive_gui_builder.py
```
