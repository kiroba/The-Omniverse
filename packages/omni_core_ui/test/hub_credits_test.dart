// Tests for HubCreditsClient (lib/src/hub_credits.dart): the hub daemon's
// TEST credits ledger (daemon v8.10.0+, signed sends v8.15.0+).
//
// Cross-language vector: signing bytes and signature made with the daemon's
// own rule (credit_signing_bytes in Admin/omni_live_daemon_server.py,
// kiroba/Omni-Daemon v8.22.0: json.dumps(sort_keys=True, separators=(",", ":"),
// ensure_ascii=False), raw UTF-8) and the Python `cryptography` package,
// seed 0..31.
//
// Optional live check against a real daemon: set OMNI_CREDITS_LIVE_IPC_PORT to
// a running daemon's :5000 port on 127.0.0.1 (and OMNI_CREDITS_LIVE_TOKEN when
// it was started with OMNI_LOCAL_TOKEN=1).
import 'dart:convert';
import 'dart:io';

import 'package:cryptography/cryptography.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:omni_core_ui/omni_core_ui.dart';

const seedHex = '000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f';
const pubA = '03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8';
// Non-ASCII (í, 🎧), quote, backslash, slash, U+2028, DEL: all signed raw.
const vMemo = 'OmniMarket: K\u00edro \u{1F3A7} "q" \\ / \u2028\u007f';
const vNonce = '00112233445566778899aabbccddeeff';
const vTs = 1793334636472;
const vBytesHex =
    '7b22616d6f756e74223a3235302c2266726f6d223a2230336131303762666633636531306265316437306464313865373462633039393637653464363330396261353064356631646463383636343132353533316238222c'
    '226b696e64223a227075726368617365222c226d656d6f223a224f6d6e694d61726b65743a204bc3ad726f20f09f8ea7205c22715c22205c5c202f20e280a87f222c'
    '226e6f6e6365223a223030313132323333343435353636373738383939616162626363646465656666222c22726566223a226974656d5f3032222c22746f223a227472656173757279222c'
    '227473223a313739333333343633363437322c2274797065223a226f6d6e692e637265646974732e7472616e736665722e7631227d';
const vSig =
    '90d7df1d9a7d1ebb2110ec804eeea9b3b51e84904d7ffa35fec2e16f88554285bfbfca3c4efb82f8dd5f2a9381d4ecff3d8d3c6c3b17a2ca57b4d6d36a4f5406';

List<int> unhex(String h) => [for (var i = 0; i < h.length; i += 2) int.parse(h.substring(i, i + 2), radix: 16)];
String hex(List<int> b) => b.map((x) => x.toRadixString(16).padLeft(2, '0')).join();

/// Test-only signer from a raw seed (apps pass StargateIdentity.signBytes).
class SeedKey {
  final SimpleKeyPair kp;
  final String pub;
  SeedKey._(this.kp, this.pub);
  static Future<SeedKey> fromSeed(List<int> seed) async {
    final kp = await Ed25519().newKeyPairFromSeed(seed);
    return SeedKey._(kp, hex((await kp.extractPublicKey()).bytes));
  }

  Future<String> sign(List<int> m) async => hex((await Ed25519().sign(m, keyPair: kp)).bytes);
}

/// A fake hub on loopback that answers like the daemon's credits endpoints.
class FakeCreditsHub {
  late HttpServer server;
  final List<HttpRequest> seen = [];
  final List<Map<String, dynamic>> sends = [];
  String? requiredToken;
  int balance = 1000;

  Future<void> start() async {
    server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((req) async {
      seen.add(req);
      final body = await utf8.decoder.bind(req).join();
      Future<void> reply(int code, Map<String, dynamic> j) async {
        req.response.statusCode = code;
        req.response.headers.contentType = ContentType.json;
        req.response.write(jsonEncode(j));
        await req.response.close();
      }

      if (requiredToken != null && req.headers.value('authorization') != 'Bearer $requiredToken') {
        return reply(401, {'status': 'ERROR', 'message': 'missing or invalid local token'});
      }
      final pubkey = req.uri.queryParameters['pubkey'];
      if (req.method == 'GET' && req.uri.path == '/api/credits/balance') {
        return reply(200, {
          'status': 'OK', 'pubkey': pubkey, 'balance': balance, 'available': balance, 'welcome_pending': false,
          'test_only': true, 'fee_bps': 2000, 'version': '8.22.0'
        });
      }
      if (req.method == 'GET' && req.uri.path == '/api/credits/history') {
        return reply(200, {
          'status': 'OK', 'pubkey': pubkey, 'balance': balance, 'test_only': true, 'count': 1, 'has_more': false,
          'entries': [
            {
              'id': 1, 'event_id': '0xabc', 'ts_ms': vTs, 'verified': true, 'kind': 'grant', 'from': 'treasury',
              'to': pubkey, 'amount': 1000, 'fee': 0, 'memo': 'welcome grant: 1,000 test credits, no cash value',
              'test_only': true, 'delta': 1000, 'balance_after': 1000
            }
          ]
        });
      }
      if (req.method == 'POST' && req.uri.path == '/api/credits/send') {
        final t = jsonDecode(body) as Map<String, dynamic>;
        sends.add(t);
        if ((t['amount'] as int) > balance) {
          return reply(409, {'status': 'ERROR', 'message': 'insufficient test credits', 'balance': balance});
        }
        balance -= t['amount'] as int;
        return reply(200, {
          'status': 'SUCCESS', 'event_id': '0xdef', 'balance': balance,
          'entry': {'kind': t['kind'], 'from': t['from'], 'to': t['to'], 'amount': t['amount'], 'fee': 0, 'memo': t['memo']}
        });
      }
      return reply(404, {'status': 'ERROR', 'message': 'not found'});
    });
  }

  OmniHubClient client({String? token}) => OmniHubClient(ipcPort: server.port, token: token);
}

void main() {
  test('signing bytes and signature match the daemon (cross-language vector)', () async {
    final key = await SeedKey.fromSeed(unhex(seedHex));
    expect(key.pub, pubA);
    final t = await buildSignedCreditTransfer(
      from: key.pub,
      to: kCreditTreasury,
      amount: 250,
      kind: 'purchase',
      memo: vMemo,
      ref: 'item_02',
      nonce: vNonce,
      tsMs: vTs,
      sign: key.sign,
    );
    expect(hex(creditTransferSigningBytes(t)), vBytesHex);
    expect(t['sig'], vSig);
    expect(t['type'], kCreditTransferType);
    expect(t.keys.toSet(), {'type', 'from', 'to', 'amount', 'kind', 'memo', 'ref', 'nonce', 'ts', 'sig'});
  });

  test('buildSignedCreditTransfer refuses what the hub would refuse', () async {
    final key = await SeedKey.fromSeed(unhex(seedHex));
    Future<void> bad({String? from, String to = kCreditTreasury, int amount = 1, String kind = 'purchase', String? ref}) =>
        expectLater(
            buildSignedCreditTransfer(
                from: from ?? key.pub, to: to, amount: amount, kind: kind, ref: ref, sign: key.sign),
            throwsArgumentError);
    await bad(from: key.pub.toUpperCase());
    await bad(to: key.pub);
    await bad(amount: 0);
    await bad(amount: 1000001);
    await bad(kind: 'grant');
    await bad(kind: 'tip'); // no ref
    await bad(ref: 'has space');
    // Memo is trimmed and control characters dropped, like the daemon's credit_memo.
    final t = await buildSignedCreditTransfer(
        from: key.pub, to: kCreditTreasury, amount: 1, kind: 'transfer', memo: '  hi\u0001 ', sign: key.sign);
    expect(t['memo'], 'hi');
    expect((t['nonce'] as String).length, 32);
  });

  test('HTTP answers map to states', () {
    expect(CreditsResult<Map<String, dynamic>>.fromHttp(200, {'balance': 1}).state, CreditsState.ok);
    expect(CreditsResult<Map<String, dynamic>>.fromHttp(401, {'message': 'missing or invalid local token'}).state,
        CreditsState.unauthorized);
    expect(CreditsResult<Map<String, dynamic>>.fromHttp(401, {'message': 'bad signature: ...'}).state,
        CreditsState.rejected);
    expect(CreditsResult<Map<String, dynamic>>.fromHttp(403, {'message': 'loopback only'}).state,
        CreditsState.forbidden);
    expect(CreditsResult<Map<String, dynamic>>.fromHttp(404, null).state, CreditsState.unsupported);
    expect(CreditsResult<Map<String, dynamic>>.fromHttp(409, {'integrity': 'FAILED'}).state, CreditsState.integrity);
    expect(CreditsResult<Map<String, dynamic>>.fromHttp(409, {'message': 'insufficient'}).state,
        CreditsState.rejected);
    expect(CreditsResult<Map<String, dynamic>>.fromHttp(409, {'integrity': 'FAILED'}).hubProblem, isTrue);
    expect(CreditsResult<Map<String, dynamic>>.fromHttp(409, {'message': 'x'}).hubProblem, isFalse);
  });

  test('nothing listening -> unreachable, never a number', () async {
    final s = await ServerSocket.bind(InternetAddress.loopbackIPv4, 0);
    final port = s.port;
    await s.close();
    final r = await HubCreditsClient(OmniHubClient(ipcPort: port)).balance(pubA);
    expect(r.state, CreditsState.unreachable);
    expect(r.value, isNull);
    expect(r.hubProblem, isTrue);
  });

  test('balance, history and send against a fake hub, with the local token as Bearer', () async {
    final hub = FakeCreditsHub()..requiredToken = 'tok123';
    await hub.start();
    try {
      final noToken = await HubCreditsClient(hub.client()).balance(pubA);
      expect(noToken.state, CreditsState.unauthorized);

      final c = HubCreditsClient(hub.client(token: 'tok123'));
      final b = await c.balance(pubA);
      expect(b.ok, isTrue);
      expect(b.value!.available, 1000);
      expect(b.value!.feeBps, 2000);
      expect(hub.seen.last.uri.queryParameters['pubkey'], pubA);

      final h = await c.history(pubA, limit: 500);
      expect(h.ok, isTrue);
      expect(hub.seen.last.uri.queryParameters['limit'], '200');
      expect(h.value!.entries.single.delta, 1000);
      expect(h.value!.entries.single.from, kCreditTreasury);

      final key = await SeedKey.fromSeed(unhex(seedHex));
      final t = await buildSignedCreditTransfer(
          from: key.pub, to: kCreditTreasury, amount: 100, kind: 'purchase', ref: 'item_01', sign: key.sign);
      final s = await c.send(t);
      expect(s.ok, isTrue);
      expect(s.value!.balance, 900);
      expect(s.value!.eventId, '0xdef');
      expect(hub.seen.last.headers.contentLength, greaterThan(0));
      expect(hub.sends.single['sig'], t['sig']);

      final big = await buildSignedCreditTransfer(
          from: key.pub, to: kCreditTreasury, amount: 5000, kind: 'purchase', sign: key.sign);
      final over = await c.send(big);
      expect(over.state, CreditsState.rejected);
      expect(over.hubProblem, isFalse);
    } finally {
      await hub.server.close(force: true);
    }
  });

  final livePort = int.tryParse(Platform.environment['OMNI_CREDITS_LIVE_IPC_PORT'] ?? '');
  test('live daemon: balance, signed purchase, ALREADY_APPLIED retry, history', () async {
    final c = HubCreditsClient(OmniHubClient(
        ipcPort: livePort!, token: Platform.environment['OMNI_CREDITS_LIVE_TOKEN'], timeout: const Duration(seconds: 5)));
    final key = await SeedKey.fromSeed(List<int>.generate(32, (i) => (i * 7 + DateTime.now().millisecond) % 256));
    final b0 = await c.balance(key.pub);
    expect(b0.ok, isTrue, reason: '${b0.state} ${b0.message}');
    expect(b0.value!.available, 1000);
    final t = await buildSignedCreditTransfer(
        from: key.pub, to: kCreditTreasury, amount: 250, kind: 'purchase', ref: 'item_02', memo: vMemo, sign: key.sign);
    final s1 = await c.send(t);
    expect(s1.ok, isTrue, reason: '${s1.state} ${s1.message}');
    expect(s1.value!.balance, 750);
    final s2 = await c.send(t);
    expect(s2.ok, isTrue);
    expect(s2.value!.alreadyApplied, isTrue);
    final over = await c.send(await buildSignedCreditTransfer(
        from: key.pub, to: kCreditTreasury, amount: 5000, kind: 'purchase', sign: key.sign));
    expect(over.state, CreditsState.rejected);
    final h = await c.history(key.pub);
    expect(h.ok, isTrue);
    expect(h.value!.entries.first.delta, -250);
    expect(h.value!.entries.first.memo, vMemo);
    expect(h.value!.entries.first.signedBySender, isTrue);
    expect((await c.balance(key.pub)).value!.balance, 750);
  }, skip: livePort == null ? 'set OMNI_CREDITS_LIVE_IPC_PORT to run against a daemon' : false);
}
