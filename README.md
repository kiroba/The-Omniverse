# The Omniverse

A peer-to-peer social and gaming ecosystem. Each person's phone or PC runs a small local hub, and the hubs sync signed events directly with each other, over LAN or Tailscale, with no central server. The apps only talk to their own local hub.

**Status: pre-alpha.** Android only (arm64, Android 8.0+). Testing with a small, invited group. Test credits have no cash value.

## Download

Signed builds are on the [Releases page](https://github.com/kiroba/The-Omniverse/releases). Install the APKs you want. Each release ships a signed update manifest, so the apps can check for updates.

## The apps

| App | What it is | Repo |
| --- | --- | --- |
| KickBack | Human-first social feed: signed posts, profiles, wallet, biometric app lock | [kiroba/KickBack](https://github.com/kiroba/KickBack) |
| OmniCast | 1:1 P2P video calls, and Classroom Mode (in development) | [kiroba/OmniCast](https://github.com/kiroba/OmniCast) |
| Idle Plaza | Halo Plaza idle and brawler game | [kiroba/Idle-Plaza](https://github.com/kiroba/Idle-Plaza) |
| Phaser Studio | 2D creator suite for games and mods | [kiroba/Phaser-Studio](https://github.com/kiroba/Phaser-Studio) |
| Mesh Monitor | Health and telemetry dashboard for your hub and the mesh | [kiroba/Mesh-Monitor](https://github.com/kiroba/Mesh-Monitor) |
| Omniverse Superapp | Every experience in one app | [kiroba/Omniverse-Superapp](https://github.com/kiroba/Omniverse-Superapp) |

## Core pieces

| Piece | What it does | Repo |
| --- | --- | --- |
| Omni-Hub daemon | Local hub: signed event log, peer sync (negentropy catch-up), remote hub over Tailscale, test-credits ledger, OmniCast signaling | [kiroba/The-Omni-Hub](https://github.com/kiroba/The-Omni-Hub) |
| Omni-Core-UI | Shared Flutter package: Ed25519 identity, local event store, hub client, signed OTA updates, status badges | [kiroba/Omni-Core-UI](https://github.com/kiroba/Omni-Core-UI) |
| OmniMind | AI agent that maintains the worlds and runs every game NPC, including NPCs built by community devs | [kiroba/OmniMind](https://github.com/kiroba/OmniMind) |
| Continuity Engine | Newsfeed-based profiles | [kiroba/Continuity-Engine](https://github.com/kiroba/Continuity-Engine) |

## How it fits together

```
 App (Flutter)  ──loopback──▶  Local Omni-Hub  ◀──signed sync──▶  Other hubs
   uses Omni-Core-UI            (:5000 / :9100)     (:5005, LAN or Tailscale)
```

- Every event is Ed25519-signed and hash-chained, and every hub verifies it.
- Apps never talk to peers directly. Only the hub does.
- Hosting costs about $0: GitHub Pages for the site, GitHub Releases for binaries, and the free Actions tier for builds.

## This repo

The-Omniverse is the umbrella. It holds the project site (`docs/`, on GitHub Pages), the signed release pipeline (`.github/workflows/release.yml`), and the code that is still moving out to its own repo.

**Repo split in progress (Oct 2026).** Each app and core service is moving to its own repo, with its git history. Until a repo builds green by itself, this monorepo stays the source of truth and still produces the signed releases.

## Testers

Found a bug? Use **Report a bug** inside the app, or open an [issue](https://github.com/kiroba/The-Omniverse/issues).

## Security

See [SECURITY](docs/SECURITY.md). Never post keys, seeds, or tokens in issues.
