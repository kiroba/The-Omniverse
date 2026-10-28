import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:omni_hub_core/views/omnicast_video_chat_ui.dart';

void main() {
  testWidgets('OmniCast P2P UI Smoke Test', (WidgetTester tester) async {
    // Build OmniCast App and trigger a frame.
    await tester.pumpWidget(const OmniCastApp());

    // Verify title and main action button are rendered.
    expect(find.text('OmniCast P2P'), findsOneWidget);
    expect(find.text('Authenticate & Connect Stargate Key'), findsOneWidget);

    // Tap button to initiate Stargate Enclave authentication.
    await tester.tap(find.byType(ElevatedButton));
    await tester.pump();

    // Verify progress indicator appears during attestation.
    expect(find.text('Attesting Stargate Hardware Enclave Key...'), findsOneWidget);

    // Advance fake timer to complete the delayed attestation and transition to lobby
    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();

    // Verify navigation to OmniCast Dialer Lobby
    expect(find.text('OmniCast Dialer'), findsOneWidget);
  });
}
