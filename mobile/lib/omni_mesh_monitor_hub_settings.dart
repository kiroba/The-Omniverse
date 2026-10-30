import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'omni_mesh_telemetry.dart';

/// ============================================================================
/// MESH MONITOR HUB SETTING: which Omni-Hub (daemon) this monitor reads
/// ============================================================================
/// Same pattern as KickBack's Settings > Hub:
/// - "This phone" (default): the daemon runs in Termux on this phone,
///   127.0.0.1 :5000 / :9100, no token.
/// - "Remote hub": another device runs the daemon (v8.7.0+, OMNI_HUB_REMOTE=1),
///   usually reached over Tailscale (its 100.x address). Every call sends
///   "Authorization: Bearer <token>" (the hub's ~/.omni/hub_token).
/// Stored in flutter_secure_storage (Android Keystore-encrypted), token
/// included, under the Mesh Monitor's own keys.
/// ============================================================================
enum MonitorHubMode { local, remote }

class MonitorHubSettings {
  final MonitorHubMode mode;
  final String host;
  final int ipcPort;
  final int telemetryPort;
  final String token;

  const MonitorHubSettings({
    this.mode = MonitorHubMode.local,
    this.host = '',
    this.ipcPort = HubTarget.defaultIpcPort,
    this.telemetryPort = HubTarget.defaultTelemetryPort,
    this.token = '',
  });

  bool get isRemote => mode == MonitorHubMode.remote && host.isNotEmpty;

  HubTarget target() => isRemote
      ? HubTarget(host: host, ipcPort: ipcPort, telemetryPort: telemetryPort, token: token)
      : const HubTarget();

  String get label => isRemote ? 'Remote hub $host' : 'This phone (127.0.0.1)';
}

class MonitorHubSettingsStore {
  static const String _kMode = 'mesh_monitor_hub_mode_v1';
  static const String _kHost = 'mesh_monitor_hub_host_v1';
  static const String _kIpc = 'mesh_monitor_hub_ipc_port_v1';
  static const String _kTel = 'mesh_monitor_hub_telemetry_port_v1';
  static const String _kToken = 'mesh_monitor_hub_token_v1';

  static const FlutterSecureStorage _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  /// Never throws: any storage problem falls back to "This phone".
  static Future<MonitorHubSettings> load() async {
    try {
      final mode = await _storage.read(key: _kMode);
      final host = await _storage.read(key: _kHost) ?? '';
      final ipc = int.tryParse(await _storage.read(key: _kIpc) ?? '');
      final tel = int.tryParse(await _storage.read(key: _kTel) ?? '');
      final token = await _storage.read(key: _kToken) ?? '';
      return MonitorHubSettings(
        mode: mode == 'remote' && host.isNotEmpty ? MonitorHubMode.remote : MonitorHubMode.local,
        host: host,
        ipcPort: ipc ?? HubTarget.defaultIpcPort,
        telemetryPort: tel ?? HubTarget.defaultTelemetryPort,
        token: token,
      );
    } catch (_) {
      return const MonitorHubSettings();
    }
  }

  static Future<void> save(MonitorHubSettings s) async {
    await _storage.write(key: _kMode, value: s.mode == MonitorHubMode.remote ? 'remote' : 'local');
    await _storage.write(key: _kHost, value: s.host);
    await _storage.write(key: _kIpc, value: '${s.ipcPort}');
    await _storage.write(key: _kTel, value: '${s.telemetryPort}');
    await _storage.write(key: _kToken, value: s.token);
  }
}
