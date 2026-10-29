# Omni Credits TEST ledger (daemon v8.10.0)

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

## Endpoints (`:5000`, loopback only)

| Method | Path | Body / query | Answer |
|---|---|---|---|
| GET | `/api/credits/balance?pubkey=` | 64-hex pubkey or `treasury` | `{"balance", "fee_bps", "test_only": true, ...}` |
| GET | `/api/credits/history?pubkey=&limit=` | limit 1-200, default 50 | entries newest first with `delta`, `balance_after`, `event_id`, `ts_ms` |
| POST | `/api/credits/transfer` | `{"from", "to", "amount", "memo"?, "kind"?: "transfer"\|"purchase"}` | `{"event_id", "entry", "balance"}`; 409 on overdraft |
| POST | `/api/credits/grant` (admin) | `{"to", "amount", "memo"?}` or `{"kind": "reset", "pubkey", "memo"?}` | `{"event_id", "entry"}` |

Errors: 400 bad input, 403 non-loopback, 409 overdraft or integrity failure, 411/413 missing/oversized body (max 4 KB).

**Why loopback only, even in remote-hub mode:** the remote-hub pattern (bearer token + the phone's own
signature on appends) authenticates the *device*, not the owner of the `from` pubkey. A transfer
needs proof that the `from` identity authorized it (a request signed by that pubkey), which the
daemon doesn't check yet. So `/api/credits/*` is not in `REMOTE_GET_PATHS`/`REMOTE_POST_PATHS`, and any
loopback process can currently move test credits between any pubkeys. That is acceptable for test
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
3. Before phones use it over the remote hub: signed transfer requests from the `from` key, then add the
   paths to the remote allow-list.

## Not done yet (issue #29)

- Per-author chains + convergent sync, and double-spend protection across nodes (each daemon's ledger is its own).
- Signed-by-owner transfers (see above).
- Subscriptions as recurring transfers.
- Any real money in or out. The credit bundles in `kickback_gift_and_credit_engine.py` remain mock.
