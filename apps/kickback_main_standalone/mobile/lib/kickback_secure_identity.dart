import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:omni_core_ui/omni_core_ui.dart';

/// ============================================================================
/// KICKBACK IDENTITY SEED STORE (flutter_secure_storage)
/// ============================================================================
/// Keeps this install's Ed25519 seed in flutter_secure_storage, which on Android
/// encrypts it with an AES key held in the Android Keystore (EncryptedSharedPreferences).
///
/// Honest limits:
/// - The Keystore key is not set to "require user authentication", so the seed
///   can be decrypted without a fingerprint. The biometric prompt (kickback_app_lock.dart)
///   gates app access and posting; it is not a hardware binding of the key.
/// - Signing happens in Dart memory (package:cryptography), not inside the Keystore,
///   because Android Keystore has no Ed25519 signing on most devices.
///
/// Migration: earlier builds kept the seed in the shared omni_core SQLite file
/// (`kv.ed25519_seed`). On first read we copy it here, read it back to confirm,
/// then delete the SQLite copy, so the identity (public key) does not change.
/// ============================================================================
class SecureStorageSeedStore implements IdentitySeedStore {
  static const String _key = 'kickback_ed25519_seed_v1';

  final FlutterSecureStorage _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  @override
  Future<List<int>?> read() async {
    final v = await _storage.read(key: _key);
    if (v != null) return base64Decode(v);

    // One-time move from the old SQLite location.
    final legacy = SqliteSeedStore();
    final old = await legacy.read();
    if (old == null) return null;
    await write(old);
    final check = await _storage.read(key: _key);
    if (check != null && check == base64Encode(old)) {
      await legacy.delete();
    }
    return old;
  }

  @override
  Future<void> write(List<int> seed) => _storage.write(key: _key, value: base64Encode(seed));
}
