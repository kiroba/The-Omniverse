import 'package:flutter/material.dart';

/// ============================================================================
/// THE OMNI-HUB: UNIVERSAL MOBILE GATEWAY & PLANET LAUNCHER
/// Repositories: kiroba/The-Omni-Hub | hactikgamesstudio/9x9 | kiroba/The-KickBack
/// 
/// Core Features:
///   1. Stargate Zero-Click Login: Hardware Enclave Ed25519 Identity Auth.
///   2. OmniMind Divine Pulse: Omnipresent, read-only God-Engine status indicator.
///   3. Planet Directory: Multi-application launcher featuring Planet 1 (The KickBack)
///      and Planet 2 (9x9: Unity 6000 3D Cube Survival Puzzle Game).
///   4. Cross-Planet Credits: Shared OmniCredit balance & unified wallet across all planets.
///   5. Progressive Recovery Vault: 1-Tap Cloud Passkey, 24-Word Seed, Social Guardians.
/// ============================================================================

class OmniHubGatewayApp extends StatelessWidget {
  const OmniHubGatewayApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'The Omni-Hub',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF090D16), // Deep Space Slate
        primaryColor: const Color(0xFF38BDF8),
      ),
      home: const OmniHubStargateGatekeeper(),
    );
  }
}

/// ----------------------------------------------------------------------------
/// STARGATE LOGIN FLOW: Zero-Click Local Hardware Key Enclave Authentication
/// ----------------------------------------------------------------------------
class OmniHubStargateGatekeeper extends StatefulWidget {
  const OmniHubStargateGatekeeper({Key? key}) : super(key: key);

  @override
  State<OmniHubStargateGatekeeper> createState() => _OmniHubStargateGatekeeperState();
}

class _OmniHubStargateGatekeeperState extends State<OmniHubStargateGatekeeper> {
  bool _isAuthenticating = true;
  String _authStepMessage = "Initializing Hardware Key Enclave...";
  Map<String, dynamic>? _authenticatedCitizen;

  @override
  void initState() {
    super.initState();
    _executeStargateLogin();
  }

  /// Simulates zero-click local hardware enclave authentication (Ed25519)
  Future<void> _executeStargateLogin() async {
    await Future.delayed(const Duration(milliseconds: 600));
    setState(() => _authStepMessage = "Reading Ed25519 Public Key from Secure Enclave...");

    await Future.delayed(const Duration(milliseconds: 600));
    setState(() => _authStepMessage = "Verifying OmniMind Universe Network Policy...");

    await Future.delayed(const Duration(milliseconds: 500));
    setState(() => _authStepMessage = "Auto-Provisioning KickBack Social Profile...");

    await Future.delayed(const Duration(milliseconds: 500));
    setState(() {
      _isAuthenticating = false;
      _authenticatedCitizen = {
        "pubkey": "0x8f9b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b",
        "handle": "@alice.omni",
        "omniCredits": 12500,
        "usdBalance": 145.50,
        "tier": "CREATOR",
        "kickbackProvisioned": true,
      };
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_isAuthenticating) {
      return Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const SizedBox(
                width: 60,
                height: 60,
                child: CircularProgressIndicator(
                  strokeWidth: 3,
                  valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF38BDF8)),
                ),
              ),
              const SizedBox(height: 24),
              const Text(
                'THE OMNI-HUB',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 3,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                _authStepMessage,
                style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
              ),
            ],
          ),
        ),
      );
    }

    return OmniHubMainDashboardScreen(citizen: _authenticatedCitizen!);
  }
}

/// ----------------------------------------------------------------------------
/// MAIN GATEWAY DASHBOARD: Planet Directory, Universal Wallet & OmniMind Pulse
/// ----------------------------------------------------------------------------
class OmniHubMainDashboardScreen extends StatefulWidget {
  final Map<String, dynamic> citizen;

  const OmniHubMainDashboardScreen({Key? key, required this.citizen}) : super(key: key);

  @override
  State<OmniHubMainDashboardScreen> createState() => _OmniHubMainDashboardScreenState();
}

class _OmniHubMainDashboardScreenState extends State<OmniHubMainDashboardScreen> {
  int _currentDockIndex = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // 1. Citizen Header & Identity Status
            _buildCitizenHeader(widget.citizen),

            // 2. OmniMind "Divine Pulse" Status Bar (Omnipresent Maintenance Engine)
            _buildOmniMindDivinePulse(context),

            // 3. Main Planet & Application Carousel
            Expanded(
              child: IndexedStack(
                index: _currentDockIndex,
                children: [
                  _buildPlanetDirectory(context, widget.citizen),
                  _buildUniversalWalletView(widget.citizen),
                  _buildGodViewObserverCanvas(),
                  _buildRecoveryAndSettingsView(context),
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentDockIndex,
        onTap: (idx) => setState(() => _currentDockIndex = idx),
        backgroundColor: const Color(0xFF0F172A),
        selectedItemColor: const Color(0xFF38BDF8),
        unselectedItemColor: const Color(0xFF64748B),
        type: BottomNavigationBarType.fixed,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.public), label: 'Planets'),
          BottomNavigationBarItem(icon: Icon(Icons.account_balance_wallet), label: 'Wallet'),
          BottomNavigationBarItem(icon: Icon(Icons.visibility), label: 'God View'),
          BottomNavigationBarItem(icon: Icon(Icons.shield), label: 'Recovery'),
        ],
      ),
    );
  }

  /// Header widget rendering user handle, key status, and cross-planet credits
  Widget _buildCitizenHeader(Map<String, dynamic> citizen) {
    return Container(
      padding: const EdgeInsets.all(16),
      color: const Color(0xFF0F172A),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              const CircleAvatar(
                backgroundColor: Color(0xFF0284C7),
                child: Icon(Icons.person, color: Colors.white),
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    citizen['handle'],
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  const SizedBox(height: 2),
                  Row(
                    children: const [
                      Icon(Icons.verified, color: Colors.greenAccent, size: 12),
                      SizedBox(width: 4),
                      Text('Ed25519 Enclave Verified', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                    ],
                  ),
                ],
              ),
            ],
          ),
          // Cross-Planet OmniCredit Display
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: const Color(0xFF38BDF8).withOpacity(0.4)),
            ),
            child: Row(
              children: [
                const Icon(Icons.monetization_on, color: Colors.amber, size: 16),
                const SizedBox(width: 6),
                Text(
                  '${citizen['omniCredits']} 💎',
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// OmniMind Divine Pulse Widget: Represents the omnipresent background maintainer
  Widget _buildOmniMindDivinePulse(BuildContext context) {
    return GestureDetector(
      onTap: () => _showDivinePulseDetails(context),
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0xFF0284C7).withOpacity(0.12),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: const Color(0xFF0284C7).withOpacity(0.5)),
        ),
        child: Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: const BoxDecoration(color: Colors.cyanAccent, shape: BoxShape.circle),
            ),
            const SizedBox(width: 10),
            const Expanded(
              child: Text(
                'OmniMind Engine: Universe Healthy • Epoch #1024 Anchor Signed',
                style: TextStyle(color: Color(0xFF38BDF8), fontSize: 11, fontWeight: FontWeight.w600),
              ),
            ),
            const Icon(Icons.chevron_right, color: Color(0xFF38BDF8), size: 16),
          ],
        ),
      ),
    );
  }

  /// Directory displaying connected application "Planets"
  Widget _buildPlanetDirectory(BuildContext context, Map<String, dynamic> citizen) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          'CONNECT TO PLANETS',
          style: TextStyle(color: Color(0xFF64748B), fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.2),
        ),
        const SizedBox(height: 12),

        // Planet 1: The KickBack (Default Social Planet)
        _buildPlanetCard(
          context,
          title: 'The KickBack',
          subtitle: 'Sovereign Social Media & Monetized Gifting',
          badge: 'DEFAULT HOME',
          badgeColor: Colors.blue,
          icon: Icons.dynamic_feed,
          statusText: 'Auto-Provisioned • Active Feed',
          onTap: () => _launchPlanet(context, 'The KickBack'),
        ),

        // Planet 2: 9x9 Cube Survival Puzzle Game (Unity 6000 Title)
        _buildPlanetCard(
          context,
          title: '9x9: Cube Survival Puzzle',
          subtitle: '3D Procedural 9x9x9 Maze Game (Unity 6000) • Battle Royale & Co-op',
          badge: 'GAME PLANET',
          badgeColor: Colors.purple,
          icon: Icons.view_in_ar,
          statusText: '729 Cubic Rooms • Center Exit (4,4,4) • P2P Ready',
          onTap: () => _launch9x9GameModal(context),
        ),

        // Planet 3: Media & Streaming Hub
        _buildPlanetCard(
          context,
          title: 'Omniverse Media & Live Stream',
          subtitle: 'Real-time Video Streaming with 3D Overlays',
          badge: 'MEDIA PLANET',
          badgeColor: Colors.orange,
          icon: Icons.live_tv,
          statusText: '14 Streams Active • Instant Split',
          onTap: () => _launchPlanet(context, 'Omniverse Live Stream'),
        ),
      ],
    );
  }

  Widget _buildPlanetCard(
    BuildContext context, {
    required String title,
    required String subtitle,
    required String badge,
    required Color badgeColor,
    required IconData icon,
    required String statusText,
    required VoidCallback onTap,
  }) {
    return Card(
      color: const Color(0xFF1E293B),
      margin: const EdgeInsets.only(bottom: 14),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFF334155)),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Icon(icon, color: const Color(0xFF38BDF8), size: 24),
                      const SizedBox(width: 10),
                      Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                    ],
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: badgeColor.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: badgeColor, width: 0.8),
                    ),
                    child: Text(badge, style: TextStyle(color: badgeColor, fontSize: 9, fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(subtitle, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
              const Divider(color: Color(0xFF334155), height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(statusText, style: const TextStyle(color: Colors.greenAccent, fontSize: 11)),
                  const Text('Launch Planet →', style: TextStyle(color: Color(0xFF38BDF8), fontSize: 12, fontWeight: FontWeight.bold)),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// 9x9 Game Mode Selection Modal
  void _launch9x9GameModal(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1E293B),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: const [
                Text('9x9: Select Game Mode', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                Icon(Icons.view_in_ar, color: Colors.purpleAccent),
              ],
            ),
            const SizedBox(height: 8),
            const Text('Unity 6000.2.10f1 Procedural Maze Escape Game', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
            const SizedBox(height: 16),
            _buildGameModeOption(ctx, '🏆 Battle Royale', '8 Players • 10 Min Time Limit • PvP Exit Race'),
            _buildGameModeOption(ctx, '🤝 Co-op Mode', '2-8 Players • Team Center Exit Escape'),
            _buildGameModeOption(ctx, '⚡ 3x3 Mode', '27 Cubic Rooms • 5 Min Blitz'),
            _buildGameModeOption(ctx, '🎲 5x5 Mode', '125 Cubic Rooms • 8 Min Medium Maze'),
            _buildGameModeOption(ctx, '🔧 Standard 9x9x9 Mode', 'Full 729 Cubic Rooms (~218 Sparse) • Practice'),
          ],
        ),
      ),
    );
  }

  Widget _buildGameModeOption(BuildContext context, String title, String subtitle) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: const Icon(Icons.play_circle_fill, color: Color(0xFF38BDF8)),
      title: Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
      subtitle: Text(subtitle, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
      onTap: () {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Launching 9x9 ($title) via Omniverse Game Engine...')),
        );
      },
    );
  }

  /// Universal Wallet Screen: Cross-Planet Credits & Instant Cashout
  Widget _buildUniversalWalletView(Map<String, dynamic> citizen) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text('CROSS-PLANET UNIVERSAL WALLET',
            style: TextStyle(color: Color(0xFF64748B), fontSize: 12, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF38BDF8)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Shared OmniCredits Balance', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
              const SizedBox(height: 4),
              Text('${citizen['omniCredits']} Credits 💎',
                  style: const TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              Text('Available USD Cash-Out: \$${citizen['usdBalance'].toStringAsFixed(2)}',
                  style: const TextStyle(color: Colors.greenAccent, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              const Text(
                'OmniCredits are usable across all planets (The KickBack, 9x9 Cube Game, and Live Streaming). Purchases and earnings sync automatically over P2P logs.',
                style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
              ),
            ],
          ),
        ),
      ],
    );
  }

  /// God-View Observer Canvas View
  Widget _buildGodViewObserverCanvas() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text('OMNIMIND GOD-VIEW OBSERVER HUD',
            style: TextStyle(color: Color(0xFF64748B), fontSize: 12, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF020617),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF334155)),
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Read-Only Telemetry Stream', style: TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              Text('• [12:50:01] Epoch #1024 Merkle State Trie Anchored (32 nodes synced)',
                  style: TextStyle(color: Colors.white70, fontSize: 11, fontFamily: 'monospace')),
              Text('• [12:48:12] 9x9 Cube Maze Room Generator Seeds Verified for Battle Royale',
                  style: TextStyle(color: Colors.white70, fontSize: 11, fontFamily: 'monospace')),
              Text('• [12:45:00] Human-First Feed Rule Audit: 0 AI posts detected on KickBack',
                  style: TextStyle(color: Colors.white70, fontSize: 11, fontFamily: 'monospace')),
            ],
          ),
        ),
      ],
    );
  }

  /// Progressive Profile Recovery View
  Widget _buildRecoveryAndSettingsView(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text('PROFILE RECOVERY VAULT & SETTINGS',
            style: TextStyle(color: Color(0xFF64748B), fontSize: 12, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        _buildRecoveryOptionTile(
          icon: Icons.fingerprint,
          title: '1-Tap Cloud Passkey Backup',
          subtitle: 'AES-256 key encrypted to Apple iCloud Keychain / Google Passkey (Recommended)',
          badgeText: 'ENABLED',
          badgeColor: Colors.greenAccent,
          onTap: () {},
        ),
        _buildRecoveryOptionTile(
          icon: Icons.key,
          title: '24-Word Seed Phrase',
          subtitle: 'View your offline BIP-39 mnemonic seed phrase for manual recovery',
          badgeText: 'VIEW SEED',
          badgeColor: const Color(0xFF38BDF8),
          onTap: () {},
        ),
        _buildRecoveryOptionTile(
          icon: Icons.people,
          title: 'Social Guardians',
          subtitle: 'Assign 3 trusted contacts on The KickBack for Shamir Secret Sharing recovery',
          badgeText: 'CONFIGURE',
          badgeColor: Colors.amber,
          onTap: () {},
        ),
      ],
    );
  }

  Widget _buildRecoveryOptionTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required String badgeText,
    required Color badgeColor,
    required VoidCallback onTap,
  }) {
    return Card(
      color: const Color(0xFF1E293B),
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFF334155)),
      ),
      child: ListTile(
        leading: Icon(icon, color: const Color(0xFF38BDF8)),
        title: Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
        subtitle: Text(subtitle, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: badgeColor.withOpacity(0.2),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: badgeColor, width: 0.8),
          ),
          child: Text(badgeText, style: TextStyle(color: badgeColor, fontSize: 9, fontWeight: FontWeight.bold)),
        ),
        onTap: onTap,
      ),
    );
  }

  void _launchPlanet(BuildContext context, String planetName) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Launching $planetName planet via Omni-Hub Gateway...')),
    );
  }

  void _showDivinePulseDetails(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('OmniMind God Engine Status', style: TextStyle(color: Colors.white)),
        content: const Text(
          'OmniMind runs silently as the background maintainer of the universe. It manages system rules, anchors state snapshots, and enforces human sovereignty with zero direct user chat or prompting.',
          style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Close')),
        ],
      ),
    );
  }
}
