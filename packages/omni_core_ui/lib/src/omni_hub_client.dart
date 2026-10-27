import 'dart:async';
import 'dart:convert';
import 'dart:io';

/// The app's single door to the outside world: the Omni-Hub.
///
/// The Omni-Hub is the local daemon (Admin/start_local_stack.sh, in Termux on
/// the same phone today). Apps only ever talk to it over loopback:
///   :9100  telemetry   (node health, OmniMind)
///   :5000  IPC gateway (append events, event stats)
/// The daemon signs events with the node key, stores them, and is the only
/// thing that speaks to peers (P2P sync on :5005, UDP discovery on :9101).
/// Apps never open :5005 or reach peers themselves, so there is exactly one
/// outward-facing API to secure and version.
class OmniHubClient {
  final String host;
  final int telemetryPort;
  final int ipcPort;
  final Duration timeout;

  const OmniHubClient({
    this.host = '127.0.0.1',
    this.telemetryPort = 9100,
    this.ipcPort = 5000,
    this.timeout = const Duration(milliseconds: 1500),
  });

  Future<Map<String, dynamic>?> nodeHealth() => _get(telemetryPort, '/api/v1/telemetry/node-health');
  Future<Map<String, dynamic>?> omnimindTelemetry() => _get(telemetryPort, '/api/omnimind/telemetry');
  Future<Map<String, dynamic>?> eventStats() => _get(ipcPort, '/api/events/stats');

  /// Hands an event to the hub. The hub sets itself as author and signs it.
  Future<Map<String, dynamic>?> appendEvent(String action, Map<String, dynamic> payload) =>
      _post(ipcPort, '/api/events/append', {'action': action, 'payload': payload});

  /// Simple, human-readable status for badges.
  Future<HubStatus> status() async {
    final h = await nodeHealth();
    if (h == null) return const HubStatus(online: false, peers: 0);
    final peers = h['active_peers'];
    return HubStatus(
      online: '${h['status']}'.toUpperCase() == 'ONLINE',
      peers: peers is int ? peers : int.tryParse('$peers') ?? 0,
      nodeId: h['node_id']?.toString(),
      version: h['version']?.toString(),
    );
  }

  Future<Map<String, dynamic>?> _get(int port, String path) async {
    final client = HttpClient()..connectionTimeout = timeout;
    try {
      final req = await client.getUrl(Uri.parse('http://$host:$port$path')).timeout(timeout);
      final res = await req.close().timeout(timeout);
      if (res.statusCode != 200) return null;
      return _decode(await res.transform(utf8.decoder).join().timeout(timeout));
    } catch (_) {
      return null;
    } finally {
      client.close(force: true);
    }
  }

  Future<Map<String, dynamic>?> _post(int port, String path, Map<String, dynamic> body) async {
    final client = HttpClient()..connectionTimeout = timeout;
    try {
      final req = await client.postUrl(Uri.parse('http://$host:$port$path')).timeout(timeout);
      req.headers.contentType = ContentType.json;
      req.write(jsonEncode(body));
      final res = await req.close().timeout(timeout);
      return _decode(await res.transform(utf8.decoder).join().timeout(timeout));
    } catch (_) {
      return null;
    } finally {
      client.close(force: true);
    }
  }

  Map<String, dynamic>? _decode(String s) {
    final d = jsonDecode(s);
    return d is Map<String, dynamic> ? d : null;
  }
}

class HubStatus {
  final bool online;
  final int peers;
  final String? nodeId;
  final String? version;
  const HubStatus({required this.online, required this.peers, this.nodeId, this.version});
}
