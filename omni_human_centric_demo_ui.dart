import 'dart:async';
import 'package:flutter/material.dart';

void main() {
  runApp(const OmniHumanCentricApp());
}

class OmniHumanCentricApp extends StatelessWidget {
  const OmniHumanCentricApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'The Omniverse - Human First Experience',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0F172A),
        primaryColor: const Color(0xFF10B981),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF10B981),
          secondary: Color(0xFFF59E0B),
          surface: Color(0xFF1E293B),
        ),
      ),
      home: const HumanFeedHomeScreen(),
    );
  }
}

class HumanFeedHomeScreen extends StatefulWidget {
  const HumanFeedHomeScreen({super.key});

  @override
  State<HumanFeedHomeScreen> createState() => _HumanFeedHomeScreenState();
}

class _HumanFeedHomeScreenState extends State<HumanFeedHomeScreen> {
  bool _isDaemonOnline = false;
  int _activePeers = 0;
  String _nodeId = 'Connecting...';
  Timer? _telemetryTimer;

  @override
  void initState() {
    super.initState();
    _fetchDaemonHealth();
  }

  @override
  void dispose() {
    _telemetryTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchDaemonHealth() async {
    // Daemon check placeholder
    setState(() {
      _isDaemonOnline = true;
      _activePeers = 1;
      _nodeId = '0x8f2a9c1e4b3d';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF0F172A),
        elevation: 0,
        title: Row(
          children: [
            const Text(
              'The Omniverse',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 20, color: Colors.white),
            ),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: _isDaemonOnline ? const Color(0xFF064E3B) : const Color(0xFF7F1D1D),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: _isDaemonOnline ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                  width: 1,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: _isDaemonOnline ? const Color(0xFF34D399) : const Color(0xFFF87171),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    _isDaemonOnline ? 'Synced (' + _activePeers.toString() + ' Peers)' : 'Local Only',
                    style: TextStyle(
                      color: _isDaemonOnline ? const Color(0xFFA7F3D0) : const Color(0xFFFCA5A5),
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(vertical: 12),
        children: [
          _buildLpeAvatarHeaderCard(),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            child: Text(
              'Human-Verified Community Feed',
              style: TextStyle(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 0.5),
            ),
          ),
          _buildHumanFeedCard(
            author: 'Ecosystem Member',
            handle: '@peer_node_1',
            timeAgo: '12m ago',
            content: 'Building decentralized communities on local mesh networks. Direct, private, and human-verified!',
            likes: 24,
            isVerifiedHuman: true,
          ),
          _buildHumanFeedCard(
            author: 'Network Peer',
            handle: '@peer_node_2',
            timeAgo: '45m ago',
            content: 'Testing OmniCast HD P2P Video calls on mobile and desktop. Clear streams over local mesh sockets!',
            likes: 42,
            isVerifiedHuman: true,
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: const Color(0xFF10B981),
        onPressed: () {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Launching OmniCast P2P Video Call...')),
          );
        },
        icon: const Icon(Icons.videocam, color: Colors.white),
        label: const Text('OmniCast Call', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
      ),
    );
  }

  Widget _buildLpeAvatarHeaderCard() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.3),
            blurRadius: 12,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Row(
        children: [
          Stack(
            alignment: Alignment.center,
            children: [
              Container(
                width: 64,
                height: 64,
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [Color(0xFF10B981), Color(0xFF3B82F6)],
                  ),
                ),
              ),
              const CircleAvatar(
                radius: 29,
                backgroundColor: Color(0xFF0F172A),
                child: Icon(Icons.person, size: 32, color: Color(0xFFF59E0B)),
              ),
            ],
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Your Live Persona',
                  style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text(
                  'Node: ' + (_nodeId.length > 16 ? _nodeId.substring(0, 16) + '...' : _nodeId),
                  style: const TextStyle(color: Colors.white54, fontSize: 12, fontFamily: 'monospace'),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    _buildTraitBadge('Ed25519 Enclave'),
                    const SizedBox(width: 6),
                    _buildTraitBadge('Human Verified'),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTraitBadge(String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: const Color(0xFF334155),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(
        label,
        style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 10, fontWeight: FontWeight.w600),
      ),
    );
  }

  Widget _buildHumanFeedCard({
    required String author,
    required String handle,
    required String timeAgo,
    required String content,
    required int likes,
    required bool isVerifiedHuman,
  }) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.2),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 18,
                backgroundColor: const Color(0xFF0D9488),
                child: Text(
                  author[0],
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        author,
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                      ),
                      if (isVerifiedHuman) ...[
                        const SizedBox(width: 4),
                        const Icon(Icons.verified, size: 15, color: Color(0xFF2DD4BF)),
                      ],
                    ],
                  ),
                  Text(
                    handle,
                    style: const TextStyle(color: Colors.white38, fontSize: 12),
                  ),
                ],
              ),
              const Spacer(),
              Text(
                timeAgo,
                style: const TextStyle(color: Colors.white38, fontSize: 12),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            content,
            style: const TextStyle(color: Color(0xFFE2E8F0), fontSize: 14, height: 1.4),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              const Icon(Icons.favorite_border, size: 18, color: Color(0xFFF43F5E)),
              const SizedBox(width: 6),
              Text(likes.toString(), style: const TextStyle(color: Colors.white60, fontSize: 12)),
              const SizedBox(width: 24),
              const Icon(Icons.chat_bubble_outline, size: 18, color: Color(0xFF38BDF8)),
              const Spacer(),
              const Icon(Icons.share_outlined, size: 18, color: Colors.white38),
            ],
          ),
        ],
      ),
    );
  }
}
