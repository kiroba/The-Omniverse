#!/usr/bin/env python3
"""
==============================================================================
THE OMNIVERSE - FLET DESKTOP CONTROL PANEL (v2.0, Flet 1.0.x)
==============================================================================
A small desktop window for the real daemon (Admin/omni_live_daemon_server.py):
- Node health from GET :9100/api/v1/telemetry/node-health (version, node id, mesh, peers)
- Recent events from GET :5000/api/events/feed (newest first, with the Verified flag)
- Post a local test event with POST :5000/api/events/append (this PC's daemon only)

Remote hub: point "Hub address" at another PC's daemon (e.g. its Tailscale 100.x IP). Requests
then carry "Authorization: Bearer <token>", read from ~/.omni/hub_token or the token field.
Posting is disabled for remote hubs because remote posts must be signed by the client's own key.

Run:  pip install "flet>=1.0,<2"  &&  python omni_flet_desktop_control_panel.py
Replaces the v1.0 panel, which targeted a non-existent port 9200, never called the daemon and
did not run on Flet 1.0 (ft.app / ElevatedButton / SizedBox were removed). Issue #8.
==============================================================================
"""

import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import flet as ft
except ImportError:  # the client below works without Flet (and is what the tests use)
    ft = None

DEFAULT_HOST = "127.0.0.1"
IPC_PORT = 5000
TELEMETRY_PORT = 9100
LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def read_hub_token(path: Optional[Path] = None) -> str:
    path = path or (Path.home() / ".omni" / "hub_token")
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


class DaemonClient:
    """Thin HTTP client for the daemon's app endpoints. Every call returns (status, body)."""

    def __init__(self, host: str = DEFAULT_HOST, token: str = "", ipc_port: int = IPC_PORT,
                 telemetry_port: int = TELEMETRY_PORT, timeout: float = 4.0):
        self.host = (host or DEFAULT_HOST).strip()
        self.token = (token or "").strip()
        self.ipc_port, self.telemetry_port, self.timeout = ipc_port, telemetry_port, timeout
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @property
    def is_remote(self) -> bool:
        return self.host not in LOOPBACK

    def _url(self, port: int, path: str) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"http://{host}:{port}{path}"

    def _request(self, method: str, url: str, body: Optional[dict] = None) -> Tuple[int, Dict[str, Any]]:
        headers = {"Content-Type": "application/json"}
        if self.is_remote and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with self._opener.open(req, timeout=self.timeout) as r:
                return r.status, json.loads(r.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read().decode("utf-8") or "{}")
            except ValueError:
                return e.code, {"message": e.reason}
        except (urllib.error.URLError, OSError, ValueError) as e:
            return 0, {"message": f"unreachable: {getattr(e, 'reason', e)}"}

    def health(self):
        return self._request("GET", self._url(self.telemetry_port, "/api/v1/telemetry/node-health"))

    def feed(self, limit: int = 25):
        return self._request("GET", self._url(self.ipc_port, f"/api/events/feed?limit={int(limit)}"))

    def append(self, action: str, payload: dict):
        if self.is_remote:
            return 0, {"message": "posting is only allowed to this PC's daemon (remote posts must be client-signed)"}
        return self._request("POST", self._url(self.ipc_port, "/api/events/append"),
                             {"action": action, "payload": payload})


def describe_health(status: int, body: Dict[str, Any]) -> str:
    if status == 0:
        return f"Daemon offline ({body.get('message', '')}). Start Admin/omni_live_daemon_server.py."
    if status == 401:
        return "401: wrong or missing hub token for this remote hub."
    if status != 200:
        return f"HTTP {status}: {body.get('message', body)}"
    peers = body.get("peer_ips") or body.get("peer_addresses") or []
    node = str(body.get("node_id", ""))
    return (f"Online | v{body.get('version', '?')} | mesh {body.get('mesh_id', '?')} | "
            f"node {node[:12]}... | {len(peers)} peer(s)")


def describe_event(ev: Dict[str, Any]) -> str:
    when = ev.get("ts_ms") or ev.get("ts")
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(when / 1000)) if isinstance(when, int) else "?"
    badge = "Verified" if ev.get("verified") else "Unverified"
    payload = json.dumps(ev.get("payload", {}), ensure_ascii=False)
    if len(payload) > 80:
        payload = payload[:77] + "..."
    return f"{stamp}  {ev.get('action', '?')}  [{badge}]  {str(ev.get('author_pubkey', ''))[:10]}...  {payload}"


def build_view(page, client_factory=DaemonClient, poll_seconds: float = 5.0):
    """Builds the panel on a Flet page. Split out from main() so it can be tested headless."""
    page.title = "The Omniverse - Desktop Control Panel"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0F172A"
    page.padding = 20

    host_field = ft.TextField(label="Hub address", value=DEFAULT_HOST, width=260)
    token_field = ft.TextField(label="Hub token (remote only)", value=read_hub_token(),
                               password=True, can_reveal_password=True, width=360)
    status_text = ft.Text("Checking daemon...", color="#94A3B8", selectable=True)
    events_list = ft.ListView(spacing=4, auto_scroll=False, expand=True)
    post_field = ft.TextField(label="Test post text", expand=True)
    console = ft.Text("", size=12, color="#00FFCC", font_family="Consolas", selectable=True)

    def log(msg: str):
        console.value = (time.strftime("[%H:%M:%S] ") + msg + "\n" + (console.value or ""))[:4000]

    def client():
        return client_factory(host_field.value, token_field.value)

    def refresh(_=None):
        c = client()
        status_text.value = describe_health(*c.health())
        st, body = c.feed(25)
        events_list.controls.clear()
        if st == 200:
            for ev in body.get("events", []):
                events_list.controls.append(ft.Text(describe_event(ev), size=12, selectable=True,
                                                    color="#10B981" if ev.get("verified") else "#F59E0B"))
        else:
            events_list.controls.append(ft.Text(f"Feed unavailable (HTTP {st}): {body.get('message', '')}",
                                                color="#F87171"))
        post_button.disabled = c.is_remote
        page.update()

    def post(_=None):
        text = (post_field.value or "").strip()
        if not text:
            return
        st, body = client().append("CREATOR_POST_PUBLISHED", {"title": text, "source": "flet-panel"})
        log(f"POST -> {st} {body.get('event_id') or body.get('message', '')}")
        if st == 200:
            post_field.value = ""
        refresh()

    post_button = ft.Button(content="Post to this PC's daemon", on_click=post)

    page.add(
        ft.Column(expand=True, controls=[
            ft.Container(padding=15, bgcolor="#1E293B", border_radius=10, content=ft.Column([
                ft.Text("THE OMNIVERSE - DESKTOP CONTROL PANEL", size=18,
                        weight=ft.FontWeight.BOLD, color="#00FFCC"),
                ft.Text("Talks to the live daemon on :9100 / :5000 (or a remote hub over Tailscale)",
                        size=12, color="#94A3B8"),
                ft.Row([host_field, token_field, ft.Button(content="Refresh", on_click=refresh)], wrap=True),
                status_text,
            ])),
            ft.Container(height=10),
            ft.Text("Recent events", weight=ft.FontWeight.BOLD, color="#00FFCC"),
            ft.Container(content=events_list, expand=True, bgcolor="#050811", padding=10, border_radius=8),
            ft.Row([post_field, post_button]),
            ft.Container(content=console, height=90, bgcolor="#050811", padding=8, border_radius=8),
        ])
    )
    refresh()

    if poll_seconds > 0:
        def poll():
            while True:
                time.sleep(poll_seconds)
                try:
                    refresh()
                except Exception:   # window closed
                    return
        threading.Thread(target=poll, daemon=True).start()
    return {"refresh": refresh, "post": post, "status": status_text, "events": events_list,
            "host": host_field, "token": token_field, "post_field": post_field, "post_button": post_button}


def main(page):
    build_view(page)


if __name__ == "__main__":
    if ft is None:
        raise SystemExit('Flet is not installed. Run: pip install "flet>=1.0,<2"')
    ft.run(main)
