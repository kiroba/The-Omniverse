import 'dart:io';

import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// ============================================================================
/// KICKBACK PLATFORM SETUP (Android + Windows desktop)
/// ============================================================================
/// KickBack ships as an Android APK and, from v0.1.8, as a Windows desktop
/// build (kickback-social-windows-x64.zip) that talks to the Omni daemon on the
/// same PC ("This device" = 127.0.0.1) or to a remote hub over Tailscale.
///
/// Plugin support on Windows, and what this file does about it:
/// - sqflite (local event log + legacy seed): the sqflite plugin has no Windows
///   implementation, so on desktop we switch the global sqflite factory to
///   sqflite_common_ffi (SQLite is bundled by package:sqlite3's build hook) and
///   keep the database in %APPDATA%\TheOmniverse\KickBack instead of the
///   working directory.
/// - flutter_secure_storage: has a Windows implementation (Windows-protected
///   storage via the plugin's Windows backend). AndroidOptions are ignored there.
/// - local_auth: has a Windows implementation (Windows Hello). If Windows Hello
///   is not set up, AppLock falls back to "unprotected" and says so on screen.
/// - ota_update: Android-only. OmniOta skips in-app updates on other platforms.
/// - http / dart:io HttpClient / cryptography / crypto: pure Dart, no
///   cleartext restriction on Windows, so http:// to 127.0.0.1 and to a
///   Tailscale 100.x hub works as it does on Android (where the generated
///   network_security_config allows it).
/// ============================================================================

/// True on Windows / Linux / macOS desktop builds.
bool get kickbackIsDesktop => Platform.isWindows || Platform.isLinux || Platform.isMacOS;

/// What to call the machine the app runs on, for UI text.
String get kickbackDeviceNoun => kickbackIsDesktop ? 'PC' : 'phone';

/// Call once, after WidgetsFlutterBinding.ensureInitialized() and before the
/// identity or event store is first opened.
Future<void> initKickBackPlatform() async {
  if (!(Platform.isWindows || Platform.isLinux)) return;
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;
  final base = Platform.isWindows
      ? (Platform.environment['APPDATA'] ?? Directory.current.path)
      : (Platform.environment['XDG_DATA_HOME'] ??
          '${Platform.environment['HOME'] ?? Directory.current.path}/.local/share');
  final sep = Platform.pathSeparator;
  final dir = Directory('$base${sep}TheOmniverse${sep}KickBack');
  try {
    await dir.create(recursive: true);
    await databaseFactory.setDatabasesPath(dir.path);
  } catch (_) {
    // Keep sqflite_common_ffi's default location if AppData is not writable.
  }
}
