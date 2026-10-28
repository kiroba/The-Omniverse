import 'dart:convert';

import 'package:crypto/crypto.dart';

import 'canonical_json.dart';
import 'local_event_store.dart';
import 'stargate_identity.dart';

/// Keys an app adds to the payload when it hands its own signed event to the
/// daemon (see [LocalEventStore.syncToHubDetailed]). Stripping them gives back
/// the payload the app signed.
const Set<String> kAppEnvelopeKeys = {
  'app_event_id',
  'app_author_pubkey',
  'app_signature',
  'app_previous_hash',
  'app_ts',
  'app_timestamp',
};

/// One event from the daemon's `GET :5000/api/events/feed` (daemon v8.6.0+).
/// It can be this phone's own post (relayed through the local daemon) or one
/// that arrived from a peer over /p2p/sync.
class HubFeedEvent {
  /// Daemon row id: arrival order on that node, the paging cursor.
  final int id;
  final String eventId;
  final String action;

  /// The node that signed the event (the daemon re-signs app posts as itself).
  final String authorPubkey;

  /// "local" (this phone's daemon wrote it) or "remote" (came from a peer).
  final String origin;

  /// Exactly one of [ts] (int ms) / [timestamp] (legacy float s) is the signed field.
  final int? ts;
  final double? timestamp;
  final int tsMs;
  final Map<String, dynamic> payload;
  final String previousHash;
  final String? signature;

  /// What the daemon says about the node signature. Informational only: the
  /// app re-checks signatures itself ([verifyHubEvent]).
  final bool daemonVerified;

  HubFeedEvent({
    required this.id,
    required this.eventId,
    required this.action,
    required this.authorPubkey,
    required this.origin,
    this.ts,
    this.timestamp,
    required this.tsMs,
    required this.payload,
    required this.previousHash,
    this.signature,
    required this.daemonVerified,
  });

  /// Returns null for anything malformed, so one bad row never breaks the feed.
  static HubFeedEvent? fromJson(Object? raw) {
    if (raw is! Map) return null;
    try {
      final id = raw['id'];
      final eventId = raw['event_id'];
      final action = raw['action'] ?? raw['type'];
      final author = raw['author_pubkey'];
      final prev = raw['previous_hash'];
      if (id is! int || eventId is! String || action is! String || author is! String || prev is! String) {
        return null;
      }
      final p = raw['payload'];
      final payload = p is Map ? Map<String, dynamic>.from(p) : <String, dynamic>{};
      final ts = raw['ts'] is int ? raw['ts'] as int : null;
      final tsRaw = raw['timestamp'];
      final timestamp = ts == null && tsRaw is num ? tsRaw.toDouble() : null;
      final tsMsRaw = raw['ts_ms'];
      final tsMs = tsMsRaw is int
          ? tsMsRaw
          : ts ?? (timestamp != null ? (timestamp * 1000).round() : 0);
      final sig = raw['signature'];
      return HubFeedEvent(
        id: id,
        eventId: eventId,
        action: action,
        authorPubkey: author,
        origin: '${raw['origin'] ?? 'remote'}',
        ts: ts,
        timestamp: timestamp,
        tsMs: tsMs,
        payload: payload,
        previousHash: prev,
        signature: sig is String && sig.isNotEmpty ? sig : null,
        daemonVerified: raw['verified'] == true,
      );
    } catch (_) {
      return null;
    }
  }

  DateTime get time => DateTime.fromMillisecondsSinceEpoch(tsMs);

  /// Which post this is, for dedupe and for the UI's caches. Only ever an id
  /// that is bound to the content: the app event id when it equals the hash
  /// of the app envelope, else the node event id when it equals the hash of
  /// the node envelope, else a fingerprint of the whole row. A peer can put
  /// any id it likes in a row, so an id that does not hash out is never used
  /// (it could shadow someone else's post or inherit its Verified badge).
  late final String dedupeKey = appIdMatches
      ? payload['app_event_id'] as String
      : nodeIdMatches
          ? eventId
          : 'unbound:$fingerprint';

  /// sha256 over everything the card shows and every signature on it (not the
  /// daemon row id). Two rows with the same fingerprint are the same content.
  late final String fingerprint = _fingerprint();

  String _fingerprint() {
    final m = <String, dynamic>{
      'event_id': eventId,
      'action': action,
      'author_pubkey': authorPubkey,
      'previous_hash': previousHash,
      'ts': ts,
      'timestamp': timestamp,
      'payload': payload,
      'signature': signature,
    };
    String text;
    try {
      text = canonicalJson(m);
    } catch (_) {
      text = jsonEncode(m);
    }
    return sha256.convert(utf8.encode(text)).toString();
  }

  /// True when payload.app_event_id is the canonical hash of the app envelope.
  late final bool appIdMatches = _appIdMatches();

  bool _appIdMatches() {
    final claimed = payload['app_event_id'];
    if (claimed is! String || claimed.isEmpty || !hasAppEnvelope) return false;
    try {
      final appTs = payload['app_ts'];
      return canonicalEventId(
            action: action,
            authorPubkey: payload['app_author_pubkey'] as String,
            payload: appPayload,
            previousHash: payload['app_previous_hash'] as String,
            tsMs: appTs is int ? appTs : null,
            timestamp: appTs is int ? null : (payload['app_timestamp'] as num).toDouble(),
          ) ==
          claimed;
    } catch (_) {
      return false;
    }
  }

  /// True when [eventId] is the canonical hash of the node envelope (the
  /// daemon enforces the same rule on /p2p/sync).
  late final bool nodeIdMatches = _nodeIdMatches();

  bool _nodeIdMatches() {
    try {
      return canonicalEventId(
            action: action,
            authorPubkey: authorPubkey,
            payload: payload,
            previousHash: previousHash,
            tsMs: ts,
            timestamp: ts == null ? timestamp : null,
          ) ==
          eventId;
    } catch (_) {
      return false;
    }
  }

  /// The person's (app) key when the post carries an app envelope (whose
  /// signature [verifyHubEvent] then checks), else the node key. A bare
  /// app_author_pubkey without an envelope is ignored: nothing signs it.
  String get displayAuthor => hasAppEnvelope ? payload['app_author_pubkey'] as String : authorPubkey;

  /// Payload as the app signed it (app_* keys removed).
  Map<String, dynamic> get appPayload =>
      {for (final e in payload.entries) if (!kAppEnvelopeKeys.contains(e.key)) e.key: e.value};

  String get text => '${payload['text'] ?? ''}';

  bool get hasAppEnvelope =>
      payload['app_author_pubkey'] is String &&
      payload['app_signature'] is String &&
      payload['app_previous_hash'] is String &&
      (payload['app_ts'] is int || payload['app_timestamp'] is num);

  /// The node-signed envelope, exactly as the daemon signed it.
  Map<String, dynamic>? nodeEnvelope() {
    if (signature == null) return null;
    return {
      'event_id': eventId,
      'action': action,
      'author_pubkey': authorPubkey,
      'previous_hash': previousHash,
      if (ts != null) 'ts': ts else 'timestamp': timestamp,
      'payload': payload,
      'signature': signature,
    };
  }

  /// The app's original signed envelope, rebuilt from the app_* fields.
  Map<String, dynamic>? appEnvelope() {
    if (!hasAppEnvelope) return null;
    final appTs = payload['app_ts'];
    return {
      'event_id': payload['app_event_id'],
      'action': action,
      'author_pubkey': payload['app_author_pubkey'],
      'previous_hash': payload['app_previous_hash'],
      if (appTs is int) 'ts': appTs else 'timestamp': (payload['app_timestamp'] as num).toDouble(),
      'payload': appPayload,
      'signature': payload['app_signature'],
    };
  }
}

/// How a feed card's signature checked out on this phone.
enum FeedVerification {
  /// The author's own app key signed exactly this content.
  appSigned,

  /// No app envelope, but the relaying node's key signed it.
  nodeSigned,

  /// No signature, or it does not match the content.
  unverified,
}

/// Re-checks a daemon feed event on the device (never trusts the daemon's
/// `verified` flag). If an app envelope is present it must verify: a node
/// signature over a forged app envelope does not count. Either way the
/// advertised id must be the hash of the signed content, so a valid signature
/// cannot be paired with someone else's post id.
Future<FeedVerification> verifyHubEvent(HubFeedEvent e) async {
  try {
    final app = e.appEnvelope();
    if (app != null) {
      if (!e.appIdMatches) return FeedVerification.unverified;
      return await StargateIdentity.verify(app) ? FeedVerification.appSigned : FeedVerification.unverified;
    }
    final node = e.nodeEnvelope();
    if (node != null && e.nodeIdMatches && await StargateIdentity.verify(node)) {
      return FeedVerification.nodeSigned;
    }
  } catch (_) {}
  return FeedVerification.unverified;
}

int _rank(FeedVerification? v) => switch (v) {
      FeedVerification.appSigned => 2,
      FeedVerification.nodeSigned => 1,
      _ => 0,
    };

/// The app's copy of the daemon feed: one event per [HubFeedEvent.dedupeKey],
/// with the on-device verification result cached per content
/// ([HubFeedEvent.fingerprint]), never per id. A row whose content differs
/// from the one already held is verified on its own, and it only replaces the
/// held one when it verifies at least as strongly (ties keep the first).
class HubFeedCache {
  final int maxEvents;
  final Future<FeedVerification> Function(HubFeedEvent) _verify;
  final Map<String, HubFeedEvent> _events = {};
  final Map<String, FeedVerification> _verified = {};

  HubFeedCache({this.maxEvents = 500, Future<FeedVerification> Function(HubFeedEvent)? verify})
      : _verify = verify ?? verifyHubEvent;

  Iterable<HubFeedEvent> get events => _events.values;
  int get length => _events.length;
  bool get isEmpty => _events.isEmpty;

  /// The cached result for exactly this content, or null if not checked yet.
  FeedVerification? verificationOf(HubFeedEvent e) => _verified[e.fingerprint];

  Future<void> addAll(Iterable<HubFeedEvent> incoming) async {
    for (final e in incoming) {
      final v = _verified[e.fingerprint] ??= await _verify(e);
      final held = _events[e.dedupeKey];
      if (held == null || held.fingerprint == e.fingerprint || _rank(v) > _rank(_verified[held.fingerprint])) {
        _events[e.dedupeKey] = e;
      }
    }
    _prune();
  }

  void _prune() {
    if (_events.length > maxEvents) {
      final byAge = _events.values.toList()..sort((a, b) => a.tsMs.compareTo(b.tsMs));
      for (final e in byAge.take(_events.length - maxEvents)) {
        _events.remove(e.dedupeKey);
      }
    }
    final live = {for (final e in _events.values) e.fingerprint};
    _verified.removeWhere((k, _) => !live.contains(k));
  }
}

enum HubFeedState {
  /// The daemon answered with a page.
  ok,

  /// The daemon is up but has no /api/events/feed (older than v8.6.0).
  unsupported,

  /// Nothing answered on loopback.
  unreachable,

  /// The daemon answered with an error.
  error,
}

class HubFeedResult {
  final HubFeedState state;
  final List<HubFeedEvent> events;
  final int latestId;
  final int? nextBefore;
  final bool hasMore;
  final String? error;

  const HubFeedResult({
    required this.state,
    this.events = const [],
    this.latestId = 0,
    this.nextBefore,
    this.hasMore = false,
    this.error,
  });

  /// Classifies one HTTP answer from `GET /api/events/feed`.
  /// 404 means the daemon predates the feed (v8.6.0); so does a 200 without an
  /// "events" list (an old daemon answering some other route).
  static HubFeedResult fromResponse(int statusCode, String body) {
    Object? decoded;
    try {
      decoded = jsonDecode(body);
    } catch (_) {
      decoded = null;
    }
    final map = decoded is Map ? Map<String, dynamic>.from(decoded) : null;
    if (statusCode == 404) {
      return const HubFeedResult(state: HubFeedState.unsupported, error: 'daemon has no /api/events/feed (needs v8.6.0+)');
    }
    if (statusCode != 200) {
      final msg = map != null && map['message'] != null ? ': ${map['message']}' : '';
      return HubFeedResult(state: HubFeedState.error, error: 'HTTP $statusCode$msg');
    }
    if (map == null) {
      return const HubFeedResult(state: HubFeedState.error, error: 'daemon answered with something that is not JSON');
    }
    if ('${map['status'] ?? 'OK'}'.toUpperCase() == 'ERROR') {
      return HubFeedResult(state: HubFeedState.error, error: '${map['message'] ?? 'daemon error'}');
    }
    if (map['events'] is! List) {
      return const HubFeedResult(state: HubFeedState.unsupported, error: 'daemon answer has no event list (needs v8.6.0+)');
    }
    return fromJson(map);
  }

  /// Highest daemon row id in this page (0 when empty). Use it as the next `since`.
  int get maxEventId {
    var m = 0;
    for (final e in events) {
      if (e.id > m) m = e.id;
    }
    return m;
  }

  static HubFeedResult fromJson(Map<String, dynamic> j) {
    final raw = j['events'];
    final events = <HubFeedEvent>[
      if (raw is List)
        for (final r in raw)
          if (HubFeedEvent.fromJson(r) case final e?) e,
    ];
    final latest = j['latest_id'];
    final next = j['next_before'];
    return HubFeedResult(
      state: HubFeedState.ok,
      events: events,
      latestId: latest is int ? latest : 0,
      nextBefore: next is int ? next : null,
      hasMore: j['has_more'] == true,
    );
  }
}

/// One card in the merged feed: a post from this phone's log, or a daemon
/// feed event that is not already in the log.
class FeedEntry {
  final OmniEvent? local;
  final HubFeedEvent? hub;
  const FeedEntry.local(OmniEvent this.local) : hub = null;
  const FeedEntry.hub(HubFeedEvent this.hub) : local = null;

  String get key => local?.eventId ?? hub!.dedupeKey;
  DateTime get time => local?.time ?? hub!.time;
  String get author => local?.authorPubkey ?? hub!.displayAuthor;
  String get text => local != null ? '${local!.payload['text'] ?? ''}' : hub!.text;
}

/// Local posts first-class; daemon events are added unless they are the same
/// post (same app_event_id as a local event id, or the node event the local
/// post became, or a duplicate of another daemon row). Newest first.
List<FeedEntry> mergeFeed(List<OmniEvent> local, Iterable<HubFeedEvent> hub) {
  final seen = <String>{};
  final out = <FeedEntry>[];
  for (final e in local) {
    if (seen.add(e.eventId)) out.add(FeedEntry.local(e));
    if (e.hubEventId != null) seen.add(e.hubEventId!);
  }
  for (final h in hub) {
    // Only ids bound to content take part: a forged row cannot hide a real
    // post by claiming its id (it gets its own card, marked Unverified).
    final boundNodeId = h.nodeIdMatches ? h.eventId : null;
    if (seen.contains(h.dedupeKey) || (boundNodeId != null && seen.contains(boundNodeId))) continue;
    seen.add(h.dedupeKey);
    if (boundNodeId != null) seen.add(boundNodeId);
    out.add(FeedEntry.hub(h));
  }
  out.sort((a, b) => b.time.compareTo(a.time));
  return out;
}
