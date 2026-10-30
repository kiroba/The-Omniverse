# App check-ins: consent, app versions, crash counts (daemon v8.16.0)

Feeds the Mesh Monitor tiles that said **"Not wired yet"**: consent acceptances, app versions in the
field, app crash / error rates (`mobile/lib/omni_mesh_telemetry.dart`, `kNotWiredUsers` /
`kNotWiredServices`).

## Endpoint

`POST :5000/api/telemetry/app-checkin` (loopback, or remote hub + bearer token). Body ≤ 4 KB:

```json
{"type": "omni.app-checkin.v1", "pubkey": "<the app's StargateIdentity key, 64 hex>",
 "app": "kickback", "app_version": "0.1.10", "platform": "android", "os_major": 15,
 "consent_version": "1", "consent_accepted": true,
 "crashes": {"count": 2, "last_kind": "StateError"},
 "ts": 1793334636472, "sig": "<128 hex>"}
```

| field | rule |
|---|---|
| `app` | 1-32 chars `a-z 0-9 _` (`kickback`, `superapp`, `mesh_monitor`, `phaser_studio`, `idle_plaza`, `omnicast`) |
| `app_version` | 1-32 chars `0-9 A-Z a-z . + -` |
| `platform` | `android` `windows` `ios` `linux` `macos` `web` |
| `os_major` | optional int 0-99 (Android 15 → 15) |
| `consent_version` | the first-launch agreement version the user saw, or `null` |
| `consent_accepted` | bool |
| `crashes` | optional: `count` 0-1000 = crashes **since the last check-in**; `last_kind` = exception **type name** only (`[A-Za-z0-9_.:]`, ≤ 64) |
| `ts` | int ms, within 10 min of the hub clock |
| `sig` | Ed25519 by `pubkey` over sorted-key compact JSON of every field except `sig` (raw UTF-8) |

Any other field (device model, name, IP, message, stack) is refused with 400. Answers: 200
`{"status": "OK", "install_id", "recorded": {"crashes": n}}`, 400 schema, 401 signature or ts, 429 more
than 2 check-ins per install+app per minute, 503 table full.

When to send: on app start (after the consent gate) and after a crash is caught by
`FlutterError.onError` / `PlatformDispatcher.onError` (count it locally, send the count + type with
the next check-in, then reset the counter).

## What the hub keeps (privacy)

- `install_id` = first 20 hex of `sha256("omni-checkin-v1:" + key bytes)`. The key itself, the
  signature and the IP are **not stored**. The id is stable per install so repeat check-ins update
  one row.
- `app_checkins`: one row per install + app (version, platform, os_major, consent, first/last seen).
  Rows not seen for **90 days** are deleted; at most 10,000 rows.
- `app_crashes`: daily UTC buckets of (app, app_version, kind) → count. Buckets older than **30 days**
  are deleted.
- Both are SQLite side tables in `continuity_events.db`, not chain events, never relayed to peers.

## In `/api/telemetry/summary`

`users.app_checkins`: `installs`, `active_24h`, `active_7d`, `consent: {accepted, not_accepted,
by_version}` (latest check-in per install), `app_versions: {app: {version: rows}}`, `platforms`
(rows per install+app), `basis`.

`services.app_crashes`: `last_24h` (today's UTC bucket), `last_7d`, `by_app`, `top_kinds` (top 10),
`basis`.

No pubkeys or prefixes appear in either part.

## App side (not in this PR)

Mesh Monitor: replace the three "Not wired yet" tiles with these fields. KickBack/Superapp: send the
check-in from `omni_consent_gate.dart` after acceptance and on each start; sign with
`StargateIdentity.signBytes`.

## Tests

`tests/test_app_telemetry.py` (5): install id ≠ key; validation (unknown fields like a device model,
crash messages instead of type names, out-of-range counts, wrong signer, stale ts); live: four
check-ins → exact summary aggregates with no key or key prefix in the JSON or in the DB dump; upsert
keeps one row per install+app; rate limit 429; forged/extra-field/future rejections.
