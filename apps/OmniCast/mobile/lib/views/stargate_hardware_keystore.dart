import 'package:flutter/material.dart';

class StargateHardwareKeystore {
  static const String keyAlias = 'stargate_master_identity';

  /// No real attestation exists yet (no Android Key Attestation / App Attest call), so this
  /// reports "not verified" instead of a hardcoded pass (issue #5).
  static Future<Map<String, dynamic>> verifyHardwareEnclaveAttestation() async {
    return {
      'is_hardware_backed': false,
      'enclave_type': 'not verified',
      'key_alias': keyAlias,
      'non_exportable': false,
      'attestation_score': null,
    };
  }
}

class HardwareSecurityBadge extends StatefulWidget {
  const HardwareSecurityBadge({super.key});

  @override
  State<HardwareSecurityBadge> createState() => _HardwareSecurityBadgeState();
}

class _HardwareSecurityBadgeState extends State<HardwareSecurityBadge> {
  bool _isAttested = false;

  @override
  void initState() {
    super.initState();
    _checkAttestation();
  }

  void _checkAttestation() async {
    final result = await StargateHardwareKeystore.verifyHardwareEnclaveAttestation();
    if (mounted) {
      setState(() {
        _isAttested = result['is_hardware_backed'] == true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: _isAttested ? const Color(0x2610B981) : const Color(0x26FF9800),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _isAttested ? const Color(0xFF10B981) : Colors.orange),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            _isAttested ? Icons.verified_user_rounded : Icons.security_rounded,
            size: 12,
            color: _isAttested ? const Color(0xFF10B981) : Colors.orange,
          ),
          const SizedBox(width: 4),
          Text(
            _isAttested ? 'Hardware key (attested)' : 'Software key (not attested)',
            style: TextStyle(
              color: _isAttested ? const Color(0xFF10B981) : Colors.orange,
              fontSize: 10,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
