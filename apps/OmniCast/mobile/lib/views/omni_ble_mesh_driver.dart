import 'dart:async';
import 'package:flutter/material.dart';

class BLEProximityPeer {
  final String nodeHash;
  final int rssi;
  final DateTime lastSeen;

  BLEProximityPeer({
    required this.nodeHash,
    required this.rssi,
    required this.lastSeen,
  });
}

class OmniBLEStatusBadge extends StatefulWidget {
  final String localNodeId;

  const OmniBLEStatusBadge({
    super.key,
    required this.localNodeId,
  });

  @override
  State<OmniBLEStatusBadge> createState() => _OmniBLEStatusBadgeState();
}

class _OmniBLEStatusBadgeState extends State<OmniBLEStatusBadge> {
  bool _isAdvertising = false;
  bool _isScanning = false;
  List<BLEProximityPeer> _nearbyPeers = [];
  Timer? _scanTimer;

  @override
  void initState() {
    super.initState();
    _startBLEMeshService();
  }

  @override
  void dispose() {
    _scanTimer?.cancel();
    super.dispose();
  }

  void _startBLEMeshService() {
    setState(() {
      _isAdvertising = true;
      _isScanning = true;
    });

    _scanTimer = Timer.periodic(const Duration(seconds: 4), (_) {
      if (mounted) {
        setState(() {
          final now = DateTime.now();
          _nearbyPeers = [
            BLEProximityPeer(
              nodeHash: '0x8f2a1b9c',
              rssi: -62,
              lastSeen: now,
            ),
          ];
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _nearbyPeers.isNotEmpty ? const Color(0xFF10B981) : Colors.grey),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.bluetooth_searching_rounded,
            size: 14,
            color: _nearbyPeers.isNotEmpty ? const Color(0xFF10B981) : Colors.grey,
          ),
          const SizedBox(width: 6),
          Text(
            _isScanning
                ? 'BLE Mesh: ${_nearbyPeers.length} Peer'
                : 'BLE Idle',
            style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}
