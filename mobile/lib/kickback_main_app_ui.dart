import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:omni_core_ui/omni_core_ui.dart';

import 'kickback_app_lock.dart';
import 'kickback_secure_identity.dart';

/// ============================================================================
/// THE KICKBACK SOCIAL NETWORK UI
/// ============================================================================
/// What is real here:
/// - Posts are signed with this install's Ed25519 identity (omni_core_ui
///   StargateIdentity, canonical int-ms "ts" form that matches the daemon's
///   Admin/omni_signing.py byte for byte) and stored in the on-device SQLite log
///   (LocalEventStore). The feed is loaded from that log on every start.
/// - Each post is then handed to the local Omni-Hub daemon over loopback
///   (POST 127.0.0.1:5000/api/events/append). The daemon re-signs it as the node
///   and relays it to peers; the app's own signature travels inside the payload.
/// - The header reads the daemon's real node-health telemetry
///   (GET 127.0.0.1:9100/api/v1/telemetry/node-health): reachable or not, peers.
/// - The app is locked behind fingerprint / face / device PIN (kickback_app_lock.dart).
///
/// - Other people's posts come from the daemon's event feed
///   (GET 127.0.0.1:5000/api/events/feed, daemon v8.6.0+): posts its peers sent
///   over P2P sync. They are merged with this device's log (deduped by the app
///   event id), refreshed every 5 s with ?since=<last row id> and on
///   pull-to-refresh. Each one is re-verified on this phone (Ed25519 over the
///   author's app envelope, or the relaying node's signature if there is none)
///   and marked Verified / Unverified; the daemon's own "verified" flag is not
///   trusted.
/// - If the daemon is offline or older than v8.6.0 (no feed endpoint, HTTP 404),
///   the app keeps showing this device's own posts and says why.
///
/// Not here yet (shown honestly instead of faked):
/// - Peers are only whoever the daemon syncs with; there is no account,
///   follow list or discovery in the app.
/// - Payments: "Payments coming soon". No purchase, no coin balance.
/// - Hardware attestation / Play Integrity: not implemented.
/// ============================================================================

const String kPostAction = 'KICKBACK_POST';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Must be set before the identity is first loaded.
  StargateIdentity.seedStore = SecureStorageSeedStore();
  runApp(const KickBackApp());
}

class KickBackApp extends StatelessWidget {
  const KickBackApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'The KickBack',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        primaryColor: const Color(0xFF6200EE),
        scaffoldBackgroundColor: const Color(0xFF121212),
        cardColor: const Color(0xFF1E1E1E),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFFBB86FC),
          secondary: Color(0xFF03DAC6),
          surface: Color(0xFF1E1E1E),
        ),
      ),
      home: const KickBackLockGate(child: KickBackMainScreen()),
    );
  }
}

class KickBackMainScreen extends StatefulWidget {
  const KickBackMainScreen({super.key});

  @override
  State<KickBackMainScreen> createState() => _KickBackMainScreenState();
}

class _KickBackMainScreenState extends State<KickBackMainScreen> {
  static const Color _teal = Color(0xFF03DAC6);
  static const Color _purple = Color(0xFFBB86FC);
  static const Color _amber = Color(0xFFFFC107);
  static const Color _red = Color(0xFFFF5370);

  final TextEditingController _postController = TextEditingController();
  final LocalEventStore _store = LocalEventStore();
  final OmniHubClient _hub = const OmniHubClient();

  List<OmniEvent> _posts = [];
  final Map<String, bool> _sigOk = {};

  // Daemon feed (other phones' posts). Keyed by HubFeedEvent.dedupeKey.
  static const int _maxHubEvents = 500;
  final Map<String, HubFeedEvent> _hubEvents = {};
  final Map<String, FeedVerification> _hubVerified = {};
  int _hubCursor = 0; // highest daemon row id seen; 0 = not loaded yet
  HubFeedState? _feedState; // null = not checked yet
  String? _feedError;
  bool _loading = true;
  String? _loadError;
  bool _isPublishing = false;

  StargateIdentity? _identity;
  HubStatus? _hubStatus; // null = not checked yet
  int? _daemonEventCount;
  HubSyncResult? _lastSync;
  int _pending = 0;
  Timer? _timer;
  bool _polling = false;

  @override
  void initState() {
    super.initState();
    _init();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _postController.dispose();
    super.dispose();
  }

  Future<void> _init() async {
    try {
      _identity = await StargateIdentity.load();
      await _loadFeed();
    } catch (e) {
      if (mounted) setState(() => _loadError = '$e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
    await _pollHub();
    _timer = Timer.periodic(const Duration(seconds: 5), (_) => _pollHub());
  }

  Future<void> _loadFeed() async {
    final posts = await _store.recent(limit: 200, action: kPostAction);
    final pending = await _store.pendingCount();
    for (final p in posts) {
      if (!_sigOk.containsKey(p.eventId)) {
        _sigOk[p.eventId] = await StargateIdentity.verify(p.toEnvelope());
      }
    }
    if (!mounted) return;
    setState(() {
      _posts = posts;
      _pending = pending;
    });
  }

  /// Pulls new posts from the daemon feed. Keeps what it already has when the
  /// daemon is offline, too old, or errors, so the local feed always shows.
  Future<void> _refreshHubFeed() async {
    final first = _hubCursor == 0;
    final r = first
        ? await _hub.eventsFeed(limit: 100, type: kPostAction)
        : await _hub.eventsFeed(limit: 200, since: _hubCursor, type: kPostAction);
    if (r.state == HubFeedState.ok) {
      for (final e in r.events) {
        if (!_hubVerified.containsKey(e.dedupeKey)) {
          _hubVerified[e.dedupeKey] = await verifyHubEvent(e);
        }
        _hubEvents[e.dedupeKey] = e;
      }
      final top = r.maxEventId;
      if (top > _hubCursor) _hubCursor = top;
      if (first && _hubCursor == 0 && r.latestId > 0) _hubCursor = r.latestId;
      if (_hubEvents.length > _maxHubEvents) {
        final byAge = _hubEvents.values.toList()..sort((a, b) => a.tsMs.compareTo(b.tsMs));
        for (final e in byAge.take(_hubEvents.length - _maxHubEvents)) {
          _hubEvents.remove(e.dedupeKey);
          _hubVerified.remove(e.dedupeKey);
        }
      }
    }
    if (!mounted) return;
    setState(() {
      _feedState = r.state;
      _feedError = r.error;
    });
  }

  Future<void> _refreshAll() async {
    await _pollHub();
    await _loadFeed();
  }

  /// Reads daemon health, pushes any posts still waiting, then pulls the feed.
  Future<void> _pollHub() async {
    if (_polling) return;
    _polling = true;
    try {
      final status = await _hub.status();
      int? count;
      HubSyncResult? sync;
      if (status.online) {
        final stats = await _hub.eventStats();
        final n = stats?['total_events'];
        count = n is int ? n : int.tryParse('${n ?? ''}');
        if (await _store.pendingCount() > 0) {
          sync = await _store.syncToHubDetailed(_hub);
        }
      }
      if (!mounted) return;
      setState(() {
        _hubStatus = status;
        _daemonEventCount = count;
        if (sync != null) _lastSync = sync;
      });
      if (sync != null && sync.sent > 0) await _loadFeed();
      if (mounted) {
        final pending = await _store.pendingCount();
        if (mounted) setState(() => _pending = pending);
      }
      // Tried even when :9100 telemetry is down: the feed lives on :5000.
      await _refreshHubFeed();
    } catch (_) {
      // Never let one failed poll stop the timer from trying again.
    } finally {
      _polling = false;
    }
  }

  Future<void> _publishLocalPost() async {
    final text = _postController.text.trim();
    if (text.isEmpty || _isPublishing) return;

    // Signing uses the identity key, so require a recent unlock first.
    final auth = await AppLock.ensureRecentUnlock('Confirm it\'s you to sign this post');
    if (!auth.ok) {
      _snack(auth.message ?? 'Post not signed: not unlocked', _red);
      return;
    }

    setState(() => _isPublishing = true);
    try {
      final ev = await _store.append(kPostAction, {'text': text, 'app': 'kickback'});
      _postController.clear();
      await _loadFeed();

      final sync = await _store.syncToHubDetailed(_hub);
      final status = sync.hubReachable ? await _hub.status() : const HubStatus(online: false, peers: 0);
      if (!mounted) return;
      setState(() {
        _lastSync = sync;
        _hubStatus = status;
      });
      await _loadFeed();
      final sent = _posts.any((p) => p.eventId == ev.eventId && p.synced);
      if (sent) {
        _snack('Signed, saved on this device and sent to the local daemon.', _teal);
      } else if (!sync.hubReachable) {
        _snack('Signed and saved on this device. Daemon offline: it will be sent when the daemon is running.', _amber);
      } else {
        _snack('Signed and saved on this device. The daemon refused it: ${sync.error ?? 'unknown error'}', _red);
      }
    } catch (e) {
      _snack('Could not save the post: $e', _red);
    } finally {
      if (mounted) setState(() => _isPublishing = false);
    }
  }

  void _snack(String msg, Color color) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg, style: const TextStyle(color: Colors.black)),
      backgroundColor: color,
      duration: const Duration(seconds: 3),
    ));
  }

  // ---------------------------------------------------------------------------
  // Header status (from node-health telemetry, never hardcoded)
  // ---------------------------------------------------------------------------
  ({String text, Color color}) _headerStatus() {
    final s = _hubStatus;
    if (s == null) return (text: 'Checking local daemon…', color: Colors.grey);
    if (!s.online) {
      return (text: 'Daemon offline • posts stay on this device', color: _amber);
    }
    final peers = s.peers == 0 ? 'no peers yet' : '${s.peers} peer${s.peers == 1 ? '' : 's'}';
    final v = s.version != null ? ' v${s.version}' : '';
    return (text: 'Daemon$v online • $peers', color: _teal);
  }

  @override
  Widget build(BuildContext context) {
    final header = _headerStatus();
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('The KickBack', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            Text(
              _pending > 0 ? '${header.text} • $_pending waiting' : header.text,
              style: TextStyle(color: header.color, fontSize: 11, fontWeight: FontWeight.w500),
            ),
          ],
        ),
        backgroundColor: const Color(0xFF1F1F1F),
        elevation: 2,
        actions: [
          IconButton(
            icon: const Icon(Icons.account_balance_wallet_outlined, color: _purple),
            tooltip: 'Wallet',
            onPressed: () => _showWalletModal(context),
          ),
          IconButton(
            icon: const Icon(Icons.info_outline, color: _teal),
            tooltip: 'Identity & node',
            onPressed: () => _showNodeInfoModal(context),
          ),
        ],
      ),
      body: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            color: const Color(0xFF1E1E1E),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _postController,
                    maxLines: null,
                    style: const TextStyle(color: Colors.white, fontSize: 14),
                    decoration: InputDecoration(
                      hintText: 'Share something…',
                      hintStyle: const TextStyle(color: Colors.grey),
                      filled: true,
                      fillColor: const Color(0xFF2C2C2C),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                _isPublishing
                    ? const SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(strokeWidth: 2, color: _purple),
                      )
                    : IconButton(
                        icon: const Icon(Icons.send_rounded, color: _purple),
                        tooltip: 'Sign & post',
                        onPressed: _publishLocalPost,
                      ),
              ],
            ),
          ),
          const Divider(height: 1, color: Color(0xFF333333)),
          Expanded(child: _buildFeed()),
        ],
      ),
    );
  }

  Widget _buildFeed() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator(color: _purple));
    }
    if (_loadError != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text('Could not open the on-device feed:\n$_loadError',
              textAlign: TextAlign.center, style: const TextStyle(color: _red)),
        ),
      );
    }
    final entries = mergeFeed(_posts, _hubEvents.values);
    final notice = _feedNotice();
    if (entries.isEmpty) {
      // Pull-to-refresh works on the empty screen too.
      return RefreshIndicator(
        onRefresh: _refreshAll,
        child: LayoutBuilder(
          builder: (context, constraints) => ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            children: [
              ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: _buildZeroStateView(),
              ),
            ],
          ),
        ),
      );
    }
    final offset = notice == null ? 0 : 1;
    return RefreshIndicator(
      onRefresh: _refreshAll,
      child: ListView.builder(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(12),
        itemCount: entries.length + offset,
        itemBuilder: (context, index) {
          if (notice != null && index == 0) return _buildNotice(notice);
          final entry = entries[index - offset];
          final local = entry.local;
          if (local != null) return _buildEventCard(local);
          return _buildHubCard(entry.hub!);
        },
      ),
    );
  }

  /// Why other people's posts may be missing, or null when the feed is fine.
  ({String text, Color color})? _feedNotice() {
    switch (_feedState) {
      case HubFeedState.unsupported:
        return (
          text: 'The local daemon is too old to share posts (needs v8.6.0+). Showing this device\'s posts only.',
          color: _amber,
        );
      case HubFeedState.unreachable:
        return (
          text: 'Local daemon not reachable. Showing this device\'s posts${_hubEvents.isEmpty ? '' : ' and posts already received'}.',
          color: _amber,
        );
      case HubFeedState.error:
        return (text: 'Could not read the shared feed: ${_feedError ?? 'unknown error'}', color: _red);
      default:
        return null;
    }
  }

  Widget _buildNotice(({String text, Color color}) n) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Icon(Icons.info_outline, size: 14, color: n.color),
          const SizedBox(width: 6),
          Expanded(child: Text(n.text, style: TextStyle(fontSize: 11, color: n.color))),
        ],
      ),
    );
  }

  Widget _buildHubCard(HubFeedEvent e) {
    final key = e.displayAuthor;
    final mine = _identity != null && key == _identity!.pubkeyHex;
    final author = mine
        ? 'You (${_identity!.shortId})'
        : key.length > 8
            ? '${key.substring(0, 4)}…${key.substring(key.length - 4)}'
            : key;
    final v = _hubVerified[e.dedupeKey];
    final bool ok = v == FeedVerification.appSigned || v == FeedVerification.nodeSigned;
    final String markText = v == null
        ? 'Checking…'
        : v == FeedVerification.appSigned
            ? 'Verified'
            : v == FeedVerification.nodeSigned
                ? 'Verified (relay)'
                : 'Unverified';
    final String markTip = v == FeedVerification.appSigned
        ? 'This phone checked the author\'s Ed25519 signature over this exact post'
        : v == FeedVerification.nodeSigned
            ? 'No author signature; the relaying daemon\'s Ed25519 signature checks out'
            : 'No valid signature for this content: it may have been altered';
    final Color markColor = v == null ? Colors.grey : (ok ? _teal : _red);
    final String origin = e.origin == 'local' ? 'Via this phone\'s daemon' : 'From a peer';

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const CircleAvatar(
                  radius: 16,
                  backgroundColor: _teal,
                  child: Icon(Icons.person_outline, size: 18, color: Colors.black),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(author, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                      Text(_formatTime(e.time), style: const TextStyle(fontSize: 10, color: Colors.grey)),
                    ],
                  ),
                ),
                Tooltip(
                  message: markTip,
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon(ok ? Icons.verified_user_outlined : Icons.gpp_bad_outlined, size: 14, color: markColor),
                    const SizedBox(width: 4),
                    Text(markText, style: TextStyle(fontSize: 10, color: markColor)),
                  ]),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(e.text, style: const TextStyle(fontSize: 14, color: Colors.white, height: 1.3)),
            const SizedBox(height: 10),
            Row(
              children: [
                const Icon(Icons.hub_outlined, size: 13, color: Colors.grey),
                const SizedBox(width: 4),
                Expanded(child: Text(origin, style: const TextStyle(fontSize: 11, color: Colors.grey))),
                InkWell(
                  onTap: () {
                    Clipboard.setData(ClipboardData(text: e.dedupeKey));
                    _snack('Event hash copied', _teal);
                  },
                  child: Text(
                    _shortHash(e.dedupeKey),
                    style: const TextStyle(fontSize: 10, color: Colors.grey, fontFamily: 'monospace'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildZeroStateView() {
    final daemonLine = _hubStatus == null
        ? 'Checking for the local daemon…'
        : _hubStatus!.online
            ? 'Local daemon is running${_daemonEventCount != null ? ' ($_daemonEventCount events in its log)' : ''}.'
            : 'Local daemon is not running. Posts will be saved on this device and sent when it starts.';
    final feedLine = switch (_feedState) {
      HubFeedState.ok => 'Posts from other phones on the mesh will show up here.',
      HubFeedState.unsupported => 'This daemon is too old to share posts (needs v8.6.0+).',
      HubFeedState.error => 'Could not read the shared feed: ${_feedError ?? 'unknown error'}',
      _ => '',
    };
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: const Color(0xFF1E1E1E),
                shape: BoxShape.circle,
                border: Border.all(color: _teal.withOpacity(0.4), width: 2),
              ),
              child: const Icon(Icons.edit_note, size: 48, color: _teal),
            ),
            const SizedBox(height: 20),
            const Text(
              'No posts yet',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(height: 8),
            Text(
              'Posts you write are signed with this phone\'s key and kept in its local log.\n$daemonLine'
              '${feedLine.isEmpty ? '' : '\n$feedLine'}\nPull down to refresh.',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 13, color: Colors.grey, height: 1.4),
            ),
          ],
        ),
      ),
    );
  }

  ({String text, Color color, IconData icon}) _postStatus(OmniEvent e) {
    if (e.synced) return (text: 'Sent to daemon', color: _teal, icon: Icons.cloud_done_outlined);
    if (_hubStatus != null && !_hubStatus!.online) {
      return (text: 'Saved on device • Daemon offline', color: _amber, icon: Icons.cloud_off);
    }
    if (_lastSync?.error != null) {
      return (text: 'Saved on device • daemon refused', color: _red, icon: Icons.error_outline);
    }
    return (text: 'Saved on device', color: Colors.grey, icon: Icons.phone_android);
  }

  String _shortHash(String h) => h.length > 18 ? '${h.substring(0, 10)}…${h.substring(h.length - 6)}' : h;

  String _formatTime(DateTime t) {
    String two(int n) => n.toString().padLeft(2, '0');
    return '${t.year}-${two(t.month)}-${two(t.day)} ${two(t.hour)}:${two(t.minute)}';
  }

  Widget _buildEventCard(OmniEvent e) {
    final mine = _identity != null && e.authorPubkey == _identity!.pubkeyHex;
    final author = mine
        ? 'You (${_identity!.shortId})'
        : '${e.authorPubkey.substring(0, 4)}…${e.authorPubkey.substring(e.authorPubkey.length - 4)}';
    final sigOk = _sigOk[e.eventId];
    final status = _postStatus(e);
    final text = '${e.payload['text'] ?? ''}';

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const CircleAvatar(
                  radius: 16,
                  backgroundColor: _purple,
                  child: Icon(Icons.person, size: 18, color: Colors.black),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(author, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                      Text(_formatTime(e.time), style: const TextStyle(fontSize: 10, color: Colors.grey)),
                    ],
                  ),
                ),
                // Backed by a real Ed25519 check of the stored envelope.
                if (sigOk != null)
                  Tooltip(
                    message: sigOk
                        ? 'Ed25519 signature checks out for this author key'
                        : 'Signature does not match the content',
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      Icon(sigOk ? Icons.verified_user_outlined : Icons.gpp_bad_outlined,
                          size: 14, color: sigOk ? _teal : _red),
                      const SizedBox(width: 4),
                      Text(sigOk ? 'Signed' : 'Bad signature',
                          style: TextStyle(fontSize: 10, color: sigOk ? _teal : _red)),
                    ]),
                  ),
              ],
            ),
            const SizedBox(height: 10),
            Text(text, style: const TextStyle(fontSize: 14, color: Colors.white, height: 1.3)),
            const SizedBox(height: 10),
            Row(
              children: [
                Icon(status.icon, size: 13, color: status.color),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(status.text, style: TextStyle(fontSize: 11, color: status.color)),
                ),
                InkWell(
                  onTap: () {
                    Clipboard.setData(ClipboardData(text: e.eventId));
                    _snack('Event hash copied', _teal);
                  },
                  child: Text(
                    _shortHash(e.eventId),
                    style: const TextStyle(fontSize: 10, color: Colors.grey, fontFamily: 'monospace'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _showWalletModal(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1E1E1E),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Wallet',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF2C2C2C),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.schedule, color: _amber),
                    SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Payments coming soon. Coins can\'t be bought yet and there is no coin balance.',
                        style: TextStyle(color: Colors.grey, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              const SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: null, // disabled until real checkout exists
                  child: Text('Buy coins (coming soon)'),
                ),
              ),
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Close'),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  void _showNodeInfoModal(BuildContext context) {
    final s = _hubStatus;
    String daemon;
    if (s == null) {
      daemon = 'checking…';
    } else if (!s.online) {
      daemon = 'offline (nothing answering on 127.0.0.1:9100)';
    } else {
      daemon = 'online${s.version != null ? ' v${s.version}' : ''}, ${s.peers} peer(s)'
          '${s.meshId != null ? ', mesh "${s.meshId}"' : ''}';
    }
    Widget row(String k, String v, {Color color = Colors.grey}) => Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(width: 110, child: Text(k, style: const TextStyle(color: Colors.white70, fontSize: 12))),
            Expanded(child: SelectableText(v, style: TextStyle(color: color, fontSize: 12))),
          ]),
        );
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1E1E1E),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Identity & node',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
              const SizedBox(height: 12),
              row('Your key', _identity?.pubkeyHex ?? 'loading…'),
              row('Key storage', 'Android Keystore-encrypted storage (flutter_secure_storage)'),
              row('App lock', AppLock.unprotected
                  ? 'No screen lock on this phone: app can\'t be locked'
                  : 'Fingerprint / face / device PIN',
                  color: AppLock.unprotected ? _amber : _teal),
              row('Local daemon', daemon, color: s?.online == true ? _teal : _amber),
              if (s?.nodeId != null) row('Daemon node', s!.nodeId!),
              if (_daemonEventCount != null) row('Daemon log', '$_daemonEventCount events'),
              row(
                'Shared feed',
                switch (_feedState) {
                  null => 'checking…',
                  HubFeedState.ok => '${_hubEvents.length} post(s) from the daemon feed',
                  HubFeedState.unsupported => 'daemon too old (needs v8.6.0+ for /api/events/feed)',
                  HubFeedState.unreachable => 'offline (nothing answering on 127.0.0.1:5000)',
                  HubFeedState.error => 'error: ${_feedError ?? 'unknown'}',
                },
                color: _feedState == HubFeedState.ok ? _teal : _amber,
              ),
              row('Waiting to send', '$_pending post(s)'),
              if (_lastSync?.error != null) row('Last refusal', _lastSync!.error!, color: _red),
              row('Attestation', 'Not implemented (no Play Integrity / hardware attestation yet)'),
              const SizedBox(height: 8),
            ],
          ),
        );
      },
    );
  }
}
