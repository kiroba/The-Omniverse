import 'dart:convert';

import 'canonical_json.dart';
import 'core_db.dart';
import 'omni_hub_client.dart';
import 'stargate_identity.dart';

/// A signed, hash-chained event as stored on the device.
class OmniEvent {
  final String eventId;
  final String action;
  final String authorPubkey;
  final String previousHash;
  final double timestamp;
  final Map<String, dynamic> payload;
  final String signature;
  final bool synced;

  OmniEvent({
    required this.eventId,
    required this.action,
    required this.authorPubkey,
    required this.previousHash,
    required this.timestamp,
    required this.payload,
    required this.signature,
    required this.synced,
  });

  Map<String, dynamic> toEnvelope() => {
        'event_id': eventId,
        'action': action,
        'author_pubkey': authorPubkey,
        'previous_hash': previousHash,
        'timestamp': timestamp,
        'payload': payload,
        'signature': signature,
      };
}

/// Offline-first local log. Writes land on the device instantly (one SQLite
/// insert), are signed by this app's [StargateIdentity] and hash-chained, then
/// [syncToHub] hands them to the Omni-Hub when it is reachable.
///
/// Honest scope: this is a linear hash chain per device, not a Merkle DAG.
/// Merging chains from many devices is the daemon's job.
class LocalEventStore {
  static const String genesisHash = '0x0000000000000000000000000000000000000000000000000000000000000000';

  Future<OmniEvent> append(String action, Map<String, dynamic> payload) async {
    final id = await StargateIdentity.load();
    final db = await OmniCoreDb.open();
    final last = await db.query('events', columns: ['event_id'], orderBy: 'id DESC', limit: 1);
    final prev = last.isEmpty ? genesisHash : last.first['event_id'] as String;
    final ts = DateTime.now().microsecondsSinceEpoch / 1e6;

    final unsigned = eventStruct(
      action: action,
      authorPubkey: id.pubkeyHex,
      payload: payload,
      previousHash: prev,
      timestamp: ts,
    );
    final eventId = canonicalEventId(
      action: action,
      authorPubkey: id.pubkeyHex,
      payload: payload,
      previousHash: prev,
      timestamp: ts,
    );
    final sig = await id.sign(unsigned);

    await db.insert('events', {
      'event_id': eventId,
      'action': action,
      'author_pubkey': id.pubkeyHex,
      'previous_hash': prev,
      'timestamp': ts,
      'payload_json': jsonEncode(payload),
      'signature': sig,
    });
    return OmniEvent(
      eventId: eventId,
      action: action,
      authorPubkey: id.pubkeyHex,
      previousHash: prev,
      timestamp: ts,
      payload: payload,
      signature: sig,
      synced: false,
    );
  }

  Future<List<OmniEvent>> recent({int limit = 50}) async {
    final db = await OmniCoreDb.open();
    final rows = await db.query('events', orderBy: 'id DESC', limit: limit);
    return rows.map(_fromRow).toList();
  }

  Future<int> pendingCount() async {
    final db = await OmniCoreDb.open();
    final r = await db.rawQuery('SELECT COUNT(*) AS n FROM events WHERE synced = 0');
    return (r.first['n'] as int?) ?? 0;
  }

  /// Pushes unsynced events to the Omni-Hub, oldest first. Returns how many
  /// went through. Stops at the first failure so order is kept.
  Future<int> syncToHub(OmniHubClient hub) async {
    final db = await OmniCoreDb.open();
    final rows = await db.query('events', where: 'synced = 0', orderBy: 'id ASC');
    var sent = 0;
    for (final row in rows) {
      final e = _fromRow(row);
      final res = await hub.appendEvent(e.action, {
        ...e.payload,
        'app_event_id': e.eventId,
        'app_author_pubkey': e.authorPubkey,
        'app_signature': e.signature,
      });
      if (res == null || res['status'] != 'SUCCESS') break;
      await db.update('events', {'synced': 1, 'hub_event_id': res['event_id']},
          where: 'event_id = ?', whereArgs: [e.eventId]);
      sent++;
    }
    return sent;
  }

  OmniEvent _fromRow(Map<String, Object?> r) => OmniEvent(
        eventId: r['event_id'] as String,
        action: r['action'] as String,
        authorPubkey: r['author_pubkey'] as String,
        previousHash: r['previous_hash'] as String,
        timestamp: (r['timestamp'] as num).toDouble(),
        payload: Map<String, dynamic>.from(jsonDecode(r['payload_json'] as String) as Map),
        signature: r['signature'] as String,
        synced: (r['synced'] as int) == 1,
      );
}
