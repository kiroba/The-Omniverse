# 📱 Mobile Assembly & Self-Build Guide (v3.0 — Standalone Planet & Zero-Dependency Spec)
## The Omniverse & The KickBack — Mobile Development & File Placement Master Manual

This guide details how to assemble, test, and build **The Omniverse SuperApp**, **The KickBack** (LiFeed ecosystem), and all **Standalone Planet Applications** (such as **9x9** and **ImpostorMX Social Deduction**) directly on a mobile device or cloud environment using standard-library, zero-dependency Python tools and Flutter compilation workflows.

---

## 🛠️ Choose Your Mobile Workflow

| Requirement | **Method 1: Termux + Acode** (100% On-Device) | **Method 2: GitHub Codespaces** (Cloud Mobile IDE) |
| :--- | :--- | :--- |
| **Best For** | Running local P2P nodes, zero-dep Python engines, & offline testing | Compiling Flutter Android APKs & hosting web PWAs |
| **Dependencies** | **0 pip packages required** (Pure Python Standard Library) | Standard Flutter / Dart SDK toolchain |
| **Internet Need** | Works 100% Offline | Requires active cellular/Wi-Fi connection |
| **Battery Impact** | Low | Very Low (Builds run on cloud servers) |
| **Setup Time** | < 1 Minute | 30 Seconds |

---

# 📲 METHOD 1: 100% On-Device Mobile Build (Termux + Acode)

Use this method to run local P2P nodes, test cryptographic Merkle DAGs, execute standalone planet adapters, and edit code locally on your phone without pip or Rust compiler issues.

### **Step 1: Install Mobile Tools**
1. **Termux (Terminal Emulator):** Download and install from [F-Droid Termux Page](https://f-droid.org/en/packages/com.termux/). *(Do not use the Google Play Store version as it is deprecated)*.
2. **Acode (Code Editor):** Download **Acode - code editor** from the Google Play Store or F-Droid for tabbed editing with syntax highlighting.

### **Step 2: Automated 1-Tap Setup Command (v9.0)**
Open **Termux** on your phone, paste the following single command block, and press **Enter**:

```bash
termux-setup-storage && pkg update -y && pkg install -y git python sqlite micro
```

*(When prompted for storage permissions, tap **Allow**).*

> 💡 **Why No `pip install`?** The core system engines have been refactored to use Python's built-in standard libraries (`dataclasses`, `hashlib`, `hmac`, `sqlite3`, `json`, `secrets`). This bypasses Termux Python 3.14 wheel errors, Rust compilation (`maturin`) failures, and disk space limits.

### **Step 3: Connect Acode Editor to Your Project Folder**
1. Open **Acode** on your phone.
2. Open the side menu $\rightarrow$ **Files** $\rightarrow$ **Add Source / Folder**.
3. Select **Storage Access Framework (SAF)**.
4. Choose **Termux** or your project download folder (`~/storage/downloads/The-Omniverse`).
5. You can now visually edit any Python, Dart, or Markdown file in Acode while running commands in Termux!

### **Step 4: Execute & Verify System Engines & Standalone Planets**
Inside Termux, navigate to your project directory and run the master runner, brand refactoring suite, or standalone planet adapter:

```bash
# Navigate to project directory
cd ~/storage/downloads/The-Omniverse

# 1. Run Master Zero-Dependency Verification Suite (Executes all 6 sub-tests)
python3 zero_dep_master_runner.py

# 2. Run Standalone Planet Adapter Engine (Tests 9x9 & KickBack in Standalone vs Hub modes)
python3 standalone_planet_adapter_engine.py --test

# 3. Execute LiFeed Brand Refactoring Suite (Verifies full LiVid -> LiFeed migration)
python3 lifeed_migration_runner.py --dry-run
```

---

# ☁️ METHOD 2: GitHub Codespaces (Fastest Mobile APK Compilation)

Use this method to compile Flutter `.apk` installer files or web PWA bundles without straining your phone's CPU, RAM, or battery.

### **Step 1: Launch Codespaces in Mobile Browser**
1. Open **Google Chrome** or **Brave** on your Android phone.
2. Navigate to your GitHub repository (e.g., `https://github.com/kiroba/The-Omni-Hub`).
3. Tap **Code** (green button) $\rightarrow$ select the **Codespaces** tab $\rightarrow$ tap **Create codespace on main**.

### **Step 2: Turn Codespaces into a Fullscreen Mobile App**
1. While viewing VS Code in Chrome, tap the Chrome **⋮ (Three Dots)** menu at the top right.
2. Select **Add to Home Screen** or **Install App**.
3. A **VS Code** icon will appear on your phone home screen, launching as a fullscreen development environment.

### **Step 3: Compile Standalone Release APKs**
In the Codespaces bottom terminal panel, run:

```bash
# Navigate to the mobile app root
cd mobile

# Compile The KickBack Standalone APK
flutter build apk --release --target=lib/omni_hub_gateway_launcher_ui.dart
```

Once compilation completes, right-click (or long-press) `build/app/outputs/flutter-apk/app-release.apk` in the file tree and select **Download** to install it directly on your phone!

---

# 📂 Repository File Hierarchy Tree (v3.0 Specification)

Below is the updated file directory layout showing where every zero-dependency engine script, standalone planet adapter, Flutter UI component, configuration file, and third-party attribution document belongs in your project root:

```text
The-Omniverse/
├── core/
│   └── engines/
│       ├── zero_dep_master_runner.py                # Master 6-in-1 verification suite
│       ├── standalone_planet_adapter_engine.py      # Standalone vs Hub planet execution adapter
│       ├── lifeed_migration_runner.py               # Case-preserving LiVid -> LiFeed refactor script
│       ├── zero_dep_mainnet_cutover_suite.py        # Genesis cutover, SQLite WAL Merkle log
│       ├── zero_dep_role_entitlement_engine.py      # Day 1 baseline & commercial role injections
│       ├── zero_dep_p2p_milestone_consensus_engine.py # P2P median swarm consensus & feature unlocks
│       ├── zero_dep_websocket_pubsub_bridge.py      # Real-time WebSocket pub/sub live frame signing
│       ├── zero_dep_p2p_bootnode_cluster.py         # Cellular CGNAT traversal & bootnode relay
│       ├── zero_dep_continuity_social_import_engine.py # Blind SHA-256 friend matching & fanbase
│       ├── lpe_idle_plaza_engine.py                 # Live Persona Engine (LPE) plaza & Markov NPC simulation
│       ├── lpe_p2p_jail_quarantine_engine.py        # Quarantined node parole & reputation tracking
│       ├── lpe_reputation_aura_engine.py            # Peer aura calculation & slashing rules
│       ├── spatial_anchor_engine.py                 # Zero-trust camera/LiDAR AR anchor matching
│       ├── time_vault_engine.py                     # Shamir Secret Sharing time-vault release
│       ├── branching_story_consensus_engine.py      # WebRTC live interactive stream voting
│       ├── kickback_gift_and_credit_engine.py       # Gift accounting & 2% platform fee split
│       ├── kickback_payout_and_anti_fraud_engine.py  # Creator payout calculation & fraud guards
│       ├── hybrid_storage_engine.py                 # RocksDB hot cache + SQLite cold storage
│       ├── disaster_recovery_validator.py           # Snapshot restoration & DAG validation
│       └── public_accountability_engine.py          # Public audit logs & transparency reports
│
├── mobile/
│   └── lib/
│       ├── continuum_ui_templates_staging-v2.dart   # Zero-dependency FlutterScreens UI staging templates
│       ├── kickback_wallet_and_store_ui.dart        # Storefront, wallet balance & payment UI
│       ├── kickback_creator_studio_ui.dart          # Creator dashboard & stream control panel
│       ├── kickback_storefront_mini_app_ui.dart      # Local eatery / business storefront UI
│       ├── omni_hub_gateway_launcher_ui.dart        # P2P node status & gateway launcher UI
│       └── flutter_live_stream_reaction_overlay.dart # Live stream 3D overlay animations & floating reaction UI
│
├── web/
│   ├── kickback_pwa_manifest.json                   # Progressive Web App manifest
│   └── kickback_pwa_service_worker.js               # Offline caching & PWA service worker
│
├── config/
│   ├── p2p_seed_nodes.json                          # Global bootnode multiaddrs & region tags
│   └── kickback_tier_payment_config.py              # Subscription tier pricing & role mapping
│
└── docs/
    ├── dev_blog_changelog-v30.md                    # Master Devlog v30.0 (Standalone Planets & LiFeed)
    ├── mobile_assembly_and_build_guide-v3.md        # This master build & placement guide
    ├── THIRD-PARTY-NOTICES.md                       # Apache 2.0 & MIT open-source legal attribution
    ├── PRIVACY_POLICY_AND_TERMS.md                  # Privacy policy and terms of service
    ├── launch_release_notes-v2.md                   # Release notes for Genesis Swarm & Standalone Planets
    ├── README.md                                    # Project overview
    └── SECURITY.md                                  # 5-Layer zero-trust security specification
```

---

# 🧩 Assembly & Deployment Checklist

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    SELF-BUILD & ASSEMBLY SYSTEM FLOWCHART                               │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Setup Environment  ──► Run `pkg install git python sqlite` in Termux.                 │
│ 2. Test Core Engines  ──► Run `python3 zero_dep_master_runner.py` (0 pip dependencies). │
│ 3. Test Standalone    ──► Run `python3 standalone_planet_adapter_engine.py --test`.      │
│ 4. Build App Binary   ──► Run `flutter build apk --release` in GitHub Codespaces.       │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Troubleshooting Quick Reference

* **`No space left on device` or `maturin` errors:** Do not run `pip install`. Use the `zero_dep_*.py` scripts which run on Python's built-in standard library without compiling Rust/C extensions.
* **Storage Permission Error in Termux:** Run `termux-setup-storage` and tap **Allow** on the Android system prompt.
* **Acode Directory Access:** Use Storage Access Framework (SAF) when adding source folders in Acode to grant read/write access to Termux folders.
