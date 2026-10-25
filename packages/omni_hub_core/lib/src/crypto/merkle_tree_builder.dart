import 'dart:convert';

import 'package:crypto/crypto.dart';

/// Builds Merkle Trees and computes cryptographic Merkle roots for P2P sync and ledger verification.
abstract final class MerkleTreeBuilder {
  MerkleTreeBuilder._();

  /// Computes the SHA-256 hash of a string input.
  static String hashString(String input) {
    final bytes = utf8.encode(input);
    final digest = sha256.convert(bytes);
    return '0x${digest.toString()}';
  }

  /// Computes the cryptographic Merkle Root hash from a list of data strings or transactions.
  static String computeMerkleRoot(List<String> leaves) {
    if (leaves.isEmpty) {
      return hashString('OMNIVERSE_GENESIS_MERKLE_ROOT');
    }

    List<String> currentLevel = leaves.map((leaf) => hashString(leaf)).toList();

    while (currentLevel.length > 1) {
      final nextLevel = <String>[];
      for (var i = 0; i < currentLevel.length; i += 2) {
        final left = currentLevel[i];
        final right =
            (i + 1 < currentLevel.length) ? currentLevel[i + 1] : left;
        final combined = hashString(left + right);
        nextLevel.add(combined);
      }
      currentLevel = nextLevel;
    }

    return currentLevel.first;
  }
}
