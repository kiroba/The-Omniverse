import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const OmniMeshMonitorApp());
}

class OmniMeshMonitorApp extends StatelessWidget {
  const OmniMeshMonitorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Omniverse Mesh Telemetry Monitor',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0F172A),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF03DAC6),
          secondary: Color(0xFFBB86FC),
          surface: Color(0xFF1E293B),
        ),
      ),
      home: const MeshMonitorDashboard(),
    );
  }
}

class MeshMonitorDashboard extends StatefulWidget {
  const MeshMonitorDashboard({super.key});

  @override
  State<MeshMonitorDashboard> createState() => _MeshMonitorDashboardState();
}

class _MeshMonitorDashboardState extends State<MeshMonitorDashboard> {
  String _host = '127.0.0.1';
  Map<String, dynamic>? _nodeHealth;
  Map<String, dynamic>? _dbStats;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _fetchTelemetry();
    _timer = Timer.periodic(const Duration(seconds: 2), (_) => _fetchTelemetry());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _fetchTelemetry() async {
    try {
      final hRes = await http
          .get(Uri.parse('http://$_host:9100/api/v1/telemetry/node-health'))
          .timeout(const Duration(seconds: 1));
      if (hRes.statusCode == 200) {
        final hData = jsonDecode(hRes.body);
        setState(() {
          _nodeHealth = hData;
          if (hData['auto_detected_ip'] != null && _host == '127.0.0.1') {
            // Keep local host reference synced
          }
        });
      }
    } catch (_) {}

    try {
      final sRes = await http
          .get(Uri.parse('http://$_host:5000/api/events/stats'))
          .timeout(const Duration(seconds: 1));
      if (sRes.statusCode == 200) {
        setState(() {
          _dbStats = jsonDecode(sRes.body);
        });
      }
    } catch (_) {}
  }

  Future<void> _toggleWan(bool enable) async {
    try {
      await http.post(
        Uri.parse('http://$_host:9100/api/wan/toggle'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'enable': enable, 'duration_minutes': 15}),
      );
      _fetchTelemetry();
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final isOnline = _nodeHealth != null;
    final autoIp = _nodeHealth?['auto_detected_ip'] ?? 'Auto-Detecting...';
    final nodeId = _nodeHealth?['node_id'] ?? 'N/A';
    final activePeers = List<dynamic>.from(_nodeHealth?['discovered_peers'] ?? []);
    final wanActive = _nodeHealth?['wan_active'] ?? false;
    final wanRem = _nodeHealth?['wan_time_remaining'] ?? 0;

    final totalEvents = _dbStats?['total_events'] ?? 0;
    final lastMerkle = _dbStats?['last_merkle_hash'] ?? '0x00000000000000000000000000000000';

    return Scaffold(
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAlignment.start,
          children: [
            Text('Omniverse Mesh Telemetry', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            Text('ZERO-CONFIG DYNAMIC AUTO-IP MONITOR', style: TextStyle(fontSize: 10, color: Color(0xFF03DAC6), letterSpacing: 0.8)),
          ],
        ),
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16.0),
            child: Center(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: isOnline ? const Color(0x2610B981) : const Color(0x26FF9800),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: isOnline ? const Color(0xFF10B981) : Colors.orange),
                ),
                child: Row(
                  children: [
                    Icon(Icons.circle, size: 8, color: isOnline ? const Color(0xFF10B981) : Colors.orange),
                    const SizedBox(width: 6),
                    Text(
                      isOnline ? 'Online' : 'Searching...',
                      style: TextStyle(
                        color: isOnline ? const Color(0xFF10B981) : Colors.orange,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          )
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Local Node Identity Card
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF03DAC6).withOpacity(0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAlignment.start,
              children: [
                const Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text("LOCAL NODE AUTO-IDENTITY", style: TextStyle(fontSize: 11, color: Colors.grey, fontWeight: FontWeight.bold)),
                    Icon(Icons.auto_awesome, size: 16, color: Color(0xFF03DAC6)),
                  ],
                ),
                const SizedBox(height: 10),
                SelectableText("Auto IP: $autoIp", style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF03DAC6))),
                const SizedBox(height: 4),
                SelectableText("Node ID: $nodeId", style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: Colors.grey)),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // WAN Listener Toggle Card
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white10),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAlignment.start,
                  children: [
                    const Text("Public WAN Mesh Listener", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white)),
                    Text(
                      wanActive ? "WAN Socket Active ($wanRem s remaining)" : "Standby (Local Subnet Only)",
                      style: TextStyle(fontSize: 11, color: wanActive ? const Color(0xFF10B981) : Colors.grey),
                    ),
                  ],
                ),
                Switch(
                  value: wanActive,
                  activeThumbColor: const Color(0xFF10B981),
                  activeTrackColor: const Color(0x3310B981),
                  onChanged: (val) => _toggleWan(val),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Discovered Peers Section
          const Text("DYNAMICALLY DISCOVERED PEER NODES", style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.grey)),
          const SizedBox(height: 8),
          if (activePeers.isNotEmpty)
            Column(
              children: activePeers.map((p) {
                final pNode = p['node_id'] ?? 'Peer';
                final pIp = p['ip'] ?? '';
                final pTrans = p['transport'] ?? 'P2P';
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  color: const Color(0xFF1E293B),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  child: ListTile(
                    leading: const CircleAvatar(
                      backgroundColor: Color(0x26BB86FC),
                      child: Icon(Icons.hub, color: Color(0xFFBB86FC), size: 20),
                    ),
                    title: Text("Node: ${pNode.substring(0, 12)}...", style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white)),
                    subtitle: Text("IP: $pIp", style: const TextStyle(fontSize: 11, color: Colors.grey)),
                    trailing: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(color: const Color(0x3303DAC6), borderRadius: BorderRadius.circular(6)),
                      child: Text(pTrans, style: const TextStyle(fontSize: 10, color: Color(0xFF03DAC6), fontWeight: FontWeight.bold)),
                    ),
                  ),
                );
              }).toList(),
            )
          else
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: const Color(0xFF1E293B), borderRadius: BorderRadius.circular(10)),
              child: const Center(
                child: Text("Scanning local subnet & UDP beacons for active peers...", style: TextStyle(fontSize: 12, color: Colors.grey, fontStyle: FontStyle.italic)),
              ),
            ),
          const SizedBox(height: 16),

          // Merkle DAG Metrics Card
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white10),
            ),
            child: Column(
              crossAxisAlignment: CrossAlignment.start,
              children: [
                const Text("CONTINUITY MERKLE DAG DATABASE", style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.grey)),
                const SizedBox(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text("Total Micro-Blocks", style: TextStyle(fontSize: 13, color: Colors.white70)),
                    Text("$totalEvents Events", style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Color(0xFF03DAC6))),
                  ],
                ),
                const SizedBox(height: 6),
                SelectableText("Latest Merkle Root: ${lastMerkle.substring(0, 24)}...", style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: Colors.grey)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
