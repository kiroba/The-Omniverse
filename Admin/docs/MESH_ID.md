# Mesh ID: keeping dev and production meshes apart (daemon v8.5.1)

`OMNI_MESH_ID` names the mesh a daemon belongs to. Nodes only discover and sync with nodes on the
same mesh, so a laptop running a dev daemon on the same Wi-Fi as a production node can't join it by
accident. It is defense in depth next to the trusted-keys allowlist (`OMNI_TRUSTED_KEYS_FILE`, see
[SIGNED_EVENTS.md](SIGNED_EVENTS.md)); it is **not** an authentication mechanism on its own, since the
name is sent in clear text and anyone who knows it can send it.

## Setting it

```bash
export OMNI_MESH_ID=prod          # default when unset or empty: dev
```

- Allowed: 1 to 32 characters of `a-z`, `0-9` and `-` (lowercase only).
- Anything else (for example `Prod`, `prod_1`, or 33+ characters): the daemon prints
  `[x] FATAL: OMNI_MESH_ID=... is invalid` and exits with code 2. It never falls back to `dev`
  silently.
- Printed at startup (`Mesh ID (OMNI_MESH_ID): ...`) and reported as `mesh_id` in
  `GET :9100/api/v1/telemetry/node-health`.

## What it changes on the wire

| Where | Behaviour |
|---|---|
| UDP discovery beacon (:9101) | carries `"mesh_id": "<id>"`. The listener ignores beacons whose `mesh_id` differs or is missing: the sender is not added to `active_peers` (and is dropped if it was there). |
| `POST /p2p/sync` (:5005) | requires header `X-Omni-Mesh: <id>`. A missing or different value gets **403** before the body is parsed, verified or stored. |
| Relay (`relay_event_to_peers`) | sends `X-Omni-Mesh` with this node's mesh id. |

Order of checks on `POST /p2p/sync`: mesh header (403), payload size (413), JSON / time fields (400),
signature (401), trusted-keys allowlist (403), then store and relay.

Rejected peers are logged once per (peer IP, foreign mesh id), so a neighbour on another mesh does
not flood the log every 3 seconds.

The mesh id is **not** part of the signed canonical event. Event ids, signatures and the Dart/Python
interop vectors in `packages/omni_core_ui/test/interop_test.dart` are unchanged.

## Recommended production setup

```bash
export OMNI_MESH_ID=prod
export OMNI_TRUSTED_KEYS_FILE=~/.omniverse/trusted_keys.json   # {"keys": ["<64-hex node id>", ...]}
python3 Admin/omni_live_daemon_server.py
```

Keep developer machines on the default `dev` (or a per-developer name such as `dev-keith`).

## Upgrading

Older daemons (before this change) send no `mesh_id` and no `X-Omni-Mesh` header, so an upgraded
node ignores their beacons and answers their sync requests with 403. Upgrade every node on a mesh
together. Tools that post to `/p2p/sync` by hand (for example `tests/two_node_check.py`) must send
the header; that script reads `OMNI_MESH_ID` (default `dev`).
