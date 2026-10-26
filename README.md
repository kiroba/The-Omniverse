# The Omniverse & The KickBack Architecture Standard [v8.5.0]

## Overview
The Omniverse is a serverless, local-first P2P mesh network and decentralized application framework. It enables peer-to-peer messaging, asset synchronization, offline-first Merkle event logs, and off-chain reward ledgers without central servers or mandatory cloud infrastructure.

---

## Active System Architecture & Microservices

| Service / Subsystem | Binding Host | Port | Role & Implementation Status |
| :--- | :--- | :--- | :--- |
| **Node Telemetry API** | `127.0.0.1` | `:9100` | Node health stats, active peer IP table, uptime (`omni_live_daemon_server.py`) |
| **Local IPC Event Gateway** | `127.0.0.1` | `:5000` | Local append-only Merkle DAG gateway (`/api/events/append`) |
| **P2P Network Sync Receiver** | `0.0.0.0` | `:5005` | Inter-device network sync for signed envelopes (`/p2p/sync`) |
| **Crypto & Payments Gateway** | `127.0.0.1` | `:5001` | HMAC checkout intents, 64-bit integer Satoshis, verified webhooks |
| **LPE Trait Normalizer** | `127.0.0.1` | `:5002` | Avatar trait schema normalization, hex color validation, Z-layers |
| **IPFS CAS Storage Engine** | `127.0.0.1` | `:5003` | Content-addressed storage, 256 KB chunking, encrypted CIDs (`bafy...`) |
| **BFT Patch Consensus Engine** | `127.0.0.1` | `:5004` | Multi-desktop relay BFT voting (>66.7% consensus threshold) |
| **UDP Subnet Discovery** | `0.0.0.0` | `:9101` | Local Wi-Fi beacon broadcaster/listener (advertises port 5005) |

---

## Key Hardened Features [v8.5.0]

1. **P2P Sync Receiver on Port 5005 (`0.0.0.0:5005`):**
   - Receives signed P2P event envelopes from remote nodes.
   - Enforces deduplication across in-memory cache and SQLite WAL DB.
   - Skips relaying back to `origin_peer` IP to eliminate feedback loops.

2. **Re-Verified Hash Integrity & Exact Timestamps:**
   - Canonical event hashes are computed over `(action, author_pubkey, payload, previous_hash, timestamp)` using compact JSON formatting (`sort_keys=True, separators=(',', ':')`).
   - Receiving nodes recompute the canonical SHA-256 ID; tampered or mismatched hashes are rejected with HTTP 400.

3. **Secure Financial Ledger (`omni_crypto_payment_gateway.py`):**
   - Bound strictly to `127.0.0.1:5001`.
   - Payment amounts are strictly positive 64-bit integers (`amount_cents > 0`).
   - Settlement requires Webhook Secret verification (`X-Webhook-Secret`).

4. **Encrypted CAS Storage Engine (`omni_ipfs_cas_streaming_engine.py`):**
   - Chunks binary assets into 256 KB slices and computes `bafy...` multihashes.
   - Enforces LRU cache quotas on mobile edge devices.

---

## File Inventory & Workspace Outbox

All source files are included directly in the delivery outbox:

* `omni_live_daemon_server.py` — Hardened P2P Daemon & Merkle DAG Gateway
* `omni_crypto_payment_gateway.py` — Crypto & Payments Microservice
* `lpe_trait_normalizer.py` — Avatar Trait Normalizer Microservice
* `omni_ipfs_cas_streaming_engine.py` — On-Device IPFS CAS Engine
* `omni_bft_patch_consensus_engine.py` — BFT Patch Consensus Engine
* `omnimind_agent_telemetry_engine.py` — Autonomous Edge Agent Emitter
* `omni_telemetry_monitor.py` — Real-Time Terminal Telemetry Dashboard
* `omnicast_video_chat_ui.dart` — OmniCast Flutter P2P Video UI
* `test_v85_mesh.py` — Comprehensive System & Security Integration Test Suite
