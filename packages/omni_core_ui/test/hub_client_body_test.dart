import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:omni_core_ui/omni_core_ui.dart';
import 'package:omni_core_ui/src/core_db.dart' show resyncAfterEmptyAppendBug;

// Regression test for the KickBack "posts never show up" bug: OmniHubClient._post sent its JSON
// with Transfer-Encoding: chunked and no Content-Length, and every daemon up to v8.12.0 read that
// as an empty body (stored an empty USER_ACTION event, answered SUCCESS). The fake hub below
// behaves like those daemons: it only reads Content-Length.

class _Seen {
  int? contentLength;
  bool chunked = false;
  Map<String, dynamic>? body;
}

Future<HttpServer> _contentLengthOnlyHub(_Seen seen) async {
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((req) async {
    final cl = req.headers.contentLength; // -1 when the header is absent
    seen.contentLength = cl;
    seen.chunked = req.headers.chunkedTransferEncoding;
    final raw = await utf8.decoder.bind(req).join();
    // A v8.12.0-and-older daemon: no Content-Length -> "{}".
    final text = cl > 0 ? raw : '{}';
    seen.body = jsonDecode(text) as Map<String, dynamic>;
    final ok = seen.body!['action'] == 'KICKBACK_POST';
    req.response.headers.contentType = ContentType.json;
    req.response.write(jsonEncode(ok
        ? {'status': 'SUCCESS', 'event_id': '0xabc'}
        : {'status': 'SUCCESS', 'event_id': '0xempty', 'note': 'stored as empty USER_ACTION'}));
    await req.response.close();
  });
  return server;
}

void main() {
  test('appendEvent sends Content-Length (not chunked) with the whole body', () async {
    final seen = _Seen();
    final hub = await _contentLengthOnlyHub(seen);
    addTearDown(() => hub.close(force: true));
    final client = OmniHubClient(host: '127.0.0.1', ipcPort: hub.port, telemetryPort: hub.port);
    // Non-ASCII text: Content-Length must count UTF-8 bytes, not UTF-16 code units.
    const text = 'another post ✓ café 🚀';
    final res = await client.appendEvent('KICKBACK_POST', {'text': text, 'app': 'kickback'}, tsMs: 1793333318342);
    expect(res, isNotNull);
    expect(res!['event_id'], '0xabc');
    expect(seen.chunked, isFalse);
    expect(seen.contentLength, greaterThan(0));
    expect(seen.body!['action'], 'KICKBACK_POST');
    expect((seen.body!['payload'] as Map)['text'], text);
    expect(seen.body!['ts'], 1793333318342);
    final expected = utf8.encode(jsonEncode({
      'action': 'KICKBACK_POST',
      'payload': {'text': text, 'app': 'kickback'},
      'ts': 1793333318342,
    }));
    expect(seen.contentLength, expected.length);
  });

  test('schema v3 migration re-sends every local event once', () {
    expect(resyncAfterEmptyAppendBug, 'UPDATE events SET synced = 0, hub_event_id = NULL');
  });
}
