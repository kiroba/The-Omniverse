import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:omni_core_ui/omni_core_ui.dart';

/// ============================================================================
/// KICKBACK HUB SETTING: which Omni-Hub (daemon) this app talks to
/// ============================================================================
/// - "This phone" (default): the daemon runs in Termux on this phone,
///   127.0.0.1 :5000 / :9100, no token. Same as every earlier build.
/// - "Remote hub": another phone runs the daemon (v8.7.0+, started with
///   OMNI_HUB_REMOTE=1) and this phone reaches it, usually over Tailscale
///   (its 100.x address). Every call sends "Authorization: Bearer <token>".
///   Posts are still signed with this phone's own key.
///
/// Stored in flutter_secure_storage (Android Keystore-encrypted), the token
/// included. See Admin/docs/REMOTE_HUB.md on the desktop branch.
/// ============================================================================
enum HubMode { local, remote }

class HubSettings {
  static const int defaultIpcPort = 5000;
  static const int defaultTelemetryPort = 9100;

  final HubMode mode;
  final String host;
  final int ipcPort;
  final int telemetryPort;
  final String token;

  const HubSettings({
    this.mode = HubMode.local,
    this.host = '',
    this.ipcPort = defaultIpcPort,
    this.telemetryPort = defaultTelemetryPort,
    this.token = '',
  });

  bool get isRemote => mode == HubMode.remote && host.isNotEmpty;

  /// The client for this setting. Remote calls cross the internet, so they get
  /// a longer timeout than loopback.
  OmniHubClient client() => isRemote
      ? OmniHubClient(
          host: host,
          ipcPort: ipcPort,
          telemetryPort: telemetryPort,
          token: token,
          timeout: const Duration(seconds: 4),
        )
      : const OmniHubClient();

  String get label => isRemote ? 'Remote hub $host' : 'This phone (127.0.0.1)';

  /// Cleans what the user typed: drops "http://", a path, and spaces. Returns
  /// (host, port) where port is the IPC port if they typed "host:5000", or
  /// null host when nothing usable is left.
  static ({String? host, int? port}) parseAddress(String input) {
    var a = input.trim();
    a = a.replaceFirst(RegExp(r'^[a-zA-Z][a-zA-Z0-9+.-]*://'), '');
    final slash = a.indexOf('/');
    if (slash >= 0) a = a.substring(0, slash);
    a = a.replaceAll(' ', '');
    if (a.isEmpty) return (host: null, port: null);
    int? port;
    // host:port (but not a bare IPv6 address, which has several colons)
    final colon = a.lastIndexOf(':');
    if (colon > 0 && a.indexOf(':') == colon) {
      port = int.tryParse(a.substring(colon + 1));
      a = a.substring(0, colon);
    } else if (a.startsWith('[') && a.contains(']:')) {
      port = int.tryParse(a.substring(a.indexOf(']:') + 2));
      a = a.substring(1, a.indexOf(']'));
    }
    if (a.startsWith('[') && a.endsWith(']')) a = a.substring(1, a.length - 1);
    if (!RegExp(r'^[A-Za-z0-9.\-:]+$').hasMatch(a)) return (host: null, port: null);
    if (port != null && (port < 1 || port > 65535)) port = null;
    return (host: a, port: port);
  }
}

class HubSettingsStore {
  static const String _kMode = 'kickback_hub_mode_v1';
  static const String _kHost = 'kickback_hub_host_v1';
  static const String _kIpc = 'kickback_hub_ipc_port_v1';
  static const String _kTel = 'kickback_hub_telemetry_port_v1';
  static const String _kToken = 'kickback_hub_token_v1';

  static const FlutterSecureStorage _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  /// Never throws: any storage problem falls back to "This phone".
  static Future<HubSettings> load() async {
    try {
      final mode = await _storage.read(key: _kMode);
      final host = await _storage.read(key: _kHost) ?? '';
      final ipc = int.tryParse(await _storage.read(key: _kIpc) ?? '');
      final tel = int.tryParse(await _storage.read(key: _kTel) ?? '');
      final token = await _storage.read(key: _kToken) ?? '';
      return HubSettings(
        mode: mode == 'remote' && host.isNotEmpty ? HubMode.remote : HubMode.local,
        host: host,
        ipcPort: ipc ?? HubSettings.defaultIpcPort,
        telemetryPort: tel ?? HubSettings.defaultTelemetryPort,
        token: token,
      );
    } catch (_) {
      return const HubSettings();
    }
  }

  static Future<void> save(HubSettings s) async {
    await _storage.write(key: _kMode, value: s.mode == HubMode.remote ? 'remote' : 'local');
    await _storage.write(key: _kHost, value: s.host);
    await _storage.write(key: _kIpc, value: '${s.ipcPort}');
    await _storage.write(key: _kTel, value: '${s.telemetryPort}');
    await _storage.write(key: _kToken, value: s.token);
  }
}
