# The KickBack & The Omniverse: Complete System Architecture & Feature Specification

## Executive System Architecture Overview
The KickBack is a zero-server, edge-native, decentralized social platform and metaverse client operating as part of The Omniverse ecosystem (`com.kickback` / `com.omniverse.core_engines`). The system eliminates central server infrastructure (AWS/GCP), central databases, and third-party cloud brokers in favor of an **offline-first, device-centric architecture**.

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                            THE KICKBACK DECENTRALIZED STACK                               │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│  1. Presentation & UI Layer                                                               │
│     └── Flutter / Dart (Native ARM64 AOT Compilation, Impeller GPU Canvas)               │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│  2. Identity & Security Layer (Stargate Enclave)                                          │
│     └── Hardware Key Pair (Ed25519 in Keystore/Secure Enclave) + 4-Tier Bot Detection      │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│  3. Local Engine & Storage Layer (Continuity-Engine)                                      │
│     └── Embedded SQLite Write-Ahead Log (WAL) + Local Merkle DAG Event Hash Chain          │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│  4. Transport & Peer Synchronization Layer (The-Omni-Hub)                                 │
│     └── Dual-Radio Mesh (Wi-Fi Aware + BLE) + libp2p GossipSub & Delta-State CRDTs         │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│  5. Live Persona Engine (LPE) & Asset Storage                                             │
│     └── PersonaTraitSchema + 2D/3D Composite Renderer + Local CAS / IPFS Storage           │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Module 1: Stargate Identity & Human-Only Sovereignty

### 1.1 Hardware-Enclave Identity Provisioning
* **Key Generation:** Private key pairs (`Ed25519`) are generated inside the host device's hardware security enclave (Android Keystore / iOS Secure Enclave / TPM 2.0).
* **Non-Exportable Security:** Private keys never leave hardware isolation. All state changes, posts, and transactions are signed inside the enclave via hardware platform channels.
* **Citizen Handle & Key Linking:** Every citizen is identified by an enclave public key hash (`0x...`) and a human handle (`@citizen.xxxx`).

### 1.2 Multi-Tier Script Bot Prevention Engine
The KickBack enforces a **100% Human-Only Feed Policy**, prohibiting AI agents (e.g., OmniMind) or headless scripts from posting to the social feed (with explicit exceptions for system maintenance notices).
* **Tier 1: Hardware Remote Attestation:** Validates device signatures via Apple App Attest / Android Play Integrity API.
* **Tier 2: Keystroke Dynamics & Motion Telemetry:** Analyzes timing variance, composition speed ratio, and accelerometer/gyroscope micro-jitter to distinguish human touch from simulated clicks.
* **Tier 3: Sliding-Window Rate Limiting:** Enforces maximum publication frequency thresholds per public key.
* **Tier 4: Content Entropy & Duplication Analysis:** Analyzes character randomness and cross-network content duplication.

### 1.3 Peer Reputation & Slashing Rules
* **Node Scoring Algorithm:** Peer nodes evaluate incoming relays based on attestation validity and signature verification.
* **Dynamic Slashing & Banning:** Relaying un-attested or bot-flagged posts results in point slashing. Nodes crossing the negative threshold are automatically banned from the P2P GossipSub cluster.

---

## Module 2: Client Application Interface (The KickBack Shell UI)

The KickBack client application (`mobile/lib/main.dart`) is built in Flutter/Dart, featuring a multi-tab interface:

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                            THE KICKBACK FLUTTER APPLICATION UI                            │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                           │
│  [ Top Bar & Identity Drawer ]                                                           │
│  ├── Stargate Hardware Identity Badge (@citizen.a8f9 | 0x8F92A1B4...)                     │
│  ├── P2P Mesh Telemetry (6 Active Wi-Fi Aware & BLE Peer Nodes)                           │
│  └── Hardware Wallet Balance ($142.50 USD / 3,250 OmniCredits)                             │
│                                                                                           │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                           │
│  ┌──────────────────┬──────────────────┬──────────────────┬──────────────────┐            │
│  │  1. HUMAN FEED   │  2. MESH FUSION  │  3. OMNIMARKET   │  4. TELEMETRY    │            │
│  └──────────────────┴──────────────────┴──────────────────┴──────────────────┘            │
│                                                                                           │
│  Tab 1: Sovereign Human Feed                                                              │
│  ├── Bot-Free Post Stream with [HUMAN_VERIFIED] Hardware Attestation Badges.              │
│  ├── Real-Time Merkle DAG Event Hash Attribution (`evt_...` | `0x0185D7BE92C4`).            │
│  ├── Integrated Post Publisher with Local Merkle Hash Generation.                         │
│  └── Direct Creator USD Tipping ($1, $5, $10, $20) & Reaction Overlays.                   │
│                                                                                           │
│  Tab 2: Multi-Perspective Camera Fusion                                                   │
│  ├── Real-Time WebRTC Stream Switcher (Stage 4K, Stage Left, Crowd Pit, Drone Overhead).  │
│  └── Sub-12ms Frame Latency Video Buffer over Local P2P Mesh.                             │
│                                                                                           │
│  Tab 3: OmniMarket Creator Storefront & Mini-App Hub                                      │
│  ├── 98% Direct-to-Enclave Creator Monetization Payout Model.                            │
│  ├── Dynamic 2D/3D Avatar Cosmetics & Equipment Marketplace.                             │
│  └── Integrated Mini-Apps (9x9 Survival Maze, Spades Lounge, Janken AI, Puzzle Vault).    │
│                                                                                           │
│  Tab 4: Core Engine Telemetry & IPC Console                                               │
│  ├── ANSI Process Daemon Telemetry (`127.0.0.1:9200` Loopback & GossipSub Relays).        │
│  └── Secret 5-Tap Developer Easter Egg 3D Raycaster Dialog.                               │
│                                                                                           │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Module 3: Live Persona Engine (LPE Core & Avatars)

### 3.1 Persona Trait Schema Normalization
Raw user data and cosmetic configurations are mapped into a deterministic JSON schema:
```json
{
  "persona_id": "lpe_usr_9021",
  "owner_pubkey": "0x8F92A1B439C0E71D",
  "archetype": "humanoid",
  "skin_tone_hex": "#FFDFC4",
  "eye_color_hex": "#3B2219",
  "equipped_cosmetics": {
    "head_socket": "item_cyber_helmet_v2",
    "torso_bone": "item_tactical_vest",
    "outerwear": "item_neon_jacket"
  }
}
```

### 3.2 Dual Rendering Pipelines
1. **2D Canvas Layer Compositor:** Stacked PNG/SVG transparency rendering in strict Z-index order (`Base Skin → Facial Features → Hair → Base Clothing → Accessories`).
2. **3D Bone Socket Attachment:** Attaches 3D `.glb` mesh models directly to named skeleton joints (`head_socket`, `torso_bone`, `chest_socket`).

### 3.3 Content-Addressed Storage (CAS / IPFS CIDs)
Composite preview renders and 3D binary assets pass through local SHA-256 / BLAKE3 chunking, generating IPFS Content Identifiers (`ipfs://bafy...`) stored in local SQLite stores.

---

## Module 4: Mobile and Desktop Node Bridge Architecture

### 4.1 Asymmetric Division of Labor
* **Mobile Client Nodes (Android/iOS):** Primary identity, UI, hardware key signing, battery-optimized operations.
* **Desktop Relay Nodes (Windows/macOS/Linux):** Standalone background daemon (`omni_core_engines_desktop`), unmetered storage, 24/7 CAS blob caching, STUN/NAT traversal, and WebRTC seeding.

### 4.2 Control Plane: Low-Power BLE 5.0+ GATT Handshake
* **Binary Framing Structure (4-Byte Header):**
  * `Byte 0`: `0x51` (`0x5` Magic Version, `0x1` Version 1).
  * `Byte 1`: Opcode ID (`0x01` ClientHello, `0x02` ServerHello, `0x03` AuthProof, `0x04` HandoffOffer, `0x05` HandoffAck, `0xFF` ErrorRst).
  * `Bytes 2-3`: Big-endian uint16 Payload Length.
* **GATT Characteristics:**
  * `RELAY_CTRL_IN` (`...-1001`): Write Without Response (Client-to-Server).
  * `RELAY_CTRL_OUT` (`...-1002`): Notify (Server-to-Client).
  * `RELAY_INFO` (`...-1003`): Read Node Identity & Capacity.

### 4.3 Data Plane: High-Speed Subnet Streaming
Once BLE authentication completes, streaming transitions to local LAN / mDNS / UDP sockets or Wi-Fi Direct for high-speed chunk synchronization.

---

## Module 5: Storage & Decentralized Synchronization

### 5.1 Local SQLite Write-Ahead Logging (WAL)
Device state is maintained in an embedded SQLite database (`omni_hub_immutable.db`), forming an append-only cryptographic event chain:
```sql
CREATE TABLE IF NOT EXISTS event_log (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    author_pubkey TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    previous_hash TEXT NOT NULL,
    signature TEXT NOT NULL,
    timestamp_ns INTEGER NOT NULL
);
```

### 5.2 Conflict-Free Replicated Data Types (Delta-State CRDTs)
Out-of-order or concurrent event broadcasts received over P2P GossipSub are resolved deterministically across peers without central server locking.

### 5.3 Cryptographic Log Pruning & State Checkpointing
To prevent client storage bloat, historical event logs are periodically collapsed into signed Merkle State Snapshots, purging raw logs while preserving global verification proofs.

---

## Module 6: Build Automation, CI/CD, & Control Panel

### 6.1 Standalone Master Builder (`build_core_engines_standalone_app.py`)
Generates the complete application hierarchy (`omni_core_engines_standalone/`), constructing:
* `mobile/lib/main.dart`: Complete KickBack multi-tab UI.
* `mobile/android/gradle/wrapper/gradle-wrapper.properties`: Pinned to Gradle 8.12.
* `mobile/android/settings.gradle`: AGP `8.3.0` / `8.7.3` and Kotlin `1.9.22`.
* `mobile/android/app/build.gradle`: `JavaVersion.VERSION_17`, compileSdk 34.

### 6.2 Codemagic Automated CI/CD (`codemagic.yaml`)
Runs on `mac_mini_m2` instances, configuring JDK 17 bindings (`flutter config --jdk-dir "$JAVA_HOME"`), decoding release keystores, and building signed `app-release.apk` and `app-release.aab` packages.

### 6.3 Interactive Ecosystem Desktop GUI (`omniverse_interactive_gui_builder.py`)
Provides a visual desktop application featuring:
* **DAG Dependency Enforcement:** Enforces mandatory Level 0 root (`Continuity-Engine`) and auto-resolves prerequisite modules.
* **Visual Topology Canvas:** Real-time rendering of module DAG nodes and vector arrows.
* **1-Click Profile Presets:** Full Mobile Client, Minimal Edge Node, Desktop Booster Relay, and Autonomous AI Node.
* **Threaded Execution:** Non-blocking background generation with real-time log output.
* **Standalone Compilation:** Compilable via PyInstaller (`pyinstaller --onefile --noconsole omniverse_interactive_gui_builder.py`) into a single executable binary (`.exe`).

---

## Verification & Build Checklist
- [x] Hardware Security Enclave (Ed25519) identity generation implemented.
- [x] 4-Tier Script Bot Prevention Engine defined and integrated.
- [x] Multi-tab Flutter application UI (`main.dart`) constructed with Feed, Fusion, Storefront, and Telemetry.
- [x] Live Persona Engine (LPE) trait normalization and dual 2D/3D renderers configured.
- [x] Mobile-to-Desktop BLE GATT control plane and LAN data plane specified.
- [x] Local SQLite WAL event chain and Delta-State CRDT convergence enabled.
- [x] Gradle 8.12 wrapper and JDK 17 build configurations validated.
- [x] Interactive Desktop Control Panel (`omniverse_interactive_gui_builder.py`) deployed.
