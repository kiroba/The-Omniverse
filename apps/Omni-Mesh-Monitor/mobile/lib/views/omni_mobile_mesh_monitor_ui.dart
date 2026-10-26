import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const OmniMobileMeshMonitorApp());
}

class OmniMobileMeshMonitorApp extends StatelessWidget {
  const OmniMobileMeshMonitorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'OmniVerse Telemetry Monitor',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0B0F19),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF10B981),
          secondary: Color(0xFF6366F1),
          surface: Color(0xFF151D30),
        ),
      ),
      home: const MeshMonitorDashboardScreen(),
    );
  }
}

class MeshMonitorDashboardScreen extends StatefulWidget {
  const MeshMonitorDashboardScreen({super.key});

  @override
  State<MeshMonitorDashboardScreen> createState() => _MeshMonitorDashboardScreenState();
}

class _MeshMonitorDashboardScreenState extends State<MeshMonitorDashboardScreen> {
  late final TextEditingController _hostController;
  String _targetHost = '127.0.0.1';
  Timer? _pollTimer;

  Map<String, dynamic>? _nodeHealth;
  Map<String, dynamic>? _omnimindTelemetry;
  Map<String, dynamic>? _dbStats;
  List<dynamic> _recentEvents = [];

  @override
  void initState() {
    super.initState();
    _hostController = TextEditingController(text: _targetHost);
    _pollAllTelemetry();
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) => _pollAllTelemetry());
  }

  @override
  void dispose() {
    _hostController.dispose();
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _pollAllTelemetry() async {
    // 1. Node Health
    try {
      final res = await http
          .get(Uri.parse('http://$_targetHost:9100/api/v1/telemetry/node-health'))
          .timeout(const Duration(seconds: 2));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        if (mounted) setState(() => _nodeHealth = data);
      }
    } catch (_) {
      if (mounted) setState(() => _nodeHealth = null);
    }

    // 2. OmniMind Telemetry
    try {
      final omRes = await http
          .get(Uri.parse('http://$_targetHost:9100/api/omnimind/telemetry'))
          .timeout(const Duration(seconds: 2));
      if (omRes.statusCode == 200) {
        final omData = jsonDecode(omRes.body);
        if (mounted) setState(() => _omnimindTelemetry = omData);
      }
    } catch (_) {
      if (mounted) setState(() => _omnimindTelemetry = null);
    }

    // 3. Database Stats
    try {
      final statsRes = await http
          .get(Uri.parse('http://$_targetHost:5000/api/events/stats'))
          .timeout(const Duration(seconds: 2));
      if (statsRes.statusCode == 200) {
        final statsData = jsonDecode(statsRes.body);
        if (mounted) setState(() => _dbStats = statsData);
      }
    } catch (_) {
      if (mounted) setState(() => _dbStats = null);
    }

    // 4. Event Stream List
    try {
      final listRes = await http
          .get(Uri.parse('http://$_targetHost:5000/api/events/list'))
          .timeout(const Duration(seconds: 2));
      if (listRes.statusCode == 200) {
        final listData = jsonDecode(listRes.body);
        if (mounted) setState(() => _recentEvents = listData['events'] ?? []);
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.monitor_heart_rounded, color: Color(0xFF10B981)),
            SizedBox(width: 8),
            Text('OmniVerse Mesh Monitor', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
          ],
        ),
        backgroundColor: const Color(0xFF151D30),
        elevation: 0,
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16.0),
            child: Center(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: _nodeHealth != null ? const Color(0x2610B981) : const Color(0x26EF4444),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: _nodeHealth != null ? const Color(0xFF10B981) : Colors.redAccent),
                ),
                child: Row(
                  children: [
                    Icon(Icons.circle, size: 8, color: _nodeHealth != null ? const Color(0xFF10B981) : Colors.redAccent),
                    const SizedBox(width: 6),
                    Text(
                      _nodeHealth != null ? 'ONLINE' : 'OFFLINE',
                      style: TextStyle(
                        color: _nodeHealth != null ? const Color(0xFF10B981) : Colors.redAccent,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Daemon Host Config
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFF151D30),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: TextField(
                controller: _hostController,
                style: const TextStyle(color: Colors.white, fontFamily: 'monospace', fontSize: 14),
                decoration: const InputDecoration(
                  labelText: 'Target Node Daemon Host',
                  labelStyle: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                  border: InputBorder.none,
                  prefixIcon: Icon(Icons.dns_rounded, color: Color(0xFF10B981), size: 20),
                ),
                onSubmitted: (val) {
                  setState(() => _targetHost = val.trim());
                  _pollAllTelemetry();
                },
              ),
            ),

            const SizedBox(height: 20),

            // Node Telemetry Card
            _buildCard(
              title: 'LOCAL DAEMON TELEMETRY (:9100)',
              icon: Icons.dns_rounded,
              accentColor: const Color(0xFF10B981),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildMetricRow('Node ID', _nodeHealth?['node_id'] ?? 'OFFLINE'),
                  _buildMetricRow('Daemon Version', _nodeHealth?['version'] ?? 'N/A'),
                  _buildMetricRow('Active WAN Peers', '${_nodeHealth?['active_peers'] ?? 0} connected'),
                  _buildMetricRow('Throughput Rx / Tx', '${_nodeHealth?['rx_bytes_sec'] ?? 0.0} B/s | ${_nodeHealth?['tx_bytes_sec'] ?? 0.0} B/s'),
                  _buildMetricRow('Uptime', '${_nodeHealth?['uptime_seconds'] ?? 0}s'),
                  _buildMetricRow('Human Attestation', '${_nodeHealth?['human_attestation_rate'] ?? 100.0}%'),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // OmniMind Agent Card
            _buildCard(
              title: 'OMNIMIND AUTONOMOUS EDGE AGENT',
              icon: Icons.psychology_rounded,
              accentColor: const Color(0xFF6366F1),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildMetricRow('Agent ID', _omnimindTelemetry?['agent_id'] ?? 'OmniMind_Edge_0x01'),
                  _buildMetricRow('Agent Status', _omnimindTelemetry?['status'] ?? 'STANDBY'),
                  _buildMetricRow('Current Action', _omnimindTelemetry?['current_action'] ?? 'AUDITING_MERKLE_CHAIN'),
                  _buildMetricRow('Events Audited', '${_omnimindTelemetry?['events_processed'] ?? 0}'),
                  _buildMetricRow('System Free Memory', '${_omnimindTelemetry?['mem_free_mb'] ?? 0} MB'),
                  _buildMetricRow('Database Size On Disk', '${_omnimindTelemetry?['db_size_bytes'] ?? 0} bytes'),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // Continuity Merkle DB Card
            _buildCard(
              title: 'CONTINUITY MERKLE DAG DATABASE (:5000)',
              icon: Icons.dataset_rounded,
              accentColor: const Color(0xFFF59E0B),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildMetricRow('Total Events', '${_dbStats?['total_events'] ?? 0}'),
                  _buildMetricRow('Storage Mode', '${_dbStats?['db_mode'] ?? 'WAL'} (SQLite Write-Ahead Logging)'),
                  _buildMetricRow('Latest Merkle Hash', _dbStats?['last_merkle_hash'] ?? 'GENESIS'),
                ],
              ),
            ),

            const SizedBox(height: 20),

            // Live Event Stream Table
            const Text('LIVE DATABASE EVENT STREAM', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white)),
            const SizedBox(height: 10),
            _recentEvents.isEmpty
                ? Container(
                    padding: const EdgeInsets.all(20),
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: const Color(0xFF151D30),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Center(
                      child: Text('No events recorded in continuity_events.db yet.', style: TextStyle(color: Colors.grey, fontSize: 13)),
                    ),
                  )
                : ListView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: _recentEvents.length,
                    itemBuilder: (context, index) {
                      final evt = _recentEvents[index];
                      return Card(
                        color: const Color(0xFF151D30),
                        margin: const EdgeInsets.only(bottom: 8),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                          side: const BorderSide(color: Colors.white10),
                        ),
                        child: ListTile(
                          leading: const CircleAvatar(
                            radius: 16,
                            backgroundColor: Color(0x2610B981),
                            child: Icon(Icons.bolt_rounded, color: Color(0xFF10B981), size: 18),
                          ),
                          title: Text(
                            evt['action'] ?? 'UNKNOWN_ACTION',
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                          ),
                          subtitle: Text(
                            "Author: ${evt['author_pubkey']}\nHash: ${evt['event_id']}",
                            style: const TextStyle(fontFamily: 'monospace', fontSize: 10, color: Color(0xFF94A3B8)),
                          ),
                          isThreeLine: true,
                        ),
                      );
                    },
                  ),
          ],
        ),
      ),
    );
  }

  Widget _buildCard({
    required String title,
    required IconData icon,
    required Color accentColor,
    required Widget child,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF151D30),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: accentColor, size: 20),
              const SizedBox(width: 8),
              Text(
                title,
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: accentColor),
              ),
            ],
          ),
          const Divider(color: Colors.white10, height: 20),
          child,
        ],
      ),
    );
  }

  Widget _buildMetricRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8))),
          Flexible(
            child: SelectableText(
              value,
              style: const TextStyle(fontFamily: 'monospace', fontSize: 12, color: Colors.white, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}
