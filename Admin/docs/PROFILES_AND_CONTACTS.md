# Profiles, contact cards, hub card and invite codes (daemon v8.13.0)

Gives apps a way to find out **who a key is** (handle, display name) and to **exchange keys** (QR
codes and short invite codes). OmniCast needs this to know whom to call; KickBack needs it to show names
instead of key prefixes.

## Person-signed events (the pattern every v8.13+ social write uses)

The phone signs; the hub verifies and stores. The event is the same canonical envelope the app already
signs for posts (`Admin/docs/SIGNED_EVENTS.md`):

```json
{"action": "profile_update", "author_pubkey": "<64 hex, the person's StargateIdentity key>",
 "previous_hash": "0x<64 hex: the author's previous event id, or 0x00…00>",
 "ts": 1793334636472, "payload": {...}, "signature": "<128 hex>", "event_id": "0x… (optional)"}
```

- `signature` = Ed25519 by `author_pubkey` over `canonical_event_bytes({action, author_pubkey, payload,
  previous_hash, ts})` (sorted keys, compact, int-ms `ts`) — exactly `StargateIdentity.sign(...)`.
- Stored **as signed**: `author_pubkey` is the person, not the hub. Peers receive it over `/p2p/sync`
  and catch-up like any peer event and re-verify it. The hub never signs on a person's behalf.
- Bad signature → 401; bad schema → 400; more than `OMNI_USER_RATE_MAX` (default 30) writes per key
  per minute → 429 (spec Module 1.2, tier 3); replay → `{"result": "ALREADY_EXISTS"}`.
- `POST /api/events/append` refuses these actions (403) so nothing skips the schema check.
- If `OMNI_TRUSTED_KEYS_FILE` is set, people's keys must be on it too (same as remote-hub posts).
- On read, every row is re-verified and schema-checked; anything invalid a peer relayed is ignored.

## Profiles

`POST /api/profile/update` — body: a signed event with `action: "profile_update"` and payload

| field | rule |
|---|---|
| `schema` | `1` (required) |
| `handle` | 3-20 chars `a-z 0-9 _` (required) |
| `display_name` | ≤ 48 chars, trimmed |
| `bio` | ≤ 280 chars, newlines allowed |
| `avatar` | ≤ 200 chars (a CID or URL; the hub does not fetch it) |
| `omnicast` | `true`/`false`: accepts OmniCast calls |

`GET /api/profile?pubkey=<hex>` → `{"status":"OK","profile":{pubkey, handle, handle_display,
display_name?, bio?, avatar?, omnicast?, updated_ts_ms, event_id, origin, verified}}`; 404 if the hub
has none. The latest **signed `ts`** wins, so a late-arriving older update never overwrites a newer one.

`GET /api/profile/list?q=<prefix>&limit=<1-200>` → newest-updated first; `q` matches the start of the
handle, display name or pubkey (a leading `@` is ignored).

**Handles are not unique.** There is no global registry (no consensus between hubs), so two people can
both pick `keith`. `handle_display` adds the first 4 hex of the key (`@keith.ab12`, the spec's
`@citizen.xxxx` form) and the pubkey is the real identity. Apps should show `handle_display` and pin
contacts by pubkey.

## Contact cards and QR codes

A card is signed by its own key (domain-separated by `type`):

```json
{"type": "omni.contact-card.v1", "pubkey": "<hex>", "handle": "keith_b",
 "display_name": "Keith", "hub": {"host": "100.101.102.103", "ipc_port": 5000},
 "ts": 1793334636472, "sig": "<128 hex>"}
```

- `sig` = Ed25519 over sorted-key compact JSON of every field except `sig`, raw UTF-8
  (`ensure_ascii=False`, i.e. Dart `jsonEncode` of a key-sorted map) — the same rule as OmniCast
  signaling. `display_name` and `hub` are optional. Cards older than a year are refused.
- QR text: `omni://contact?c=<base64url(card JSON), no padding>`.
- `POST /api/contacts/verify` with the card or `{"qr": "omni://contact?c=…"}` → `{"valid": true, card,
  handle_display, qr, profile}` (`profile` = what this hub knows about that key, or null), else 400.
  Phones can verify cards themselves; this endpoint is for apps that don't carry Ed25519 code.
- **The contact list stays on the phone.** The hub stores no social graph (a contact event in the log
  would be relayed to every peer).

## Hub card ("join this hub" QR)

`GET /api/hub/card` → node-signed `{"type": "omni.hub-card.v1", node_id, mesh_id, version, ipc_port,
telemetry_port, addresses, remote_hub, ts, sig}` plus `qr: "omni://hub?c=…"`. `sig` is by `node_id`
with the card rule above. The **bearer token is never in it**; testers still copy `~/.omni/hub_token`
separately. `addresses` = the listen hosts plus the Tailscale IP when one is found.

## Invite codes

`POST /api/invites/create` `{"card": <contact card signed in the last 10 min>, "ttl_s"?: 60-604800
(default 86400), "max_uses"?: 1-100 (default 1)}` → `{"code": "K7QM-3XWD", "expires_ms", "max_uses",
"qr": "omni://invite?code=K7QM-3XWD"}`. Max 20 live invites per key.

`GET /api/invites/redeem?code=K7QM-3XWD` (case and dash optional) → `{"card", "handle_display",
"uses_left", "expires_ms"}`; 404 unknown/expired/used up; 429 after 20 failed codes per client per
minute. Codes are 8 chars from a 31-letter alphabet without 0/O/1/I/L (~40 bits).

Invites live in an `invites` table next to `events` in `continuity_events.db`: not chain events, not
relayed, so a code only works on the hub that issued it. They survive restarts.

## Remote hub

All of these are allowed from other devices in remote hub mode with the bearer token
(`REMOTE_GET_PATHS` / `REMOTE_POST_PATHS`).

## Not built (honest list)

- Global handle uniqueness / name registry: needs cross-hub consensus. Deferred.
- Follows, blocks, DMs: not in the KickBack spec; not built.
- Avatars are a string only; the hub does not store or serve images (spec CAS/IPFS: not built).
- Key rotation / recovery (linking a new key to an old profile): not built.

## Tests

`tests/test_profiles_contacts.py` (15): profile schema unit tests, handle display, card signature + QR
round trip and forgery, rate limiter; live daemon: update/read with latest-ts-wins, stored with the
person as author, replay, forged/wrong-author 401, bad schema 400, `/api/events/append` 403, per-key
429, list + search; card verify + QR + forged + future-dated; hub card node signature and no token;
invite create/redeem/use-up/bad code/restart survival/brute-force 429; remote hub with token.
