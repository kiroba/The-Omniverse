# Dev Blog & Architecture Changelog (v29.0)

**Date:** September 25, 2026  
**Scope:** Architectural Clarification & Formal Legacy Deprecation Standard  
**Target Application:** The KickBack (`com.kickback`)  

---

## Architectural Clarification: Legacy Concept Deprecation & Successor Standard

### 1. Absolute Deprecation of LiVid & ViVid
* **Historical Context Only:** `LiVid` and `ViVid` are strictly recognized as retired, legacy proof-of-concept prototypes from early R&D.
* **Zero Standalone APK Policy:** No standalone APK applications exist for LiVid or ViVid, and **none ever will**. Any historical references to parallel APKs (`com.mobile`, `com.vivid`) are completely removed from active build pipelines.

### 2. The KickBack as Sole Mobile Successor
* **Single Active Application:** **The KickBack** (`com.kickback`) is the **sole active mobile application and APK** built upon the lessons learned from early legacy research.
* **Unified Tech Stack:** All active P2P mesh networking, local SQLite WAL Merkle DAG event logging, Ed25519 Stargate attestation, and Flutter UI layers are engineered exclusively for **The KickBack**.

### 3. Unified Token & Identity Scope
* **OmniToken:** All legacy token references (`LiVidToken`) are permanently consolidated under **OmniToken** on the underlying off-chain ledger / Polygon relay layer.
* **Unified Stargate Scope:** Admin and user scopes are consolidated under the single KickBack / Omniverse ecosystem identity.

---

## Updated Release Pipeline
* **Target Package:** `com.kickback`
* **Target UI File:** `mobile/lib/omni_hub_gateway_launcher_ui.dart`
* **Release Artifact:** `app-release.apk` (The KickBack Closed Alpha)
