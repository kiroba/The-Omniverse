// ignore_for_file: unused_field
import 'dart:async';
import 'package:flutter/material.dart';

void main() {
  runApp(const OmniCastApp());
}

class OmniCastApp extends StatelessWidget {
  const OmniCastApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'OmniCast P2P Video Chat',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0F172A),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF6366F1),
          secondary: Color(0xFF10B981),
          surface: Color(0xFF1E293B),
        ),
      ),
      home: const StargateAuthLoginScreen(),
    );
  }
}

class StargateAuthLoginScreen extends StatefulWidget {
  const StargateAuthLoginScreen({Key? key}) : super(key: key);

  @override
  State<StargateAuthLoginScreen> createState() => _StargateAuthLoginScreenState();
}

class _StargateAuthLoginScreenState extends State<StargateAuthLoginScreen> {
  bool _isAuthenticating = false;
  String? _peerId;
  String? _merkleRoot;

  Future<void> _authenticateWithStargate() async {
    setState(() {
      _isAuthenticating = true;
    });

    // Simulate Stargate Ed25519 Hardware Enclave Auth & Local Merkle Init
    await Future.delayed(const Duration(seconds: 2));

    final fakePeerId = "0x${List.generate(16, (i) => (i * 17 % 16).toRadixString(16)).join()}";
    final fakeMerkle = "0x${List.generate(32, (i) => (i * 31 % 16).toRadixString(16)).join()}";

    setState(() {
      _isAuthenticating = false;
      _peerId = fakePeerId;
      _merkleRoot = fakeMerkle;
    });

    if (mounted) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (context) => OmniCastDialerLobby(
            peerId: fakePeerId,
            merkleRoot: fakeMerkle,
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFF6366F1).withValues(alpha: 0.15),
                  border: Border.all(color: const Color(0xFF6366F1), width: 2),
                ),
                child: const Icon(Icons.videocam_rounded, size: 64, color: Color(0xFF6366F1)),
              ),
              const SizedBox(height: 24),
              const Text(
                'OmniCast P2P',
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, letterSpacing: 1.2),
              ),
              const SizedBox(height: 8),
              const Text(
                'Zero-Server WebRTC Video & Encrypted Mesh Chat',
                style: TextStyle(fontSize: 14, color: Colors.grey),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 48),
              if (_isAuthenticating)
                Column(
                  children: const [
                    CircularProgressIndicator(color: Color(0xFF6366F1)),
                    SizedBox(height: 16),
                    Text("Attesting Stargate Hardware Enclave Key...", style: TextStyle(color: Colors.grey)),
                  ],
                )
              else
                ElevatedButton.icon(
                  onPressed: _authenticateWithStargate,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF6366F1),
                    padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  icon: const Icon(Icons.fingerprint_rounded, color: Colors.white),
                  label: const Text(
                    'Authenticate & Initialize Merkle Tree',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.white),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class OmniCastDialerLobby extends StatefulWidget {
  final String peerId;
  final String merkleRoot;

  const OmniCastDialerLobby({
    Key? key,
    required this.peerId,
    required this.merkleRoot,
  }) : super(key: key);

  @override
  State<OmniCastDialerLobby> createState() => _OmniCastDialerLobbyState();
}

class _OmniCastDialerLobbyState extends State<OmniCastDialerLobby> {
  final TextEditingController _targetPeerController = TextEditingController();

  void _startCall({bool videoCall = true}) {
    final target = _targetPeerController.text.trim();
    if (target.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a target Peer ID or choose an active node.')),
      );
      return;
    }

    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => OmniCastVideoCallScreen(
          myPeerId: widget.peerId,
          targetPeerId: target,
          isVideo: videoCall,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('OmniCast Lobby'),
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
      ),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white10),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("LOCAL HARDWARE IDENTITY", style: TextStyle(fontSize: 11, color: Colors.grey, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  SelectableText("Peer ID: ${widget.peerId}", style: const TextStyle(fontFamily: 'monospace', fontSize: 13, color: Color(0xFF10B981))),
                  const SizedBox(height: 4),
                  SelectableText("Merkle Root: ${widget.merkleRoot}", style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: Colors.grey)),
                ],
              ),
            ),
            const SizedBox(height: 28),
            const Text("ENTER TARGET PEER ID", style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.grey)),
            const SizedBox(height: 8),
            TextField(
              controller: _targetPeerController,
              decoration: InputDecoration(
                hintText: 'e.g. 0x0123456789abcdef',
                filled: true,
                fillColor: const Color(0xFF1E293B),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                prefixIcon: const Icon(Icons.person_search_rounded, color: Colors.grey),
              ),
            ),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _startCall(videoCall: true),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF6366F1),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    icon: const Icon(Icons.videocam_rounded, color: Colors.white),
                    label: const Text('Start Video Call', style: TextStyle(color: Colors.white)),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _startCall(videoCall: false),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      side: const BorderSide(color: Color(0xFF10B981)),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    icon: const Icon(Icons.call_rounded, color: Color(0xFF10B981)),
                    label: const Text('Audio Call', style: TextStyle(color: Color(0xFF10B981))),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class OmniCastVideoCallScreen extends StatefulWidget {
  final String myPeerId;
  final String targetPeerId;
  final bool isVideo;

  const OmniCastVideoCallScreen({
    Key? key,
    required this.myPeerId,
    required this.targetPeerId,
    required this.isVideo,
  }) : super(key: key);

  @override
  State<OmniCastVideoCallScreen> createState() => _OmniCastVideoCallScreenState();
}

class _OmniCastVideoCallScreenState extends State<OmniCastVideoCallScreen> {
  bool _isMuted = false;
  bool _isVideoOff = false;
  bool _isConnected = false;
  final List<String> _chatMessages = [];
  final TextEditingController _msgController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _connectWebRTCStream();
  }

  void _connectWebRTCStream() async {
    await Future.delayed(const Duration(seconds: 2));
    if (mounted) {
      setState(() {
        _isConnected = true;
      });
    }
  }

  void _sendMessage() {
    final text = _msgController.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _chatMessages.add("Me: $text");
      _msgController.clear();
    });
  }

  void _showChatDrawer() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF1E293B),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom,
                top: 16, left: 16, right: 16,
              ),
              child: SizedBox(
                height: 400,
                child: Column(
                  children: [
                    Container(width: 40, height: 4, decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(2))),
                    const SizedBox(height: 12),
                    const Text('Encrypted Mesh Chat', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const Divider(color: Colors.white10),
                    Expanded(
                      child: ListView.builder(
                        itemCount: _chatMessages.length,
                        itemBuilder: (context, index) {
                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4.0),
                            child: Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(color: const Color(0xFF0F172A), borderRadius: BorderRadius.circular(8)),
                              child: Text(_chatMessages[index], style: const TextStyle(color: Colors.white)),
                            ),
                          );
                        },
                      ),
                    ),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _msgController,
                            decoration: const InputDecoration(
                              hintText: 'Type encrypted message...',
                              border: InputBorder.none,
                            ),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.send_rounded, color: Color(0xFF6366F1)),
                          onPressed: () {
                            _sendMessage();
                            setModalState(() {});
                          },
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Stack(
          children: [
            // Remote Video Placeholder
            Positioned.fill(
              child: Container(
                color: const Color(0xFF0F172A),
                child: Center(
                  child: _isConnected
                      ? Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.account_circle, size: 96, color: Colors.indigoAccent),
                            const SizedBox(height: 12),
                            Text("Connected to ${widget.targetPeerId.substring(0, 10)}...", style: const TextStyle(color: Colors.white70)),
                            const SizedBox(height: 6),
                            const Text("WebRTC SRTP Encrypted Stream Active", style: TextStyle(fontSize: 12, color: Color(0xFF10B981))),
                          ],
                        )
                      : Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: const [
                            CircularProgressIndicator(color: Color(0xFF6366F1)),
                            SizedBox(height: 16),
                            Text("Exchanging SDP & ICE Candidates via Local Hub...", style: TextStyle(color: Colors.grey)),
                          ],
                        ),
                ),
              ),
            ),

            // Local Video Preview Box
            Positioned(
              top: 20, right: 20,
              child: Container(
                width: 110, height: 160,
                decoration: BoxDecoration(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.white24),
                ),
                child: Center(
                  child: Icon(
                    _isVideoOff ? Icons.videocam_off_rounded : Icons.person_rounded,
                    color: Colors.white54, size: 36,
                  ),
                ),
              ),
            ),

            // Call Controls Overlay
            Positioned(
              bottom: 30, left: 20, right: 20,
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 20),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B).withValues(alpha: 0.9),
                  borderRadius: BorderRadius.circular(30),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    IconButton(
                      icon: Icon(_isMuted ? Icons.mic_off_rounded : Icons.mic_rounded, color: Colors.white),
                      onPressed: () => setState(() => _isMuted = !_isMuted),
                    ),
                    IconButton(
                      icon: Icon(_isVideoOff ? Icons.videocam_off_rounded : Icons.videocam_rounded, color: Colors.white),
                      onPressed: () => setState(() => _isVideoOff = !_isVideoOff),
                    ),
                    IconButton(
                      icon: const Icon(Icons.chat_bubble_rounded, color: Color(0xFF6366F1)),
                      onPressed: _showChatDrawer,
                    ),
                    FloatingActionButton(
                      backgroundColor: Colors.redAccent,
                      mini: true,
                      onPressed: () => Navigator.of(context).pop(),
                      child: const Icon(Icons.call_end_rounded, color: Colors.white),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
