# The Omniverse

**Rule one: human first. Simple, human first.**

The Omniverse is the whole ecosystem, a peer-to-peer social and gaming world. Each person's phone or PC runs a small local hub, and the hubs sync signed events directly with each other, over LAN or Tailscale, with no central server. The apps only talk to their own local hub.

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
| The Omni-Hub | The superapp: one container that holds every Omniverse experience | [kiroba/The-Omni-Hub](https://github.com/kiroba/The-Omni-Hub) |

## Core pieces

| Piece | What it does | Repo |
| --- | --- | --- |
| Omni daemon | The networked protocol on each device: signed event log, peer sync (negentropy catch-up), Internet reach without Tailscale, self-hosted call relay (STUN/TURN), test-credits ledger, OmniCast signaling | [kiroba/Omni-Daemon](https://github.com/kiroba/Omni-Daemon) |
| Omni Node | The daemon as its own Android app: one Network switch, nearby radios (BLE, Wi-Fi Aware), Connect apps token, opt-in Relay calls | [kiroba/Omni-Node-Daemon](https://github.com/kiroba/Omni-Node-Daemon) |
| Omni-Core-UI | Shared Flutter package: Ed25519 identity, local event store, hub client, signed OTA updates, status badges | [kiroba/Omni-Core-UI](https://github.com/kiroba/Omni-Core-UI) |
| OmniMind | AI agent that maintains the worlds and runs every game NPC, including NPCs built by community devs | [kiroba/OmniMind](https://github.com/kiroba/OmniMind) |
| Continuity Engine | Profile ingestion: takes profiles from the daemons on each device and combines them into one | [kiroba/Continuity-Engine](https://github.com/kiroba/Continuity-Engine) |

## How it fits together

| Level | What it is |
| --- | --- |
| The Omniverse | The whole ecosystem |
| The Omni-Hub | The superapp people open: the container for every experience |
| Apps | KickBack, OmniCast, Idle Plaza, Phaser Studio, Mesh Monitor |
| Continuity Engine | Combines a person's profile across their devices' daemons |
| Omni daemon | The network protocol on each device |
| OmniMind | Runs the worlds and every NPC |

```
 App (Flutter)  ──loopback──▶  Local Omni daemon  ◀──signed sync──▶  Other daemons
   uses Omni-Core-UI            (:5000 / :9100)     (:5005, LAN or Tailscale)
```

- Every event is Ed25519-signed and hash-chained, and every hub verifies it.
- Apps never talk to peers directly. Only the daemon does.
- No third-party servers, calls included: OmniCast connects directly when it can, otherwise through another Omni node's built-in relay (desktops by default; phones opt in, Wi-Fi + charging only). In review and not field-tested yet.
- Hosting costs about $0: GitHub Pages for the site, GitHub Releases for binaries, and the free Actions tier for builds.

## This repo

The-Omniverse is the umbrella. It holds the project site (`docs/`, on GitHub Pages), the signed release pipeline (`.github/workflows/release.yml`), and the code that is still moving out to its own repo.

**Repo split in progress (Oct 2026).** Each app and core service is moving to its own repo, with its git history. Until a repo builds green by itself, this monorepo stays the source of truth and still produces the signed releases.

## Testers

Found a bug? Use **Report a bug** inside the app, or open an [issue](https://github.com/kiroba/The-Omniverse/issues).

## Security

See [SECURITY](docs/SECURITY.md). Never post keys, seeds, or tokens in issues.
