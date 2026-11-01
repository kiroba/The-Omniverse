// Widget tests for the OmniMarket storefront (mobile/lib/kickback_storefront_mini_app_ui.dart).
//
// The storefront lives in mobile/lib (apps copy it from there) and only needs
// Flutter + omni_core_ui, so it is tested here where CI already runs
// `flutter test`. The hub is a fake HubCreditsClient: these tests check what
// the screen does with the node's answers (balance and history from the node,
// signed purchases sent to the node, and a "Can't reach your node" state with
// no local balance), not the HTTP itself (see hub_credits_test.dart).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:omni_core_ui/omni_core_ui.dart';

import '../../../mobile/lib/kickback_storefront_mini_app_ui.dart';

final List<int> seed = List<int>.generate(32, (i) => i);

class FakeCredits extends HubCreditsClient {
  FakeCredits() : super(const OmniHubClient());

  CreditsState state = CreditsState.ok;
  String? message;
  int balanceValue = 1000;
  final List<Map<String, dynamic>> sends = [];
  final List<CreditEntry> entries = [];

  CreditsResult<T> _fail<T>() => CreditsResult<T>(state, message: message, statusCode: 401);

  @override
  Future<CreditsResult<CreditBalance>> balance(String pubkey) async {
    if (state != CreditsState.ok) return _fail();
    return CreditsResult(CreditsState.ok,
        value: CreditBalance(pubkey: pubkey, balance: balanceValue, available: balanceValue));
  }

  @override
  Future<CreditsResult<CreditHistory>> history(String pubkey, {int limit = 50}) async {
    if (state != CreditsState.ok) return _fail();
    return CreditsResult(CreditsState.ok,
        value: CreditHistory(balance: balanceValue, entries: List.of(entries.reversed)));
  }

  @override
  Future<CreditsResult<CreditSendReceipt>> send(Map<String, dynamic> signedTransfer) async {
    if (state != CreditsState.ok) return _fail();
    sends.add(signedTransfer);
    final amount = signedTransfer['amount'] as int;
    balanceValue -= amount;
    entries.add(CreditEntry(
      eventId: '0xfeed${sends.length}',
      kind: 'purchase',
      from: signedTransfer['from'] as String,
      to: signedTransfer['to'] as String,
      amount: amount,
      fee: 0,
      memo: signedTransfer['memo'] as String,
      delta: -amount,
      balanceAfter: balanceValue,
      tsMs: signedTransfer['ts'] as int,
    ));
    return CreditsResult(CreditsState.ok,
        value: CreditSendReceipt(eventId: '0xfeed${sends.length}', balance: balanceValue, fee: 0, amount: amount));
  }
}

Widget storefront(FakeCredits fake) => MaterialApp(
      home: OmniMarketStorefrontMiniApp(
        loadHub: () async => const OmniHubClient(),
        loadIdentity: () => StargateIdentity.fromSeed(seed),
        catalogStore: MemoryStorefrontCatalog(),
        creditsClientFor: (_) => fake,
      ),
    );

/// Lets real async work (Ed25519 in package:cryptography) and frames run.
Future<void> settle(WidgetTester tester) async {
  for (var i = 0; i < 12; i++) {
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 10)));
    await tester.pump(const Duration(milliseconds: 100));
  }
}

void main() {
  testWidgets("unreachable node: \"Can't reach your node\", no balance, Buy off", (tester) async {
    final fake = FakeCredits()..state = CreditsState.unreachable;
    await tester.pumpWidget(storefront(fake));
    await settle(tester);

    expect(find.text("Can't reach your node"), findsWidgets);
    expect(find.text('— test credits'), findsOneWidget);
    expect(find.textContaining('1000'), findsNothing); // the old local seed value never appears
    final buy = tester.widget<ElevatedButton>(find.byKey(const Key('buy-item_01')));
    expect(buy.onPressed, isNull);
    expect(fake.sends, isEmpty);
  });

  testWidgets('token refused: points at Omni Node > Connect apps', (tester) async {
    final fake = FakeCredits()
      ..state = CreditsState.unauthorized
      ..message = 'missing or invalid local token';
    await tester.pumpWidget(storefront(fake));
    await settle(tester);

    expect(find.text("Can't reach your node"), findsWidgets);
    expect(find.textContaining('Omni Node > Connect apps'), findsWidgets);
    expect(find.text('— test credits'), findsOneWidget);
  });

  testWidgets('balance from the node; Buy sends a signed purchase and shows the new balance', (tester) async {
    final fake = FakeCredits();
    await tester.pumpWidget(storefront(fake));
    await settle(tester);

    expect(find.text('1000 test credits'), findsOneWidget);
    expect(find.text("Can't reach your node"), findsNothing);

    await tester.tap(find.byKey(const Key('buy-item_01')));
    await settle(tester);

    expect(fake.sends, hasLength(1));
    final t = fake.sends.single;
    final me = await tester.runAsync(() => StargateIdentity.fromSeed(seed));
    expect(t['type'], kCreditTransferType);
    expect(t['from'], me!.pubkeyHex);
    expect(t['to'], kCreditTreasury); // demo items have no merchant key
    expect(t['kind'], 'purchase');
    expect(t['ref'], 'item_01');
    expect(t['amount'], 100);
    final ok = await tester.runAsync(
        () => StargateIdentity.verifyBytes(creditTransferSigningBytes(t), t['sig'] as String, me.pubkeyHex));
    expect(ok, isTrue);

    expect(find.text('Test purchase recorded by your node'), findsOneWidget);
    expect(find.text('900 test credits'), findsOneWidget);

    // Close the dialog; the item is now equipped and can't be bought again.
    await tester.tap(find.text('Equip to Avatar'));
    await settle(tester);
    expect(find.text('Equipped'), findsOneWidget);
    final buy = tester.widget<ElevatedButton>(find.byKey(const Key('buy-item_01')));
    expect(buy.onPressed, isNull);
  });

  testWidgets('history tab lists the node ledger', (tester) async {
    final fake = FakeCredits()
      ..entries.add(const CreditEntry(
        eventId: '0xabc',
        kind: 'grant',
        from: kCreditTreasury,
        to: 'me',
        amount: 1000,
        fee: 0,
        memo: 'welcome grant: 1,000 test credits, no cash value',
        delta: 1000,
        balanceAfter: 1000,
        tsMs: 1793334636472,
      ));
    await tester.pumpWidget(storefront(fake));
    await settle(tester);

    await tester.tap(find.text('Test credits'));
    await settle(tester);
    expect(find.text('welcome grant: 1,000 test credits, no cash value'), findsOneWidget);
    expect(find.text('+1000'), findsOneWidget);
  });
}
