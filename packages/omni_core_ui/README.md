# omni_core_ui

Shared core for every Omniverse app. Built from the Gemini "Omni-Hub bundling" blueprint (NotebookLM, Oct 27 2026), with the parts made real.

| Module | What it really does |
|---|---|
| `OmniHubClient` | The app's **only** door out. Talks to the Omni-Hub (local daemon) over loopback: `:9100` telemetry, `:5000` IPC gateway. The daemon alone talks to peers (`:5005` P2P sync, `:9101` UDP discovery). |
| `StargateIdentity` | Per-install Ed25519 key (seed in app-private SQLite). Signs and verifies events in the exact format of `Admin/omni_signing.py`. |
| `LocalEventStore` | Offline-first, signed, hash-chained local log (SQLite). Writes are instant; `syncToHub()` pushes pending events to the hub in order. |
| `OmniOta` | OTA updates: manifest from GitHub Releases today (OmniNet peers first once the mesh transport exists), optional Ed25519-pinned manifest, SHA-256 checked download, Android install prompt. |
| `MeshStatusBadge`, `HumanVerifiedBadge` | Human-first status: "Mesh online · 1 connected" / "Offline mode", and a HUMAN badge only when a signature truly verifies. |

## Honest limits
- The identity seed isn't in the Android hardware keystore yet.
- `LocalEventStore` is a per-device hash chain, not a Merkle DAG. Merging across devices is the daemon's job.
- Android always shows the install prompt for sideloaded updates. Flutter release builds can't hot-swap Dart code, so a "patch without restart" can only change assets or config.
- Signed manifests turn on when the repo secret `OMNI_OTA_SIGNING_KEY` (64-hex Ed25519 private seed) is set. Until then, manifests rely on HTTPS + SHA-256.

## Tests
`flutter test`: the vectors come from the daemon's Python signer, so passing proves byte-for-byte interop (canonical JSON, event ids, signatures).
