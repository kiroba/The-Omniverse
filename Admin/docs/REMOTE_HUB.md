# Remote hub: one phone runs the daemon, another phone's KickBack uses it (daemon v8.7.0)

By default the daemon's app ports only listen on the phone itself (`127.0.0.1`), so KickBack has to
run on the same phone as the daemon. Remote hub mode lets **phone A** run the daemon in Termux and
**phone B** use it over the internet through **Tailscale** (free personal plan). Nothing changes
unless you turn it on.

Remote testers with their own Tailscale accounts: see [TESTER_GUIDE.md](TESTER_GUIDE.md).

## What it does

| Setting | Meaning |
|---|---|
| `OMNI_HUB_REMOTE=1` | Turn remote hub mode on. Unset = off (exactly the old behavior). |
| `OMNI_HUB_BIND=<ip>` | Where the app ports also listen: phone A's Tailscale address (`100.x.y.z`), or `0.0.0.0` for every network. Default `127.0.0.1`. |
| `OMNI_HUB_TOKEN_FILE` | Optional. Where the token lives. Default `~/.omni/hub_token`. |

With it on, these endpoints are also reachable from other devices (ports unchanged):

- `GET :5000/api/events/feed`, `GET :5000/api/events/stats` (and `/api/events/list`)
- `POST :5000/api/events/append` (post submit)
- `GET :9100/api/v1/telemetry/node-health`

Rules:

- **Every request that does not come from phone A itself needs `Authorization: Bearer <token>`.**
  No token or a wrong token gets **401**. Other paths (like the OmniMind agent cache) stay
  phone-A-only and answer **403**. Requests from phone A itself work as before, no token.
- The token is made once, saved to `~/.omni/hub_token` (only you can read it: `chmod 600` on Linux/macOS, an owner-only
  `icacls` ACL on Windows, re-applied on every start), and
  printed when the daemon starts. It stays the same across restarts. To change it, delete the file
  and restart the daemon; then type the new one into phone B.
- On Windows (v8.8.1+) the daemon forces UTF-8 output, so redirecting it to a file no longer needs
  `PYTHONUTF8=1`, and a second daemon on the same PC exits with "Port ... is already in use".
- **Phone B's posts keep phone B's own signature.** KickBack signs each post with its own key; the
  daemon checks that signature (the same check it does for posts from other nodes) and stores the
  post with phone B as the author. It never signs on phone B's behalf. An unsigned post gets 400,
  a tampered one 401. If you use `OMNI_TRUSTED_KEYS_FILE`, add phone B's KickBack key to it, or its
  posts get 403.

## Set up (plain steps)

### Both phones
1. Install **Tailscale** from the Play Store.
2. Open it and sign in with **the same account** on both phones (Google is fine). Allow the VPN
   prompt. Leave Tailscale switched on.
3. On phone A, Tailscale shows its address, something like `100.101.102.103`. Write it down.

### Phone A (runs the daemon, in Termux)
```bash
cd ~/The-Omniverse            # your clone of kiroba/The-Omniverse
git fetch origin && git checkout desktop && git pull origin desktop
termux-wake-lock              # keeps Android from pausing Termux in the background
export OMNI_HUB_REMOTE=1
export OMNI_HUB_BIND=0.0.0.0   # or your Tailscale address, e.g. 100.101.102.103
python3 Admin/omni_live_daemon_server.py
```
The start-up banner prints `REMOTE HUB ON`, the addresses to use, and the token. To see the token
again later (in a second Termux session):
```bash
cat ~/.omni/hub_token
```
`bash Admin/start_local_stack.sh` works too (export the two variables first); the banner then goes
to `daemon.log` (`grep -A4 "REMOTE HUB" daemon.log`).

`OMNI_HUB_BIND=0.0.0.0` is the easiest: it keeps working if Tailscale reconnects. It also answers on
your Wi-Fi, but only to requests that carry the token. Use the `100.x` address instead if you want
it reachable only through Tailscale (if Tailscale is off when the daemon starts, binding to it fails
and the daemon exits with an error; start Tailscale first).

### Phone B (runs KickBack only)
1. Install the KickBack APK (v0.1.7 or newer).
2. Open KickBack, go to **Settings > Hub**, choose **Remote hub**.
3. Address: phone A's Tailscale address (`100.x.y.z`). Leave the ports at 5000 / 9100.
4. Token: paste the token from phone A.
5. Save. The hub status should read **connected**. **Unauthorized** means the token is wrong;
   **unreachable** means phone A's daemon or Tailscale is off, or the address is wrong.

### Quick check from any device on the tailnet
```bash
curl -H "Authorization: Bearer $TOKEN" http://100.x.y.z:9100/api/v1/telemetry/node-health
curl -i http://100.x.y.z:5000/api/events/feed     # no token -> 401
```

## Cost and security notes
- Tailscale's free personal plan covers this; no servers, no recurring cost.
- Traffic between the phones is encrypted by Tailscale (WireGuard). The daemon itself speaks plain
  HTTP, so don't expose these ports to the open internet (no port forwarding); keep it on Tailscale.
- Anyone with the token can read the feed and submit **signed** posts. Treat the token like a password.
