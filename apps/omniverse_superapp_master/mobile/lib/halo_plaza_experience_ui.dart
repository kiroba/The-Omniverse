import 'dart:async';
import 'package:flutter/material.dart';

/// ============================================================================
/// HALO PLAZA & ARCADE SPATIAL HUB UI (CANONICAL - REAL-TIME SINGLE NODE)
/// ============================================================================
/// - Spatial hub hosting the Arcade Lounge (Combat Brawler, 9x9, Janken, Spades)
/// - RPG Idle Realm portal for background offline skilling
/// - Zero fake online lobbies or simulated mock players
/// - Bound to 1 sovereign player node
/// ============================================================================

void main() => runApp(const HaloPlazaApp());

class HaloPlazaApp extends StatelessWidget {
  const HaloPlazaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Halo Plaza & Arcade Hub',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        primaryColor: const Color(0xFF6200EE),
        scaffoldBackgroundColor: const Color(0xFF0F0F1A),
        cardColor: const Color(0xFF1A1A2E),
      ),
      home: const HaloPlazaMainScreen(),
    );
  }
}

class HaloPlazaMainScreen extends StatefulWidget {
  const HaloPlazaMainScreen({super.key});

  @override
  State<HaloPlazaMainScreen> createState() => _HaloPlazaMainScreenState();
}

class _HaloPlazaMainScreenState extends State<HaloPlazaMainScreen> {
  int _currentZoneIndex = 0; // 0: Plaza Hub, 1: Arcade Lounge, 2: RPG Idle Realm

  // Idle RPG Skilling State (Sovereign Local Progress)
  int _miningLevel = 1;
  int _miningExp = 0;
  bool _isMiningActive = false;
  Timer? _skillingTimer;

  @override
  void dispose() {
    _skillingTimer?.cancel();
    super.dispose();
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
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text('Halo Plaza Hub', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            Text('1 Sovereign Player Online • Local State', style: TextStyle(color: Color(0xFF03DAC6), fontSize: 11)),
          ],
        ),
        backgroundColor: const Color(0xFF16162A),
        elevation: 2,
      ),
      body: _buildCurrentZoneView(),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentZoneIndex,
        backgroundColor: const Color(0xFF16162A),
        selectedItemColor: const Color(0xFFBB86FC),
        unselectedItemColor: Colors.grey,
        onTap: (index) {
          setState(() {
            _currentZoneIndex = index;
          });
        },
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.location_city_outlined), label: 'Plaza Hub'),
          BottomNavigationBarItem(icon: Icon(Icons.sports_esports_outlined), label: 'Arcade Lounge'),
          BottomNavigationBarItem(icon: Icon(Icons.shield_outlined), label: 'RPG Idle Realm'),
        ],
      ),
    );
  }

  Widget _buildCurrentZoneView() {
    switch (_currentZoneIndex) {
      case 1:
        return _buildArcadeLoungeView();
      case 2:
        return _buildRpgIdleRealmView();
      case 0:
      default:
        return _buildPlazaHubView();
    }
  }

  Widget _buildPlazaHubView() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF2E1A47), Color(0xFF1A1A2E)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFBB86FC).withOpacity(0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Text(
                  'Welcome to Halo Plaza',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                SizedBox(height: 8),
                Text(
                  'The central gathering ground for spatial interaction, Arcade mini-games, and RPG skilling. Pre-launch local node active.',
                  style: TextStyle(color: Colors.grey, fontSize: 13, height: 1.4),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          const Text('Plaza Gathering Destinations', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 12),
          Expanded(
            child: ListView(
              children: [
                _buildDestinationTile(
                  title: 'Arcade Lounge',
                  subtitle: '2D Combat Brawler, 9x9 Maze, Janken AI, Spades',
                  icon: Icons.sports_esports,
                  color: const Color(0xFFBB86FC),
                  onTap: () => setState(() => _currentZoneIndex = 1),
                ),
                _buildDestinationTile(
                  title: 'RPG Idle Realm',
                  subtitle: 'Offline Skilling (Mining, Woodcutting, Smithing, Slayer)',
                  icon: Icons.fort_outlined,
                  color: const Color(0xFF03DAC6),
                  onTap: () => setState(() => _currentZoneIndex = 2),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildArcadeLoungeView() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Arcade Lounge Mini-Games', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 6),
          const Text('All skill-based mini-games run locally on your sovereign engine.', style: TextStyle(color: Colors.grey, fontSize: 12)),
          const SizedBox(height: 16),
          Expanded(
            child: GridView.count(
              crossAxisCount: 2,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              children: [
                _buildArcadeGameCard('2D Combat Brawler', 'Arena PvP/PvE Action', Icons.sports_mma, const Color(0xFFFF5252)),
                _buildArcadeGameCard('9x9 Cube Survival', 'Procedural Maze Escape', Icons.grid_4x4, const Color(0xFFFF4081)),
                _buildArcadeGameCard('Janken Markov AI', 'Adaptive RPSLS AI', Icons.psychology, const Color(0xFFE040FB)),
                _buildArcadeGameCard('Spades Lounge', 'Casual Card Strategy', Icons.style, const Color(0xFF7C4DFF)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRpgIdleRealmView() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('RPG Idle Realm - Skilling Hub', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 6),
          const Text('Assign offline tasks. Progress accrues safely on your local device.', style: TextStyle(color: Colors.grey, fontSize: 12)),
          const SizedBox(height: 20),
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: const [
                          Icon(Icons.hardware, color: Color(0xFF03DAC6)),
                          SizedBox(width: 8),
                          Text('Mining Skill', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                        ],
                      ),
                      Text('Level $_miningLevel', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF03DAC6))),
                    ],
                  ),
                  const SizedBox(height: 12),
                  LinearProgressIndicator(
                    value: _miningExp / (_miningLevel * 100),
                    backgroundColor: Colors.grey[800],
                    color: const Color(0xFF03DAC6),
                    minHeight: 8,
                  ),
                  const SizedBox(height: 8),
                  Text('EXP: $_miningExp / ${_miningLevel * 100}', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _toggleMining,
                      icon: Icon(_isMiningActive ? Icons.pause : Icons.play_arrow),
                      label: Text(_isMiningActive ? 'Pause Mining' : 'Start Mining Task'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: _isMiningActive ? Colors.redAccent : const Color(0xFF6200EE),
                      ),
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

  Widget _buildDestinationTile({
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        leading: CircleAvatar(backgroundColor: color.withOpacity(0.2), child: Icon(icon, color: color)),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text(subtitle, style: const TextStyle(fontSize: 11, color: Colors.grey)),
        trailing: const Icon(Icons.arrow_forward_ios, size: 14, color: Colors.grey),
        onTap: onTap,
      ),
    );
  }

  Widget _buildArcadeGameCard(String title, String subtitle, IconData icon, Color color) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Launching $title on local engine...'), backgroundColor: color),
          );
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
}
