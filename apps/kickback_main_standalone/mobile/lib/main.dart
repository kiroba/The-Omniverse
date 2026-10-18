// ============================================================================
// THE KICKBACK & OMNIVERSE: COMPLETE MULTI-TAB APPLICATION MAIN ENTRYPOINT
// Target File: mobile/lib/main.dart
// Package: com.omniverse.core_engines / com.kickback
// ============================================================================

import 'package:flutter/material.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const KickBackMainApp());
}

class KickBackMainApp extends StatelessWidget {
  const KickBackMainApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'The KickBack',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0F172A), // Dark Slate
        primaryColor: const Color(0xFF00FFCC), // Neon Cyan
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00FFCC),
          secondary: Color(0xFF7209B7),
          surface: Color(0xFF1E293B),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF1E293B),
          elevation: 0,
        ),
      ),
      home: const KickBackAppShell(),
    );
  }
}

class KickBackAppShell extends StatefulWidget {
  const KickBackAppShell({super.key});

  @override
  State<KickBackAppShell> createState() => _KickBackAppShellState();
}

class _KickBackAppShellState extends State<KickBackAppShell> {
  int _currentTabIndex = 0;
  bool _isHardwareAuthenticated = true;
  String _userHandle = "@citizen.a8f9";
  String _pubkey = "0x8F92A1B439C0E71D";
  double _usdBalance = 142.50;
  int _omniCredits = 3250;
  int _activePeers = 6;
  int _secretTapCount = 0;

  // Local state for Human Feed posts
  final List<Map<String, dynamic>> _posts = [
    {
      "id": "evt_01948a",
      "author": "@alex_creator",
      "badge": "HUMAN_VERIFIED",
      "content": "Just launched the new multi-perspective live stream for tonight's concert! Switch between 4 camera angles in real time over P2P mesh.",
      "timestamp": "2 mins ago",
      "likes": 24,
      "tipsUSD": 15.00,
      "merkleHash": "0x0185D7BE92C4",
    },
    {
      "id": "evt_01948b",
      "author": "@maya_artist",
      "badge": "HUMAN_VERIFIED",
      "content": "Updated my OmniMarket creator store with new 3D avatar cosmetics. 98% creator payout directly into my hardware enclave wallet!",
      "timestamp": "14 mins ago",
      "likes": 42,
      "tipsUSD": 38.50,
      "merkleHash": "0x89A312F401BC",
    },
    {
      "id": "evt_01948c",
      "author": "@dev_node_01",
      "badge": "SYSTEM_INFO",
      "content": "[P2P MESH NOTICE] 12 local Wi-Fi Aware & BLE bootnodes active. Zero cloud servers required.",
      "timestamp": "1 hour ago",
      "likes": 89,
      "tipsUSD": 0.00,
      "merkleHash": "0x77F102A911DE",
    },
  ];

  void _addNewPost(String content) {
    if (content.trim().isEmpty) return;
    setState(() {
      _posts.insert(0, {
        "id": "evt_${DateTime.now().millisecondsSinceEpoch.toRadixString(16)}",
        "author": _userHandle,
        "badge": "HUMAN_VERIFIED",
        "content": content,
        "timestamp": "Just now",
        "likes": 1,
        "tipsUSD": 0.00,
        "merkleHash": "0x${DateTime.now().microsecondsSinceEpoch.toRadixString(16).substring(0, 12).toUpperCase()}",
      });
    });
  }

  void _showCreatePostDialog() {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: Row(
          children: const [
            Icon(Icons.edit_note, color: Color(0xFF00FFCC)),
            SizedBox(width: 8),
            Text('Create Human Feed Post', style: TextStyle(color: Colors.white, fontSize: 16)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFF00FFCC).withOpacity(0.15),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: const Color(0xFF00FFCC)),
              ),
              child: const Text('🛡 HUMAN ATTESTED (Stargate Ed25519)', style: TextStyle(color: Color(0xFF00FFCC), fontSize: 10, fontWeight: FontWeight.bold)),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              maxLines: 3,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(
                hintText: "What's happening on your mesh node?",
                hintStyle: TextStyle(color: Colors.grey),
                border: OutlineInputBorder(),
                focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: Color(0xFF00FFCC))),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel', style: TextStyle(color: Colors.grey)),
          ),
          ElevatedButton(
            onPressed: () {
              _addNewPost(controller.text);
              Navigator.pop(ctx);
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00FFCC)),
            child: const Text('Publish Post', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: GestureDetector(
          onTap: () {
            _secretTapCount++;
            if (_secretTapCount >= 5) {
              _secretTapCount = 0;
              _showEasterEggDialog();
            }
          },
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: const Color(0xFF00FFCC).withOpacity(0.2),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.hub, color: Color(0xFF00FFCC), size: 20),
              ),
              const SizedBox(width: 10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('The KickBack', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  Text('Local Mesh: $_activePeers Peers Active', style: const TextStyle(color: Colors.grey, fontSize: 11)),
                ],
              ),
            ],
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.account_balance_wallet, color: Color(0xFF00FFCC)),
            tooltip: "Hardware Wallet",
            onPressed: _showWalletDetailsModal,
          ),
          IconButton(
            icon: const Icon(Icons.security, color: Colors.amberAccent),
            tooltip: "Stargate Security Status",
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text("🛡 Stargate Ed25519 Enclave Active | Zero-Cloud Self-Sovereignty"),
                  backgroundColor: Color(0xFF162235),
                ),
              );
            },
          ),
        ],
      ),
      body: _buildSelectedTabBody(),
      floatingActionButton: _currentTabIndex == 0
          ? FloatingActionButton(
              onPressed: _showCreatePostDialog,
              backgroundColor: const Color(0xFF00FFCC),
              child: const Icon(Icons.add, color: Colors.black),
            )
          : null,
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentTabIndex,
        onTap: (index) => setState(() => _currentTabIndex = index),
        selectedItemColor: const Color(0xFF00FFCC),
        unselectedItemColor: Colors.grey,
        backgroundColor: const Color(0xFF1E293B),
        type: BottomNavigationBarType.fixed,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.dynamic_feed), label: 'Human Feed'),
          BottomNavigationBarItem(icon: Icon(Icons.videocam), label: 'Mesh Fusion'),
          BottomNavigationBarItem(icon: Icon(Icons.storefront), label: 'OmniMarket'),
          BottomNavigationBarItem(icon: Icon(Icons.terminal), label: 'Telemetry'),
        ],
      ),
    );
  }

  Widget _buildSelectedTabBody() {
    switch (_currentTabIndex) {
      case 0:
        return _buildHumanFeedTab();
      case 1:
        return _buildMeshFusionTab();
      case 2:
        return _buildOmniMarketTab();
      case 3:
        return _buildTelemetryTab();
      default:
        return _buildHumanFeedTab();
    }
  }

  // ==========================================================================
  // TAB 1: SOVEREIGN HUMAN FEED
  // ==========================================================================
  Widget _buildHumanFeedTab() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Identity Banner
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF334155)),
          ),
          child: Row(
            children: [
              const CircleAvatar(
                backgroundColor: Color(0xFF7209B7),
                child: Icon(Icons.person, color: Colors.white),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(_userHandle, style: const TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold, fontSize: 15)),
                        const SizedBox(width: 6),
                        const Icon(Icons.verified, color: Color(0xFF00FFCC), size: 14),
                      ],
                    ),
                    Text("Key: $_pubkey", style: const TextStyle(color: Colors.grey, fontSize: 11)),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text("\$${_usdBalance.toStringAsFixed(2)} USD", style: const TextStyle(color: Colors.greenAccent, fontWeight: FontWeight.bold, fontSize: 14)),
                  Text("$_omniCredits Credits", style: const TextStyle(color: Colors.white70, fontSize: 11)),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        const Text("Sovereign Human Feed (100% Bot-Free)", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
        const SizedBox(height: 10),

        ..._posts.map((post) => _buildPostCard(post)).toList(),
      ],
    );
  }

  Widget _buildPostCard(Map<String, dynamic> post) {
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
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
              Row(
                children: [
                  Text(post['author'], style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: post['badge'] == 'HUMAN_VERIFIED' ? const Color(0xFF00FFCC).withOpacity(0.15) : Colors.amber.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: post['badge'] == 'HUMAN_VERIFIED' ? const Color(0xFF00FFCC) : Colors.amber),
                    ),
                    child: Text(post['badge'], style: TextStyle(color: post['badge'] == 'HUMAN_VERIFIED' ? const Color(0xFF00FFCC) : Colors.amber, fontSize: 9, fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
              Text(post['timestamp'], style: const TextStyle(color: Colors.grey, fontSize: 11)),
            ],
          ),
          const SizedBox(height: 10),
          Text(post['content'], style: const TextStyle(color: Colors.white70, fontSize: 13, height: 1.4)),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.favorite_border, color: Colors.pinkAccent, size: 18),
                    onPressed: () {
                      setState(() => post['likes']++);
                    },
                  ),
                  Text("${post['likes']}", style: const TextStyle(color: Colors.grey, fontSize: 12)),
                  const SizedBox(width: 16),
                  IconButton(
                    icon: const Icon(Icons.monetization_on_outlined, color: Colors.greenAccent, size: 18),
                    onPressed: () {
                      setState(() {
                        post['tipsUSD'] += 1.00;
                        _usdBalance -= 1.00;
                      });
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text("Tipped \$1.00 USD to ${post['author']}"), backgroundColor: Colors.green),
                      );
                    },
                  ),
                  Text("\$${post['tipsUSD'].toStringAsFixed(2)}", style: const TextStyle(color: Colors.grey, fontSize: 12)),
                ],
              ),
              Text("DAG: ${post['merkleHash']}", style: const TextStyle(color: Colors.grey, fontSize: 10, fontFamily: 'monospace')),
            ],
          ),
        ],
      ),
    );
  }

  // ==========================================================================
  // TAB 2: MULTI-PERSPECTIVE MESH FUSION
  // ==========================================================================
  Widget _buildMeshFusionTab() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text("🎥 Live Multi-Perspective Camera Fusion", style: TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 6),
        const Text("Switch seamlessly between 4 P2P camera angles with zero cloud relay servers.", style: TextStyle(color: Colors.grey, fontSize: 12)),
        const SizedBox(height: 16),

        // Main Viewport
        Container(
          height: 200,
          decoration: BoxDecoration(
            color: Colors.black,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF00FFCC)),
          ),
          child: Stack(
            children: [
              const Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.videocam, color: Color(0xFF00FFCC), size: 48),
                    SizedBox(height: 8),
                    Text("[ ACTIVE STAGE STREAM: CAM 01 - MAIN FRONT ]", style: TextStyle(color: Color(0xFF00FFCC), fontFamily: 'monospace', fontSize: 12)),
                    Text("1080p @ 60 FPS | P2P Direct WebRTC Stream", style: TextStyle(color: Colors.grey, fontSize: 11)),
                  ],
                ),
              ),
              Positioned(
                top: 12,
                left: 12,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(color: Colors.red, borderRadius: BorderRadius.circular(4)),
                  child: const Text("LIVE P2P", style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        const Text("Select Perspective Angle:", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
        const SizedBox(height: 10),

        Row(
          children: [
            _buildCamThumbnail("Cam 1: Front", Icons.camera_front, true),
            const SizedBox(width: 8),
            _buildCamThumbnail("Cam 2: Stage Left", Icons.videocam, false),
            const SizedBox(width: 8),
            _buildCamThumbnail("Cam 3: Crowd", Icons.people, false),
            const SizedBox(width: 8),
            _buildCamThumbnail("Cam 4: Drone", Icons.air, false),
          ],
        ),
      ],
    );
  }

  Widget _buildCamThumbnail(String label, IconData icon, bool isActive) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: isActive ? const Color(0xFF00FFCC).withOpacity(0.2) : const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: isActive ? const Color(0xFF00FFCC) : const Color(0xFF334155)),
        ),
        child: Column(
          children: [
            Icon(icon, color: isActive ? const Color(0xFF00FFCC) : Colors.grey, size: 20),
            const SizedBox(height: 4),
            Text(label, style: TextStyle(color: isActive ? const Color(0xFF00FFCC) : Colors.white70, fontSize: 10, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }

  // ==========================================================================
  // TAB 3: OMNIMARKET CREATOR STOREFRONT & MINI-APPS
  // ==========================================================================
  Widget _buildOmniMarketTab() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text("🛒 OmniMarket Creator Storefront", style: TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold, fontSize: 16)),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(color: const Color(0xFF7209B7), borderRadius: BorderRadius.circular(12)),
              child: const Text("98% Creator Payout", style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
        const SizedBox(height: 16),

        _buildStoreItem("Neon Cyber Helmet", "Avatar Cosmetics", "250 Credits", Icons.security),
        _buildStoreItem("9x9 Cube Survival Pass", "Game Mini-App", "500 Credits", Icons.grid_on),
        _buildStoreItem("Spades VIP Lounge Badge", "Social Mini-App", "150 Credits", Icons.style),
        _buildStoreItem("Markov AI NPC Architect", "AI Agent License", "1,000 Credits", Icons.smart_toy),
      ],
    );
  }

  Widget _buildStoreItem(String title, String category, String price, IconData icon) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: const Color(0xFF00FFCC).withOpacity(0.15), borderRadius: BorderRadius.circular(8)),
            child: Icon(icon, color: const Color(0xFF00FFCC)),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
                Text(category, style: const TextStyle(color: Colors.grey, fontSize: 11)),
              ],
            ),
          ),
          ElevatedButton(
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text("Purchased $title for $price!"), backgroundColor: const Color(0xFF7209B7)),
              );
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00FFCC)),
            child: Text(price, style: const TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 12)),
          ),
        ],
      ),
    );
  }

  // ==========================================================================
  // TAB 4: PROCESS TELEMETRY & HARDWARE ENCLAVE
  // ==========================================================================
  Widget _buildTelemetryTab() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text("💻 Core Engine Telemetry & IPC Console", style: TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 12),

        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Colors.black,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFF334155)),
          ),
          child: const Text(
            "[SYS] Daemon Loop running on 127.0.0.1:9200\n"
            "[P2P] Wi-Fi Aware & BLE Transports: ONLINE\n"
            "[CRDT] Merkle Root: 0x0185D7BE92C4\n"
            "[AUTH] Stargate Ed25519 Hardware Enclave Key Validated\n"
            "[MARKOV] Sub-1ms CPU NPC Builder Inference Loop Active",
            style: TextStyle(color: Color(0xFF00FFCC), fontFamily: 'monospace', fontSize: 11, height: 1.5),
          ),
        ),
        const SizedBox(height: 20),

        ElevatedButton.icon(
          onPressed: _showEasterEggDialog,
          icon: const Icon(Icons.monitor, color: Colors.black),
          label: const Text('OPEN EASTER EGG MONITOR', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF00FFCC),
            padding: const EdgeInsets.symmetric(vertical: 14),
          ),
        ),
      ],
    );
  }

  void _showWalletDetailsModal() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1E293B),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => Container(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text("🔑 Stargate Hardware Wallet", style: TextStyle(color: Color(0xFF00FFCC), fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            Text("Public Key: $_pubkey", style: const TextStyle(color: Colors.grey, fontFamily: 'monospace', fontSize: 12)),
            const Divider(color: Colors.white24, height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text("USD Payout Balance:", style: TextStyle(color: Colors.white70)),
                Text("\$${_usdBalance.toStringAsFixed(2)} USD", style: const TextStyle(color: Colors.greenAccent, fontWeight: FontWeight.bold, fontSize: 16)),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text("OmniCredits Balance:", style: TextStyle(color: Colors.white70)),
                Text("$_omniCredits Credits", style: const TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold, fontSize: 16)),
              ],
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(ctx),
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00FFCC)),
                child: const Text("Close Wallet", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showEasterEggDialog() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF0A0E17),
        title: const Text('🕹 EASTER EGG UNLOCKED!', style: TextStyle(color: Color(0xFF00FFCC))),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'You unlocked the secret developer easter egg monitor! All 7 core engines are running in zero-dependency native mode.',
              style: TextStyle(color: Colors.white70, fontSize: 12),
            ),
            const SizedBox(height: 16),
            Container(
              height: 120,
              width: double.infinity,
              color: Colors.black,
              child: const Center(
                child: Text('[ 3D RAYCAST PROCESS MONITOR ]', style: TextStyle(color: Color(0xFF00FFCC), fontFamily: 'monospace')),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('OK', style: TextStyle(color: Color(0xFF00FFCC))),
          ),
        ],
      ),
    );
  }
}
