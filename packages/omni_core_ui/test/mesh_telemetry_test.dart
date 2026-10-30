import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import '../../../mobile/lib/omni_mesh_telemetry.dart';

// Real output of daemon v8.12.0 GET :5000/api/telemetry/summary after one local post, one peer event,
// one forged peer event, a bug report, a welcome credit grant and one OmniCast signal (temp ports).
const String kSummaryVector = r'''{"status": "OK", "schema": 1, "version": "8.12.0", "generated_at_ms": 1793331382623, "counters_since_ms": 1793331382504, "counters_note": "since-start counters are in memory and reset when the daemon restarts", "protocols": [{"id": "tcp_api", "name": "TCP app API (:49451 telemetry, :51899 events)", "state": "up", "listen": ["127.0.0.1"], "ports": [49451, 51899], "remote_hub": false, "last_seen_ago_s": 0.0, "counts": {"loopback_requests": 6, "remote_requests": 0}}, {"id": "p2p_sync", "name": "P2P event sync (HTTP :58625 /p2p/sync)", "state": "up", "listen": ["0.0.0.0"], "ports": [58625], "last_seen_ago_s": 0.0, "counts": {"requests": 2, "events_from_peers": 1, "relay_ok": 0, "relay_failed": 0, "rejected_mesh": 0}}, {"id": "udp_discovery", "name": "UDP LAN discovery beacons (:59297)", "state": "up", "detail": "listening", "ports": [59297], "last_seen_ago_s": null, "last_sent_ago_s": 0.1, "active_peers": 0, "peer_pubkey_prefixes": [], "require_signed": false, "counts": {"sent": 1, "accepted": 0, "rejected_signature": 0, "rejected_mesh": 0}}, {"id": "negentropy", "name": "Catch-up sync (negentropy v1)", "state": "idle", "static_peers": 0, "interval_s": 0.0, "last_run": null, "last_seen_ago_s": null, "counts": {"served_reconcile": 0, "served_events": 0, "denied_unknown_peer": 0}}, {"id": "signaling", "name": "OmniCast signaling mailbox (memory only)", "state": "up", "queued": 1, "recipients": 1, "ttl_s": 60, "last_seen_ago_s": 0.0, "counts": {"sends_ok": 1, "sends_rejected": 0, "polls_ok": 0, "delivered": 0, "ice_config_ok": 0}}, {"id": "turn", "name": "TURN relay credentials (ice-config)", "state": "off", "configured": false, "detail": "STUN only", "last_seen_ago_s": null}], "security": {"events_stored_local_signed": 3, "events_verified_from_peers": 1, "events_rejected_signature": 1, "events_rejected_untrusted": 0, "events_rejected_invalid": 0, "events_duplicate": 0, "last_signature_reject_ago_s": 0.0, "signal_sends_rejected": 0, "signal_sends_rejected_by_status": {}, "signal_polls_rejected": 0, "beacons_rejected_signature": 0, "bearer_auth_failures": 0, "last_bearer_failure_ago_s": null, "remote_denied_loopback_only": 0, "trusted_keys_allowlist": null, "remote_hub": false, "hub_token_age_s": null, "unsigned_rows_in_store": 1}, "finance": {"state": "ok", "test_only": true, "note": "test credits, no cash value", "treasury_fee_bps": 250, "integrity": "VERIFIED", "entries": 1, "accounts": 1, "welcome_grants": 1, "total_issued": 1000, "total_transferred": 0, "fees_collected": 0, "entries_by_kind": {"grant": 1, "transfer": 0, "purchase": 0, "reset": 0}, "last_entry_ms": 1793331382620}, "users": {"identities_seen": 1, "active_24h": 1, "active_7d": 1, "new_7d": 1, "bug_reports": 1, "basis": "distinct signing pubkeys in stored events (author or app_author_pubkey), this node excluded; activity by signed event time"}, "services": {"daemon_version": "8.12.0", "uptime_seconds": 0.1, "node_id_prefix": "b0ad355fd5e6", "mesh_id": "tel-fx", "event_store": {"total_events": 5, "db_bytes": 16384, "last_event_ago_s": 0.0, "events_by_action": {"GENESIS_NODE_INIT": 1, "KICKBACK_POST": 1, "USER_POST": 1, "bug_report": 1, "credit_entry": 1}}, "omnimind_agent": {"live": false, "last_report_ago_s": null}}}''';

// Shapes of daemon v8.11.0 legacy endpoints (no summary endpoint there).
const Map<String, dynamic> kLegacyHealth = {
  'status': 'ONLINE', 'version': '8.11.0', 'node_id': 'aa11', 'mesh_id': 'dev', 'local_ip': '192.168.1.5',
  'p2p_sync_port': 5005, 'active_peers': 2, 'peer_ips': ['192.168.1.6', '192.168.1.7'], 'uptime_seconds': 3725.0,
  'catchup': null,
};
const Map<String, dynamic> kLegacyStats = {
  'status': 'OK', 'db_mode': 'WAL', 'total_events': 42, 'last_merkle_hash': '0xabcdef0123456789abcdef', 'node_id': 'aa11',
};
final Map<String, dynamic> kLegacyFeed = {
  'status': 'OK', 'node_id': 'aa11', 'version': '8.11.0', 'events': [
    {'id': 3, 'type': 'KICKBACK_POST', 'action': 'KICKBACK_POST', 'author_pubkey': 'aa11', 'verified': true,
     'payload': {'app_author_pubkey': 'b' * 64}},
    {'id': 2, 'type': 'bug_report', 'action': 'bug_report', 'author_pubkey': 'aa11', 'verified': true, 'payload': {}},
    {'id': 1, 'type': 'USER_POST', 'action': 'USER_POST', 'author_pubkey': 'c' * 64, 'verified': false, 'payload': {}},
  ],
};

Map<String, dynamic> summary() => jsonDecode(kSummaryVector) as Map<String, dynamic>;

/// A fake hub on loopback: [routes] maps "port-kind:path" to (status, json).
Future<(HttpServer, HttpServer)> fakeHub(Map<String, (int, Object?)> routes, {String? token}) async {
  final ipc = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  final tel = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  void serve(HttpServer s, String kind) {
    s.listen((req) async {
      final r = routes['$kind:${req.uri.path}'];
      final authOk = token == null || req.headers.value('authorization') == 'Bearer $token';
      final (code, body) = !authOk ? (401, {'status': 'ERROR'}) : (r ?? (404, null));
      req.response.statusCode = code;
      if (body != null) {
        req.response.headers.contentType = ContentType.json;
        req.response.write(jsonEncode(body));
      } else {
        req.response.write('<html>404</html>');
      }
      await req.response.close();
    });
  }
  serve(ipc, 'ipc');
  serve(tel, 'tel');
  return (ipc, tel);
}

Iterable<TelemetryTile> allTiles(List<TelemetrySection> s) => s.expand((x) => x.tiles);

void main() {
  group('sections from a v8.12.0 summary', () {
    final snap = HubSnapshot(HubState.live, DateTime.now(), summary: summary());
    final sections = buildSections(snap, appBuild: '42');

    test('five sections in order, each with a source line', () {
      expect(sections.map((s) => s.title), ['Protocols', 'Security', 'Finance', 'Users', 'Services']);
      for (final s in sections) {
        expect(s.source, contains('/api/telemetry/summary'));
        expect(s.tiles, isNotEmpty);
      }
    });

    test('every section carries honest not-wired tiles that name a feed', () {
      for (final s in sections) {
        final nw = s.tiles.where((t) => t.status == TileStatus.notWired).toList();
        expect(nw, isNotEmpty, reason: s.title);
        for (final t in nw) {
          expect(t.value, 'Not wired yet');
          expect(t.detail, isNotNull);
          expect(t.detail!.length, greaterThan(20));
        }
      }
      final labels = allTiles(sections).where((t) => t.status == TileStatus.notWired).map((t) => t.label);
      expect(labels, containsAll(['GossipSub pub/sub', 'BLE discovery', 'Hardware attestation', 'Subscriptions',
          'Consent acceptances']));
    });

    test('protocol tiles reflect the reported state', () {
      final p = sections[0].tiles;
      expect(p.take(6).map((t) => t.status).toList(),
          [TileStatus.ok, TileStatus.ok, TileStatus.ok, TileStatus.idle, TileStatus.ok, TileStatus.off]);
      expect(p[3].value, 'no catch-up run yet');
      expect(p[4].value, '1 queued for 1 recipients');
      expect(p[5].value, 'off');
    });

    test('security, finance, users and services show the hub numbers', () {
      final sec = sections[1].tiles;
      expect(sec[0].value, '3 local • 1 verified from peers');
      expect(sec[1].value, startsWith('1 bad signature'));
      expect(sec[1].status, TileStatus.warn);
      expect(sec.firstWhere((t) => t.label == 'Trusted-keys allowlist').value, 'off');
      final fin = sections[2].tiles;
      expect(fin[0].value, 'VERIFIED');
      expect(fin.firstWhere((t) => t.label == 'Total issued').value, '1,000 credits');
      expect(fin.firstWhere((t) => t.label == 'Treasury fees').detail, 'fee 250 bps');
      final users = sections[3].tiles;
      expect(users[0].value, '1');
      expect(users.firstWhere((t) => t.label == 'Bug reports').value, '1');
      final sv = sections[4].tiles;
      expect(sv[0].value, 'v8.12.0');
      expect(sv.firstWhere((t) => t.label == 'This app build').value, '42');
    });

    test('a missing number reads "not reported", never a made-up value', () {
      final s = summary();
      (s['finance'] as Map).remove('total_issued');
      (s['users'] as Map).remove('identities_seen');
      final secs = buildSections(HubSnapshot(HubState.live, DateTime.now(), summary: s));
      expect(secs[2].tiles.firstWhere((t) => t.label == 'Total issued').value, 'not reported credits');
      expect(secs[3].tiles.first.value, 'not reported');
    });

    test('ledger integrity failure is shown as bad', () {
      final s = summary();
      s['finance'] = {'state': 'integrity_failed', 'integrity': 'FAILED', 'detail': 'bad Ed25519 signature',
          'test_only': true, 'treasury_fee_bps': 0};
      final fin = buildSections(HubSnapshot(HubState.live, DateTime.now(), summary: s))[2].tiles;
      expect(fin.first.status, TileStatus.bad);
      expect(fin.first.value, 'INTEGRITY_FAILED');
    });
  });

  group('legacy hub (< v8.12.0)', () {
    final snap = HubSnapshot(HubState.legacy, DateTime.now(),
        health: kLegacyHealth, stats: kLegacyStats, feed: kLegacyFeed);
    final sections = buildSections(snap);

    test('says which sections need v8.12.0 and invents nothing', () {
      expect(snap.version, '8.11.0');
      expect(sections[2].tiles.first.value, 'Needs hub v8.12.0');
      expect(sections[0].tiles.first.value, 'Needs hub v8.12.0');
      expect(sections[0].tiles.firstWhere((t) => t.label == 'UDP LAN discovery').value, '2 active peers');
    });

    test('feed-derived numbers are labelled with their window', () {
      final sec = sections[1].tiles.firstWhere((t) => t.label.startsWith('Signatures'));
      expect(sec.label, 'Signatures (last 3 events)');
      expect(sec.value, '2 verified • 1 not');
      final ids = sections[3].tiles.firstWhere((t) => t.label.startsWith('Identities'));
      expect(ids.value, '2'); // app key + the c* author; the hub's own key is excluded
      expect(sections[3].tiles.firstWhere((t) => t.label.startsWith('Bug reports')).value, '1');
      expect(sections[4].tiles.firstWhere((t) => t.label == 'Event store').value, '42 events • WAL');
    });
  });

  test('offline, unauthorized and forbidden states keep the not-wired tiles', () {
    for (final st in [HubState.offline, HubState.unauthorized, HubState.forbidden, HubState.error]) {
      final secs = buildSections(HubSnapshot(st, DateTime.now(), detail: 'x'));
      expect(secs.length, 5);
      expect(secs.first.tiles.first.label, 'Hub');
      expect(secs.first.tiles.first.value, hubStateLabel(st));
      expect(allTiles(secs).where((t) => t.status == TileStatus.notWired), isNotEmpty);
    }
  });

  group('TelemetryClient against a fake hub', () {
    test('v8.12.0 summary -> live', () async {
      final (ipc, tel) = await fakeHub({'ipc:/api/telemetry/summary': (200, summary())});
      final snap = await TelemetryClient(HubTarget(ipcPort: ipc.port, telemetryPort: tel.port)).fetch();
      expect(snap.state, HubState.live);
      expect(snap.version, '8.12.0');
      await ipc.close(force: true);
      await tel.close(force: true);
    });

    test('404 on summary -> legacy fallback through node-health/stats/feed', () async {
      final (ipc, tel) = await fakeHub({
        'tel:/api/v1/telemetry/node-health': (200, kLegacyHealth),
        'ipc:/api/events/stats': (200, kLegacyStats),
        'ipc:/api/events/feed': (200, kLegacyFeed),
      });
      final snap = await TelemetryClient(HubTarget(ipcPort: ipc.port, telemetryPort: tel.port)).fetch();
      expect(snap.state, HubState.legacy);
      expect(snap.stats?['total_events'], 42);
      expect((snap.feed?['events'] as List).length, 3);
      await ipc.close(force: true);
      await tel.close(force: true);
    });

    test('bearer token is sent; a wrong token -> unauthorized', () async {
      final (ipc, tel) = await fakeHub({'ipc:/api/telemetry/summary': (200, summary())}, token: 'good');
      // "localhost" counts as loopback for isRemote, so use 127.0.0.1 with an explicit token.
      final ok = await TelemetryClient(HubTarget(ipcPort: ipc.port, telemetryPort: tel.port, token: 'good')).fetch();
      expect(ok.state, HubState.live);
      final bad = await TelemetryClient(HubTarget(ipcPort: ipc.port, telemetryPort: tel.port, token: 'nope')).fetch();
      expect(bad.state, HubState.unauthorized);
      await ipc.close(force: true);
      await tel.close(force: true);
    });

    test('403 everywhere -> forbidden (remote mode off)', () async {
      final (ipc, tel) = await fakeHub({
        'ipc:/api/telemetry/summary': (403, {'status': 'ERROR', 'message': 'loopback only'}),
        'tel:/api/v1/telemetry/node-health': (403, {'status': 'ERROR', 'message': 'loopback only'}),
      });
      final snap = await TelemetryClient(HubTarget(ipcPort: ipc.port, telemetryPort: tel.port)).fetch();
      expect(snap.state, HubState.forbidden);
      await ipc.close(force: true);
      await tel.close(force: true);
    });

    test('403 on summary but node-health OK -> older remote hub, legacy', () async {
      final (ipc, tel) = await fakeHub({
        'ipc:/api/telemetry/summary': (403, {'status': 'ERROR', 'message': 'loopback only'}),
        'tel:/api/v1/telemetry/node-health': (200, kLegacyHealth),
      });
      final snap = await TelemetryClient(HubTarget(ipcPort: ipc.port, telemetryPort: tel.port)).fetch();
      expect(snap.state, HubState.legacy);
      await ipc.close(force: true);
      await tel.close(force: true);
    });

    test('nothing listening -> offline', () async {
      final s = await ServerSocket.bind(InternetAddress.loopbackIPv4, 0);
      final port = s.port;
      await s.close();
      final snap = await TelemetryClient(HubTarget(ipcPort: port, telemetryPort: port),
          timeout: const Duration(milliseconds: 800)).fetch();
      expect(snap.state, HubState.offline);
    });
  });

  test('address parsing and formatting helpers', () {
    expect(HubTarget.parseAddress('http://100.64.0.7:5000/api').host, '100.64.0.7');
    expect(HubTarget.parseAddress('http://100.64.0.7:5000/api').port, 5000);
    expect(HubTarget.parseAddress('[fd7a::1]:5000').host, 'fd7a::1');
    expect(HubTarget.parseAddress('bad host!').host, isNull);
    expect(const HubTarget(host: '100.64.0.7').isRemote, isTrue);
    expect(const HubTarget().isRemote, isFalse);
    expect(fmtInt(1234567), '1,234,567');
    expect(fmtInt(null), 'not reported');
    expect(fmtAgo(null), 'never');
    expect(fmtAgo(75), '1m ago');
    expect(fmtDuration(3725), '1h 2m');
    expect(fmtBytes(16384), '16.0 KB');
    expect(compareVersions('8.11.0', kTelemetrySummaryMinVersion), lessThan(0));
    expect(compareVersions('8.12.0', kTelemetrySummaryMinVersion), 0);
  });
}
