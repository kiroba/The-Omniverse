import 'package:flutter_test/flutter_test.dart';
import 'package:omni_hub_core/omni_hub_core.dart';

void main() {
  group('MerkleTreeBuilder Tests', () {
    test('hashString returns 0x prefixed sha256 hash', () {
      final hash = MerkleTreeBuilder.hashString('test');
      expect(hash, startsWith('0x'));
      expect(hash.length, equals(66)); // '0x' + 64 hex characters
    });

    test('computeMerkleRoot returns genesis root when leaves are empty', () {
      final root = MerkleTreeBuilder.computeMerkleRoot([]);
      final expectedGenesis =
          MerkleTreeBuilder.hashString('OMNIVERSE_GENESIS_MERKLE_ROOT');
      expect(root, equals(expectedGenesis));
    });

    test('computeMerkleRoot computes correct root for single leaf', () {
      final root = MerkleTreeBuilder.computeMerkleRoot(['data_1']);
      final expected = MerkleTreeBuilder.hashString('data_1');
      expect(root, equals(expected));
    });

    test('computeMerkleRoot computes correct root for even number of leaves', () {
      final root = MerkleTreeBuilder.computeMerkleRoot(['leaf1', 'leaf2']);
      final h1 = MerkleTreeBuilder.hashString('leaf1');
      final h2 = MerkleTreeBuilder.hashString('leaf2');
      final expected = MerkleTreeBuilder.hashString(h1 + h2);
      expect(root, equals(expected));
    });

    test('computeMerkleRoot computes correct root for odd number of leaves', () {
      final root =
          MerkleTreeBuilder.computeMerkleRoot(['leaf1', 'leaf2', 'leaf3']);
      final h1 = MerkleTreeBuilder.hashString('leaf1');
      final h2 = MerkleTreeBuilder.hashString('leaf2');
      final h3 = MerkleTreeBuilder.hashString('leaf3');

      final level1Left = MerkleTreeBuilder.hashString(h1 + h2);
      final level1Right = MerkleTreeBuilder.hashString(h3 + h3);

      final expected = MerkleTreeBuilder.hashString(level1Left + level1Right);
      expect(root, equals(expected));
    });
  });
}
