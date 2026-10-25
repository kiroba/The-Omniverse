
import 'package:flutter/material.dart';

/// KickBack Creator Studio Hub
/// 
/// Unified 4-Tab Creator Suite for The KickBack platform:
/// - Tab 1: Dashboard & Mesh Analytics
/// - Tab 2: Treasury & Monetization
/// - Tab 3: Live & Interactive Studio
/// - Tab 4: Persona & Content Studio
class KickBackCreatorStudioUI extends StatefulWidget {
  final String userId;
  final String userRoleTier; // COMMON, CREATOR, INFLUENCER, EDUCATOR

  const KickBackCreatorStudioUI({
    super.key,
    required this.userId,
    this.userRoleTier = 'CREATOR',
  });

  @override
  State<KickBackCreatorStudioUI> createState() => _KickBackCreatorStudioUIState();
}

class _KickBackCreatorStudioUIState extends State<KickBackCreatorStudioUI>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  // Mock State Data (Connected via Continuity-Engine & OmniLedger)
  final int _omniCreditsBalance = 14850;
  final int _verifiedFansCount = 382;
  final int _verifiedFanTarget = 500;
  final double _platformFeePercent = 2.0; // Fixed 2% Platform Treasury Fee
  
  double get _creatorSplitPercent {
    switch (widget.userRoleTier.toUpperCase()) {
      case 'EDUCATOR':
        return 90.0;
      case 'INFLUENCER':
        return 85.0;
      case 'CREATOR':
        return 82.0;
      case 'COMMON':
      default:
        return 80.0;
    }
  }

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A), // Dark Slate Background
      appBar: AppBar(
        backgroundColor: const Color.fromARGB(255, 57, 37, 128),
        elevation: 2,
        title: Row(
          children: [
            const Icon(Icons.auto_awesome, color: Color(0xFF87EBDC)),
            const SizedBox(width: 8),
            const Text(
              'KickBack Creator Studio',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 18,
              ),
            ),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: const Color.fromARGB(255, 86, 202, 184),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color.fromARGB(255, 57, 37, 128), width: 1.5)
              ),
              child: Text(
                widget.userRoleTier,
                style: const TextStyle(
                  color: Color.fromARGB(255, 57, 37, 128),
                  fontWeight: FontWeight.bold,
                  fontSize: 11,
                ),
              ),
            ),
          ],
        ),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: const Color.fromARGB(255, 93, 128, 37),
          labelColor: const Color.fromARGB(455, 93, 128, 37),
          unselectedLabelColor: const Color.fromARGB(255, 100, 100, 100),
          tabs: const [
            Tab(icon: Icon(Icons.analytics_outlined), text: "Analytics"),
            Tab(icon: Icon(Icons.account_balance_wallet_outlined), text: "Treasury"),
            Tab(icon: Icon(Icons.live_tv_outlined), text: "Live Studio"),
            Tab(icon: Icon(Icons.person_outline), text: "Persona"),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildAnalyticsTab(),
          _buildTreasuryTab(),
          _buildLiveStudioTab(),
          _buildPersonaTab(),
        ],
      ),
    );
  }

  // TAB 1: Analytics & Mesh Reach
  Widget _buildAnalyticsTab() {
    final double fanProgress = (_verifiedFansCount / _verifiedFanTarget).clamp(0.0, 1.0);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Verified Fan Progress Bar
        Card(
          color: const Color(0xFF1E293B),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Verified Fan Milestone (Payout Floor)',
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                    ),
                    Text(
                      '$_verifiedFansCount / $_verifiedFanTarget Fans',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                LinearProgressIndicator(
                  value: fanProgress,
                  backgroundColor: const Color(0xFF334155),
                  color: const Color.fromARGB(255, 23, 35, 3),
                  minHeight: 10,
                  borderRadius: BorderRadius.circular(5),
                ),
                const SizedBox(height: 8),
                Text(
                  'Reach $_verifiedFanTarget verified fans to unlock zero-touch automated weekly payout distributions.',
                  style: const TextStyle(color: Color.fromARGB(255, 140, 140, 140), fontSize: 12),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        // Network Metrics
        Row(
          children: [
            Expanded(child: _buildMetricCard('P2P Mesh Reach', '12,450 Nodes', Icons.hub_outlined, Colors.purpleAccent)),
            const SizedBox(width: 12),
            Expanded(child: _buildMetricCard('Signed Reactions', '48.2k', Icons.favorite_outline, Colors.pinkAccent)),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(child: _buildMetricCard('3D Gift Volume', '3,920 Tokens', Icons.card_giftcard, Colors.amberAccent)),
            const SizedBox(width: 12),
            Expanded(child: _buildMetricCard('GossipSub Latency', '< 82 ms', Icons.speed, Colors.greenAccent)),
          ],
        ),
      ],
    );
  }

  // TAB 2: Treasury & 1-Tap Cash Out
  Widget _buildTreasuryTab() {
    final double usdEquivalent = _omniCreditsBalance / 100.0;
    final double grossUSD = usdEquivalent;
    final double platformFeeUSD = grossUSD * (_platformFeePercent / 100.0);
    final double netPayoutUSD = grossUSD - platformFeeUSD;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Balance Banner
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF0284C7), Color(0xFF0369A1)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Available Treasury Balance', style: TextStyle(color: Colors.white70, fontSize: 13)),
              const SizedBox(height: 6),
              Text(
                '$_omniCreditsBalance OmniCredits',
                style: const TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.bold),
              ),
              Text(
                '≈ \$${usdEquivalent.toStringAsFixed(2)} USD',
                style: const TextStyle(color: Colors.white, fontSize: 14),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        // Fee Transparency Breakdown
        Card(
          color: const Color(0xFF1E293B),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Transparent Payout Breakdown', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
                const Divider(color: Color(0xFF334155), height: 20),
                _buildFeeRow('Gross Earnings', '\$${grossUSD.toStringAsFixed(2)} USD', Colors.white, const Divider(color: Color(0xFF334155), height: 20)),
                _buildFeeRow('Platform Treasury Cut ($_platformFeePercent%)', '-\$${platformFeeUSD.toStringAsFixed(2)} USD', Colors.redAccent, const Divider(color: Color(0xFF334155), height: 20)),
                _buildFeeRow('Role Subscription Split Tier', '${_creatorSplitPercent.toStringAsFixed(0)}% Net', const Color.fromARGB(171, 14, 141, 37),
                const Divider(color: Color(0xFF334155), height: 20)),
                _buildFeeRow('Estimated Net Bank Payout', '\$${netPayoutUSD.toStringAsFixed(2)} USD', const Color.fromARGB(685, 425, 152, 3), const Divider(color: Color(0xFF334155), height: 20), isBold: true),

                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color.fromARGB(255, 93, 128, 37),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    icon: const Icon(Icons.account_balance, color: Colors.black),
                    label: const Text(
                      '1-Tap Cash Out to Bank / Card',
                      style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 15),
                    ),
                    onPressed: () {
                      _showCashOutConfirmationDialog(context, netPayoutUSD);
                    },
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  // TAB 3: Live & Interactive Studio Controls
  Widget _buildLiveStudioTab() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          'Dockable Live Stream Overlay Controls',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
        ),
        const SizedBox(height: 12),
        _buildStudioActionTile(
          'Launch Interactive P2P Trivia',
          'Trigger live multiple-choice quiz overlay for stream viewers',
          Icons.quiz_outlined,
          Colors.amberAccent,
        ),
        _buildStudioActionTile(
          'Start Prediction Market Pool',
          'Let spectators stake OmniCredits on stream outcomes',
          Icons.query_stats_outlined,
          Colors.purpleAccent,
        ),
        _buildStudioActionTile(
          '3D Floating Gift Ticker',
          'Real-time stream overlay active (100-item gift catalog)',
          Icons.card_giftcard,
          Colors.pinkAccent,
        ),
      ],
    );
  }

  // TAB 4: Live Persona Engine (LPE) & Paywalls
  Widget _buildPersonaTab() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          color: const Color(0xFF1E293B),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                const CircleAvatar(
                  radius: 40,
                  backgroundColor: Color.fromARGB(255, 14, 141, 37),
                  child: Icon(Icons.person, size: 50, color: Colors.black),
                ),
                const SizedBox(height: 10),
                const Text('Live Persona Avatar Config', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                const SizedBox(height: 4),
                const Text('Layer 0: Standard Body Mesh  |  Layer 1: Equipped Cosmetics', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(side: const BorderSide(color:Color(0xFFFF9000)), backgroundColor: const Color.fromARGB(255, 14, 141, 37), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
                  icon: const Icon(Icons.style, color: Color.fromARGB(234, 14, 141, 37)),
                  label: const Text('Edit LPE Cosmetic Layers', style: TextStyle(color: Color.fromARGB(234, 14, 141, 37), fontWeight: FontWeight.bold)),
                  onPressed: () {},
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  // Helper Widgets
  Widget _buildMetricCard(String title, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(height: 8),
          Text(value, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
          Text(title, style: const TextStyle(color: Color.fromARGB(563, 45, 63, 76), fontSize: 11)),
        ],
      ),
    );
  }

  Widget _buildFeeRow(String label, String amount, Color amountColor, Divider divider, {bool isBold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: Colors.white70, fontSize: 13, fontWeight: isBold ? FontWeight.bold : FontWeight.normal)),
          Text(amount, style: TextStyle(color: amountColor, fontSize: 13, fontWeight: isBold ? FontWeight.bold : FontWeight.normal)),
        ],
      ),
    );
  }

  Widget _buildStudioActionTile(String title, String subtitle, IconData icon, Color iconColor) {
    return Card(
      color: const Color(0xFF1E293B),
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        leading: Icon(icon, color: iconColor, size: 30),
        title: Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
        subtitle: Text(subtitle, style: const TextStyle(color: Color.fromARGB(563, 45, 63, 45), fontSize: 12)),
        trailing: const Icon(Icons.arrow_forward_ios, color: Color.fromARGB(563, 45, 63, 15), size: 14),
        onTap: () {},
      ),
    );
  }

  void _showCashOutConfirmationDialog(BuildContext context, double netPayout) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Confirm Cash Out', style: TextStyle(color: Colors.white)),
        content: Text(
          'Initiate automated bank payout of \$${netPayout.toStringAsFixed(2)} USD?\n\nThis generates a signed WITHDRAWAL_REQUEST delta processed by the OmniLedger agent.',
          style: const TextStyle(color: Colors.white70, fontSize: 13),
        ),
        actions: [
          TextButton(
            child: const Text('Cancel', style: TextStyle(color: Color.fromARGB(563, 45, 63, 68))),
            onPressed: () => Navigator.pop(context),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: const Color.fromARGB(625, 256, 354, 698)),
            child: const Text('Confirm & Sign (FaceID)', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
            onPressed: () {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Withdrawal request signed and broadcast to OmniLedger!')),
              );
            },
          ),
        ],
      ),
    );
  }
}
