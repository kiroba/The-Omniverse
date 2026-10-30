# Omni Credits TEST ledger (daemon v8.10.0; signed transfers v8.15.0)

Issue #29, first slice. **Test credits only: no cash value, not redeemable, not purchasable.**
This is a closed loop on one daemon. It is not yet safe for real value (see "Not done yet").

## How it works

- Every ledger entry is a chain event with action `credit_entry`, appended through the same
  `process_and_store_event` path as `/api/events/append`, signed with the node's Ed25519 key and not
  relayed on arrival (like bug reports).
- There is **no balance table**. Balances are derived by replaying this node's own `credit_entry`
  events in chain order. Each replay re-checks every entry's content hash (event_id), Ed25519 signature
  and schema. If any entry fails, every credits endpoint answers **409** with
  `"integrity": "FAILED"` and the bad `event_id`, rather than serving a balance built on a tampered entry.
- Only entries authored by this node's key count. `credit_entry` events that arrive from peers via
  sync/catch-up are stored like any event but ignored by the replay, so a peer cannot mint credits here.
- The generic `POST /api/events/append` refuses `action: credit_entry` (403), so entries can only be
  written through `/api/credits/*`, where the overdraft check runs.
- Replay + overdraft check + append run under one lock, so two concurrent transfers can't both spend
  the same balance on this daemon.

### Entry payload (signed)

```json
{"kind": "grant|transfer|purchase|reset", "from": "<64-hex pubkey>|treasury",
 "to": "<64-hex pubkey>|treasury", "amount": 400, "fee": 10, "memo": "sticker pack", "test_only": true}
```

- `amount`: integer credits, 1 to 1,000,000. Floats (even `10.0`), strings and booleans are rejected.
- `fee`: integer Treasury fee, set by the daemon (clients can't send it): `amount * OMNI_TREASURY_FEE_BPS // 10000`,
  rounded down. Default `OMNI_TREASURY_FEE_BPS=0` (no fee). The fee comes out of what the **recipient**
  gets (seller-side platform fee); the sender pays `amount`. No fee when `to` is `treasury`.
- `grant`: treasury → pubkey, issuance (does not debit the treasury).
- `reset`: a pubkey's whole balance → treasury (test resets).
- `treasury` balance = fees collected + credits sent to it.

### Welcome grant

Each pubkey gets **1,000 test credits once** (memo `welcome grant: 1,000 test credits, no cash value`),
issued the first time it is looked up (`GET balance`) or sends a transfer. It is never issued twice,
including after a reset. A pubkey that only *receives* credits gets its welcome grant at its first lookup.

## Endpoints (`:5000`)

| Method | Path | Access | Body / query | Answer |
|---|---|---|---|---|
| GET | `/api/credits/balance?pubkey=` | loopback, or remote hub + bearer (v8.15.0) | 64-hex pubkey or `treasury` | `{"balance", "fee_bps", "test_only": true, ...}` |
| GET | `/api/credits/history?pubkey=&limit=` | loopback, or remote hub + bearer (v8.15.0) | limit 1-200, default 50 | entries newest first with `delta`, `balance_after`, `event_id`, `ts_ms` |
| POST | `/api/credits/send` | loopback, or remote hub + bearer (v8.15.0) | transfer signed by `from` ([below](#signed-transfers-v8150)) | see [Signed transfers](#signed-transfers-v8150) |
| POST | `/api/credits/transfer` | **loopback only** | `{"from", "to", "amount", "memo"?, "kind"?: "transfer"\|"purchase"}` | `{"event_id", "entry", "balance"}`; 409 on overdraft |
| POST | `/api/credits/grant` (admin) | **loopback only** | `{"to", "amount", "memo"?}` or `{"kind": "reset", "pubkey", "memo"?}` | `{"event_id", "entry"}` |

Remote access needs `OMNI_HUB_REMOTE=1` and `Authorization: Bearer <token>` (see `REMOTE_GET_PATHS` /
`REMOTE_POST_PATHS` in the daemon). Errors: 400 bad input, 401 missing/invalid bearer (remote),
403 non-loopback on a loopback-only path, 409 overdraft or integrity failure, 411/413 missing/oversized
body (max 4 KB).

**Why `/transfer` and `/grant` stay loopback only, even in remote-hub mode** (this was the reason all of
`/api/credits/*` was loopback-only before v8.15.0): the remote-hub pattern (bearer token + the phone's own
signature on appends) authenticates the *device*, not the owner of the `from` pubkey. A transfer
needs proof that the `from` identity authorized it (a request signed by that pubkey), which the
daemon doesn't check on those two. So they are not in `REMOTE_POST_PATHS`, and any loopback process can
move test credits between any pubkeys with them. Phones use the signed `/api/credits/send` instead. That is acceptable for test
credits on a tester's own machine and not for anything else.

## Storefront wiring (not done in this PR)

The storefront (`apps/The-Omniverse/mobile/lib/kickback_storefront_mini_app_ui_v2.dart`) keeps its own
on-device SQLite `credits` column (seeded at 1000, 80/20 merchant/platform split shown in the UI).
`kickback_wallet_and_store_ui.dart` and `apps/KickBack-Social/mobile/lib/main.dart` show hard-coded
balances (1200, 3250). Pointing them at this ledger needs an HTTP client, the hub address setting and
the user's pubkey in those screens, so it's a follow-up:

1. Storefront v2: read `GET /api/credits/balance?pubkey=<identity>` instead of the local `credits`
   column; on buy, `POST /api/credits/transfer {"from": me, "to": merchant, "amount": price, "kind": "purchase"}`
   and show `entry.fee` as the platform fee (set `OMNI_TREASURY_FEE_BPS=2000` to match the UI's 20%).
2. Wallet screens: replace hard-coded balances with the balance endpoint; history tab from `/api/credits/history`.
3. Over the remote hub, use the signed `POST /api/credits/send` (v8.15.0) rather than `/transfer`.

## Signed transfers (v8.15.0)

`POST /api/credits/send` is the transfer phones use. The **owner of `from` signs it**, so the ledger
records who authorized each debit, and it is allowed over the remote hub (bearer token) as well as
loopback.

```json
{"type": "omni.credits.transfer.v1", "from": "<64 hex>", "to": "<64 hex>|treasury", "amount": 250,
 "kind": "transfer|purchase|tip", "memo": "for lunch", "ref": "0x<post id> (tip: required)",
 "nonce": "<16-64 lowercase hex, random per transfer>", "ts": 1793334636472, "sig": "<128 hex>"}
```

- `sig` = Ed25519 by `from` over sorted-key compact JSON of every field except `sig`, raw UTF-8
  (same rule as contact cards and OmniCast signaling). The fee is **not** signed: the hub sets it from
  `OMNI_TREASURY_FEE_BPS` as before. Pubkeys must be lowercase and `memo` trimmed, because they are
  signed as sent.
- `kind: "tip"` needs `ref` (what is tipped, e.g. a KickBack post id) and a pubkey recipient;
  `purchase` may carry `ref` (an item id). `ref`: 1-80 chars `A-Z a-z 0-9 _ . : -`.
- `ts` must be within **10 minutes** of the hub clock (401 otherwise); bad signature 401.
- The ledger entry stores `auth: {type, nonce, ts, sig}` (and `ref`) inside the node-signed
  `credit_entry`. **Every replay re-verifies that signature** against the entry's own from/to/amount/
  kind/memo/ref, so a hub bug or a DB edit that redirects or changes a signed transfer fails integrity
  (409) like any other tampering.

### Double-spend rules (node-local)

1. One ledger per daemon, one lock: replay → nonce check → balance check → append is a single critical
   section, so concurrent sends can't overspend (tested with 8 parallel sends).
2. `(from, nonce)` can be applied **once, ever** on this node. An identical retry (same signature)
   answers `200 {"result": "ALREADY_APPLIED", "event_id"}`, so clients can retry safely; the same nonce
   with different content answers **409**.
3. `amount` ≤ balance (welcome grant included), else 409.

### What this does NOT give you (cross-node)

Each daemon's ledger is its own (entries authored by other nodes are ignored on replay). The same signed
transfer, or two different transfers spending the same 1,000 welcome credits, can be applied on **two
different hubs**, because nothing makes hubs agree on one ordering of spends. Preventing that needs
either one designated ledger hub for a mesh (simplest: point every phone's credits calls at the Windows
hub) or real cross-node consensus / per-author chains with fork detection. **Deferred**: out of scope
while credits are test-only (issue #29).

### Balance lookups over the remote hub

`GET /api/credits/balance` from another device never writes: if the key's welcome grant hasn't been
issued yet it answers `"balance": 0, "welcome_pending": true, "available": 1000`. The grant is issued
on that key's first **signed** send (which proves the caller owns the key). Loopback lookups behave as
before (they issue it). `/api/credits/history` is also allowed remotely; `/transfer` and `/grant`
stay loopback only.

### Turning off unsigned transfers

`OMNI_CREDITS_REQUIRE_SIGNED=1` makes the old unsigned `POST /api/credits/transfer` answer 403 (point
callers at `/api/credits/send`). Default is off so existing tools keep working.

### Storefront / wallet wiring (app side, not in this PR)

Storefront buy = `POST /api/credits/send` with `kind: "purchase"`, `ref: <item id>`, `to: <merchant
key>`; wallet = `GET /api/credits/balance` (show `available`) + `/api/credits/history`; KickBack tip
button = `kind: "tip"`, `ref: <post id>`. The phone signs with its StargateIdentity key
(`signBytes`), exactly like OmniCast signaling requests.

## Not done yet (issue #29)

- Per-author chains + convergent sync, and double-spend protection across nodes (each daemon's ledger is its own).
- ~~Signed-by-owner transfers~~: done in v8.15.0 (`/api/credits/send`).
- Subscriptions as recurring transfers.
- Any real money in or out. The credit bundles in `kickback_gift_and_credit_engine.py` remain mock.
