# Catch-up sync (daemon v8.8.0)

Live relay (`relay_event_to_peers`) only reaches peers that are online when an event is created. A
node that was offline (laptop asleep, daemon restarted, Wi-Fi dropped) used to miss those events for
good. Catch-up sync fixes that: nodes compare their event sets with **range-based set
reconciliation** and fetch only the events they lack.

## How it works

1. Each node sees its stored events as a sorted set of items `(timestamp, id)`:
   - `id` = the 32-byte content hash behind the `0x<64 hex>` event id (the same hash `/p2p/sync`
     re-computes and checks; the mesh-ID work in PR #24 kept these ids and the signed bytes unchanged).
   - `timestamp` = the signed event time in **whole seconds** (`ts // 1000`, or the legacy float
     `timestamp` floored). Seconds rather than ms keep the format interoperable with the negentropy
     JS reference, which mishandles values above 2^32.
   - Only signed events with a well-formed hash id take part. Each node's own unsigned genesis row is
     left out.
2. The reconnecting node (client) sends fingerprints of 16 ranges covering its set to the peer's
   `POST :5005/p2p/reconcile`. The peer answers matching ranges with "skip" and splits mismatched ones
   into smaller fingerprinted ranges, down to explicit id lists below 32 items. A few round trips find
   exactly which ids each side lacks.
3. The client pulls the ids it lacks from `POST :5005/p2p/events` (200 ids per request). **Every fetched
   event goes through `process_and_store_event`, the same path as `/p2p/sync`:** content hash must equal
   the event id (400), Ed25519 signature must verify (401), author must be on the trusted-keys
   allowlist if one is configured (403). Unrequested or duplicate events in a response are dropped.
   Nothing is trusted because of where it came from.
4. Bidirectional: the client pushes the events the peer lacks to the peer's normal `POST /p2p/sync`,
   where the peer verifies them itself. Turn this off with `OMNI_CATCHUP_PUSH=0`.
5. Caught-up events are not re-relayed (`relay=False`): each peer reconciles for itself.

### When it runs

- At startup, after `OMNI_CATCHUP_STARTUP_DELAY` seconds (default 5). This is the reconnect case.
- When UDP discovery sees a same-mesh peer that is new or back after more than 15 s of silence.
- Every `OMNI_CATCHUP_INTERVAL` seconds (default 60; `0` turns the periodic run off).
- On demand: `POST http://127.0.0.1:5000/api/sync/catchup` (loopback only) runs a pass and returns
  per-peer stats. The last run's stats also appear as `catchup` in `GET :9100/api/v1/telemetry/node-health`.

### Peers

- Same-mesh peers found by UDP discovery (`OMNI_MESH_ID`, see [MESH_ID.md](MESH_ID.md)).
- Plus `OMNI_SYNC_PEERS`, a comma-separated list of `host[:port]` P2P endpoints (port defaults to
  5005), for peers that beacons don't reach, such as over Tailscale:
  `OMNI_SYNC_PEERS=100.64.0.7:5005,laptop.tail1234.ts.net`. A malformed entry stops the daemon with
  exit code 2 instead of being dropped silently.

## Access rules

| Endpoint | Who may call it |
|---|---|
| `POST :5005/p2p/reconcile` | needs `X-Omni-Mesh` (403 before reading the body, like `/p2p/sync`), and the caller must be loopback, a fresh same-mesh discovered peer, or a host in `OMNI_SYNC_PEERS` (403 otherwise). Read-only. |
| `POST :5005/p2p/events` | same as `/p2p/reconcile`. Read-only, max 200 ids per request, about 4 MB per response (`truncated: true` when cut short). |
| `POST :5000/api/sync/catchup` | loopback only. It is not in the remote-hub allowlist, so a remote caller gets 403 even with a bearer token. |

The catch-up endpoints serve events only to the hosts live relay already pushes every new event to.
No new path is open to unknown hosts, and the remote-hub bearer-token rules (`REMOTE_HUB.md`) are
unchanged. As with `/p2p/sync`, the mesh id is not a secret. Use `OMNI_TRUSTED_KEYS_FILE` in
production.

## Wire format: negentropy v1

`Admin/omni_negentropy.py` is a pure-Python implementation (standard library only) of the
[negentropy](https://github.com/hoytech/negentropy) protocol v1 by Doug Hoyte (MIT licence). It was
written from the published spec (`docs/negentropy-protocol-v1.md` in that repo), and no reference
code was copied:

- version byte `0x61`, MSB-first varints, bounds with delta-encoded timestamps and minimal id prefixes
- modes Skip (0) / Fingerprint (1) / IdList (2)
- fingerprint = first 16 bytes of SHA-256(sum of ids as little-endian 256-bit ints mod 2^256 || varint(count))
- 16 buckets per split, IdList below 32 items (same choices as the reference)

**Interop:** in the sandbox it was run against the JS reference implementation
(`js/Negentropy.js` through `test/js/harness.js`) in both directions, as client and as server, on
7 set shapes up to 5,000 items. Messages were byte-identical. `tests/test_negentropy.py` pins vectors
from that run and has an optional live interop test (`NEGENTROPY_JS_HARNESS=/path/to/harness.js`).
Not checked against the C++, Rust or Go implementations.

On top of the protocol, the HTTP wrapping is Omniverse-specific: JSON `{"negentropy": "<hex>"}` in
and out of `/p2p/reconcile`, then `/p2p/events` to fetch the bodies.

**Not implemented:** negentropy frame-size limits. Messages are unbounded and request bodies are
capped at 5 MB. In practice a split reply carries at most 16 fingerprints per mismatched range plus
id lists below 32 items each, so the full id list is only sent when a whole set is missing (about
32 bytes per event).

## Tests

- `tests/test_negentropy.py`: identical, empty, disjoint and partially overlapping sets, 1,000-event
  sets with few differences (at most 3 round trips), equal timestamps (prefix bounds), varints,
  reference vectors and malformed input.
- `tests/test_catchup_sync.py`: two live daemons on alternate ports (A 19100/15000/15005/19101,
  B 29100/25000/25005/29101) with `OMNI_SYNC_PEERS` pointing at each other:
  - Bidirectional catch-up.
  - B offline while A gets 50 events, then B comes back: B's set equals A's exactly and every event verifies.
  - Tampered rows planted on A are rejected by B: an edited payload (hash mismatch), a forged
    signature, and a valid event under a wrong id.
  - Access rules.

  Run with `NO_PROXY=127.0.0.1,localhost` set.
