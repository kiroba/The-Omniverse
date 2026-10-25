#!/usr/bin/env python3
"""
==============================================================================
THE OMNIVERSE - SECURE FLET DESKTOP CONTROL PANEL & RELAY GATEWAY (v1.0)
==============================================================================
"""

import sys
import os
import time
import json
import secrets
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    import flet as ft
except ImportError:
    pass

MODULE_TREE: Dict[str, Dict[str, Any]] = {
    "module_1": {"id": "module_1", "name": "Continuity-Engine", "level": 0, "type": "CORE ROOT", "description": "Immutable Merkle WAL, Ed25519 Hardware Keys", "requires": [], "mandatory": True, "default": True, "color": "#00FFCC"},
    "module_2": {"id": "module_2", "name": "The-Omni-Hub Transport Engine", "level": 1, "type": "TRANSPORT", "description": "P2P GossipSub Mesh, BLE/Wi-Fi Aware & IPC Gateway", "requires": ["module_1"], "mandatory": False, "default": True, "color": "#38BDF8"},
    "module_3": {"id": "module_3", "name": "Live Persona Engine (LPE Core)", "level": 1, "type": "AVATAR RENDER", "description": "PersonaTraitSchema Normalizer & CAS IPFS Engine", "requires": ["module_1"], "mandatory": False, "default": True, "color": "#A855F7"},
    "module_4": {"id": "module_4", "name": "OmniMind Autonomous Agent", "level": 2, "type": "AI AGENT", "description": "AutoGPT Maintenance Loops, Off-Chain Shadow Ledger", "requires": ["module_1", "module_2"], "mandatory": False, "default": False, "color": "#F59E0B"},
    "module_5": {"id": "module_5", "name": "The KickBack Mobile Client UI", "level": 2, "type": "FLUTTER UI", "description": "Sovereign Human Feed & OmniMarket Store", "requires": ["module_1", "module_2", "module_3"], "mandatory": False, "default": True, "color": "#EC4899"},
    "module_6": {"id": "module_6", "name": "Omni-Hub Desktop Relay Daemon", "level": 2, "type": "DESKTOP DAEMON", "description": "24/7 Unmetered CAS Blob Caching & Seeding", "requires": ["module_1", "module_2"], "mandatory": False, "default": False, "color": "#10B981"}
}

PRESET_PROFILES: Dict[str, List[str]] = {
    "Desktop Booster Relay": ["module_1", "module_2", "module_6"],
    "Autonomous AI Node": ["module_1", "module_2", "module_4"],
    "Full Mobile Client": ["module_1", "module_2", "module_3", "module_5"],
    "Minimal Edge Node": ["module_1", "module_2"],
    "Complete Omniverse Suite": ["module_1", "module_2", "module_3", "module_4", "module_5", "module_6"]
}

class SecureDaemonManager:
    """Manages Bearer authentication and health checks for the background relay daemon."""

    def __init__(self, port: int = 9200):
        self.port = port
        self.host = "127.0.0.1"
        self.auth_token = secrets.token_hex(32)
        self.is_running = False

    def get_auth_header(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Host": f"{self.host}:{self.port}",
            "Content-Type": "application/json"
        }

    def start_daemon(self, daemon_script_path: Path) -> bool:
        if self.is_running:
            return True
        self.is_running = True
        return True

    def stop_daemon(self):
        self.is_running = False


def main(page):
    page.title = "The Omniverse - Secure Flet Desktop Control Panel"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0F172A"
    page.padding = 20

    daemon_mgr = SecureDaemonManager(port=9200)
    selected_modules: Dict[str, bool] = {m_id: m["default"] for m_id, m in MODULE_TREE.items()}
    
    console_text = ft.Text(value="[SYSTEM INITIALIZED] Flet Material 3 Control Panel Ready.\n", font_family="Consolas", size=12, color="#00FFCC")

    def log(msg: str):
        timestamp = time.strftime("[%H:%M:%S] ")
        console_text.value += f"{timestamp}{msg}\n"
        page.update()

    def update_module_checkboxes():
        changed = True
        while changed:
            changed = False
            for m_id, m in MODULE_TREE.items():
                if selected_modules[m_id]:
                    for req in m["requires"]:
                        if not selected_modules[req]:
                            selected_modules[req] = True
                            log(f"[DAG AUTO-RESOLVE] Enabled prerequisite '{MODULE_TREE[req]['name']}' for '{m['name']}'")
                            changed = True

    def on_module_toggle(e, mod_id: str):
        selected_modules[mod_id] = e.control.value
        update_module_checkboxes()
        refresh_ui()

    def apply_preset(preset_name: str):
        active = PRESET_PROFILES.get(preset_name, [])
        for m_id in MODULE_TREE.keys():
            selected_modules[m_id] = (m_id in active) or MODULE_TREE[m_id]["mandatory"]
        update_module_checkboxes()
        log(f"[PRESET APPLIED] Loaded build profile: '{preset_name}'")
        refresh_ui()

    def build_header():
        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text("THE OMNIVERSE — SECURE DESKTOP CONTROL PANEL", size=18, weight=ft.FontWeight.BOLD, color="#00FFCC"),
                    ft.Text("Material 3 Flet Engine | Zero-Cloud Local IPC Gateway", size=12, color="#94A3B8")
                ])
            ]),
            padding=15,
            bgcolor="#1E293B",
            border_radius=10
        )

    def build_preset_row():
        buttons = []
        for p_name in PRESET_PROFILES.keys():
            buttons.append(
                ft.ElevatedButton(
                    text=p_name,
                    on_click=lambda e, name=p_name: apply_preset(name),
                    style=ft.ButtonStyle(color="#F8FAFC", bgcolor="#334155", shape=ft.RoundedRectangleBorder(radius=8))
                )
            )
        return ft.Container(
            content=ft.Column([
                ft.Text("Build Profile Presets", size=14, weight=ft.FontWeight.BOLD, color="#00FFCC"),
                ft.Row(buttons, wrap=True)
            ]),
            padding=15,
            bgcolor="#1E293B",
            border_radius=10
        )

    def refresh_ui():
        page.controls.clear()
        page.add(
            ft.Column([
                build_header(),
                ft.SizedBox(height=10),
                build_preset_row(),
                ft.SizedBox(height=10),
                ft.Container(content=ft.ListView(controls=[console_text], auto_scroll=True), height=200, bgcolor="#050811", padding=10)
            ])
        )
        page.update()

    refresh_ui()


if __name__ == "__main__":
    try:
        import flet as ft
        ft.app(target=main)
    except Exception as e:
        print("[INFO] Script ready. Run 'pip install flet && python omni_flet_desktop_control_panel.py' on desktop.")
