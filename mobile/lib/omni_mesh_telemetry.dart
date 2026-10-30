import 'dart:async';
import 'dart:convert';
import 'dart:io';

/// ============================================================================
/// MESH MONITOR TELEMETRY (pure Dart: dart:io + dart:convert, no Flutter)
/// ============================================================================
/// Reads one hub (Omni daemon) and turns what it reports into dashboard
/// sections: Protocols / Security / Finance / Users / Services.
///
///   Hub v8.12.0+: GET :5000/api/telemetry/summary (aggregates only).
///   Older hubs:   falls back to GET :9100/api/v1/telemetry/node-health,
///                 GET :5000/api/events/stats and GET :5000/api/events/feed,
///                 and says plainly which sections need v8.12.0.
///
/// Rule: no number on screen that the hub didn't send. An area nothing feeds
/// yet gets a "Not wired yet" tile that names what would feed it.
/// Kept free of Flutter so it can be unit-tested with plain Dart.
/// ============================================================================

const String kTelemetrySummaryPath = '/api/telemetry/summary';
const String kTelemetrySummaryMinVersion = '8.12.0';

/// How a tile should be colored. [notWired] means nothing in the code feeds it.
enum TileStatus { ok, warn, bad, idle, off, notWired, unknown }

class TelemetryTile {
  final String label;
  final String value;
  final TileStatus status;
  final String? detail;

  const TelemetryTile(this.label, this.value, this.status, {this.detail});

  /// An honest placeholder: [feed] names what would have to exist to fill it.
  const TelemetryTile.notWired(this.label, String feed)
      : value = 'Not wired yet',
        status = TileStatus.notWired,
        detail = feed;
}

class TelemetrySection {
  final String title;

  /// Where the numbers came from, shown under the section title.
  final String source;
  final List<TelemetryTile> tiles;
  const TelemetrySection(this.title, this.source, this.tiles);
}

enum HubState {
  /// v8.12.0+ answered the summary.
  live,

  /// An older hub answered the legacy endpoints only.
  legacy,

  /// The hub refused the bearer token (HTTP 401).
  unauthorized,

  /// The hub is up but not serving remote phones (HTTP 403, remote mode off).
  forbidden,

  /// Nothing answered.
  offline,

  /// Any other answer.
  error,
}

/// Which hub to read. Same shape as KickBack's Settings > Hub.
class HubTarget {
  static const int defaultIpcPort = 5000;
  static const int defaultTelemetryPort = 9100;

  final String host;
  final int ipcPort;
  final int telemetryPort;

  /// Bearer token for a remote hub. Empty = no Authorization header (loopback).
  final String token;

  const HubTarget({
    this.host = '127.0.0.1',
    this.ipcPort = defaultIpcPort,
    this.telemetryPort = defaultTelemetryPort,
    this.token = '',
  });

  bool get isRemote => !(host == '127.0.0.1' || host == 'localhost' || host == '::1');

  /// Cleans what the user typed: drops "http://", a path and spaces. Returns
  /// (host, port) where port is the IPC port if they typed "host:5000", or a
  /// null host when nothing usable is left. Mirrors KickBack's parseAddress.
  static ({String? host, int? port}) parseAddress(String input) {
    var a = input.trim();
    a = a.replaceFirst(RegExp(r'^[a-zA-Z][a-zA-Z0-9+.-]*://'), '');
    final slash = a.indexOf('/');
    if (slash >= 0) a = a.substring(0, slash);
    a = a.replaceAll(' ', '');
    if (a.isEmpty) return (host: null, port: null);
    int? port;
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

/// One poll's result. Holds the hub's own JSON, untouched.
class HubSnapshot {
  final HubState state;
  final DateTime fetchedAt;
  final String detail;
  final Map<String, dynamic>? summary;
  final Map<String, dynamic>? health;
  final Map<String, dynamic>? stats;
  final Map<String, dynamic>? feed;
  final Map<String, dynamic>? omnimind;

  const HubSnapshot(
    this.state,
    this.fetchedAt, {
    this.detail = '',
    this.summary,
    this.health,
    this.stats,
    this.feed,
    this.omnimind,
  });

  bool get hasData => state == HubState.live || state == HubState.legacy;

  String? get version {
    final v = summary?['version'] ?? health?['version'] ?? feed?['version'];
    return v?.toString();
  }
}

class _Resp {
  final int code;
  final Map<String, dynamic>? json;
  const _Resp(this.code, this.json);
}

/// Polls one hub. Never throws.
class TelemetryClient {
  final HubTarget target;
  final Duration timeout;

  TelemetryClient(this.target, {Duration? timeout})
      : timeout = timeout ?? (target.isRemote ? const Duration(seconds: 4) : const Duration(milliseconds: 2000));

  Future<_Resp?> _get(int port, String path, [Map<String, String>? query]) async {
    final client = HttpClient()..connectionTimeout = timeout;
    try {
      final uri = Uri(scheme: 'http', host: target.host, port: port, path: path, queryParameters: query);
      final req = await client.getUrl(uri).timeout(timeout);
      if (target.token.isNotEmpty) {
        req.headers.set(HttpHeaders.authorizationHeader, 'Bearer ${target.token}');
      }
      final res = await req.close().timeout(timeout);
      final body = await res.transform(utf8.decoder).join().timeout(timeout);
      Map<String, dynamic>? json;
      try {
        final d = jsonDecode(body);
        if (d is Map<String, dynamic>) json = d;
      } catch (_) {}
      return _Resp(res.statusCode, json);
    } catch (_) {
      return null;
    } finally {
      client.close(force: true);
    }
  }

  Future<HubSnapshot> fetch() async {
    final now = DateTime.now();
    final s = await _get(target.ipcPort, kTelemetrySummaryPath);
    if (s == null) {
      return HubSnapshot(HubState.offline, now, detail: 'nothing answered at ${target.host}:${target.ipcPort}');
    }
    if (s.code == 401) {
      return HubSnapshot(HubState.unauthorized, now, detail: 'hub refused the token (HTTP 401)');
    }
    final omnimind = target.isRemote ? null : await _omnimind();
    if (s.code == 200 && s.json?['status'] == 'OK' && s.json?['protocols'] is List) {
      return HubSnapshot(HubState.live, now, summary: s.json, omnimind: omnimind);
    }
    if (s.code == 404 || s.code == 403) {
      // 404: hub older than v8.12.0. 403 from a remote hub: either remote mode is off, or an older
      // hub that doesn't list the summary as a remote path. node-health tells them apart.
      return _legacy(now, s.code, omnimind);
    }
    return HubSnapshot(HubState.error, now, detail: 'summary answered HTTP ${s.code}');
  }

  Future<Map<String, dynamic>?> _omnimind() async {
    final o = await _get(target.telemetryPort, '/api/omnimind/telemetry');
    return o != null && o.code == 200 ? o.json : null;
  }

  Future<HubSnapshot> _legacy(DateTime now, int summaryCode, Map<String, dynamic>? omnimind) async {
    final health = await _get(target.telemetryPort, '/api/v1/telemetry/node-health');
    if (health?.code == 401) {
      return HubSnapshot(HubState.unauthorized, now, detail: 'hub refused the token (HTTP 401)');
    }
    if (summaryCode == 403 && health?.code == 403) {
      return HubSnapshot(HubState.forbidden, now,
          detail: 'hub is not in remote mode (HTTP 403): start it with OMNI_HUB_REMOTE=1');
    }
    final stats = await _get(target.ipcPort, '/api/events/stats');
    final feed = await _get(target.ipcPort, '/api/events/feed', {'limit': '50'});
    final h = health?.code == 200 ? health!.json : null;
    final st = stats?.code == 200 ? stats!.json : null;
    final f = feed?.code == 200 && feed!.json?['events'] is List ? feed.json : null;
    if (h == null && st == null && f == null) {
      return HubSnapshot(HubState.error, now, detail: 'summary HTTP $summaryCode and no legacy endpoint answered');
    }
    return HubSnapshot(HubState.legacy, now,
        detail: 'hub is older than v$kTelemetrySummaryMinVersion', health: h, stats: st, feed: f, omnimind: omnimind);
  }
}

// ---------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------

Map<String, dynamic> _map(dynamic v) => v is Map<String, dynamic> ? v : const <String, dynamic>{};
num? _num(dynamic v) => v is num ? v : (v is String ? num.tryParse(v) : null);
int _int(dynamic v) => _num(v)?.toInt() ?? 0;

String fmtInt(dynamic v) {
  final n = _num(v);
  if (n == null) return 'not reported';
  final s = n.toInt().abs().toString();
  final b = StringBuffer(n < 0 ? '-' : '');
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) b.write(',');
    b.write(s[i]);
  }
  return b.toString();
}

String fmtAgo(dynamic seconds) {
  final s = _num(seconds);
  if (s == null) return 'never';
  if (s < 60) return '${s.round()}s ago';
  if (s < 3600) return '${(s / 60).floor()}m ago';
  if (s < 86400) return '${(s / 3600).floor()}h ago';
  return '${(s / 86400).floor()}d ago';
}

String fmtDuration(dynamic seconds) {
  final s = _num(seconds);
  if (s == null) return 'not reported';
  final t = s.toInt();
  final d = t ~/ 86400, h = (t % 86400) ~/ 3600, m = (t % 3600) ~/ 60;
  if (d > 0) return '${d}d ${h}h';
  if (h > 0) return '${h}h ${m}m';
  if (m > 0) return '${m}m ${t % 60}s';
  return '${t}s';
}

String fmtBytes(dynamic bytes) {
  final b = _num(bytes);
  if (b == null) return 'not reported';
  if (b < 1024) return '${b.toInt()} B';
  if (b < 1024 * 1024) return '${(b / 1024).toStringAsFixed(1)} KB';
  if (b < 1024 * 1024 * 1024) return '${(b / (1024 * 1024)).toStringAsFixed(1)} MB';
  return '${(b / (1024 * 1024 * 1024)).toStringAsFixed(2)} GB';
}

TileStatus statusForState(dynamic state) {
  switch ('$state') {
    case 'up':
    case 'configured':
    case 'ok':
      return TileStatus.ok;
    case 'degraded':
      return TileStatus.warn;
    case 'down':
    case 'error':
    case 'integrity_failed':
      return TileStatus.bad;
    case 'idle':
      return TileStatus.idle;
    case 'off':
      return TileStatus.off;
    default:
      return TileStatus.unknown;
  }
}

/// Compares dotted versions ("8.11.0" < "8.12.0"). Unparseable parts count as 0.
int compareVersions(String a, String b) {
  final pa = a.split('.').map((e) => int.tryParse(e) ?? 0).toList();
  final pb = b.split('.').map((e) => int.tryParse(e) ?? 0).toList();
  for (var i = 0; i < 3; i++) {
    final x = i < pa.length ? pa[i] : 0, y = i < pb.length ? pb[i] : 0;
    if (x != y) return x.compareTo(y);
  }
  return 0;
}

// ---------------------------------------------------------------------------
// "Not wired yet" tiles: areas the code doesn't feed. Named so nobody mistakes
// a placeholder for a feature (repo rule: no UI claiming what the code lacks).
// ---------------------------------------------------------------------------

const List<TelemetryTile> kNotWiredProtocols = [
  TelemetryTile.notWired('GossipSub pub/sub',
      'Admin/omni_gossipsub_swarm_router.py exists but the daemon does not run it; events relay over HTTP /p2p/sync'),
  TelemetryTile.notWired('BLE discovery',
      'Admin/omni_ble_discovery_engine.py exists but is not wired into the daemon; discovery is UDP LAN beacons only'),
  TelemetryTile.notWired('NAT hole punching',
      'Admin/omni_ice_cgnat_hole_puncher.py is not wired in; remote phones reach the hub over Tailscale'),
  TelemetryTile.notWired('OmniCast call media (WebRTC)',
      'Only the signaling mailbox is live; a call-media stats feed from the apps would fill this'),
];

const List<TelemetryTile> kNotWiredSecurity = [
  TelemetryTile.notWired('Hardware attestation',
      'Would need a device attestation check (e.g. Android key attestation) that the hub verifies; not built'),
  TelemetryTile.notWired('Encrypted event store',
      'Admin/omni_sqlcipher_db_engine.py is not used; the daemon stores events in plain SQLite (WAL)'),
];

const List<TelemetryTile> kNotWiredFinance = [
  TelemetryTile.notWired('Subscriptions',
      'No subscription billing exists; would be fed by a payments backend reporting to the hub'),
  TelemetryTile.notWired('In-app credit transfers',
      'The hub has a loopback-only /api/credits/transfer, but no app calls it and remote phones cannot reach it'),
  TelemetryTile.notWired('Cash payments / payouts',
      'Credits are closed-loop TEST credits with no cash value; nothing is redeemable'),
];

const List<TelemetryTile> kNotWiredUsers = [
  TelemetryTile.notWired('Consent acceptances',
      'The first-launch agreement is saved only on each phone; an app check-in to the hub would feed this'),
  TelemetryTile.notWired('App versions in the field',
      'Apps do not report their build to the hub; an app check-in event would feed this'),
];

const List<TelemetryTile> kNotWiredServices = [
  TelemetryTile.notWired('App crash / error rates',
      'Only manual bug reports reach the hub; automatic crash reporting is not built'),
];

// ---------------------------------------------------------------------------
// Section builders
// ---------------------------------------------------------------------------

/// The five dashboard sections for [snap]. Pure: same input, same tiles.
List<TelemetrySection> buildSections(HubSnapshot snap, {String appBuild = 'dev'}) {
  switch (snap.state) {
    case HubState.live:
      return _liveSections(snap, appBuild);
    case HubState.legacy:
      return _legacySections(snap, appBuild);
    default:
      final why = TelemetryTile('Hub', _stateLabel(snap.state), _stateStatus(snap.state), detail: snap.detail);
      return [
        TelemetrySection('Protocols', 'no hub data', [why, ...kNotWiredProtocols]),
        TelemetrySection('Security', 'no hub data', [why, ...kNotWiredSecurity]),
        TelemetrySection('Finance', 'no hub data', [why, ...kNotWiredFinance]),
        TelemetrySection('Users', 'no hub data', [why, ...kNotWiredUsers]),
        TelemetrySection('Services', 'no hub data',
            [why, TelemetryTile('This app build', appBuild, TileStatus.idle), ...kNotWiredServices]),
      ];
  }
}

String _stateLabel(HubState s) => switch (s) {
      HubState.live => 'LIVE',
      HubState.legacy => 'LEGACY HUB',
      HubState.unauthorized => 'UNAUTHORIZED',
      HubState.forbidden => 'REMOTE MODE OFF',
      HubState.offline => 'OFFLINE',
      HubState.error => 'ERROR',
    };

TileStatus _stateStatus(HubState s) => switch (s) {
      HubState.live => TileStatus.ok,
      HubState.legacy => TileStatus.warn,
      HubState.offline => TileStatus.bad,
      _ => TileStatus.bad,
    };

String hubStateLabel(HubState s) => _stateLabel(s);

List<TelemetrySection> _liveSections(HubSnapshot snap, String appBuild) {
  final s = snap.summary!;
  final src = 'GET :5000$kTelemetrySummaryPath • hub v${s['version']}';
  final protocols = <TelemetryTile>[];
  for (final raw in (s['protocols'] as List)) {
    final p = _map(raw);
    protocols.add(_protocolTile(p));
  }
  protocols.addAll(kNotWiredProtocols);

  final sec = _map(s['security']);
  final rejected = _int(sec['events_rejected_signature']) + _int(sec['events_rejected_untrusted']);
  final allow = sec['trusted_keys_allowlist'];
  final byStatus = _map(sec['signal_sends_rejected_by_status']);
  final security = <TelemetryTile>[
    TelemetryTile('Signed events stored',
        '${fmtInt(sec['events_stored_local_signed'])} local • ${fmtInt(sec['events_verified_from_peers'])} verified from peers',
        TileStatus.ok,
        detail: 'local events are signed by this hub; peer and remote-app events had their Ed25519 signature checked'),
    TelemetryTile(
        'Rejected events',
        '${fmtInt(sec['events_rejected_signature'])} bad signature • ${fmtInt(sec['events_rejected_untrusted'])} untrusted • '
            '${fmtInt(sec['events_rejected_invalid'])} invalid',
        rejected > 0 ? TileStatus.warn : TileStatus.ok,
        detail: 'last bad signature ${fmtAgo(sec['last_signature_reject_ago_s'])} • '
            '${fmtInt(sec['events_duplicate'])} duplicates ignored'),
    TelemetryTile(
        'Rejected signaling',
        '${fmtInt(sec['signal_sends_rejected'])} sends • ${fmtInt(sec['signal_polls_rejected'])} polls',
        _int(sec['signal_sends_rejected']) + _int(sec['signal_polls_rejected']) > 0 ? TileStatus.warn : TileStatus.ok,
        detail: byStatus.isEmpty
            ? 'no rejected sends'
            : 'by HTTP status: ${byStatus.entries.map((e) => '${e.key}×${e.value}').join(', ')}'),
    TelemetryTile('Rejected beacon signatures', fmtInt(sec['beacons_rejected_signature']),
        _int(sec['beacons_rejected_signature']) > 0 ? TileStatus.warn : TileStatus.ok),
    TelemetryTile(
        'Bearer token failures',
        fmtInt(sec['bearer_auth_failures']),
        _int(sec['bearer_auth_failures']) > 0 ? TileStatus.warn : TileStatus.ok,
        detail: 'last ${fmtAgo(sec['last_bearer_failure_ago_s'])} • '
            '${fmtInt(sec['remote_denied_loopback_only'])} remote calls refused (loopback-only paths)'),
    TelemetryTile(
        'Trusted-keys allowlist',
        allow == null ? 'off' : '${fmtInt(allow)} keys',
        allow == null ? TileStatus.warn : TileStatus.ok,
        detail: allow == null ? 'any validly signed peer event is accepted (OMNI_TRUSTED_KEYS_FILE not set)' : null),
    if (sec['remote_hub'] == true)
      TelemetryTile('Hub token age', sec['hub_token_age_s'] == null ? 'not reported' : fmtDuration(sec['hub_token_age_s']),
          TileStatus.idle,
          detail: 'remote hub mode is on'),
    TelemetryTile('Unsigned rows in store', fmtInt(sec['unsigned_rows_in_store']), TileStatus.idle,
        detail: 'the genesis row is unsigned by design'),
    ...kNotWiredSecurity,
  ];

  final f = _map(s['finance']);
  final finance = <TelemetryTile>[
    if (f['state'] != 'ok')
      TelemetryTile('Credits ledger', '${f['state']}'.toUpperCase(), statusForState(f['state']),
          detail: f['detail']?.toString())
    else ...[
      TelemetryTile('Credits ledger integrity', '${f['integrity']}',
          f['integrity'] == 'VERIFIED' ? TileStatus.ok : TileStatus.bad,
          detail: 'every entry re-hashed and signature-checked • TEST credits, no cash value'),
      TelemetryTile('Ledger entries', '${fmtInt(f['entries'])} entries • ${fmtInt(f['accounts'])} accounts',
          TileStatus.idle,
          detail: 'last entry ${f['last_entry_ms'] == null ? 'never' : _agoFromMs(f['last_entry_ms'], snap.fetchedAt)}'),
      TelemetryTile('Total issued', '${fmtInt(f['total_issued'])} credits', TileStatus.idle,
          detail: '${fmtInt(f['welcome_grants'])} welcome grants'),
      TelemetryTile('Total transferred', '${fmtInt(f['total_transferred'])} credits', TileStatus.idle,
          detail: 'via the hub\'s loopback admin/test endpoints'),
      TelemetryTile('Treasury fees', '${fmtInt(f['fees_collected'])} credits collected', TileStatus.idle,
          detail: 'fee ${fmtInt(f['treasury_fee_bps'])} bps'),
    ],
    ...kNotWiredFinance,
  ];

  final u = _map(s['users']);
  final users = <TelemetryTile>[
    TelemetryTile('Identities seen', fmtInt(u['identities_seen']), TileStatus.idle, detail: u['basis']?.toString()),
    TelemetryTile('Active', '${fmtInt(u['active_24h'])} in 24h • ${fmtInt(u['active_7d'])} in 7d',
        _int(u['active_24h']) > 0 ? TileStatus.ok : TileStatus.idle),
    TelemetryTile('New in 7 days', fmtInt(u['new_7d']), TileStatus.idle),
    TelemetryTile('Bug reports', fmtInt(u['bug_reports']), TileStatus.idle, detail: 'stored as signed chain events'),
    ...kNotWiredUsers,
  ];

  final sv = _map(s['services']);
  final store = _map(sv['event_store']);
  final agent = _map(sv['omnimind_agent']);
  final topActions = _map(store['events_by_action']);
  final services = <TelemetryTile>[
    TelemetryTile('Daemon', 'v${sv['daemon_version']}', TileStatus.ok,
        detail: 'node ${sv['node_id_prefix']}… • mesh ${sv['mesh_id']}'),
    TelemetryTile('Uptime', fmtDuration(sv['uptime_seconds']), TileStatus.ok,
        detail: 'since-start counters reset when the daemon restarts'),
    TelemetryTile('Event store', '${fmtInt(store['total_events'])} events • ${fmtBytes(store['db_bytes'])}', TileStatus.idle,
        detail: 'last event ${fmtAgo(store['last_event_ago_s'])}'),
    if (topActions.isNotEmpty)
      TelemetryTile('Events by type', topActions.entries.take(5).map((e) => '${e.key} ${fmtInt(e.value)}').join(' • '),
          TileStatus.idle),
    _omnimindTile(agent['live'] == true, agent['last_report_ago_s'], snap.omnimind),
    TelemetryTile('This app build', appBuild, TileStatus.idle),
    ...kNotWiredServices,
  ];

  return [
    TelemetrySection('Protocols', src, protocols),
    TelemetrySection('Security', '$src • counters since daemon start', security),
    TelemetrySection('Finance', '$src • TEST credits ledger replay', finance),
    TelemetrySection('Users', '$src • from stored events', users),
    TelemetrySection('Services', src, services),
  ];
}

String _agoFromMs(dynamic ms, DateTime now) {
  final m = _num(ms);
  if (m == null) return 'never';
  return fmtAgo((now.millisecondsSinceEpoch - m) / 1000);
}

TelemetryTile _omnimindTile(bool live, dynamic ago, Map<String, dynamic>? details) {
  final integrity = details?['chain_integrity']?.toString();
  return TelemetryTile(
    'OmniMind agent',
    live ? 'ACTIVE' : 'IDLE',
    live ? (integrity == null || integrity == 'VERIFIED' ? TileStatus.ok : TileStatus.bad) : TileStatus.idle,
    detail: live
        ? [
            'last report ${fmtAgo(ago)}',
            if (integrity != null) 'chain $integrity',
            if (details?['events_processed'] != null) '${fmtInt(details!['events_processed'])} events audited',
          ].join(' • ')
        : 'no agent posting to this hub',
  );
}

TelemetryTile _protocolTile(Map<String, dynamic> p) {
  final counts = _map(p['counts']);
  final status = statusForState(p['state']);
  final seen = 'last seen ${fmtAgo(p['last_seen_ago_s'])}';
  final name = '${p['name'] ?? p['id']}';
  switch (p['id']) {
    case 'tcp_api':
      final listen = (p['listen'] is List) ? (p['listen'] as List).join(', ') : '?';
      return TelemetryTile(name, 'listening on $listen • remote hub ${p['remote_hub'] == true ? 'on' : 'off'}', status,
          detail: '$seen • ${fmtInt(counts['loopback_requests'])} loopback / ${fmtInt(counts['remote_requests'])} remote requests');
    case 'p2p_sync':
      return TelemetryTile(name, '${fmtInt(counts['events_from_peers'])} events from peers', status,
          detail: '$seen • relay ${fmtInt(counts['relay_ok'])} ok / ${fmtInt(counts['relay_failed'])} failed • '
              '${fmtInt(counts['rejected_mesh'])} wrong-mesh rejects');
    case 'udp_discovery':
      final prefixes = (p['peer_pubkey_prefixes'] is List) ? (p['peer_pubkey_prefixes'] as List) : const [];
      return TelemetryTile(name, '${fmtInt(p['active_peers'])} active peers', status,
          detail: [
            '${p['detail'] ?? ''}',
            seen,
            'sent ${fmtInt(counts['sent'])} • accepted ${fmtInt(counts['accepted'])} • '
                'rejected ${fmtInt(_int(counts['rejected_signature']) + _int(counts['rejected_mesh']))}',
            if (prefixes.isNotEmpty) 'peers ${prefixes.map((e) => '$e…').join(', ')}',
          ].where((e) => e.isNotEmpty).join(' • '));
    case 'negentropy':
      final run = p['last_run'] is Map<String, dynamic> ? p['last_run'] as Map<String, dynamic> : null;
      return TelemetryTile(
          name,
          run == null
              ? 'no catch-up run yet'
              : '${fmtInt(run['peers'])} peers • ${fmtInt(run['stored'])} stored • ${fmtInt(run['pushed'])} pushed',
          status,
          detail: [
            if (run != null) 'last run ${fmtAgo(run['at_ago_s'])} • ${fmtInt(run['errors'])} errors • ${fmtInt(run['rejected'])} rejected',
            '${fmtInt(p['static_peers'])} static peers',
            'served ${fmtInt(counts['served_reconcile'])} reconciles',
          ].join(' • '));
    case 'signaling':
      return TelemetryTile(name, '${fmtInt(p['queued'])} queued for ${fmtInt(p['recipients'])} recipients', status,
          detail: '$seen • sends ${fmtInt(counts['sends_ok'])} ok / ${fmtInt(counts['sends_rejected'])} rejected • '
              '${fmtInt(counts['delivered'])} delivered');
    case 'turn':
      return TelemetryTile(name, p['configured'] == true ? 'configured' : 'off', status,
          detail: [if (p['detail'] != null) '${p['detail']}', 'credentials handed out ${fmtAgo(p['last_seen_ago_s'])}'].join(' • '));
    default:
      return TelemetryTile(name, '${p['state']}', status, detail: seen);
  }
}

const String _needs = 'Needs hub v$kTelemetrySummaryMinVersion';

List<TelemetrySection> _legacySections(HubSnapshot snap, String appBuild) {
  final h = snap.health ?? const <String, dynamic>{};
  final st = snap.stats;
  final events = (snap.feed?['events'] as List?)?.whereType<Map<String, dynamic>>().toList() ?? const [];
  final version = snap.version ?? '?';
  final src = 'legacy endpoints • hub v$version (older than $kTelemetrySummaryMinVersion)';
  final upgrade = TelemetryTile('Full telemetry', _needs, TileStatus.warn,
      detail: 'this hub has no $kTelemetrySummaryPath; update the daemon for every section');

  final catchup = _map(h['catchup']);
  final runs = (catchup['peers'] as List?) ?? const [];
  final protocols = <TelemetryTile>[
    upgrade,
    const TelemetryTile('TCP app API', 'answering', TileStatus.ok),
    if (snap.health != null) ...[
      TelemetryTile('P2P event sync', 'port ${h['p2p_sync_port'] ?? 'not reported'}', TileStatus.idle),
      TelemetryTile('UDP LAN discovery', '${fmtInt(h['active_peers'])} active peers',
          _int(h['active_peers']) > 0 ? TileStatus.ok : TileStatus.idle),
      TelemetryTile('Catch-up sync (negentropy)', catchup.isEmpty ? 'no run reported' : '${runs.length} peers in last run',
          catchup.isEmpty ? TileStatus.idle : TileStatus.ok),
    ],
    const TelemetryTile('Signaling / TURN', _needs, TileStatus.unknown),
    ...kNotWiredProtocols,
  ];

  // The genesis row is unsigned by design; leave it out of the signature check.
  final signedRows = events.where((e) => e['action'] != 'GENESIS_NODE_INIT' && e['type'] != 'GENESIS_NODE_INIT').toList();
  final verified = signedRows.where((e) => e['verified'] == true).length;
  final security = <TelemetryTile>[
    upgrade,
    if (signedRows.isNotEmpty)
      TelemetryTile('Signatures (last ${signedRows.length} events)', '$verified verified • ${signedRows.length - verified} not',
          verified == signedRows.length ? TileStatus.ok : TileStatus.warn,
          detail: 'the feed re-checks each event\'s Ed25519 signature when read')
    else
      const TelemetryTile('Signatures', 'no signed events in the newest feed page', TileStatus.unknown),
    const TelemetryTile('Rejected events / auth failures', _needs, TileStatus.unknown),
    ...kNotWiredSecurity,
  ];

  final finance = <TelemetryTile>[
    const TelemetryTile('Credits ledger', _needs, TileStatus.unknown,
        detail: 'older hubs keep credits loopback-only with no aggregate endpoint'),
    ...kNotWiredFinance,
  ];

  final authors = <String>{};
  for (final e in events) {
    final a = e['author_pubkey'];
    final app = _map(e['payload'])['app_author_pubkey'];
    for (final k in [a, app]) {
      if (k is String && k.isNotEmpty && k != h['node_id'] && k != snap.feed?['node_id']) authors.add(k);
    }
  }
  final users = <TelemetryTile>[
    upgrade,
    if (events.isNotEmpty)
      TelemetryTile('Identities in last ${events.length} events', fmtInt(authors.length), TileStatus.idle,
          detail: 'distinct signing keys in the newest feed page only, this hub excluded'),
    TelemetryTile('Bug reports in last ${events.length} events',
        fmtInt(events.where((e) => e['type'] == 'bug_report' || e['action'] == 'bug_report').length), TileStatus.idle),
    ...kNotWiredUsers,
  ];

  final services = <TelemetryTile>[
    TelemetryTile('Daemon', 'v$version', TileStatus.warn, detail: 'update to v$kTelemetrySummaryMinVersion+'),
    if (snap.health != null) TelemetryTile('Uptime', fmtDuration(h['uptime_seconds']), TileStatus.ok),
    if (st != null)
      TelemetryTile('Event store', '${fmtInt(st['total_events'])} events • ${st['db_mode'] ?? '?'}', TileStatus.idle,
          detail: 'head ${'${st['last_merkle_hash'] ?? ''}'.padRight(18).substring(0, 18)}…'),
    _omnimindTile(snap.omnimind != null, snap.omnimind?['age_seconds'], snap.omnimind),
    TelemetryTile('This app build', appBuild, TileStatus.idle),
    ...kNotWiredServices,
  ];

  return [
    TelemetrySection('Protocols', src, protocols),
    TelemetrySection('Security', src, security),
    TelemetrySection('Finance', src, finance),
    TelemetrySection('Users', src, users),
    TelemetrySection('Services', src, services),
  ];
}
