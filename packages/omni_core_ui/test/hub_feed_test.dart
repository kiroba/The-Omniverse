import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:omni_core_ui/omni_core_ui.dart';

// Real output of daemon v8.6.0 GET :5000/api/events/feed?limit=1: a post that
// phone B signed with its app key, relayed by B's daemon and received by this
// node over /p2p/sync. Both the node signature and the app signature are real
// (checked with Python's Ed25519 before this test was written).
const String kFeedVector = r'''{"status": "OK", "node_id": "95d2cebfe25a1cc1bd56bfbab1d948abfbe6242ec25b4d6c7010cb51f1e1f4e1", "mesh_id": "dev", "version": "8.6.0", "limit": 1, "events": [{"id": 4, "event_id": "0x296d8e38daa5c3ed88299e24210377c1a12a602d285e5b62e281381791fbd900", "type": "KICKBACK_POST", "action": "KICKBACK_POST", "author_pubkey": "44ac472406b9d7977fa380695d999f6225065a2774bae322b032cf10852344f5", "origin": "remote", "ts": 1793163300000, "ts_ms": 1793163300000, "payload": {"text": "hi from phone B é", "app": "kickback", "app_event_id": "0x05e33ea1152dd95bedddce14d54bdfc2bc62654d7ce0c14d36e4d6ba4d4e388b", "app_author_pubkey": "53839fa26fc4e88b39ca81b973b701f24740a3d0266dc10210c8d5839f54b69a", "app_signature": "abc2c59b10e413e37d384ed3b55cd33c0b8c4e096ceef70c937c49400ae19e72da79ea0066532f9b16f6f4134322ca91bce19e62f6cb41459de42f023ed4310d", "app_previous_hash": "0x0000000000000000000000000000000000000000000000000000000000000000", "app_ts": 1793163300000}, "previous_hash": "0x4444444444444444444444444444444444444444444444444444444444444444", "signature": "2d285644af9f45f6be7b1e15925d227438af0f7d1d3dc59654325cbe91a6953dde9ce1ad7d88a2a344e0493c37c4598386315f52673155137fc6d73c690d1208", "verified": true}], "count": 1, "has_more": true, "next_before": 4, "latest_id": 4}''';

void main() {
  Map<String, dynamic> vector() => jsonDecode(kFeedVector) as Map<String, dynamic>;

  test('parses the daemon feed page', () {
    final r = HubFeedResult.fromResponse(200, kFeedVector);
    expect(r.state, HubFeedState.ok);
    expect(r.events.length, 1);
    expect(r.latestId, 4);
    expect(r.nextBefore, 4);
    expect(r.hasMore, isTrue);
    expect(r.maxEventId, 4);
    final e = r.events.first;
    expect(e.action, 'KICKBACK_POST');
    expect(e.origin, 'remote');
    expect(e.ts, 1793163300000);
    expect(e.text, 'hi from phone B \u00e9');
    expect(e.dedupeKey, '0x05e33ea1152dd95bedddce14d54bdfc2bc62654d7ce0c14d36e4d6ba4d4e388b');
    expect(e.displayAuthor, '53839fa26fc4e88b39ca81b973b701f24740a3d0266dc10210c8d5839f54b69a');
    expect(e.appPayload.keys.toSet(), {'text', 'app'});
    expect(e.daemonVerified, isTrue);
  });

  test('app signature and node signature verify on device', () async {
    final e = HubFeedResult.fromResponse(200, kFeedVector).events.first;
    expect(await StargateIdentity.verify(e.appEnvelope()!), isTrue);
    expect(await StargateIdentity.verify(e.nodeEnvelope()!), isTrue);
    expect(await verifyHubEvent(e), FeedVerification.appSigned);
    expect(
      canonicalEventId(
        action: e.action,
        authorPubkey: e.displayAuthor,
        payload: e.appPayload,
        previousHash: '${e.payload['app_previous_hash']}',
        tsMs: e.payload['app_ts'] as int,
      ),
      e.dedupeKey,
    );
  });

  test('edited text is unverified even though the daemon said verified', () async {
    final j = vector();
    final ev = Map<String, dynamic>.from((j['events'] as List).first as Map);
    ev['payload'] = {...(ev['payload'] as Map), 'text': 'edited'};
    j['events'] = [ev];
    final e = HubFeedResult.fromResponse(200, jsonEncode(j)).events.first;
    expect(e.daemonVerified, isTrue);
    expect(await verifyHubEvent(e), FeedVerification.unverified);
  });

  test('without the app envelope the node signature is used', () async {
    final j = vector();
    final ev = Map<String, dynamic>.from((j['events'] as List).first as Map);
    final p = Map<String, dynamic>.from(ev['payload'] as Map)..remove('app_signature');
    ev['payload'] = p;
    j['events'] = [ev];
    final e = HubFeedResult.fromResponse(200, jsonEncode(j)).events.first;
    // Payload changed, so the node signature no longer matches either.
    expect(await verifyHubEvent(e), FeedVerification.unverified);
  });

  test('malformed rows are dropped, not fatal', () {
    final j = vector();
    j['events'] = [
      {'id': 'x'},
      42,
      ...(j['events'] as List),
    ];
    final r = HubFeedResult.fromResponse(200, jsonEncode(j));
    expect(r.state, HubFeedState.ok);
    expect(r.events.length, 1);
  });

  test('response classification', () {
    expect(HubFeedResult.fromResponse(404, '<html>Endpoint Not Found</html>').state, HubFeedState.unsupported);
    expect(HubFeedResult.fromResponse(200, '{"status":"OK","total_events":3}').state, HubFeedState.unsupported);
    expect(HubFeedResult.fromResponse(500, '{"status":"ERROR","message":"feed read failed"}').state, HubFeedState.error);
    expect(HubFeedResult.fromResponse(400, '{"status":"ERROR","message":"bad"}').error, contains('bad'));
    expect(HubFeedResult.fromResponse(200, 'not json').state, HubFeedState.error);
  });

  test('merge drops the daemon copy of a post already in the local log', () {
    final hub = HubFeedResult.fromResponse(200, kFeedVector).events;
    final local = OmniEvent(
      eventId: hub.first.dedupeKey,
      action: 'KICKBACK_POST',
      authorPubkey: hub.first.displayAuthor,
      previousHash: '${hub.first.payload['app_previous_hash']}',
      timestamp: 1793163300.0,
      tsMs: 1793163300000,
      payload: {'text': 'hi from phone B \u00e9', 'app': 'kickback'},
      signature: '${hub.first.payload['app_signature']}',
      synced: true,
    );
    expect(mergeFeed([local], hub).length, 1);
    expect(mergeFeed([local], hub).first.local, isNotNull);
    expect(mergeFeed([], [...hub, ...hub]).length, 1);
    expect(mergeFeed([], hub).first.hub, isNotNull);
  });

  group('OmniHubClient.eventsFeed', () {
    HttpServer? server;
    tearDown(() async {
      await server?.close(force: true);
      server = null;
    });

    Future<OmniHubClient> serve(int code, String body) async {
      final s = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      server = s;
      s.listen((req) {
        req.response.statusCode = code;
        req.response.headers.contentType = ContentType.json;
        req.response.write(body);
        req.response.close();
      });
      return OmniHubClient(ipcPort: s.port);
    }

    test('200 page', () async {
      final c = await serve(200, kFeedVector);
      final r = await c.eventsFeed(limit: 1, since: 0);
      expect(r.state, HubFeedState.ok);
      expect(r.events.length, 1);
    });

    test('404 means the daemon is too old', () async {
      final c = await serve(404, '{"status":"ERROR"}');
      expect((await c.eventsFeed()).state, HubFeedState.unsupported);
    });

    test('nothing listening means offline', () async {
      final s = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      final port = s.port;
      await s.close(force: true);
      final r = await OmniHubClient(ipcPort: port).eventsFeed();
      expect(r.state, HubFeedState.unreachable);
    });
  });

  group('verification is bound to content, not to the post id', () {
    const genesis = '0x0000000000000000000000000000000000000000000000000000000000000000';
    const nodePrev = '0x4444444444444444444444444444444444444444444444444444444444444444';
    List<int> seed(int b) => List<int>.filled(32, b);
    var rowId = 100;

    // A real KickBack post: signed by an app key, relayed (re-signed) by a node.
    // [claimId] replaces app_event_id after signing (app_event_id is not part of
    // what the app signs, so the app signature still checks out).
    Future<Map<String, dynamic>> post({
      required String text,
      int appSeed = 1,
      int nodeSeed = 2,
      String? claimId,
      String? appSigOverride,
      int appTs = 1793163300000,
    }) async {
      final app = await StargateIdentity.fromSeed(seed(appSeed));
      final appPayload = <String, dynamic>{'text': text, 'app': 'kickback'};
      final appStruct = eventStruct(
          action: 'KICKBACK_POST', authorPubkey: app.pubkeyHex, payload: appPayload, previousHash: genesis, tsMs: appTs);
      final appId = canonicalEventId(
          action: 'KICKBACK_POST', authorPubkey: app.pubkeyHex, payload: appPayload, previousHash: genesis, tsMs: appTs);
      final appSig = await app.sign(appStruct);
      return relay({
        ...appPayload,
        'app_event_id': claimId ?? appId,
        'app_author_pubkey': app.pubkeyHex,
        'app_signature': appSigOverride ?? appSig,
        'app_previous_hash': genesis,
        'app_ts': appTs,
      }, nodeSeed: nodeSeed, ts: appTs + 1000);
    }

    // A node-signed row around [payload] with a correct node event id.
    Future<Map<String, dynamic>> relay(Map<String, dynamic> payload, {int nodeSeed = 2, int ts = 1793163301000}) async {
      final node = await StargateIdentity.fromSeed(seed(nodeSeed));
      final struct = eventStruct(
          action: 'KICKBACK_POST', authorPubkey: node.pubkeyHex, payload: payload, previousHash: nodePrev, tsMs: ts);
      return {
        'id': rowId++,
        'event_id': canonicalEventId(
            action: 'KICKBACK_POST', authorPubkey: node.pubkeyHex, payload: payload, previousHash: nodePrev, tsMs: ts),
        'action': 'KICKBACK_POST',
        'author_pubkey': node.pubkeyHex,
        'origin': 'remote',
        'ts': ts,
        'payload': payload,
        'previous_hash': nodePrev,
        'signature': await node.sign(struct),
        'verified': true,
      };
    }

    HubFeedEvent ev(Map<String, dynamic> row) => HubFeedEvent.fromJson(row)!;

    test('the daemon vector ids are bound to their content', () {
      final e = HubFeedResult.fromResponse(200, kFeedVector).events.first;
      expect(e.appIdMatches, isTrue);
      expect(e.nodeIdMatches, isTrue);
    });

    test('reusing a post id with tampered text never inherits Verified', () async {
      final realRow = await post(text: 'real post');
      final real = ev(realRow);
      // Hostile peer: same app_event_id and app signature, different text, and
      // a perfectly valid node signature from its own key.
      final forgedPayload = {...(realRow['payload'] as Map<String, dynamic>), 'text': 'fake post'};
      final forged = ev(await relay(forgedPayload, nodeSeed: 9));

      expect(await verifyHubEvent(real), FeedVerification.appSigned);
      expect(await verifyHubEvent(forged), FeedVerification.unverified);
      expect(forged.payload['app_event_id'], real.dedupeKey);
      expect(forged.appIdMatches, isFalse);
      expect(forged.dedupeKey, isNot(real.dedupeKey));

      for (final order in [
        [real, forged],
        [forged, real],
      ]) {
        final cache = HubFeedCache();
        for (final e in order) {
          await cache.addAll([e]);
        }
        expect(cache.length, 2);
        final byText = {for (final e in cache.events) e.text: cache.verificationOf(e)};
        expect(byText['real post'], FeedVerification.appSigned);
        expect(byText['fake post'], FeedVerification.unverified);
        // The forged row cannot hide the real one in the merged feed either.
        final merged = mergeFeed([], cache.events);
        expect(merged.map((m) => m.text).toSet(), {'real post', 'fake post'});
      }
    });

    test('a valid signature paired with someone else\'s post id is unverified', () async {
      final real = ev(await post(text: 'real post'));
      // Attacker signs its own post with its own app key, then claims the
      // victim's app_event_id (which the app signature does not cover).
      final claimed = ev(await post(text: 'shadow', appSeed: 7, nodeSeed: 9, claimId: real.dedupeKey));
      expect(await StargateIdentity.verify(claimed.appEnvelope()!), isTrue);
      expect(await verifyHubEvent(claimed), FeedVerification.unverified);
      expect(claimed.dedupeKey, isNot(real.dedupeKey));
      final cache = HubFeedCache();
      await cache.addAll([real, claimed]);
      expect(cache.verificationOf(real), FeedVerification.appSigned);
      expect(cache.verificationOf(claimed), FeedVerification.unverified);
      expect(mergeFeed([], cache.events).length, 2);
    });

    test('same post id, different content: the verified copy is kept, the other is not marked', () async {
      final good = ev(await post(text: 'real post'));
      // Same content (so the id hashes out) but a bad author signature.
      final bad = ev(await post(text: 'real post', nodeSeed: 9, appSigOverride: 'ab' * 64));
      expect(bad.dedupeKey, good.dedupeKey);
      expect(bad.fingerprint, isNot(good.fingerprint));
      expect(await verifyHubEvent(bad), FeedVerification.unverified);

      final c1 = HubFeedCache();
      await c1.addAll([good]);
      await c1.addAll([bad]);
      expect(c1.length, 1);
      expect(c1.events.single.fingerprint, good.fingerprint);
      expect(c1.verificationOf(c1.events.single), FeedVerification.appSigned);
      expect(c1.verificationOf(bad), isNot(FeedVerification.appSigned));

      final c2 = HubFeedCache();
      await c2.addAll([bad]);
      expect(c2.verificationOf(c2.events.single), FeedVerification.unverified);
      await c2.addAll([good]);
      expect(c2.events.single.fingerprint, good.fingerprint);
      expect(c2.verificationOf(c2.events.single), FeedVerification.appSigned);
    });

    test('Verified (relay): a reused node event id with new content is unverified', () async {
      final realRow = await relay({'text': 'relay only', 'app': 'kickback'});
      final real = ev(realRow);
      expect(await verifyHubEvent(real), FeedVerification.nodeSigned);
      expect(real.displayAuthor, real.authorPubkey);

      // Hostile node signs new content with its own key but reuses the id.
      final fake = await relay({'text': 'fake relay', 'app': 'kickback'}, nodeSeed: 9);
      fake['event_id'] = realRow['event_id'];
      final forged = ev(fake);
      expect(await StargateIdentity.verify(forged.nodeEnvelope()!), isTrue);
      expect(forged.nodeIdMatches, isFalse);
      expect(await verifyHubEvent(forged), FeedVerification.unverified);
      expect(forged.dedupeKey, isNot(real.dedupeKey));

      final cache = HubFeedCache();
      await cache.addAll([real, forged]);
      expect(cache.length, 2);
      expect(cache.verificationOf(real), FeedVerification.nodeSigned);
      expect(cache.verificationOf(forged), FeedVerification.unverified);
      expect(mergeFeed([], cache.events).length, 2);
    });

    test('a bare app_author_pubkey without an envelope is not shown as the author', () async {
      final row = await relay({'text': 'hi', 'app': 'kickback', 'app_author_pubkey': 'ff' * 32});
      final e = ev(row);
      expect(e.hasAppEnvelope, isFalse);
      expect(e.displayAuthor, e.authorPubkey);
      expect(await verifyHubEvent(e), FeedVerification.nodeSigned);
    });

    test('cache pruning keeps at most maxEvents and drops their results', () async {
      final cache = HubFeedCache(maxEvents: 2);
      final rows = [
        for (var i = 0; i < 3; i++) ev(await post(text: 'p$i', appTs: 1793163300000 + i)),
      ];
      await cache.addAll(rows);
      expect(cache.length, 2);
      expect(cache.events.map((e) => e.text).toSet(), {'p1', 'p2'});
      expect(cache.verificationOf(rows.first), isNull);
    });
  });
}
