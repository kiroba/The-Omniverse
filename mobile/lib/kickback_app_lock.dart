import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:local_auth/local_auth.dart';

import 'kickback_platform.dart';

/// ============================================================================
/// KICKBACK APP LOCK (fingerprint / face / device PIN)
/// ============================================================================
/// What this really does:
/// - Asks Android (BiometricPrompt via local_auth) for the owner's fingerprint,
///   face, or device PIN/pattern/password before the app UI is shown, and again
///   before a post is signed if the last unlock is older than [signGrace].
/// - It is an APP-LEVEL GATE. The identity key is not cryptographically bound to
///   the biometric: the seed sits in flutter_secure_storage (encrypted with an
///   Android Keystore key), and that Keystore key does not require user
///   authentication to use. So this stops someone who picks up an unlocked phone
///   from opening KickBack or posting as you; it does not stop a rooted device or
///   an attacker with code execution inside the app from reading the key.
/// - If the phone has no screen lock and no enrolled biometrics, there is nothing
///   for Android to check. The app then opens in "unprotected" mode and says so
///   on screen rather than pretending to be locked.
/// ============================================================================

enum LockState { checking, locked, unlocked, unprotected }

class AuthOutcome {
  final bool ok;
  final String? message;
  const AuthOutcome(this.ok, [this.message]);
}

class AppLock {
  AppLock._();

  static final LocalAuthentication _auth = LocalAuthentication();
  static DateTime? _lastUnlock;
  static bool _unprotected = false;

  /// How long an unlock also covers signing a post without asking again.
  static const Duration signGrace = Duration(minutes: 2);

  /// How long the app may sit in the background before it locks again.
  static const Duration backgroundGrace = Duration(seconds: 30);

  /// True when the phone has nothing to authenticate with (no screen lock and
  /// no enrolled biometrics). Set by [probe].
  static bool get unprotected => _unprotected;

  /// Works out whether the device can authenticate the owner at all.
  /// isDeviceSupported() is true when there is biometric hardware or a secure
  /// lock screen (PIN/pattern/password).
  static Future<bool> probe() async {
    try {
      final supported = await _auth.isDeviceSupported();
      _unprotected = !supported;
    } on PlatformException {
      _unprotected = true;
    } on MissingPluginException {
      _unprotected = true;
    }
    return !_unprotected;
  }

  static void lock() => _lastUnlock = null;

  static bool unlockedWithin(Duration d) =>
      _lastUnlock != null && DateTime.now().difference(_lastUnlock!) < d;

  /// Shows the system prompt. Biometrics first; Android offers the device
  /// PIN/pattern/password as the fallback (biometricOnly: false).
  static Future<AuthOutcome> authenticate(String reason) async {
    if (_unprotected) return const AuthOutcome(true);
    try {
      final ok = await _auth.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(
          biometricOnly: false,
          stickyAuth: true,
          useErrorDialogs: true,
          sensitiveTransaction: true,
        ),
      );
      if (ok) _lastUnlock = DateTime.now();
      return AuthOutcome(ok, ok ? null : 'Not unlocked');
    } on PlatformException catch (e) {
      switch (e.code) {
        case 'NotAvailable':
        case 'PasscodeNotSet':
        case 'NotEnrolled':
          // Nothing to check against. Re-probe: if the device really has no
          // lock at all, fall back to unprotected mode instead of trapping the user.
          final hasLock = await probe();
          if (!hasLock) return const AuthOutcome(true);
          return AuthOutcome(false, kickbackIsDesktop
              ? 'Set up Windows Hello (PIN, face or fingerprint) in Windows Settings > Accounts > Sign-in options (${e.code}).'
              : 'Set up a fingerprint, face or screen lock in Android Settings (${e.code}).');
        case 'LockedOut':
          return const AuthOutcome(false, 'Too many attempts. Wait 30 seconds and try again.');
        case 'PermanentlyLockedOut':
          return const AuthOutcome(false, 'Biometrics locked. Unlock the phone with your PIN first, then try again.');
        default:
          return AuthOutcome(false, e.message ?? e.code);
      }
    } on MissingPluginException {
      // No local_auth implementation on this platform: don't trap the user.
      _unprotected = true;
      return const AuthOutcome(true);
    }
  }

  /// Used right before signing: passes if the user unlocked recently,
  /// otherwise prompts again.
  static Future<AuthOutcome> ensureRecentUnlock(String reason) async {
    if (_unprotected || unlockedWithin(signGrace)) return const AuthOutcome(true);
    return authenticate(reason);
  }
}

/// Shows [child] only after the owner unlocks. Locks again after the app has
/// been in the background longer than [AppLock.backgroundGrace].
class KickBackLockGate extends StatefulWidget {
  final Widget child;
  const KickBackLockGate({super.key, required this.child});

  @override
  State<KickBackLockGate> createState() => _KickBackLockGateState();
}

class _KickBackLockGateState extends State<KickBackLockGate> with WidgetsBindingObserver {
  LockState _state = LockState.checking;
  String? _message;
  bool _prompting = false;
  DateTime? _backgroundedAt;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _start());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (_prompting) return; // the system prompt itself pauses the activity
    if (s == AppLifecycleState.paused || s == AppLifecycleState.hidden) {
      _backgroundedAt ??= DateTime.now();
    } else if (s == AppLifecycleState.resumed) {
      final away = _backgroundedAt;
      _backgroundedAt = null;
      if (_state == LockState.unlocked && away != null &&
          DateTime.now().difference(away) > AppLock.backgroundGrace) {
        AppLock.lock();
        setState(() => _state = LockState.locked);
        _unlock();
      }
    }
  }

  Future<void> _start() async {
    final canLock = await AppLock.probe();
    if (!mounted) return;
    if (!canLock) {
      setState(() => _state = LockState.unprotected);
      return;
    }
    setState(() => _state = LockState.locked);
    await _unlock();
  }

  Future<void> _unlock() async {
    if (_prompting) return;
    _prompting = true;
    final r = await AppLock.authenticate('Unlock The KickBack');
    _prompting = false;
    if (!mounted) return;
    setState(() {
      if (r.ok) {
        _state = AppLock.unprotected ? LockState.unprotected : LockState.unlocked;
        _message = null;
      } else {
        _state = LockState.locked;
        _message = r.message;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    switch (_state) {
      case LockState.unlocked:
        return widget.child;
      case LockState.unprotected:
        return Column(children: [
          Material(
            color: const Color(0xFF5C3B00),
            child: SafeArea(
              bottom: false,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                child: Row(children: [
                  const Icon(Icons.lock_open, size: 16, color: Color(0xFFFFC107)),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      kickbackIsDesktop
                          ? 'Windows Hello is not set up on this PC, so KickBack can\'t be locked. Add a PIN in Windows Settings > Accounts > Sign-in options.'
                          : 'No screen lock or biometrics on this phone, so KickBack can\'t be locked. Add one in Android Settings.',
                      style: const TextStyle(fontSize: 11, color: Color(0xFFFFE082)),
                    ),
                  ),
                ]),
              ),
            ),
          ),
          Expanded(child: MediaQuery.removePadding(context: context, removeTop: true, child: widget.child)),
        ]);
      case LockState.checking:
      case LockState.locked:
        return Scaffold(
          backgroundColor: const Color(0xFF121212),
          body: Center(
            child: Padding(
              padding: const EdgeInsets.all(32),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                const Icon(Icons.fingerprint, size: 72, color: Color(0xFFBB86FC)),
                const SizedBox(height: 16),
                const Text('The KickBack is locked',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
                const SizedBox(height: 8),
                Text(
                  _message ?? 'Use your fingerprint, face or device PIN to open the app.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.grey, fontSize: 13),
                ),
                const SizedBox(height: 20),
                if (_state == LockState.locked)
                  ElevatedButton.icon(
                    onPressed: _prompting ? null : _unlock,
                    icon: const Icon(Icons.lock_open),
                    label: const Text('Unlock'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF6200EE),
                      foregroundColor: Colors.white,
                    ),
                  )
                else
                  const CircularProgressIndicator(color: Color(0xFFBB86FC)),
              ]),
            ),
          ),
        );
    }
  }
}
