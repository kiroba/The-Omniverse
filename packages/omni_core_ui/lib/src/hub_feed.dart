import 'dart:convert';

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

  /// The app's own event id when the post came from an app, else the node event id.
  String get dedupeKey {
    final a = payload['app_event_id'];
    return a is String && a.isNotEmpty ? a : eventId;
  }

  /// The person's (app) key when present, else the node key.
  String get displayAuthor {
    final a = payload['app_author_pubkey'];
    return a is String && a.isNotEmpty ? a : authorPubkey;
  }

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
/// signature over a forged app envelope does not count.
Future<FeedVerification> verifyHubEvent(HubFeedEvent e) async {
  try {
    final app = e.appEnvelope();
    if (app != null) {
      return await StargateIdentity.verify(app) ? FeedVerification.appSigned : FeedVerification.unverified;
    }
    final node = e.nodeEnvelope();
    if (node != null && await StargateIdentity.verify(node)) return FeedVerification.nodeSigned;
  } catch (_) {}
  return FeedVerification.unverified;
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
    if (seen.contains(h.eventId) || seen.contains(h.dedupeKey)) continue;
    seen
      ..add(h.eventId)
      ..add(h.dedupeKey);
    out.add(FeedEntry.hub(h));
  }
  out.sort((a, b) => b.time.compareTo(a.time));
  return out;
}
