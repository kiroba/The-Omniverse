import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// The KickBack Mobile Checkout & Educator Domain Verification UI
/// Handles accredited .edu registry validation, ZK-Email live challenge,
/// role tier subscription selection, net revenue split breakdown,
/// and multi-rail payments (Cash App, Venmo, PayPal, Lightning).

class KickBackCheckoutScreen extends StatefulWidget {
  final String authorPubkey;
  final String authorUsername;
  final String currentRoleTier; // 'COMMON', 'CREATOR', 'INFLUENCER', 'EDUCATOR'

  const KickBackCheckoutScreen({
    Key? key,
    required this.authorPubkey,
    required this.authorUsername,
    this.currentRoleTier = 'CREATOR',
  }) : super(key: key);

  @override
  _KickBackCheckoutScreenState createState() => _KickBackCheckoutScreenState();
}

class _KickBackCheckoutScreenState extends State<KickBackCheckoutScreen> {
  // Navigation & Selection State
  int _currentStep = 0; // 0: Select Tier, 1: Educator Verification (if selected), 2: Payment
  String _selectedRoleTier = 'CREATOR';
  String _selectedPaymentRail = 'CASH_APP'; // 'CASH_APP', 'VENMO', 'PAYPAL', 'LIGHTNING'

  // Educator Verification Form State
  final TextEditingController _emailController = TextEditingController();
  bool _isRegistryVerified = false;
  String _verifiedInstitutionName = '';
  bool _isGeneratingZkProof = false;
  bool _isZkProofValidated = false;
  String _zkProofNullifier = '';

  // Payment Calculation Details
  double get grossPriceUsd {
    if (_selectedRoleTier == 'EDUCATOR') return 5.00;
    return 10.00;
  }

  double get platformFeePercent {
    switch (_selectedRoleTier) {
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

  double get platformFeeUsd => (grossPriceUsd * (platformFeePercent / 100.0));
  double get creatorPayoutUsd => grossPriceUsd - platformFeeUsd;

  // Accredited Registry Mock Lookup
  final Map<String, String> _accreditedRegistry = {
    'wgu.edu': 'Western Governors University',
    'stanford.edu': 'Stanford University',
    'mit.edu': 'Massachusetts Institute of Technology',
    'harvard.edu': 'Harvard University',
    'oxford.ac.uk': 'University of Oxford',
  };

  void _checkDomainRegistry(String email) {
    final parts = email.trim().toLowerCase().split('@');
    if (parts.length == 2) {
      final domain = parts[1];
      if (_accreditedRegistry.containsKey(domain)) {
        setState(() {
          _isRegistryVerified = true;
          _verifiedInstitutionName = _accreditedRegistry[domain]!;
        });
        return;
      }
    }
    setState(() {
      _isRegistryVerified = false;
      _verifiedInstitutionName = '';
    });
  }

  Future<void> _simulateZkProofGeneration() async {
    setState(() {
      _isGeneratingZkProof = true;
    });

    await Future.delayed(const Duration(seconds: 2));

    setState(() {
      _isGeneratingZkProof = false;
      _isZkProofValidated = true;
      _zkProofNullifier = '0x448bd2aa88fbb51e9203847291048471';
      _selectedRoleTier = 'EDUCATOR';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('Checkout & Verification', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Progress Header
            _buildProgressHeader(),
            const SizedBox(height: 20),

            // Step 1: Role Tier Selection
            if (_currentStep == 0) _buildTierSelectionStep(),

            // Step 2: Educator Domain Verification
            if (_currentStep == 1) _buildEducatorVerificationStep(),

            // Step 3: Payment Rail & Split Breakdown
            if (_currentStep == 2) _buildPaymentRailStep(),
          ],
        ),
      ),
    );
  }

  Widget _buildProgressHeader() {
    return Row(
      children: [
        _buildStepIndicator(0, 'Select Tier'),
        _buildStepLine(0),
        _buildStepIndicator(1, 'Verify .EDU'),
        _buildStepLine(1),
        _buildStepIndicator(2, 'Payment'),
      ],
    );
  }

  Widget _buildStepIndicator(int stepIndex, String label) {
    final bool isActive = _currentStep == stepIndex;
    final bool isDone = _currentStep > stepIndex;

    return Column(
      children: [
        CircleAvatar(
          radius: 14,
          backgroundColor: isDone
              ? Colors.green
              : isActive
                  ? const Color(0xFF38BDF8)
                  : const Color(0xFF334155),
          child: isDone
              ? const Icon(Icons.check, size: 16, color: Colors.white)
              : Text('${stepIndex + 1}', style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)),
        ),
        const SizedBox(height: 4),
        Text(label, style: TextStyle(color: isActive ? const Color(0xFF38BDF8) : Colors.grey, fontSize: 10)),
      ],
    );
  }

  Widget _buildStepLine(int stepIndex) {
    return Expanded(
      child: Container(
        height: 2,
        color: _currentStep > stepIndex ? Colors.green : const Color(0xFF334155),
        margin: const EdgeInsets.symmetric(horizontal: 4),
      ),
    );
  }

  Widget _buildTierSelectionStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text("Choose Your Subscription Tier", style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        Text("Subscribing to @${widget.authorUsername}", style: const TextStyle(color: Colors.grey, fontSize: 13)),
        const SizedBox(height: 16),

        _buildTierOptionCard(
          tierKey: 'CREATOR',
          title: 'Content Creator',
          price: '\$10.00 / month',
          feeShare: '82% to Creator (18% Platform Fee)',
          description: 'Standard paywall unlock tier with full access to exclusive posts.',
          icon: Icons.star_border,
          badgeColor: Colors.purple,
        ),
        const SizedBox(height: 12),

        _buildTierOptionCard(
          tierKey: 'EDUCATOR',
          title: 'Educator Tier (50% Off)',
          price: '\$5.00 / month',
          feeShare: '90% to Creator (10% Platform Fee)',
          description: 'Requires active account verification at an accredited .edu domain (e.g. wgu.edu, stanford.edu).',
          icon: Icons.school_outlined,
          badgeColor: Colors.green,
          isVerified: _isZkProofValidated,
        ),
        const SizedBox(height: 12),

        _buildTierOptionCard(
          tierKey: 'INFLUENCER',
          title: 'Influencer',
          price: '\$10.00 / month',
          feeShare: '85% to Creator (15% Platform Fee)',
          description: 'High-reach account. All promotional videos feature mandatory ad tags.',
          icon: Icons.campaign_outlined,
          badgeColor: Colors.orange,
        ),

        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          height: 48,
          child: ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0284C7)),
            onPressed: () {
              if (_selectedRoleTier == 'EDUCATOR' && !_isZkProofValidated) {
                setState(() => _currentStep = 1);
              } else {
                setState(() => _currentStep = 2);
              }
            },
            child: Text(
              _selectedRoleTier == 'EDUCATOR' && !_isZkProofValidated
                  ? "Verify .EDU Account to Continue"
                  : "Proceed to Payment (\$${grossPriceUsd.toStringAsFixed(2)})",
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
            ),
          ),
        )
      ],
    );
  }

  Widget _buildTierOptionCard({
    required String tierKey,
    required String title,
    required String price,
    required String feeShare,
    required String description,
    required IconData icon,
    required Color badgeColor,
    bool isVerified = false,
  }) {
    final bool isSelected = _selectedRoleTier == tierKey;

    return GestureDetector(
      onTap: () => setState(() => _selectedRoleTier = tierKey),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: isSelected ? const Color(0xFF38BDF8) : const Color(0xFF334155), width: isSelected ? 2.0 : 1.0),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Icon(icon, color: badgeColor, size: 22),
                    const SizedBox(width: 8),
                    Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
                  ],
                ),
                Text(price, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
              ],
            ),
            const SizedBox(height: 6),
            Text(feeShare, style: TextStyle(color: badgeColor, fontSize: 11, fontWeight: FontWeight.bold)),
            const SizedBox(height: 6),
            Text(description, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
            if (isVerified) ...[
              const SizedBox(height: 8),
              Row(
                children: const [
                  Icon(Icons.verified, color: Colors.green, size: 14),
                  SizedBox(width: 4),
                  Text("Active Account Verified via ZK-Email", style: TextStyle(color: Colors.green, fontSize: 11, fontWeight: FontWeight.bold)),
                ],
              )
            ]
          ],
        ),
      ),
    );
  }

  Widget _buildEducatorVerificationStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text("Official Educator Verification", style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        const Text("Enter your active institutional email address to verify your account against the Official Accredited Registry.", style: TextStyle(color: Colors.grey, fontSize: 12)),
        const SizedBox(height: 16),

        TextField(
          controller: _emailController,
          style: const TextStyle(color: Colors.white),
          onChanged: _checkDomainRegistry,
          decoration: InputDecoration(
            labelText: 'Institutional Email (e.g. professor@wgu.edu)',
            labelStyle: const TextStyle(color: Colors.grey),
            filled: true,
            fillColor: const Color(0xFF1E293B),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFF334155))),
            suffixIcon: _isRegistryVerified
                ? const Icon(Icons.check_circle, color: Colors.green)
                : const Icon(Icons.school, color: Colors.grey),
          ),
        ),

        const SizedBox(height: 12),

        if (_isRegistryVerified) ...[
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: Colors.green.withOpacity(0.15), borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.green)),
            child: Row(
              children: [
                const Icon(Icons.verified, color: Colors.green, size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    "Accredited Institution Found: $_verifiedInstitutionName",
                    style: const TextStyle(color: Colors.green, fontWeight: FontWeight.bold, fontSize: 12),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          if (!_isZkProofValidated) ...[
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
                onPressed: _isGeneratingZkProof ? null : _simulateZkProofGeneration,
                icon: _isGeneratingZkProof
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.lock_clock),
                label: Text(_isGeneratingZkProof ? "Generating Live ZK-Email Proof..." : "Generate ZK-Email DKIM Proof"),
              ),
            ),
          ] else ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: const Color(0xFF1E293B), borderRadius: BorderRadius.circular(8), border: Border.all(color: const Color(0xFF38BDF8))),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("ZK-Email Proof Successfully Generated!", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Text("Anonymous Nullifier: $_zkProofNullifier", style: const TextStyle(color: Colors.grey, fontSize: 10, fontFamily: 'monospace')),
                  const SizedBox(height: 4),
                  const Text("Validity Window: 365 Days (Annual Re-Verification Enforced)", style: TextStyle(color: Color(0xFF38BDF8), fontSize: 11)),
                ],
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0284C7)),
                onPressed: () => setState(() => _currentStep = 2),
                child: const Text("Continue to Payment (\$5.00/mo)"),
              ),
            )
          ]
        ] else if (_emailController.text.isNotEmpty) ...[
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: Colors.amber.withOpacity(0.15), borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.amber)),
            child: const Text(
              "Domain not listed in Official Accredited Registry. Generic or unverified .edu domains are prohibited.",
              style: TextStyle(color: Colors.amber, fontSize: 12),
            ),
          )
        ]
      ],
    );
  }

  Widget _buildPaymentRailStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text("Payment & Settlement", style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        Text("Selected Role: $_selectedRoleTier (\$${grossPriceUsd.toStringAsFixed(2)}/month)", style: const TextStyle(color: Color(0xFF38BDF8), fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),

        // Net Revenue Split Card
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(color: const Color(0xFF1E293B), borderRadius: BorderRadius.circular(10), border: Border.all(color: const Color(0xFF334155))),
          child: Column(
            children: [
              _buildSplitRow("Gross Subscription Amount", "\$${grossPriceUsd.toStringAsFixed(2)}", isBold: true),
              const Divider(color: Color(0xFF334155)),
              _buildSplitRow("Net Creator Payout (${(100 - platformFeePercent).toInt()}%)", "\$${creatorPayoutUsd.toStringAsFixed(2)}", color: Colors.green),
              _buildSplitRow("KickBack Platform Fee (${platformFeePercent.toInt()}%)", "\$${platformFeeUsd.toStringAsFixed(2)}", color: Colors.grey),
            ],
          ),
        ),

        const SizedBox(height: 20),
        const Text("Select Fiat or P2P Payment Rail", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
        const SizedBox(height: 12),

        _buildPaymentRailButton("CASH_APP", "Cash App USD", "Instant 1-Tap USD via LNURL-Pay", Icons.monetization_on, Colors.green),
        const SizedBox(height: 8),
        _buildPaymentRailButton("VENMO", "Venmo Direct", "Deep link transfer to Creator & Treasury handles", Icons.send, Colors.blue),
        const SizedBox(height: 8),
        _buildPaymentRailButton("PAYPAL", "PayPal Direct", "Direct P2P checkout without middleman fees", Icons.account_balance_wallet, Colors.indigo),
        const SizedBox(height: 8),
        _buildPaymentRailButton("LIGHTNING", "Lightning Network", "Zero-trust HTLC with atomic preimage release", Icons.bolt, Colors.amber),

        const SizedBox(height: 24),

        SizedBox(
          width: double.infinity,
          height: 50,
          child: ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0284C7)),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Processing $_selectedPaymentRail payment of \$${grossPriceUsd.toStringAsFixed(2)}...')),
              );
            },
            child: Text("Pay \$${grossPriceUsd.toStringAsFixed(2)} via $_selectedPaymentRail", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          ),
        )
      ],
    );
  }

  Widget _buildSplitRow(String label, String value, {bool isBold = false, Color color = Colors.white}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: color, fontSize: 13, fontWeight: isBold ? FontWeight.bold : FontWeight.normal)),
          Text(value, style: TextStyle(color: color, fontSize: 13, fontWeight: isBold ? FontWeight.bold : FontWeight.normal)),
        ],
      ),
    );
  }

  Widget _buildPaymentRailButton(String key, String title, String subtitle, IconData icon, Color iconColor) {
    final bool isSelected = _selectedPaymentRail == key;

    return GestureDetector(
      onTap: () => setState(() => _selectedPaymentRail = key),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: isSelected ? const Color(0xFF38BDF8) : const Color(0xFF334155), width: isSelected ? 2.0 : 1.0),
        ),
        child: Row(
          children: [
            Icon(icon, color: iconColor, size: 24),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
                  Text(subtitle, style: const TextStyle(color: Colors.grey, fontSize: 11)),
                ],
              ),
            ),
            if (isSelected) const Icon(Icons.check_circle, color: Color(0xFF38BDF8), size: 18),
          ],
        ),
      ),
    );
  }
}
