import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:omni_core_ui/omni_core_ui.dart';

// A tiny stand-in for daemon v8.7.0 in remote mode: every request needs
// "Authorization: Bearer <token>", else 401 (what Admin/omni_live_daemon_server.py does).
const _token = 'test-token-0123456789abcdefghijklmnop';

Future<HttpServer> _fakeHub() async {
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((req) async {
    final auth = req.headers.value(HttpHeaders.authorizationHeader);
    if (auth != 'Bearer $_token') {
      req.response.statusCode = 401;
      req.response.write(jsonEncode({'status': 'ERROR', 'message': 'missing or invalid bearer token'}));
      await req.response.close();
      return;
    }
    req.response.headers.contentType = ContentType.json;
    if (req.uri.path == '/api/v1/telemetry/node-health') {
      req.response.write(jsonEncode({
        'status': 'ONLINE',
        'version': '8.7.0',
        'node_id': 'ab' * 32,
        'mesh_id': 'dev',
        'active_peers': 0,
      }));
    } else if (req.uri.path == '/api/events/feed') {
      req.response.write(jsonEncode({
        'status': 'OK',
        'node_id': 'ab' * 32,
        'version': '8.7.0',
        'events': [],
        'count': 0,
        'has_more': false,
        'next_before': null,
        'latest_id': 1,
      }));
    } else if (req.uri.path == '/api/events/append') {
      await utf8.decoder.bind(req).join();
      req.response.write(jsonEncode({'status': 'SUCCESS', 'event_id': '0xabc'}));
    } else {
      req.response.statusCode = 404;
    }
    await req.response.close();
  });
  return server;
}

void main() {
  late HttpServer hub;
  setUpAll(() async => hub = await _fakeHub());
  tearDownAll(() async => hub.close(force: true));

  OmniHubClient client({String? token}) =>
      OmniHubClient(host: '127.0.0.1', ipcPort: hub.port, telemetryPort: hub.port, token: token);

  test('default client is loopback and not remote', () {
    const c = OmniHubClient();
    expect(c.isRemote, isFalse);
    expect(c.token, isNull);
    expect(const OmniHubClient(host: '100.64.0.1', token: 't').isRemote, isTrue);
  });

  test('no token -> unauthorized', () async {
    final c = await client().connection();
    expect(c.state, HubConnectionState.unauthorized);
    expect(c.connected, isFalse);
  });

  test('wrong token -> unauthorized', () async {
    expect((await client(token: 'nope').connection()).state, HubConnectionState.unauthorized);
  });

  test('right token -> connected with node status', () async {
    final c = await client(token: _token).connection();
    expect(c.state, HubConnectionState.connected);
    expect(c.status.online, isTrue);
    expect(c.status.version, '8.7.0');
  });

  test('nothing listening -> unreachable', () async {
    final free = await ServerSocket.bind(InternetAddress.loopbackIPv4, 0);
    final port = free.port;
    await free.close();
    final c = await OmniHubClient(host: '127.0.0.1', telemetryPort: port, ipcPort: port, token: _token).connection();
    expect(c.state, HubConnectionState.unreachable);
  });

  test('feed: 401 is reported as unauthorized, token makes it ok', () async {
    final bad = await client().eventsFeed();
    expect(bad.state, HubFeedState.error);
    expect(bad.error, contains('unauthorized'));
    final ok = await client(token: _token).eventsFeed();
    expect(ok.state, HubFeedState.ok);
  });

  test('append sends the token', () async {
    expect((await client().appendEvent('KICKBACK_POST', {'text': 'x'}))?['status'], 'ERROR');
    expect((await client(token: _token).appendEvent('KICKBACK_POST', {'text': 'x'}))?['status'], 'SUCCESS');
  });
}
