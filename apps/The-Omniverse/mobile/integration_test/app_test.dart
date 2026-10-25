// ============================================================================
// THE OMNIVERSE: FLUTTER INTEGRATION TEST SUITE FOR VIRTUAL / PHYSICAL DEVICES
// Target File: integration_test/app_test.dart
// Command: flutter test integration_test/app_test.dart -d <emulator-id>
// ============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

// Import local app entrypoints
import 'package:mobile/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('The KickBack & Halo Plaza Automated E2E Test Suite', () {
    testWidgets('Complete Virtual Device Onboarding & Interactivity Walkthrough', (WidgetTester tester) async {
      // 1. Launch Main Application
      app.main();
      await tester.pumpAndSettle();

      print('✓ App Launched Successfully on Target Device.');

      // 2. Verify Feed Cleanliness (No raw Merkle hashes or dBm stats on main screen)
      expect(find.textContaining('0x0185D7BE'), findsNothing);
      expect(find.textContaining('dBm'), findsNothing);
      expect(find.text('@citizen.a8f9'), findsOneWidget);

      print('✓ Clean Feed UI Verified (Raw Telemetry successfully hidden).');

      // 3. Test Creator Tipping Interactivity ($1 Tip Button)
      final tipButton = find.widgetWithText(ElevatedButton, '\$1').first;
      expect(tipButton, findsOneWidget);
      await tester.tap(tipButton);
      await tester.pumpAndSettle();

      print('✓ Creator Tipping Action Verified.');

      // 4. Open Settings & System Diagnostics Drawer
      final settingsGear = find.byIcon(Icons.settings);
      expect(settingsGear, findsOneWidget);
      await tester.tap(settingsGear);
      await tester.pumpAndSettle();

      print('✓ Settings & System Diagnostics Drawer Opened.');

      // 5. Verify Network & Telemetry relocated inside Settings
      expect(find.text('Settings & Diagnostics'), findsOneWidget);
      expect(find.textContaining('P2P Mesh Network Health'), findsOneWidget);
      expect(find.textContaining('Local IPC Loopback'), findsOneWidget);

      print('✓ Telemetry Relocation Verified inside Settings.');

      // 6. Close Settings Drawer
      final closeButton = find.byIcon(Icons.close);
      await tester.tap(closeButton);
      await tester.pumpAndSettle();

      print('✓ Settings Drawer Dismissed.');

      // 7. Test Navigation Tab Switch to Halo Plaza Stage
      final plazaTab = find.byIcon(Icons.sports_esports);
      if (plazaTab.evaluate().isNotEmpty) {
        await tester.tap(plazaTab);
        await tester.pumpAndSettle();
        print('✓ Navigated to Halo Plaza Stage.');
      }
    });
  });
}
