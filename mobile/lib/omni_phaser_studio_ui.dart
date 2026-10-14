// ============================================================================
// THE OMNIVERSE & THE KICKBACK: PHASER 2D CREATOR STUDIO UI (BAREBONES V1)
// Target File: mobile/lib/omni_phaser_studio_ui.dart
// Version: 1.0.0 - Modular Studio & Cross-Industry Creator Shell
// Tag: [FUNDAMENTAL_FEATURE_TAG: LOCALSEND_PHASER_STUDIO_V1]
// ============================================================================

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const OmniPhaserStudioApp());
}

class OmniPhaserStudioApp extends StatelessWidget {
  const OmniPhaserStudioApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'OmniVerse Creator Studio',
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
      home: const PhaserStudioShell(),
    );
  }
}

class PhaserStudioShell extends StatefulWidget {
  const PhaserStudioShell({super.key});

  @override
  State<PhaserStudioShell> createState() => _PhaserStudioShellState();
}

class _PhaserStudioShellState extends State<PhaserStudioShell> {
  // Navigation State
  int _activeTab = 0; // 0: Project Canvas, 1: Asset Inspector, 2: Manifest & Security, 3: LocalSend Export
  final List<int> _tabHistory = [0];

  // Industry Categories
  String _selectedIndustry = "Arcade Games";
  final List<String> _industries = [
    "Arcade Games",
    "Educator Course Passes",
    "LPE Cosmetic Packs",
    "Puzzle Vaults",
    "Social Deduction & Audio"
  ];

  // Mod Project Form Controls
  final TextEditingController _titleController = TextEditingController(text: "Cyber Runner 2D");
  final TextEditingController _modIdController = TextEditingController(text: "omnimod.alex_studio.cyber_runner_2d");
  final TextEditingController _descController = TextEditingController(text: "Neon platformer with custom Tiled maps and LocalSend P2P racing.");
  final TextEditingController _authorHandleController = TextEditingController(text: "@alex.creative");

  // Asset Mappings (Barebones state)
  final List<Map<String, String>> _spritesheets = [
    {"key": "player_run", "path": "assets/sprites/player_runner.png", "dims": "64x64"},
    {"key": "enemy_drone", "path": "assets/sprites/drone.png", "dims": "32x32"}
  ];

  final List<Map<String, String>> _tilemaps = [
    {"key": "level_1_map", "path": "assets/maps/stage_01.json", "format": "TILED_JSON"}
  ];

  final List<Map<String, String>> _audioBanks = [
    {"key": "bgm_synthwave", "path": "assets/audio/cyber_beat.ogg"}
  ];

  // Security & Hardware State
  bool _networkAccess = false; // Strictly false for Zero-Trust sandbox
  int _p2pSyncHz = 10;
  final String _hardwareKey = "0x8F92A1B439C0E71D000000000000000000000000000000000000000000000001";
  bool _isCompiled = false;
  String _statusMessage = "Ready to package .omnimod archive";

  void _switchTab(int newIndex) {
    if (_activeTab != newIndex) {
      setState(() {
        _activeTab = newIndex;
        _tabHistory.add(newIndex);
      });
    }
  }

  bool _handleBackNavigation() {
    if (_tabHistory.length > 1) {
      setState(() {
        _tabHistory.removeLast();
        _activeTab = _tabHistory.last;
      });
      return false; // Handled internally
    }
    return true; // Allow OS default back / exit
  }

  void _compileAndExportPackage() {
    setState(() {
      _statusMessage = "Generating SHA-256 Merkle Root & Signing with Ed25519 Enclave Key...";
    });

    Future.delayed(const Duration(milliseconds: 1200), () {
      setState(() {
        _isCompiled = true;
        _statusMessage = "SUCCESS: Package compiled & signed at /workspace/scratch/quarantine/${_modIdController.text}.omnimod";
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Package compiled! Ready for LocalSend P2P subnet transfer."),
          backgroundColor: Color(0xFF00FFCC),
        ),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: _tabHistory.length <= 1,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) {
          _handleBackNavigation();
        }
      },
      child: KeyboardListener(
        focusNode: FocusNode()..requestFocus(),
        onKeyEvent: (KeyEvent event) {
          if (event is KeyDownEvent) {
            if (event.logicalKey == LogicalKeyboardKey.escape ||
                (HardwareKeyboard.instance.isAltPressed &&
                    event.logicalKey == LogicalKeyboardKey.arrowLeft)) {
              _handleBackNavigation();
            }
          }
        },
        child: Scaffold(
          appBar: AppBar(
            leading: _tabHistory.length > 1
                ? IconButton(
                    icon: const Icon(Icons.arrow_back, color: Color(0xFF00FFCC)),
                    tooltip: 'Back (Esc / Alt+Left)',
                    onPressed: _handleBackNavigation,
                  )
                : const Icon(Icons.handcraft_outlined, color: Color(0xFF00FFCC)),
            title: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Phaser 2D Creator Studio',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
                ),
                Text(
                  'Industry Target: $_selectedIndustry',
                  style: const TextStyle(fontSize: 11, color: Colors.grey),
                ),
              ],
            ),
            actions: [
              Container(
                margin: const EdgeInsets.only(right: 12),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF00FFCC).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFF00FFCC), width: 1),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.verified_user, color: Color(0xFF00FFCC), size: 14),
                    SizedBox(width: 4),
                    Text(
                      'ENCLAVE SIGNING',
                      style: TextStyle(color: Color(0xFF00FFCC), fontSize: 10, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ),
            ],
          ),
          body: Column(
            children: [
              // Industry Selector Ribbon
              Container(
                height: 48,
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                color: const Color(0xFF1E293B),
                child: ListView.builder(
                  scrollDirection: Axis.horizontal,
                  itemCount: _industries.length,
                  itemBuilder: (context, index) {
                    final industry = _industries[index];
                    final isSelected = _selectedIndustry == industry;
                    return Padding(
                      padding: const EdgeInsets.only(right: 8.0),
                      child: ChoiceChip(
                        label: Text(industry, style: TextStyle(fontSize: 12, color: isSelected ? Colors.black : Colors.white)),
                        selected: isSelected,
                        selectedColor: const Color(0xFF00FFCC),
                        backgroundColor: const Color(0xFF0F172A),
                        onSelected: (selected) {
                          if (selected) {
                            setState(() => _selectedIndustry = industry);
                          }
                        },
                      ),
                    );
                  },
                ),
              ),

              // Main Workspace Body
              Expanded(child: _buildActiveWorkspace()),
            ],
          ),
          bottomNavigationBar: BottomNavigationBar(
            currentIndex: _activeTab,
            onTap: _switchTab,
            type: BottomNavigationBarType.fixed,
            backgroundColor: const Color(0xFF1E293B),
            selectedItemColor: const Color(0xFF00FFCC),
            unselectedItemColor: Colors.grey,
            items: const [
              BottomNavigationBarItem(icon: Icon(Icons.dashboard_customize), label: 'Canvas'),
              BottomNavigationBarItem(icon: Icon(Icons.collections), label: 'Assets'),
              BottomNavigationBarItem(icon: Icon(Icons.security), label: 'Manifest'),
              BottomNavigationBarItem(icon: Icon(Icons.wifi_tethering), label: 'LocalSend'),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActiveWorkspace() {
    switch (_activeTab) {
      case 0:
        return _buildCanvasView();
      case 1:
        return _buildAssetInspectorView();
      case 2:
        return _buildManifestSecurityView();
      case 3:
        return _buildLocalSendExportView();
      default:
        return _buildCanvasView();
    }
  }

  // View 1: 2D Interactive Canvas Preview
  Widget _buildCanvasView() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            height: 220,
            width: double.infinity,
            decoration: BoxDecoration(
              color: const Color(0xFF111827),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF00FFCC).withOpacity(0.4), width: 1.5),
            ),
            child: Stack(
              children: [
                Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.videogame_asset, size: 48, color: Color(0xFF00FFCC)),
                      const SizedBox(height: 8),
                      Text(
                        'Phaser 3.80.0 Interactive Canvas Grid (800x600)',
                        style: TextStyle(color: Colors.grey.shade400, fontSize: 13),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'Tilemap: stage_01.json Loaded • Sprite: player_runner.png',
                        style: TextStyle(color: Color(0xFF00FFCC), fontSize: 11, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
                Positioned(
                  top: 8,
                  left: 8,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    color: Colors.black54,
                    child: const Text('2D PREVIEW MODE', style: TextStyle(color: Colors.greenAccent, fontSize: 10)),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          const Text('Quick Action Toolbox', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () {},
                  icon: const Icon(Icons.grid_on, size: 18),
                  label: const Text('Add Tilemap Layer'),
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF1E293B)),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () {},
                  icon: const Icon(Icons.nature_people, size: 18),
                  label: const Text('Add Sprite Atlas'),
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF1E293B)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // View 2: Asset Inspector & Mapping
  Widget _buildAssetInspectorView() {
    return ListView(
      padding: const EdgeInsets.all(16.0),
      children: [
        const Text('Spritesheets & Atlases', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Color(0xFF00FFCC))),
        const SizedBox(height: 8),
        ..._spritesheets.map((sprite) => Card(
              color: const Color(0xFF1E293B),
              child: ListTile(
                leading: const Icon(Icons.image, color: Color(0xFF00FFCC)),
                title: Text(sprite['key']!, style: const TextStyle(fontWeight: FontWeight.bold)),
                subtitle: Text('${sprite['path']} (${sprite['dims']})'),
                trailing: IconButton(icon: const Icon(Icons.delete_outline, color: Colors.redAccent), onPressed: () {}),
              ),
            )),
        const SizedBox(height: 16),
        const Text('Tilemaps (Tiled JSON)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Color(0xFF00FFCC))),
        const SizedBox(height: 8),
        ..._tilemaps.map((map) => Card(
              color: const Color(0xFF1E293B),
              child: ListTile(
                leading: const Icon(Icons.map, color: Color(0xFF7209B7)),
                title: Text(map['key']!, style: const TextStyle(fontWeight: FontWeight.bold)),
                subtitle: Text('${map['path']} [${map['format']}]'),
                trailing: IconButton(icon: const Icon(Icons.delete_outline, color: Colors.redAccent), onPressed: () {}),
              ),
            )),
      ],
    );
  }

  // View 3: Manifest & Zero-Trust Security Settings
  Widget _buildManifestSecurityView() {
    return ListView(
      padding: const EdgeInsets.all(16.0),
      children: [
        const Text('Mod Metadata Configuration', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Color(0xFF00FFCC))),
        const SizedBox(height: 12),
        TextField(controller: _titleController, decoration: const InputDecoration(labelText: 'Mod Title', border: OutlineInputBorder())),
        const SizedBox(height: 12),
        TextField(controller: _modIdController, decoration: const InputDecoration(labelText: 'Unique Mod ID', border: OutlineInputBorder())),
        const SizedBox(height: 12),
        TextField(controller: _authorHandleController, decoration: const InputDecoration(labelText: 'Author Handle', border: OutlineInputBorder())),
        const SizedBox(height: 12),
        TextField(controller: _descController, maxLines: 2, decoration: const InputDecoration(labelText: 'Description', border: OutlineInputBorder())),
        const SizedBox(height: 20),
        const Text('Zero-Trust Sandbox Constraints', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Color(0xFF00FFCC))),
        SwitchListTile(
          title: const Text('Direct Internet Network Access'),
          subtitle: const Text('Strictly false. Network is routed through local IPC (127.0.0.1:9200).'),
          value: _networkAccess,
          onChanged: null, // Hard-locked false
          secondary: const Icon(Icons.block, color: Colors.redAccent),
        ),
        ListTile(
          title: const Text('P2P State Sync Frequency'),
          subtitle: Text('$_p2pSyncHz Hz (Updates per second)'),
          trailing: SizedBox(
            width: 120,
            child: Slider(
              value: _p2pSyncHz.toDouble(),
              min: 1,
              max: 30,
              divisions: 29,
              onChanged: (v) => setState(() => _p2pSyncHz = v.toInt()),
            ),
          ),
        ),
      ],
    );
  }

  // View 4: LocalSend Export & Subnet Broadcast
  Widget _buildLocalSendExportView() {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Card(
            color: const Color(0xFF1E293B),
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Hardware Enclave Signing', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Color(0xFF00FFCC))),
                  const SizedBox(height: 8),
                  Text('Ed25519 Key: ${_hardwareKey.substring(0, 18)}...', style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
                  const SizedBox(height: 8),
                  const Text('Attestation Badge: HUMAN_VERIFIED_CREATOR', style: TextStyle(color: Colors.greenAccent, fontSize: 12, fontWeight: FontWeight.bold)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            onPressed: _compileAndExportPackage,
            icon: const Icon(Icons.archive),
            label: const Text('Compile & Sign .omnimod Archive'),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF00FFCC),
              foregroundColor: Colors.black,
              minimumSize: const Size(double.infinity, 48),
            ),
          ),
          const SizedBox(height: 16),
          Text(_statusMessage, style: TextStyle(fontSize: 12, color: _isCompiled ? Colors.greenAccent : Colors.grey)),
        ],
      ),
    );
  }
}
