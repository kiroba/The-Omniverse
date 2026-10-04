import 'package:flutter/material.dart';

void main() {
  runApp(const OmniCoreEnginesApp());
}

class OmniCoreEnginesApp extends StatelessWidget {
  const OmniCoreEnginesApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Omniverse Core Engines Gateway',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0A0E17),
        primaryColor: const Color(0xFF00FFCC),
      ),
      home: const CoreEnginesDashboard(),
    );
  }
}

class CoreEnginesDashboard extends StatefulWidget {
  const CoreEnginesDashboard({super.key});

  @override
  State<CoreEnginesDashboard> createState() => _CoreEnginesDashboardState();
}

class _CoreEnginesDashboardState extends State<CoreEnginesDashboard> {
  bool _isDaemonActive = true;
  int _activePeers = 4;
  int _secretTapCount = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: GestureDetector(
          onTap: () {
            setState(() {
              _secretTapCount++;
              if (_secretTapCount >= 5) {
                _secretTapCount = 0;
                _showEasterEggDialog(context);
              }
            });
          },
          child: const Text(
            '🕹 OMNIVERSE CORE ENGINES GATEWAY',
            style: TextStyle(color: Color(0xFF00FFCC), fontWeight: FontWeight.bold, fontSize: 16),
          ),
        ),
        backgroundColor: const Color(0xFF121A29),
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildStatusHeader(),
            const SizedBox(height: 20),
            _buildEngineCard(
              title: 'ENGINE 01: 9x9 3D CUBE SURVIVAL MAZE',
              status: 'Native Flutter Raycaster Active',
              detail: 'Deterministic 729-Room Matrix | Mesh In-Sync',
              color: Colors.greenAccent,
            ),
            const SizedBox(height: 12),
            _buildEngineCard(
              title: 'ENGINE 02: KNIT P2P MESH & MERKLE DAG',
              status: 'Local Loopback 127.0.0.1:9200',
              detail: ' Peer Nodes (Wi-Fi Aware & BLE) | GossipSub Relays',
              color: Colors.cyanAccent,
            ),
            const SizedBox(height: 12),
            _buildEngineCard(
              title: 'ENGINE 03: MARKOV AI BUILDER NPCS',
              status: 'Sub-1ms CPU Inference Loop',
              detail: 'Adaptive Construction & Hazard Repair Shaders',
              color: Colors.amberAccent,
            ),
            const SizedBox(height: 20),
            Center(
              child: ElevatedButton.icon(
                onPressed: () => _showEasterEggDialog(context),
                icon: const Icon(Icons.monitor, color: Colors.black),
                label: const Text('OPEN PROCESS MONITOR & EASTER EGG', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF00FFCC),
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF162235),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF00FFCC).withValues(alpha: 0.4)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('GATEWAY STATUS', style: TextStyle(color: Colors.grey, fontSize: 12)),
              Text(
                _isDaemonActive ? 'ACTIVE (127.0.0.1:9200)' : 'STOPPED',
                style: const TextStyle(color: Colors.greenAccent, fontWeight: FontWeight.bold, fontSize: 16),
              ),
            ],
          ),
          Switch(
            value: _isDaemonActive,
            activeThumbColor: const Color(0xFF00FFCC),
            onChanged: (val) => setState(() => _isDaemonActive = val),
          ),
        ],
      ),
    );
  }

  Widget _buildEngineCard({required String title, required String status, required String detail, required Color color}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF121A29),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 14)),
          const SizedBox(height: 6),
          Text(status, style: const TextStyle(color: Colors.white, fontSize: 13)),
          const SizedBox(height: 4),
          Text(detail, style: const TextStyle(color: Colors.grey, fontSize: 11)),
        ],
      ),
    );
  }

  void _showEasterEggDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: const Color(0xFF0A0E17),
        title: const Text('🕹 CORE ENGINES PROCESS MONITOR', style: TextStyle(color: Color(0xFF00FFCC))),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Running Standalone Daemon Loop:
• P2P GossipSub Mesh: ACTIVE
• Merkle Root: 0x0185D7BE
• Local SQLite WAL: READY',
              style: TextStyle(color: Colors.white70, fontSize: 12),
            ),
            const SizedBox(height: 16),
            Container(
              height: 150,
              width: double.infinity,
              color: Colors.black,
              child: const Center(
                child: Text('[ EASTER EGG GIF VISUALIZER PLACEHOLDER ]', style: TextStyle(color: Color(0xFF00FFCC), fontSize: 10)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('CLOSE', style: TextStyle(color: Color(0xFF00FFCC))),
          ),
        ],
      ),
    );
  }
}
