import 'dart:convert';

import 'canonical_json.dart';
import 'core_db.dart';
import 'omni_hub_client.dart';
import 'stargate_identity.dart';

/// A signed, hash-chained event as stored on the device.
///
/// Time is either [tsMs] (integer milliseconds, canonical key "ts", what new
/// events use) or legacy float seconds (canonical key "timestamp", events
/// written before int-ms support). [timestamp] is always filled (seconds) for
/// display and ordering; only one of the two is part of the signed bytes.
class OmniEvent {
  final String eventId;
  final String action;
  final String authorPubkey;
  final String previousHash;
  final double timestamp;
  final int? tsMs;
  final Map<String, dynamic> payload;
  final String signature;
  final bool synced;
  final String? hubEventId;

  OmniEvent({
    required this.eventId,
    required this.action,
    required this.authorPubkey,
    required this.previousHash,
    required this.timestamp,
    this.tsMs,
    required this.payload,
    required this.signature,
    required this.synced,
    this.hubEventId,
  });

  DateTime get time => tsMs != null
      ? DateTime.fromMillisecondsSinceEpoch(tsMs!)
      : DateTime.fromMicrosecondsSinceEpoch((timestamp * 1e6).round());

  /// Exactly what was signed, plus event_id and signature. Carries "ts" or
  /// "timestamp", never both, so [StargateIdentity.verify] and the daemon's
  /// verify_event check the same bytes.
  Map<String, dynamic> toEnvelope() => {
        'event_id': eventId,
        'action': action,
        'author_pubkey': authorPubkey,
        'previous_hash': previousHash,
        if (tsMs != null) 'ts': tsMs else 'timestamp': timestamp,
        'payload': payload,
        'signature': signature,
      };
}

/// Outcome of one [LocalEventStore.syncToHub] pass.
class HubSyncResult {
  /// Events the hub accepted this pass.
  final int sent;

  /// Events still waiting after this pass.
  final int pending;

  /// False when the hub could not be reached at all.
  final bool hubReachable;

  /// The hub's error message when it answered but refused an event.
  final String? error;

  const HubSyncResult({required this.sent, required this.pending, required this.hubReachable, this.error});
}

/// Offline-first local log. Writes land on the device instantly (one SQLite
/// insert), are signed by this app's [StargateIdentity] and hash-chained, then
/// [syncToHub] hands them to the Omni-Hub when it is reachable.
///
/// Honest scope: this is a linear hash chain per device, not a Merkle DAG.
/// Merging chains from many devices is the daemon's job.
class LocalEventStore {
  static const String genesisHash = '0x0000000000000000000000000000000000000000000000000000000000000000';

  /// Signs and stores a new event. New events use integer-ms "ts" (daemon
  /// 8.5.1+ canonical form); pass `intMs: false` only to produce a legacy
  /// float-"timestamp" event for an old daemon.
  Future<OmniEvent> append(String action, Map<String, dynamic> payload, {bool intMs = true}) async {
    final id = await StargateIdentity.load();
    final db = await OmniCoreDb.open();
    final last = await db.query('events', columns: ['event_id'], orderBy: 'id DESC', limit: 1);
    final prev = last.isEmpty ? genesisHash : last.first['event_id'] as String;
    final now = DateTime.now();
    final int? tsMs = intMs ? now.millisecondsSinceEpoch : null;
    final double ts = intMs ? tsMs! / 1000.0 : now.microsecondsSinceEpoch / 1e6;

    final unsigned = eventStruct(
      action: action,
      authorPubkey: id.pubkeyHex,
      payload: payload,
      previousHash: prev,
      timestamp: intMs ? null : ts,
      tsMs: tsMs,
    );
    final eventId = canonicalEventId(
      action: action,
      authorPubkey: id.pubkeyHex,
      payload: payload,
      previousHash: prev,
      timestamp: intMs ? null : ts,
      tsMs: tsMs,
    );
    final sig = await id.sign(unsigned);

    await db.insert('events', {
      'event_id': eventId,
      'action': action,
      'author_pubkey': id.pubkeyHex,
      'previous_hash': prev,
      'timestamp': ts,
      'ts_ms': tsMs,
      'payload_json': jsonEncode(payload),
      'signature': sig,
    });
    return OmniEvent(
      eventId: eventId,
      action: action,
      authorPubkey: id.pubkeyHex,
      previousHash: prev,
      timestamp: ts,
      tsMs: tsMs,
      payload: payload,
      signature: sig,
      synced: false,
    );
  }

  /// Newest first. Pass [action] to only return one kind of event.
  Future<List<OmniEvent>> recent({int limit = 50, String? action}) async {
    final db = await OmniCoreDb.open();
    final rows = await db.query('events',
        where: action == null ? null : 'action = ?',
        whereArgs: action == null ? null : [action],
        orderBy: 'id DESC',
        limit: limit);
    return rows.map(_fromRow).toList();
  }

  Future<int> pendingCount() async {
    final db = await OmniCoreDb.open();
    final r = await db.rawQuery('SELECT COUNT(*) AS n FROM events WHERE synced = 0');
    return (r.first['n'] as int?) ?? 0;
  }

  /// Pushes unsynced events to the Omni-Hub, oldest first. Returns how many
  /// went through. Stops at the first failure so order is kept.
  Future<int> syncToHub(OmniHubClient hub) async => (await syncToHubDetailed(hub)).sent;

  /// Like [syncToHub] but says why it stopped.
  ///
  /// What the hub does with it (daemon IPC POST /api/events/append): for a
  /// loopback (local app) submission the daemon makes ITSELF the author and
  /// signs with the node key; it does not check the app's signature. So the
  /// app's own signed envelope travels inside the payload (app_event_id,
  /// app_author_pubkey, app_signature, app_previous_hash and app_ts or
  /// app_timestamp), where anyone can re-verify it against the app key. The
  /// daemon's own time field is the event's int-ms "ts".
  Future<HubSyncResult> syncToHubDetailed(OmniHubClient hub) async {
    final db = await OmniCoreDb.open();
    final rows = await db.query('events', where: 'synced = 0', orderBy: 'id ASC');
    var sent = 0;
    String? error;
    var reachable = true;
    for (final row in rows) {
      final e = _fromRow(row);
      final res = await hub.appendEvent(
        e.action,
        {
          ...e.payload,
          'app_event_id': e.eventId,
          'app_author_pubkey': e.authorPubkey,
          'app_signature': e.signature,
          'app_previous_hash': e.previousHash,
          if (e.tsMs != null) 'app_ts': e.tsMs else 'app_timestamp': e.timestamp,
        },
        tsMs: e.tsMs,
      );
      if (res == null) {
        reachable = false;
        break;
      }
      if (res['status'] != 'SUCCESS') {
        error = '${res['message'] ?? res['status'] ?? 'rejected'}';
        break;
      }
      await db.update('events', {'synced': 1, 'hub_event_id': res['event_id']},
          where: 'event_id = ?', whereArgs: [e.eventId]);
      sent++;
    }
    return HubSyncResult(
      sent: sent,
      pending: rows.length - sent,
      hubReachable: reachable,
      error: error,
    );
  }

  OmniEvent _fromRow(Map<String, Object?> r) => OmniEvent(
        eventId: r['event_id'] as String,
        action: r['action'] as String,
        authorPubkey: r['author_pubkey'] as String,
        previousHash: r['previous_hash'] as String,
        timestamp: (r['timestamp'] as num).toDouble(),
        tsMs: (r['ts_ms'] as num?)?.toInt(),
        payload: Map<String, dynamic>.from(jsonDecode(r['payload_json'] as String) as Map),
        signature: r['signature'] as String,
        synced: (r['synced'] as int) == 1,
        hubEventId: r['hub_event_id'] as String?,
      );
}
