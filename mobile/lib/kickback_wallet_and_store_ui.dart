import 'package:flutter/material.dart';

/// ============================================================================
/// THE KICKBACK - EXPANDED 100-GIFT CATALOG, LIVE NOTIFICATIONS & WALLET UI
/// Repository: kiroba/The-KickBack
/// Features:
///   1. Wallet Earnings Dashboard ($10 min cashout, 500-fan milestone, P2P history)
///   2. OmniCredit Store (Preload bundles $5-$100 with 5%-25% bonus credits)
///   3. Expanded 100-Gift Catalog Modal ($1 - $100 Universal & Role Exclusives)
///   4. Live Gift Overlay Notification Banner Component
/// ============================================================================

class KickBackWalletAndStoreScreen extends StatefulWidget {
  final String currentRoleTier; // 'COMMON', 'CREATOR', 'INFLUENCER', 'EDUCATOR'
  final double usdBalance;
  final int omniCreditBalance;
  final int verifiedFanCount;
  final List<Map<String, dynamic>> giftTransactions;
  final Map<String, dynamic>? activeLiveNotification;

  const KickBackWalletAndStoreScreen({
    Key? key,
    this.currentRoleTier = 'COMMON',
    this.usdBalance = 7.50,
    this.omniCreditBalance = 1200,
    this.verifiedFanCount = 342,
    this.giftTransactions = const [],
    this.activeLiveNotification,
  }) : super(key: key);

  @override
  State<KickBackWalletAndStoreScreen> createState() => _KickBackWalletAndStoreScreenState();
}

class _KickBackWalletAndStoreScreenState extends State<KickBackWalletAndStoreScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  Map<String, dynamic>? _liveNotification;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _liveNotification = widget.activeLiveNotification;
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A), // Slate 900
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        title: Row(
          children: [
            const Icon(Icons.account_balance_wallet_outlined, color: Color(0xFF38BDF8)),
            const SizedBox(width: 10),
            const Text(
              'KickBack Treasury & Wallet',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: Colors.white),
            ),
          ],
        ),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: const Color(0xFF38BDF8),
          labelColor: const Color(0xFF38BDF8),
          unselectedLabelColor: const Color(0xFF94A3B8),
          tabs: const [
            Tab(icon: Icon(Icons.dashboard_outlined), text: 'Earnings'),
            Tab(icon: Icon(Icons.storefront_outlined), text: 'Credit Store'),
            Tab(icon: Icon(Icons.card_giftcard), text: '100-Gift Catalog'),
          ],
        ),
      ),
      body: Stack(
        children: [
          TabBarView(
            controller: _tabController,
            children: [
              _WalletEarningsTab(
                roleTier: widget.currentRoleTier,
                usdBalance: widget.usdBalance,
                omniCreditBalance: widget.omniCreditBalance,
                verifiedFanCount: widget.verifiedFanCount,
                transactions: widget.giftTransactions,
                onOpenGiftModal: () => _showGiftCatalogModal(context),
              ),
              _OmniCreditStoreTab(
                currentCredits: widget.omniCreditBalance,
              ),
              _Expanded100GiftCatalogGridTab(
                userRoleTier: widget.currentRoleTier,
                currentCredits: widget.omniCreditBalance,
              ),
            ],
          ),

          // Live Gift Notification Overlay Banner
          if (_liveNotification != null)
            Positioned(
              top: 12,
              left: 16,
              right: 16,
              child: LiveGiftNotificationBanner(
                notificationData: _liveNotification!,
                onDismiss: () => setState(() => _liveNotification = null),
              ),
            ),
        ],
      ),
    );
  }

  void _showGiftCatalogModal(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.85,
        maxChildSize: 0.95,
        minChildSize: 0.5,
        builder: (_, scrollController) => Container(
          decoration: const BoxDecoration(
            color: Color(0xFF1E293B),
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Container(
                width: 40,
                height: 4,
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  color: Colors.grey.shade600,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Send OmniGifts ($1 - $100)',
                    style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0284C7).withOpacity(0.2),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '${widget.omniCreditBalance} Credits',
                      style: const TextStyle(color: Color(0xFF38BDF8), fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Expanded(
                child: _Expanded100GiftCatalogGridTab(
                  userRoleTier: widget.currentRoleTier,
                  currentCredits: widget.omniCreditBalance,
                  scrollController: scrollController,
                  onGiftSent: (giftName, priceUsd) {
                    Navigator.pop(ctx);
                    setState(() {
                      _liveNotification = {
                        "sender_username": "You",
                        "sender_tier": widget.currentRoleTier,
                        "recipient_username": "Featured_Creator",
                        "gift_name": giftName,
                        "gross_usd": priceUsd,
                        "visual_effects": {
                          "overlay_animation": priceUsd >= 50.0 ? "3D_GALACTIC_SUPERNOVA" : "CELEBRATION_SPARKLES",
                          "sound_effect": "ROYAL_CHIME_FANFARE"
                        }
                      };
                    });
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ============================================================================
// LIVE GIFT NOTIFICATION BANNER OVERLAY WIDGET
// ============================================================================
class LiveGiftNotificationBanner extends StatelessWidget {
  final Map<String, dynamic> notificationData;
  final VoidCallback onDismiss;

  const LiveGiftNotificationBanner({
    Key? key,
    required this.notificationData,
    required this.onDismiss,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final String sender = notificationData['sender_username'] ?? 'Anonymous';
    final String recipient = notificationData['recipient_username'] ?? 'Creator';
    final String giftName = notificationData['gift_name'] ?? 'Gift';
    final double grossUsd = (notificationData['gross_usd'] as num?)?.toDouble() ?? 1.0;
    final Map<String, dynamic> effects = notificationData['visual_effects'] ?? {};
    final String animation = effects['overlay_animation'] ?? 'SPARKLE_BURST';

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: grossUsd >= 50.0
              ? [const Color(0xFF7C3AED), const Color(0xFFC026D3)]
              : [const Color(0xFF0284C7), const Color(0xFF0F172A)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.5),
            blurRadius: 10,
            offset: const Offset(0, 4),
          )
        ],
        border: Border.all(color: Colors.amber, width: 1.5),
      ),
      child: Row(
        children: [
          const CircleAvatar(
            backgroundColor: Colors.amber,
            child: Icon(Icons.card_giftcard, color: Colors.black),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    const Icon(Icons.stars, color: Colors.amber, size: 14),
                    const SizedBox(width: 4),
                    Text(
                      'LIVE GIFT: $giftName (\$${grossUsd.toStringAsFixed(2)})',
                      style: const TextStyle(color: Colors.amber, fontSize: 11, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                RichText(
                  text: TextSpan(
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                    children: [
                      TextSpan(text: sender, style: const TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF38BDF8))),
                      const TextSpan(text: ' sent '),
                      TextSpan(text: giftName, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.amber)),
                      const TextSpan(text: ' to '),
                      TextSpan(text: recipient, style: const TextStyle(fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
                Text(
                  'Effect: $animation | 98% Net Routed to Creator',
                  style: TextStyle(color: Colors.white.withOpacity(0.7), fontSize: 9),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close, color: Colors.white70, size: 18),
            onPressed: onDismiss,
          )
        ],
      ),
    );
  }
}

// ============================================================================
// TAB 1: WALLET EARNINGS & MILESTONE DASHBOARD
// ============================================================================
class _WalletEarningsTab extends StatelessWidget {
  final String roleTier;
  final double usdBalance;
  final int omniCreditBalance;
  final int verifiedFanCount;
  final List<Map<String, dynamic>> transactions;
  final VoidCallback onOpenGiftModal;

  const _WalletEarningsTab({
    Key? key,
    required this.roleTier,
    required this.usdBalance,
    required this.omniCreditBalance,
    required this.verifiedFanCount,
    required this.transactions,
    required this.onOpenGiftModal,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final bool isCommon = roleTier.toUpperCase() == 'COMMON';
    final double minCashout = 10.00;
    final int minFans = 500;
    final bool canCashout = !isCommon || usdBalance >= minCashout;
    final bool autoPayoutActive = verifiedFanCount >= minFans;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Balance Overview Header Card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF1E293B), Color(0xFF0F172A)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF334155), width: 1.5),
            ),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Available Earnings', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13)),
                        const SizedBox(height: 4),
                        Text('\$${usdBalance.toStringAsFixed(2)} USD',
                            style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.bold)),
                      ],
                    ),
                    _RoleBadge(roleTier: roleTier),
                  ],
                ),
                const Divider(color: Color(0xFF334155), height: 24),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.monetization_on, color: Colors.amber, size: 20),
                        const SizedBox(width: 6),
                        Text('$omniCreditBalance OmniCredits', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
                      ],
                    ),
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF0284C7),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      onPressed: onOpenGiftModal,
                      icon: const Icon(Icons.card_giftcard, size: 16),
                      label: const Text('Send Gift'),
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 20),

          // Common User Progress Cards or Paid Tier Instant Status
          if (isCommon) ...[
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Minimum Cashout Floor ($10.00)',
                          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                      Text(
                        '\$${usdBalance.toStringAsFixed(2)} / \$10.00',
                        style: TextStyle(
                            color: usdBalance >= 10.00 ? Colors.greenAccent : const Color(0xFF38BDF8),
                            fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: (usdBalance / minCashout).clamp(0.0, 1.0),
                      backgroundColor: const Color(0xFF0F172A),
                      valueColor: AlwaysStoppedAnimation<Color>(
                        usdBalance >= 10.00 ? Colors.greenAccent : const Color(0xFF0284C7),
                      ),
                      minHeight: 8,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    usdBalance >= 10.00
                        ? '✓ Minimum threshold met! You can request a manual payout below.'
                        : 'Earn \$${(minCashout - usdBalance).toStringAsFixed(2)} more to unlock manual cash-outs.',
                    style: TextStyle(color: Colors.grey.shade400, fontSize: 11),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 12),

            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: autoPayoutActive ? Colors.green.shade700 : const Color(0xFF334155),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: const [
                          Icon(Icons.people_alt_outlined, color: Color(0xFF38BDF8), size: 18),
                          SizedBox(width: 6),
                          Text('500-Fan Auto-Payout Milestone',
                              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                        ],
                      ),
                      Text(
                        '$verifiedFanCount / $minFans Fans',
                        style: TextStyle(
                          color: autoPayoutActive ? Colors.greenAccent : Colors.orangeAccent,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: (verifiedFanCount / minFans).clamp(0.0, 1.0),
                      backgroundColor: const Color(0xFF0F172A),
                      valueColor: AlwaysStoppedAnimation<Color>(
                        autoPayoutActive ? Colors.greenAccent : Colors.orangeAccent,
                      ),
                      minHeight: 8,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    autoPayoutActive
                        ? '🎉 Milestone Achieved! Automatic weekly payouts enabled on Cash App/PayPal.'
                        : 'Reach 500 verified fans to unlock zero-touch automated weekly payouts.',
                    style: TextStyle(color: Colors.grey.shade400, fontSize: 11),
                  ),
                ],
              ),
            ),
          ] else ...[
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF0284C7).withOpacity(0.15),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF0284C7)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.flash_on, color: Colors.amber, size: 28),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('$roleTier Tier Privilege: 24/7 Instant Payouts',
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 2),
                        const Text('No minimum floor or fan requirements. Withdraw directly to Cash App, Venmo, or PayPal.',
                            style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],

          const SizedBox(height: 20),

          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: canCashout ? Colors.green.shade600 : Colors.grey.shade800,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              onPressed: canCashout ? () => _handleCashoutRequest(context) : null,
              icon: const Icon(Icons.account_balance, color: Colors.white),
              label: Text(
                canCashout ? 'Request Instant Payout (\$${usdBalance.toStringAsFixed(2)})' : 'Cash-out Locked (Min \$10.00 Required)',
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
              ),
            ),
          ),

          const SizedBox(height: 24),

          const Text('Recent Gift & Payout Transactions',
              style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),

          _TransactionList(transactions: transactions),
        ],
      ),
    );
  }

  void _handleCashoutRequest(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Select Payout Rail', style: TextStyle(color: Colors.white)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.attach_money, color: Colors.green),
              title: const Text('Cash App ($cashtag)', style: TextStyle(color: Colors.white)),
              subtitle: const Text('Instant 0-fee transfer', style: TextStyle(color: Colors.grey, fontSize: 11)),
              onTap: () => Navigator.pop(ctx),
            ),
            ListTile(
              leading: const Icon(Icons.payment, color: Colors.blue),
              title: const Text('Venmo / PayPal', style: TextStyle(color: Colors.white)),
              subtitle: const Text('Direct handle payout', style: TextStyle(color: Colors.grey, fontSize: 11)),
              onTap: () => Navigator.pop(ctx),
            ),
            ListTile(
              leading: const Icon(Icons.bolt, color: Colors.amber),
              title: const Text('Lightning Network', style: TextStyle(color: Colors.white)),
              subtitle: const Text('Atomic LNURL payout', style: TextStyle(color: Colors.grey, fontSize: 11)),
              onTap: () => Navigator.pop(ctx),
            ),
          ],
        ),
      ),
    );
  }
}

// ============================================================================
// TAB 2: OMNICREDIT IN-APP PRELOAD STORE BUNDLES
// ============================================================================
class _OmniCreditStoreTab extends StatelessWidget {
  final int currentCredits;

  const _OmniCreditStoreTab({Key? key, required this.currentCredits}) : super(key: key);

  static const List<Map<String, dynamic>> bundles = [
    {"usd": 5.0, "credits": 500, "bonus": 25, "percent": "5% Bonus", "badge": "STARTER"},
    {"usd": 10.0, "credits": 1000, "bonus": 100, "percent": "10% Bonus", "badge": "POPULAR"},
    {"usd": 25.0, "credits": 2500, "bonus": 375, "percent": "15% Bonus", "badge": "VALUE"},
    {"usd": 50.0, "credits": 5000, "bonus": 1000, "percent": "20% Bonus", "badge": "PRO"},
    {"usd": 100.0, "credits": 10000, "bonus": 2500, "percent": "25% Bonus", "badge": "VIP WHALE"},
  ];

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF0284C7)),
          ),
          child: Row(
            children: [
              const Icon(Icons.account_balance_wallet, color: Colors.amber, size: 32),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Preload Profile with OmniCredits',
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
                  const SizedBox(height: 2),
                  Text('Current Balance: $currentCredits Credits (Extensible across Omniverse Apps)',
                      style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        ...bundles.map((b) => _buildBundleCard(context, b)).toList(),
      ],
    );
  }

  Widget _buildBundleCard(BuildContext context, Map<String, dynamic> b) {
    final int totalCredits = (b['credits'] as int) + (b['bonus'] as int);
    return Card(
      color: const Color(0xFF1E293B),
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFF334155)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: const Color(0xFF0284C7).withOpacity(0.2),
                  child: const Icon(Icons.monetization_on, color: Colors.amber),
                ),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text('$totalCredits Credits',
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.green.shade800,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(b['percent'], style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.bold)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 2),
                    Text('${b['credits']} Base + ${b['bonus']} Bonus Credits',
                        style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                  ],
                ),
              ],
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0284C7)),
              onPressed: () => _handlePurchaseBundle(context, b),
              child: Text('\$${(b['usd'] as double).toStringAsFixed(2)}'),
            )
          ],
        ),
      ),
    );
  }

  void _handlePurchaseBundle(BuildContext context, Map<String, dynamic> b) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Processing Cash App / Fiat Preload for \$${b['usd']} (${b['credits'] + b['bonus']} Credits)...')),
    );
  }
}

// ============================================================================
// TAB 3: EXPANDED 100-GIFT CATALOG GRID TAB ($1 - $100)
// ============================================================================
class _Expanded100GiftCatalogGridTab extends StatefulWidget {
  final String userRoleTier;
  final int currentCredits;
  final ScrollController? scrollController;
  final Function(String giftName, double priceUsd)? onGiftSent;

  const _Expanded100GiftCatalogGridTab({
    Key? key,
    required this.userRoleTier,
    required this.currentCredits,
    this.scrollController,
    this.onGiftSent,
  }) : super(key: key);

  @override
  State<_Expanded100GiftCatalogGridTab> createState() => _Expanded100GiftCatalogGridTabState();
}

class _Expanded100GiftCatalogGridTabState extends State<_Expanded100GiftCatalogGridTab> {
  String _selectedCategory = 'ALL'; // ALL (Universal), CREATOR, INFLUENCER, EDUCATOR

  // Generate catalog of gifts ($1 to $100)
  List<Map<String, dynamic>> _getFilteredGifts() {
    final List<Map<String, dynamic>> allGifts = [];

    // 70 Universal Gifts ($1 to $100) - accessible to ALL senders
    for (int i = 1; i <= 70; i++) {
      double price = (i <= 50) ? i.toDouble() : 50.0 + (i - 50) * 2.5;
      allGifts.add({
        "name": "Universal Gift #$i",
        "usd": price,
        "credits": (price * 100).toInt(),
        "tier": "COMMON",
        "category": "UNIVERSAL",
        "icon": Icons.card_giftcard
      });
    }

    // 10 Creator Exclusives ($1 to $100)
    final creatorPrices = [2.0, 5.0, 12.0, 20.0, 35.0, 50.0, 65.0, 80.0, 90.0, 100.0];
    final creatorNames = ["Creator Mic", "Studio Light", "Gold Play Button", "Director Chair", "4K Camera", "Pro Synth", "Vinyl Master", "Hologram Stage", "Producer Desk", "Masterpiece"];
    for (int i = 0; i < 10; i++) {
      allGifts.add({
        "name": creatorNames[i],
        "usd": creatorPrices[i],
        "credits": (creatorPrices[i] * 100).toInt(),
        "tier": "CREATOR",
        "category": "CREATOR",
        "icon": Icons.mic
      });
    }

    // 10 Influencer Exclusives ($1 to $100)
    final infPrices = [3.0, 8.0, 15.0, 25.0, 40.0, 55.0, 70.0, 85.0, 95.0, 100.0];
    final infNames = ["VIP Pass", "Red Carpet", "Neon Spotlight", "Cyber Supercar", "Hollywood Star", "Golden Throne", "Fashion Runway", "Yacht Party", "Private Jet", "Met Gala Crown"];
    for (int i = 0; i < 10; i++) {
      allGifts.add({
        "name": infNames[i],
        "usd": infPrices[i],
        "credits": (infPrices[i] * 100).toInt(),
        "tier": "INFLUENCER",
        "category": "INFLUENCER",
        "icon": Icons.star
      });
    }

    // 10 Educator Exclusives ($1 to $100)
    final eduPrices = [1.5, 6.0, 10.0, 18.0, 30.0, 45.0, 60.0, 75.0, 88.0, 100.0];
    final eduNames = ["Wisdom Scroll", "Graduation Cap", "Honor Quill", "Academy Podium", "Library Key", "Research Telescope", "Scholar Globe", "Encyclopedia", "Observatory", "Galaxy Castle"];
    for (int i = 0; i < 10; i++) {
      allGifts.add({
        "name": eduNames[i],
        "usd": eduPrices[i],
        "credits": (eduPrices[i] * 100).toInt(),
        "tier": "EDUCATOR",
        "category": "EDUCATOR",
        "icon": Icons.school
      });
    }

    if (_selectedCategory == 'ALL') {
      return allGifts;
    }
    return allGifts.where((g) => g['category'] == _selectedCategory).toList();
  }

  bool _isGiftUnlocked(String requiredTier) {
    if (requiredTier.toUpperCase() == 'COMMON') return true; // Universal gifts unlocked for ALL senders
    final Map<String, int> ranks = {'COMMON': 1, 'CREATOR': 2, 'INFLUENCER': 3, 'EDUCATOR': 4};
    final int userRank = ranks[widget.userRoleTier.toUpperCase()] ?? 1;
    final int reqRank = ranks[requiredTier.toUpperCase()] ?? 1;
    return userRank >= reqRank;
  }

  @override
  Widget build(BuildContext context) {
    final filteredGifts = _getFilteredGifts();

    return Column(
      children: [
        // Category Selector Chips
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
          child: Row(
            children: [
              _buildCategoryChip('ALL', 'Universal (70 Gifts $1-$100)'),
              _buildCategoryChip('CREATOR', 'Creator Exclusives (10)'),
              _buildCategoryChip('INFLUENCER', 'Influencer Exclusives (10)'),
              _buildCategoryChip('EDUCATOR', 'Educator Exclusives (10)'),
            ],
          ),
        ),
        const SizedBox(height: 6),
        Expanded(
          child: GridView.builder(
            controller: widget.scrollController,
            padding: const EdgeInsets.all(12),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              childAspectRatio: 0.85,
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
            ),
            itemCount: filteredGifts.length,
            itemBuilder: (context, index) {
              final g = filteredGifts[index];
              final bool isUnlocked = _isGiftUnlocked(g['tier']);
              final bool canAfford = widget.currentCredits >= (g['credits'] as int);

              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isUnlocked ? const Color(0xFF334155) : Colors.red.shade900.withOpacity(0.5),
                  ),
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        _RoleBadge(roleTier: g['tier']),
                        if (!isUnlocked)
                          const Icon(Icons.lock, color: Colors.redAccent, size: 16),
                      ],
                    ),
                    Icon(
                      g['icon'] as IconData,
                      size: 32,
                      color: isUnlocked ? const Color(0xFF38BDF8) : Colors.grey,
                    ),
                    Text(
                      g['name'],
                      textAlign: TextAlign.center,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: isUnlocked ? Colors.white : Colors.grey,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                    Text(
                      '${g['credits']} Credits (\$${(g['usd'] as double).toStringAsFixed(2)})',
                      style: const TextStyle(color: Colors.amber, fontSize: 10, fontWeight: FontWeight.w600),
                    ),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: isUnlocked && canAfford ? const Color(0xFF0284C7) : Colors.grey.shade800,
                        minimumSize: const Size(double.infinity, 28),
                        padding: EdgeInsets.zero,
                      ),
                      onPressed: isUnlocked && canAfford
                          ? () => _sendGift(context, g)
                          : () => _explainLock(context, g, isUnlocked),
                      child: Text(
                        !isUnlocked ? 'Requires ${g['tier']}' : (canAfford ? 'Send Gift' : 'Need Credits'),
                        style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold),
                      ),
                    )
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildCategoryChip(String categoryKey, String label) {
    final bool isSelected = _selectedCategory == categoryKey;
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: FilterChip(
        selected: isSelected,
        label: Text(label, style: TextStyle(color: isSelected ? Colors.white : const Color(0xFF94A3B8), fontSize: 11)),
        selectedColor: const Color(0xFF0284C7),
        backgroundColor: const Color(0xFF1E293B),
        onSelected: (_) => setState(() => _selectedCategory = categoryKey),
      ),
    );
  }

  void _sendGift(BuildContext context, Map<String, dynamic> g) {
    final double price = g['usd'] as double;
    final String name = g['name'] as String;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Sent $name (\$${price.toStringAsFixed(2)})! Live broadcast sent to stream overlay.')),
    );
    if (widget.onGiftSent != null) {
      widget.onGiftSent!(name, price);
    }
  }

  void _explainLock(BuildContext context, Map<String, dynamic> g, bool isUnlocked) {
    final String msg = !isUnlocked
        ? 'Gift "${g['name']}" is exclusive to ${g['tier']} tier.'
        : 'Insufficient OmniCredits balance. Preload credits in Store.';
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg), backgroundColor: Colors.red));
  }
}

class _RoleBadge extends StatelessWidget {
  final String roleTier;
  const _RoleBadge({required this.roleTier});

  @override
  Widget build(BuildContext context) {
    Color color;
    switch (roleTier.toUpperCase()) {
      case 'CREATOR':
        color = Colors.purple;
        break;
      case 'INFLUENCER':
        color = Colors.orange;
        break;
      case 'EDUCATOR':
        color = Colors.green;
        break;
      default:
        color = Colors.blueGrey;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.2),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color, width: 0.8),
      ),
      child: Text(
        roleTier.toUpperCase(),
        style: TextStyle(color: color, fontSize: 9, fontWeight: FontWeight.bold),
      ),
    );
  }
}

class _TransactionList extends StatelessWidget {
  final List<Map<String, dynamic>> transactions;

  const _TransactionList({Key? key, required this.transactions}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    if (transactions.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(10),
        ),
        child: const Center(
          child: Text('No recent gift or payout transactions logged.', style: TextStyle(color: Colors.grey, fontSize: 12)),
        ),
      );
    }

    return Column(
      children: transactions.map((tx) {
        return Card(
          color: const Color(0xFF1E293B),
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            leading: const Icon(Icons.card_giftcard, color: Color(0xFF38BDF8)),
            title: Text(tx['title'] ?? 'Gift Received', style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
            subtitle: Text(tx['subtitle'] ?? 'Net payout after 2% fee', style: const TextStyle(color: Colors.grey, fontSize: 11)),
            trailing: Text(
              tx['amount'] ?? '+$0.00',
              style: const TextStyle(color: Colors.greenAccent, fontWeight: FontWeight.bold),
            ),
          ),
        );
      }).toList(),
    );
  }
}
