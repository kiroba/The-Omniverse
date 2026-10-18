// ============================================================================
// THE OMNIVERSE & THE KICKBACK: HALO PLAZA (LPE PLAZA) EXPERIENCE (V4)
// Target Module: com.kickback.halo_plaza
// File: mobile/lib/halo_plaza_experience_ui.dart
// Version: 4.0.0 - Windows Back Navigation & Proximity Sheet Edition
// ============================================================================

import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

void main() {
  runApp(const HaloPlazaApp());
}

class HaloPlazaApp extends StatelessWidget {
  const HaloPlazaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Halo Plaza Experience',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF090D16), // Deep Slate
        primaryColor: const Color(0xFF00FFCC), // Neon Cyan
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00FFCC),
          secondary: Color(0xFF7209B7),
          surface: Color(0xFF162235),
        ),
      ),
      home: const HaloPlazaScreen(),
    );
  }
}

class HaloPlazaScreen extends StatefulWidget {
  const HaloPlazaScreen({super.key});

  @override
  State<HaloPlazaScreen> createState() => _HaloPlazaScreenState();
}

class _HaloPlazaScreenState extends State<HaloPlazaScreen> {
  // User Halo State
  double _userX = 150.0;
  double _userY = 150.0;
  final String _userHandle = "@citizen.a8f9";
  
  // Peer Halos
  final List<Map<String, dynamic>> _peers = [
    {"id": "peer_1", "handle": "@alex.creative", "x": 120.0, "y": 180.0, "color": 0xFF00FFCC, "rssi": -42},
    {"id": "peer_2", "handle": "@sarah.design", "x": 220.0, "y": 110.0, "color": 0xFF7209B7, "rssi": -58},
    {"id": "peer_3", "handle": "@dev_master", "x": 80.0, "y": 250.0, "color": 0xFF4CC9F0, "rssi": -65},
  ];

  Map<String, dynamic>? _selectedPeer;

  void _moveUser(double dx, double dy) {
    setState(() {
      _userX = (_userX + dx).clamp(20.0, 320.0);
      _userY = (_userY + dy).clamp(20.0, 320.0);
    });
    _checkProximity();
  }

  void _checkProximity() {
    for (var p in _peers) {
      double px = p['x'] as double;
      double py = p['y'] as double;
      double dist = math.sqrt(math.pow(_userX - px, 2) + math.pow(_userY - py, 2));
      if (dist < 35.0 && _selectedPeer == null) {
        _showProximityPeerSheet(p);
        break;
      }
    }
  }

  bool _handleBack() {
    if (_selectedPeer != null) {
      setState(() {
        _selectedPeer = null;
      });
      return true;
    }
    if (Navigator.canPop(context)) {
      Navigator.pop(context);
      return true;
    }
    return false;
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: !Navigator.canPop(context) && _selectedPeer == null,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) {
          _handleBack();
        }
      },
      child: KeyboardListener(
        focusNode: FocusNode()..requestFocus(),
        onKeyEvent: (KeyEvent event) {
          if (event is KeyDownEvent) {
            if (event.logicalKey == LogicalKeyboardKey.escape ||
                (event.logicalKey == LogicalKeyboardKey.arrowLeft && HardwareKeyboard.instance.isAltPressed)) {
              _handleBack();
            }
          }
        },
        child: Scaffold(
          appBar: AppBar(
            backgroundColor: const Color(0xFF121A29),
            leading: IconButton(
              icon: const Icon(Icons.arrow_back, color: Color(0xFF00FFCC)),
              tooltip: "Back (Esc / Alt+Left)",
              onPressed: _handleBack,
            ),
            title: const Text(
              'HALO PLAZA STAGE',
              style: TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold, fontSize: 16),
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.settings, color: Colors.grey),
                tooltip: "Plaza Diagnostics",
                onPressed: _showDiagnosticsSheet,
              ),
            ],
          ),
          body: Column(
            children: [
              _buildHaloTransferHeader(),
              Expanded(child: _buildPlazaCanvas()),
              _buildVirtualDPadControlBar(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHaloTransferHeader() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      color: const Color(0xFF121A29),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              const CircleAvatar(radius: 12, backgroundColor: Color(0xFF00FFCC)),
              const SizedBox(width: 8),
              Text(_userHandle, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
            ],
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFF7209B7).withOpacity(0.3),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFF7209B7)),
            ),
            child: const Text("LPE HALO: ACTIVE", style: TextStyle(color: Colors.purpleAccent, fontSize: 10, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Widget _buildPlazaCanvas() {
    return Container(
      margin: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0B101D),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF00FFCC).withOpacity(0.3)),
      ),
      child: Stack(
        children: [
          // Grid background
          CustomPaint(
            size: Size.infinite,
            painter: _GridBlueprintPainter(),
          ),
          // User Halo
          Positioned(
            left: _userX - 18,
            top: _userY - 18,
            child: Column(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: const Color(0xFF00FFCC),
                    boxShadow: [
                      BoxShadow(color: const Color(0xFF00FFCC).withOpacity(0.6), blurRadius: 10, spreadRadius: 2),
                    ],
                  ),
                  child: const Center(child: Icon(Icons.person, color: Colors.black, size: 20)),
                ),
                const SizedBox(height: 2),
                const Text("YOU", style: TextStyle(color: Color(0xFF00FFCC), fontSize: 9, fontWeight: FontWeight.bold)),
              ],
            ),
          ),
          // Peer Halos
          ..._peers.map((p) => Positioned(
                left: (p['x'] as double) - 16,
                top: (p['y'] as double) - 16,
                child: GestureDetector(
                  onTap: () => _showProximityPeerSheet(p),
                  child: Column(
                    children: [
                      Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: Color(p['color'] as int),
                          boxShadow: [
                            BoxShadow(color: Color(p['color'] as int).withOpacity(0.5), blurRadius: 8),
                          ],
                        ),
                        child: Center(child: Text((p['handle'] as String)[1].toUpperCase(), style: const TextStyle(color: Colors.black, fontWeight: FontWeight.bold))),
                      ),
                      const SizedBox(height: 2),
                      Text(p['handle'] as String, style: const TextStyle(color: Colors.grey, fontSize: 8)),
                    ],
                  ),
                ),
              )),
        ],
      ),
    );
  }

  Widget _buildVirtualDPadControlBar() {
    return Container(
      padding: const EdgeInsets.all(16),
      color: const Color(0xFF121A29),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text("Virtual Joystick Navigation", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
              Text("Move Halo into peer proximity rings", style: TextStyle(color: Colors.grey, fontSize: 10)),
            ],
          ),
          Row(
            children: [
              IconButton(icon: const Icon(Icons.arrow_back, color: Color(0xFF00FFCC)), onPressed: () => _moveUser(-15, 0)),
              Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(icon: const Icon(Icons.arrow_upward, color: Color(0xFF00FFCC)), onPressed: () => _moveUser(0, -15)),
                  IconButton(icon: const Icon(Icons.arrow_downward, color: Color(0xFF00FFCC)), onPressed: () => _moveUser(0, 15)),
                ],
              ),
              IconButton(icon: const Icon(Icons.arrow_forward, color: Color(0xFF00FFCC)), onPressed: () => _moveUser(15, 0)),
            ],
          ),
        ],
      ),
    );
  }

  void _showProximityPeerSheet(Map<String, dynamic> peer) {
    setState(() => _selectedPeer = peer);
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF162235),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text("Proximity Peer: ${peer['handle']}", style: const TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold, fontSize: 15)),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(color: Colors.greenAccent.withOpacity(0.2), borderRadius: BorderRadius.circular(6)),
                    child: Text("Signal: ${peer['rssi']} dBm", style: const TextStyle(color: Colors.greenAccent, fontSize: 10)),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const Text("Hardware Attestation: Stargate Ed25519 (Pass)", style: TextStyle(color: Colors.white70, fontSize: 12)),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () {
                        Navigator.pop(context);
                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Initiated P2P trade request with ${peer['handle']}")));
                      },
                      icon: const Icon(Icons.swap_horiz, color: Colors.black, size: 16),
                      label: const Text("P2P Item Trade", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 11)),
                      style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00FFCC)),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () {
                        Navigator.pop(context);
                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Opened direct chat session with ${peer['handle']}")));
                      },
                      icon: const Icon(Icons.chat, color: Colors.white, size: 16),
                      label: const Text("Direct Chat", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 11)),
                      style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF7209B7)),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  void _showDiagnosticsSheet() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF162235),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text("Plaza Mesh & Render Diagnostics", style: TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold, fontSize: 15)),
              const SizedBox(height: 12),
              const Text("Wi-Fi Aware & BLE Mesh: 3 Connected Peers", style: TextStyle(color: Colors.white, fontSize: 12)),
              const Text("LPE Vector Rendering: 60 FPS (Sub-1ms Frame Time)", style: TextStyle(color: Colors.greenAccent, fontSize: 12)),
              const Text("Local Merkle Sync: In-Sync (0x8F92A1...)", style: TextStyle(color: Colors.grey, fontSize: 12)),
            ],
          ),
        );
      },
    );
  }
}

class _GridBlueprintPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFF00FFCC).withOpacity(0.08)
      ..strokeWidth = 1.0;

    double step = 25.0;
    for (double x = 0; x < size.width; x += step) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y < size.height; y += step) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
