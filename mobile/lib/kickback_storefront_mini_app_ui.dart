// kickback_storefront_mini_app_ui.dart
// OmniMarket Storefront & Merchant Studio mini-app
// Ecosystem: The Omniverse / KickBack Universe (com.kickback)
//
// Test credits come from your node (the hub daemon's TEST credits ledger,
// daemon v8.15.0+, Admin/docs/CREDITS_LEDGER.md in kiroba/Omni-Daemon):
//   - balance: GET  :5000/api/credits/balance?pubkey=<your key>
//   - history: GET  :5000/api/credits/history?pubkey=<your key>
//   - buy:     POST :5000/api/credits/send, kind "purchase", ref = item id,
//              signed by this install's StargateIdentity key.
// There is no balance on this device any more. When the node can't be used,
// the screen says "Can't reach your node" and buying is off; it never shows a
// local number instead.
//
// Still on this device (SQLite, omni_hub_immutable.db): the catalog, which
// items are equipped, the merchant-license flag and a receipt per purchase.
// The old `citizen_identity.credits` column is no longer read or written.
//
// Which hub and token: [OmniMarketStorefrontMiniApp.loadHub], built from the
// app's Hub setting. In KickBack:
//   OmniMarketStorefrontMiniApp(loadHub: () async => (await HubSettingsStore.load()).client())
// which is Omni Node on 127.0.0.1 with its local token (Omni Node > Connect
// apps) by default, or the remote hub with its bearer token.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:omni_core_ui/omni_core_ui.dart';
import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

class OmniMarketStorefrontMiniApp extends StatefulWidget {
  /// The hub to use (address + token), from the app's Hub setting.
  final Future<OmniHubClient> Function() loadHub;

  /// This install's identity. Defaults to [StargateIdentity.load].
  final Future<StargateIdentity> Function()? loadIdentity;

  /// Catalog / equipped / license storage. Defaults to [SqliteStorefrontCatalog].
  final StorefrontCatalogStore? catalogStore;

  /// Builds the credits client for a hub. Tests swap in a fake.
  final HubCreditsClient Function(OmniHubClient hub)? creditsClientFor;

  const OmniMarketStorefrontMiniApp({
    super.key,
    required this.loadHub,
    this.loadIdentity,
    this.catalogStore,
    this.creditsClientFor,
  });

  @override
  State<OmniMarketStorefrontMiniApp> createState() => _OmniMarketStorefrontMiniAppState();
}

class _OmniMarketStorefrontMiniAppState extends State<OmniMarketStorefrontMiniApp>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  late final StorefrontCatalogStore _catalog = widget.catalogStore ?? SqliteStorefrontCatalog();

  OmniHubClient? _hub;
  HubCreditsClient? _credits;
  StargateIdentity? _identity;

  CreditBalance? _balance;
  CreditHistory? _history;

  /// Set when the node can't be used (unreachable, token refused, too old,
  /// ledger integrity failure). While set, no balance is shown and buying is off.
  CreditsResult<Object?>? _nodeProblem;

  bool _isLicensedMerchant = false;
  bool _isLoading = true;
  bool _refreshing = false;
  String? _buyingItemId;
  String? _loadError;

  List<Map<String, dynamic>> _cosmeticsCatalog = [];

  String get _userPubkey => _identity?.pubkeyHex ?? '';

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _init();
  }

  Future<void> _init() async {
    try {
      _identity = await (widget.loadIdentity ?? StargateIdentity.load)();
      _hub = await widget.loadHub();
      final makeClient = widget.creditsClientFor;
      _credits = makeClient != null ? makeClient(_hub!) : HubCreditsClient(_hub!);
      await _catalog.open();
      _cosmeticsCatalog = await _catalog.items();
      _isLicensedMerchant = await _catalog.merchantLicensed(_userPubkey);
    } catch (e) {
      _loadError = '$e';
    }
    if (!mounted) return;
    setState(() => _isLoading = false);
    await _refreshFromNode();
  }

  /// Reads balance and history from the node. Never falls back to a local number.
  Future<void> _refreshFromNode() async {
    final credits = _credits;
    if (credits == null || _userPubkey.isEmpty || _refreshing) return;
    setState(() => _refreshing = true);
    final bal = await credits.balance(_userPubkey);
    CreditsResult<CreditHistory>? hist;
    if (bal.ok) hist = await credits.history(_userPubkey, limit: 100);
    if (!mounted) return;
    setState(() {
      _refreshing = false;
      if (bal.ok) {
        _balance = bal.value;
        _nodeProblem = null;
        if (hist != null && hist.ok) _history = hist.value;
        if (hist != null && hist.hubProblem) _nodeProblem = hist;
      } else {
        _balance = null;
        _history = null;
        _nodeProblem = bal;
      }
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _catalog.close();
    super.dispose();
  }

  void _snack(String text, Color color) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text), backgroundColor: color));
  }

  Future<void> _purchaseItem(Map<String, dynamic> item) async {
    if (item["equipped"] == true || _buyingItemId != null) return;
    final bal = _balance;
    final credits = _credits;
    final identity = _identity;
    if (bal == null || credits == null || identity == null || _nodeProblem != null) {
      _snack("Can't reach your node, so nothing can be bought right now.", Colors.redAccent);
      return;
    }
    final int price = item["price"] as int;
    if (bal.available < price) {
      _snack("Not enough test credits (you have ${bal.available}).", Colors.redAccent);
      return;
    }
    final String? merchantKey = item["merchant_pubkey"] as String?;
    final to = merchantKey ?? kCreditTreasury;

    setState(() => _buyingItemId = item["id"] as String);
    Map<String, dynamic> transfer;
    try {
      transfer = await buildSignedCreditTransfer(
        from: identity.pubkeyHex,
        to: to,
        amount: price,
        kind: 'purchase',
        ref: item["id"] as String,
        memo: 'OmniMarket: ${item["name"]}',
        sign: identity.signBytes,
      );
    } catch (e) {
      if (mounted) setState(() => _buyingItemId = null);
      _snack('Could not sign the purchase: $e', Colors.redAccent);
      return;
    }
    final res = await credits.send(transfer);
    if (!mounted) return;
    setState(() => _buyingItemId = null);

    if (!res.ok) {
      if (res.hubProblem) {
        setState(() {
          _nodeProblem = res;
          _balance = null;
        });
        _snack(
            res.state == CreditsState.unreachable
                ? "Purchase not confirmed: can't reach your node. If it went through, it will show "
                    "in Test credits history once your node is back."
                : "Purchase not confirmed: ${_problemTitle(res)}.",
            Colors.redAccent);
      } else {
        _snack('Your node refused the purchase: ${res.message ?? 'HTTP ${res.statusCode}'}', Colors.redAccent);
        await _refreshFromNode();
      }
      return;
    }

    final receipt = res.value!;
    await _catalog.markEquipped(item["id"] as String);
    await _catalog.recordPurchase(
        eventId: receipt.eventId, itemId: item["id"] as String, price: price, buyerPubkey: identity.pubkeyHex, to: to);
    if (!mounted) return;
    setState(() => item["equipped"] = true);
    await _refreshFromNode();
    if (!mounted) return;

    final fee = receipt.fee ?? 0;
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1E1E2C),
        title: const Row(
          children: [
            Icon(Icons.check_circle_outline, color: Colors.greenAccent),
            SizedBox(width: 8),
            Expanded(
              child: Text("Test purchase recorded by your node", style: TextStyle(color: Colors.white, fontSize: 16)),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Item: ${item['name']}", style: const TextStyle(color: Colors.white70)),
            const SizedBox(height: 6),
            Text("Price: $price test credits (no real money)",
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            const Divider(color: Colors.white24, height: 20),
            if (merchantKey == null)
              const Text("Paid to the hub treasury: demo items have no merchant key yet.",
                  style: TextStyle(color: Colors.cyanAccent, fontSize: 13))
            else ...[
              Text("• Merchant gets: ${price - fee} test credits",
                  style: const TextStyle(color: Colors.greenAccent, fontSize: 13)),
              Text("• Platform fee: $fee test credits",
                  style: const TextStyle(color: Colors.cyanAccent, fontSize: 13)),
            ],
            if (receipt.balance != null) ...[
              const SizedBox(height: 6),
              Text("Your balance: ${receipt.balance} test credits",
                  style: const TextStyle(color: Colors.white70, fontSize: 13)),
            ],
            const SizedBox(height: 8),
            Text("Ledger entry: ${_short(receipt.eventId, 18)}",
                style: const TextStyle(color: Colors.white38, fontSize: 10, fontFamily: 'monospace')),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Equip to Avatar", style: TextStyle(color: Colors.cyanAccent)),
          ),
        ],
      ),
    );
  }

  Future<void> _applyMerchantLicense() async {
    await _catalog.setMerchantLicensed(_userPubkey);
    if (!mounted) return;
    setState(() => _isLicensedMerchant = true);
    _snack("Merchant studio turned on (saved on this device).", Colors.greenAccent);
  }

  static String _short(String s, int n) => s.length > n ? '${s.substring(0, n)}…' : s;

  String _problemTitle(CreditsResult<Object?> r) {
    switch (r.state) {
      case CreditsState.unauthorized:
        return 'your node refused this app\'s token';
      case CreditsState.forbidden:
        return 'the hub refused this phone';
      case CreditsState.unsupported:
        return 'your node is too old for test credits';
      case CreditsState.integrity:
        return 'your node\'s credits ledger failed its integrity check';
      default:
        return 'can\'t reach your node';
    }
  }

  String _problemDetail(CreditsResult<Object?> r) {
    final hub = _hub;
    final where = hub == null ? 'your node' : '${hub.address}:${hub.ipcPort}';
    final remote = hub?.isRemote ?? false;
    switch (r.state) {
      case CreditsState.unreachable:
        return remote
            ? 'Nothing answered at $where. Check that the hub is running and Tailscale is on for both devices.'
            : 'Nothing answered at $where. Open Omni Node and check that it is running.';
      case CreditsState.unauthorized:
        return remote
            ? 'The hub refused the token. Copy it again from the hub into Settings > Hub.'
            : 'Omni Node refused this app\'s token. Copy it from Omni Node > Connect apps into Settings > Hub.';
      case CreditsState.forbidden:
        return 'The hub at $where is not serving remote devices (start it with OMNI_HUB_REMOTE=1).';
      case CreditsState.unsupported:
        return 'Update Omni Node: signed test-credit purchases need hub daemon v8.15.0 or newer.';
      case CreditsState.integrity:
        return 'Your node will not show a balance built on a ledger entry that fails verification. '
            '(${r.message ?? 'integrity FAILED'})';
      default:
        return r.message ?? 'Your node answered with an error (HTTP ${r.statusCode}).';
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        backgroundColor: Color(0xFF0F0F1A),
        body: Center(child: CircularProgressIndicator(color: Colors.cyanAccent)),
      );
    }
    if (_loadError != null) {
      return Scaffold(
        backgroundColor: const Color(0xFF0F0F1A),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text("OmniMarket could not start: $_loadError",
                textAlign: TextAlign.center, style: const TextStyle(color: Colors.white70)),
          ),
        ),
      );
    }

    final bal = _balance;
    final offline = _nodeProblem != null || bal == null;
    return Scaffold(
      backgroundColor: const Color(0xFF0F0F1A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF181824),
        elevation: 0,
        title: const Row(
          children: [
            Icon(Icons.shopping_bag_outlined, color: Colors.cyanAccent),
            SizedBox(width: 8),
            Flexible(
              child: Text("OmniMarket Boutique",
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Refresh from your node',
            onPressed: _refreshing ? null : _refreshFromNode,
            icon: _refreshing
                ? const SizedBox(
                    width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.cyanAccent))
                : const Icon(Icons.refresh, color: Colors.white70),
          ),
          Container(
            margin: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              color: (offline ? Colors.red : Colors.cyan).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: (offline ? Colors.redAccent : Colors.cyanAccent).withValues(alpha: 0.4)),
            ),
            child: Row(
              children: [
                Icon(offline ? Icons.cloud_off : Icons.bolt,
                    color: offline ? Colors.redAccent : Colors.amberAccent, size: 16),
                const SizedBox(width: 4),
                Text(
                  offline ? "— test credits" : "${bal?.available} test credits",
                  key: const Key('storefront-balance'),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.cyanAccent,
          labelColor: Colors.cyanAccent,
          unselectedLabelColor: Colors.white54,
          tabs: const [
            Tab(icon: Icon(Icons.dry_cleaning_rounded), text: "Boutique"),
            Tab(icon: Icon(Icons.receipt_long_rounded), text: "Test credits"),
            Tab(icon: Icon(Icons.storefront_rounded), text: "Merchant"),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildAvatarBoutiqueTab(),
          _buildHistoryTab(),
          _buildMerchantStudioTab(),
        ],
      ),
    );
  }

  /// The "Can't reach your node" card shown instead of any balance.
  Widget _buildNodeProblemCard(CreditsResult<Object?> r) {
    return Container(
      key: const Key('storefront-node-problem'),
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.red.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.redAccent.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.cloud_off, color: Colors.redAccent),
              SizedBox(width: 8),
              Text("Can't reach your node",
                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
            ],
          ),
          const SizedBox(height: 6),
          Text(_problemDetail(r), style: const TextStyle(color: Colors.white70, fontSize: 12)),
          const SizedBox(height: 4),
          const Text("Test credits live on your node, so no balance is shown and buying is off until it's back.",
              style: TextStyle(color: Colors.white38, fontSize: 11)),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              onPressed: _refreshing ? null : _refreshFromNode,
              icon: const Icon(Icons.refresh, color: Colors.cyanAccent, size: 18),
              label: const Text("Try again", style: TextStyle(color: Colors.cyanAccent)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAvatarBoutiqueTab() {
    final problem = _nodeProblem;
    final canBuy = problem == null && _balance != null;
    final hub = _hub;
    return CustomScrollView(
      slivers: [
        if (problem != null) SliverToBoxAdapter(child: _buildNodeProblemCard(problem)),
        SliverToBoxAdapter(
          child: Container(
          margin: const EdgeInsets.all(16),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [Colors.purple.shade900.withValues(alpha: 0.5), Colors.blue.shade900.withValues(alpha: 0.5)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.purpleAccent.withValues(alpha: 0.3)),
          ),
          child: Row(
            children: [
              Container(
                width: 60,
                height: 60,
                decoration: BoxDecoration(
                  color: Colors.black38,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.cyanAccent, width: 2),
                ),
                child: const Icon(Icons.person_pin_rounded, color: Colors.cyanAccent, size: 36),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("LPE Live Dressing Room",
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
                    const SizedBox(height: 4),
                    Row(children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                            color: canBuy ? Colors.greenAccent : Colors.redAccent, shape: BoxShape.circle),
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          canBuy
                              ? "Test credits from your node${hub != null && hub.isRemote ? ' (${hub.address})' : ''}"
                              : "Not connected to your node",
                          style: const TextStyle(color: Colors.white60, fontSize: 12),
                        ),
                      ),
                    ]),
                  ],
                ),
              ),
            ],
          ),
        ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          sliver: SliverGrid.builder(
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              childAspectRatio: 0.8,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
            ),
            itemCount: _cosmeticsCatalog.length,
            itemBuilder: (context, index) {
              final item = _cosmeticsCatalog[index];
              final equipped = item["equipped"] == true;
              final buying = _buyingItemId == item["id"];
              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF181824),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: equipped ? Colors.greenAccent : Colors.white10,
                    width: equipped ? 2 : 1,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Container(
                        decoration: BoxDecoration(
                          color: (item["color"] as Color).withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Center(
                          child: Icon(item["icon"] as IconData, color: item["color"] as Color, size: 40),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(item["name"] as String,
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                    Text("Socket: ${item['socket']}", style: const TextStyle(color: Colors.white38, fontSize: 10)),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text("${item['price']} test CR",
                            style: const TextStyle(color: Colors.amberAccent, fontWeight: FontWeight.bold)),
                        ElevatedButton(
                          key: Key('buy-${item["id"]}'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: equipped ? Colors.green.withValues(alpha: 0.2) : Colors.cyan,
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          ),
                          onPressed: equipped || !canBuy || _buyingItemId != null ? null : () => _purchaseItem(item),
                          child: Text(
                            equipped ? "Equipped" : (buying ? "…" : "Buy"),
                            style: TextStyle(
                              color: equipped ? Colors.greenAccent : Colors.black,
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildHistoryTab() {
    final problem = _nodeProblem;
    final hist = _history;
    final children = <Widget>[];
    if (problem != null) {
      children.add(_buildNodeProblemCard(problem));
    } else if (hist == null) {
      children.add(const Padding(
        padding: EdgeInsets.all(32),
        child: Center(child: CircularProgressIndicator(color: Colors.cyanAccent)),
      ));
    } else if (hist.entries.isEmpty) {
      children.add(const Padding(
        padding: EdgeInsets.all(32),
        child: Center(child: Text("No test-credit activity yet.", style: TextStyle(color: Colors.white54))),
      ));
    } else {
      children.add(const Padding(
        padding: EdgeInsets.fromLTRB(16, 16, 16, 4),
        child: Text("From your node's ledger, newest first. Test credits: no cash value.",
            style: TextStyle(color: Colors.white38, fontSize: 11)),
      ));
      for (final e in hist.entries) {
        children.add(_historyTile(e));
      }
      if (hist.hasMore) {
        children.add(const Padding(
          padding: EdgeInsets.all(12),
          child: Center(child: Text("Older entries not shown.", style: TextStyle(color: Colors.white38, fontSize: 11))),
        ));
      }
    }
    return RefreshIndicator(
      onRefresh: _refreshFromNode,
      child: ListView(physics: const AlwaysScrollableScrollPhysics(), children: children),
    );
  }

  Widget _historyTile(CreditEntry e) {
    final incoming = e.delta >= 0;
    final title = e.memo.isNotEmpty ? e.memo : e.kind;
    final t = e.time.toLocal();
    final when = '${t.year}-${_two(t.month)}-${_two(t.day)} ${_two(t.hour)}:${_two(t.minute)}';
    final who = incoming
        ? (e.from == kCreditTreasury ? 'from treasury' : 'from ${_short(e.from, 8)}')
        : (e.to == kCreditTreasury ? 'to treasury' : 'to ${_short(e.to, 8)}');
    return ListTile(
      dense: true,
      leading: Icon(incoming ? Icons.south_west_rounded : Icons.north_east_rounded,
          color: incoming ? Colors.greenAccent : Colors.orangeAccent),
      title: Text(title, style: const TextStyle(color: Colors.white, fontSize: 13)),
      subtitle: Text(
        '${e.kind} • $who • $when${e.fee > 0 && incoming ? ' • fee ${e.fee}' : ''}',
        style: const TextStyle(color: Colors.white38, fontSize: 11),
      ),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text('${incoming ? '+' : ''}${e.delta}',
              style: TextStyle(
                  color: incoming ? Colors.greenAccent : Colors.orangeAccent, fontWeight: FontWeight.bold)),
          Text('${e.balanceAfter}', style: const TextStyle(color: Colors.white38, fontSize: 10)),
        ],
      ),
      onLongPress: () {
        Clipboard.setData(ClipboardData(text: e.eventId));
        _snack('Ledger entry id copied.', Colors.cyan);
      },
    );
  }

  static String _two(int n) => n.toString().padLeft(2, '0');

  Widget _buildMerchantStudioTab() {
    if (!_isLicensedMerchant) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.storefront_rounded, color: Colors.cyanAccent, size: 70),
              const SizedBox(height: 16),
              const Text(
                "Open Your Avatar Boutique",
                style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text(
                "Preview the merchant studio. Publishing items to other people isn't built yet; "
                "this switch is saved on this device only.",
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white60, fontSize: 13),
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.cyanAccent,
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                ),
                onPressed: _applyMerchantLicense,
                icon: const Icon(Icons.verified_sharp, color: Colors.black),
                label: const Text("Turn on merchant studio",
                    style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF181824),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.cyanAccent.withValues(alpha: 0.3)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                const Column(
                  children: [
                    Text("Merchant studio", style: TextStyle(color: Colors.white54, fontSize: 12)),
                    SizedBox(height: 4),
                    Text("ON (this device)",
                        style: TextStyle(color: Colors.greenAccent, fontWeight: FontWeight.bold, fontSize: 16)),
                  ],
                ),
                Column(
                  children: [
                    const Text("Your key (receives sales)", style: TextStyle(color: Colors.white54, fontSize: 12)),
                    const SizedBox(height: 4),
                    GestureDetector(
                      onTap: () {
                        Clipboard.setData(ClipboardData(text: _userPubkey));
                        _snack('Public key copied.', Colors.cyan);
                      },
                      child: Text(
                        _short(_userPubkey, 10),
                        style: const TextStyle(
                            color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14, fontFamily: 'monospace'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Device-local storefront state: the catalog, equipped flags, the merchant
/// switch and purchase receipts. Never a credit balance.
abstract class StorefrontCatalogStore {
  Future<void> open();

  /// Catalog items as maps: id, name, socket, price, merchant, merchant_pubkey
  /// (null = pays the hub treasury), equipped, icon, color.
  Future<List<Map<String, dynamic>>> items();
  Future<void> markEquipped(String itemId);
  Future<bool> merchantLicensed(String pubkey);
  Future<void> setMerchantLicensed(String pubkey);
  Future<void> recordPurchase(
      {required String eventId, required String itemId, required int price, required String buyerPubkey, required String to});
  Future<void> close();
}

const List<Map<String, Object>> kDefaultStorefrontItems = [
  {"item_id": "item_01", "name": "Cyber Visor", "socket": "head_socket", "price": 100, "merchant_handle": "@P2PMerchant"},
  {"item_id": "item_02", "name": "Plasma Wings", "socket": "torso_bone", "price": 250, "merchant_handle": "@P2PMerchant"},
];

Map<String, dynamic> _itemView(Map<String, Object?> i) => {
      "id": i["item_id"],
      "name": i["name"],
      "socket": i["socket"],
      "price": i["price"],
      "merchant": i["merchant_handle"],
      // Demo items have no merchant key, so purchases pay the hub treasury.
      "merchant_pubkey": null,
      "equipped": i["equipped"] == 1 || i["equipped"] == true,
      "icon": Icons.style_outlined,
      "color": Colors.cyanAccent,
    };

/// The storefront's existing SQLite file (omni_hub_immutable.db). Same schema
/// as earlier builds; `citizen_identity.credits` is left in place for old
/// installs but never read or written (balances live on the node).
class SqliteStorefrontCatalog implements StorefrontCatalogStore {
  Database? _db;

  @override
  Future<void> open() async {
    final dbPath = p.join(await getDatabasesPath(), 'omni_hub_immutable.db');
    _db = await openDatabase(
      dbPath,
      version: 1,
      onCreate: (Database db, int version) async {
        await db.execute('''
          CREATE TABLE IF NOT EXISTS citizen_identity (
            pubkey TEXT PRIMARY KEY,
            handle TEXT,
            credits INTEGER,
            merchant_licensed INTEGER
          )
        ''');
        await db.execute('''
          CREATE TABLE IF NOT EXISTS event_log (
            event_id TEXT PRIMARY KEY,
            event_type TEXT,
            timestamp_ns INTEGER,
            payload_json TEXT
          )
        ''');
        await db.execute('''
          CREATE TABLE IF NOT EXISTS store_catalog (
            item_id TEXT PRIMARY KEY,
            name TEXT,
            socket TEXT,
            price INTEGER,
            merchant_handle TEXT,
            equipped INTEGER
          )
        ''');
      },
    );
  }

  @override
  Future<List<Map<String, dynamic>>> items() async {
    var rows = await _db!.query('store_catalog');
    if (rows.isEmpty) {
      for (final item in kDefaultStorefrontItems) {
        await _db!.insert('store_catalog', {...item, "equipped": 0});
      }
      rows = await _db!.query('store_catalog');
    }
    return rows.map(_itemView).toList();
  }

  @override
  Future<void> markEquipped(String itemId) async {
    await _db!.update('store_catalog', {'equipped': 1}, where: 'item_id = ?', whereArgs: [itemId]);
  }

  @override
  Future<bool> merchantLicensed(String pubkey) async {
    final rows = await _db!.query('citizen_identity', where: 'pubkey = ?', whereArgs: [pubkey], limit: 1);
    return rows.isNotEmpty && rows.first['merchant_licensed'] == 1;
  }

  @override
  Future<void> setMerchantLicensed(String pubkey) async {
    await _db!.insert('citizen_identity', {'pubkey': pubkey, 'handle': '@citizen', 'merchant_licensed': 1},
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  @override
  Future<void> recordPurchase(
      {required String eventId,
      required String itemId,
      required int price,
      required String buyerPubkey,
      required String to}) async {
    // A local receipt only; the hub's ledger entry (eventId) is the record.
    await _db!.insert(
        'event_log',
        {
          'event_id': eventId,
          'event_type': 'ITEM_PURCHASED',
          'timestamp_ns': DateTime.now().microsecondsSinceEpoch * 1000,
          'payload_json': '{"item_id":"$itemId","price":$price,"buyer_pubkey":"$buyerPubkey","to":"$to"}',
        },
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  @override
  Future<void> close() async {
    await _db?.close();
  }
}

/// In-memory store (tests, or a device without SQLite).
class MemoryStorefrontCatalog implements StorefrontCatalogStore {
  final List<Map<String, dynamic>> _items = [
    for (final i in kDefaultStorefrontItems) _itemView({...i, "equipped": 0})
  ];
  final Set<String> _licensed = {};
  final List<Map<String, Object>> receipts = [];

  @override
  Future<void> open() async {}
  @override
  Future<List<Map<String, dynamic>>> items() async => _items;
  @override
  Future<void> markEquipped(String itemId) async {
    for (final i in _items) {
      if (i["id"] == itemId) i["equipped"] = true;
    }
  }

  @override
  Future<bool> merchantLicensed(String pubkey) async => _licensed.contains(pubkey);
  @override
  Future<void> setMerchantLicensed(String pubkey) async => _licensed.add(pubkey);
  @override
  Future<void> recordPurchase(
      {required String eventId,
      required String itemId,
      required int price,
      required String buyerPubkey,
      required String to}) async {
    receipts.add({'event_id': eventId, 'item_id': itemId, 'price': price, 'to': to});
  }

  @override
  Future<void> close() async {}
}
