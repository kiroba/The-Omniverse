import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'hub_feed.dart';

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
///
/// Remote hub (daemon v8.7.0+, OMNI_HUB_REMOTE=1): [host] can be another
/// phone's address (e.g. its Tailscale 100.x IP). Then [token] is sent as
/// "Authorization: Bearer <token>" on every call, and the hub answers 401 if
/// it is missing or wrong. Posts still carry this phone's own signature; the
/// remote hub stores them with this phone as the author and never re-signs.
class OmniHubClient {
  final String host;
  final int telemetryPort;
  final int ipcPort;
  final Duration timeout;

  /// Bearer token for a remote hub. Null/empty = no Authorization header (loopback).
  final String? token;

  const OmniHubClient({
    this.host = '127.0.0.1',
    this.telemetryPort = 9100,
    this.ipcPort = 5000,
    this.timeout = const Duration(milliseconds: 1500),
    this.token,
  });

  /// True when this client talks to a hub on another device.
  bool get isRemote => !(host == '127.0.0.1' || host == 'localhost' || host == '::1');

  /// Where the hub is, for status text: "127.0.0.1" or "100.x.y.z".
  String get address => host;

  void _auth(HttpClientRequest req) {
    final t = token;
    if (t != null && t.isNotEmpty) {
      req.headers.set(HttpHeaders.authorizationHeader, 'Bearer $t');
    }
  }

  /// One call to node-health that says whether the hub is reachable and whether
  /// it accepted our token. Never throws.
  Future<HubConnection> connection() async {
    final client = HttpClient()..connectionTimeout = timeout;
    try {
      final req = await client
          .getUrl(Uri(scheme: 'http', host: host, port: telemetryPort, path: '/api/v1/telemetry/node-health'))
          .timeout(timeout);
      _auth(req);
      final res = await req.close().timeout(timeout);
      final text = await res.transform(utf8.decoder).join().timeout(timeout);
      if (res.statusCode == 401) {
        return const HubConnection(HubConnectionState.unauthorized, detail: 'hub refused the token (HTTP 401)');
      }
      if (res.statusCode == 403) {
        return const HubConnection(HubConnectionState.forbidden,
            detail: 'hub is not in remote mode (HTTP 403): start it with OMNI_HUB_REMOTE=1');
      }
      if (res.statusCode != 200) {
        return HubConnection(HubConnectionState.error, detail: 'HTTP ${res.statusCode}');
      }
      final h = _decode(text);
      if (h == null) return const HubConnection(HubConnectionState.error, detail: 'unexpected reply');
      return HubConnection(HubConnectionState.connected, status: HubStatus.fromHealth(h));
    } catch (e) {
      return HubConnection(HubConnectionState.unreachable, detail: '$e');
    } finally {
      client.close(force: true);
    }
  }

  Future<Map<String, dynamic>?> nodeHealth() => _get(telemetryPort, '/api/v1/telemetry/node-health');
  Future<Map<String, dynamic>?> omnimindTelemetry() => _get(telemetryPort, '/api/omnimind/telemetry');
  Future<Map<String, dynamic>?> eventStats() => _get(ipcPort, '/api/events/stats');

  /// Hands an event to the hub. The hub sets itself as author and signs it.
  /// [tsMs] (integer ms) becomes the event's signed "ts"; leave it null and the
  /// daemon stamps its own time. Returns null only when the hub is unreachable;
  /// a refusal comes back as {"status": "ERROR", "message": ...}.
  Future<Map<String, dynamic>?> appendEvent(String action, Map<String, dynamic> payload, {int? tsMs}) =>
      _post(ipcPort, '/api/events/append', {
        'action': action,
        'payload': payload,
        if (tsMs != null) 'ts': tsMs,
      });

  /// Reads the daemon's event feed (`GET :5000/api/events/feed`, daemon v8.6.0+),
  /// newest first. [before] pages back in history; [since] returns only rows
  /// newer than that row id (polling). [type] filters by action.
  /// Never throws: the result's state says whether the daemon answered
  /// ([HubFeedState.ok]), is too old ([HubFeedState.unsupported], HTTP 404),
  /// is not running ([HubFeedState.unreachable]) or failed ([HubFeedState.error]).
  Future<HubFeedResult> eventsFeed({int limit = 50, int? before, int? since, String? type}) async {
    final uri = Uri(
      scheme: 'http',
      host: host,
      port: ipcPort,
      path: '/api/events/feed',
      queryParameters: <String, String>{
        'limit': '$limit',
        if (before != null) 'before': '$before',
        if (since != null) 'since': '$since',
        if (type != null) 'type': type,
      },
    );
    final client = HttpClient()..connectionTimeout = timeout;
    int? code;
    try {
      final req = await client.getUrl(uri).timeout(timeout);
      _auth(req);
      final res = await req.close().timeout(timeout);
      code = res.statusCode;
      final body = await res.transform(utf8.decoder).join().timeout(timeout);
      if (code == 401) {
        return const HubFeedResult(
            state: HubFeedState.error, error: 'unauthorized (HTTP 401): check the hub token in Settings > Hub');
      }
      return HubFeedResult.fromResponse(code, body);
    } catch (e) {
      if (code != null) {
        return HubFeedResult(state: HubFeedState.error, error: 'HTTP $code: $e');
      }
      return HubFeedResult(state: HubFeedState.unreachable, error: '$e');
    } finally {
      client.close(force: true);
    }
  }

  /// Simple, human-readable status for badges.
  Future<HubStatus> status() async {
    final h = await nodeHealth();
    if (h == null) return const HubStatus(online: false, peers: 0);
    return HubStatus.fromHealth(h);
  }

  Future<Map<String, dynamic>?> _get(int port, String path) async {
    final client = HttpClient()..connectionTimeout = timeout;
    try {
      final req = await client.getUrl(Uri.parse('http://${_hostForUrl()}:$port$path')).timeout(timeout);
      _auth(req);
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
      final req = await client.postUrl(Uri.parse('http://${_hostForUrl()}:$port$path')).timeout(timeout);
      _auth(req);
      req.headers.contentType = ContentType.json;
      // Always send Content-Length. Without it dart:io sends "Transfer-Encoding: chunked", which
      // daemons up to v8.12.0 read as an empty body: every post was stored as an empty
      // USER_ACTION event and never showed up in ?type=KICKBACK_POST (see
      // Admin/docs/REQUEST_BODIES.md on the desktop branch).
      final bytes = utf8.encode(jsonEncode(body));
      req.contentLength = bytes.length;
      req.add(bytes);
      final res = await req.close().timeout(timeout);
      final text = await res.transform(utf8.decoder).join().timeout(timeout);
      try {
        final decoded = _decode(text);
        if (decoded != null) return decoded;
      } catch (_) {}
      // Reached the hub, but it answered with a non-JSON error page.
      return {'status': 'ERROR', 'message': 'HTTP ${res.statusCode}'};
    } catch (_) {
      return null;
    } finally {
      client.close(force: true);
    }
  }

  String _hostForUrl() => host.contains(':') && !host.startsWith('[') ? '[$host]' : host;

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
  final String? meshId;
  const HubStatus({required this.online, required this.peers, this.nodeId, this.version, this.meshId});

  factory HubStatus.fromHealth(Map<String, dynamic> h) {
    final peers = h['active_peers'];
    return HubStatus(
      online: '${h['status']}'.toUpperCase() == 'ONLINE',
      peers: peers is int ? peers : int.tryParse('$peers') ?? 0,
      nodeId: h['node_id']?.toString(),
      version: h['version']?.toString(),
      meshId: h['mesh_id']?.toString(),
    );
  }
}

/// How the last [OmniHubClient.connection] check went.
enum HubConnectionState {
  /// The hub answered node-health (and accepted the token, if remote).
  connected,

  /// The hub is there but refused the token (HTTP 401).
  unauthorized,

  /// The hub is there but not serving remote phones (HTTP 403, remote mode off).
  forbidden,

  /// Nothing answered (daemon off, Tailscale off, wrong address).
  unreachable,

  /// Any other answer.
  error,
}

class HubConnection {
  final HubConnectionState state;
  final HubStatus status;
  final String? detail;
  const HubConnection(this.state, {this.status = const HubStatus(online: false, peers: 0), this.detail});

  bool get connected => state == HubConnectionState.connected;
}
