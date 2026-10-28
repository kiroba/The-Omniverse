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
}
