# The Omniverse

**Rule one: human first. Simple, human first.**

The Omniverse is the whole ecosystem, a peer-to-peer social and gaming world. Each person's phone or PC runs a small local hub, and the hubs sync signed events directly with each other, over LAN or the internet, with no central server. The apps only talk to their own local hub.

**Status: pre-alpha.** Android first (arm64, Android 8.0+), with Windows desktop builds for Omni Node, Plaza Brawler, Mesh Monitor and OmniStudio. Testing with a small, invited group. Test credits have no cash value.

**Next public step:** the STLGameDev playtest on **Sat Nov 28, 2026** (St. Louis County Library, Clark Family branch; our showcase window is 12–2 PM). The playtest builds freeze on Nov 22. Made by **Hactik Games Studios**.

## Download

Signed builds are on the [Releases page](https://github.com/kiroba/The-Omniverse/releases). Install the APKs you want. Each release ships a signed update manifest, so the apps can check for updates.

## The apps

| App | What it is | Repo |
| --- | --- | --- |
| KickBack | Human-first social feed: signed posts, profiles, wallet, biometric app lock; LPE identity transfer import and Mastodon public-post import | [kiroba/KickBack](https://github.com/kiroba/KickBack) |
| OmniCast | 1:1 P2P video calls through your own Omni Node, and Classroom Mode (in development) | [kiroba/OmniCast](https://github.com/kiroba/OmniCast) |
| LPE | Live Persona Engine: create your Halo — your identity home, with appearance choosers | [kiroba/LPE](https://github.com/kiroba/LPE) |
| Omni Plaza | The living shared plaza where your Halo lives (standalone app; the repo keeps its Idle-Plaza name until the post-playtest rename sweep) | [kiroba/Idle-Plaza](https://github.com/kiroba/Idle-Plaza) |
| Plaza Brawler | 2D fighter: offline vs AI, plus online PvP versus (lockstep, proven phone-vs-laptop Nov 15, 2026); Windows build with controller support | [kiroba/Plaza-Brawler](https://github.com/kiroba/Plaza-Brawler) |
| OmniStudio | Creator suite for games and mods (.omnimod packs); Windows + Linux desktop build with a read-only local API hook | [kiroba/OmniStudio](https://github.com/kiroba/OmniStudio) |
| Mesh Monitor | Health and telemetry dashboard for your hub and the mesh; Windows build | [kiroba/Mesh-Monitor](https://github.com/kiroba/Mesh-Monitor) |
| The Omni-Hub | The superapp: one container that holds every Omniverse experience | [kiroba/The-Omni-Hub](https://github.com/kiroba/The-Omni-Hub) |

## Core pieces

| Piece | What it does | Repo |
| --- | --- | --- |
| Omni daemon | The networked protocol on each device: signed event log, peer sync (negentropy catch-up), Internet reach by rendezvous and relay, self-hosted call relay (STUN/TURN), test-credits ledger, OmniCast signaling | [kiroba/Omni-Daemon](https://github.com/kiroba/Omni-Daemon) |
| Omni Node | The daemon as its own Android app: one Network switch, nearby radios (BLE, Wi-Fi Aware), Connect apps token, opt-in Relay calls | [kiroba/Omni-Node-Daemon](https://github.com/kiroba/Omni-Node-Daemon) |
| Omni-Core-UI | Shared Flutter package: Ed25519 identity, local event store, hub client, signed OTA updates, status badges | [kiroba/Omni-Core-UI](https://github.com/kiroba/Omni-Core-UI) |
| OmniMind | AI agent that maintains the worlds and runs every game NPC, including NPCs built by community devs | [kiroba/OmniMind](https://github.com/kiroba/OmniMind) |
| Continuity Engine | Profile ingestion: takes profiles from the daemons on each device and combines them into one | [kiroba/Continuity-Engine](https://github.com/kiroba/Continuity-Engine) |

## How it fits together

| Level | What it is |
| --- | --- |
| The Omniverse | The whole ecosystem |
| The Omni-Hub | The superapp people open: the container for every experience |
| Apps | KickBack, OmniCast, LPE, Omni Plaza, Plaza Brawler, OmniStudio, Mesh Monitor |
| Continuity Engine | Combines a person's profile across their devices' daemons |
| Omni daemon | The network protocol on each device |
| OmniMind | Runs the worlds and every NPC |

```
 App (Flutter)  ──loopback──▶  Local Omni daemon  ◀──signed sync──▶  Other daemons
   uses Omni-Core-UI            (:5000 / :9100)     (:5005, LAN or internet)
```

- Every event is Ed25519-signed and hash-chained, and every hub verifies it.
- Apps never talk to peers directly. Only the daemon does.
- No third-party servers, calls included: OmniCast connects directly when it can, otherwise through another Omni node's built-in relay (desktops by default; phones opt in, Wi-Fi + charging only).
- Field-proven so far: the desktop Omni Node synced with a phone on the same LAN and over the internet (Nov 14, 2026 — 128 reconciles, 0 errors, stores converged), and Plaza Brawler PvP played a full phone-vs-laptop match (Nov 15, 2026; dual-signed results via daemon 8.33.2). Still untested: OmniCast 1:1 calls between real phones on different networks — the first trial is the friend test on Nov 18/19, 2026.
- Hosting costs about $0: GitHub Pages for the site, GitHub Releases for binaries, and the free Actions tier for builds.

## Roadmap — the Nov 30, 2026 cycle

After the Nov 28 playtest (playtest-breakage fixes first), the next dev cycle fires on Mon Nov 30, 2026:

- **Split-package migration:** Omni-Core-UI first, then the apps, one CI-verified PR each.
- **Envelope encryption:** S1 Core-UI → S2 apps → S4 daemon secrets → S3 daemon store (envelope-over-SQLCipher; no private-layer field in plaintext).
- **OmniMind rebuild** scaffold, with its grading channel.
- **Cross-app per-person stats.**
- **Stage-2 front door:** one path from link → LPE → Halo → Plaza.

Also in progress, not shipped yet: the anime low-poly Halo figures (the realistic figure line is on hold; one Halo, each app renders its own view), the first Omni Plaza scenery set (storefronts, billboard, trees — being built locally), and the Hactik Games Studios splash screen for Plaza Brawler (drafted, not built). The Idle-Plaza → Omni Plaza code/repo rename sweep itself waits until after Nov 28 — docs already use the new names.

## This repo

The-Omniverse is the umbrella. It holds the project site (`docs/`, on GitHub Pages), the signed release pipeline (`.github/workflows/release.yml`), and the code that is still moving out to its own repo.

**Repo split in progress (Oct 2026).** Each app and core service is moving to its own repo, with its git history. Until a repo builds green by itself, this monorepo stays the source of truth and still produces the signed releases.

## Testers

Found a bug? Use **Report a bug** inside the app, or open an [issue](https://github.com/kiroba/The-Omniverse/issues).

## Security

See [SECURITY](docs/SECURITY.md). Never post keys, seeds, or tokens in issues.
