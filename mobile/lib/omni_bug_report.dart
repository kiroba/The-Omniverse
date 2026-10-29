// omni_bug_report.dart - "Report a bug" sheet for pre-alpha testers.
//
// Two ways out, both always available:
//   * Report on GitHub: opens the bug_report.yml issue form, prefilled.
//   * Email instead:    opens the mail app addressed to the developer.
// If the app has a hub configured, the report is ALSO posted (fire-and-forget)
// to the hub's POST /api/bugs/report (daemon v8.9.0+), where it is stored as a
// signed `bug_report` event for OmniMind triage. A hub failure never blocks or
// delays the GitHub/email path.
//
// Privacy: only what the tester types plus app name/version, device model and
// Android version. Never identity seeds, tokens, or message contents.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:device_info_plus/device_info_plus.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

const String kOmniAppVersion =
    String.fromEnvironment('OMNI_APP_VERSION', defaultValue: '0.1.10');
const String _issueFormUrl =
    'https://github.com/kiroba/The-Omniverse/issues/new';
const String _devEmail = 'keithb2290@gmail.com';

/// Optional hub to store the report on. `host` empty means this device
/// (127.0.0.1); `token` is only sent to a remote hub.
class BugReportHub {
  final String host;
  final int ipcPort;
  final String token;
  const BugReportHub({this.host = '', this.ipcPort = 5000, this.token = ''});
}

Future<({String device, String android})> _deviceInfo() async {
  try {
    if (Platform.isAndroid) {
      final a = await DeviceInfoPlugin().androidInfo;
      return (
        device: '${a.manufacturer} ${a.model}'.trim(),
        android: '${a.version.release} (SDK ${a.version.sdkInt})',
      );
    }
    return (device: Platform.operatingSystem, android: Platform.operatingSystemVersion);
  } catch (_) {
    return (device: 'unknown', android: 'unknown');
  }
}

String _clip(String s, int max) => s.length <= max ? s : '${s.substring(0, max)}…';

Future<bool> _postToHub(BugReportHub hub, Map<String, String> report) async {
  final client = HttpClient()..connectionTimeout = const Duration(seconds: 5);
  try {
    final remote = hub.host.isNotEmpty;
    final uri = Uri(
      scheme: 'http',
      host: remote ? hub.host : '127.0.0.1',
      port: hub.ipcPort,
      path: '/api/bugs/report',
    );
    final req = await client.postUrl(uri).timeout(const Duration(seconds: 5));
    req.headers.contentType = ContentType.json;
    if (remote && hub.token.isNotEmpty) {
      req.headers.set(HttpHeaders.authorizationHeader, 'Bearer ${hub.token}');
    }
    final body = utf8.encode(jsonEncode(report));
    req.contentLength = body.length;
    req.add(body);
    final res = await req.close().timeout(const Duration(seconds: 5));
    await res.drain<void>();
    return res.statusCode == 200 || res.statusCode == 201;
  } catch (_) {
    return false;
  } finally {
    client.close(force: true);
  }
}

/// Opens the Report a bug sheet. [appName] must match an option in the
/// GitHub issue form's App dropdown (e.g. "KickBack", "Omniverse Superapp").
Future<void> showBugReportSheet(BuildContext context,
    {required String appName, BugReportHub? hub}) {
  final what = TextEditingController();
  final steps = TextEditingController();
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: const Color(0xFF1E1E1E),
    builder: (ctx) {
      Future<void> send({required bool email}) async {
        final text = what.text.trim();
        if (text.isEmpty) {
          ScaffoldMessenger.of(ctx).showSnackBar(
              const SnackBar(content: Text('Describe what happened first.')));
          return;
        }
        final info = await _deviceInfo();
        final title = _clip(text.split('\n').first, 80);
        final report = <String, String>{
          'what_happened': _clip(text, 3000),
          'title': title,
          'app': appName,
          'app_version': kOmniAppVersion,
          'device': _clip(info.device, 120),
          'android_version': _clip(info.android, 60),
        };
        if (steps.text.trim().isNotEmpty) report['steps'] = _clip(steps.text.trim(), 2000);

        final messenger = ScaffoldMessenger.of(context);
        if (hub != null) {
          // Fire-and-forget: never awaited before launching GitHub/email.
          unawaited(_postToHub(hub, report).then((ok) {
            messenger.showSnackBar(SnackBar(
                content: Text(ok ? 'Saved to hub' : 'Hub not reachable')));
          }));
        }

        final Uri target;
        if (email) {
          final body = StringBuffer()
            ..writeln('App: $appName v$kOmniAppVersion')
            ..writeln('Device: ${report['device']}')
            ..writeln('Android: ${report['android_version']}')
            ..writeln()
            ..writeln('What happened:')
            ..writeln(report['what_happened']);
          if (report['steps'] != null) {
            body..writeln()..writeln('Steps:')..writeln(report['steps']);
          }
          target = Uri(
            scheme: 'mailto',
            path: _devEmail,
            query: 'subject=${Uri.encodeComponent('[Bug] $appName: $title')}'
                '&body=${Uri.encodeComponent(body.toString())}',
          );
        } else {
          final q = <String, String>{
            'template': 'bug_report.yml',
            'title': '[Bug]: $title',
            'app': appName,
            'app_version': kOmniAppVersion,
            'device': report['device']!,
            'android_version': report['android_version']!,
            'what_happened': _clip(report['what_happened']!, 2500),
          };
          if (report['steps'] != null) q['steps'] = _clip(report['steps']!, 1500);
          target = Uri.parse(_issueFormUrl).replace(queryParameters: q);
        }
        bool opened = false;
        try {
          opened = await launchUrl(target, mode: LaunchMode.externalApplication);
        } catch (_) {}
        if (ctx.mounted) Navigator.of(ctx).pop();
        if (!opened) {
          messenger.showSnackBar(SnackBar(
              content: Text(email
                  ? 'No mail app found. Email $_devEmail'
                  : 'Could not open the browser.')));
        }
      }

      return Padding(
        padding: EdgeInsets.only(
            left: 16, right: 16, top: 16,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Report a bug',
                style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text(
                'App version and device model are added for you. Don\'t include passwords or private messages.',
                style: TextStyle(color: Colors.grey, fontSize: 12)),
            const SizedBox(height: 12),
            TextField(
              controller: what,
              maxLines: 4,
              maxLength: 3000,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(
                  labelText: 'What happened?', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: steps,
              maxLines: 3,
              maxLength: 2000,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(
                  labelText: 'Steps to reproduce (optional)', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 8),
            FilledButton.icon(
              icon: const Icon(Icons.bug_report_outlined),
              label: const Text('Report on GitHub'),
              onPressed: () => send(email: false),
            ),
            TextButton.icon(
              icon: const Icon(Icons.email_outlined),
              label: const Text('Email instead'),
              onPressed: () => send(email: true),
            ),
          ],
        ),
      );
    },
  );
}
