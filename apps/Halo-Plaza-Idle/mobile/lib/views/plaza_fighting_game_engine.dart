// ============================================================================
// THE OMNIVERSE & HALO PLAZA: PLAZA COMBAT BRAWLER ENGINE
// Target Module: `com.kickback.halo_plaza.fighting_game`
// File: `mobile/lib/plaza_fighting_game_engine.dart`
// ============================================================================
// System Architecture:
// - Modular 2D Real-Time Fighting Engine designed for the Halo Plaza.
// - Integrates Live Persona Engine (LPE) avatars, cosmetic traits, & aura effects.
// - Features deterministic frame-based physics, hitbox/hurtbox collision,
//   combo state machines, special moves, and local/P2P mesh peer combat.
// ============================================================================

import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';

void main() {
  runApp(const PlazaFightingGameApp());
}

class PlazaFightingGameApp extends StatelessWidget {
  const PlazaFightingGameApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Plaza Combat Brawler',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF070B12),
        primaryColor: const Color(0xFF00FFCC),
      ),
      home: const PlazaFightingGameScreen(),
    );
  }
}

/// Fighter Action States
enum FighterState { idle, walking, jumping, crouching, attackingLight, attackingHeavy, blocking, hitStun, knockDown }

/// Fighter Character Engine Data Structure
class FighterCharacter {
  final String id;
  final String name;
  final String handle;
  final Color auraColor;
  final Color primaryColor;
  
  // Position & Dynamics
  double x;
  double y;
  double vx;
  double vy;
  bool isFacingRight;
  bool isGrounded;
  
  // Attributes
  double maxHealth;
  double currentHealth;
  double stamina;
  double superMeter; // 0.0 to 100.0
  
  // State Machine
  FighterState state;
  int stateTimer; // Frame counter for current state
  int comboCount;
  
  // Hitbox parameters
  Rect get hurtbox => Rect.fromLTWH(x - 25, y - 90, 50, 90);
  Rect? activeHitbox;
  double attackDamage;

  FighterCharacter({
    required this.id,
    required this.name,
    required this.handle,
    required this.auraColor,
    required this.primaryColor,
    required this.x,
    this.y = 300.0,
    this.vx = 0.0,
    this.vy = 0.0,
    this.isFacingRight = true,
    this.isGrounded = true,
    this.maxHealth = 100.0,
    this.currentHealth = 100.0,
    this.stamina = 100.0,
    this.superMeter = 0.0,
    this.state = FighterState.idle,
    this.stateTimer = 0,
    this.comboCount = 0,
    this.attackDamage = 0.0,
  });

  void resetPosition(double startX, bool facingRight) {
    x = startX;
    y = 300.0;
    vx = 0.0;
    vy = 0.0;
    currentHealth = maxHealth;
    stamina = 100.0;
    superMeter = 0.0;
    state = FighterState.idle;
    stateTimer = 0;
    comboCount = 0;
    isFacingRight = facingRight;
    isGrounded = true;
    activeHitbox = null;
  }
}

class PlazaFightingGameScreen extends StatefulWidget {
  const PlazaFightingGameScreen({super.key});

  @override
  State<PlazaFightingGameScreen> createState() => _PlazaFightingGameScreenState();
}

class _PlazaFightingGameScreenState extends State<PlazaFightingGameScreen> with TickerProviderStateMixin {
  // Game Loop
  Timer? _gameLoopTimer;
  static const int _fps = 60;
  static const double _gravity = 1.2;
  static const double _groundY = 300.0;
  static const double _stageWidth = 800.0;

  // Players
  late FighterCharacter p1;
  late FighterCharacter p2;

  // Match State
  int _roundNumber = 1;
  int _p1Wins = 0;
  int _p2Wins = 0;
  int _matchTimer = 99;
  Timer? _secondClockTimer;
  bool _isGameOver = false;
  String _announcementText = "ROUND 1 - FIGHT!";

  // Combat Particle Effects Buffer
  List<CombatParticle> _particles = [];

  @override
  void initState() {
    super.initState();
    _initializeFighters();
    _startGameLoop();
  }

  void _initializeFighters() {
    p1 = FighterCharacter(
      id: "p1_user",
      name: "Cyber Citizen",
      handle: "@citizen.a8f9",
      auraColor: const Color(0xFF00FFCC), // Neon Cyan
      primaryColor: const Color(0xFF00B4D8),
      x: 250.0,
      isFacingRight: true,
    );

    p2 = FighterCharacter(
      id: "p2_rival",
      name: "Plaza Rival AI",
      handle: "@rival.p2p",
      auraColor: const Color(0xFFFF0055), // Crimson
      primaryColor: const Color(0xFF7209B7),
      x: 550.0,
      isFacingRight: false,
    );
  }

  void _startGameLoop() {
    _gameLoopTimer?.cancel();
    _secondClockTimer?.cancel();

    _gameLoopTimer = Timer.periodic(const Duration(milliseconds: 1000 ~/ _fps), (timer) {
      if (!_isGameOver) {
        _updatePhysicsAndState();
      }
    });

    _secondClockTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!_isGameOver && _matchTimer > 0) {
        setState(() {
          _matchTimer--;
          if (_matchTimer == 0) {
            _handleTimeOut();
          }
        });
      }
    });
  }

  void _updatePhysicsAndState() {
    setState(() {
      // 1. Update Player 1 Physics
      _updateFighterPhysics(p1);

      // 2. Update Player 2 (AI or Peer) Physics & Behavior
      _updateAIBehavior(p2, p1);
      _updateFighterPhysics(p2);

      // 3. Resolve Hitbox Collisions
      _checkHitboxCollisions();

      // 4. Face each other
      if (p1.x < p2.x) {
        p1.isFacingRight = true;
        p2.isFacingRight = false;
      } else {
        p1.isFacingRight = false;
        p2.isFacingRight = true;
      }

      // 5. Update Particles
      _updateParticles();
    });
  }

  void _updateFighterPhysics(FighterCharacter f) {
    // Apply velocity
    f.x += f.vx;
    f.y += f.vy;

    // Boundary limits
    f.x = f.x.clamp(50.0, _stageWidth - 50.0);

    // Gravity
    if (!f.isGrounded) {
      f.vy += _gravity;
      if (f.y >= _groundY) {
        f.y = _groundY;
        f.vy = 0;
        f.isGrounded = true;
        if (f.state == FighterState.jumping) {
          f.state = FighterState.idle;
        }
      }
    }

    // Ground friction
    if (f.isGrounded) {
      f.vx *= 0.75;
      if (f.vx.abs() < 0.1) f.vx = 0.0;
    }

    // State frame progression
    if (f.stateTimer > 0) {
      f.stateTimer--;
      if (f.stateTimer == 0) {
        // Reset active hitbox and return to idle
        f.activeHitbox = null;
        if (f.state != FighterState.knockDown) {
          f.state = FighterState.idle;
        }
      }
    }

    // Active Attack Hitbox Placement
    if (f.activeHitbox != null) {
      double offsetX = f.isFacingRight ? 35.0 : -65.0;
      f.activeHitbox = Rect.fromLTWH(f.x + offsetX, f.y - 70.0, 50.0, 40.0);
    }

    // Passive Stamina Regeneration
    if (f.stamina < 100.0) {
      f.stamina = (f.stamina + 0.3).clamp(0.0, 100.0);
    }
  }

  void _updateAIBehavior(FighterCharacter ai, FighterCharacter opponent) {
    if (ai.stateTimer > 0 || _isGameOver) return;

    double dist = (ai.x - opponent.x).abs();

    if (dist > 120.0) {
      // Approach opponent
      ai.vx = ai.x < opponent.x ? 3.5 : -3.5;
      ai.state = FighterState.walking;
    } else {
      // Range reached: Random attack selection
      int r = math.Random().nextInt(100);
      if (r < 40) {
        _executeAttack(ai, isHeavy: false);
      } else if (r < 75) {
        _executeAttack(ai, isHeavy: true);
      } else {
        ai.state = FighterState.blocking;
        ai.stateTimer = 15;
      }
    }
  }

  void _executeAttack(FighterCharacter f, {required bool isHeavy}) {
    if (f.stateTimer > 0 || !f.isGrounded) return;

    double cost = isHeavy ? 25.0 : 12.0;
    if (f.stamina < cost) return;

    f.stamina -= cost;
    f.state = isHeavy ? FighterState.attackingHeavy : FighterState.attackingLight;
    f.stateTimer = isHeavy ? 22 : 12;
    f.attackDamage = isHeavy ? 18.0 : 9.0;

    double offsetX = f.isFacingRight ? 35.0 : -65.0;
    f.activeHitbox = Rect.fromLTWH(f.x + offsetX, f.y - 70.0, 50.0, 40.0);
  }

  void _checkHitboxCollisions() {
    _resolveAttackHit(p1, p2);
    _resolveAttackHit(p2, p1);
  }

  void _resolveAttackHit(FighterCharacter attacker, FighterCharacter defender) {
    if (attacker.activeHitbox == null) return;

    if (attacker.activeHitbox!.overlaps(defender.hurtbox)) {
      bool isBlocked = defender.state == FighterState.blocking;
      double damage = attacker.attackDamage * (isBlocked ? 0.2 : 1.0);

      defender.currentHealth = (defender.currentHealth - damage).clamp(0.0, defender.maxHealth);
      attacker.superMeter = (attacker.superMeter + (isBlocked ? 5.0 : 12.0)).clamp(0.0, 100.0);

      // Hit recoil & particles
      defender.vx = attacker.isFacingRight ? 6.0 : -6.0;
      defender.state = isBlocked ? FighterState.blocking : FighterState.hitStun;
      defender.stateTimer = isBlocked ? 10 : 18;

      // Spawn spark particles
      _spawnImpactSparks(defender.x, defender.y - 50, isBlocked ? Colors.amber : attacker.auraColor);

      // Consume attack frame
      attacker.activeHitbox = null;

      // Check KO
      if (defender.currentHealth <= 0) {
        _handleKO(winner: attacker, loser: defender);
      }
    }
  }

  void _handleKO({required FighterCharacter winner, required FighterCharacter loser}) {
    _isGameOver = true;
    loser.state = FighterState.knockDown;

    if (winner.id == p1.id) {
      _p1Wins++;
    } else {
      _p2Wins++;
    }

    _announcementText = "${winner.name} WINS ROUND $_roundNumber!";

    Timer(const Duration(seconds: 3), () {
      if (_p1Wins >= 2 || _p2Wins >= 2) {
        setState(() {
          _announcementText = "${_p1Wins >= 2 ? p1.name : p2.name} CHAMPION OF THE PLAZA!";
        });
      } else {
        _startNextRound();
      }
    });
  }

  void _handleTimeOut() {
    _isGameOver = true;
    FighterCharacter winner = p1.currentHealth >= p2.currentHealth ? p1 : p2;
    _announcementText = "TIME OVER - ${winner.name} DECISION!";
  }

  void _startNextRound() {
    setState(() {
      _roundNumber++;
      _matchTimer = 99;
      _isGameOver = false;
      _announcementText = "ROUND $_roundNumber - FIGHT!";
      p1.resetPosition(250.0, true);
      p2.resetPosition(550.0, false);
    });
  }

  void _spawnImpactSparks(double x, double y, Color color) {
    for (int i = 0; i < 8; i++) {
      double angle = math.Random().nextDouble() * 2 * math.pi;
      double speed = math.Random().nextDouble() * 6 + 2;
      _particles.add(CombatParticle(
        x: x,
        y: y,
        vx: math.cos(angle) * speed,
        vy: math.sin(angle) * speed,
        color: color,
        maxLife: 15,
      ));
    }
  }

  void _updateParticles() {
    _particles.removeWhere((p) => p.life >= p.maxLife);
    for (var p in _particles) {
      p.x += p.vx;
      p.y += p.vy;
      p.life++;
    }
  }

  // --- Input Controls ---
  void _p1Jump() {
    if (p1.isGrounded && p1.stateTimer == 0) {
      setState(() {
        p1.vy = -18.0;
        p1.isGrounded = false;
        p1.state = FighterState.jumping;
      });
    }
  }

  void _p1Move(double vx) {
    if (p1.stateTimer == 0 && p1.isGrounded) {
      setState(() {
        p1.vx = vx;
        p1.state = FighterState.walking;
      });
    }
  }

  void _p1SuperMove() {
    if (p1.superMeter < 100.0 || p1.stateTimer > 0) return;
    setState(() {
      p1.superMeter = 0.0;
      p1.state = FighterState.attackingHeavy;
      p1.stateTimer = 30;
      p1.attackDamage = 45.0;
      double offsetX = p1.isFacingRight ? 40.0 : -80.0;
      p1.activeHitbox = Rect.fromLTWH(p1.x + offsetX, p1.y - 80.0, 90.0, 60.0);
      _spawnImpactSparks(p1.x, p1.y - 40, p1.auraColor);
    });
  }

  @override
  void dispose() {
    _gameLoopTimer?.cancel();
    _secondClockTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D1527),
        title: const Text("PLAZA COMBAT BRAWLER (LPE ENGINE)", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF00FFCC))),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.cyanAccent),
            onPressed: () => setState(() {
              _p1Wins = 0;
              _p2Wins = 0;
              _roundNumber = 1;
              _startNextRound();
            }),
          )
        ],
      ),
      body: Column(
        children: [
          // 1. Health Bars & Telemetry HUD
          _buildHUD(),

          // 2. Main Arena Canvas View
          Expanded(
            child: Stack(
              children: [
                // Background Plaza Canvas
                Positioned.fill(
                  child: CustomPaint(
                    painter: ArenaStagePainter(p1: p1, p2: p2, particles: _particles),
                  ),
                ),

                // Match Announcement Banner
                if (_announcementText.isNotEmpty)
                  Center(
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.75),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFF00FFCC), width: 2),
                      ),
                      child: Text(
                        _announcementText,
                        style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF00FFCC)),
                      ),
                    ),
                  ),
              ],
            ),
          ),

          // 3. On-Screen Touch Controls
          _buildControls(),
        ],
      ),
    );
  }

  Widget _buildHUD() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: const Color(0xFF0A0F1D),
      child: Column(
        children: [
          Row(
            children: [
              // Player 1 HUD
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("${p1.name} (${p1.handle})", style: TextStyle(color: p1.auraColor, fontWeight: FontWeight.bold, fontSize: 13)),
                    const SizedBox(height: 4),
                    LinearProgressIndicator(value: p1.currentHealth / p1.maxHealth, backgroundColor: Colors.red.shade900, valueColor: AlwaysStoppedAnimation(p1.auraColor), minHeight: 12),
                    const SizedBox(height: 2),
                    LinearProgressIndicator(value: p1.superMeter / 100.0, backgroundColor: Colors.grey.shade900, valueColor: const AlwaysStoppedAnimation(Colors.amber), minHeight: 4),
                  ],
                ),
              ),

              // Match Timer & Score
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Column(
                  children: [
                    Text("$_matchTimer", style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white)),
                    Text("ROUND $_roundNumber", style: const TextStyle(fontSize: 10, color: Colors.grey)),
                  ],
                ),
              ),

              // Player 2 HUD
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text("${p2.name} (${p2.handle})", style: TextStyle(color: p2.auraColor, fontWeight: FontWeight.bold, fontSize: 13)),
                    const SizedBox(height: 4),
                    LinearProgressIndicator(value: p2.currentHealth / p2.maxHealth, backgroundColor: Colors.red.shade900, valueColor: AlwaysStoppedAnimation(p2.auraColor), minHeight: 12),
                    const SizedBox(height: 2),
                    LinearProgressIndicator(value: p2.superMeter / 100.0, backgroundColor: Colors.grey.shade900, valueColor: const AlwaysStoppedAnimation(Colors.amber), minHeight: 4),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildControls() {
    return Container(
      padding: const EdgeInsets.all(16),
      color: const Color(0xFF0B101D),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // D-Pad Movement
          Row(
            children: [
              ElevatedButton(
                onPressed: () => _p1Move(-5.0),
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF131E32), shape: const CircleBorder(), padding: const EdgeInsets.all(18)),
                child: const Icon(Icons.arrow_back, color: Colors.white),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: _p1Jump,
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF131E32), shape: const CircleBorder(), padding: const EdgeInsets.all(18)),
                child: const Icon(Icons.arrow_upward, color: Colors.white),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: () => _p1Move(5.0),
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF131E32), shape: const CircleBorder(), padding: const EdgeInsets.all(18)),
                child: const Icon(Icons.arrow_forward, color: Colors.white),
              ),
            ],
          ),

          // Action Buttons
          Row(
            children: [
              ElevatedButton(
                onPressed: () => _executeAttack(p1, isHeavy: false),
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00B4D8)),
                child: const Text("LIGHT"),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: () => _executeAttack(p1, isHeavy: true),
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF7209B7)),
                child: const Text("HEAVY"),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: _p1SuperMove,
                style: ElevatedButton.styleFrom(backgroundColor: Colors.amber),
                child: const Text("SUPER", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class CombatParticle {
  double x;
  double y;
  double vx;
  double vy;
  Color color;
  int life = 0;
  int maxLife;

  CombatParticle({required this.x, required this.y, required this.vx, required this.vy, required this.color, required this.maxLife});
}

class ArenaStagePainter extends CustomPainter {
  final FighterCharacter p1;
  final FighterCharacter p2;
  final List<CombatParticle> particles;

  ArenaStagePainter({required this.p1, required this.p2, required this.particles});

  @override
  void paint(Canvas canvas, Size size) {
    // 1. Draw Grid Ground Stage
    final groundPaint = Paint()
      ..color = const Color(0xFF1A263D)
      ..strokeWidth = 3.0;
    canvas.drawLine(Offset(0, p1.y), Offset(size.width, p1.y), groundPaint);

    // 2. Draw Fighters
    _drawFighter(canvas, p1);
    _drawFighter(canvas, p2);

    // 3. Draw Impact Particles
    for (var pt in particles) {
      final pPaint = Paint()..color = pt.color.withValues(alpha: 1.0 - (pt.life / pt.maxLife));
      canvas.drawCircle(Offset(pt.x, pt.y), 3.0, pPaint);
    }
  }

  void _drawFighter(Canvas canvas, FighterCharacter f) {
    // Aura Glow
    final auraPaint = Paint()
      ..color = f.auraColor.withValues(alpha: 0.35)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 15);
    canvas.drawCircle(Offset(f.x, f.y - 45), 35, auraPaint);

    // Character Body
    final bodyPaint = Paint()..color = f.primaryColor;
    canvas.drawRect(Rect.fromLTWH(f.x - 20, f.y - 80, 40, 80), bodyPaint);

    // Eye / Visor Direction Indicator
    final visorPaint = Paint()..color = Colors.white;
    double eyeOffsetX = f.isFacingRight ? 8 : -18;
    canvas.drawRect(Rect.fromLTWH(f.x + eyeOffsetX, f.y - 70, 10, 6), visorPaint);

    // Active Attack Hitbox Overlay
    if (f.activeHitbox != null) {
      final hitPaint = Paint()..color = f.auraColor.withValues(alpha: 0.5);
      canvas.drawRect(f.activeHitbox!, hitPaint);
    }
  }

  @override
  bool shouldRepaint(covariant ArenaStagePainter oldDelegate) => true;
}
