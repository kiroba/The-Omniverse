// ignore_for_file: unused_field
// ============================================================================
// THE OMNIVERSE & THE KICKBACK: HALO PLAZA (LPE PLAZA) EXPERIENCE
// Target Module: `com.kickback.halo_plaza`
// File: `mobile/lib/halo_plaza_experience_ui.dart`
// ============================================================================
// Complete, Production-Grade Interactive Flutter UI Showcase.
// Integrates the Live Persona Engine (LPE) "Halo" transfers into a shared
// interactive Plaza space, driven by local Wi-Fi Aware & BLE Mesh discovery.
// ============================================================================

import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

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
          surface: Color(0xFF131C2E),
        ),
      ),
      home: const HaloPlazaScreen(),
    );
  }
}

/// Data Model for a Peer's Live Persona ("Halo") in the Plaza
class PeerHalo {
  final String id;
  final String handle;
  final String pubkey;
  final String auraColorHex;
  final String currentCosmetic;
  final double reputationScore;
  double x;
  double y;
  double targetX;
  double targetY;
  final bool isHardwareAttested;
  final int rssi; // BLE Signal Strength dBm

  PeerHalo({
    required this.id,
    required this.handle,
    required this.pubkey,
    required this.auraColorHex,
    required this.currentCosmetic,
    required this.reputationScore,
    required this.x,
    required this.y,
    required this.targetX,
    required this.targetY,
    this.isHardwareAttested = true,
    required this.rssi,
  });
}

class HaloPlazaScreen extends StatefulWidget {
  const HaloPlazaScreen({super.key});

  @override
  State<HaloPlazaScreen> createState() => _HaloPlazaScreenState();
}

class _HaloPlazaScreenState extends State<HaloPlazaScreen>
    with TickerProviderStateMixin {
  // Local User's Halo State
  final String _userHandle = "@citizen.a8f9";
  final String _userPubkey = "0x8F92A1B439C0E71D";
  double _userX = 180.0;
  double _userY = 220.0;
  int _omniCredits = 4500;
  double _usdBalance = 185.20;
  String _equippedHat = "Neon Cyber Visor";
  String _equippedAura = "Emerald Enclave Glow";

  // Peer Halos discovered via Wi-Fi Aware & BLE Mesh
  List<PeerHalo> _peers = [];
  PeerHalo? _selectedPeer;
  Timer? _movementTimer;
  Timer? _meshDiscoveryTimer;
  int _activeMeshPeersCount = 4;
  bool _isBleActive = true;
  bool _isWifiAwareActive = true;

  // Selected Superapp Portal
  String? _activePortalName;

  @override
  void initState() {
    super.initState();
    _initializeMockPeers();
    _startPlazaSimulation();
  }

  @override
  void dispose() {
    _movementTimer?.cancel();
    _meshDiscoveryTimer?.cancel();
    super.dispose();
  }

  void _initializeMockPeers() {
    _peers = [
      PeerHalo(
        id: "peer_01",
        handle: "@alex_creator",
        pubkey: "0x3A2190B1",
        auraColorHex: "0xFF00FFCC",
        currentCosmetic: "Gold Crown & Wings",
        reputationScore: 99.4,
        x: 80.0,
        y: 120.0,
        targetX: 90.0,
        targetY: 140.0,
        rssi: -42,
      ),
      PeerHalo(
        id: "peer_02",
        handle: "@maya_artist",
        pubkey: "0x89A312F4",
        auraColorHex: "0xFFF72585",
        currentCosmetic: "Cyberpunk Mask",
        reputationScore: 98.2,
        x: 280.0,
        y: 100.0,
        targetX: 260.0,
        targetY: 120.0,
        rssi: -58,
      ),
      PeerHalo(
        id: "peer_03",
        handle: "@dev_node_99",
        pubkey: "0x77F102A9",
        auraColorHex: "0xFF3A86EF",
        currentCosmetic: "Holographic Visor",
        reputationScore: 95.0,
        x: 100.0,
        y: 300.0,
        targetX: 120.0,
        targetY: 280.0,
        rssi: -65,
      ),
      PeerHalo(
        id: "peer_04",
        handle: "@sam_builder",
        pubkey: "0x12BC88D1",
        auraColorHex: "0xFFFFB703",
        currentCosmetic: "Solar Cape",
        reputationScore: 97.8,
        x: 290.0,
        y: 280.0,
        targetX: 270.0,
        targetY: 290.0,
        rssi: -51,
      ),
    ];
  }

  void _startPlazaSimulation() {
    // Smooth wander movements for Peer Halos
    _movementTimer = Timer.periodic(const Duration(milliseconds: 80), (timer) {
      if (!mounted) return;
      setState(() {
        final rnd = math.Random();
        for (var peer in _peers) {
          // Lerp position towards target
          peer.x += (peer.targetX - peer.x) * 0.08;
          peer.y += (peer.targetY - peer.y) * 0.08;

          // Occasionally pick a new target within bounds
          if ((peer.x - peer.targetX).abs() < 5 &&
              (peer.y - peer.targetY).abs() < 5) {
            if (rnd.nextDouble() < 0.3) {
              peer.targetX = 40.0 + rnd.nextDouble() * 280.0;
              peer.targetY = 60.0 + rnd.nextDouble() * 280.0;
            }
          }
        }
      });
    });

    // Simulate BLE / Wi-Fi Aware peer discovery pulses
    _meshDiscoveryTimer = Timer.periodic(const Duration(seconds: 4), (timer) {
      if (!mounted) return;
      setState(() {
        _activeMeshPeersCount = 3 + math.Random().nextInt(4);
      });
    });
  }

  void _moveUserHalo(double dx, double dy) {
    setState(() {
      _userX = (_userX + dx).clamp(30.0, 330.0);
      _userY = (_userY + dy).clamp(40.0, 340.0);
      _checkPortalProximity();
    });
  }

  void _checkPortalProximity() {
    // Kiosk 1: 9x9 Maze (Top Left: 60, 60)
    if ((_userX - 60).abs() < 40 && (_userY - 60).abs() < 40) {
      _activePortalName = "9x9 3D Cube Survival Maze";
    }
    // Kiosk 2: Janken AI (Top Right: 300, 60)
    else if ((_userX - 300).abs() < 40 && (_userY - 60).abs() < 40) {
      _activePortalName = "Janken Markov AI Arena";
    }
    // Kiosk 3: Spades Lounge (Bottom Left: 60, 320)
    else if ((_userX - 60).abs() < 40 && (_userY - 320).abs() < 40) {
      _activePortalName = "Spades Lounge & Social Table";
    }
    // Kiosk 4: Idle Skilling (Bottom Right: 300, 320)
    else if ((_userX - 300).abs() < 40 && (_userY - 320).abs() < 40) {
      _activePortalName = "Idle Plaza XP Generator";
    } else {
      _activePortalName = null;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.hub, color: Color(0xFF00FFCC), size: 20),
            SizedBox(width: 8),
            Text(
              "HALO PLAZA SHOWCASE",
              style: TextStyle(
                  color: Color(0xFF00FFCC),
                  fontWeight: FontWeight.bold,
                  fontSize: 16),
            ),
          ],
        ),
        backgroundColor: const Color(0xFF131C2E),
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(
              Icons.bluetooth_connected,
              color: _isBleActive ? const Color(0xFF00FFCC) : Colors.grey,
            ),
            tooltip: "BLE GATT Mesh Active",
            onPressed: () => setState(() => _isBleActive = !_isBleActive),
          ),
          IconButton(
            icon: Icon(
              Icons.wifi_tethering,
              color: _isWifiAwareActive ? const Color(0xFF38BDF8) : Colors.grey,
            ),
            tooltip: "Wi-Fi Aware NAN Cluster Active",
            onPressed: () =>
                setState(() => _isWifiAwareActive = !_isWifiAwareActive),
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // 1. User Halo Transfer Header Card
            _buildHaloTransferHeader(),

            // 2. Main Interactive Plaza Canvas Stage
            _buildPlazaStage(),

            // 3. Proximity D-Pad Controls & Portal Action Banner
            _buildControlBar(),

            // 4. Live P2P Mesh Telemetry & Superapp Status
            _buildMeshTelemetryCard(),
          ],
        ),
      ),
    );
  }

  Widget _buildHaloTransferHeader() {
    return Container(
      margin: const EdgeInsets.all(12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF131C2E),
        borderRadius: BorderRadius.circular(12),
        border:
            Border.all(color: const Color(0xFF00FFCC).withValues(alpha: 0.4)),
      ),
      child: Row(
        children: [
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: const Color(0xFF00FFCC).withValues(alpha: 0.2),
              border: Border.all(color: const Color(0xFF00FFCC), width: 2),
            ),
            child: const Center(
              child: Icon(Icons.person, color: Color(0xFF00FFCC), size: 28),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      _userHandle,
                      style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 15),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF7209B7).withValues(alpha: 0.6),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text(
                        "HALO TRANSFER ACTIVE",
                        style: TextStyle(
                            color: Colors.white,
                            fontSize: 9,
                            fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  "Cosmetics: $_equippedHat | Aura: $_equippedAura",
                  style: const TextStyle(color: Colors.white60, fontSize: 11),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                "$_omniCredits OC",
                style: const TextStyle(
                    color: Color(0xFF00FFCC),
                    fontWeight: FontWeight.bold,
                    fontSize: 14),
              ),
              Text(
                "\$${_usdBalance.toStringAsFixed(2)} USD",
                style: const TextStyle(color: Colors.greenAccent, fontSize: 11),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPlazaStage() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12),
      height: 380,
      width: double.infinity,
      decoration: BoxDecoration(
        color: const Color(0xFF0A0E1A),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF1E293B), width: 2),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF00FFCC).withValues(alpha: 0.05),
            blurRadius: 15,
            spreadRadius: 2,
          )
        ],
      ),
      child: Stack(
        children: [
          // Background Grid Blueprint
          CustomPaint(
            size: Size.infinite,
            painter: _GridBlueprintPainter(),
          ),

          // Portal Kiosks
          _buildPortalKiosk(
              60, 60, "9x9 Maze", Colors.greenAccent, Icons.grid_view),
          _buildPortalKiosk(
              300, 60, "Janken AI", Colors.amberAccent, Icons.casino),
          _buildPortalKiosk(60, 320, "Spades", Colors.cyanAccent, Icons.style),
          _buildPortalKiosk(
              300, 320, "Idle Plaza", Colors.purpleAccent, Icons.bolt),

          // Peer Halos Discovered in Mesh
          for (var peer in _peers)
            Positioned(
              left: peer.x - 22,
              top: peer.y - 22,
              child: GestureDetector(
                onTap: () => _showPeerInteractionSheet(peer),
                child: Column(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Color(int.parse(peer.auraColorHex))
                            .withValues(alpha: 0.2),
                        border: Border.all(
                            color: Color(int.parse(peer.auraColorHex)),
                            width: 2),
                        boxShadow: [
                          BoxShadow(
                            color: Color(int.parse(peer.auraColorHex))
                                .withValues(alpha: 0.4),
                            blurRadius: 10,
                          )
                        ],
                      ),
                      child: Center(
                        child: Text(
                          peer.handle.substring(1, 3).toUpperCase(),
                          style: TextStyle(
                            color: Color(int.parse(peer.auraColorHex)),
                            fontWeight: FontWeight.bold,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 2),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 4, vertical: 1),
                      decoration: BoxDecoration(
                        color: Colors.black87,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        peer.handle,
                        style:
                            const TextStyle(color: Colors.white, fontSize: 9),
                      ),
                    ),
                  ],
                ),
              ),
            ),

          // User's Local Halo
          Positioned(
            left: _userX - 26,
            top: _userY - 26,
            child: Column(
              children: [
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: const Color(0xFF00FFCC).withValues(alpha: 0.3),
                    border:
                        Border.all(color: const Color(0xFF00FFCC), width: 3),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0xFF00FFCC),
                        blurRadius: 14,
                        spreadRadius: 1,
                      )
                    ],
                  ),
                  child: const Center(
                    child: Icon(Icons.star, color: Color(0xFF00FFCC), size: 24),
                  ),
                ),
                const SizedBox(height: 2),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0xFF00FFCC),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Text(
                    "YOU (HALO)",
                    style: TextStyle(
                        color: Colors.black,
                        fontSize: 9,
                        fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPortalKiosk(
      double x, double y, String label, Color color, IconData icon) {
    return Positioned(
      left: x - 30,
      top: y - 30,
      child: Container(
        width: 60,
        height: 60,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          color: color.withValues(alpha: 0.15),
          border: Border.all(color: color.withValues(alpha: 0.6), width: 1.5),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 20),
            const SizedBox(height: 2),
            Text(
              label,
              style: TextStyle(
                  color: color, fontSize: 8, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildControlBar() {
    return Container(
      margin: const EdgeInsets.all(12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF131C2E),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          // Directional D-Pad Controls
          Column(
            children: [
              IconButton(
                icon: const Icon(Icons.arrow_drop_up, color: Color(0xFF00FFCC)),
                onPressed: () => _moveUserHalo(0, -20),
              ),
              Row(
                children: [
                  IconButton(
                    icon:
                        const Icon(Icons.arrow_left, color: Color(0xFF00FFCC)),
                    onPressed: () => _moveUserHalo(-20, 0),
                  ),
                  const Icon(Icons.touch_app, color: Colors.white54, size: 16),
                  IconButton(
                    icon:
                        const Icon(Icons.arrow_right, color: Color(0xFF00FFCC)),
                    onPressed: () => _moveUserHalo(20, 0),
                  ),
                ],
              ),
              IconButton(
                icon:
                    const Icon(Icons.arrow_drop_down, color: Color(0xFF00FFCC)),
                onPressed: () => _moveUserHalo(0, 20),
              ),
            ],
          ),
          const SizedBox(width: 16),
          Expanded(
            child: _activePortalName == null
                ? const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        "PLAZA NAVIGATOR",
                        style: TextStyle(
                            color: Color(0xFF00FFCC),
                            fontWeight: FontWeight.bold,
                            fontSize: 12),
                      ),
                      SizedBox(height: 4),
                      Text(
                        "Move your Halo near peers to interact or step onto a Kiosk Pad to launch Superapp Mini-Apps over P2P mesh.",
                        style: TextStyle(color: Colors.white60, fontSize: 10),
                      ),
                    ],
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "PORTAL DETECTED:",
                        style: const TextStyle(
                            color: Colors.amberAccent,
                            fontSize: 10,
                            fontWeight: FontWeight.bold),
                      ),
                      Text(
                        _activePortalName!,
                        style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 14),
                      ),
                      const SizedBox(height: 6),
                      ElevatedButton.icon(
                        onPressed: () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(
                                  "Launching $_activePortalName over local P2P mesh!"),
                              backgroundColor: const Color(0xFF7209B7),
                            ),
                          );
                        },
                        icon: const Icon(Icons.rocket_launch,
                            size: 14, color: Colors.black),
                        label: const Text("ENTER MINI-APP ARENA",
                            style: TextStyle(
                                color: Colors.black,
                                fontWeight: FontWeight.bold,
                                fontSize: 11)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF00FFCC),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 6),
                        ),
                      ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildMeshTelemetryCard() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF131C2E),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                "P2P MESH & PLAZA TELEMETRY",
                style: TextStyle(
                    color: Colors.white70,
                    fontSize: 11,
                    fontWeight: FontWeight.bold),
              ),
              Text(
                "127.0.0.1:9200 IN-SYNC",
                style: TextStyle(
                    color: Color(0xFF00FFCC),
                    fontSize: 10,
                    fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildTelemetryMetric("DISCOVERED HALOS",
                  "$_activeMeshPeersCount Peers", Colors.cyanAccent),
              _buildTelemetryMetric(
                  "BLE RSSI", "-48 dBm Avg", Colors.greenAccent),
              _buildTelemetryMetric(
                  "FRAME LATENCY", "7.2 ms (120 FPS)", Colors.purpleAccent),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTelemetryMetric(String label, String val, Color col) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: Colors.white38, fontSize: 9)),
        Text(val,
            style: TextStyle(
                color: col, fontWeight: FontWeight.bold, fontSize: 11)),
      ],
    );
  }

  void _showPeerInteractionSheet(PeerHalo peer) {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF131C2E),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: Color(int.parse(peer.auraColorHex))
                          .withValues(alpha: 0.3),
                      border: Border.all(
                          color: Color(int.parse(peer.auraColorHex)), width: 2),
                    ),
                    child: Center(
                      child: Text(
                        peer.handle.substring(1, 3).toUpperCase(),
                        style: TextStyle(
                            color: Color(int.parse(peer.auraColorHex)),
                            fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            peer.handle,
                            style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 16),
                          ),
                          const SizedBox(width: 6),
                          const Icon(Icons.shield,
                              color: Color(0xFF00FFCC), size: 16),
                        ],
                      ),
                      Text(
                        "Key: ${peer.pubkey} | Reputation: ${peer.reputationScore}%",
                        style: const TextStyle(
                            color: Colors.white54, fontSize: 11),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFF090D16),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text("Equipped Item: ${peer.currentCosmetic}",
                        style: const TextStyle(
                            color: Colors.white70, fontSize: 12)),
                    const Text("98% Creator Split",
                        style: TextStyle(
                            color: Color(0xFF00FFCC),
                            fontSize: 10,
                            fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () {
                        Navigator.pop(context);
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                                "Tipped 50 OmniCredits to ${peer.handle}!"),
                            backgroundColor: const Color(0xFF00FFCC),
                          ),
                        );
                      },
                      icon: const Icon(Icons.card_giftcard,
                          size: 16, color: Colors.black),
                      label: const Text("TIP 50 OC",
                          style: TextStyle(
                              color: Colors.black,
                              fontWeight: FontWeight.bold)),
                      style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF00FFCC)),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () {
                        Navigator.pop(context);
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content:
                                Text("Initiated P2P Trade with ${peer.handle}"),
                            backgroundColor: const Color(0xFF7209B7),
                          ),
                        );
                      },
                      icon: const Icon(Icons.swap_horiz,
                          size: 16, color: Color(0xFF00FFCC)),
                      label: const Text("P2P TRADE",
                          style: TextStyle(color: Color(0xFF00FFCC))),
                      style: OutlinedButton.styleFrom(
                          side: const BorderSide(color: Color(0xFF00FFCC))),
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
}

class _GridBlueprintPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFF1E293B).withValues(alpha: 0.5)
      ..strokeWidth = 1.0;

    const double step = 25.0;
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
