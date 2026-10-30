import 'dart:convert';
import 'dart:math';

import 'package:cryptography/cryptography.dart';
import 'package:sqflite/sqflite.dart' show ConflictAlgorithm;

import 'canonical_json.dart';
import 'core_db.dart';

/// This app install's Ed25519 identity, plus signature checks for any event.
///
/// Signing format is identical to the daemon's omni_signing.py: the signature
/// covers the canonical JSON of {action, author_pubkey, payload, previous_hash,
/// timestamp}, and author_pubkey is the raw public key as 64 hex chars.
///
/// Where the 32-byte seed lives is pluggable ([seedStore]). The default,
/// [SqliteSeedStore], keeps it in the app's private SQLite file (not the
/// Android keystore). Apps can set a stronger store before the first [load],
/// e.g. KickBack plugs in flutter_secure_storage (Keystore-encrypted).
class StargateIdentity {
  static final Ed25519 _algo = Ed25519();
  static StargateIdentity? _instance;

  /// Seed storage used by [load]. Set once, before the first [load].
  static IdentitySeedStore seedStore = SqliteSeedStore();

  final SimpleKeyPair _keyPair;
  final String pubkeyHex;

  StargateIdentity._(this._keyPair, this.pubkeyHex);

  /// Loads the identity, creating it on first launch.
  static Future<StargateIdentity> load() async {
    if (_instance != null) return _instance!;
    var seed = await seedStore.read();
    if (seed == null) {
      final rnd = Random.secure();
      seed = List<int>.generate(32, (_) => rnd.nextInt(256));
      await seedStore.write(seed);
    }
    _instance = await fromSeed(seed);
    return _instance!;
  }

  /// Builds an identity from a raw 32-byte Ed25519 seed (no storage). Used by
  /// [load] and by the interop tests.
  static Future<StargateIdentity> fromSeed(List<int> seed) async {
    if (seed.length != 32) throw ArgumentError('Ed25519 seed must be 32 bytes');
    final kp = await _algo.newKeyPairFromSeed(seed);
    final pub = await kp.extractPublicKey();
    return StargateIdentity._(kp, _hex(pub.bytes));
  }

  /// Short, human-friendly handle for the badge (first 4 + last 4 hex).
  String get shortId => '${pubkeyHex.substring(0, 4)}…${pubkeyHex.substring(pubkeyHex.length - 4)}';

  Future<String> sign(Map<String, dynamic> unsignedEvent) async {
    final msg = utf8.encode(canonicalJson(_struct(unsignedEvent)));
    final sig = await _algo.sign(msg, keyPair: _keyPair);
    return _hex(sig.bytes);
  }

  /// Signs exact bytes with this identity's key; returns a 128-char hex
  /// signature. For protocols with their own canonical form, e.g. the OmniCast
  /// signaling mailbox (mobile/lib/omni_signal_client.dart), so they reuse this
  /// one identity instead of keeping a second key.
  Future<String> signBytes(List<int> message) async {
    final sig = await _algo.sign(message, keyPair: _keyPair);
    return _hex(sig.bytes);
  }

  /// True only if `signature` was made by the key behind `author_pubkey`.
  /// Works for events from this app, the local daemon, or any peer.
  static Future<bool> verify(Map<String, dynamic> event) async {
    try {
      final pub = _unhex(event['author_pubkey'] as String);
      final sig = _unhex(event['signature'] as String);
      if (pub.length != 32 || sig.length != 64) return false;
      final msg = utf8.encode(canonicalJson(_struct(event)));
      return await _algo.verify(
        msg,
        signature: Signature(sig, publicKey: SimplePublicKey(pub, type: KeyPairType.ed25519)),
      );
    } catch (_) {
      return false;
    }
  }

  /// Verifies raw bytes against a hex public key (used for OTA manifests).
  static Future<bool> verifyBytes(List<int> message, String signatureHex, String pubkeyHex) async {
    try {
      final pub = _unhex(pubkeyHex);
      final sig = _unhex(signatureHex);
      if (pub.length != 32 || sig.length != 64) return false;
      return await _algo.verify(
        message,
        signature: Signature(sig, publicKey: SimplePublicKey(pub, type: KeyPairType.ed25519)),
      );
    } catch (_) {
      return false;
    }
  }

  /// Same rules as omni_signing.canonical_event_struct: an event carries
  /// either int-ms "ts" or float-seconds "timestamp", never both.
  static Map<String, dynamic> _struct(Map<String, dynamic> e) {
    final hasTs = e.containsKey('ts');
    final hasLegacy = e.containsKey('timestamp');
    if (hasTs == hasLegacy) {
      throw ArgumentError("event must carry exactly one of 'ts' or 'timestamp'");
    }
    final ts = e['ts'];
    if (hasTs && ts is! int) {
      throw ArgumentError("'ts' must be an integer (milliseconds since epoch)");
    }
    return eventStruct(
      action: e['action'] as String,
      authorPubkey: e['author_pubkey'] as String,
      payload: Map<String, dynamic>.from(e['payload'] as Map),
      previousHash: e['previous_hash'] as String,
      timestamp: hasLegacy ? (e['timestamp'] as num).toDouble() : null,
      tsMs: hasTs ? ts as int : null,
    );
  }

  static String _hex(List<int> b) => b.map((x) => x.toRadixString(16).padLeft(2, '0')).join();

  static List<int> _unhex(String h) {
    if (h.length.isOdd) throw const FormatException('odd hex');
    return [for (var i = 0; i < h.length; i += 2) int.parse(h.substring(i, i + 2), radix: 16)];
  }
}

/// Where an app keeps its identity seed.
abstract class IdentitySeedStore {
  /// The stored 32-byte seed, or null on first launch.
  Future<List<int>?> read();
  Future<void> write(List<int> seed);
}

/// Default store: the seed in the app-private SQLite file (`kv` table).
/// Not hardware-backed; anyone with root or a backup of app data can read it.
class SqliteSeedStore implements IdentitySeedStore {
  static const String key = 'ed25519_seed';

  @override
  Future<List<int>?> read() async {
    final db = await OmniCoreDb.open();
    final rows = await db.query('kv', where: 'k = ?', whereArgs: [key]);
    if (rows.isEmpty) return null;
    return base64Decode(rows.first['v'] as String);
  }

  @override
  Future<void> write(List<int> seed) async {
    final db = await OmniCoreDb.open();
    await db.insert('kv', {'k': key, 'v': base64Encode(seed)}, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  /// Removes the SQLite copy (used after migrating to a stronger store).
  Future<void> delete() async {
    final db = await OmniCoreDb.open();
    await db.delete('kv', where: 'k = ?', whereArgs: [key]);
  }
}
