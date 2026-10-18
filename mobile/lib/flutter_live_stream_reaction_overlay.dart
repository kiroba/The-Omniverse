import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';

/// Flutter Live Stream Reaction Overlay Widget for KickBack Universe
///
/// Provides real-time, lightweight floating vector/particle reaction overlays
/// for WebRTC live video streams and spectator stages on KickBack.
/// Listens to Socket.IO reaction events (`omni.stream.reactions`) and renders
/// smooth rising particle streams along the right edge of video viewports.

class LiveStreamReactionOverlay extends StatefulWidget {
  final Widget child; // The underlying live video stream player
  final String streamId;
  final bool isHost;

  const LiveStreamReactionOverlay({
    super.key,
    required this.child,
    required this.streamId,
    this.isHost = false,
  });

  @override
  State<LiveStreamReactionOverlay> createState() => _LiveStreamReactionOverlayState();
}

class _LiveStreamReactionOverlayState extends State<LiveStreamReactionOverlay> {
  final List<_FloatingParticle> _particles = [];
  final Random _random = Random();
  int _totalReactionsCount = 1248; // Live counter

  // Reaction types supported
  final List<String> _reactionEmojis = ['❤️', '🔥', '🚀', '⭐', '👏', '💎'];

  @override
  void initState() {
    super.initState();
    // Simulate incoming P2P / Socket.IO reaction stream events
    _startSimulatedSocketStream();
  }

  void _startSimulatedSocketStream() {
    Timer.periodic(const Duration(milliseconds: 800), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      // Periodically trigger ambient spectator reactions
      if (_random.nextDouble() > 0.3) {
        final emoji = _reactionEmojis[_random.nextInt(_reactionEmojis.length)];
        _spawnParticle(emoji, isLocalUser: false);
      }
    });
  }

  void _spawnParticle(String emoji, {bool isLocalUser = false}) {
    setState(() {
      _totalReactionsCount++;
      _particles.add(
        _FloatingParticle(
          id: UniqueKey().toString(),
          emoji: emoji,
          startX: _random.nextDouble() * 60 + 10, // Right-side variance
          durationMs: 2000 + _random.nextInt(1000),
          isLocalUser: isLocalUser,
          onComplete: _removeParticle,
        ),
      );
    });
  }

  void _removeParticle(String id) {
    setState(() {
      _particles.removeWhere((p) => p.id == id);
    });
  }

  void _triggerLocalReaction(String emoji) {
    _spawnParticle(emoji, isLocalUser: true);
    // In production, emit Socket.IO / P2P event envelope:
    // socketService.emit('omni.stream.reactions', {
    //   'streamId': widget.streamId,
    //   'emoji': emoji,
    //   'timestamp': DateTime.now().millisecondsSinceEpoch
    // });
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // 1. Base Video Stream Viewport
        widget.child,

        // 2. Stream Stats Badge (Top Right)
        Positioned(
          top: 16,
          right: 16,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.6),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: Colors.white24, width: 1),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.bolt_rounded, color: Colors.amber, size: 16),
                const SizedBox(width: 4),
                Text(
                  '$_totalReactionsCount',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ),

        // 3. Floating Reaction Particle Overlay Area
        Positioned(
          right: 12,
          bottom: 90,
          top: 80,
          width: 90,
          child: IgnorePointer(
            child: Stack(
              clipBehavior: Clip.none,
              children: _particles.map((particle) {
                return _FloatingParticleWidget(
                  key: ValueKey(particle.id),
                  particle: particle,
                );
              }).toList(),
            ),
          ),
        ),

        // 4. Interactive Bottom Reaction Selector Bar
        Positioned(
          bottom: 16,
          left: 16,
          right: 16,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A).withValues(alpha: 0.85),
              borderRadius: BorderRadius.circular(30),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: _reactionEmojis.map((emoji) {
                return GestureDetector(
                  onTap: () => _triggerLocalReaction(emoji),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    padding: const EdgeInsets.all(8),
                    decoration: const BoxDecoration(
                      shape: BoxShape.circle,
                    ),
                    child: Text(
                      emoji,
                      style: const TextStyle(fontSize: 24),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
        ),
      ],
    );
  }
}

/// Particle Data Class
class _FloatingParticle {
  final String id;
  final String emoji;
  final double startX;
  final int durationMs;
  final bool isLocalUser;
  final Function(String) onComplete;

  _FloatingParticle({
    required this.id,
    required this.emoji,
    required this.startX,
    required this.durationMs,
    required this.isLocalUser,
    required this.onComplete,
  });
}

/// Animated Floating Particle Widget
class _FloatingParticleWidget extends StatefulWidget {
  final _FloatingParticle particle;

  const _FloatingParticleWidget({
    super.key,
    required this.particle,
  });

  @override
  State<_FloatingParticleWidget> createState() => _FloatingParticleWidgetState();
}

class _FloatingParticleWidgetState extends State<_FloatingParticleWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _yAnimation;
  late Animation<double> _opacityAnimation;
  late Animation<double> _scaleAnimation;
  late double _sineFrequency;

  @override
  void initState() {
    super.initState();
    _sineFrequency = Random().nextDouble() * 3 + 2; // Horizontal sway frequency

    _controller = AnimationController(
      vsync: this,
      duration: Duration(milliseconds: widget.particle.durationMs),
    );

    _yAnimation = Tween<double>(begin: 0.0, end: -350.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
    );

    _opacityAnimation = TweenSequence<double>([
      TweenSequenceItem(tween: Tween<double>(begin: 0.0, end: 1.0), weight: 15),
      TweenSequenceItem(tween: Tween<double>(begin: 1.0, end: 1.0), weight: 55),
      TweenSequenceItem(tween: Tween<double>(begin: 1.0, end: 0.0), weight: 30),
    ]).animate(_controller);

    _scaleAnimation = TweenSequence<double>([
      TweenSequenceItem(tween: Tween<double>(begin: 0.4, end: 1.3), weight: 20),
      TweenSequenceItem(tween: Tween<double>(begin: 1.3, end: 1.0), weight: 80),
    ]).animate(_controller);

    _controller.forward().then((_) {
      widget.particle.onComplete(widget.particle.id);
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        // Compute horizontal sine-wave jitter
        final xOffset = widget.particle.startX +
            (sin(_controller.value * _sineFrequency * pi) * 15);

        return Positioned(
          bottom: -_yAnimation.value,
          right: xOffset,
          child: Opacity(
            opacity: _opacityAnimation.value,
            child: Transform.scale(
              scale: _scaleAnimation.value,
              child: Container(
                decoration: widget.particle.isLocalUser
                    ? BoxDecoration(
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: Colors.lightBlueAccent.withValues(alpha: 0.6),
                            blurRadius: 10,
                            spreadRadius: 2,
                          )
                        ],
                      )
                    : null,
                child: Text(
                  widget.particle.emoji,
                  style: const TextStyle(fontSize: 28),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}
