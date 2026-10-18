# 🖥️ The Omniverse & The KickBack — Desktop Developer & Tester Guide

Welcome to **The Omniverse Desktop Control Panel & Node Suite**. On desktop systems (Windows, macOS, Linux), the platform operates as a **dual-architecture node**: a high-capacity background P2P relay daemon and local storage engine paired with a Material 3 desktop control panel GUI.

---

## 🚀 Quickstart: 1-Click Launch

We provide unified, 1-click launch scripts that start both the background **P2P Relay Daemon** and the **Desktop Control Panel** in a single step.

### **Windows**
Double-click `run_desktop.bat` or run in Command Prompt / PowerShell:
```cmd
python run_desktop.py
```

### **macOS / Linux**
Run in terminal:
```bash
chmod +x run_desktop.sh
./run_desktop.sh
```

---

## 🛠️ System Components & Architecture

### **1. P2P Mesh Relay Daemon (`backend/localsend_chunk_receiver.py` & daemon scripts)**
* **Loopback IPC Gateway:** Binds to `127.0.0.1:9200` for zero-latency local communication with desktop and mobile UIs.
* **LocalSend REST Server:** Ingests incoming P2P chunk transfers on port `53317`.
* **CAS Storage & Quarantine:** Validates incoming `.omnimod` asset packages and Merkle DAG records.

### **2. Desktop Control Panel GUI (`omni_flet_desktop_control_panel.py`)**
* Built with **Flet (Python Material 3)** for instant desktop execution without heavy compilation.
* Displays live network topology, connected peers, bandwidth throughput, and quarantine file inspection.

---

## 💻 Native Flutter Desktop App (Windows / macOS / Linux)

If you prefer to run the **native compiled Flutter desktop application**:

### **Step 1: Generate Standalone Workspace**
Run the workspace generator script from the repository root:
```bash
python3 build_core_engines_standalone_app-v4.py
```

### **Step 2: Launch Native Flutter App**

#### **Windows:**
```cmd
cd omni_core_engines_standalone\mobile
flutter run -d windows
```
*(Note: If Windows desktop support is missing in local Flutter SDK cache, run `flutter create --platforms=windows .` inside `omni_core_engines_standalone\mobile` prior to running).*

#### **macOS:**
```bash
cd omni_core_engines_standalone/mobile
flutter run -d macos
```

#### **Linux:**
```bash
cd omni_core_engines_standalone/mobile
flutter run -d linux
```

---

## 🔧 Troubleshooting & Port Reference

| Port / Path | Purpose | Recommended Action if Blocked |
| :--- | :--- | :--- |
| `127.0.0.1:9200` | Local IPC Gateway | Ensure no secondary daemon process is occupying port 9200. |
| `0.0.0.0:53317` | LocalSend REST P2P Receiver | Allow port 53317 through Windows Defender / macOS Firewall for LAN P2P transfers. |
| `/workspace/scratch/quarantine/` | Asset Quarantine Buffer | Temporary staging location where incoming `.omnimod` files undergo cryptographic verification. |

---

*For security reports or architecture specifications, refer to `docs/SECURITY.md` and `docs/termux_and_desktop_cheatsheet.md`.*
