import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

/// One on-device SQLite file for the app core (identity + local events).
class OmniCoreDb {
  static Database? _db;

  static Future<Database> open() async {
    if (_db != null) return _db!;
    final dir = await getDatabasesPath();
    _db = await openDatabase(
      p.join(dir, 'omni_core.db'),
      version: 1,
      onCreate: (db, _) async {
        await db.execute('CREATE TABLE kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)');
        await db.execute('''
          CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            action TEXT NOT NULL,
            author_pubkey TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            timestamp REAL NOT NULL,
            payload_json TEXT NOT NULL,
            signature TEXT NOT NULL,
            synced INTEGER NOT NULL DEFAULT 0,
            hub_event_id TEXT
          )''');
      },
    );
    return _db!;
  }
}
