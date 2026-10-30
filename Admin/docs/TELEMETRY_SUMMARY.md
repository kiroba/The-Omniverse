# Telemetry summary (daemon v8.12.0)

`GET http://127.0.0.1:5000/api/telemetry/summary` returns one JSON document with aggregate counts for
the Mesh Monitor app. No query parameters (any parameter gets 400).

**Access:** same gate as the other hub endpoints. Loopback is always allowed. In remote hub mode
(`OMNI_HUB_REMOTE=1`) a non-loopback caller needs `Authorization: Bearer <~/.omni/hub_token>`; without it
the answer is 401 and the failure is counted. With remote hub off, :5000 only listens on 127.0.0.1.

**Privacy:** aggregates only. Never included: event payloads, signaling SDP/ICE contents, bug report
text, peer IP addresses, the hub token, the TURN secret, per-account credit balances, or any full
public key. Keys appear only as 12-character prefixes (this node, discovered beacon peers).

**Counters reset on restart.** Everything under "since start" lives in memory (`counters_since_ms`
says when it started). Store-wide numbers (event totals, identities, bug reports, credits) are read
from SQLite and cached for 5 s (`OMNI_TELEMETRY_CACHE_S`, max 60; tests use 0).

## Sections

| Section | Fields | Source |
|---|---|---|
| `protocols[]` | `id`, `name`, `state`, `last_seen_ago_s`, `counts`, plus per-protocol fields | see below |
| `security` | `events_stored_local_signed`, `events_verified_from_peers`, `events_rejected_signature` / `_untrusted` / `_invalid`, `events_duplicate`, `signal_sends_rejected` (+ `_by_status`), `signal_polls_rejected`, `beacons_rejected_signature`, `bearer_auth_failures`, `remote_denied_loopback_only`, `trusted_keys_allowlist` (count or null = off), `hub_token_age_s` (remote mode only), `unsigned_rows_in_store` | since-start counters; allowlist/token from config; unsigned rows from SQLite |
| `finance` | `state`, `integrity`, `entries`, `accounts`, `welcome_grants`, `total_issued`, `total_transferred`, `fees_collected`, `entries_by_kind`, `treasury_fee_bps`, `test_only` | replay of the TEST credits ledger (hash + signature re-checked, like `/api/credits/*`) |
| `users` | `identities_seen`, `active_24h`, `active_7d`, `new_7d`, `bug_reports`, `basis` | distinct signing pubkeys in stored events (author, or `payload.app_author_pubkey` for local app posts), this node excluded; activity by signed event time |
| `services` | `daemon_version`, `uptime_seconds`, `node_id_prefix`, `mesh_id`, `event_store` (`total_events`, `db_bytes`, `last_event_ago_s`, `events_by_action` top 20), `omnimind_agent` | process + SQLite |

Protocol ids: `tcp_api` (:9100/:5000, listen hosts, remote hub on/off), `p2p_sync` (:5005 `/p2p/sync`,
peer events stored, relay ok/failed, mesh rejects), `udp_discovery` (:9101 listener state, beacons
sent/accepted/rejected, active peers + pubkey prefixes), `negentropy` (last catch-up run totals,
static peers, reconcile requests served; `idle` until a run happens), `signaling` (mailbox queued /
recipients, sends ok/rejected, polls, deliveries), `turn` (`configured` yes/no only).

## Not reported (nothing in the daemon produces it yet)

- Consent: the first-launch agreement is stored only on the phone (`omni_consent_gate.dart`), so the
  hub cannot count acceptances.
- Subscriptions, cash payments, payouts: not built. Credits are test-only and closed-loop.
- GossipSub, BLE discovery, NAT hole punching, WebRTC media: modules exist under `Admin/` but are not
  wired into this daemon, so they have no telemetry.
- Hardware attestation: not built.

## What is and isn't verified (v8.12.0)

- `tests/test_telemetry_summary.py` starts real daemons on temp ports and checks every counter it
  can drive locally (local/peer/duplicate/forged events, mesh rejects, signal accept/reject, bug
  report count, credits totals with a 250 bps fee, TURN flag, bearer 401 counting, remote-off bind),
  and that full keys, payload text, SDP text, the token and the TURN secret never appear in the JSON.
- Beacon counters and catch-up run totals are wired but not exercised by this test (UDP broadcast and
  two-node catch-up are covered by their own tests, not re-checked through the summary).
