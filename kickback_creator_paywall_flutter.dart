import 'package:flutter/material.dart';

/// The KickBack Creator Subscription, Educator Verification & Paywall Unlock Modal
/// Repository: kiroba/The-KickBack
class KickBackPaywallAndSubscriptionModal extends StatefulWidget {
  final String creatorUsername;
  final String creatorPubkey;
  final String roleTier; // CREATOR, INFLUENCER, EDUCATOR
  final double monthlyPriceUsd;
  final Function(String paymentMethod) onSubscribeConfirmed;
  final Function(String eduEmail) onEducatorProofSubmitted;

  const KickBackPaywallAndSubscriptionModal({
    Key? key,
    required this.creatorUsername,
    required this.creatorPubkey,
    required this.roleTier,
    this.monthlyPriceUsd = 10.00,
    required this.onSubscribeConfirmed,
    required this.onEducatorProofSubmitted,
  }) : super(key: key);

  @override
  _KickBackPaywallAndSubscriptionModalState createState() =>
      _KickBackPaywallAndSubscriptionModalState();
}

class _KickBackPaywallAndSubscriptionModalState
    extends State<KickBackPaywallAndSubscriptionModal>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final TextEditingController _eduEmailController = TextEditingController();
  bool _isProcessing = false;
  String _selectedPaymentMethod = 'Lightning / P2P Rail';

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _eduEmailController.dispose();
    super.dispose();
  }

  double get _effectivePrice {
    if (widget.roleTier == 'EDUCATOR') return 5.00; // 50% discount
    return widget.monthlyPriceUsd;
  }

  double get _platformFeePercent {
    switch (widget.roleTier) {
      case 'EDUCATOR':
        return 10.0;
      case 'INFLUENCER':
        return 15.0;
      case 'CREATOR':
        return 18.0;
      default:
        return 20.0;
    }
  }

  void _handleSubscribe() async {
    setState(() => _isProcessing = true);
    await Future.delayed(const Duration(milliseconds: 1200)); // Simulate P2P network settlement
    setState(() => _isProcessing = false);
    widget.onSubscribeConfirmed(_selectedPaymentMethod);
    Navigator.of(context).pop();
  }

  void _handleVerifyEducator() async {
    final email = _eduEmailController.text.trim();
    if (!email.contains('@') || (!email.endsWith('.edu') && !email.contains('.ac.'))) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter a valid accredited .edu or academic email.'),
          backgroundColor: Colors.redAccent,
        ),
      );
      return;
    }

    setState(() => _isProcessing = true);
    await Future.delayed(const Duration(milliseconds: 1500)); // Simulate ZK-Email proof generation
    setState(() => _isProcessing = false);
    widget.onEducatorProofSubmitted(email);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Educator status verified via anonymous ZK-Proof! Price reduced to $5/mo.'),
        backgroundColor: Colors.green,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.78,
      decoration: const BoxDecoration(
        color: Color(0xFF0F172A), // Dark Slate
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        children: [
          // Drag Handle
          Container(
            margin: const EdgeInsets.only(top: 10, bottom: 8),
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: const Color(0xFF475569),
              borderRadius: BorderRadius.circular(2),
            ),
          ),

          // Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.lock_open_rounded, color: Color(0xFF38BDF8), size: 22),
                    const SizedBox(width: 8),
                    Text(
                      'Unlock @${widget.creatorUsername}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.grey),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
          ),

          // Tabs
          TabBar(
            controller: _tabController,
            indicatorColor: const Color(0xFF38BDF8),
            labelColor: const Color(0xFF38BDF8),
            unselectedLabelColor: const Color(0xFF94A3B8),
            tabs: const [
              Tab(text: "Subscribe & Unlock"),
              Tab(text: "Educator Discount (50% Off)"),
            ],
          ),

          // Tab Content
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                // TAB 1: Subscribe & Unlock
                SingleChildScrollView(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Subscription Card
                      Container(
                        padding: const EdgeInsets.all(18),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF1E293B), Color(0xFF0F172A)],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: const Color(0xFF38BDF8), width: 1.5),
                        ),
                        child: Column(
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      '${widget.roleTier} SUBSCRIPTION',
                                      style: const TextStyle(
                                        color: Color(0xFF38BDF8),
                                        fontSize: 12,
                                        fontWeight: FontWeight.extrabold,
                                        letterSpacing: 1.0,
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      '\$${_effectivePrice.toStringAsFixed(2)} / month',
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 26,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ],
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: Colors.purple.withOpacity(0.2),
                                    borderRadius: BorderRadius.circular(20),
                                    border: Border.all(color: Colors.purpleAccent),
                                  ),
                                  child: Text(
                                    '${(100 - _platformFeePercent).toInt()}% to Creator',
                                    style: const TextStyle(
                                      color: Colors.purpleAccent,
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                )
                              ],
                            ),
                            const Divider(color: Color(0xFF334155), height: 24),
                            _BenefitRow(icon: Icons.check_circle_outline, text: 'Unlimited access to paywalled video & text posts'),
                            _BenefitRow(icon: Icons.check_circle_outline, text: 'Direct P2P encrypted subscriber badge'),
                            _BenefitRow(icon: Icons.check_circle_outline, text: 'Zero central platform censorship'),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),

                      // Payment Method Selector
                      const Text(
                        'Select P2P Payment Rail',
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                      ),
                      const SizedBox(height: 10),
                      _PaymentMethodTile(
                        title: 'Lightning Network / P2P Rail',
                        subtitle: 'Instant settlement, zero fees',
                        icon: Icons.bolt,
                        isSelected: _selectedPaymentMethod == 'Lightning / P2P Rail',
                        onTap: () => setState(() => _selectedPaymentMethod = 'Lightning / P2P Rail'),
                      ),
                      _PaymentMethodTile(
                        title: 'USD Stablecoin (USDC / USDT)',
                        subtitle: 'Decentralized L2 channel',
                        icon: Icons.account_balance_wallet_outlined,
                        isSelected: _selectedPaymentMethod == 'USD Stablecoin',
                        onTap: () => setState(() => _selectedPaymentMethod = 'USD Stablecoin'),
                      ),
                      const SizedBox(height: 20),

                      // Action Button
                      SizedBox(
                        width: double.infinity,
                        height: 52,
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF0284C7),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          onPressed: _isProcessing ? null : _handleSubscribe,
                          child: _isProcessing
                              ? const CircularProgressIndicator(color: Colors.white)
                              : Text(
                                  'Confirm Subscription (\$${_effectivePrice.toStringAsFixed(2)})',
                                  style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                                ),
                        ),
                      ),
                    ],
                  ),
                ),

                // TAB 2: Educator Verification
                SingleChildScrollView(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1E293B),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.green.shade700),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: const [
                            Text(
                              "Educator Role Privileges",
                              style: TextStyle(color: Colors.greenAccent, fontWeight: FontWeight.bold, fontSize: 16),
                            ),
                            SizedBox(height: 6),
                            Text(
                              "Educators pay only \$5/month (50% off standard Creator pricing) and enjoy an industry-lowest 10% platform fee schedule.",
                              style: TextStyle(color: Color(0xFFCBD5E1), fontSize: 13, height: 1.4),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),

                      const Text(
                        "Prove Educator Role via Anonymous ZK-Email",
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        "Enter your accredited .edu email address. Zero-Knowledge proofs verify your academic domain without revealing your identity on-chain.",
                        style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                      ),
                      const SizedBox(height: 14),

                      TextField(
                        controller: _eduEmailController,
                        style: const TextStyle(color: Colors.white),
                        decoration: InputDecoration(
                          hintText: "professor@university.edu",
                          hintStyle: const TextStyle(color: Color(0xFF64748B)),
                          filled: true,
                          fillColor: const Color(0xFF1E293B),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(10),
                            borderSide: const BorderSide(color: Color(0xFF334155)),
                          ),
                          prefixIcon: const Icon(Icons.school, color: Color(0xFF38BDF8)),
                        ),
                      ),
                      const SizedBox(height: 20),

                      SizedBox(
                        width: double.infinity,
                        height: 52,
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.green.shade700,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          onPressed: _isProcessing ? null : _handleVerifyEducator,
                          child: _isProcessing
                              ? const CircularProgressIndicator(color: Colors.white)
                              : const Text(
                                  "Generate ZK-Email Proof & Apply 50% Off",
                                  style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
                                ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _BenefitRow extends StatelessWidget {
  final IconData icon;
  final String text;
  const _BenefitRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Row(
        children: [
          Icon(icon, color: const Color(0xFF38BDF8), size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }
}

class _PaymentMethodTile extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final bool isSelected;
  final VoidCallback onTap;

  const _PaymentMethodTile({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isSelected ? const Color(0xFF38BDF8) : const Color(0xFF334155),
            width: isSelected ? 1.5 : 1.0,
          ),
        ),
        child: Row(
          children: [
            Icon(icon, color: isSelected ? const Color(0xFF38BDF8) : Colors.grey),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                  Text(subtitle, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                ],
              ),
            ),
            if (isSelected) const Icon(Icons.check_circle, color: Color(0xFF38BDF8), size: 20),
          ],
        ),
      ),
    );
  }
}
