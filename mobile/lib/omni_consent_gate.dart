// omni_consent_gate.dart - first-launch pre-alpha tester agreement.
//
// Shown once per consent version before the app's home screen. Acceptance is
// stored as a small marker file next to the app's SQLite databases (sqflite's
// getDatabasesPath, already a dependency of every generated app), so no new
// packages are needed. Bump [kOmniConsentVersion] when the terms change and
// every tester is asked again. Declining leaves the app on this screen.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

const int kOmniConsentVersion = 1;

Future<File> _markerFile() async {
  final dir = await getDatabasesPath();
  return File(p.join(dir, 'omni_consent_v$kOmniConsentVersion.txt'));
}

Future<bool> omniConsentAccepted() async {
  try {
    return await (await _markerFile()).exists();
  } catch (_) {
    return false;
  }
}

Future<void> _recordConsent() async {
  final f = await _markerFile();
  await f.parent.create(recursive: true);
  await f.writeAsString(
      'accepted v$kOmniConsentVersion at ${DateTime.now().toUtc().toIso8601String()}\n');
}

const String _terms = '''
This is a pre-alpha test build of The Omniverse. By continuing you agree that:

• You are 18 or older and were invited to test.
• The app is provided as-is. It may crash, lose data, or behave unexpectedly. Don't rely on it for anything important.
• Omni Credits in this build are test credits only. They have no cash value and may be reset at any time. No real money is charged.
• Please keep unreleased features and screenshots private until public launch.
• Your posts are stored on your own device and synced to the test hub and other testers' devices on the mesh. Don't post anything sensitive.
• Bug reports you choose to send include what you type plus app version, device model and Android version. They never include your recovery keys, tokens, or messages.
• You can stop testing at any time by uninstalling the app, which deletes your local identity.
''';

/// Wraps [child]; shows the agreement until the tester accepts it.
class OmniConsentGate extends StatefulWidget {
  final Widget child;
  final String appName;
  const OmniConsentGate({super.key, required this.child, required this.appName});

  @override
  State<OmniConsentGate> createState() => _OmniConsentGateState();
}

class _OmniConsentGateState extends State<OmniConsentGate> {
  bool? _accepted;
  bool _checked = false;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    omniConsentAccepted().then((ok) {
      if (mounted) setState(() => _accepted = ok);
    });
  }

  Future<void> _accept() async {
    setState(() => _saving = true);
    try {
      await _recordConsent();
    } catch (_) {
      // If the marker can't be written we still let them in for this session;
      // they'll simply be asked again next launch.
    }
    if (mounted) setState(() => _accepted = true);
  }

  @override
  Widget build(BuildContext context) {
    if (_accepted == true) return widget.child;
    if (_accepted == null) {
      return const Scaffold(
        backgroundColor: Color(0xFF121212),
        body: Center(child: CircularProgressIndicator()),
      );
    }
    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('${widget.appName} pre-alpha',
                  style: const TextStyle(
                      color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              const Text('Tester agreement',
                  style: TextStyle(color: Color(0xFF03DAC6), fontSize: 14)),
              const SizedBox(height: 16),
              const Expanded(
                child: SingleChildScrollView(
                  child: Text(_terms,
                      style: TextStyle(color: Colors.white70, fontSize: 14, height: 1.4)),
                ),
              ),
              CheckboxListTile(
                value: _checked,
                onChanged: (v) => setState(() => _checked = v ?? false),
                controlAffinity: ListTileControlAffinity.leading,
                contentPadding: EdgeInsets.zero,
                title: const Text('I have read and agree to these terms.',
                    style: TextStyle(color: Colors.white)),
              ),
              const SizedBox(height: 8),
              FilledButton(
                onPressed: _checked && !_saving ? _accept : null,
                child: const Text('Agree and continue'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
