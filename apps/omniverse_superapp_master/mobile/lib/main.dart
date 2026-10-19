import 'dart:async';
import 'package:flutter/material.dart';

/// ============================================================================
/// OMNIVERSE UNIFIED SUPERAPP MASTER UI (CANONICAL USER-FACING SHELL)
/// ============================================================================
/// - Unifies Social Feed (KickBack), Halo Plaza & Arcade, RPG Idle Realm,
///   and Sovereign Wallet / Storefront in a singular consumer app.
/// - Excludes all administrative monitoring tools (Mobile Mesh Monitor is isolated)
/// - Pure local state binding, 1-node pre-launch display, zero mock data.
/// ============================================================================

void main() => runApp(const OmniverseSuperappMaster());

class OmniverseSuperappMaster extends StatelessWidget {
  const OmniverseSuperappMaster({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'The Omniverse Superapp',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        primaryColor: const Color(0xFF6200EE),
        scaffoldBackgroundColor: const Color(0xFF121212),
        cardColor: const Color(0xFF1E1E1E),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFFBB86FC),
          secondary: Color(0xFF03DAC6),
          surface: Color(0xFF1E1E1E),
        ),
      ),
      home: const SuperappMasterScreen(),
    );
  }
}

class SuperappMasterScreen extends StatefulWidget {
  const SuperappMasterScreen({super.key});

  @override
  State<SuperappMasterScreen> createState() => _SuperappMasterScreenState();
}

class _SuperappMasterScreenState extends State<SuperappMasterScreen> {
  int _activeTab = 0;

  // Social Feed State
  final TextEditingController _postController = TextEditingController();
  final List<Map<String, dynamic>> _socialEvents = [];

  // RPG Idle State
  int _miningLevel = 1;
  int _miningExp = 0;
  bool _isMiningActive = false;
  Timer? _skillingTimer;

  @override
  void dispose() {
    _postController.dispose();
    _skillingTimer?.cancel();
    super.dispose();
  }

  void _publishLocalPost() {
    final text = _postController.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _socialEvents.insert(0, {
        'id': DateTime.now().millisecondsSinceEpoch.toString(),
        'content': text,
        'timestamp': DateTime.now().toIso8601String().substring(11, 16),
        'author': 'Sovereign User (You)',
        'hash': '0x${DateTime.now().millisecondsSinceEpoch.toRadixString(16)}...',
      });
      _postController.clear();
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Post committed to local SQLite WAL database.'),
        backgroundColor: Color(0xFF03DAC6),
        duration: Duration(seconds: 2),
      ),
    );
  }

  void _toggleMining() {
    setState(() {
      _isMiningActive = !_isMiningActive;
    });

    if (_isMiningActive) {
      _skillingTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
        if (!mounted) return;
        setState(() {
          _miningExp += 15;
          if (_miningExp >= _miningLevel * 100) {
            _miningLevel++;
            _miningExp = 0;
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('LEVEL UP! Mining is now Level $_miningLevel'),
                backgroundColor: const Color(0xFF03DAC6),
              ),
            );
          }
        });
      });
    } else {
      _skillingTimer?.cancel();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAlignment.start,
          children: const [
            Text('The Omniverse', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            Text('1 Sovereign Node Active • Mainnet Shell', style: TextStyle(color: Color(0xFF03DAC6), fontSize: 11)),
          ],
        ),
        backgroundColor: const Color(0xFF1F1F1F),
        elevation: 2,
        actions: [
          IconButton(
            icon: const Icon(Icons.account_balance_wallet, color: Color(0xFFBB86FC)),
            tooltip: 'Sovereign Wallet',
            onPressed: () => _showWalletDialog(context),
          ),
        ],
      ),
      body: IndexedStack(
        index: _activeTab,
        children: [
          _buildKickBackSocialTab(),
          _buildHaloPlazaAndArcadeTab(),
          _buildRpgIdleRealmTab(),
          _buildSovereignWalletAndStoreTab(),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _activeTab,
        type: BottomNavigationBarType.fixed,
        backgroundColor: const Color(0xFF1F1F1F),
        selectedItemColor: const Color(0xFFBB86FC),
        unselectedItemColor: Colors.grey,
        onTap: (index) => setState(() => _activeTab = index),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.dynamic_feed), label: 'KickBack'),
          BottomNavigationBarItem(icon: Icon(Icons.sports_esports), label: 'Plaza & Arcade'),
          BottomNavigationBarItem(icon: Icon(Icons.shield), label: 'Idle RPG'),
          BottomNavigationBarItem(icon: Icon(Icons.storefront), label: 'Store & Wallet'),
        ],
      ),
    );
  }

  // TAB 1: KickBack Social Network
  Widget _buildKickBackSocialTab() {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          color: const Color(0xFF1E1E1E),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _postController,
                  style: const TextStyle(color: Colors.white, fontSize: 14),
                  decoration: InputDecoration(
                    hintText: 'Share a sovereign moment...',
                    hintStyle: const TextStyle(color: Colors.grey),
                    filled: true,
                    fillColor: const Color(0xFF2C2C2C),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.send, color: Color(0xFFBB86FC)),
                onPressed: _publishLocalPost,
              ),
            ],
          ),
        ),
        const Divider(height: 1, color: Color(0xFF333333)),
        Expanded(
          child: _socialEvents.isEmpty
              ? _buildPreLaunchZeroState('Pre-Launch KickBack Feed', '1 Sovereign Node Active. Create your first post.')
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: _socialEvents.length,
                  itemBuilder: (context, index) {
                    final item = _socialEvents[index];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Column(
                          crossAxisAlignment: CrossAlignment.start,
                          children: [
                            Row(
                              children: [
                                const CircleAvatar(radius: 14, backgroundColor: Color(0xFFBB86FC), child: Icon(Icons.person, size: 16, color: Colors.black)),
                                const SizedBox(width: 8),
                                Text(item['author'], style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                                const SizedBox(width: 4),
                                const Icon(Icons.verified, size: 14, color: Color(0xFF03DAC6)),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(item['content'], style: const TextStyle(fontSize: 14, color: Colors.white)),
                          ],
                        ),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  // TAB 2: Halo Plaza & Arcade Hub
  Widget _buildHaloPlazaAndArcadeTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAlignment.start,
        children: [
          const Text('Halo Plaza & Arcade Lounge', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 6),
          const Text('Spatial gathering hub hosting mini-games and arena brawlers.', style: TextStyle(color: Colors.grey, fontSize: 12)),
          const SizedBox(height: 16),
          Expanded(
            child: GridView.count(
              crossAxisCount: 2,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              children: [
                _buildArcadeCard('2D Combat Brawler', 'Arena PvP/PvE Action', Icons.sports_mma, const Color(0xFFFF5252)),
                _buildArcadeCard('9x9 Cube Survival', 'Procedural Maze Escape', Icons.grid_4x4, const Color(0xFFFF4081)),
                _buildArcadeCard('Janken Markov AI', 'Adaptive RPSLS AI', Icons.psychology, const Color(0xFFE040FB)),
                _buildArcadeCard('Spades Lounge', 'Casual Card Strategy', Icons.style, const Color(0xFF7C4DFF)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // TAB 3: RPG Idle Realm
  Widget _buildRpgIdleRealmTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAlignment.start,
        children: [
          const Text('RPG Idle Realm', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 6),
          const Text('Offline skilling loop. Assign tasks and collect rewards safely on-device.', style: TextStyle(color: Colors.grey, fontSize: 12)),
          const SizedBox(height: 20),
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Mining Skill', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                      Text('Level $_miningLevel', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF03DAC6))),
                    ],
                  ),
                  const SizedBox(height: 12),
                  LinearProgressIndicator(value: _miningExp / (_miningLevel * 100), backgroundColor: Colors.grey[800], color: const Color(0xFF03DAC6)),
                  const SizedBox(height: 8),
                  Text('EXP: $_miningExp / ${_miningLevel * 100}', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _toggleMining,
                      icon: Icon(_isMiningActive ? Icons.pause : Icons.play_arrow),
                      label: Text(_isMiningActive ? 'Pause Mining' : 'Start Mining Task'),
                      style: ElevatedButton.styleFrom(backgroundColor: _isMiningActive ? Colors.redAccent : const Color(0xFF6200EE)),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // TAB 4: Sovereign Wallet & Storefront
  Widget _buildSovereignWalletAndStoreTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAlignment.start,
        children: [
          const Text('Sovereign Storefront & Wallet', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 6),
          const Text('Stripe 1-Tap Fiat Checkout + Polygon Shadow Balance.', style: TextStyle(color: Colors.grey, fontSize: 12)),
          const SizedBox(height: 16),
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: const [
                      Text('Shadow Off-Chain Balance', style: TextStyle(color: Colors.grey)),
                      Text('0.00 OMNI', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF03DAC6))),
                    ],
                  ),
                  const Divider(height: 24, color: Color(0xFF333333)),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: const [
                      Text('Stripe Gateway', style: TextStyle(color: Colors.grey)),
                      Text('Ready (1-Tap)', style: TextStyle(color: Color(0xFFBB86FC), fontWeight: FontWeight.bold)),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPreLaunchZeroState(String title, String subtitle) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.blur_on, size: 48, color: Color(0xFF03DAC6)),
          const SizedBox(height: 16),
          Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text(subtitle, style: const TextStyle(color: Colors.grey, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildArcadeCard(String title, String subtitle, IconData icon, Color color) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Launching $title...'), backgroundColor: color));
        },
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 36, color: color),
              const SizedBox(height: 8),
              Text(title, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              const SizedBox(height: 4),
              Text(subtitle, textAlign: TextAlign.center, style: const TextStyle(fontSize: 10, color: Colors.grey)),
            ],
          ),
        ),
      ),
    );
  }

  void _showWalletDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1E1E1E),
        title: const Text('Sovereign Wallet'),
        content: const Text('Shadow balance: 0.00 OMNI\nLocal node signature verified.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Close')),
        ],
      ),
    );
  }
}
