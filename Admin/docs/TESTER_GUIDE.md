# Remote tester guide: Keith's hub over Tailscale (daemon v8.7.0+)

Up to 10 Android testers use KickBack against **one hub**: the daemon running on Keith's Windows PC.
Each tester has their **own free Tailscale account**. Keith shares **only the hub PC** with them
(Tailscale "node sharing"), and a policy rule limits them to the two hub ports KickBack needs.
Nothing here costs money.

How the daemon side works (env vars, token, endpoints) is in [REMOTE_HUB.md](REMOTE_HUB.md).
This guide is the Tailscale and tester layer on top of it.

## Ports

| Port | Used by testers? | What it is |
|---|---|---|
| TCP 5000 | **Yes** | App API: `/api/events/feed`, `/api/events/append`, bug reports (`/api/bugs/report`, daemon v8.9.0+). Needs the hub token. |
| TCP 9100 | **Yes** | `GET /api/v1/telemetry/node-health` (hub status in KickBack). Needs the hub token. |
| TCP 5005 | No | Daemon-to-daemon P2P sync. Testers run only KickBack, so they don't need it. |
| UDP 9101 | No | LAN discovery broadcast. Doesn't cross Tailscale. |
| UDP/TCP 3478 + a relay port range | **Upcoming, not built yet** | OmniCast TURN relay planned for the hub. Add these to the rule below only when it ships. |

---

## A. Keith: one-time hub setup

### 1. Tailscale on the hub PC
1. Install Tailscale for Windows from https://tailscale.com/download and sign in with your account.
2. In the admin console **Machines** page, note the PC's `100.x.y.z` address and its name.
3. Optional but useful: in the admin console **DNS** page, keep **MagicDNS** on. Testers can then use
   the name `<pc-name>.<your-tailnet-name>.ts.net` instead of the IP.

### 2. Turn on the remote hub (PowerShell, in your clone on `desktop`)
```powershell
cd $HOME\The-Omniverse
git fetch origin; git checkout desktop; git pull origin desktop
$env:OMNI_HUB_REMOTE = "1"
$env:OMNI_HUB_BIND   = "0.0.0.0"     # or the PC's 100.x address (Tailscale must be up first)
python Admin\omni_live_daemon_server.py
```
The banner prints `REMOTE HUB ON` and the token. To read the token later:
`Get-Content $HOME\.omni\hub_token`. If Windows Firewall asks about Python, allow it on the network
Tailscale uses, or testers will see **unreachable**.

### 3. Create the share link
1. Admin console > **Machines** > the hub PC > `...` menu > **Share**.
2. Tab **Copy invite link**, turn on **Reusable link**, then **Copy share link**.
3. Send it to testers privately. Treat it like a password.

Facts from Tailscale's docs: a reusable link can be accepted up to 1,000 times; **unused links expire
after 30 days**; testers see **only the shared machine**, nothing else on your tailnet; the shared
machine is quarantined (it can't open connections into their tailnets); and sharing **does not add
users** to your tailnet, so it doesn't use your free plan's 6-user limit. After all testers have
joined, you can revoke the link itself so it can't be reused.

### 4. Lock testers to ports 5000 and 9100 (tailnet policy file)
The default policy allows everyone everything, and per Tailscale's docs `"src": ["*"]` **includes
shared users**. Replace it so your own devices keep full access and shared testers get only the two
hub ports.

Admin console > **Access controls**. Before editing, copy the whole current file somewhere safe.
Then make the `grants` section look like this (keep any `ssh`, `tagOwners` or other sections you
already have, and put your hub's real `100.x` address in `hosts`):

```jsonc
{
  "hosts": {
    "omni-hub": "100.101.102.103" // the hub PC's Tailscale IP (Machines page)
  },
  "grants": [
    // You (and anyone you add as a member of your own tailnet): full access, as before.
    {
      "src": ["autogroup:member"],
      "dst": ["*"],
      "ip": ["*"]
    },
    // Shared-in testers: only the hub, only the two KickBack ports.
    {
      "src": ["autogroup:shared"],
      "dst": ["omni-hub"],
      "ip": ["tcp:5000", "tcp:9100"]
    }
    // Upcoming OmniCast TURN relay (not built yet), add when it ships:
    // { "src": ["autogroup:shared"], "dst": ["omni-hub"], "ip": ["udp:3478", "tcp:3478", "udp:<relay-range>"] }
  ]
}
```

Notes:
- `autogroup:member` covers devices of users who are members of your tailnet; it does **not**
  include shared users. If you have **tagged** devices (servers, exit nodes) that need to reach
  other machines, they lose access under this rule; add a grant for `autogroup:tagged` or the tag.
- If anything stops working, paste back the copy you saved. The console rejects a file that doesn't
  parse, so a typo can't half-apply.
- What hasn't been tested: we haven't checked live that this exact policy blocks the other ports. After saving, ask
  one tester to try `http://<hub>:5005` (it should fail) and the KickBack hub status (it should
  connect).
- The tester's own tailnet must also allow the connection. A new account's default policy does.

### 5. Revoke one tester
Admin console > **Machines** > hub PC > **Share**. The dialog lists who accepted (email and picture).
Use the `...` menu next to that tester to revoke. They lose access right away; to restore it, send a
new invite.

All testers share **one hub token**, so revoking someone's share cuts their network path but they
still know the token. That's fine as long as they can't reach the hub. If you want to be sure, also
rotate the token (next step).

Not verified: whether revoking one person who accepted a **reusable** link leaves the others
connected. If the dialog only offers to revoke the whole link, send each tester a **single-use**
link (same dialog with Reusable off, or **Share by email**) so each one can be revoked on their own.

### 6. Rotate the hub token
```powershell
Remove-Item $HOME\.omni\hub_token
# restart the daemon (Ctrl+C, then run it again with the same env vars)
Get-Content $HOME\.omni\hub_token
```
Send the new token to every remaining tester privately. Until they paste it in, they see
**unauthorized**.

---

## B. Tester steps (Android 8.0 or newer)

1. **Tailscale account.** Install **Tailscale** from the Play Store, tap **Get Started**, accept the
   VPN prompt, and sign in (Google is fine). This creates your own free tailnet.
2. **Accept the share.** Open the link Keith sent while signed in to that same account and accept.
   The hub PC then shows up in your Tailscale app's device list.
3. **Note the hub's address** as **your** Tailscale app shows it: a `100.x.y.z` IP, or the full name
   `<pc-name>.<keith-tailnet>.ts.net`. Use the one your app shows. The IP is usually the same as on
   Keith's side but can differ, and the short name alone won't work for a shared machine.
4. **Install KickBack** from the signed APK on
   [GitHub Releases](https://github.com/kiroba/The-Omniverse/releases) (latest release). Allow
   "install unknown apps" for your browser when Android asks.
5. **Open KickBack** and read and accept the **Tester agreement** (pre-alpha consent screen).
6. **Settings > Hub > Remote hub.** Enter the hub address from step 3. Leave the ports at
   **5000 / 9100**. Paste the **token Keith sent you privately**. Save. Status should read
   **connected**.
7. **Report bugs** from the app's **Report a bug** sheet: describe what happened, then tap
   **Report on GitHub** (opens a prefilled issue) or **Email instead**. App version, device model and
   Android version are added for you. With a hub set, a copy is also saved on the hub. Don't include
   passwords, the token, or private messages.

Keep the token to yourself. Anyone with it, and a path to the hub, can read the feed and post.

---

## C. Troubleshooting

| What KickBack shows | Meaning | Fix |
|---|---|---|
| **unreachable** | No network path to the hub. | Tailscale is off on your phone, the hub PC is off or asleep, Keith's daemon isn't running, the address is wrong, or your share was revoked. Open Tailscale and check the hub is listed and online. Try the IP if the name fails, or turn on MagicDNS in **your** admin console (DNS page). |
| **unauthorized** | You reached the hub but the token is wrong. | Re-paste the token exactly (no spaces). If Keith rotated it, ask for the new one. |

**Keeping Tailscale connected on Android.** Android's battery saving can pause Tailscale in the
background and the hub then looks unreachable. In Android **Settings > Network (or Connections) >
VPN > Tailscale (gear)**, turn on **Always-on VPN**. Leave **Block connections without VPN off**:
without an exit node it can cut your phone off the internet. Also set Tailscale's battery usage to
**Unrestricted**. Menu names vary by phone maker.

**Android older than 8.0 is not supported.** KickBack's APKs are built with `minSdk 26`
(Android 8.0); older phones can't install them.

## Sources (Tailscale docs, checked Oct 2026)
- Sharing, reusable links, 30-day expiry, quarantine, `autogroup:shared`, MagicDNS FQDN rule, revoke:
  https://tailscale.com/kb/1084/sharing (now https://tailscale.com/docs/features/sharing)
- Sharing doesn't increase user count: https://tailscale.com/docs/reference/inviting-vs-sharing
- Policy file, `*` includes `autogroup:shared`, `autogroup:member` excludes shared users, `hosts`:
  https://tailscale.com/docs/reference/syntax/policy-file
- Grants `ip` syntax (`tcp:5000`): https://tailscale.com/docs/reference/syntax/grants
- Personal plan (free, up to 6 users, unlimited user devices): https://tailscale.com/pricing
- Android install: https://tailscale.com/docs/install/android
