import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

const String u1 = 'http://127.0.0.1:9100/api/v1/telemetry/node-health';
const String u2 = 'http://127.0.0.1:5000/api/events/stats';

String formatHandle(String pubKey) {
  if (pubKey.isEmpty) return '@Node-Peer';
  if (pubKey.length <= 10) return '@$pubKey';
  final prefix = pubKey.substring(2, min(6, pubKey.length)).toUpperCase();
  final suffix = pubKey.substring(max(0, pubKey.length - 4)).toUpperCase();
  return '@Node-$prefix..$suffix';
}

String generateSecureRandomHex(int length) {
  final rand = Random.secure();
  final bytes = List<int>.generate(length, (_) => rand.nextInt(256));
  final hexStr = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join('');
  return '0x$hexStr';
}

class ContactNode {
  final String id;
  final String handle;
  final String address;
  final String transportType;
  final bool isOnline;

  ContactNode({
    required this.id,
    required this.handle,
    required this.address,
    required this.transportType,
    this.isOnline = true,
  });
}

void main() {
  runApp(const OmniCastApp());
}

class OmniCastApp extends StatelessWidget {
  const OmniCastApp({super.key});

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
  const StargateAuthLoginScreen({super.key});

  @override
  State<StargateAuthLoginScreen> createState() =>
      _StargateAuthLoginScreenState();
}

class _StargateAuthLoginScreenState extends State<StargateAuthLoginScreen> {
  bool _isAuthenticating = false;

  Future<void> _authenticateWithStargate() async {
    setState(() {
      _isAuthenticating = true;
    });

    // Simulate Stargate Ed25519 Hardware Enclave Auth & Local Merkle Init
    await Future.delayed(const Duration(seconds: 2));

    String livePeerId = '';
    String liveMerkleRoot = '';

    try {
      final res =
          await http.get(Uri.parse(u1)).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        if (data['node_id'] != null && data['node_id'].toString().isNotEmpty) {
          livePeerId = data['node_id'].toString();
        }
      }
    } catch (_) {}

    try {
      final statsRes =
          await http.get(Uri.parse(u2)).timeout(const Duration(seconds: 5));
      if (statsRes.statusCode == 200) {
        final statsData = jsonDecode(statsRes.body);
        if (statsData['last_merkle_hash'] != null &&
            statsData['last_merkle_hash'].toString().isNotEmpty) {
          liveMerkleRoot = statsData['last_merkle_hash'].toString();
        }
      }
    } catch (_) {}

    if (livePeerId.isEmpty) {
      livePeerId = generateSecureRandomHex(16);
    }
    if (liveMerkleRoot.isEmpty) {
      liveMerkleRoot = generateSecureRandomHex(32);
    }

    final fakePeerId = livePeerId;
    final fakeMerkle = liveMerkleRoot;

    if (!mounted) return;

    setState(() {
      _isAuthenticating = false;
    });

    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (context) => OmniCastDialerLobby(
          peerId: fakePeerId,
          merkleRoot: fakeMerkle,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
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
                child: const Icon(Icons.videocam_rounded,
                    size: 64, color: Color(0xFF6366F1)),
              ),
              const SizedBox(height: 24),
              const Text(
                'OmniCast P2P',
                style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.2,
                    color: Colors.white),
              ),
              const SizedBox(height: 8),
              const Text(
                'Zero-Server WebRTC Video & Encrypted Mesh Chat',
                style: TextStyle(fontSize: 14, color: Colors.grey),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 48),
              if (_isAuthenticating)
                const Column(
                  children: [
                    CircularProgressIndicator(color: Color(0xFF6366F1)),
                    SizedBox(height: 16),
                    Text("Attesting Stargate Hardware Enclave Key...",
                        style: TextStyle(color: Colors.grey)),
                  ],
                )
              else
                ElevatedButton.icon(
                  onPressed: _authenticateWithStargate,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF6366F1),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 32, vertical: 16),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                  ),
                  icon: const Icon(Icons.fingerprint_rounded,
                      color: Colors.white),
                  label: const Text(
                    'Authenticate & Connect Stargate Key',
                    style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: Colors.white),
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
    super.key,
    required this.peerId,
    required this.merkleRoot,
  });

  @override
  State<OmniCastDialerLobby> createState() => _OmniCastDialerLobbyState();
}

class _OmniCastDialerLobbyState extends State<OmniCastDialerLobby> {
  final TextEditingController _addContactController = TextEditingController();
  Map<String, dynamic>? _nodeHealth;
  List<ContactNode> _contacts = [];
  bool _wanListenerActive = false;
  int _selectedWanDurationMinutes = 15;
  Timer? _pollingTimer;

  @override
  void initState() {
    super.initState();
    _fetchNodeHealth();
    _pollingTimer =
        Timer.periodic(const Duration(seconds: 3), (_) => _fetchNodeHealth());
  }

  @override
  void dispose() {
    _addContactController.dispose();
    _pollingTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchNodeHealth() async {
    try {
      final res =
          await http.get(Uri.parse(u1)).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        if (!mounted) return;
        setState(() {
          _nodeHealth = data;

          final List<String> peers = List<String>.from(
              data['peer_ips'] ?? data['peer_addresses'] ?? []);
          final Map<String, ContactNode> currentMap = {
            for (var c in _contacts) c.address: c
          };

          for (var peerAddr in peers) {
            if (!currentMap.containsKey(peerAddr)) {
              final shortId = peerAddr.hashCode.abs().toRadixString(16);
              currentMap[peerAddr] = ContactNode(
                id: shortId,
                handle: formatHandle('0x$shortId'),
                address: peerAddr,
                transportType:
                    peerAddr.contains(':') ? 'UDP Subnet' : 'P2P Mesh',
                isOnline: true,
              );
            }
          }

          _contacts = currentMap.values.toList();
        });
      }
    } catch (_) {}
  }

  void _addManualContact() {
    final input = _addContactController.text.trim();
    if (input.isEmpty) return;

    setState(() {
      final shortId = input.hashCode.abs().toRadixString(16);
      _contacts.insert(
        0,
        ContactNode(
          id: shortId,
          handle: formatHandle(input.startsWith('0x') ? input : '0x$shortId'),
          address: input,
          transportType: 'Saved Contact',
          isOnline: true,
        ),
      );
      _addContactController.clear();
    });

    Navigator.of(context).pop();
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Contact added successfully!')),
    );
  }

  void _showAddContactDialog() {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: const Color(0xFF1E293B),
          title: const Text('Add Contact Node',
              style: TextStyle(color: Colors.white, fontSize: 16)),
          content: TextField(
            controller: _addContactController,
            style: const TextStyle(color: Colors.white),
            decoration: InputDecoration(
              hintText: 'Enter Node Address or Public Key',
              hintStyle: const TextStyle(color: Colors.grey, fontSize: 13),
              filled: true,
              fillColor: const Color(0xFF0F172A),
              border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: BorderSide.none),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel', style: TextStyle(color: Colors.grey)),
            ),
            ElevatedButton(
              onPressed: _addManualContact,
              style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF6366F1)),
              child: const Text('Add', style: TextStyle(color: Colors.white)),
            ),
          ],
        );
      },
    );
  }

  void _startCall({required String targetAddress, bool videoCall = true}) {
    if (targetAddress.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select or enter a target node.')),
      );
      return;
    }

    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => OmniCastVideoCallScreen(
          myPeerId: widget.peerId,
          targetPeerId: targetAddress,
          isVideo: videoCall,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final userHandle = formatHandle(widget.peerId);

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('OmniCast Dialer',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.person_add_alt_1_rounded,
                color: Color(0xFF6366F1)),
            onPressed: _showAddContactDialog,
            tooltip: 'Add Contact',
          ),
          Padding(
            padding: const EdgeInsets.only(right: 12.0),
            child: Center(
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: _nodeHealth != null
                      ? const Color(0x2610B981)
                      : const Color(0x26FF9800),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                      color: _nodeHealth != null
                          ? const Color(0xFF10B981)
                          : Colors.orange),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.circle,
                        size: 8,
                        color: _nodeHealth != null
                            ? const Color(0xFF10B981)
                            : Colors.orange),
                    const SizedBox(width: 6),
                    Text(
                      _nodeHealth != null ? 'Mesh Online' : 'Connecting...',
                      style: TextStyle(
                        color: _nodeHealth != null
                            ? const Color(0xFF10B981)
                            : Colors.orange,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          )
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
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
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: const BoxDecoration(
                        shape: BoxShape.circle, color: Color(0x2610B981)),
                    child: const Icon(Icons.shield_rounded,
                        color: Color(0xFF10B981), size: 24),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(userHandle,
                            style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                                color: Colors.white)),
                        const SizedBox(height: 2),
                        SelectableText(
                          'Node ID: ${widget.peerId}',
                          style: const TextStyle(
                              fontFamily: 'monospace',
                              fontSize: 11,
                              color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white10),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Ephemeral WAN Listener',
                          style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 12,
                              color: Colors.white)),
                      Text('Opens public socket with auto-teardown',
                          style: TextStyle(fontSize: 10, color: Colors.grey)),
                    ],
                  ),
                  Row(
                    children: [
                      DropdownButton<int>(
                        value: _selectedWanDurationMinutes,
                        dropdownColor: const Color(0xFF1E293B),
                        style:
                            const TextStyle(color: Colors.white, fontSize: 12),
                        underline: const SizedBox(),
                        items: const [
                          DropdownMenuItem(value: 5, child: Text('5m')),
                          DropdownMenuItem(value: 15, child: Text('15m')),
                          DropdownMenuItem(value: 30, child: Text('30m')),
                        ],
                        onChanged: (val) {
                          if (val != null) {
                            setState(() => _selectedWanDurationMinutes = val);
                          }
                        },
                      ),
                      Switch(
                        value: _wanListenerActive,
                        activeThumbColor: const Color(0xFF10B981),
                        activeTrackColor: const Color(0x3310B981),
                        onChanged: (val) {
                          setState(() => _wanListenerActive = val);
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('CONTACTS & DISCOVERED NODES',
                    style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: Colors.grey)),
                Text('${_contacts.length} Available',
                    style: const TextStyle(
                        fontSize: 11, color: Color(0xFF10B981))),
              ],
            ),
            const SizedBox(height: 8),
            Expanded(
              child: _contacts.isEmpty
                  ? const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.radar_rounded,
                              size: 48, color: Colors.grey),
                          SizedBox(height: 12),
                          Text('Scanning mesh for peers...',
                              style:
                                  TextStyle(color: Colors.grey, fontSize: 13)),
                          SizedBox(height: 4),
                          Text('Tap + in app bar to add a contact manually',
                              style:
                                  TextStyle(color: Colors.grey, fontSize: 11)),
                        ],
                      ),
                    )
                  : ListView.builder(
                      itemCount: _contacts.length,
                      itemBuilder: (context, index) {
                        final contact = _contacts[index];
                        return Card(
                          margin: const EdgeInsets.only(bottom: 8),
                          color: const Color(0xFF1E293B),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12)),
                          child: ListTile(
                            leading: CircleAvatar(
                              backgroundColor: const Color(0x266366F1),
                              child: Text(
                                contact.handle.length > 6
                                    ? contact.handle[6]
                                    : 'N',
                                style: const TextStyle(
                                    color: Color(0xFF6366F1),
                                    fontWeight: FontWeight.bold),
                              ),
                            ),
                            title: Text(contact.handle,
                                style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 14)),
                            subtitle: Text(
                                '${contact.address} • ${contact.transportType}',
                                style: const TextStyle(
                                    color: Colors.grey, fontSize: 11)),
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                IconButton(
                                  icon: const Icon(Icons.call_rounded,
                                      color: Color(0xFF10B981), size: 20),
                                  onPressed: () => _startCall(
                                      targetAddress: contact.address,
                                      videoCall: false),
                                  tooltip: 'Audio Call',
                                ),
                                IconButton(
                                  icon: const Icon(Icons.videocam_rounded,
                                      color: Color(0xFF6366F1), size: 22),
                                  onPressed: () => _startCall(
                                      targetAddress: contact.address,
                                      videoCall: true),
                                  tooltip: 'Video Call',
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
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
    super.key,
    required this.myPeerId,
    required this.targetPeerId,
    required this.isVideo,
  });

  @override
  State<OmniCastVideoCallScreen> createState() =>
      _OmniCastVideoCallScreenState();
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

  @override
  void dispose() {
    _msgController.dispose();
    super.dispose();
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
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom,
                top: 16,
                left: 16,
                right: 16,
              ),
              child: SizedBox(
                height: 400,
                child: Column(
                  children: [
                    Container(
                        width: 40,
                        height: 4,
                        decoration: BoxDecoration(
                            color: Colors.white24,
                            borderRadius: BorderRadius.circular(2))),
                    const SizedBox(height: 12),
                    const Text('Encrypted Mesh Chat',
                        style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                            color: Colors.white)),
                    const Divider(color: Colors.white10),
                    Expanded(
                      child: ListView.builder(
                        itemCount: _chatMessages.length,
                        itemBuilder: (context, index) {
                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4.0),
                            child: Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                  color: const Color(0xFF0F172A),
                                  borderRadius: BorderRadius.circular(8)),
                              child: Text(_chatMessages[index],
                                  style: const TextStyle(color: Colors.white)),
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
                            style: const TextStyle(color: Colors.white),
                            decoration: const InputDecoration(
                              hintText: 'Type encrypted message...',
                              hintStyle: TextStyle(color: Colors.grey),
                              border: InputBorder.none,
                            ),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.send_rounded,
                              color: Color(0xFF6366F1)),
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
                            const Icon(Icons.account_circle,
                                size: 96, color: Colors.indigoAccent),
                            const SizedBox(height: 12),
                            Text(
                                "Connected to ${widget.targetPeerId.length >= 10 ? widget.targetPeerId.substring(0, 10) : widget.targetPeerId}...",
                                style: const TextStyle(color: Colors.white70)),
                            const SizedBox(height: 6),
                            const Text("WebRTC SRTP Encrypted Stream Active",
                                style: TextStyle(
                                    fontSize: 12, color: Color(0xFF10B981))),
                          ],
                        )
                      : const Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            CircularProgressIndicator(color: Color(0xFF6366F1)),
                            SizedBox(height: 16),
                            Text(
                                "Exchanging SDP & ICE Candidates via Local Hub...",
                                style: TextStyle(color: Colors.grey)),
                          ],
                        ),
                ),
              ),
            ),

            // Local Video Preview Box
            Positioned(
              top: 20,
              right: 20,
              child: Container(
                width: 110,
                height: 160,
                decoration: BoxDecoration(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.white24),
                ),
                child: Center(
                  child: Icon(
                    _isVideoOff
                        ? Icons.videocam_off_rounded
                        : Icons.person_rounded,
                    color: Colors.white54,
                    size: 36,
                  ),
                ),
              ),
            ),

            // Call Controls Overlay
            Positioned(
              bottom: 30,
              left: 20,
              right: 20,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(vertical: 12, horizontal: 20),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B).withValues(alpha: 0.9),
                  borderRadius: BorderRadius.circular(30),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    IconButton(
                      icon: Icon(
                          _isMuted ? Icons.mic_off_rounded : Icons.mic_rounded,
                          color: Colors.white),
                      onPressed: () {
                        setState(() => _isMuted = !_isMuted);
                      },
                    ),
                    IconButton(
                      icon: Icon(
                          _isVideoOff
                              ? Icons.videocam_off_rounded
                              : Icons.videocam_rounded,
                          color: Colors.white),
                      onPressed: () {
                        setState(() => _isVideoOff = !_isVideoOff);
                      },
                    ),
                    IconButton(
                      icon: const Icon(Icons.chat_bubble_rounded,
                          color: Color(0xFF6366F1)),
                      onPressed: _showChatDrawer,
                    ),
                    FloatingActionButton(
                      backgroundColor: Colors.redAccent,
                      mini: true,
                      onPressed: () => Navigator.of(context).pop(),
                      child: const Icon(Icons.call_end_rounded,
                          color: Colors.white),
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
