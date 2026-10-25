import 'dart:convert';
import 'dart:io';

class IPCDaemonClient {
  final String host;
  final int telemetryPort;
  final int eventPort;

  IPCDaemonClient({
    this.host = '127.0.0.1',
    this.telemetryPort = 9100,
    this.eventPort = 5000,
  });

  Future<Map<String, dynamic>?> fetchNodeHealth() async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 2);
    try {
      final req = await client.getUrl(
        Uri.parse('http://$host:$telemetryPort/api/v1/telemetry/node-health'),
      );
      final resp = await req.close();
      if (resp.statusCode == 200) {
        final body = await resp.transform(utf8.decoder).join();
        return jsonDecode(body) as Map<String, dynamic>;
      }
    } catch (_) {
    } finally {
      client.close();
    }
    return null;
  }
}
