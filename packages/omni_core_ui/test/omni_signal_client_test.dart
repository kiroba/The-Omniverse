// Tests for mobile/lib/omni_signal_client.dart (OmniCast step 2).
//
// The client lives in mobile/lib (copied into apps by build_multi_app_suite.py)
// but is pure Dart, so it is tested here where CI already runs `flutter test`.
//
// Cross-language vectors: generated with the daemon's own
// signal_send_bytes / signal_auth_bytes (Admin/omni_live_daemon_server.py,
// desktop, v8.11.0) and the `cryptography` package, seeds 0..31 (A) and 32..63
// (B). The same vectors are asserted on the Python side in
// tests/test_signal_mailbox.py (SignalVectorTests).
//
// Optional live check against a real daemon: set OMNI_SIGNAL_LIVE_IPC_PORT to a
// running daemon's :5000 port on 127.0.0.1.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:cryptography/cryptography.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../mobile/lib/omni_signal_client.dart';

const seedAHex = '000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f';
const pubA = '03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8';
const seedBHex = '202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f';
const pubB = '29acbae141bccaf0b22e1a94d34d0bc7361e526d0bfe12c89794bc9322966dd7';
const vTs = 1793042651190;
const vCallId = 'call-vector_1.a:b';
// CRLF, non-ASCII (í, 🎧), quote, backslash, slash, tab, U+2028, U+0001, DEL.
const vPayload = 'v=0\r\no=- 46117 2 IN IP4 127.0.0.1\r\ns=K\u00edro \u{1F3A7} "q" \\ /\t\u2028\u0001\u007f\r\n';
const vSendBytesHex =
    '7b2263616c6c5f6964223a2263616c6c2d766563746f725f312e613a62222c2266726f6d223a223033613130376266663363653130626531643730646431386537346263303939363765346436333039626135306435663164646338363634313235353331623822'
    '2c226b696e64223a226f66666572222c227061796c6f6164223a22763d305c725c6e6f3d2d203436313137203220494e20495034203132372e302e302e315c725c6e733d4bc3ad726f20f09f8ea7205c22715c22205c5c202f5c74e280a85c75303030317f5c725c6e22'
    '2c22746f223a2232396163626165313431626363616630623232653161393464333464306263373336316535323664306266653132633839373934626339333232393636646437222c227473223a313739333034323635313139302c2274797065223a226f6d6e69636173742e7369676e616c2e7631227d';
const vSendSig =
    'afe1e65c40101a39de0e9f12882ff6fc42bcee1f1d2839637ad27664f5cc7d6b67fe3f3e923d7bbd5aa643a71ff0e322c733aea0435c0a96eefe96c210060209';
const vPollText =
    '{"to":"29acbae141bccaf0b22e1a94d34d0bc7361e526d0bfe12c89794bc9322966dd7","ts":1793042651191,"type":"omnicast.poll.v1"}';
const vPollSig =
    'ddfd60d8474e6e45f06cd64dbbcdcfda042dbe0f1604a9f9b644807c6fccc91565d1c4a68875262a536a3457ef00ea752d36999c2ba5550a2dc9192499763702';
const vIceText =
    '{"pubkey":"03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8","ts":1793042651192,"type":"omnicast.ice-config.v1"}';
const vIceSig =
    '8ad5e9c912765e54c0050122176af04b440e69bfde3dc50e0564ef479f32327d5dda34c195fc9ebf216e37d39663d827bf14eac1a11eada842233fcaa7c37803';

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

  static Future<SeedKey> random() async {
    final kp = await Ed25519().newKeyPair();
    return SeedKey._(kp, hex((await kp.extractPublicKey()).bytes));
  }

  Future<String> sign(List<int> m) async => hex((await Ed25519().sign(m, keyPair: kp)).bytes);
}

/// Minimal in-process hub with the daemon's mailbox rules that matter to the
/// client: signature checks, delete on delivery, long-poll. [dropNext] makes
/// the hub lose the next N delivered messages (at-most-once in action).
class FakeHub {
  late HttpServer server;
  final boxes = <String, List<Map<String, dynamic>>>{};
  final waiters = <String, Completer<void>>{};
  final seen = <String>{};
  int seq = 0;
  int dropNextOffers = 0;
  int polls = 0;
  int sends = 0;
  int failNextPolls = 0; // answer 500 to the next N polls
  int clockSkewMs = 0; // hub clock = real + skew
  String? lastAuth;

  int get port => server.port;
  int now() => DateTime.now().millisecondsSinceEpoch + clockSkewMs;

  Future<void> start() async {
    server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen(_handle);
  }

  Future<void> stop() => server.close(force: true);

  void _json(HttpRequest r, int code, Object body) {
    r.response.statusCode = code;
    r.response.headers.contentType = ContentType.json;
    r.response.headers.date = DateTime.fromMillisecondsSinceEpoch(now(), isUtc: true);
    r.response.write(jsonEncode(body));
    r.response.close();
  }

  bool _tsOk(int ts) => (now() - ts).abs() <= 120000;

  Future<void> _handle(HttpRequest r) async {
    lastAuth = r.headers.value(HttpHeaders.authorizationHeader);
    if (failNextPolls > 0 && r.uri.path == '/api/signal/poll') {
      failNextPolls--;
      return _json(r, 500, {'status': 'ERROR', 'message': 'boom'});
    }
    final p = r.uri.path;
    if (p == '/api/signal/send' && r.method == 'POST') {
      sends++;
      if (r.contentLength < 0) return _json(r, 411, {'status': 'ERROR', 'message': 'length required'});
      final m = jsonDecode(await utf8.decoder.bind(r).join()) as Map<String, dynamic>;
      if (m.keys.toSet().difference({'to', 'from', 'call_id', 'kind', 'payload', 'ts', 'sig'}).isNotEmpty ||
          m.length != 7) {
        return _json(r, 400, {'status': 'ERROR', 'message': 'fields'});
      }
      if (!_tsOk(m['ts'] as int)) {
        return _json(r, 401, {'status': 'ERROR', 'message': "stale or future 'ts' (must be within 120 s of the hub clock)"});
      }
      final bytes = signalSendBytes(
          to: m['to'], from: m['from'], callId: m['call_id'], kind: m['kind'], payload: m['payload'], ts: m['ts']);
      if (!await verifySignalSignature(bytes, m['sig'], m['from'])) {
        return _json(r, 401, {'status': 'ERROR', 'message': 'bad signature'});
      }
      if (!seen.add(m['sig'] as String)) return _json(r, 409, {'status': 'ERROR', 'message': 'replayed'});
      if (m['kind'] == 'offer' && dropNextOffers > 0) {
        dropNextOffers--; // queued, then "lost in transit"
        return _json(r, 200, {'status': 'QUEUED', 'seq': ++seq, 'expires_in': 60});
      }
      boxes.putIfAbsent(m['to'], () => []).add({...m, 'seq': ++seq});
      waiters.remove(m['to'])?.complete();
      return _json(r, 200, {'status': 'QUEUED', 'seq': seq, 'expires_in': 60});
    }
    if (p == '/api/signal/poll') {
      polls++;
      final q = r.uri.queryParameters;
      final to = q['to']!, ts = int.parse(q['ts']!);
      if (q.containsKey('since')) return _json(r, 400, {'status': 'ERROR', 'message': 'client should not send since'});
      if (!_tsOk(ts)) {
        return _json(r, 401, {'status': 'ERROR', 'message': "stale or future 'ts' (must be within 120 s of the hub clock)"});
      }
      if (!await verifySignalSignature(signalAuthBytes(kSignalPollType, to, ts), q['sig']!, to)) {
        return _json(r, 401, {'status': 'ERROR', 'message': 'bad signature'});
      }
      if (!seen.add(q['sig']!)) return _json(r, 409, {'status': 'ERROR', 'message': 'replayed'});
      final wait = int.tryParse(q['wait'] ?? '0') ?? 0;
      if ((boxes[to] ?? []).isEmpty && wait > 0) {
        final c = Completer<void>();
        waiters[to] = c;
        await c.future.timeout(Duration(seconds: wait), onTimeout: () {});
      }
      final msgs = boxes.remove(to) ?? [];
      return _json(r, 200, {'status': 'OK', 'count': msgs.length, 'cursor': seq, 'messages': msgs});
    }
    if (p == '/api/signal/ice-config') {
      final q = r.uri.queryParameters;
      final pk = q['pubkey']!, ts = int.parse(q['ts']!);
      if (!_tsOk(ts)) {
        return _json(r, 401, {'status': 'ERROR', 'message': "stale or future 'ts' (must be within 120 s of the hub clock)"});
      }
      if (!await verifySignalSignature(signalAuthBytes(kSignalIceType, pk, ts), q['sig']!, pk)) {
        return _json(r, 401, {'status': 'ERROR', 'message': 'bad signature'});
      }
      return _json(r, 200, {
        'status': 'OK',
        'turn': true,
        'ttl': 3600,
        'expires_at': 1793046251,
        'ice_transport_policy': 'relay',
        'ice_servers': [
          {'urls': ['stun:stun.l.google.com:19302']},
          {
            'urls': ['turn:100.101.102.103:3478?transport=udp', 'turn:100.101.102.103:3478?transport=tcp'],
            'username': '1793046251:$pk',
            'credential': 'c2VjcmV0',
          },
        ],
      });
    }
    return _json(r, 404, {'status': 'ERROR', 'message': 'not found'});
  }

  /// Puts a raw message straight in a mailbox (to test what the client drops).
  void inject(Map<String, dynamic> m) {
    boxes.putIfAbsent(m['to'], () => []).add({...m, 'seq': ++seq});
    waiters.remove(m['to'])?.complete();
  }
}

void main() {
  group('cross-language vectors (Python daemon v8.11.0)', () {
    test('send canonical bytes match Python byte-for-byte', () {
      final b = signalSendBytes(to: pubB, from: pubA, callId: vCallId, kind: 'offer', payload: vPayload, ts: vTs);
      expect(hex(b), vSendBytesHex);
    });

    test('seed A -> pubkey A, seed B -> pubkey B', () async {
      expect((await SeedKey.fromSeed(unhex(seedAHex))).pub, pubA);
      expect((await SeedKey.fromSeed(unhex(seedBHex))).pub, pubB);
    });

    test('Dart signature equals the Python signature (Ed25519 is deterministic)', () async {
      final a = await SeedKey.fromSeed(unhex(seedAHex));
      expect(await a.sign(unhex(vSendBytesHex)), vSendSig);
    });

    test('Python-signed message verifies; any changed field does not', () async {
      final m = SignalMessage(
          seq: 1, from: pubA, to: pubB, callId: vCallId, kind: SignalKind.offer, payload: vPayload, ts: vTs, sig: vSendSig);
      expect(await m.verify(), isTrue);
      Future<bool> v(SignalMessage x) => x.verify();
      SignalMessage w({String? to, String? cid, SignalKind? k, String? p, int? ts}) => SignalMessage(
          seq: 1, from: pubA, to: to ?? pubB, callId: cid ?? vCallId, kind: k ?? SignalKind.offer,
          payload: p ?? vPayload, ts: ts ?? vTs, sig: vSendSig);
      expect(await v(w(p: '${vPayload}a=evil\r\n')), isFalse);
      expect(await v(w(to: pubA)), isFalse);
      expect(await v(w(cid: 'call-other')), isFalse);
      expect(await v(w(k: SignalKind.answer)), isFalse);
      expect(await v(w(ts: vTs + 1)), isFalse);
      // wrong claimed sender
      final forged = SignalMessage(
          seq: 1, from: pubB, to: pubB, callId: vCallId, kind: SignalKind.offer, payload: vPayload, ts: vTs, sig: vSendSig);
      expect(await forged.verify(), isFalse);
    });

    test('poll and ice-config auth bytes and signatures match Python', () async {
      final a = await SeedKey.fromSeed(unhex(seedAHex));
      final b = await SeedKey.fromSeed(unhex(seedBHex));
      final pb = signalAuthBytes(kSignalPollType, pubB, vTs + 1);
      final ib = signalAuthBytes(kSignalIceType, pubA, vTs + 2);
      expect(utf8.decode(pb), vPollText);
      expect(utf8.decode(ib), vIceText);
      expect(await b.sign(pb), vPollSig);
      expect(await a.sign(ib), vIceSig);
    });
  });

  group('local validation', () {
    test('lone surrogates are detected (Python could not sign them)', () {
      expect(hasLoneSurrogate('ok \u{1F3A7}'), isFalse);
      expect(hasLoneSurrogate(String.fromCharCode(0xD83C)), isTrue);
      expect(hasLoneSurrogate('a${String.fromCharCode(0xDFA7)}b'), isTrue);
    });

    test('call ids and payload limits', () async {
      final a = await SeedKey.random();
      final c = OmniSignalClient(hub: const SignalHub.loopback(ipcPort: 1), pubkeyHex: a.pub, sign: a.sign);
      expect(isValidCallId(newCallId()), isTrue);
      expect(() => c.send(pubB, 'bad id', SignalKind.ring, ''), throwsArgumentError);
      expect(() => c.send('XX', 'c1', SignalKind.ring, ''), throwsArgumentError);
      // 14,336 code points max; an emoji is 2 UTF-16 units but 1 code point (Python len)
      expect(() => c.send(pubB, 'c1', SignalKind.offer, 'x' * (14 * 1024 + 1)), throwsArgumentError);
    });

    test('bearer only for a remote hub with a token', () {
      expect(const SignalHub(host: '127.0.0.1', token: 't').authorization, isNull);
      expect(const SignalHub(host: '', token: 't').authorization, isNull);
      expect(const SignalHub(host: '100.64.0.9', token: '').authorization, isNull);
      expect(const SignalHub(host: '100.64.0.9', token: 'abc').authorization, 'Bearer abc');
      expect(const SignalHub(host: '100.64.0.9').uri('/api/signal/send').toString(),
          'http://100.64.0.9:5000/api/signal/send');
    });

    test('fresh ts is strictly increasing', () async {
      final a = await SeedKey.random();
      final c = OmniSignalClient(hub: const SignalHub.loopback(), pubkeyHex: a.pub, sign: a.sign, nowMs: () => 1000);
      expect([c.freshTs(), c.freshTs(), c.freshTs()], [1000, 1001, 1002]);
    });
  });

  group('against a fake hub', () {
    late FakeHub hub;
    late SeedKey alice, bob;
    late OmniSignalClient ca, cb;

    setUp(() async {
      hub = FakeHub();
      await hub.start();
      alice = await SeedKey.random();
      bob = await SeedKey.random();
      ca = OmniSignalClient(hub: SignalHub.loopback(ipcPort: hub.port), pubkeyHex: alice.pub, sign: alice.sign, longPollSeconds: 2);
      cb = OmniSignalClient(hub: SignalHub.loopback(ipcPort: hub.port), pubkeyHex: bob.pub, sign: bob.sign, longPollSeconds: 2);
    });

    tearDown(() async {
      await ca.close();
      await cb.close();
      await hub.stop();
    });

    test('send -> poll delivers once, verified, non-ASCII intact; no bearer on loopback', () async {
      final r = await ca.send(bob.pub, 'call-1', SignalKind.ring, '{"caller":"K\u00edro \u{1F3A7}"}');
      expect(r.ok, isTrue, reason: '$r');
      expect(hub.lastAuth, isNull);
      final got = await cb.pollOnce();
      expect(got, hasLength(1));
      expect(got.first.payload, '{"caller":"K\u00edro \u{1F3A7}"}');
      expect(got.first.kind, SignalKind.ring);
      expect(await cb.pollOnce(), isEmpty);
    });

    test('drops tampered, forged, misaddressed, stale and duplicate messages', () async {
      Future<Map<String, dynamic>> signed(SeedKey k, String to, String payload, {int? ts}) async {
        final t = ts ?? DateTime.now().millisecondsSinceEpoch;
        final sig = await k.sign(signalSendBytes(to: to, from: k.pub, callId: 'c1', kind: 'offer', payload: payload, ts: t));
        return {'to': to, 'from': k.pub, 'call_id': 'c1', 'kind': 'offer', 'payload': payload, 'ts': t, 'sig': sig};
      }

      final good = await signed(alice, bob.pub, 'good');
      hub.inject({...await signed(alice, bob.pub, 'x'), 'payload': 'tampered'});
      hub.inject({...await signed(alice, bob.pub, 'y'), 'from': (await SeedKey.random()).pub});
      final other = await SeedKey.random();
      hub.inject(await signed(alice, other.pub, 'for someone else'));
      hub.inject({...await signed(alice, other.pub, 'z'), 'to': bob.pub}); // re-addressed
      hub.inject(await signed(alice, bob.pub, 'old', ts: DateTime.now().millisecondsSinceEpoch - 600000));
      hub.inject({'to': bob.pub, 'garbage': true});
      hub.inject(good);
      hub.inject(good); // a hub re-delivering the same signed message
      final got = await cb.pollOnce();
      expect(got.map((m) => m.payload).toList(), ['good']);
      hub.inject(good); // and again on a later poll
      expect(await cb.pollOnce(), isEmpty);
    });

    test('ice-config: servers ready for flutter_webrtc, relay policy', () async {
      final servers = await ca.fetchIceConfig();
      expect(servers, hasLength(2));
      expect(servers[0], {'urls': ['stun:stun.l.google.com:19302']});
      expect(servers[1]['username'], '1793046251:${alice.pub}');
      expect(servers[1]['urls'], isA<List<String>>());
      final cfg = await ca.fetchIceConfiguration();
      expect(cfg.iceTransportPolicy, 'relay');
      expect(cfg.rtcConfiguration['iceTransportPolicy'], 'relay');
      expect(cfg.rtcConfiguration['iceServers'], same(cfg.iceServers));
    });

    test('phone clock 10 min off: learns the hub clock from Date and retries once', () async {
      for (final skew in [10 * 60 * 1000, -10 * 60 * 1000]) {
        hub.clockSkewMs = skew;
        final r = await ca.send(bob.pub, 'call-skew', SignalKind.ring, '');
        expect(r.ok, isTrue, reason: '$r');
        expect(ca.clockOffsetMs, closeTo(skew, 2000));
        expect(await cb.pollOnce(), hasLength(1)); // bob learns it on his first call too
        expect(cb.clockOffsetMs, closeTo(skew, 2000));
      }
    });

    test('poll loop streams messages, backs off on errors, stops on cancel', () async {
      hub.failNextPolls = 2; // first two polls fail -> backoff 1 s, 2 s
      final received = <SignalMessage>[];
      final sub = cb.messages().listen(received.add, onError: (_) {}, cancelOnError: false);
      await Future<void>.delayed(const Duration(milliseconds: 300));
      expect(hub.polls, 0); // still backing off (the two failures don't count as polls)
      await ca.send(bob.pub, 'call-2', SignalKind.offer, 'sdp-1');
      await ca.sendIce(bob.pub, 'call-2', candidate: 'candidate:1 1 udp 1 100.64.0.2 5000 typ relay', sdpMid: '0', sdpMLineIndex: 0);
      final deadline = DateTime.now().add(const Duration(seconds: 10));
      while (received.length < 2 && DateTime.now().isBefore(deadline)) {
        await Future<void>.delayed(const Duration(milliseconds: 100));
      }
      expect(received.map((m) => m.kind).toList(), [SignalKind.offer, SignalKind.ice]);
      expect(received[1].iceCandidate?['sdpMLineIndex'], 0);
      await sub.cancel();
      final pollsAtCancel = hub.polls;
      await Future<void>.delayed(const Duration(seconds: 3));
      expect(hub.polls, lessThanOrEqualTo(pollsAtCancel + 1));
    });

    test('a 401 from the hub is surfaced as a SignalHubException error event', () async {
      final mallory = await SeedKey.random();
      // pubkey says bob, signature by mallory -> hub answers 401 bad signature
      final bad = OmniSignalClient(hub: SignalHub.loopback(ipcPort: hub.port), pubkeyHex: bob.pub, sign: mallory.sign);
      final errs = <Object>[];
      final sub = bad.messages().listen((_) {}, onError: errs.add, cancelOnError: false);
      final deadline = DateTime.now().add(const Duration(seconds: 5));
      while (errs.isEmpty && DateTime.now().isBefore(deadline)) {
        await Future<void>.delayed(const Duration(milliseconds: 50));
      }
      await sub.cancel();
      expect(errs.first, isA<SignalHubException>());
      expect((errs.first as SignalHubException).statusCode, 401);
    });

    test('offer lost in transit: OfferResender re-sends, callee answers once and re-answers duplicates', () async {
      hub.dropNextOffers = 1;
      final aliceIn = ca.messages().asBroadcastStream();
      final tracker = CalleeOfferTracker();
      var answersSent = 0;
      final bobSub = cb.messages().listen((m) async {
        if (m.kind != SignalKind.offer) return;
        switch (tracker.onOffer(m)) {
          case OfferDisposition.fresh:
            answersSent++;
            await tracker.answer(cb, m, 'answer-sdp');
          case OfferDisposition.duplicatePending:
            break;
          case OfferDisposition.duplicateAnswered:
            await tracker.resendAnswer(cb, m);
        }
      });
      final resender = OfferResender(ca, interval: const Duration(milliseconds: 400), timeout: const Duration(seconds: 15));
      final answer = await resender.sendUntilAnswered(to: bob.pub, callId: 'call-3', sdp: 'offer-sdp', incoming: aliceIn);
      expect(answer?.payload, 'answer-sdp');
      expect(answer?.from, bob.pub);
      expect(resender.sends, greaterThanOrEqualTo(2)); // the first copy was lost
      expect(answersSent, 1);
      await bobSub.cancel();
    });

    test('OfferResender gives up at the ring timeout and on hangup', () async {
      final aliceIn = ca.messages().asBroadcastStream();
      final r1 = OfferResender(ca, interval: const Duration(milliseconds: 300), timeout: const Duration(seconds: 1));
      expect(await r1.sendUntilAnswered(to: bob.pub, callId: 'call-4', sdp: 's', incoming: aliceIn), isNull);
      expect(r1.sends, inInclusiveRange(2, 5));
      final r2 = OfferResender(ca, interval: const Duration(milliseconds: 300), timeout: const Duration(seconds: 10));
      unawaited(Future<void>.delayed(const Duration(milliseconds: 500), () => cb.hangup(alice.pub, 'call-5')));
      final t0 = DateTime.now();
      expect(await r2.sendUntilAnswered(to: bob.pub, callId: 'call-5', sdp: 's', incoming: aliceIn), isNull);
      expect(DateTime.now().difference(t0), lessThan(const Duration(seconds: 6)));
    });
  });

  final livePort = int.tryParse(Platform.environment['OMNI_SIGNAL_LIVE_IPC_PORT'] ?? '');
  group('live daemon (OMNI_SIGNAL_LIVE_IPC_PORT)', () {
    test('send, long-poll, verify and ice-config against a real hub', () async {
      final a = await SeedKey.random(), b = await SeedKey.random();
      final hub = SignalHub.loopback(ipcPort: livePort!);
      final ca = OmniSignalClient(hub: hub, pubkeyHex: a.pub, sign: a.sign);
      final cb = OmniSignalClient(hub: hub, pubkeyHex: b.pub, sign: b.sign, longPollSeconds: 5);
      final pending = cb.pollOnce(wait: 5);
      await Future<void>.delayed(const Duration(milliseconds: 300));
      final r = await ca.send(b.pub, newCallId(), SignalKind.offer, vPayload);
      expect(r.ok, isTrue, reason: '$r');
      final got = await pending;
      expect(got, hasLength(1));
      expect(got.first.payload, vPayload);
      expect(await cb.pollOnce(), isEmpty);
      final cfg = await ca.fetchIceConfiguration();
      expect(cfg.iceServers, isNotEmpty);
      if (cfg.turn) expect(cfg.iceTransportPolicy, 'relay');
      // a phone whose clock is 10 minutes slow still gets through (Date-header sync)
      final slow = OmniSignalClient(
          hub: hub, pubkeyHex: a.pub, sign: a.sign,
          nowMs: () => DateTime.now().millisecondsSinceEpoch - 600000);
      final r2 = await slow.send(b.pub, 'c', SignalKind.ring, '');
      expect(r2.ok, isTrue, reason: '$r2');
      expect(slow.clockOffsetMs, closeTo(600000, 2000));
      expect((await cb.pollOnce()).single.kind, SignalKind.ring);
    });
  }, skip: livePort == null ? 'set OMNI_SIGNAL_LIVE_IPC_PORT to run' : false);
}
