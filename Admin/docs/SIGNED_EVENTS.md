# Signed events: trusted keys and timestamps (daemon v8.5.1)

## Trusted-keys allowlist (peer sync :5005)

Order of checks on `POST /p2p/sync`:

1. Bad or missing Ed25519 signature: **401**.
2. Valid signature but the author key is not on the allowlist: **403**.
3. Otherwise the event is stored and relayed.

Set the allowlist with an env var pointing at a JSON file:

```bash
export OMNI_TRUSTED_KEYS_FILE=~/.omniverse/trusted_keys.json
```

```json
{"keys": ["03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8"]}
```

A plain list (`["<hex>", ...]`) works too. Keys are the 64-hex raw Ed25519 public keys (the node id /
`author_pubkey`), case-insensitive. The node's own key is always trusted.

- **Not set:** behaviour is unchanged (any validly signed event is accepted) and the daemon prints a
  warning at startup.
- **Set but missing or malformed:** the daemon refuses to start, so a typo never silently turns the
  allowlist off.
- The file is read once at startup; restart the daemon after editing it.

## Timestamps: `ts` (int ms) and legacy `timestamp` (float s)

The canonical signed struct carries exactly one time field:

| Form | Key | Example | Who sends it |
|---|---|---|---|
| New | `ts` | `1793042651190` (int, ms since epoch) | events the v8.5.1 daemon stamps itself |
| Legacy | `timestamp` | `1793042651.19` (float, seconds) | pre-8.5.1 daemons; the Dart `omni_core_ui` package today |

Both verify. The legacy struct is byte-for-byte unchanged, so existing event ids, signatures and the
Dart/Python interop vectors in `packages/omni_core_ui/test/interop_test.dart` still match.
An event that carries both keys, or a `ts` that is not a non-negative integer, gets **400**.

The daemon keeps the `timestamp` column (seconds, for ordering and display) and adds a `ts_ms`
column holding the exact signed integer (NULL for legacy events). Existing databases are migrated
with `ALTER TABLE` on startup.

### Mixed meshes

A pre-8.5.1 peer only understands `timestamp`, so int-ms events from an upgraded node would be
rejected (401) there. Until every peer is upgraded, run upgraded nodes with:

```bash
export OMNI_LEGACY_FLOAT_TS=1
```

### Dart follow-up (not in this change)

`omni_core_ui` still signs with `double timestamp` and does not yet understand `ts`. To move it over:
add an `int ts` variant of `eventStruct`/`canonicalEventId` that writes the `ts` key, and add a
Python-generated `ts` vector to `interop_test.dart`. Integer ms serialises identically in Dart and
Python, so it removes the float-repr edge cases `_pyFloat` has to handle.
