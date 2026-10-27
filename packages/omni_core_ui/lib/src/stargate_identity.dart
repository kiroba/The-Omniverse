import 'dart:convert';
import 'dart:math';

import 'package:cryptography/cryptography.dart';

import 'canonical_json.dart';
import 'core_db.dart';

/// This app install's Ed25519 identity, plus signature checks for any event.
///
/// Signing format is identical to the daemon's omni_signing.py: the signature
/// covers the canonical JSON of {action, author_pubkey, payload, previous_hash,
/// timestamp}, and author_pubkey is the raw public key as 64 hex chars.
///
/// Honest limit: the 32-byte seed lives in the app's private SQLite file, not
/// in the Android hardware keystore. Good for testing; move to the keystore
/// before real users.
class StargateIdentity {
  static final Ed25519 _algo = Ed25519();
  static StargateIdentity? _instance;

  final SimpleKeyPair _keyPair;
  final String pubkeyHex;

  StargateIdentity._(this._keyPair, this.pubkeyHex);

  /// Loads the identity, creating it on first launch.
  static Future<StargateIdentity> load() async {
    if (_instance != null) return _instance!;
    final db = await OmniCoreDb.open();
    final rows = await db.query('kv', where: 'k = ?', whereArgs: ['ed25519_seed']);
    List<int> seed;
    if (rows.isEmpty) {
      final rnd = Random.secure();
      seed = List<int>.generate(32, (_) => rnd.nextInt(256));
      await db.insert('kv', {'k': 'ed25519_seed', 'v': base64Encode(seed)});
    } else {
      seed = base64Decode(rows.first['v'] as String);
    }
    final kp = await _algo.newKeyPairFromSeed(seed);
    final pub = await kp.extractPublicKey();
    _instance = StargateIdentity._(kp, _hex(pub.bytes));
    return _instance!;
  }

  /// Short, human-friendly handle for the badge (first 4 + last 4 hex).
  String get shortId => '${pubkeyHex.substring(0, 4)}…${pubkeyHex.substring(pubkeyHex.length - 4)}';

  Future<String> sign(Map<String, dynamic> unsignedEvent) async {
    final msg = utf8.encode(canonicalJson(_struct(unsignedEvent)));
    final sig = await _algo.sign(msg, keyPair: _keyPair);
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

  static Map<String, dynamic> _struct(Map<String, dynamic> e) => eventStruct(
        action: e['action'] as String,
        authorPubkey: e['author_pubkey'] as String,
        payload: Map<String, dynamic>.from(e['payload'] as Map),
        previousHash: e['previous_hash'] as String,
        timestamp: (e['timestamp'] as num).toDouble(),
      );

  static String _hex(List<int> b) => b.map((x) => x.toRadixString(16).padLeft(2, '0')).join();

  static List<int> _unhex(String h) {
    if (h.length.isOdd) throw const FormatException('odd hex');
    return [for (var i = 0; i < h.length; i += 2) int.parse(h.substring(i, i + 2), radix: 16)];
  }
}
