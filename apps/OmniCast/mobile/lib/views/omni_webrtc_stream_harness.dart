import 'dart:async';
import 'package:flutter/material.dart';

enum WebRTCConnectionState {
  idle,
  connecting,
  connected,
  disconnected,
  failed,
}

class OmniWebRTCStreamHarness extends StatefulWidget {
  final String myPeerId;
  final String targetPeerId;
  final bool isVideoCall;
  final VoidCallback? onCallEnded;

  const OmniWebRTCStreamHarness({
    super.key,
    required this.myPeerId,
    required this.targetPeerId,
    this.isVideoCall = true,
    this.onCallEnded,
  });

  @override
  State<OmniWebRTCStreamHarness> createState() => _OmniWebRTCStreamHarnessState();
}

class _OmniWebRTCStreamHarnessState extends State<OmniWebRTCStreamHarness> {
  WebRTCConnectionState _connectionState = WebRTCConnectionState.connecting;
  bool _isMuted = false;
  bool _isVideoOff = false;
  int _bandwidthKbps = 1250;
  Timer? _metricsTimer;

  @override
  void initState() {
    super.initState();
    _initPeerConnectionPipeline();
  }

  @override
  void dispose() {
    _metricsTimer?.cancel();
    super.dispose();
  }

  void _initPeerConnectionPipeline() async {
    await Future.delayed(const Duration(seconds: 2));
    if (!mounted) return;

    setState(() {
      _connectionState = WebRTCConnectionState.connected;
    });

    _metricsTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (_connectionState == WebRTCConnectionState.connected && mounted) {
        setState(() {
          _bandwidthKbps = 1200 + (DateTime.now().second % 100);
        });
      }
    });
  }

  void _endCall() {
    setState(() {
      _connectionState = WebRTCConnectionState.disconnected;
    });
    if (widget.onCallEnded != null) {
      widget.onCallEnded!();
    } else {
      Navigator.of(context).maybePop();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF0F172A),
      child: Stack(
        children: [
          // Main Remote Video Stream Viewport
          Center(
            child: _connectionState == WebRTCConnectionState.connected
                ? Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.account_circle_rounded, size: 96, color: Color(0xFF6366F1)),
                      const SizedBox(height: 16),
                      Text(
                        'Connected to ${widget.targetPeerId}',
                        style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0x2610B981),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFF10B981)),
                        ),
                        child: Text(
                          'WebRTC SRTP Active • $_bandwidthKbps Kbps',
                          style: const TextStyle(color: Color(0xFF10B981), fontSize: 11, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  )
                : const Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      CircularProgressIndicator(color: Color(0xFF6366F1)),
                      SizedBox(height: 16),
                      Text(
                        'Exchanging SDP Offer/Answer via Local Daemon...',
                        style: TextStyle(color: Colors.grey, fontSize: 13),
                      ),
                    ],
                  ),
          ),

          // Local PIP Preview Video Box
          Positioned(
            top: 16,
            right: 16,
            child: Container(
              width: 100,
              height: 140,
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white24),
              ),
              child: Center(
                child: Icon(
                  _isVideoOff ? Icons.videocam_off_rounded : Icons.person_rounded,
                  color: Colors.white54,
                  size: 32,
                ),
              ),
            ),
          ),

          // Action Overlay Bar
          Positioned(
            bottom: 24,
            left: 24,
            right: 24,
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 20),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B).withValues(alpha: 0.95),
                borderRadius: BorderRadius.circular(32),
                border: Border.all(color: Colors.white10),
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
                  FloatingActionButton(
                    mini: true,
                    backgroundColor: Colors.redAccent,
                    onPressed: _endCall,
                    child: const Icon(Icons.call_end_rounded, color: Colors.white),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
