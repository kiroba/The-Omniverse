# Hub daemon API reference (daemon v8.17.0)

Every HTTP endpoint and the UDP beacon served by `Admin/omni_live_daemon_server.py` (`VERSION = "8.17.0"`).
This page is the map; the feature docs linked from each section hold the design notes, limits and tests.
When this page and the code disagree, the code wins. Please file an issue.

**Example labels.** Examples marked **live (v8.17.0)** were captured from a real daemon in the sandbox
(a temp copy with ports moved to 19100/15000/15005/19101, fresh `HOME`, empty DB) and trimmed with `…`.
That is why those responses show test ports. Every other example is marked **from code, not live-tested**:
it was built from the handler code and the feature docs' examples, and its keys match what the handler
returns. Values are made up.

## Index

| Group | Method | Path | Port | Remote hub? | Section |
|---|---|---|---|---|---|
| Events | POST | `/api/events/append` | 5000 | yes (phone-signed) | [→](#post-apieventsappend) |
| Events | GET | `/api/events/feed` | 5000 | yes | [→](#get-apieventsfeed) |
| Events | GET | `/api/events/list` | 5000 | yes | [→](#get-apieventsstats--apieventslist) |
| Events | GET | `/api/events/stats` | 5000 | yes | [→](#get-apieventsstats--apieventslist) |
| Social | POST | `/api/social/comment` | 5000 | yes | [→](#post-apisocialcomment) |
| Social | POST | `/api/social/react` | 5000 | yes | [→](#post-apisocialreact) |
| Social | GET | `/api/social/thread` | 5000 | yes | [→](#get-apisocialthread) |
| Social | GET | `/api/social/counts` | 5000 | yes | [→](#get-apisocialcounts) |
| Profiles/Contacts | POST | `/api/profile/update` | 5000 | yes | [→](#post-apiprofileupdate) |
| Profiles/Contacts | GET | `/api/profile` | 5000 | yes | [→](#get-apiprofile) |
| Profiles/Contacts | GET | `/api/profile/list` | 5000 | yes | [→](#get-apiprofilelist) |
| Profiles/Contacts | POST | `/api/contacts/verify` | 5000 | yes | [→](#post-apicontactsverify) |
| Profiles/Contacts | GET | `/api/hub/card` | 5000 | yes | [→](#get-apihubcard) |
| Profiles/Contacts | POST | `/api/invites/create` | 5000 | yes | [→](#post-apiinvitescreate) |
| Profiles/Contacts | GET | `/api/invites/redeem` | 5000 | yes | [→](#get-apiinvitesredeem) |
| Credits | GET | `/api/credits/balance` | 5000 | yes (read-only remotely) | [→](#get-apicreditsbalance) |
| Credits | GET | `/api/credits/history` | 5000 | yes | [→](#get-apicreditshistory) |
| Credits | POST | `/api/credits/send` | 5000 | yes (owner-signed) | [→](#post-apicreditssend) |
| Credits | POST | `/api/credits/transfer` | 5000 | **no**, loopback only | [→](#post-apicreditstransfer) |
| Credits | POST | `/api/credits/grant` | 5000 | **no**, loopback only | [→](#post-apicreditsgrant) |
| OmniCast | POST | `/api/signal/send` | 5000 | yes | [→](#post-apisignalsend) |
| OmniCast | GET | `/api/signal/poll` | 5000 | yes | [→](#get-apisignalpoll) |
| OmniCast | GET | `/api/signal/ice-config` | 5000 | yes | [→](#get-apisignalice-config) |
| Telemetry | GET | `/api/v1/telemetry/node-health` | **9100** | yes | [→](#get-apiv1telemetrynode-health-port-9100) |
| Telemetry | GET | `/api/telemetry/summary` | 5000 | yes | [→](#get-apitelemetrysummary) |
| Telemetry | POST | `/api/telemetry/app-checkin` | 5000 | yes | [→](#post-apitelemetryapp-checkin) |
| Telemetry | GET / POST | `/api/omnimind/telemetry` | **9100** | **no**, loopback only | [→](#get--post-apiomnimindtelemetry-port-9100) |
| Bugs | POST | `/api/bugs/report` | 5000 | yes | [→](#post-apibugsreport) |
| Bugs | GET | `/api/bugs/list` | 5000 | **no**, loopback only | [→](#get-apibugslist) |
| Sync/P2P | POST | `/api/sync/catchup` | 5000 | **no**, loopback only | [→](#post-apisynccatchup) |
| Sync/P2P | POST | `/p2p/sync` | 5005 | n/a (mesh header) | [→](#post-p2psync) |
| Sync/P2P | POST | `/p2p/reconcile` | 5005 | n/a (mesh + known peer) | [→](#post-p2preconcile) |
| Sync/P2P | POST | `/p2p/events` | 5005 | n/a (mesh + known peer) | [→](#post-p2pevents) |
| Sync/P2P | UDP | beacon | 9101 | n/a | [→](#udp-discovery-9101) |

That is 33 HTTP endpoints (counting `/api/omnimind/telemetry` GET and POST as one) plus the UDP beacon.
Any other path gets **404** (`send_error`, an HTML body, not JSON). Every port also answers `OPTIONS`
with CORS headers (`GET, POST, OPTIONS`; `Content-Type, Authorization`).

---

## 1. Quick start

### Ports

| Port | Env override | Bind | What |
|---|---|---|---|
| 5000 | `OMNI_IPC_PORT` | 127.0.0.1 (+ `OMNI_HUB_BIND` in remote hub mode) | App API / IPC: events, social, profiles, credits, signaling, telemetry summary, bugs |
| 9100 | `OMNI_TELEMETRY_PORT` | 127.0.0.1 (+ `OMNI_HUB_BIND` in remote hub mode) | App-facing health: `node-health`, plus the local OmniMind agent cache |
| 5005 | `OMNI_P2P_PORT` | 0.0.0.0 | P2P between daemons: `/p2p/sync`, `/p2p/reconcile`, `/p2p/events` |
| 9101 | `OMNI_UDP_PORT` | 0.0.0.0 (UDP) | LAN discovery beacons (advertise the 5005 port) |

### Base URLs

| Hub setting in the app | `:5000` base | `:9100` base | Token |
|---|---|---|---|
| **This phone** (daemon on the same device) | `http://127.0.0.1:5000` | `http://127.0.0.1:9100` | none |
| **Remote hub** over Tailscale | `http://100.x.y.z:5000` (hub's Tailscale IP) | `http://100.x.y.z:9100` | `Authorization: Bearer <token>` |

Remote hub mode is off unless the hub runs with `OMNI_HUB_REMOTE=1` and `OMNI_HUB_BIND=<tailscale ip | 0.0.0.0>`.
The token is created once at `~/.omni/hub_token` (override: `OMNI_HUB_TOKEN_FILE`), printed at
startup and kept across restarts. Delete the file and restart the daemon to rotate it. Setup is in
[REMOTE_HUB.md](REMOTE_HUB.md). Keep these ports on Tailscale, because the daemon speaks plain HTTP.

```bash
TOKEN=$(cat ~/.omni/hub_token)            # on the hub
curl -H "Authorization: Bearer $TOKEN" http://100.x.y.z:9100/api/v1/telemetry/node-health
```

### Always send a body length

For a POST, send `Content-Length`. Since v8.12.1 the `:5000` POSTs also accept
`Transfer-Encoding: chunked` ([REQUEST_BODIES.md](REQUEST_BODIES.md)). The OmniMind cache on `:9100` and
all three `/p2p/*` routes still read **only** `Content-Length`. Without a body, most `:5000`
POSTs answer **411**; `/api/events/append` answers **400**. In Dart, set `request.contentLength`
before `write`.

### Which version is running?

```bash
curl -s http://127.0.0.1:9100/api/v1/telemetry/node-health | python3 -c "import sys,json;print(json.load(sys.stdin)['version'])"
```

`version` also shows up in `/api/events/feed`, `/api/telemetry/summary`, `/api/hub/card` and
`/api/bugs/list`. Older daemons answer **404** on paths added after them. Treat a 404 as "this hub is
too old for the feature", not as an error.

### Common error shape

Handlers on `:5000` answer `{"status": "ERROR", "message": "…"}` with the status code. The
remote gate's 401 also sends `WWW-Authenticate: Bearer realm="omni-hub"`. Unknown paths, and a few
older handlers noted below, use `send_error`, which returns an HTML body rather than JSON.

---

## 2. Auth rules

The `:5000` and `:9100` handlers run the same gate (`remote_gate`) before any route:

| Caller | Path in `REMOTE_GET_PATHS` / `REMOTE_POST_PATHS` | Result |
|---|---|---|
| Loopback (`127.*`, `::1`) | any | allowed, no token |
| Non-loopback, remote hub **off** | any | **403** `loopback only` |
| Non-loopback, remote hub on | not in the allow-list | **403** `loopback only` |
| Non-loopback, remote hub on | in the allow-list, missing or wrong bearer | **401** `missing or invalid bearer token` |
| Non-loopback, remote hub on | in the allow-list, valid bearer (`hmac.compare_digest`) | allowed |

Summary per endpoint class:

| Class | Endpoints | Rule |
|---|---|---|
| **Loopback only** | `POST /api/credits/transfer`, `POST /api/credits/grant`, `GET /api/bugs/list`, `POST /api/sync/catchup`, `GET`/`POST :9100/api/omnimind/telemetry` | Never reachable from another device, even with the token |
| **Bearer when remote** | everything else on `:5000` and `GET :9100/api/v1/telemetry/node-health` | Loopback is open. Remote needs remote hub mode and `Authorization: Bearer <token>` |
| **Mesh header** | `POST :5005/p2p/sync` | `X-Omni-Mesh: <OMNI_MESH_ID>` or 403. Then signature (401) and trusted-keys allowlist (403) |
| **Mesh header + known peer** | `POST :5005/p2p/reconcile`, `POST :5005/p2p/events` | Mesh header (403) and caller must be loopback, a fresh same-mesh discovered peer, or a host in `OMNI_SYNC_PEERS` (403) |

The bearer token authenticates the **device**, not a person. Writes that act for a person also need
that person's Ed25519 signature: remote appends, profiles, comments, reactions, signaling, signed credit
sends and app check-ins. The hub never signs on a remote person's behalf.

> `SECURITY.md` §2.2 describes a per-run bearer token on every IPC call, Host/Origin checks and a
> 120 req/min limiter. Those are targets, not v8.17.0 behaviour: loopback calls carry no token and
> there is no Host/Origin check. The per-key limits that exist are listed on each endpoint below.

---

## 3. Signing

All signatures are Ed25519 (hex, 128 chars) by a 64-char lowercase-hex raw public key. There are two
canonical-bytes rules. Use the one for the type you're signing:

| Signed thing | Bytes | Domain separation | Feature doc |
|---|---|---|---|
| **Chain events** (`/api/events/append` remote, `/p2p/*`, profile / comment / reaction) | `json.dumps({action, author_pubkey, payload, previous_hash, ts│timestamp}, sort_keys=True, separators=(",", ":"))`: **ASCII-escaped** (`ensure_ascii` default). `event_id = "0x" + sha256(same bytes)` | the `action` field (`profile_update`, `kickback_comment`, `kickback_reaction`, …) | [SIGNED_EVENTS.md](SIGNED_EVENTS.md), `Admin/omni_signing.py` |
| **Contact card** | sorted-key compact JSON of every field except `sig`, **raw UTF-8** (`ensure_ascii=False`) | `"type": "omni.contact-card.v1"` | [PROFILES_AND_CONTACTS.md](PROFILES_AND_CONTACTS.md) |
| **Hub card** (node-signed) | same as contact card | `"type": "omni.hub-card.v1"` | [PROFILES_AND_CONTACTS.md](PROFILES_AND_CONTACTS.md) |
| **Signal send** | `{call_id, from, kind, payload, to, ts, type}` raw UTF-8 | `"type": "omnicast.signal.v1"` | [OMNICAST_SIGNALING.md](OMNICAST_SIGNALING.md#signing-exact-bytes) |
| **Signal poll** | `{to, ts, type}` raw UTF-8 | `"type": "omnicast.poll.v1"` | same |
| **ICE config** | `{pubkey, ts, type}` raw UTF-8 | `"type": "omnicast.ice-config.v1"` | same |
| **Credit send** | every body field except `sig`, raw UTF-8 (the fee isn't signed) | `"type": "omni.credits.transfer.v1"` | [CREDITS_LEDGER.md](CREDITS_LEDGER.md#signed-transfers-v8150) |
| **App check-in** | every body field except `sig`, raw UTF-8 | `"type": "omni.app-checkin.v1"` | [APP_TELEMETRY.md](APP_TELEMETRY.md) |
| **UDP beacon** (node-signed) | `b"OMNI_BEACON_V1\n"` + sorted compact JSON of every field except `sig`, ASCII-escaped | byte prefix `OMNI_BEACON_V1\n` | [MESH_ID.md](MESH_ID.md) |

`ts` is always an **int** (milliseconds). Legacy chain events may carry float `timestamp` seconds instead.
Never send both. The two JSON rules differ only on non-ASCII text, so test with an emoji.

---

## 4. Endpoints

### Events

#### POST /api/events/append
- **Port / auth:** 5000; loopback, or bearer when remote.
- **Purpose:** append an app event to the chain. **Loopback**: the node signs it and becomes `author_pubkey`.
  **Remote**: the body must carry the phone's own signature, either top-level `author_pubkey` +
  `signature` or KickBack's `payload.app_*` envelope. It is verified like a peer event and stored with the
  phone as author. Stored events are relayed to live peers.
- **Body:** ≤ 5 MB, Content-Length or chunked. `action`, `payload`, optionally `ts` / `timestamp`,
  `previous_hash`, `event_id` (checked against the computed hash).

Request (remote, KickBack envelope). **From code, not live-tested.**
```json
{"action": "KICKBACK_POST",
 "payload": {"text": "hi from phone B", "app": "kickback",
             "app_event_id": "0x05e3…", "app_author_pubkey": "5383…", "app_signature": "abc2…",
             "app_previous_hash": "0x0000…", "app_ts": 1793163300000}}
```
Response. **From code, not live-tested.**
```json
{"status": "SUCCESS", "event_id": "0x296d…", "merkle_hash": "0x4444…", "ts": 1793163300000}
```
A replay answers `{"status": "SUCCESS", "event_id": "0x…", "result": "ALREADY_EXISTS"}`.

| Code | When |
|---|---|
| 400 | empty body, `{}` or non-object; bad JSON; both `ts` and `timestamp`; `ts` not a non-negative int; time > `OMNI_MAX_FUTURE_SKEW_S` (600 s) ahead; `event_id` mismatch; remote post without a phone signature |
| 401 | remote: bad signature |
| 403 | `action` is `credit_entry` (use `/api/credits/*`) or a reserved person-signed action (`profile_update`, `kickback_comment`, `kickback_reaction`: use their endpoints); remote author not on `OMNI_TRUSTED_KEYS_FILE`; remote gate |
| 413 | body > 5 MB |

#### GET /api/events/feed
- **Port / auth:** 5000; loopback, or bearer when remote. Read-only.
- **Purpose:** newest-first page of stored events (local and from peers), with `verified` re-checked at read time.
- **Query:** `limit` (default 50, clamped 1–200), `before=<id>` (older page), `since=<id>` (poll), `type=<action>`.
  The cursor is the local row `id` (arrival order). Details: [EVENT_FEED.md](EVENT_FEED.md).

Response: **live (v8.17.0)**, `GET /api/events/feed?limit=5` on a fresh DB:
```json
{"status": "OK", "node_id": "609b7ede42abad7b9cd3d39a6be947309d6f2c6dbfae711b11e35786df6e3b60", "mesh_id": "dev",
 "version": "8.17.0", "limit": 5,
 "events": [{"id": 1, "event_id": "0xgenesis_000", "type": "GENESIS_NODE_INIT", "action": "GENESIS_NODE_INIT",
             "author_pubkey": "609b7ede…", "origin": "local", "timestamp": 1700000000.0, "ts_ms": 1700000000000,
             "payload": {"system": "Genesis Node Init"},
             "previous_hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
             "signature": null, "verified": false}],
 "count": 1, "has_more": false, "next_before": null, "latest_id": 1}
```
Errors: **400** for an unknown parameter, a non-integer cursor or a bad `type`; **500** if the DB read fails.

#### GET /api/events/stats · /api/events/list
- **Port / auth:** 5000; loopback, or bearer when remote. Both paths return the same counts (no event list).
- **Quirk:** these match on the full raw path, so **any query string gets 404**.

Response: **live (v8.17.0)**, `GET /api/events/stats`:
```json
{"status": "OK", "db_mode": "WAL", "total_events": 1, "last_merkle_hash": "0xgenesis_000",
 "node_id": "609b7ede42abad7b9cd3d39a6be947309d6f2c6dbfae711b11e35786df6e3b60"}
```
Errors: none of its own. DB errors fall back to `total_events: 0`.

### Social ([SOCIAL.md](SOCIAL.md))

Comments and reactions are **person-signed chain events**: the envelope is
`{action, author_pubkey, previous_hash, ts, payload, signature[, event_id]}` (no other keys), with the
signature over the chain-event bytes (§3). Body ≤ 16 KB. Shared answers:

| Code | When |
|---|---|
| 200 | `{"status": "SUCCESS", "event_id", "merkle_hash", "ts", "author_pubkey", "action"}`; a replay adds `"result": "ALREADY_EXISTS"` |
| 400 | envelope or payload schema |
| 401 | bad author signature |
| 403 | author not on the trusted-keys allowlist (when set); remote gate |
| 411 / 413 | no body / too large |
| 429 | more than `OMNI_USER_RATE_MAX` (30) writes per key per minute, shared with profile updates |

#### POST /api/social/comment
5000; loopback or bearer. `action: "kickback_comment"`. **From code, not live-tested.**
```json
{"action": "kickback_comment", "author_pubkey": "ab12…(64 hex)", "previous_hash": "0x0000…(64 hex)",
 "ts": 1793334636472, "signature": "…(128 hex)",
 "payload": {"schema": 1, "post_id": "0x…(64 hex)", "text": "nice one", "reply_to": "0x…(optional)"}}
```
```json
{"status": "SUCCESS", "event_id": "0x7c1e…", "merkle_hash": "0x0000…", "ts": 1793334636472,
 "author_pubkey": "ab12…", "action": "kickback_comment"}
```

#### POST /api/social/react
5000; loopback or bearer. `action: "kickback_reaction"`. The payload must be exactly
`{schema, post_id, reaction, on}`. The latest signed `ts` wins per (person, post, reaction).
**From code, not live-tested.**
```json
{"action": "kickback_reaction", "author_pubkey": "ab12…", "previous_hash": "0x…", "ts": 1793334637000,
 "signature": "…", "payload": {"schema": 1, "post_id": "0x…", "reaction": "🔥", "on": true}}
```
The response has the same shape as a comment.

#### GET /api/social/thread
5000; loopback or bearer. Query: `post_id` (required), `limit` 1–500, `viewer=<pubkey>`. **From code, not live-tested.**
```json
{"status": "OK", "post_id": "0x…", "post_known": true,
 "post": {"author_pubkey": "…", "text": "first 280 chars", "ts_ms": 1793334636472},
 "comment_count": 2, "has_more": false,
 "comments": [{"event_id": "0x…", "author_pubkey": "…", "handle_display": "@alice.ab12", "text": "first!",
               "reply_to": null, "ts_ms": 1793334636000, "origin": "remote", "verified": true}],
 "reactions": {"🔥": 2, "lol": 1}, "my_reactions": ["lol"]}
```
Errors: **400** for a missing or bad `post_id` or an unknown parameter.

#### GET /api/social/counts
5000; loopback or bearer. Query: `post_ids=a,b,…` (max 100), `viewer`. **From code, not live-tested.**
```json
{"status": "OK", "posts": {"0x…": {"comments": 3, "reactions": {"🔥": 2}, "my_reactions": []}}}
```
Errors: **400** for bad or too many ids, or an unknown parameter.

### Profiles / Contacts ([PROFILES_AND_CONTACTS.md](PROFILES_AND_CONTACTS.md))

#### POST /api/profile/update
5000; loopback or bearer. Person-signed event with `action: "profile_update"`. It has the same envelope, limits
and codes as the Social writes above. Payload: `schema: 1`, `handle` (3–20 `a-z0-9_`), optional
`display_name` (≤ 48), `bio` (≤ 280), `avatar` (≤ 200), `omnicast` (bool). **From code, not live-tested.**
```json
{"action": "profile_update", "author_pubkey": "ab12…", "previous_hash": "0x0000…", "ts": 1793334636472,
 "signature": "…", "payload": {"schema": 1, "handle": "keith_b", "display_name": "Keith", "omnicast": true}}
```
```json
{"status": "SUCCESS", "event_id": "0x…", "merkle_hash": "0x…", "ts": 1793334636472,
 "author_pubkey": "ab12…", "action": "profile_update"}
```

#### GET /api/profile
5000; loopback or bearer. Query: `pubkey=<64 hex>`. The latest signed `ts` wins. **From code, not live-tested.**
```json
{"status": "OK", "profile": {"pubkey": "ab12…", "handle": "keith_b", "handle_display": "@keith_b.ab12",
 "display_name": "Keith", "omnicast": true, "updated_ts_ms": 1793334636472, "event_id": "0x…",
 "origin": "remote", "verified": true}}
```
Errors: **400** for a bad or missing pubkey; **404** `{"status": "ERROR", "message": "no profile for that key on this hub", "pubkey": "…"}`.

#### GET /api/profile/list
5000; loopback or bearer. Query: `q=<prefix>` (handle, display name or pubkey; a leading `@` is ignored), `limit` 1–200.

Response: **live (v8.17.0)**, empty hub:
```json
{"status": "OK", "count": 0, "has_more": false, "profiles": []}
```
`profiles[]` items have the same shape as `profile` above. Errors: **400** for an unknown parameter or bad limit.

#### POST /api/contacts/verify
5000; loopback or bearer. Body ≤ 8 KB: a contact card, or `{"qr": "omni://contact?c=…"}`. **From code, not live-tested.**
```json
{"qr": "omni://contact?c=eyJkaXNwbGF5X25hbWUiOiJLZWl0aCIs…"}
```
```json
{"status": "OK", "valid": true,
 "card": {"type": "omni.contact-card.v1", "pubkey": "ab12…", "handle": "keith_b", "display_name": "Keith",
          "hub": {"host": "100.101.102.103", "ipc_port": 5000}, "ts": 1793334636472, "sig": "…"},
 "handle_display": "@keith_b.ab12", "qr": "omni://contact?c=…", "profile": null}
```
Errors: **400** `{"status": "ERROR", "valid": false, "message": …}` for a bad signature or schema, a future-dated card,
or a card older than one year. 411/413 for the body.

#### GET /api/hub/card
5000; loopback or bearer. No parameters (any parameter → **400**). A node-signed "join this hub" card.
The bearer token is **never** in it.

Response: **live (v8.17.0)** (`qr` trimmed):
```json
{"status": "OK",
 "card": {"type": "omni.hub-card.v1", "node_id": "609b7ede42abad7b9cd3d39a6be947309d6f2c6dbfae711b11e35786df6e3b60",
          "mesh_id": "dev", "version": "8.17.0", "ipc_port": 15000, "telemetry_port": 19100,
          "addresses": ["127.0.0.1"], "remote_hub": false, "ts": 1793389376168,
          "sig": "b77eb3c3a6ada858e26ed935115a7a2ac607b06ce26b8dd57c3df33a9eb7fe43914f8cfc730c60baf2ebc74ce0892cd96b8e0746e8dfa88b3dd14569e7e5f808"},
 "qr": "omni://hub?c=eyJhZGRyZXNzZXMiOlsiMTI3LjAuMC4xIl0s…",
 "note": "the bearer token is not in the card; copy ~/.omni/hub_token separately"}
```

#### POST /api/invites/create
5000; loopback or bearer. Body ≤ 8 KB: `{"card": <contact card signed in the last 10 min>, "ttl_s"?: 60–604800 (default 86400), "max_uses"?: 1–100 (default 1)}`.
**From code, not live-tested.**
```json
{"card": {"type": "omni.contact-card.v1", "pubkey": "ab12…", "handle": "keith_b", "ts": 1793334636472, "sig": "…"},
 "ttl_s": 86400, "max_uses": 1}
```
```json
{"status": "OK", "code": "K7QM-3XWD", "expires_ms": 1793421036472, "max_uses": 1, "qr": "omni://invite?code=K7QM-3XWD"}
```
Errors: **400** for a bad or stale card or bad ttl/uses; **429** for rate limiting or 20 live invites per key; **503** if a code can't be allocated.

#### GET /api/invites/redeem
5000; loopback or bearer. Query: `code=K7QM-3XWD` (case and dash optional). Codes only work on the issuing hub.
**From code, not live-tested.**
```json
{"status": "OK", "card": {"type": "omni.contact-card.v1", "pubkey": "ab12…", "handle": "keith_b", "ts": 1793334636472, "sig": "…"},
 "handle_display": "@keith_b.ab12", "uses_left": 0, "expires_ms": 1793421036472}
```
Errors: **400** for a malformed code; **404** for an unknown, expired or used-up code; **429** after 20 failed codes per client per minute.

### Credits: TEST ledger, no cash value ([CREDITS_LEDGER.md](CREDITS_LEDGER.md))

Balances are replayed from node-signed `credit_entry` events. Each pubkey gets a one-time 1,000-credit
welcome grant. Bodies ≤ 4 KB. All credits endpoints answer **409** `{"integrity": "FAILED", "event_id": …}` when
a stored entry fails its hash, signature or schema check during replay, and **500** for other ledger errors.

#### GET /api/credits/balance
5000; loopback or bearer. Query: `pubkey=<64 hex | treasury>`. A **loopback** lookup issues the welcome
grant if it hasn't been issued yet. A **remote** lookup never writes; it reports `welcome_pending` and counts the grant in `available`.
**From code, not live-tested.**
```json
{"status": "OK", "pubkey": "ab12…", "balance": 1000, "test_only": true, "available": 1000,
 "welcome_pending": false, "note": "test credits, no cash value", "fee_bps": 0,
 "entries_replayed": 1, "version": "8.17.0"}
```
Errors: **400** for a bad pubkey.

#### GET /api/credits/history
5000; loopback or bearer. Query: `pubkey`, `limit` 1–200 (default 50). Newest first. **From code, not live-tested.**
```json
{"status": "OK", "pubkey": "ab12…", "balance": 750, "test_only": true, "count": 2, "has_more": false,
 "entries": [{"kind": "transfer", "from": "ab12…", "to": "cd34…", "amount": 250, "fee": 0, "memo": "for lunch",
              "test_only": true, "event_id": "0x…", "ts_ms": 1793334636472, "delta": -250, "balance_after": 750}]}
```
Errors: **400** for an unknown parameter, bad pubkey or bad limit.

#### POST /api/credits/send
5000; loopback or bearer. **Signed by the owner of `from`** (§3). This is the endpoint phones should use.
**From code, not live-tested.**
```json
{"type": "omni.credits.transfer.v1", "from": "ab12…", "to": "cd34…", "amount": 250, "kind": "tip",
 "memo": "for lunch", "ref": "0x…(post id; required for tip)", "nonce": "9f2c4be01a7d3e55", "ts": 1793334636472, "sig": "…"}
```
```json
{"status": "SUCCESS", "event_id": "0x…",
 "entry": {"kind": "tip", "from": "ab12…", "to": "cd34…", "amount": 250, "fee": 0, "memo": "for lunch", "test_only": true,
           "auth": {"type": "omni.credits.transfer.v1", "nonce": "9f2c4be01a7d3e55", "ts": 1793334636472, "sig": "…"},
           "ref": "0x…"},
 "balance": 750}
```
An identical retry answers `{"status": "SUCCESS", "result": "ALREADY_APPLIED", "event_id", "balance"}`.

| Code | When |
|---|---|
| 400 | unknown or missing field, bad kind/amount/memo/ref, uppercase pubkey, `from == to` |
| 401 | bad signature; `ts` more than 10 min from the hub clock |
| 409 | insufficient balance; nonce reused with different content; ledger integrity failure |
| 411 / 413 | no body / > 4 KB |

#### POST /api/credits/transfer
5000; **loopback only**. Unsigned. Answers **403** when `OMNI_CREDITS_REQUIRE_SIGNED=1`. **From code, not live-tested.**
```json
{"from": "ab12…", "to": "cd34…", "amount": 400, "memo": "sticker pack", "kind": "purchase"}
```
```json
{"status": "SUCCESS", "event_id": "0x…",
 "entry": {"kind": "purchase", "from": "ab12…", "to": "cd34…", "amount": 400, "fee": 0, "memo": "sticker pack", "test_only": true},
 "balance": 600}
```
Errors: **400** for bad input; **403** for non-loopback or require-signed; **409** for overdraft or integrity; 411/413.

#### POST /api/credits/grant
5000; **loopback only** (admin). `{"to", "amount", "memo"?}` grants from the treasury; `{"kind": "reset", "pubkey", "memo"?}`
moves a whole balance back to the treasury. **From code, not live-tested.**
```json
{"to": "ab12…", "amount": 500, "memo": "tester top-up"}
```
```json
{"status": "SUCCESS", "event_id": "0x…",
 "entry": {"kind": "grant", "from": "treasury", "to": "ab12…", "amount": 500, "fee": 0, "memo": "tester top-up", "test_only": true}}
```
A reset of an empty account answers `{"status": "SUCCESS", "result": "NOTHING_TO_RESET", "balance": 0}`. Errors: **400** (including using
the reserved welcome memo), **403** for non-loopback, **409** for integrity, 411/413.

### OmniCast signaling ([OMNICAST_SIGNALING.md](OMNICAST_SIGNALING.md))

Memory-only mailbox. `ts` must be within ±120 s, each signature is accepted once (409 on reuse), and
messages expire after 60 s (`OMNI_SIGNAL_TTL`). See the feature doc for every limit.

#### POST /api/signal/send
5000; loopback or bearer. Body ≤ 16 KB with exactly these fields. **From code, not live-tested.**
```json
{"to": "cd34…", "from": "ab12…", "call_id": "call-7f3a", "kind": "offer",
 "payload": "v=0\r\no=- 46117 2 IN IP4 127.0.0.1\r\n…", "ts": 1793042651190, "sig": "…"}
```
```json
{"status": "QUEUED", "seq": 42, "epoch": "9f2c4be01a7d3e55", "expires_in": 60}
```
Errors: **400** field or JSON; **401** signature or `ts`; **409** replay; **411** no body; **413** too big; **429** rate limit or
mailbox full (64); **503** hub full (4,096).

#### GET /api/signal/poll
5000; loopback or bearer. Query: `to`, `ts`, `sig` (signed by `to`, type `omnicast.poll.v1`), optional `since`,
`epoch` (v8.17.0) and `wait` (0–25 s long-poll). Returns **and removes** queued messages. **From code, not live-tested.**
```json
{"status": "OK", "count": 1, "cursor": 42, "epoch": "9f2c4be01a7d3e55", "cursor_reset": false,
 "messages": [{"seq": 42, "from": "ab12…", "to": "cd34…", "call_id": "call-7f3a", "kind": "offer",
               "payload": "v=0…", "ts": 1793042651190, "sig": "…"}]}
```
Errors: **400** for a missing, duplicate or unknown parameter or a bad `epoch`; **401** for a signature or stale `ts`; **409** replay.

#### GET /api/signal/ice-config
5000; loopback or bearer. Query: `pubkey`, `ts`, `sig` (type `omnicast.ice-config.v1`). STUN plus TURN REST credentials
when `OMNI_TURN_URLS` + `OMNI_TURN_SECRET` are set. **From code, not live-tested.**
```json
{"status": "OK", "turn": true, "ttl": 3600, "expires_at": 1793046251, "ice_transport_policy": "relay",
 "ice_servers": [{"urls": ["stun:stun.l.google.com:19302"]},
                 {"urls": ["turn:100.101.102.103:3478?transport=udp"], "username": "1793046251:ab12…", "credential": "<base64>"}]}
```
Without TURN: `"turn": false`, `"ice_transport_policy": "all"`, STUN only. Errors: **400**, **401**, **409**, as for poll.

### Telemetry

#### GET /api/v1/telemetry/node-health (port 9100)
9100; loopback, or bearer when remote. Exact-path match: a query string gets **404**. `catchup` is the last
catch-up run (`null` until one has run).

Response: **live (v8.17.0)**:
```json
{"status": "ONLINE", "version": "8.17.0", "node_id": "609b7ede42abad7b9cd3d39a6be947309d6f2c6dbfae711b11e35786df6e3b60",
 "mesh_id": "dev", "local_ip": "172.16.18.145", "p2p_sync_port": 15005, "active_peers": 0, "peer_ips": [],
 "uptime_seconds": 4.9, "catchup": null}
```

#### GET /api/telemetry/summary
5000; loopback or bearer. No parameters (any → **400**). Aggregates only, with no contents, IPs or full keys.
Counters reset on restart. **500** if building the summary fails. Sections: [TELEMETRY_SUMMARY.md](TELEMETRY_SUMMARY.md).

Response: **live (v8.17.0)**, heavily trimmed:
```json
{"status": "OK", "schema": 1, "version": "8.17.0", "generated_at_ms": 1793389376109, "counters_since_ms": 1793389371122,
 "counters_note": "since-start counters are in memory and reset when the daemon restarts",
 "protocols": [
   {"id": "tcp_api", "name": "TCP app API (:19100 telemetry, :15000 events)", "state": "up", "listen": ["127.0.0.1"],
    "ports": [19100, 15000], "remote_hub": false, "last_seen_ago_s": 0.0, "counts": {"loopback_requests": 4, "remote_requests": 0}},
   {"id": "p2p_sync", "state": "up", "…": "…"}, {"id": "udp_discovery", "…": "…"}, {"id": "negentropy", "state": "idle", "…": "…"},
   {"id": "signaling", "…": "…"}, {"id": "turn", "state": "off", "configured": false, "detail": "STUN only", "last_seen_ago_s": null}],
 "security": {"events_stored_local_signed": 0, "events_rejected_signature": 0, "bearer_auth_failures": 0,
              "trusted_keys_allowlist": null, "remote_hub": false, "hub_token_age_s": null, "unsigned_rows_in_store": 1, "…": "…"},
 "finance": {"state": "ok", "test_only": true, "note": "test credits, no cash value", "treasury_fee_bps": 0,
             "integrity": "VERIFIED", "entries": 0, "accounts": 0, "…": "…"},
 "users": {"identities_seen": 0, "active_24h": 0, "active_7d": 0, "new_7d": 0, "bug_reports": 0,
           "app_checkins": {"installs": 0, "consent": {"accepted": 0, "not_accepted": 0, "by_version": {}}, "…": "…"}},
 "services": {"app_crashes": {"last_24h": 0, "last_7d": 0, "by_app": {}, "top_kinds": {}, "…": "…"},
              "daemon_version": "8.17.0", "uptime_seconds": 4.9, "node_id_prefix": "609b7ede42ab", "mesh_id": "dev",
              "event_store": {"total_events": 1, "db_bytes": 16384, "events_by_action": {"GENESIS_NODE_INIT": 1}},
              "omnimind_agent": {"live": false, "last_report_ago_s": null}}}
```

#### POST /api/telemetry/app-checkin
5000; loopback or bearer. Body ≤ 4 KB, signed by the app key (type `omni.app-checkin.v1`). Fields and privacy rules: [APP_TELEMETRY.md](APP_TELEMETRY.md).
**From code, not live-tested.**
```json
{"type": "omni.app-checkin.v1", "pubkey": "ab12…", "app": "kickback", "app_version": "0.1.10", "platform": "android",
 "os_major": 15, "consent_version": "1", "consent_accepted": true, "crashes": {"count": 2, "last_kind": "StateError"},
 "ts": 1793334636472, "sig": "…"}
```
```json
{"status": "OK", "install_id": "3fa1c09e2b7d4e5f6a70", "recorded": {"crashes": 2}}
```
Errors: **400** schema or extra fields; **401** signature or `ts` more than 10 min off; **429** more than 2 per install+app per minute; **503** table full.

#### GET / POST /api/omnimind/telemetry (port 9100)
9100; **loopback only**. The cache for the local OmniMind agent (`omnimind_agent_telemetry_engine.py`).
POST: a JSON object, `Content-Length` only (chunked not supported), ≤ 64 KB → `{"status":"CACHED"}`.
GET: the cached object plus `age_seconds`, or **404** "No live OmniMind agent" when nothing has been posted in the last 15 s.
Errors: POST **413** for a missing or oversized body, **400** for bad JSON or a non-object (HTML `send_error` bodies).
**From code, not live-tested.**
```json
{"cpu_percent": 12.5, "mem_mb": 210, "age_seconds": 3.2}
```
(The payload is whatever the agent posted; the hub doesn't check its keys.)

> Known issue (v8.17.0): the GET handler writes the response body twice (`self.wfile.write(body)` and
> then again inside `try`), so a client can read the JSON followed by trailing bytes past `Content-Length`.
> Not fixed in this docs PR.

### Bugs

#### POST /api/bugs/report
5000; loopback or bearer. Body ≤ 8 KB of string fields, with `what_happened` (≤ 4000) required.
Unknown fields are rejected. Stored as a node-signed `bug_report` event (not relayed).
**From code, not live-tested.**
```json
{"what_happened": "Feed stays empty after posting", "title": "Empty feed", "app": "kickback",
 "app_version": "0.1.10", "device": "Pixel 7"}
```
```json
{"status": "SUCCESS", "event_id": "0x…"}
```
Errors: **400** schema; **411** no body; **413** > 8 KB; **500** store failure.

#### GET /api/bugs/list
5000; **loopback only**. Query: `limit` 1–200 (default 50). **From code, not live-tested.**
```json
{"status": "OK", "node_id": "609b…", "version": "8.17.0", "limit": 50, "count": 1, "has_more": false,
 "reports": [{"id": 7, "event_id": "0x…", "ts_ms": 1793334636472, "verified": true, "author_pubkey": "609b…",
              "report": {"what_happened": "Feed stays empty after posting", "schema": 1, "received_via": "remote_hub"}}]}
```
Errors: **400** for an unknown parameter or bad limit; **403** for non-loopback; **500** read failure.

### Sync / P2P ([CATCHUP_SYNC.md](CATCHUP_SYNC.md), [MESH_ID.md](MESH_ID.md), [SIGNED_EVENTS.md](SIGNED_EVENTS.md))

#### POST /api/sync/catchup
5000; **loopback only**. Body ignored. Runs a catch-up pass now and waits (up to 60 s for a running one).
**From code, not live-tested.**
```json
{"status": "OK", "at": 1793389400,
 "peers": [{"peer": "100.64.0.7:5005", "rounds": 2, "bytes": 1834, "need": 3, "have": 1, "stored": 3, "already": 0,
            "rejected": 0, "missing": 0, "pushed": 1, "push_failed": 0, "error": null, "duration_ms": 412}]}
```
If a run is already in progress after 60 s: `{"status": "SKIPPED", "message": "a catch-up run is already in progress"}`. Always 200
(per-peer failures go in `error`). **403** for non-loopback.

#### POST /p2p/sync
5005; header `X-Omni-Mesh: <mesh id>`. Body: a full signed event envelope, `Content-Length` only, ≤ 5 MB.
Stored events are relayed onward. **From code, not live-tested.**
```json
{"event_id": "0x…", "action": "KICKBACK_POST", "author_pubkey": "44ac…", "previous_hash": "0x…",
 "ts": 1793163300000, "payload": {"text": "hi"}, "signature": "…"}
```
```json
{"status": "SUCCESS", "event_id": "0x…", "merkle_hash": "0x…", "ts": 1793163300000}
```
Order of checks: mesh **403** (body unread), **413**, JSON / time fields / hash **400**, signature **401**, trusted-keys **403**.
Replays answer `"result": "ALREADY_EXISTS"`. Bad JSON comes back as an HTML `send_error` 400.

#### POST /p2p/reconcile
5005; mesh header + known peer. Content-Length required (≤ 5 MB, else **413**). Read-only, stateless. **From code, not live-tested.**
```json
{"negentropy": "6100…(hex negentropy v1 message)"}
```
```json
{"status": "OK", "negentropy": "6100…"}
```
Errors: **400** for a missing or bad message; **403** for mesh or unknown peer; **413**; **500**.

#### POST /p2p/events
5005; mesh header + known peer. Body `{"ids": [...]}` with at most 200 `0x` ids. The response is capped at about 4 MB
(`truncated: true`). **From code, not live-tested.**
```json
{"ids": ["0x5b1f…", "0x9e02…"]}
```
```json
{"status": "OK", "events": [{"event_id": "0x5b1f…", "action": "KICKBACK_POST", "author_pubkey": "44ac…",
  "previous_hash": "0x…", "ts": 1793163300000, "payload": {"text": "hi"}, "signature": "…"}], "truncated": false}
```
Errors: **400** for a bad body or more than 200 ids; **403**; **413**; **500**.

#### UDP discovery (9101)
Every few seconds each daemon broadcasts a JSON beacon to `<broadcast>:9101`, signed by its node key
(§3: `OMNI_BEACON_V1\n` prefix, `ts` within 60 s):
```json
{"type": "OMNI_P2P_BEACON", "node_id": "609b…", "mesh_id": "dev", "ip": "192.168.1.20", "port": 5005,
 "transport": "UDP_LAN", "ts": 1793389376000, "sig": "…"}
```
Listeners ignore beacons from other meshes. With an allowlist, beacons must come from a trusted key.
Unsigned (pre-8.9) beacons are accepted only with no allowlist and `OMNI_REQUIRE_SIGNED_BEACONS` off. Accepted senders
become `active_peers` (15 s freshness) for relay and catch-up. Beacons don't cross Tailscale; use `OMNI_SYNC_PEERS`
there. **From code, not live-tested.**

---

## 5. Not in the hub (v8.17.0)

None of these has an endpoint. Apps must not assume one exists.

- **Follows, blocks, DMs, notifications/mentions.** No social graph is stored; the contact list lives on the phone.
- **Subscriptions** (recurring transfers). Not built ([CREDITS_LEDGER.md](CREDITS_LEDGER.md)).
- **Real payments.** Credits are test-only with no cash value; nothing moves real money in or out.
- **Cross-node double-spend protection.** Each daemon's ledger is its own, so one signed transfer (or one welcome balance) can be
  spent on two hubs. Mitigation for now: point every phone's credits calls at one hub.
- **Key rotation / recovery.** There's no way to link a new key to an old profile, contacts or credits.
- **Attestation and anti-bot tiers 1, 2 and 4** (hardware attestation, sensor jitter, entropy). Only tier 3 exists (per-key rate limits).
  `SECURITY.md` describes the target, not the current daemon.
- Also not built: global handle uniqueness, comment edit/delete, avatar storage, moderation/slashing.
