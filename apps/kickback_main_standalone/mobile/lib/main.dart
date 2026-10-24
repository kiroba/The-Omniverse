// ignore_for_file: unused_field
// ============================================================================
// THE KICKBACK & OMNIVERSE: MODULAR COMPONENT-DRIVEN APPLICATION SHELL (V4)
// Target File: mobile/lib/main.dart
// Version: 4.0.0 - Socioboard B2B Gateway & Windows Back Navigation Edition
// Package: com.omniverse.core_engines / com.kickback
// ============================================================================

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

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
  final List<int> _tabHistory = [0]; // Back navigation history stack
  Map<String, dynamic>? _selectedPostDetail; // Sub-view state for back button test

  final bool _isHardwareAuthenticated = true;
  final String _userHandle = "@citizen.a8f9";
  final String _pubkey = "0x8F92A1B439C0E71D";
  double _usdBalance = 142.50;
  int _omniCredits = 3250;
  int _activePeers = 6;
  String _selectedCategory = "All";
  int _selectedCamAngle = 0;

  // Socioboard 5.0 B2B Gateway State
  final List<Map<String, dynamic>> _connectedSocialAccounts = [
    {
      "platform": "Omniverse P2P Mesh",
      "handle": "@acme.corp.official",
      "icon": Icons.hub,
      "color": 0xFF00FFCC,
      "status": "VERIFIED_ENCLAVE",
      "followers": "12.4k Peers",
    },
    {
      "platform": "X / Twitter",
      "handle": "@AcmeCorpTech",
      "icon": Icons.share,
      "color": 0xFF1DA1F2,
      "status": "OAUTH2_CONNECTED",
      "followers": "85.2k",
    },
    {
      "platform": "LinkedIn Enterprise",
      "handle": "Acme Corporation",
      "icon": Icons.business,
      "color": 0xFF0A66C2,
      "status": "OAUTH2_CONNECTED",
      "followers": "44.1k",
    },
    {
      "platform": "Meta / Instagram",
      "handle": "@acmecorp.live",
      "icon": Icons.camera_alt,
      "color": 0xFFE4405F,
      "status": "OAUTH2_CONNECTED",
      "followers": "102.0k",
    },
  ];

  final List<Map<String, dynamic>> _socioboardQueue = [
    {
      "id": "sb_job_9001",
      "title": "Q4 Autonomous Supply Chain Update",
      "content": "Deploying our new P2P Merkle DAG tracking nodes across 12 regional hubs!",
      "time": "Today at 18:00",
      "status": "SCHEDULED",
      "channels": ["Omniverse P2P", "X / Twitter", "LinkedIn"],
      "enclave_signed": true,
    },
    {
      "id": "sb_job_9002",
      "title": "Creator Monetization & Tip Match",
      "content": "Matching all \$1, \$5, and \$10 tips given to verified educators this week!",
      "time": "Tomorrow at 10:00",
      "status": "DRAFT_APPROVED",
      "channels": ["Omniverse P2P", "Meta / Instagram"],
      "enclave_signed": true,
    },
  ];

  // Local state for Human Feed posts
  final List<Map<String, dynamic>> _posts = [
    {
      "id": "evt_01948a",
      "author": "@alex.creative",
      "avatar_color": 0xFF00FFCC,
      "verified_human": true,
      "time": "12m ago",
      "content": "Just finished live-coding the new P2P Merkle DAG sync module! Check out the stream highlights from the Halo Plaza stage.",
      "has_media": true,
      "media_type": "camera_fusion",
      "likes": 42,
      "replies": 9,
      "tips": 25.00,
    },
    {
      "id": "evt_01948b",
      "author": "@sarah.design",
      "avatar_color": 0xFF7209B7,
      "verified_human": true,
      "time": "45m ago",
      "content": "New LPE Cyberpunk Avatar Cosmetic Pack dropped in the OmniMarket! 100% vector-rendered for sub-1ms rendering.",
      "has_media": false,
      "likes": 88,
      "replies": 14,
      "tips": 60.00,
    },
    {
      "id": "evt_01948c",
      "author": "@dev_master",
      "avatar_color": 0xFF4CC9F0,
      "verified_human": true,
      "time": "2h ago",
      "content": "Offline mesh test in the subway was a success! 6 peers connected seamlessly over BLE GATT without internet access.",
      "has_media": true,
      "media_type": "mesh_diagram",
      "likes": 134,
      "replies": 28,
      "tips": 110.00,
    },
  ];

  void _switchTab(int newIndex) {
    if (_currentTabIndex != newIndex) {
      setState(() {
        _currentTabIndex = newIndex;
        _selectedPostDetail = null;
        if (_tabHistory.isEmpty || _tabHistory.last != newIndex) {
          _tabHistory.add(newIndex);
        }
      });
    }
  }

  bool _handleBack() {
    if (_selectedPostDetail != null) {
      setState(() {
        _selectedPostDetail = null;
      });
      return true;
    }
    if (_tabHistory.length > 1) {
      setState(() {
        _tabHistory.removeLast();
        _currentTabIndex = _tabHistory.last;
      });
      return true;
    }
    return false; // Exit app or default
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: _tabHistory.length <= 1 && _selectedPostDetail == null,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) {
          _handleBack();
        }
      },
      child: KeyboardListener(
        focusNode: FocusNode()..requestFocus(),
        onKeyEvent: (KeyEvent event) {
          if (event is KeyDownEvent) {
            // Check for Escape key or Alt+Left for Windows back button support
            if (event.logicalKey == LogicalKeyboardKey.escape ||
                (event.logicalKey == LogicalKeyboardKey.arrowLeft && HardwareKeyboard.instance.isAltPressed)) {
              _handleBack();
            }
          }
        },
        child: Scaffold(
          appBar: AppBar(
            leading: (_tabHistory.length > 1 || _selectedPostDetail != null)
                ? IconButton(
                    icon: const Icon(Icons.arrow_back, color: Color(0xFF00FFCC)),
                    tooltip: "Back (Esc / Alt+Left)",
                    onPressed: _handleBack,
                  )
                : null,
            title: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: const Color(0xFF00FFCC).withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF00FFCC)),
                  ),
                  child: const Icon(Icons.hub, color: Color(0xFF00FFCC), size: 18),
                ),
                const SizedBox(width: 10),
                Text(
                  _selectedPostDetail != null ? "POST DETAIL" : _getTabTitle(_currentTabIndex),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ],
            ),
            actions: [
              Container(
                margin: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.greenAccent.withValues(alpha: 0.4)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.account_balance_wallet, color: Colors.greenAccent, size: 14),
                    const SizedBox(width: 4),
                    Text(
                      "\$${_usdBalance.toStringAsFixed(2)}",
                      style: const TextStyle(color: Colors.greenAccent, fontWeight: FontWeight.bold, fontSize: 12),
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.settings, color: Colors.grey),
                tooltip: "Settings & Diagnostics",
                onPressed: () => _switchTab(4),
              ),
            ],
          ),
          body: _selectedPostDetail != null ? _buildPostDetailSubView() : _buildSelectedTabBody(),
          bottomNavigationBar: BottomNavigationBar(
            currentIndex: _currentTabIndex,
            onTap: _switchTab,
            type: BottomNavigationBarType.fixed,
            backgroundColor: const Color(0xFF1E293B),
            selectedItemColor: const Color(0xFF00FFCC),
            unselectedItemColor: Colors.grey,
            selectedFontSize: 11,
            unselectedFontSize: 10,
            items: const [
              BottomNavigationBarItem(icon: Icon(Icons.rss_feed), label: 'Human Feed'),
              BottomNavigationBarItem(icon: Icon(Icons.videocam), label: 'Camera Fusion'),
              BottomNavigationBarItem(icon: Icon(Icons.storefront), label: 'OmniMarket'),
              BottomNavigationBarItem(icon: Icon(Icons.business_center), label: 'B2B Gateway'),
              BottomNavigationBarItem(icon: Icon(Icons.settings_suggest), label: 'Diagnostics'),
            ],
          ),
        ),
      ),
    );
  }

  String _getTabTitle(int index) {
    switch (index) {
      case 0:
        return "THE KICKBACK";
      case 1:
        return "CAMERA FUSION";
      case 2:
        return "OMNIMARKET";
      case 3:
        return "SOCIOBOARD B2B GATEWAY";
      case 4:
        return "SETTINGS & DIAGNOSTICS";
      default:
        return "THE KICKBACK";
    }
  }

  Widget _buildSelectedTabBody() {
    switch (_currentTabIndex) {
      case 0:
        return _buildHumanFeedTab();
      case 1:
        return _buildCameraFusionTab();
      case 2:
        return _buildOmniMarketTab();
      case 3:
        return _buildSocioboardB2BGatewayTab();
      case 4:
        return _buildSettingsAndDiagnosticsTab();
      default:
        return _buildHumanFeedTab();
    }
  }

  // ============================================================================
  // TAB 0: SOVEREIGN HUMAN FEED
  // ============================================================================
  Widget _buildHumanFeedTab() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildCreatorReel(),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              "Sovereign Human Feed (100% Bot-Free)",
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFF00FFCC).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF00FFCC)),
              ),
              child: const Text("ENCLAVE SIGNED", style: TextStyle(color: Color(0xFF00FFCC), fontSize: 10, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
        const SizedBox(height: 12),
        ..._posts.map((post) => _buildHumanFeedPostCard(post)),
      ],
    );
  }

  Widget _buildCreatorReel() {
    final creators = [
      {"handle": "@alex", "color": 0xFF00FFCC, "is_live": true},
      {"handle": "@sarah", "color": 0xFF7209B7, "is_live": false},
      {"handle": "@dev_master", "color": 0xFF4CC9F0, "is_live": true},
      {"handle": "@acme.corp", "color": 0xFFFFD166, "is_live": false},
    ];

    return SizedBox(
      height: 90,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: creators.length,
        itemBuilder: (context, idx) {
          final c = creators[idx];
          return Container(
            margin: const EdgeInsets.only(right: 14),
            child: Column(
              children: [
                Stack(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(2),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: (c['is_live'] as bool) ? const Color(0xFF00FFCC) : Colors.grey,
                          width: 2,
                        ),
                      ),
                      child: CircleAvatar(
                        radius: 26,
                        backgroundColor: Color(c['color'] as int),
                        child: Text(
                          (c['handle'] as String)[1].toUpperCase(),
                          style: const TextStyle(color: Colors.black, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ),
                    if (c['is_live'] as bool)
                      Positioned(
                        bottom: 0,
                        right: 4,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                          decoration: BoxDecoration(
                            color: Colors.redAccent,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Text("LIVE", style: TextStyle(color: Colors.white, fontSize: 8, fontWeight: FontWeight.bold)),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(c['handle'] as String, style: const TextStyle(color: Colors.grey, fontSize: 10)),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildHumanFeedPostCard(Map<String, dynamic> post) {
    return Card(
      color: const Color(0xFF1E293B),
      margin: const EdgeInsets.only(bottom: 14),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 18,
                  backgroundColor: Color(post['avatar_color'] as int),
                  child: Text(
                    (post['author'] as String)[1].toUpperCase(),
                    style: const TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 12),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            post['author'] as String,
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                          ),
                          const SizedBox(width: 6),
                          if (post['verified_human'] as bool)
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: const Color(0xFF00FFCC).withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: const Text(
                                "[HUMAN_VERIFIED]",
                                style: TextStyle(color: Color(0xFF00FFCC), fontSize: 9, fontWeight: FontWeight.bold),
                              ),
                            ),
                        ],
                      ),
                      Text(post['time'] as String, style: const TextStyle(color: Colors.grey, fontSize: 10)),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.arrow_forward_ios, color: Colors.grey, size: 14),
                  tooltip: "Inspect Merkle Proof & Details",
                  onPressed: () {
                    setState(() {
                      _selectedPostDetail = post;
                    });
                  },
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              post['content'] as String,
              style: const TextStyle(color: Colors.white70, fontSize: 13, height: 1.4),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.favorite_border, color: Colors.grey, size: 16),
                    const SizedBox(width: 4),
                    Text("${post['likes']}", style: const TextStyle(color: Colors.grey, fontSize: 12)),
                    const SizedBox(width: 16),
                    const Icon(Icons.chat_bubble_outline, color: Colors.grey, size: 16),
                    const SizedBox(width: 4),
                    Text("${post['replies']}", style: const TextStyle(color: Colors.grey, fontSize: 12)),
                  ],
                ),
                Row(
                  children: [
                    const Text("Tip Creator: ", style: TextStyle(color: Colors.grey, fontSize: 11)),
                    _buildTipButton(post, 1.0),
                    const SizedBox(width: 4),
                    _buildTipButton(post, 5.0),
                    const SizedBox(width: 4),
                    _buildTipButton(post, 10.0),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTipButton(Map<String, dynamic> post, double amount) {
    return InkWell(
      onTap: () {
        if (_usdBalance >= amount) {
          setState(() {
            _usdBalance -= amount;
            post['tips'] = (post['tips'] as double) + amount;
          });
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text("Sent \$${amount.toStringAsFixed(0)} tip to ${post['author']}! Recorded on Merkle WAL."),
              backgroundColor: const Color(0xFF1E293B),
            ),
          );
        }
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: const Color(0xFF00FFCC).withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: const Color(0xFF00FFCC).withValues(alpha: 0.4)),
        ),
        child: Text(
          "+\$${amount.toStringAsFixed(0)}",
          style: const TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold, fontSize: 10),
        ),
      ),
    );
  }

  Widget _buildPostDetailSubView() {
    final p = _selectedPostDetail!;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Row(
          children: [
            IconButton(
              icon: const Icon(Icons.arrow_back, color: Color(0xFF00FFCC)),
              onPressed: () => setState(() => _selectedPostDetail = null),
            ),
            const SizedBox(width: 8),
            const Text("Back to Feed (Esc)", style: TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 12),
        Card(
          color: const Color(0xFF1E293B),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("Author: ${p['author']}", style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                const SizedBox(height: 8),
                Text(p['content'] as String, style: const TextStyle(color: Colors.white70, fontSize: 14)),
                const Divider(color: Colors.grey, height: 24),
                const Text("Immutable Cryptographic Audit Proof", style: TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                Text("Merkle Event ID: ${p['id']}", style: const TextStyle(color: Colors.grey, fontSize: 12, fontFamily: 'monospace')),
                Text("Author Key Fingerprint: $_pubkey", style: const TextStyle(color: Colors.grey, fontSize: 12, fontFamily: 'monospace')),
                const Text("Hardware Attestation: Android Play Integrity (Pass)", style: TextStyle(color: Colors.greenAccent, fontSize: 12)),
              ],
            ),
          ),
        ),
      ],
    );
  }

  // ============================================================================
  // TAB 1: CAMERA FUSION
  // ============================================================================
  Widget _buildCameraFusionTab() {
    final angles = ["Stage Center", "Crowd Matrix", "Backstage VIP", "Creator POV"];
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          "🎥 Live Multi-Perspective Camera Fusion",
          style: TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold, fontSize: 16),
        ),
        const SizedBox(height: 12),
        Container(
          height: 200,
          decoration: BoxDecoration(
            color: Colors.black,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF00FFCC)),
          ),
          child: Stack(
            children: [
              Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.videocam, color: Color(0xFF00FFCC), size: 48),
                    const SizedBox(height: 8),
                    Text(
                      "Active Angle: ${angles[_selectedCamAngle]}",
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                    ),
                    const Text("P2P WebRTC Stream | Sub-50ms Latency", style: TextStyle(color: Colors.grey, fontSize: 11)),
                  ],
                ),
              ),
              Positioned(
                top: 10,
                right: 10,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(color: Colors.redAccent, borderRadius: BorderRadius.circular(6)),
                  child: const Text("LIVE FUSION", style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        const Text("Select Perspective Angle:", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            childAspectRatio: 2.5,
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
          ),
          itemCount: angles.length,
          itemBuilder: (context, idx) {
            final isSel = _selectedCamAngle == idx;
            return InkWell(
              onTap: () => setState(() => _selectedCamAngle = idx),
              child: Container(
                decoration: BoxDecoration(
                  color: isSel ? const Color(0xFF00FFCC).withValues(alpha: 0.2) : const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: isSel ? const Color(0xFF00FFCC) : Colors.grey.withValues(alpha: 0.3)),
                ),
                child: Center(
                  child: Text(
                    angles[idx],
                    style: TextStyle(color: isSel ? const Color(0xFF00FFCC) : Colors.white, fontWeight: FontWeight.bold),
                  ),
                ),
              ),
            );
          },
        ),
      ],
    );
  }

  // ============================================================================
  // TAB 2: OMNIMARKET
  // ============================================================================
  Widget _buildOmniMarketTab() {
    final categories = ["All", "Cosmetics", "Courses", "Tickets", "3D Assets"];
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          "🛒 OmniMarket Creator Storefront",
          style: TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold, fontSize: 16),
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 36,
          child: ListView.builder(
            scrollDirection: Axis.horizontal,
            itemCount: categories.length,
            itemBuilder: (context, idx) {
              final cat = categories[idx];
              final isSel = _selectedCategory == cat;
              return Padding(
                padding: const EdgeInsets.only(right: 8),
                child: ChoiceChip(
                  label: Text(cat),
                  selected: isSel,
                  selectedColor: const Color(0xFF00FFCC),
                  backgroundColor: const Color(0xFF1E293B),
                  labelStyle: TextStyle(color: isSel ? Colors.black : Colors.white, fontWeight: FontWeight.bold),
                  onSelected: (selected) => setState(() => _selectedCategory = cat),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 16),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          childAspectRatio: 0.85,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          children: [
            _buildMarketItem("LPE Cyberpunk Aura", "1,200 OmniCredits", Icons.brush, Colors.cyanAccent),
            _buildMarketItem("P2P Systems Course Pass", "\$49.99 USD", Icons.school, Colors.amberAccent),
            _buildMarketItem("Halo Stage VIP Pass", "2,500 OmniCredits", Icons.confirmation_number, Colors.purpleAccent),
            _buildMarketItem("3D Cube Maze Shader", "\$15.00 USD", Icons.view_in_ar, Colors.greenAccent),
          ],
        ),
      ],
    );
  }

  Widget _buildMarketItem(String title, String price, IconData icon, Color accent) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: accent.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Center(child: Icon(icon, color: accent, size: 36)),
            ),
          ),
          const SizedBox(height: 8),
          Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
          const SizedBox(height: 4),
          Text(price, style: TextStyle(color: accent, fontWeight: FontWeight.bold, fontSize: 11)),
        ],
      ),
    );
  }

  // ============================================================================
  // TAB 3: SOCIOBOARD B2B GATEWAY
  // ============================================================================
  Widget _buildSocioboardB2BGatewayTab() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              "🏢 Socioboard 5.0 B2B Enterprise Gateway",
              style: TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold, fontSize: 15),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.greenAccent.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.greenAccent),
              ),
              child: const Text("127.0.0.1:9200 IPC ONLINE", style: TextStyle(color: Colors.greenAccent, fontSize: 9, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Card(
          color: const Color(0xFF1E293B),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: const Color(0xFF00FFCC).withValues(alpha: 0.3)),
          ),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text("Connected Brand Social Accounts", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                const SizedBox(height: 10),
                ..._connectedSocialAccounts.map((acc) => Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Row(
                        children: [
                          Icon(acc['icon'] as IconData, color: Color(acc['color'] as int), size: 20),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(acc['platform'] as String, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
                                Text(acc['handle'] as String, style: const TextStyle(color: Colors.grey, fontSize: 11)),
                              ],
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: Color(acc['color'] as int).withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              acc['status'] as String,
                              style: TextStyle(color: Color(acc['color'] as int), fontSize: 9, fontWeight: FontWeight.bold),
                            ),
                          ),
                        ],
                      ),
                    )),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text("Scheduled Syndication Queue", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
            ElevatedButton.icon(
              onPressed: _showCreateSyndicatedPostDialog,
              icon: const Icon(Icons.add, size: 16, color: Colors.black),
              label: const Text("New Post", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 11)),
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00FFCC)),
            ),
          ],
        ),
        const SizedBox(height: 10),
        ..._socioboardQueue.map((job) => Card(
              color: const Color(0xFF1E293B),
              margin: const EdgeInsets.only(bottom: 10),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(job['title'] as String, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0xFF7209B7).withValues(alpha: 0.3),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(job['status'] as String, style: const TextStyle(color: Colors.purpleAccent, fontSize: 9, fontWeight: FontWeight.bold)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(job['content'] as String, style: const TextStyle(color: Colors.white70, fontSize: 12)),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 6,
                      children: (job['channels'] as List<String>)
                          .map((ch) => Chip(
                                label: Text(ch, style: const TextStyle(fontSize: 9, color: Colors.white)),
                                backgroundColor: const Color(0xFF0F172A),
                                visualDensity: VisualDensity.compact,
                              ))
                          .toList(),
                    ),
                  ],
                ),
              ),
            )),
      ],
    );
  }

  void _showCreateSyndicatedPostDialog() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1E293B),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text("Broadcast Syndicated Post via Socioboard 5.0", style: TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold, fontSize: 15)),
              const SizedBox(height: 12),
              const TextField(
                decoration: InputDecoration(
                  hintText: "Enter brand announcement text...",
                  filled: true,
                  fillColor: Color(0xFF0F172A),
                  border: OutlineInputBorder(),
                ),
                maxLines: 3,
              ),
              const SizedBox(height: 12),
              const Text("Target Channels:", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
              const SizedBox(height: 6),
              const Wrap(
                spacing: 8,
                children: [
                  FilterChip(label: Text("Omniverse P2P"), selected: true, onSelected: null),
                  FilterChip(label: Text("X / Twitter"), selected: true, onSelected: null),
                  FilterChip(label: Text("LinkedIn"), selected: true, onSelected: null),
                  FilterChip(label: Text("Meta / Instagram"), selected: false, onSelected: null),
                ],
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () {
                    Navigator.pop(context);
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text("Broadcast dispatched to Web2 APIs and local P2P mesh!"),
                        backgroundColor: Color(0xFF1E293B),
                      ),
                    );
                  },
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00FFCC)),
                  child: const Text("ENCLAVE SIGN & BROADCAST NOW", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  // ============================================================================
  // TAB 4: SETTINGS & DIAGNOSTICS
  // ============================================================================
  Widget _buildSettingsAndDiagnosticsTab() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          "⚙ System Diagnostics & Settings",
          style: TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold, fontSize: 16),
        ),
        const SizedBox(height: 12),
        Card(
          color: const Color(0xFF1E293B),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text("Hardware Security Enclave", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                _buildDiagRow("Public Key Fingerprint", _pubkey, Colors.cyanAccent),
                _buildDiagRow("Hardware Remote Attestation", "Android Play Integrity (Pass)", Colors.greenAccent),
                _buildDiagRow("Sovereign Handle", _userHandle, Colors.white),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          color: const Color(0xFF1E293B),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text("Local P2P Mesh & Daemon Health", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                _buildDiagRow("IPC Gateway Port", "127.0.0.1:9200", Colors.amberAccent),
                _buildDiagRow("Active Mesh Peers", "$_activePeers Peers (Wi-Fi Aware / BLE)", Colors.greenAccent),
                _buildDiagRow("Local SQLite WAL Store", "omni_hub_immutable.db (OK)", Colors.cyanAccent),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDiagRow(String label, String val, Color valColor) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey, fontSize: 11)),
          Text(val, style: TextStyle(color: valColor, fontWeight: FontWeight.bold, fontSize: 11, fontFamily: 'monospace')),
        ],
      ),
    );
  }
}
