import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';

/// ============================================================================
/// MOBILE MESH MONITOR (LIVE)
/// ============================================================================
/// Reads the real Omniverse daemon running on this phone (Termux) or on another
/// host you type in. Polls every 2 seconds:
///   GET :9100/api/v1/telemetry/node-health   (daemon + peers)
///   GET :9100/api/omnimind/telemetry         (OmniMind agent, 404 = idle)
///   GET :5000/api/events/stats               (Merkle DAG / SQLite WAL)
/// Nothing on screen is hardcoded: a value the daemon does not report is shown
/// as "not reported". Uses dart:io only (no extra packages).
/// ============================================================================

void main() => runApp(const MobileMeshMonitorApp());

class MobileMeshMonitorApp extends StatelessWidget {
  const MobileMeshMonitorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Omniverse Mesh Monitor',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        primaryColor: const Color(0xFF03DAC6),
        scaffoldBackgroundColor: const Color(0xFF0D1117),
        cardColor: const Color(0xFF161B22),
      ),
      home: const MeshMonitorMainScreen(),
    );
  }
}

class MeshMonitorMainScreen extends StatefulWidget {
  const MeshMonitorMainScreen({super.key});

  @override
  State<MeshMonitorMainScreen> createState() => _MeshMonitorMainScreenState();
}

class _MeshMonitorMainScreenState extends State<MeshMonitorMainScreen> {
  static const Color _teal = Color(0xFF03DAC6);
  static const Color _red = Color(0xFFFF5370);

  int _selectedTab = 0;
  String _host = '127.0.0.1';
  Timer? _timer;
  bool _polling = false;

  Map<String, dynamic>? _node;
  Map<String, dynamic>? _omnimind;
  Map<String, dynamic>? _stats;
  String _nodeError = '';
  DateTime? _lastPoll;

  @override
  void initState() {
    super.initState();
    _poll();
    _timer = Timer.periodic(const Duration(seconds: 2), (_) => _poll());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<Map<String, dynamic>?> _getJson(int port, String path, {bool recordError = false}) async {
    final client = HttpClient()..connectionTimeout = const Duration(milliseconds: 1500);
    try {
      final req = await client.getUrl(Uri.parse('http://$_host:$port$path'));
      final res = await req.close().timeout(const Duration(milliseconds: 1500));
      final body = await res.transform(utf8.decoder).join();
      if (res.statusCode != 200) {
        if (recordError) _nodeError = 'HTTP ${res.statusCode}';
        return null;
      }
      final decoded = jsonDecode(body);
      return decoded is Map<String, dynamic> ? decoded : null;
    } catch (e) {
      if (recordError) _nodeError = e.runtimeType.toString();
      return null;
    } finally {
      client.close(force: true);
    }
  }

  Future<void> _poll() async {
    if (_polling) return;
    _polling = true;
    try {
      final node = await _getJson(9100, '/api/v1/telemetry/node-health', recordError: true);
      final omni = await _getJson(9100, '/api/omnimind/telemetry');
      final stats = await _getJson(5000, '/api/events/stats');
      if (!mounted) return;
      setState(() {
        _node = node;
        if (node != null) _nodeError = '';
        _omnimind = omni;
        _stats = stats;
        _lastPoll = DateTime.now();
      });
    } finally {
      _polling = false;
    }
  }

  String _v(Map<String, dynamic>? m, String key) {
    if (m == null || m[key] == null) return 'not reported';
    final value = m[key];
    if (value is List) return value.isEmpty ? 'none' : value.join(', ');
    return value.toString();
  }

  String _short(String s) => s.length > 22 ? '${s.substring(0, 22)}...' : s;

  Future<void> _editHost() async {
    final controller = TextEditingController(text: _host);
    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Daemon host'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.url,
          decoration: const InputDecoration(hintText: '127.0.0.1 (same phone, Termux)'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, controller.text.trim()), child: const Text('Save')),
        ],
      ),
    );
    if (result != null && result.isNotEmpty) {
      setState(() => _host = result);
      _poll();
    }
  }

  @override
  Widget build(BuildContext context) {
    final online = _node != null;
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Omniverse Mesh Monitor', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            Text(
              online ? 'LIVE • $_host • daemon ${_v(_node, 'version')}' : 'OFFLINE • waiting for daemon on $_host',
              style: TextStyle(color: online ? _teal : _red, fontSize: 10, letterSpacing: 0.5),
            ),
          ],
        ),
        backgroundColor: const Color(0xFF161B22),
        elevation: 2,
        actions: [
          IconButton(icon: const Icon(Icons.dns_outlined), tooltip: 'Change host', onPressed: _editHost),
          IconButton(icon: const Icon(Icons.refresh), tooltip: 'Refresh now', onPressed: _poll),
        ],
      ),
      body: IndexedStack(
        index: _selectedTab,
        children: [
          _buildDaemonTab(),
          _buildOmniMindTab(),
          _buildLedgerTab(),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedTab,
        onTap: (index) => setState(() => _selectedTab = index),
        backgroundColor: const Color(0xFF161B22),
        selectedItemColor: _teal,
        unselectedItemColor: Colors.grey,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.hub), label: 'Daemon'),
          BottomNavigationBarItem(icon: Icon(Icons.smart_toy_outlined), label: 'OmniMind'),
          BottomNavigationBarItem(icon: Icon(Icons.account_tree_outlined), label: 'Ledger'),
        ],
      ),
    );
  }

  Widget _footer() {
    final t = _lastPoll;
    final stamp = t == null
        ? 'never'
        : '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}:${t.second.toString().padLeft(2, '0')}';
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Text('Last poll $stamp • every 2s', style: const TextStyle(color: Colors.grey, fontSize: 11)),
    );
  }

  Widget _buildDaemonTab() {
    final online = _node != null;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildMetricHeaderCard('Daemon & P2P', 'GET :9100/api/v1/telemetry/node-health', Icons.hub, const Color(0xFFBB86FC)),
        const SizedBox(height: 12),
        _buildStatusRow('Status', online ? 'ONLINE' : 'OFFLINE${_nodeError.isEmpty ? '' : ' ($_nodeError)'}', online ? _teal : _red),
        if (!online)
          _hint('Start it in Termux:  bash Admin/start_local_stack.sh\n'
              'Ports 9100 and 5000 only listen on 127.0.0.1, so run the daemon on this same phone.'),
        if (online) ...[
          _buildStatusRow('Node ID', _short(_v(_node, 'node_id')), Colors.white),
          _buildStatusRow('Daemon version', _v(_node, 'version'), Colors.white),
          _buildStatusRow('Local IP', _v(_node, 'local_ip'), Colors.white),
          _buildStatusRow('P2P sync port', _v(_node, 'p2p_sync_port'), Colors.white),
          _buildStatusRow('Active peers', _v(_node, 'active_peers'), _teal),
          _buildStatusRow('Peer IPs', _v(_node, 'peer_ips'), Colors.white),
          _buildStatusRow('Uptime', '${_v(_node, 'uptime_seconds')} s', Colors.white),
        ],
        _footer(),
      ],
    );
  }

  Widget _buildOmniMindTab() {
    final live = _omnimind != null;
    final integrity = _v(_omnimind, 'chain_integrity');
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildMetricHeaderCard('OmniMind Agent', 'GET :9100/api/omnimind/telemetry', Icons.smart_toy_outlined, const Color(0xFFE91E63)),
        const SizedBox(height: 12),
        _buildStatusRow('Agent', live ? 'ACTIVE' : 'IDLE (no agent posting)', live ? _teal : Colors.grey),
        if (live) ...[
          _buildStatusRow('Agent ID', _v(_omnimind, 'agent_id'), Colors.white),
          _buildStatusRow('Current action', _short(_v(_omnimind, 'action')), _teal),
          _buildStatusRow('Events audited', _v(_omnimind, 'events_processed'), Colors.white),
          _buildStatusRow('Chain integrity', integrity, integrity == 'VERIFIED' ? _teal : _red),
          _buildStatusRow('Last verified', _short(_v(_omnimind, 'last_verified_event')), Colors.white),
          _buildStatusRow('Report age', '${_v(_omnimind, 'age_seconds')} s', Colors.white),
        ],
        _footer(),
      ],
    );
  }

  Widget _buildLedgerTab() {
    final live = _stats != null;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildMetricHeaderCard('Merkle DAG Ledger', 'GET :5000/api/events/stats', Icons.account_tree_outlined, _teal),
        const SizedBox(height: 12),
        _buildStatusRow('Ledger', live ? 'REACHABLE' : 'UNAVAILABLE', live ? _teal : _red),
        if (live) ...[
          _buildStatusRow('Total events', _v(_stats, 'total_events'), Colors.white),
          _buildStatusRow('Storage mode', _v(_stats, 'db_mode'), Colors.white),
          _buildStatusRow('Latest Merkle hash', _short(_v(_stats, 'last_merkle_hash')), _teal),
        ],
        _footer(),
      ],
    );
  }

  Widget _hint(String text) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: const Color(0xFF21262D), borderRadius: BorderRadius.circular(8)),
      child: Text(text, style: const TextStyle(fontSize: 12, color: Colors.white70)),
    );
  }

  Widget _buildMetricHeaderCard(String title, String subtitle, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF161B22),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Row(
        children: [
          CircleAvatar(backgroundColor: color.withOpacity(0.2), child: Icon(icon, color: color)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Colors.white)),
                const SizedBox(height: 4),
                Text(subtitle, style: const TextStyle(color: Colors.grey, fontSize: 11)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusRow(String label, String value, Color valueColor) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      color: const Color(0xFF21262D),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
            const SizedBox(width: 12),
            Flexible(
              child: Text(
                value,
                textAlign: TextAlign.right,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: valueColor),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
