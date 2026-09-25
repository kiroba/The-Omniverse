import json
import time
import http.server
import socketserver
import threading
import urllib.parse

# ==============================================================================
# THE OMNIVERSE - EXTERNAL ADMIN MONITORING DASHBOARD (SCAFFOLD & TELEMETRY API)
# ==============================================================================
# This standalone out-of-band monitoring application connects to global bootnodes,
# P2P mesh health endpoints, and the OmniLedger bookkeeper agent to provide real-time
# visibility across all 6 core telemetry pillars without mutating internal state.
# ==============================================================================

PORT = 9100

class TelemetryCollector:
    """Mock/Live Telemetry Aggregator for the 6 Core Omniverse Pillars."""
    
    @staticmethod
    def get_security_metrics():
        return {
            "attestation_success_rate": 99.4,
            "bot_detection_triggers_24h": 142,
            "rate_limit_violations": 18,
            "slashed_p2p_nodes": 3,
            "banned_peer_ips": ["192.168.1.105", "10.0.4.12"]
        }

    @staticmethod
    def get_financial_metrics():
        return {
            "omnicredit_circulation": 1450200,
            "omnitoken_l2_pending_batches": 2,
            "bank_treasury_usd": 125400.00,
            "creator_treasury_usd": 25080.00,
            "reserve_ratio_health": "HEALTHY (32.4% Buffer)",
            "pending_cashout_queue_count": 5
        }

    @staticmethod
    def get_citizens_metrics():
        return {
            "total_registered_accounts": 48210,
            "daily_active_citizens": 12450,
            "role_tiers": {
                "COMMON": 42100,
                "CREATOR": 4200,
                "INFLUENCER": 1100,
                "EDUCATOR": 810,
                "ADVERTISING": 0  # Locked
            }
        }

    @staticmethod
    def get_worlds_metrics():
        return {
            "planet_1_kickback_rooms": 340,
            "planet_1_live_streams": 42,
            "planet_2_9x9_matches": 128,
            "active_p2p_widgets": {
                "trivia_quizzes": 15,
                "prediction_markets": 8,
                "poll_battles": 22
            }
        }

    @staticmethod
    def get_network_metrics():
        return {
            "active_gossipsub_peers": 1240,
            "bootnode_cluster_status": {
                "US_EAST": "ONLINE",
                "US_WEST": "ONLINE",
                "EU_CENTRAL": "ONLINE",
                "ASIA_PACIFIC": "ONLINE"
            },
            "cgnat_hole_punch_success": "96.8%",
            "avg_socket_latency_ms": 42
        }

    @staticmethod
    def get_overall_health():
        return {
            "global_system_status": "100% OPERATIONAL",
            "uptime_seconds": 864000,
            "merkle_anchor_sync_status": "SYNCHRONIZED",
            "cpu_utilization": "14.2%",
            "memory_usage_mb": 512
        }

    @classmethod
    def get_full_telemetry(cls):
        return {
            "timestamp": int(time.time()),
            "security": cls.get_security_metrics(),
            "financial": cls.get_financial_metrics(),
            "citizens": cls.get_citizens_metrics(),
            "worlds": cls.get_worlds_metrics(),
            "network": cls.get_network_metrics(),
            "overall_health": cls.get_overall_health()
        }

# HTML Dashboard Interface
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>The Omniverse - External Admin Monitoring Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0b0f19; color: #e2e8f0; margin: 0; padding: 20px; }
        h1 { color: #38bdf8; border-bottom: 2px solid #1e293b; padding-bottom: 10px; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
        .card { background: #161e2e; border: 1px solid #2d3748; border-radius: 8px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .card h2 { margin-top: 0; font-size: 1.2rem; color: #38bdf8; border-bottom: 1px solid #2d3748; padding-bottom: 8px; }
        .metric { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 0.95rem; }
        .label { color: #94a3b8; }
        .value { font-weight: bold; color: #f8fafc; }
        .status-online { color: #4ade80; font-weight: bold; }
        .badge { background: #0284c7; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
    </style>
</head>
<body>
    <h1>🛡️ The Omniverse - External Admin Telemetry Dashboard <span class="badge">Master Admin Out-of-Band</span></h1>
    <div class="grid" id="telemetry-grid">
        <div class="card"><h2>Overall System Health</h2><div id="health-pillar">Loading...</div></div>
        <div class="card"><h2>Security Telemetry</h2><div id="security-pillar">Loading...</div></div>
        <div class="card"><h2>Financial & Treasury</h2><div id="financial-pillar">Loading...</div></div>
        <div class="card"><h2>Citizen Analytics</h2><div id="citizens-pillar">Loading...</div></div>
        <div class="card"><h2>Worlds & Planets</h2><div id="worlds-pillar">Loading...</div></div>
        <div class="card"><h2>P2P Mesh Network</h2><div id="network-pillar">Loading...</div></div>
    </div>

    <script>
        async function fetchTelemetry() {
            try {
                const res = await fetch('/api/telemetry');
                const data = await res.json();
                
                // Health
                document.getElementById('health-pillar').innerHTML = `
                    <div class="metric"><span class="label">System Status:</span><span class="value status-online">${data.overall_health.global_system_status}</span></div>
                    <div class="metric"><span class="label">Merkle Anchor Sync:</span><span class="value">${data.overall_health.merkle_anchor_sync_status}</span></div>
                    <div class="metric"><span class="label">CPU Usage:</span><span class="value">${data.overall_health.cpu_utilization}</span></div>
                `;

                // Security
                document.getElementById('security-pillar').innerHTML = `
                    <div class="metric"><span class="label">Attestation Pass Rate:</span><span class="value">${data.security.attestation_success_rate}%</span></div>
                    <div class="metric"><span class="label">Bot Triggers (24h):</span><span class="value">${data.security.bot_detection_triggers_24h}</span></div>
                    <div class="metric"><span class="label">Slashed P2P Nodes:</span><span class="value">${data.security.slashed_p2p_nodes}</span></div>
                `;

                // Financial
                document.getElementById('financial-pillar').innerHTML = `
                    <div class="metric"><span class="label">OmniCredits Circulating:</span><span class="value">${data.financial.omnicredit_circulation.toLocaleString()}</span></div>
                    <div class="metric"><span class="label">Bank Treasury USD:</span><span class="value">$${data.financial.bank_treasury_usd.toLocaleString()}</span></div>
                    <div class="metric"><span class="label">Creator Treasury USD:</span><span class="value">$${data.financial.creator_treasury_usd.toLocaleString()}</span></div>
                `;

                // Citizens
                document.getElementById('citizens-pillar').innerHTML = `
                    <div class="metric"><span class="label">Total Registered:</span><span class="value">${data.citizens.total_registered_accounts.toLocaleString()}</span></div>
                    <div class="metric"><span class="label">Daily Active (DAU):</span><span class="value">${data.citizens.daily_active_citizens.toLocaleString()}</span></div>
                `;

                // Worlds
                document.getElementById('worlds-pillar').innerHTML = `
                    <div class="metric"><span class="label">The KickBack Streams:</span><span class="value">${data.worlds.planet_1_live_streams}</span></div>
                    <div class="metric"><span class="label">9x9 Game Matches:</span><span class="value">${data.worlds.planet_2_9x9_matches}</span></div>
                `;

                // Network
                document.getElementById('network-pillar').innerHTML = `
                    <div class="metric"><span class="label">Active Mesh Peers:</span><span class="value">${data.network.active_gossipsub_peers}</span></div>
                    <div class="metric"><span class="label">CGNAT Punch Rate:</span><span class="value">${data.network.cgnat_hole_punch_success}</span></div>
                    <div class="metric"><span class="label">Avg Socket Latency:</span><span class="value">${data.network.avg_socket_latency_ms} ms</span></div>
                `;
            } catch (e) {
                console.error("Telemetry fetch error:", e);
            }
        }
        fetchTelemetry();
        setInterval(fetchTelemetry, 3000);
    </script>
</body>
</html>
"""

class AdminDashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/telemetry':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            telemetry = TelemetryCollector.get_full_telemetry()
            self.wfile.write(json.dumps(telemetry).encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode('utf-8'))

def run_dashboard_server():
    with socketserver.TCPServer(("", PORT), AdminDashboardHandler) as httpd:
        print(f"[Omniverse External Admin Dashboard] Server running on http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_dashboard_server()
