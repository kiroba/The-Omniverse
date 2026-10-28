# Event feed: `GET :5000/api/events/feed` (daemon v8.6.0)

A paginated, newest-first list of the events this node has stored: the ones local apps appended
(`POST :5000/api/events/append`) **and** the ones received from peers over `POST :5005/p2p/sync`.
This is what lets an app (KickBack) show other people's posts. Before v8.6.0 there was no listing
endpoint: `/api/events/list` returns only counts (it still does, unchanged).

## Access

- Served by the local IPC gateway, which binds `127.0.0.1` only, like every other `:5000` route.
  The handler also refuses any non-loopback client with 403, in case `IPC_HOST` is ever rebound.
- No bearer token (none of the IPC routes check one today). Anything running on the same phone can
  read the feed. Peers on the LAN cannot: they only reach `:5005`.
- Read-only. Never relays, never writes.

## Request

```
GET http://127.0.0.1:5000/api/events/feed?limit=50&before=<id>&since=<id>&type=<action>
```

| Param | Meaning |
|---|---|
| `limit` | Page size. Default 50, clamped to 1..200 (asking for more returns 200; the applied value is echoed as `limit`). |
| `before` | Cursor for the next (older) page: only rows with `id < before`. Use `next_before` from the previous page. |
| `since` | Polling: only rows with `id > since`. Use `latest_id` from the previous response. |
| `type` | Optional action filter, e.g. `KICKBACK_POST`. 1-64 chars of `A-Z a-z 0-9 _ . : -`. |

Any other parameter, a non-integer cursor, or a bad `type` gets **400** `{"status":"ERROR","message":...}`.

The cursor is the SQLite row `id`, i.e. **arrival order on this node**, not the signed time. A peer
event that arrives late with an older `ts` still shows up at the top of the next poll, and the
cursor never skips or repeats a row while new events arrive. Apps sort by `ts_ms` for display.

## Response

```json
{
  "status": "OK",
  "node_id": "<this node's Ed25519 pubkey>",
  "mesh_id": "dev",
  "version": "8.6.0",
  "limit": 50,
  "count": 2,
  "has_more": false,
  "next_before": null,
  "latest_id": 4,
  "events": [
    {
      "id": 4,
      "event_id": "0x296d…",
      "type": "KICKBACK_POST",
      "action": "KICKBACK_POST",
      "author_pubkey": "44ac…",
      "origin": "remote",
      "ts": 1793163300000,
      "ts_ms": 1793163300000,
      "payload": {
        "text": "hi from phone B",
        "app": "kickback",
        "app_event_id": "0x05e3…",
        "app_author_pubkey": "5383…",
        "app_signature": "abc2…",
        "app_previous_hash": "0x0000…",
        "app_ts": 1793163300000
      },
      "previous_hash": "0x4444…",
      "signature": "2d28…",
      "verified": true
    }
  ]
}
```

- `ts` **or** `timestamp`: exactly the time field that was signed (int ms for v8.5.1+ events, float
  seconds for legacy ones), so `{action, author_pubkey, payload, previous_hash, ts|timestamp, signature}`
  re-verifies with `omni_signing.verify_event` / Dart `StargateIdentity.verify` as-is.
- `ts_ms`: always present, for sorting/display (derived from `timestamp` for legacy rows).
- `author_pubkey`: the node that signed the event (the daemon re-signs local app posts as itself).
- `origin`: `local` when `author_pubkey` is this node, otherwise `remote` (came in over `/p2p/sync`).
- `payload`: stored as-is, including the `app_*` fields: the app's own signed envelope, which anyone
  can re-verify against the app key (`app_author_pubkey`). Strip the six `app_*` keys to get the
  payload the app signed.
- `verified`: the daemon re-checks the node signature at read time. `false` for the unsigned genesis
  row, for legacy unsigned rows, and for any row edited in the DB after it was stored.
- `has_more` / `next_before`: `next_before` is set only when there is an older page.
- Empty or missing DB: `200` with `events: []`, `latest_id: 0`.

## Examples

```bash
curl -s "http://127.0.0.1:5000/api/events/feed?limit=20&type=KICKBACK_POST" | python3 -m json.tool
curl -s "http://127.0.0.1:5000/api/events/feed?limit=20&before=120"          # next page
curl -s "http://127.0.0.1:5000/api/events/feed?since=140"                    # only new rows
```

## Compatibility

- Older daemons (< 8.6.0) answer **404** on this path. Apps must treat 404 as "daemon too old for the
  shared feed" and keep showing their local feed (KickBack does).
- No schema change, no change to signing, event ids, `/p2p/sync` or the Dart/Python interop vectors.

## Tests

`python -m unittest tests/test_events_feed.py -v` (no daemon needed): newest-first + fields, cursor
pagination walks every row once, `since` polling, limit cap 200 / default 50, `type` filter, 400s,
empty DB (no file and empty table), a remote event posted via `/p2p/sync` is listed with
`origin: remote`, `verified: true` and its `app_*` envelope re-verifying, tampered row reads
`verified: false`, legacy float-timestamp rows, and the old `/api/events/list` unchanged.
