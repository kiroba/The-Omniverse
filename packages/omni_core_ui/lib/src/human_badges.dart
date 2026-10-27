import 'package:flutter/material.dart';

/// "Mesh Online · 1 connected" / "Offline mode" instead of raw IPs and ports.
class MeshStatusBadge extends StatelessWidget {
  final bool online;
  final int peers;
  const MeshStatusBadge({super.key, required this.online, required this.peers});

  @override
  Widget build(BuildContext context) {
    final color = online ? const Color(0xFF10B981) : const Color(0xFF94A3B8);
    final label = !online
        ? 'Offline mode'
        : peers == 0
            ? 'Hub online · no peers yet'
            : 'Mesh online · $peers connected';
    return _Pill(color: color, icon: online ? Icons.hub : Icons.cloud_off, label: label);
  }
}

/// Green HUMAN badge, shown only when the Ed25519 signature really verified
/// (see StargateIdentity.verify). Unverified content gets a neutral badge.
class HumanVerifiedBadge extends StatelessWidget {
  final bool verified;
  const HumanVerifiedBadge({super.key, required this.verified});

  @override
  Widget build(BuildContext context) => verified
      ? const _Pill(color: Color(0xFF22C55E), icon: Icons.verified_user, label: 'HUMAN')
      : const _Pill(color: Color(0xFF94A3B8), icon: Icons.help_outline, label: 'Unverified');
}

class _Pill extends StatelessWidget {
  final Color color;
  final IconData icon;
  final String label;
  const _Pill({required this.color, required this.icon, required this.label});

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: color.withOpacity(0.15),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: color.withOpacity(0.6)),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 6),
          Text(label, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
        ]),
      );
}
