# The Omniverse: Field Cheatsheet

Quick reference guide for running mobile builds and desktop relay nodes.

---

## 1. Mobile Setup (Android via Termux)

### Navigate to Project Folder


### Run Standalone Build


---

## 2. Desktop Relay & Control Panel (Laptop / PC)

### Launch Background Relay Daemon
Runs P2P mesh relay and local IPC gateway at 127.0.0.1:9200:


### Launch Flet Control Panel
Runs visual desktop dashboard:


---

## 3. Off-Grid P2P Mesh Linking

1. Connect phone and laptop to same local Wi-Fi or Hotspot.
2. Launch The KickBack on phone and run_desktop_daemon.py on laptop.
3. Devices auto-discover via BLE/mDNS and sync off-grid.
