# Mobile Assembly & Self-Build Guide
## The Omniverse & The KickBack — Step-by-Step Mobile Development Master Manual

This guide makes assembling, testing, and building **The Omniverse SuperApp**, **The KickBack**, and all standalone edge modules as simple as possible directly from an Android phone.

---

## Choose Your Mobile Workflow

| Requirement | **Method 1: Termux + Acode** (100% On-Device) | **Method 2: GitHub Codespaces** (Cloud Mobile IDE) |
| :--- | :--- | :--- |
| **Best For** | Running local P2P nodes, Python engines, & offline testing | Compiling Flutter Android APKs & hosting web PWAs |
| **Internet Need** | Works 100% Offline | Requires active cellular/Wi-Fi connection |
| **Battery Impact** | Low | Very Low (Builds run on cloud servers) |
| **Setup Time** | 2 Minutes | 30 Seconds |

---

# METHOD 1: 100% On-Device Mobile Build (Termux + Acode)

Use this method to run local P2P nodes, test cryptographic Merkle DAGs, execute the milestone consensus engine, and edit code locally on your phone.

### **Step 1: Install Mobile Tools**
1. **Termux (Terminal Emulator):** Download and install from [F-Droid Termux Page](https://f-droid.org/en/packages/com.termux/). *(Do not use Google Play Store version as it is deprecated)*.
2. **Acode (Code Editor):** Download **Acode - code editor** from the Google Play Store or F-Droid for tabbed editing with syntax highlighting.

### **Step 2: Automated 1-Tap Setup Command**
Open **Termux** on your phone, paste the following single command block, and press **Enter**:

```bash
termux-setup-storage && pkg update -y && pkg upgrade -y && pkg install -y git python sqlite openjdk-17 clang make micro && pip install --upgrade pip && pip install pydantic fastapi uvicorn cryptography requests
```

*(When prompted for storage permissions, tap **Allow**).*

### **Step 3: Connect Acode Editor to Your Code Directory**
1. Open **Acode** on your phone.
2. Open the side menu $\rightarrow$ **Files** $\rightarrow$ **Add Source / Folder**.
3. Select **Storage Access Framework (SAF)**.
4. Choose **Termux** or your download folder where your project files reside.
5. You can now visually edit any Python, Dart, or Markdown file in Acode while running commands in Termux!

### **Step 4: Execute & Verify System Engines in Termux**
Inside Termux, navigate to your project directory and run any of the verified system engines:

```bash
# 1. Verify 100% Mainnet Cutover & P2P Bootnode Connectivity
python3 mainnet_cutover_suite.py

# 2. Run the Role Entitlement & Day 1 Module Injection Engine
python3 role_entitlement_and_milestone_engine.py

# 3. Test P2P Milestone Consensus & SuperApp Module Unlocks
python3 p2p_milestone_consensus_engine.py

# 4. Run the Local Live Persona Engine (LPE) Plaza Simulator
python3 lpe_idle_plaza_engine.py
```

---

# METHOD 2: GitHub Codespaces (Fastest Mobile APK & PWA Compilation)

Use this method if you want to compile Flutter `.apk` installer files or web PWA bundles without straining your phone's CPU, RAM, or battery.

### **Step 1: Launch Codespaces in Mobile Browser**
1. Open **Google Chrome** or **Brave** on your Android phone.
2. Navigate to your GitHub repository (e.g., `https://github.com/kiroba/The-Omni-Hub`).
3. Tap **Code** (green button) $\rightarrow$ select the **Codespaces** tab $\rightarrow$ tap **Create codespace on main**.

### **Step 2: Turn Codespaces into a Fullscreen Mobile App**
1. While in Chrome viewing VS Code, tap the Chrome **⋮ (Three Dots)** menu at the top right.
2. Select **Add to Home Screen** or **Install App**.
3. A **VS Code** icon will appear on your phone home screen, launching as a fullscreen, native-feeling development environment.

### **Step 3: Compile the Android APK File**
In the Codespaces bottom terminal panel, run:

```bash
# Navigate to the mobile app root
cd mobile

# Compile the Android APK in debug or release mode
flutter build apk --debug
```

Once compilation completes, right-click (or long-press) `build/app/outputs/flutter-apk/app-debug.apk` in the file tree and select **Download** to install it directly on your phone!

---

# Modular Assembly & Deployment Checklist

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    SELF-BUILD & ASSEMBLY SYSTEM FLOWCHART                               │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Core Engine       ──► Run `mainnet_cutover_suite.py` to verify local Merkle DAG &     │
│                          Ed25519 hardware key signing.                                  │
│ 2. Entitlement Rules ──► `role_entitlement_and_milestone_engine.py` sets Day 1 baseline  │
│                          (KickBack + LPE Plaza) and role-based feature injections.       │
│ 3. P2P Mesh Test     ──► Run local mDNS / GossipSub peer discovery across devices.      │
│ 4. Build Binary      ──► Use Codespaces `flutter build apk` to output downloadable APK. │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting Quick Reference

* **Storage Permission Error in Termux:** Run `termux-setup-storage` and tap **Allow** in the popup.
* **Missing Python Module:** Run `pip install <module_name>` inside Termux.
* **Gradle Build Locks:** Stop background daemons with `./gradlew --stop` before running `flutter build apk`.
