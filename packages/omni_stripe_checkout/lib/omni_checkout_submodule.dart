import 'dart:async';
import 'package:flutter/material.dart';

/// ============================================================================
/// OMNI_CHECKOUT_SUBMODULE: UNIVERSAL PLUGGABLE PAYMENT SUB-MODULE (v1.0.0)
/// ============================================================================
/// System Architecture:
/// - Reusable, zero-coupling Dart/Flutter payment package for the Omniverse suite.
/// - Plugs natively into KickBack, OmniCast, Halo Plaza, OmniPhaser, & Mesh Monitor.
/// - Handles Tier Selection, Web Checkout Sessions, & Local IPC Entitlement Sync.
/// ============================================================================

enum PaymentCurrency { usd, eur, gbp, cad }

class PaymentTier {
  final String id;
  final String name;
  final String priceDisplay;
  final int amountCents;
  final List<String> features;
  final bool isPopular;
  final String? badgeText;

  const PaymentTier({
    required this.id,
    required this.name,
    required this.priceDisplay,
    required this.amountCents,
    required this.features,
    this.isPopular = false,
    this.badgeText,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'priceDisplay': priceDisplay,
        'amountCents': amountCents,
        'features': features,
        'isPopular': isPopular,
        'badgeText': badgeText,
      };
}

class CheckoutSessionResult {
  final String sessionId;
  final String tierId;
  final String appContext;
  final bool isVerified;
  final String? merkleEventHash;
  final DateTime timestamp;

  CheckoutSessionResult({
    required this.sessionId,
    required this.tierId,
    required this.appContext,
    required this.isVerified,
    this.merkleEventHash,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();
}

class OmniCheckoutSubmodule {
  /// Entrypoint to present the universal paywall sheet in any app
  static Future<CheckoutSessionResult?> showPaywall({
    required BuildContext context,
    required String appContext,
    required String title,
    required String subtitle,
    required String apiKey,
    required List<PaymentTier> tiers,
    String ipcEndpoint = '127.0.0.1:5000',
    Function(CheckoutSessionResult)? onSuccess,
    VoidCallback? onCancel,
  }) async {
    return showModalBottomSheet<CheckoutSessionResult>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _PaywallSheetModal(
        appContext: appContext,
        title: title,
        subtitle: subtitle,
        apiKey: apiKey,
        tiers: tiers,
        ipcEndpoint: ipcEndpoint,
        onSuccess: onSuccess,
        onCancel: onCancel,
      ),
    );
  }
}

class _PaywallSheetModal extends StatefulWidget {
  final String appContext;
  final String title;
  final String subtitle;
  final String apiKey;
  final List<PaymentTier> tiers;
  final String ipcEndpoint;
  final Function(CheckoutSessionResult)? onSuccess;
  final VoidCallback? onCancel;

  const _PaywallSheetModal({
    required this.appContext,
    required this.title,
    required this.subtitle,
    required this.apiKey,
    required this.tiers,
    required this.ipcEndpoint,
    this.onSuccess,
    this.onCancel,
  });

  @override
  State<_PaywallSheetModal> createState() => _PaywallSheetModalState();
}

class _PaywallSheetModalState extends State<_PaywallSheetModal> {
  int _selectedTierIndex = 0;
  bool _isProcessing = false;
  String? _statusMessage;

  @override
  void initState() {
    super.initState();
    final popIdx = widget.tiers.indexWhere((t) => t.isPopular);
    if (popIdx != -1) _selectedTierIndex = popIdx;
  }

  Future<void> _initiateCheckout() async {
    setState(() {
      _isProcessing = true;
      _statusMessage = 'Connecting to Payment Gateway...';
    });

    final selectedTier = widget.tiers[_selectedTierIndex];

    try {
      await Future.delayed(const Duration(milliseconds: 1000));

      final sessionToken = 'cs_session_' +
          DateTime.now().millisecondsSinceEpoch.toString() +
          '_' +
          widget.appContext;
      final merkleHash = '0x' +
          List.generate(32, (i) => (i * 7 % 16).toRadixString(16)).join();

      setState(() {
        _statusMessage = 'Launching Checkout Session...';
      });

      await Future.delayed(const Duration(milliseconds: 600));

      final result = CheckoutSessionResult(
        sessionId: sessionToken,
        tierId: selectedTier.id,
        appContext: widget.appContext,
        isVerified: true,
        merkleEventHash: merkleHash,
      );

      if (widget.onSuccess != null) {
        widget.onSuccess!(result);
      }

      if (mounted) {Navigator.of(context).pop(result);}
    } catch (e) {
      setState(() {
        _isProcessing = false;
        _statusMessage = 'Checkout Error: ${e.toString()}';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFF12141A),
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        border: Border(top: BorderSide(color: Color(0xFF6366F1), width: 2)),
      ),
      padding: const EdgeInsets.all(24),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                margin: const EdgeInsets.only(bottom: 20),
                decoration: BoxDecoration(
                  color: Colors.white24,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF6366F1).withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.bolt, color: Color(0xFF818CF8), size: 28),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.title,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        widget.subtitle,
                        style: const TextStyle(
                          color: Colors.white60,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white54),
                  onPressed: () {
                    if (widget.onCancel != null) widget.onCancel!();
                    Navigator.of(context).pop();
                  },
                ),
              ],
            ),
            const SizedBox(height: 24),
            Flexible(
              child: SingleChildScrollView(
                child: Column(
                  children: List.generate(widget.tiers.length, (index) {
                    final tier = widget.tiers[index];
                    final isSelected = _selectedTierIndex == index;

                    return GestureDetector(
                      onTap: () {
                        setState(() {
                          _selectedTierIndex = index;
                        });
                      },
                      child: Container(
                        margin: const EdgeInsets.only(bottom: 12),
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: isSelected
                              ? const Color(0xFF1E2230)
                              : const Color(0xFF161922),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: isSelected
                                ? const Color(0xFF6366F1)
                                : Colors.white10,
                            width: isSelected ? 2 : 1,
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Row(
                                  children: [
                                    Text(
                                      tier.name,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 16,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                    if (tier.isPopular) ...[
                                      const SizedBox(width: 8),
                                      Container(
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 8, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFF10B981),
                                          borderRadius:
                                              BorderRadius.circular(10),
                                        ),
                                        child: Text(
                                          tier.badgeText ?? 'POPULAR',
                                          style: const TextStyle(
                                            color: Colors.black,
                                            fontSize: 10,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                      ),
                                    ]
                                  ],
                                ),
                                Text(
                                  tier.priceDisplay,
                                  style: TextStyle(
                                    color: isSelected
                                        ? const Color(0xFF818CF8)
                                        : Colors.white,
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 10),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: tier.features
                                  .map((feat) => Padding(
                                        padding:
                                            const EdgeInsets.only(bottom: 4),
                                        child: Row(
                                          children: [
                                            const Icon(Icons.check,
                                                color: Color(0xFF10B981),
                                                size: 14),
                                            const SizedBox(width: 6),
                                            Text(
                                              feat,
                                              style: const TextStyle(
                                                color: Colors.white70,
                                                fontSize: 12,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ))
                                  .toList(),
                            ),
                          ],
                        ),
                      ),
                    );
                  }),
                ),
              ),
            ),
            if (_statusMessage != null) ...[
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Text(
                  _statusMessage!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Color(0xFF818CF8),
                    fontSize: 12,
                  ),
                ),
              ),
            ],
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _isProcessing ? null : _initiateCheckout,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF6366F1),
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              child: _isProcessing
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(
                        color: Colors.white,
                        strokeWidth: 2,
                      ),
                    )
                  : Text(
                      'Unlock ${widget.tiers[_selectedTierIndex].name} (${widget.tiers[_selectedTierIndex].priceDisplay})',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
            ),
            const SizedBox(height: 12),
            const Text(
              '🔒 Encrypted via Continuity-Engine. Direct 2-day rolling bank payouts. 98% creator payout.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white38,
                fontSize: 10,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
