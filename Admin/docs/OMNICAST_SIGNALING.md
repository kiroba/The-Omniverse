# OmniCast signaling mailbox + hub TURN relay (daemon v8.11.0)

OmniCast calls are WebRTC. Before two phones can send audio/video they must swap an SDP **offer**,
an SDP **answer** and a few **ICE candidates**. Remote testers reach the hub over **Tailscale node
sharing**, so each phone can reach the hub but **not each other**. This PR gives them:

1. **A signaling mailbox on the hub daemon** (`:5000`). Phone A drops a signed message in phone B's
   mailbox; phone B picks it up with a signed poll. Messages live in memory only, for at most 60 s.
2. **`GET /api/signal/ice-config`**, which hands each phone the STUN/TURN servers plus a
   **time-limited TURN credential**, so media can relay through a **TURN server on the hub**.

Step 1 only: no Dart client, no OmniCast APK, no `flutter_webrtc` calls yet (later PRs).

## Trust model (short)

- **Same gate as the other hub endpoints.** Loopback: open. Non-loopback: only with remote hub mode
  on (`OMNI_HUB_REMOTE=1`) and `Authorization: Bearer <~/.omni/hub_token>`; otherwise 403/401.
  See [REMOTE_HUB.md](REMOTE_HUB.md).
- **Every message is Ed25519-signed by its sender** (`from`) over the canonical fields below. The hub
  checks it, and also hands the signature to the recipient, so the **recipient re-verifies it itself**.
  The hub can read an SDP but can't change one (e.g. swap the DTLS fingerprint) without breaking the
  signature. Media is DTLS-SRTP end to end; the TURN relay only sees encrypted packets.
- **Only the key owner can drain a mailbox.** A poll is signed by the recipient's key.
- **Replay guard.** `ts` must be within **±120 s** of the hub clock, and each signature is accepted
  **once** (409 on reuse). Ed25519 signatures are deterministic, so **use a fresh millisecond `ts` for
  every request**.
- **Nothing is persisted or logged.** Not in the event log, not in SQLite, not relayed to peers, not
  printed. A daemon restart empties every mailbox.
- **TURN secret never leaves the hub.** Clients get `username`/`credential` derived from it, valid ~1 h.

## Limits

| Limit | Value |
|---|---|
| POST body | 16 KB (413 above) |
| `payload` string | 14 KB = 14,336 chars (413 above) |
| Queued per recipient | 64 (429 "recipient mailbox full") |
| Queued in total | 4,096 (503) |
| Message lifetime | 60 s undelivered (`OMNI_SIGNAL_TTL`, 1–300 s; tests use 3 s) |
| `ts` window | ±120 s |
| Per-sender rate | token bucket: burst 40, refill 10/s (429 "rate limited") |
| Long-poll | `wait` up to 25 s; at most 64 concurrent long-polls (extra polls return at once) |

## Signing (exact bytes)

All signatures are Ed25519, hex (128 chars), over **compact JSON with sorted keys, raw UTF-8**
(`json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`). Keys are 64-char lowercase hex
raw Ed25519 public keys (the same `author_pubkey` format as signed events). `ts` is an **integer,
milliseconds since the Unix epoch**.

| Request | Object that is signed |
|---|---|
| send | `{"call_id":…,"from":…,"kind":…,"payload":…,"to":…,"ts":…,"type":"omnicast.signal.v1"}` |
| poll | `{"to":<your pubkey>,"ts":…,"type":"omnicast.poll.v1"}` |
| ice-config | `{"pubkey":<your pubkey>,"ts":…,"type":"omnicast.ice-config.v1"}` |

The `type` field is domain separation: a poll signature can't be replayed as an ice-config request
or a message, and vice versa.

Python reference (the test suite uses exactly this):
```python
def send_bytes(m):
    return json.dumps({"type": "omnicast.signal.v1", "to": m["to"], "from": m["from"],
                       "call_id": m["call_id"], "kind": m["kind"], "payload": m["payload"],
                       "ts": m["ts"]}, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")
```
Dart note for the client PR: build the map with the keys **in sorted order** and
`utf8.encode(jsonEncode(map))`. Dart's encoder emits no spaces, keeps insertion order and writes
non-ASCII as raw UTF-8, which is why the daemon uses `ensure_ascii=False` here (unlike the older
signed-event canonical form). `ts` must be an `int`, never a `double`. Add a shared test vector in the
client PR before relying on it.

## API reference

### `POST /api/signal/send`
Body (exactly these fields; unknown or missing fields are 400):
```json
{
  "to": "<recipient pubkey hex, 64>",
  "from": "<sender pubkey hex, 64>",
  "call_id": "call-7f3a",
  "kind": "offer",
  "payload": "v=0\r\no=- 46117 2 IN IP4 127.0.0.1\r\n...",
  "ts": 1793042651190,
  "sig": "<Ed25519 by from, hex 128>"
}
```
- `call_id`: 1–64 chars of `A-Z a-z 0-9 _ . : -` (pick a random one per call).
- `kind`: `offer` | `answer` | `ice` | `hangup` | `ring`.
- `payload`: a string. SDP for offer/answer, the candidate as a JSON string for `ice`
  (`{"candidate":…,"sdpMid":…,"sdpMLineIndex":…}`), may be `""` for `ring`/`hangup`.

`200 {"status":"QUEUED","seq":42,"expires_in":60}`

Errors: 400 bad field/JSON, 401 bad signature or `ts` outside ±120 s, 409 replay, 411 no
Content-Length, 413 too big, 429 rate limit / mailbox full, 503 hub full, plus the remote gate's 401/403.

### `GET /api/signal/poll?to=<pubkey>&ts=<ms>&sig=<hex>[&since=<cursor>][&wait=<0-25>]`
Returns **and removes** every queued message for `to`. Messages with `seq <= since` are dropped as
already received (pass the last `cursor` you got, so a lost response doesn't redeliver forever).
With `wait=N` and nothing queued, the request is held up to N seconds (max 25) and returns as soon as
a message arrives.
```json
{"status":"OK","count":1,"cursor":42,
 "messages":[{"seq":42,"from":"…","to":"…","call_id":"call-7f3a","kind":"offer",
              "payload":"v=0…","ts":1793042651190,"sig":"…"}]}
```
**Verify `sig` over `send_bytes(message)` with `from` before using a message.** Delivery is
at-most-once: a message is removed when it is handed out, so a response lost in transit is lost
(the caller re-sends the offer, or the call times out).

Errors: 400 missing/duplicate/unknown parameter, 401 bad signature / stale `ts`, 409 replay.

### `GET /api/signal/ice-config?pubkey=<pubkey>&ts=<ms>&sig=<hex>`
```json
{"status":"OK","turn":true,"ttl":3600,"expires_at":1793046251,"ice_transport_policy":"relay",
 "ice_servers":[
   {"urls":["stun:stun.l.google.com:19302"]},
   {"urls":["turn:100.101.102.103:3478?transport=udp","turn:100.101.102.103:3478?transport=tcp"],
    "username":"1793046251:<pubkey>","credential":"<base64>"}]}
```
- Credential = TURN REST API scheme (coturn `use-auth-secret`, eturnal `secret`,
  draft-uberti-behave-turn-rest-00): `username = "<unix expiry>:<pubkey>"`,
  `credential = base64(HMAC-SHA1(OMNI_TURN_SECRET, username))`.
- `ice_transport_policy: "relay"` is a hint: with TURN configured, testers can only reach the hub, so
  the client should set `iceTransportPolicy: 'relay'`. Without TURN it is `"all"`.
- Fetch a fresh config before each call (the credential lasts `ttl` seconds; with eturnal's default
  `strict_expiry: false` a call that started in time keeps working after expiry).

| Env (daemon) | Meaning |
|---|---|
| `OMNI_TURN_URLS` | Comma-separated `turn:`/`turns:` URLs. Unset = STUN only. |
| `OMNI_TURN_SECRET` | Same string as the TURN server's shared secret. If URLs are set but this isn't, TURN is off and the response carries a `warning`. |
| `OMNI_TURN_TTL` | Credential lifetime in seconds, default 3600 (60–86400). |
| `OMNI_STUN_URLS` | Optional STUN override. Default `stun:stun.l.google.com:19302`. |

### Call flow (what the Dart client PR will do)
1. Both phones keep a loop: `GET /api/signal/poll?...&since=<cursor>&wait=25`, fresh `ts` each time.
2. Caller: `ice-config` → create `RTCPeerConnection` (relay policy) → `ring` (optional) → `offer`.
3. Callee: verify, `ice-config`, set remote description, `answer`.
4. Both: trickle each local candidate as `ice`; `hangup` ends it. Unanswered calls die after 60 s.

## Hub relay: TURN server on Keith's Windows PC

### Choice: **eturnal** (native Windows installer, free)

| | eturnal | pion/turn | coturn |
|---|---|---|---|
| Runs natively on Windows | **Yes**: official x64 installer, runs as a Windows service | Go library; the `examples/turn-server/*` programs have no prebuilt binaries (needs the Go toolchain to build) | No Windows binaries; normally Docker Desktop or WSL2 |
| Shared-secret (REST) auth | **Yes** (`secret`) | Yes (`lt-cred-turn-rest` example) | Yes (`use-auth-secret`) |
| Maintained | 1.12.3, Sep 17 2026 | v5.1.3, Oct 24 2026 (library) | 4.18.0 (Docker), Sep 2026 |
| Cost | $0, Apache-2.0 | $0, MIT | $0, BSD |

Why eturnal: it's the only one that is a finished, installable server on Windows, it implements the
same TURN REST credential scheme the daemon mints, and it runs as a service (survives reboots, no
console window). pion would mean building and babysitting example code; coturn under Docker/WSL2 adds
a NAT layer between the relay ports and the Tailscale interface, which is exactly where TURN breaks.

Sources: https://eturnal.net/windows/ (installer, config at `C:\Program Files\eturnal\etc\eturnal.yml`),
https://eturnal.net/download/windows/ (`eturnal-1.12.3-x64.exe`), https://eturnal.net/doc/ (options),
https://github.com/processone/eturnal/blob/master/src/eturnal.erl (`username = expiry:suffix`,
`base64(HMAC-SHA1)`), https://github.com/processone/eturnal/blob/master/src/eturnal_yaml.erl
(default peer blacklist), https://github.com/pion/turn/tree/master/examples,
https://github.com/coturn/coturn.

### Important Tailscale gotcha
eturnal's default `blacklist_peers: recommended` **blocks `100.64.0.0/10`**, which is the Tailscale
address range. When both phones relay through the hub, each phone's peer address is the hub's own
Tailscale IP, so relaying would be refused. The config below whitelists **only the hub's own
Tailscale IP** (`/32`), so the relay still can't be used to reach other devices on the tailnet.

### Setup (PowerShell as Administrator; replace `100.101.102.103` with the hub PC's Tailscale IP)

1. **Tailscale IP**: `tailscale ip -4` (or the Tailscale tray icon).
2. **Install eturnal**: download `eturnal-1.12.3-x64.exe` from https://eturnal.net/download/windows/
   and run it. It installs to `C:\Program Files\eturnal` and starts a Windows service.
3. **Make a secret** (Python is already on the hub):
   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
4. **Edit `C:\Program Files\eturnal\etc\eturnal.yml`** (YAML: spaces, not tabs) to:
   ```yaml
   eturnal:
     secret: "PASTE-THE-SECRET-HERE"

     listen:
       - ip: "100.101.102.103"     # hub's Tailscale IP only: not reachable from the LAN/internet
         port: 3478
         transport: udp
       - ip: "100.101.102.103"
         port: 3478
         transport: tcp

     relay_ipv4_addr: "100.101.102.103"
     relay_ipv6_addr: none
     relay_min_port: 49160         # small range: ~2 ports per call, so ~20 calls at once
     relay_max_port: 49200

     blacklist_peers:
       - recommended               # keeps loopback, LAN and the rest of the tailnet blocked ...
     whitelist_peers:
       - "100.101.102.103"         # ... except the hub itself (relay-to-relay between two phones)

     strict_expiry: false
     log_level: notice             # no per-packet logs
     modules: {}
   ```
5. **Firewall: open the ports on the Tailscale interface only**:
   ```powershell
   New-NetFirewallRule -DisplayName "eturnal TURN UDP" -Direction Inbound -Protocol UDP -LocalPort 3478,49160-49200 -InterfaceAlias Tailscale -Action Allow
   New-NetFirewallRule -DisplayName "eturnal TURN TCP" -Direction Inbound -Protocol TCP -LocalPort 3478 -InterfaceAlias Tailscale -Action Allow
   ```
   **Tailnet policy:** if you locked shared-in testers to ports 5000/9100 (step 4 of
   [TESTER_GUIDE.md](TESTER_GUIDE.md)), add the TURN ports for them too, or their phones can't reach
   the relay (signaling itself uses port 5000, which is already allowed):
   ```jsonc
   { "src": ["autogroup:shared"], "dst": ["omni-hub"], "ip": ["udp:3478", "tcp:3478", "udp:49160-49200"] }
   ```
   (`dst` must match the hub name/tag you used in that policy.)
6. **Restart eturnal**: `Get-Service *eturnal* | Restart-Service`. Logs:
   `C:\Program Files\eturnal\log`. It should log `Relay IPv4 address: 100.101.102.103 (port range: 49160-49200)`.
7. **Start the daemon with TURN** (same PowerShell window as the other hub settings):
   ```powershell
   $env:PYTHONUTF8 = "1"
   $env:OMNI_HUB_REMOTE = "1"
   $env:OMNI_HUB_BIND = "100.101.102.103"
   $env:OMNI_TURN_URLS = "turn:100.101.102.103:3478?transport=udp,turn:100.101.102.103:3478?transport=tcp"
   $env:OMNI_TURN_SECRET = "PASTE-THE-SAME-SECRET-HERE"
   python Admin\omni_live_daemon_server.py
   ```
   The banner shows `OmniCast signaling: ... ICE: STUN + TURN`.
8. **Check the relay** from any device on the tailnet: get a config from `ice-config` (signed request),
   open https://webrtc.github.io/samples/src/content/peerconnection/trickle-ice/, enter the TURN URL,
   username and credential, and click *Gather candidates*. A candidate of type **`relay`** with
   address `100.101.102.103` means TURN works. `401`/no relay candidate: the secrets differ or the
   clock is off.

If the eturnal service starts before Tailscale at boot, binding to the 100.x IP fails; restart the
service once Tailscale is up (or set the service's startup type to *Automatic (Delayed Start)*).

### Costs
**$0.** eturnal is free and open source (Apache-2.0), Tailscale's Personal plan is free, the default
STUN server is Google's free public one, and nothing is hosted in the cloud. The only "cost" is the
hub PC's home bandwidth: each relayed call crosses it twice (in from one phone, out to the other), on
the order of 0.1 Mbps for audio and 0.5–2 Mbps per video direction. If Tailscale can't make a direct
connection to a phone, that traffic also goes through Tailscale's free DERP relays (slower, still $0).

## What is and isn't verified (v8.11.0)
- Verified in the sandbox (Linux, Python 3.12): `tests/test_signal_mailbox.py` (17 tests: signature
  rejection, replay + stale/future ts, size caps, per-recipient cap, per-sender rate limit, expiry,
  poll auth, delivery-once, `since`, non-ASCII payloads, long-poll wake-up, never in the event log or daemon log,
  ice-config STUN-only and TURN credential format, remote bearer gate, loopback-only when hub mode is off).
- **Not verified**: eturnal on Windows, relay-to-relay through one eturnal on a Tailscale IP, any
  phone or real WebRTC call, the 4,096 global cap (by design, too slow to fill in a unit test).
- `Admin/omni_webrtc_signaling_bridge.py` is older scaffolding (its "signature" is a SHA-256 hash, not
  Ed25519) and is **not** used by these endpoints.
