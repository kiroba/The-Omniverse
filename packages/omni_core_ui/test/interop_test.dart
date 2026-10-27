import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:omni_core_ui/omni_core_ui.dart';

// Vectors generated with the daemon's own Admin/omni_signing.py (Python), so
// these tests prove the Dart side hashes and verifies byte-for-byte the same.
void main() {
  const pub = '03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8';
  final event = <String, dynamic>{
    'action': 'CREATOR_POST_PUBLISHED',
    'author_pubkey': pub,
    'payload': {
      'title': 'Sovereign Post',
      'tier': 'PUBLIC',
      'emoji': 'h\u00e9llo \u{1F600}',
      'n': 3,
      'nested': {'b': 1.5, 'a': [true, null]},
    },
    'previous_hash': '0xgenesis_000',
    'timestamp': 1793042651.19,
  };

  test('canonical JSON matches Python json.dumps(sort_keys, compact)', () {
    expect(
      canonicalJson(eventStruct(
        action: event['action'],
        authorPubkey: pub,
        payload: event['payload'],
        previousHash: event['previous_hash'],
        timestamp: event['timestamp'],
      )),
      r'{"action":"CREATOR_POST_PUBLISHED","author_pubkey":"03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8","payload":{"emoji":"h\u00e9llo \ud83d\ude00","n":3,"nested":{"a":[true,null],"b":1.5},"tier":"PUBLIC","title":"Sovereign Post"},"previous_hash":"0xgenesis_000","timestamp":1793042651.19}',
    );
  });

  test('event id matches daemon compute_canonical_event_id', () {
    expect(
      canonicalEventId(
        action: event['action'],
        authorPubkey: pub,
        payload: event['payload'],
        previousHash: event['previous_hash'],
        timestamp: event['timestamp'],
      ),
      '0xfa3a7ba832dae9cb8dd24af8a922f6c159862eddd6b7cef3765eafd58fb07458',
    );
  });

  test('Python-signed event verifies; tampered event does not', () async {
    final signed = {...event, 'signature': 'd9755fc457c659d01ecab8e14f3fca2f671be756cc4ebd35e05c805acd52e0bbc3b5d8f7085be00a10b8dddfeb7765d55b0e4782eb9ca10742c731d6867d9008'};
    expect(await StargateIdentity.verify(signed), isTrue);
    final tampered = {...signed, 'payload': {...event['payload'], 'title': 'Edited'}};
    expect(await StargateIdentity.verify(tampered), isFalse);
  });

  test('signed OTA manifest verifies against pinned key', () async {
    final manifest = jsonDecode(r'{"tag": "v0.1.4", "build": 1013, "transport": "github", "apps": {"mesh-monitor": {"url": "https://x/y.apk", "sha256": "abababababababababababababababababababababababababababababababab"}}}') as Map<String, dynamic>;
    final bytes = utf8.encode(canonicalJson(manifest));
    expect(await StargateIdentity.verifyBytes(bytes, '9c6e8880c79b3e4848d33e6af0b3474ec4d0d012001d1398ac8eb26944a43dc28e087f258a0ac69d003c4f06f839699f71957ec1c6ba5a28a0fe7ddcf15c6c04', pub), isTrue);
    manifest['build'] = 9999;
    expect(await StargateIdentity.verifyBytes(utf8.encode(canonicalJson(manifest)), '9c6e8880c79b3e4848d33e6af0b3474ec4d0d012001d1398ac8eb26944a43dc28e087f258a0ac69d003c4f06f839699f71957ec1c6ba5a28a0fe7ddcf15c6c04', pub), isFalse);
  });

  test('python float formatting', () {
    expect(canonicalJson(1700000000.0), '1700000000.0');
    expect(canonicalJson(1e16), '1e+16');
    expect(canonicalJson(1e-7), '1e-07');
    expect(canonicalJson(123456789012345678.0), '1.2345678901234568e+17');
  });
}
