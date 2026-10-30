import 'dart:async';

import 'package:flutter/material.dart';

import 'package:omni_core_ui/omni_core_ui.dart';

import 'omni_mesh_monitor_hub_settings.dart';
import 'omni_mesh_telemetry.dart';

/// ============================================================================
/// MOBILE MESH MONITOR (LIVE TELEMETRY DASHBOARD)
/// ============================================================================
/// Reads one Omni-Hub (the daemon on this phone in Termux, or a remote hub over
/// Tailscale with its bearer token, set in Hub settings) every 12 seconds and
/// on pull-to-refresh:
///   Hub v8.12.0+: GET :5000/api/telemetry/summary (aggregate counts only)
///   Older hubs:   node-health + events/stats + events/feed, with the sections
///                 that need v8.12.0 marked as such.
/// Sections: Protocols / Security / Finance / Users / Services.
/// Nothing on screen is invented: a value the hub doesn't report is shown as
/// "not reported", and areas nothing feeds yet are "Not wired yet" tiles that
/// name what would feed them (see omni_mesh_telemetry.dart).
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
  static const Duration _pollEvery = Duration(seconds: 12);
  static const Color _teal = Color(0xFF03DAC6);
  static const Color _red = Color(0xFFFF5370);
  static const Color _amber = Color(0xFFFFCB6B);
  static const Color _purple = Color(0xFFBB86FC);
  static const Color _panel = Color(0xFF161B22);
  static const Color _tileBg = Color(0xFF21262D);

  static const List<({String title, IconData icon})> _tabs = [
    (title: 'Protocols', icon: Icons.hub),
    (title: 'Security', icon: Icons.verified_user_outlined),
    (title: 'Finance', icon: Icons.account_balance_wallet_outlined),
    (title: 'Users', icon: Icons.people_outline),
    (title: 'Services', icon: Icons.dns_outlined),
  ];

  int _selectedTab = 0;
  MonitorHubSettings _settings = const MonitorHubSettings();
  Timer? _timer;
  bool _polling = false;
  HubSnapshot? _snap;

  String get _appBuild => OmniOta.currentBuild == 0 ? 'dev' : '${OmniOta.currentBuild}';

  @override
  void initState() {
    super.initState();
    _init();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) OmniOta.checkAndPrompt(context, silent: true);
    });
  }

  Future<void> _init() async {
    final s = await MonitorHubSettingsStore.load();
    if (!mounted) return;
    setState(() => _settings = s);
    await _poll();
    if (!mounted) return;
    _timer = Timer.periodic(_pollEvery, (_) => _poll());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _poll() async {
    if (_polling) return;
    _polling = true;
    try {
      final snap = await TelemetryClient(_settings.target()).fetch();
      if (!mounted) return;
      setState(() => _snap = snap);
    } finally {
      _polling = false;
    }
  }

  // ---------------------------------------------------------------- settings

  Future<void> _openHubSettings() async {
    final result = await showDialog<MonitorHubSettings>(
      context: context,
      builder: (ctx) => _HubSettingsDialog(initial: _settings),
    );
    if (result == null) return;
    try {
      await MonitorHubSettingsStore.save(result);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Could not save to secure storage; using it for this session')));
      }
    }
    if (!mounted) return;
    setState(() {
      _settings = result;
      _snap = null;
    });
    _poll();
  }

  // ------------------------------------------------------------------- build

  @override
  Widget build(BuildContext context) {
    final snap = _snap;
    final sections = snap == null ? null : buildSections(snap, appBuild: _appBuild);
    return Scaffold(
      appBar: AppBar(
        backgroundColor: _panel,
        elevation: 2,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Omniverse Mesh Monitor', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            Text(_subtitle(snap), style: TextStyle(color: _headerColor(snap), fontSize: 10, letterSpacing: 0.5)),
          ],
        ),
        actions: [
          IconButton(icon: const Icon(Icons.settings_ethernet), tooltip: 'Hub settings', onPressed: _openHubSettings),
          IconButton(icon: const Icon(Icons.refresh), tooltip: 'Refresh now', onPressed: _poll),
          IconButton(
            icon: const Icon(Icons.system_update),
            tooltip: 'Check for updates',
            onPressed: () => OmniOta.checkAndPrompt(context),
          ),
        ],
      ),
      body: sections == null
          ? const Center(child: CircularProgressIndicator())
          : IndexedStack(
              index: _selectedTab,
              children: [for (final s in sections) _buildSection(snap!, s)],
            ),
      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed,
        currentIndex: _selectedTab,
        onTap: (i) => setState(() => _selectedTab = i),
        backgroundColor: _panel,
        selectedItemColor: _teal,
        unselectedItemColor: Colors.grey,
        selectedFontSize: 11,
        unselectedFontSize: 10,
        items: [for (final t in _tabs) BottomNavigationBarItem(icon: Icon(t.icon), label: t.title)],
      ),
    );
  }

  String _subtitle(HubSnapshot? snap) {
    final where = _settings.isRemote ? _settings.host : '127.0.0.1';
    if (snap == null) return 'CONNECTING • $where';
    final v = snap.version == null ? '' : ' • v${snap.version}';
    return '${hubStateLabel(snap.state)} • $where$v';
  }

  Color _headerColor(HubSnapshot? snap) {
    switch (snap?.state) {
      case HubState.live:
        return _teal;
      case HubState.legacy:
        return _amber;
      case null:
        return Colors.grey;
      default:
        return _red;
    }
  }

  Widget _buildSection(HubSnapshot snap, TelemetrySection section) {
    return RefreshIndicator(
      onRefresh: _poll,
      color: _teal,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          _connectionBanner(snap),
          _sectionHeader(section),
          const SizedBox(height: 12),
          for (final t in section.tiles) _tile(t),
          _footer(snap),
        ],
      ),
    );
  }

  Widget _connectionBanner(HubSnapshot snap) {
    final String text;
    Color color = _red;
    switch (snap.state) {
      case HubState.live:
        return const SizedBox.shrink();
      case HubState.legacy:
        color = _amber;
        text = 'This hub is v${snap.version ?? '?'}, older than v$kTelemetrySummaryMinVersion. '
            'Showing what its older endpoints report; update the daemon for the full dashboard.';
        break;
      case HubState.unauthorized:
        text = 'The hub refused the token (HTTP 401). Open Hub settings and paste the token from the hub\'s '
            '~/.omni/hub_token.';
        break;
      case HubState.forbidden:
        text = 'The hub is up but not serving remote phones (HTTP 403). Start it with OMNI_HUB_REMOTE=1 and '
            'OMNI_HUB_BIND set (see Admin/docs/REMOTE_HUB.md).';
        break;
      case HubState.offline:
        text = _settings.isRemote
            ? 'Nothing answered at ${_settings.host}:${_settings.ipcPort}. Is the hub running and Tailscale connected?'
            : 'No daemon on this phone. Start it in Termux:  bash Admin/start_local_stack.sh\n'
                'Or point Hub settings at a remote hub.';
        break;
      case HubState.error:
        text = 'The hub answered unexpectedly: ${snap.detail}';
        break;
    }
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withAlpha(30),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withAlpha(120)),
      ),
      child: Text(text, style: const TextStyle(fontSize: 12, color: Colors.white70)),
    );
  }

  Widget _sectionHeader(TelemetrySection section) {
    final icon = _tabs.firstWhere((t) => t.title == section.title, orElse: () => _tabs.first).icon;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _purple.withAlpha(100)),
      ),
      child: Row(
        children: [
          CircleAvatar(backgroundColor: _purple.withAlpha(50), child: Icon(icon, color: _purple)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(section.title,
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Colors.white)),
                const SizedBox(height: 4),
                Text(section.source, style: const TextStyle(color: Colors.grey, fontSize: 11)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  ({String label, Color color}) _chip(TileStatus s) {
    switch (s) {
      case TileStatus.ok:
        return (label: 'OK', color: _teal);
      case TileStatus.warn:
        return (label: 'CHECK', color: _amber);
      case TileStatus.bad:
        return (label: 'DOWN', color: _red);
      case TileStatus.idle:
        return (label: 'INFO', color: Colors.blueGrey);
      case TileStatus.off:
        return (label: 'OFF', color: Colors.grey);
      case TileStatus.notWired:
        return (label: 'NOT WIRED', color: Colors.grey);
      case TileStatus.unknown:
        return (label: 'UNKNOWN', color: Colors.grey);
    }
  }

  Widget _tile(TelemetryTile t) {
    final chip = _chip(t.status);
    final dim = t.status == TileStatus.notWired;
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      color: dim ? const Color(0xFF181C22) : _tileBg,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: dim ? BorderSide(color: Colors.grey.withAlpha(60)) : BorderSide.none,
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(t.label,
                      style: TextStyle(fontSize: 12, color: dim ? Colors.grey : Colors.white70,
                          fontWeight: FontWeight.w600)),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: chip.color.withAlpha(40),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: chip.color.withAlpha(140)),
                  ),
                  child: Text(chip.label,
                      style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: chip.color, letterSpacing: 0.5)),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(t.value,
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: dim ? Colors.grey : Colors.white)),
            if (t.detail != null && t.detail!.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(t.detail!, style: const TextStyle(fontSize: 11, color: Colors.grey)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _footer(HubSnapshot snap) {
    final t = snap.fetchedAt;
    final stamp =
        '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}:${t.second.toString().padLeft(2, '0')}';
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Text(
        'Last poll $stamp • every ${_pollEvery.inSeconds}s • pull down to refresh • ${_settings.label}',
        style: const TextStyle(color: Colors.grey, fontSize: 11),
      ),
    );
  }
}

/// Hub settings: This phone, or a remote hub (host, ports, bearer token).
class _HubSettingsDialog extends StatefulWidget {
  final MonitorHubSettings initial;
  const _HubSettingsDialog({required this.initial});

  @override
  State<_HubSettingsDialog> createState() => _HubSettingsDialogState();
}

class _HubSettingsDialogState extends State<_HubSettingsDialog> {
  late MonitorHubMode _mode = widget.initial.mode;
  late final TextEditingController _host = TextEditingController(text: widget.initial.host);
  late final TextEditingController _ipc = TextEditingController(text: '${widget.initial.ipcPort}');
  late final TextEditingController _tel = TextEditingController(text: '${widget.initial.telemetryPort}');
  late final TextEditingController _token = TextEditingController(text: widget.initial.token);
  bool _showToken = false;
  String? _error;

  @override
  void dispose() {
    _host.dispose();
    _ipc.dispose();
    _tel.dispose();
    _token.dispose();
    super.dispose();
  }

  void _save() {
    if (_mode == MonitorHubMode.local) {
      Navigator.pop(context, MonitorHubSettings(
        mode: MonitorHubMode.local,
        host: widget.initial.host,
        ipcPort: widget.initial.ipcPort,
        telemetryPort: widget.initial.telemetryPort,
        token: widget.initial.token,
      ));
      return;
    }
    final parsed = HubTarget.parseAddress(_host.text);
    if (parsed.host == null) {
      setState(() => _error = 'Enter the hub address, e.g. 100.101.102.103');
      return;
    }
    final ipc = parsed.port ?? int.tryParse(_ipc.text.trim()) ?? HubTarget.defaultIpcPort;
    final tel = int.tryParse(_tel.text.trim()) ?? HubTarget.defaultTelemetryPort;
    if (ipc < 1 || ipc > 65535 || tel < 1 || tel > 65535) {
      setState(() => _error = 'Ports must be 1-65535');
      return;
    }
    if (_token.text.trim().isEmpty) {
      setState(() => _error = 'A remote hub needs its token (~/.omni/hub_token on the hub)');
      return;
    }
    Navigator.pop(context, MonitorHubSettings(
      mode: MonitorHubMode.remote,
      host: parsed.host!,
      ipcPort: ipc,
      telemetryPort: tel,
      token: _token.text.trim(),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final remote = _mode == MonitorHubMode.remote;
    return AlertDialog(
      title: const Text('Hub'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            RadioListTile<MonitorHubMode>(
              contentPadding: EdgeInsets.zero,
              value: MonitorHubMode.local,
              groupValue: _mode,
              onChanged: (v) => setState(() => _mode = v!),
              title: const Text('This phone'),
              subtitle: const Text('Daemon in Termux on 127.0.0.1', style: TextStyle(fontSize: 11)),
            ),
            RadioListTile<MonitorHubMode>(
              contentPadding: EdgeInsets.zero,
              value: MonitorHubMode.remote,
              groupValue: _mode,
              onChanged: (v) => setState(() => _mode = v!),
              title: const Text('Remote hub'),
              subtitle: const Text('Another device over Tailscale (needs its token)', style: TextStyle(fontSize: 11)),
            ),
            if (remote) ...[
              TextField(
                controller: _host,
                keyboardType: TextInputType.url,
                decoration: const InputDecoration(labelText: 'Hub address', hintText: '100.101.102.103'),
              ),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _ipc,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(labelText: 'Events port'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: _tel,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(labelText: 'Telemetry port'),
                    ),
                  ),
                ],
              ),
              TextField(
                controller: _token,
                obscureText: !_showToken,
                autocorrect: false,
                enableSuggestions: false,
                decoration: InputDecoration(
                  labelText: 'Hub token',
                  suffixIcon: IconButton(
                    icon: Icon(_showToken ? Icons.visibility_off : Icons.visibility),
                    onPressed: () => setState(() => _showToken = !_showToken),
                  ),
                ),
              ),
            ],
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_error!, style: const TextStyle(color: Color(0xFFFF5370), fontSize: 12)),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
        TextButton(onPressed: _save, child: const Text('Save')),
      ],
    );
  }
}
