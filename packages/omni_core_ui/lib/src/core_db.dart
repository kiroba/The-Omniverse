import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

/// SQL run once when upgrading to schema v3: marks every local event unsynced so the next sync
/// re-sends it with a real body. The daemon's earlier copies were empty USER_ACTION rows, so the
/// re-send is the first real copy (a hub that did get it re-signs a second node copy; the app feed
/// dedupes by app_event_id).
const String resyncAfterEmptyAppendBug = 'UPDATE events SET synced = 0, hub_event_id = NULL';

/// One on-device SQLite file for the app core (identity + local events).
class OmniCoreDb {
  static Database? _db;

  static Future<Database> open() async {
    if (_db != null) return _db!;
    final dir = await getDatabasesPath();
    _db = await openDatabase(
      p.join(dir, 'omni_core.db'),
      version: 3,
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
            hub_event_id TEXT,
            ts_ms INTEGER
          )''');
      },
      // v2: ts_ms = exact signed integer-ms time (NULL for legacy float events).
      // v3: re-send everything once. Before v3 the hub client sent bodies chunked with no
      // Content-Length and every daemon up to v8.12.0 stored them as EMPTY events while answering
      // SUCCESS, so rows marked synced never really reached the hub (see [resyncAfterEmptyAppendBug]).
      onUpgrade: (db, oldVersion, _) async {
        if (oldVersion < 2) {
          await db.execute('ALTER TABLE events ADD COLUMN ts_ms INTEGER');
        }
        if (oldVersion < 3) {
          await db.execute(resyncAfterEmptyAppendBug);
        }
      },
    );
    return _db!;
  }
}
