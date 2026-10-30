// omni_signal_client.dart - OmniCast step 2: Dart client for the hub's
// signed WebRTC signaling mailbox (daemon v8.11.0+, desktop branch).
//
// Server side and the exact wire format: Admin/docs/OMNICAST_SIGNALING.md and
// Admin/omni_live_daemon_server.py (signal_send_bytes / signal_auth_bytes) on
// the `desktop` branch.
//
//   POST :5000/api/signal/send        drop a signed message in a peer's mailbox
//   GET  :5000/api/signal/poll        drain my mailbox (recipient-signed, long-poll <= 25 s)
//   GET  :5000/api/signal/ice-config  STUN + short-lived TURN credential
//
// Signing: Ed25519 over compact JSON with the keys in sorted order, raw UTF-8
// (Python: json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)).
// Dart's jsonEncode emits the same bytes when the map is built in sorted key
// order, which is what [signalSendBytes] / [signalAuthBytes] do. The shared
// test vectors (generated with the daemon's own Python functions) are in
// packages/omni_core_ui/test/omni_signal_client_test.dart and
// tests/test_signal_mailbox.py on desktop.
//
// Identity: this file holds NO key. The app passes its existing identity in:
//   final id = await StargateIdentity.load();           // the app's one identity
//   final c = await HubSettingsStore.load();            // Settings > Hub
//   final hub = c.client();                             // This phone or Remote hub
//   final signal = OmniSignalClient(
//     hub: SignalHub(host: hub.host, ipcPort: hub.ipcPort, token: hub.token),
//     pubkeyHex: id.pubkeyHex,
//     sign: id.signBytes,
//   );
// "This phone" is 127.0.0.1:5000 with no token; a remote hub gets
// "Authorization: Bearer <token>" on every call (same rule as
// omni_bug_report.dart's hub POST and OmniHubClient).
//
// Pure Dart (dart:io + package:cryptography, both already in every generated
// app): no Flutter import, so it is unit-testable without a device. Not wired
// into any app yet and no flutter_webrtc here (OmniCast steps 3/4).
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:cryptography/cryptography.dart';

const String kSignalSendType = 'omnicast.signal.v1';
const String kSignalPollType = 'omnicast.poll.v1';
const String kSignalIceType = 'omnicast.ice-config.v1';

/// Signs raw bytes with the app's identity key; returns a 128-char hex
/// Ed25519 signature. Pass `StargateIdentity.signBytes`.
typedef SignalSignFn = Future<String> Function(List<int> message);

/// Message kinds the hub accepts.
enum SignalKind { offer, answer, ice, hangup, ring }

SignalKind? signalKindFromWire(Object? s) {
  for (final k in SignalKind.values) {
    if (k.name == s) return k;
  }
  return null;
}

/// Limits and timing for OmniCast calls. The hub-side values mirror the daemon
/// (v8.11.0); the call-side values are this client's choices.
class OmniCastTimeouts {
  OmniCastTimeouts._();

  // Hub limits (daemon v8.11.0).
  static const Duration hubMessageTtl = Duration(seconds: 60); // undelivered messages die
  static const Duration hubTsWindow = Duration(seconds: 120); // request ts vs hub clock
  static const int maxPayloadChars = 14 * 1024; // code points (Python len)
  static const int maxBodyBytes = 16 * 1024;
  static const int maxLongPollSeconds = 25;

  // Call flow (client policy).
  /// Caller gives up when no answer (or hangup) arrives in this time. Kept
  /// under [hubMessageTtl] so the last offer copy is still deliverable.
  static const Duration ringTimeout = Duration(seconds: 45);

  /// Delivery is at-most-once (a lost poll response loses the message), so the
  /// caller re-sends the offer at this interval until answered.
  static const Duration offerResendInterval = Duration(seconds: 5);

  /// Most offer copies sent per call (first send included).
  static const int offerMaxSends = 6;

  /// Callee: how long a remembered answer is re-sent for duplicate offers.
  static const Duration answerCacheTtl = Duration(seconds: 90);

  /// Messages whose signed ts is further than this from our (hub-corrected)
  /// clock are dropped on receipt: hub ts window + message TTL + slack.
  static const Duration receiveMaxAge = Duration(seconds: 200);

  /// Poll loop backoff after a failed poll.
  static const Duration pollBackoffMin = Duration(seconds: 1);
  static const Duration pollBackoffMax = Duration(seconds: 30);

  /// Minimum gap between two polls that both came back empty early (the hub
  /// answers at once when its 64 long-poll slots are full).
  static const Duration pollMinGap = Duration(seconds: 1);

  /// Per-request timeouts.
  static const Duration requestTimeout = Duration(seconds: 8);
  static const Duration longPollSlack = Duration(seconds: 10);
}

final RegExp _pubkeyRe = RegExp(r'^[0-9a-f]{64}$');
final RegExp _sigRe = RegExp(r'^[0-9a-f]{128}$');
final RegExp _callIdRe = RegExp(r'^[A-Za-z0-9_.:\-]{1,64}$');

bool isValidSignalPubkey(String s) => _pubkeyRe.hasMatch(s);
bool isValidCallId(String s) => _callIdRe.hasMatch(s);

/// A random call id (16 hex chars after "call-"), valid for the hub's regex.
String newCallId([Random? rnd]) {
  final r = rnd ?? Random.secure();
  final b = List<int>.generate(8, (_) => r.nextInt(256));
  return 'call-${_hex(b)}';
}

/// Exact bytes the sender signs for POST /api/signal/send. Mirrors the
/// daemon's signal_send_bytes: keys in sorted order (call_id, from, kind,
/// payload, to, ts, type), compact, raw UTF-8, integer-ms ts.
List<int> signalSendBytes({
  required String to,
  required String from,
  required String callId,
  required String kind,
  required String payload,
  required int ts,
}) {
  final m = <String, Object>{
    'call_id': callId,
    'from': from,
    'kind': kind,
    'payload': payload,
    'to': to,
    'ts': ts,
    'type': kSignalSendType,
  };
  return utf8.encode(jsonEncode(m));
}

/// Exact bytes a key owner signs for a poll ([kSignalPollType], field "to")
/// or an ice-config request ([kSignalIceType], field "pubkey").
List<int> signalAuthBytes(String type, String pubkey, int ts) {
  final field = type == kSignalPollType ? 'to' : 'pubkey';
  // Sorted: "pubkey"/"to" < "ts" < "type".
  final m = <String, Object>{field: pubkey, 'ts': ts, 'type': type};
  return utf8.encode(jsonEncode(m));
}

/// True when [s] has an unpaired UTF-16 surrogate. Dart's jsonEncode escapes
/// one as \udXXX while Python (ensure_ascii=False) can't encode it at all, so
/// the signed bytes could never match: refuse such payloads up front.
bool hasLoneSurrogate(String s) {
  final u = s.codeUnits;
  for (var i = 0; i < u.length; i++) {
    final c = u[i];
    if (c >= 0xD800 && c <= 0xDBFF) {
      if (i + 1 < u.length && u[i + 1] >= 0xDC00 && u[i + 1] <= 0xDFFF) {
        i++;
        continue;
      }
      return true;
    }
    if (c >= 0xDC00 && c <= 0xDFFF) return true;
  }
  return false;
}

/// One delivered (and, when it reaches you through [OmniSignalClient.messages],
/// already verified) signaling message.
class SignalMessage {
  final int seq;
  final String from;
  final String to;
  final String callId;
  final SignalKind kind;
  final String payload;
  final int ts;
  final String sig;

  const SignalMessage({
    required this.seq,
    required this.from,
    required this.to,
    required this.callId,
    required this.kind,
    required this.payload,
    required this.ts,
    required this.sig,
  });

  /// Parses one entry of a poll response. Null if any field is missing or
  /// malformed (such a message is dropped, never surfaced).
  static SignalMessage? tryParse(Object? j) {
    if (j is! Map) return null;
    final seq = j['seq'], from = j['from'], to = j['to'], callId = j['call_id'];
    final kind = signalKindFromWire(j['kind']);
    final payload = j['payload'], ts = j['ts'], sig = j['sig'];
    if (seq is! int || from is! String || to is! String || callId is! String) return null;
    if (kind == null || payload is! String || ts is! int || sig is! String) return null;
    if (!_pubkeyRe.hasMatch(from) || !_pubkeyRe.hasMatch(to)) return null;
    if (!_callIdRe.hasMatch(callId) || !_sigRe.hasMatch(sig)) return null;
    return SignalMessage(
        seq: seq, from: from, to: to, callId: callId, kind: kind, payload: payload, ts: ts, sig: sig);
  }

  List<int> get signedBytes =>
      signalSendBytes(to: to, from: from, callId: callId, kind: kind.name, payload: payload, ts: ts);

  /// True only if [sig] is `from`'s Ed25519 signature over the canonical
  /// fields. The hub checked it too; this re-check means a hub can't alter an
  /// SDP (e.g. swap the DTLS fingerprint) or forge a sender.
  Future<bool> verify() => verifySignalSignature(signedBytes, sig, from);

  /// For an `ice` message: the candidate map
  /// ({"candidate", "sdpMid", "sdpMLineIndex"}), or null if not valid JSON.
  Map<String, dynamic>? get iceCandidate {
    if (kind != SignalKind.ice) return null;
    try {
      final d = jsonDecode(payload);
      return d is Map<String, dynamic> ? d : null;
    } catch (_) {
      return null;
    }
  }

  @override
  String toString() => 'SignalMessage(${kind.name} $callId from ${from.substring(0, 8)}… seq $seq)';
}

final Ed25519 _ed25519 = Ed25519();

/// Verifies a hex Ed25519 signature over [message] by the 64-hex [pubkeyHex].
Future<bool> verifySignalSignature(List<int> message, String sigHex, String pubkeyHex) async {
  try {
    if (!_pubkeyRe.hasMatch(pubkeyHex) || !_sigRe.hasMatch(sigHex)) return false;
    return await _ed25519.verify(
      message,
      signature: Signature(_unhex(sigHex),
          publicKey: SimplePublicKey(_unhex(pubkeyHex), type: KeyPairType.ed25519)),
    );
  } catch (_) {
    return false;
  }
}

/// Which hub to talk to. `host` 127.0.0.1 / localhost / ::1 / empty means
/// "This phone" (no token sent). Build it from HubSettings.client().
class SignalHub {
  final String host;
  final int ipcPort;
  final String? token;

  const SignalHub({this.host = '127.0.0.1', this.ipcPort = 5000, this.token});

  const SignalHub.loopback({this.ipcPort = 5000})
      : host = '127.0.0.1',
        token = null;

  bool get isRemote =>
      !(host.isEmpty || host == '127.0.0.1' || host == 'localhost' || host == '::1');

  String get _h => host.isEmpty ? '127.0.0.1' : host;

  Uri uri(String path, [Map<String, String>? query]) =>
      Uri(scheme: 'http', host: _h, port: ipcPort, path: path, queryParameters: query);

  /// The bearer header value, only for a remote hub with a token.
  String? get authorization {
    final t = token;
    return isRemote && t != null && t.isNotEmpty ? 'Bearer $t' : null;
  }
}

/// Result of [OmniSignalClient.send]. Never thrown: check [ok].
class SignalSendResult {
  final bool ok;
  final int statusCode; // 0 = hub unreachable
  final int? seq;
  final String? error;

  const SignalSendResult({required this.ok, required this.statusCode, this.seq, this.error});

  /// Worth trying again shortly (rate limit, full mailbox, hub busy or down).
  bool get retryable => !ok && (statusCode == 0 || statusCode == 429 || statusCode == 503);

  /// The hub refused our bearer token (remote) or isn't in remote mode.
  bool get hubAuthProblem => statusCode == 403 || (statusCode == 401 && (error ?? '').contains('token'));

  @override
  String toString() => ok ? 'QUEUED seq $seq' : 'HTTP $statusCode: $error';
}

/// ICE settings from GET /api/signal/ice-config.
class SignalIceConfig {
  /// Ready for flutter_webrtc: [{"urls": [...]}, {"urls": [...], "username", "credential"}].
  final List<Map<String, dynamic>> iceServers;

  /// "relay" when the hub has TURN (testers can only reach the hub), else "all".
  final String iceTransportPolicy;
  final bool turn;
  final int? expiresAt; // unix seconds, TURN credential expiry
  final String? warning;

  const SignalIceConfig({
    required this.iceServers,
    required this.iceTransportPolicy,
    required this.turn,
    this.expiresAt,
    this.warning,
  });

  /// The configuration map for flutter_webrtc's createPeerConnection(config).
  Map<String, dynamic> get rtcConfiguration => {
        'iceServers': iceServers,
        'iceTransportPolicy': iceTransportPolicy,
        'sdpSemantics': 'unified-plan',
      };

  static SignalIceConfig? tryParse(Object? j) {
    if (j is! Map || j['status'] != 'OK' || j['ice_servers'] is! List) return null;
    final servers = <Map<String, dynamic>>[];
    for (final s in j['ice_servers'] as List) {
      if (s is! Map) continue;
      final raw = s['urls'];
      final urls = raw is String
          ? <String>[raw]
          : raw is List
              ? raw.whereType<String>().toList()
              : <String>[];
      if (urls.isEmpty) continue;
      final m = <String, dynamic>{'urls': urls};
      if (s['username'] is String) m['username'] = s['username'];
      if (s['credential'] is String) m['credential'] = s['credential'];
      servers.add(m);
    }
    if (servers.isEmpty) return null;
    final policy = j['ice_transport_policy'] == 'relay' ? 'relay' : 'all';
    return SignalIceConfig(
      iceServers: servers,
      iceTransportPolicy: policy,
      turn: j['turn'] == true,
      expiresAt: j['expires_at'] is int ? j['expires_at'] as int : null,
      warning: j['warning'] is String ? j['warning'] as String : null,
    );
  }
}

/// A hub problem worth showing the user (added as an error event on
/// [OmniSignalClient.messages]; the poll loop keeps retrying with backoff).
class SignalHubException implements Exception {
  final int statusCode; // 0 = unreachable
  final String message;
  const SignalHubException(this.statusCode, this.message);

  bool get unauthorized => statusCode == 401;
  bool get forbidden => statusCode == 403;

  @override
  String toString() => statusCode == 0 ? 'hub unreachable: $message' : 'HTTP $statusCode: $message';
}

class _Resp {
  final int code;
  final Map<String, dynamic>? json;
  final String text;
  final DateTime? date;
  final bool bearerChallenge;
  const _Resp(this.code, this.json, this.text, this.date, this.bearerChallenge);

  String get message {
    final m = json?['message'];
    return m is String ? m : (text.length > 200 ? text.substring(0, 200) : text);
  }

  /// 401 because our ts is outside the hub's +/-120 s window.
  bool get staleTs => code == 401 && !bearerChallenge && message.contains("'ts'");
}

/// Client for the OmniCast signaling mailbox on an Omni-Hub.
class OmniSignalClient {
  final SignalHub hub;
  final String pubkeyHex;
  final SignalSignFn _sign;
  final int Function() _nowMs;
  final Random _rnd;

  /// Long-poll seconds per request (0-25).
  final int longPollSeconds;

  /// hub clock - local clock, learned from the HTTP Date header when the hub
  /// rejects our ts as stale. Phones with a wrong clock still work.
  int clockOffsetMs = 0;
  int _lastTs = 0;

  StreamController<SignalMessage>? _controller;
  HttpClient? _pollHttp;
  bool _polling = false;
  Completer<void>? _sleep;
  final List<String> _recentSigs = <String>[];
  final Set<String> _recentSigSet = <String>{};

  OmniSignalClient({
    required this.hub,
    required this.pubkeyHex,
    required SignalSignFn sign,
    this.longPollSeconds = OmniCastTimeouts.maxLongPollSeconds,
    int Function()? nowMs,
    Random? random,
  })  : _sign = sign,
        _nowMs = nowMs ?? (() => DateTime.now().millisecondsSinceEpoch),
        _rnd = random ?? Random() {
    if (!_pubkeyRe.hasMatch(pubkeyHex)) {
      throw ArgumentError('pubkeyHex must be 64 lowercase hex chars');
    }
    if (longPollSeconds < 0 || longPollSeconds > OmniCastTimeouts.maxLongPollSeconds) {
      throw ArgumentError('longPollSeconds must be 0-25');
    }
  }

  /// A fresh, strictly increasing millisecond ts on the hub's clock. Ed25519
  /// signatures are deterministic, so a reused ts would be a 409 replay.
  int freshTs() {
    final t = max(_nowMs() + clockOffsetMs, _lastTs + 1);
    _lastTs = t;
    return t;
  }

  // ---------------------------------------------------------------- send

  /// Drops a signed [kind] message for [to]. [payload]: SDP for offer/answer,
  /// candidate JSON for ice (see [sendIce]), may be "" for ring/hangup.
  /// Throws ArgumentError for input the hub would refuse (bad key, call id,
  /// oversized payload); every network/hub outcome comes back as a result.
  Future<SignalSendResult> send(String to, String callId, SignalKind kind, String payload) async {
    if (!_pubkeyRe.hasMatch(to)) throw ArgumentError('to must be a 64-hex pubkey');
    if (!_callIdRe.hasMatch(callId)) throw ArgumentError('callId must be 1-64 of A-Z a-z 0-9 _ . : -');
    if (payload.runes.length > OmniCastTimeouts.maxPayloadChars) {
      throw ArgumentError('payload over ${OmniCastTimeouts.maxPayloadChars} characters');
    }
    if (hasLoneSurrogate(payload)) throw ArgumentError('payload has an unpaired UTF-16 surrogate');

    for (var attempt = 0; attempt < 2; attempt++) {
      final ts = freshTs();
      final sig = await _sign(signalSendBytes(
          to: to, from: pubkeyHex, callId: callId, kind: kind.name, payload: payload, ts: ts));
      final body = utf8.encode(jsonEncode({
        'to': to,
        'from': pubkeyHex,
        'call_id': callId,
        'kind': kind.name,
        'payload': payload,
        'ts': ts,
        'sig': sig,
      }));
      if (body.length > OmniCastTimeouts.maxBodyBytes) {
        throw ArgumentError('request body over ${OmniCastTimeouts.maxBodyBytes} bytes');
      }
      final r = await _request('POST', hub.uri('/api/signal/send'), body: body);
      if (r == null) return const SignalSendResult(ok: false, statusCode: 0, error: 'hub unreachable');
      if (r.code == 200 && r.json?['status'] == 'QUEUED') {
        final seq = r.json?['seq'];
        return SignalSendResult(ok: true, statusCode: 200, seq: seq is int ? seq : null);
      }
      if (attempt == 0 && r.staleTs && _syncClock(r)) continue; // retry once on the hub's clock
      return SignalSendResult(ok: false, statusCode: r.code, error: r.message);
    }
    return const SignalSendResult(ok: false, statusCode: 401, error: 'clock out of sync with hub');
  }

  /// Sends one trickled ICE candidate (payload = candidate JSON).
  Future<SignalSendResult> sendIce(String to, String callId,
          {required String candidate, String? sdpMid, int? sdpMLineIndex}) =>
      send(to, callId, SignalKind.ice,
          jsonEncode({'candidate': candidate, 'sdpMid': sdpMid, 'sdpMLineIndex': sdpMLineIndex}));

  Future<SignalSendResult> ring(String to, String callId, [String payload = '']) =>
      send(to, callId, SignalKind.ring, payload);

  Future<SignalSendResult> hangup(String to, String callId) => send(to, callId, SignalKind.hangup, '');

  // ---------------------------------------------------------------- receive

  /// Every verified message for this key, from a long-poll loop that starts
  /// when you listen and stops when you cancel. Bad signatures, messages for
  /// another key, stale ts and duplicates are dropped silently. Hub auth
  /// problems are added as [SignalHubException] error events (use
  /// `cancelOnError: false`); the loop keeps retrying with backoff.
  /// Single-subscription; call [close] (or cancel) to stop.
  Stream<SignalMessage> messages() {
    if (_controller != null && !_controller!.isClosed) {
      throw StateError('messages() already has a listener; cancel it first');
    }
    final c = StreamController<SignalMessage>();
    _controller = c;
    c.onListen = () {
      _polling = true;
      unawaited(_pollLoop(c));
    };
    c.onCancel = () => _stopPolling();
    return c.stream;
  }

  /// Stops the poll loop and aborts an in-flight long-poll.
  Future<void> close() async {
    _stopPolling();
    final c = _controller;
    if (c != null && !c.isClosed) await c.close();
  }

  void _stopPolling() {
    _polling = false;
    _pollHttp?.close(force: true);
    _pollHttp = null;
    final s = _sleep;
    if (s != null && !s.isCompleted) s.complete();
  }

  /// One signed poll. Returns verified messages (oldest first). [wait] seconds
  /// of long-poll (0 = return at once). Throws [SignalHubException].
  Future<List<SignalMessage>> pollOnce({int wait = 0}) async {
    if (wait < 0 || wait > OmniCastTimeouts.maxLongPollSeconds) throw ArgumentError('wait must be 0-25');
    for (var attempt = 0; attempt < 2; attempt++) {
      final ts = freshTs();
      final sig = await _sign(signalAuthBytes(kSignalPollType, pubkeyHex, ts));
      // No `since`: the hub deletes on delivery, so a cursor adds nothing here,
      // and a daemon restart resets its seq counter (an old cursor would then
      // silently drop every new message). Duplicates are filtered by signature.
      final q = {'to': pubkeyHex, 'ts': '$ts', 'sig': sig, if (wait > 0) 'wait': '$wait'};
      final timeout = Duration(seconds: wait) + OmniCastTimeouts.longPollSlack;
      final r = await _request('GET', hub.uri('/api/signal/poll', q), timeout: timeout, forPoll: true);
      if (r == null) throw const SignalHubException(0, 'no response');
      if (r.code == 200 && r.json?['status'] == 'OK') {
        final raw = r.json?['messages'];
        final out = <SignalMessage>[];
        if (raw is List) {
          for (final j in raw) {
            final m = SignalMessage.tryParse(j);
            if (m != null && await _accept(m)) out.add(m);
          }
        }
        return out;
      }
      if (attempt == 0 && r.staleTs && _syncClock(r)) continue;
      throw SignalHubException(r.code, r.message);
    }
    throw const SignalHubException(401, 'clock out of sync with hub');
  }

  Future<bool> _accept(SignalMessage m) async {
    if (m.to != pubkeyHex) return false;
    if (_recentSigSet.contains(m.sig)) return false;
    final age = (_nowMs() + clockOffsetMs - m.ts).abs();
    if (age > OmniCastTimeouts.receiveMaxAge.inMilliseconds) return false;
    if (!await m.verify()) return false;
    _recentSigs.add(m.sig);
    _recentSigSet.add(m.sig);
    if (_recentSigs.length > 1024) _recentSigSet.remove(_recentSigs.removeAt(0));
    return true;
  }

  Future<void> _pollLoop(StreamController<SignalMessage> c) async {
    var backoff = OmniCastTimeouts.pollBackoffMin;
    while (_polling && !c.isClosed) {
      final started = DateTime.now();
      try {
        final msgs = await pollOnce(wait: longPollSeconds);
        backoff = OmniCastTimeouts.pollBackoffMin;
        if (!_polling || c.isClosed) break;
        for (final m in msgs) {
          c.add(m);
        }
        final took = DateTime.now().difference(started);
        if (msgs.isEmpty && took < OmniCastTimeouts.pollMinGap) {
          await _pause(OmniCastTimeouts.pollMinGap - took);
        }
      } catch (e) {
        if (!_polling || c.isClosed) break;
        final ex = e is SignalHubException ? e : SignalHubException(0, '$e');
        // Only surface what the user can fix (token, hub mode, clock); a hub
        // that is merely down or busy just backs off quietly.
        if (ex.statusCode == 401 || ex.statusCode == 403) c.addError(ex);
        await _pause(_jitter(backoff));
        final next = backoff * 2;
        backoff = next > OmniCastTimeouts.pollBackoffMax ? OmniCastTimeouts.pollBackoffMax : next;
      }
    }
  }

  Duration _jitter(Duration d) => d * (0.8 + 0.4 * _rnd.nextDouble());

  Future<void> _pause(Duration d) async {
    final s = Completer<void>();
    _sleep = s;
    final t = Timer(d, () {
      if (!s.isCompleted) s.complete();
    });
    await s.future;
    t.cancel();
  }

  // ---------------------------------------------------------------- ICE

  /// The iceServers list for flutter_webrtc's RTCPeerConnection config.
  /// Fetch a fresh one before each call (the TURN credential lasts ~1 h).
  /// Use [fetchIceConfiguration] to also get the hub's relay-policy hint.
  Future<List<Map<String, dynamic>>> fetchIceConfig() async => (await fetchIceConfiguration()).iceServers;

  /// Full ice-config: servers, transport policy ("relay" with TURN) and a
  /// ready-made [SignalIceConfig.rtcConfiguration]. Throws [SignalHubException].
  Future<SignalIceConfig> fetchIceConfiguration() async {
    for (var attempt = 0; attempt < 2; attempt++) {
      final ts = freshTs();
      final sig = await _sign(signalAuthBytes(kSignalIceType, pubkeyHex, ts));
      final r = await _request(
          'GET', hub.uri('/api/signal/ice-config', {'pubkey': pubkeyHex, 'ts': '$ts', 'sig': sig}));
      if (r == null) throw const SignalHubException(0, 'no response');
      if (r.code == 200) {
        final cfg = SignalIceConfig.tryParse(r.json);
        if (cfg != null) return cfg;
        throw const SignalHubException(200, 'unexpected ice-config reply');
      }
      if (attempt == 0 && r.staleTs && _syncClock(r)) continue;
      throw SignalHubException(r.code, r.message);
    }
    throw const SignalHubException(401, 'clock out of sync with hub');
  }

  // ---------------------------------------------------------------- HTTP

  bool _syncClock(_Resp r) {
    final d = r.date;
    if (d == null) return false;
    // Date has 1 s resolution: aim for its middle.
    final newOffset = d.millisecondsSinceEpoch + 500 - _nowMs();
    if ((newOffset - clockOffsetMs).abs() < 1000) return false; // not a clock problem
    clockOffsetMs = newOffset;
    // Let freshTs step back onto the hub's clock. Every ts already used was on
    // the wrong clock, so the hub refused it (or it has left the window).
    _lastTs = 0;
    return true;
  }

  Future<_Resp?> _request(String method, Uri uri,
      {List<int>? body, Duration timeout = OmniCastTimeouts.requestTimeout, bool forPoll = false}) async {
    final http = HttpClient()..connectionTimeout = OmniCastTimeouts.requestTimeout;
    if (forPoll) _pollHttp = http;
    try {
      final req = await http.openUrl(method, uri).timeout(timeout);
      final auth = hub.authorization;
      if (auth != null) req.headers.set(HttpHeaders.authorizationHeader, auth);
      if (body != null) {
        req.headers.contentType = ContentType.json;
        req.contentLength = body.length; // the hub answers 411 without it
        req.add(body);
      }
      final res = await req.close().timeout(timeout);
      final text = await res.transform(utf8.decoder).join().timeout(timeout);
      Map<String, dynamic>? json;
      try {
        final d = jsonDecode(text);
        if (d is Map<String, dynamic>) json = d;
      } catch (_) {}
      DateTime? date;
      try {
        date = res.headers.date;
      } catch (_) {}
      final challenge = res.headers.value(HttpHeaders.wwwAuthenticateHeader) != null;
      return _Resp(res.statusCode, json, text, date, challenge);
    } catch (_) {
      return null;
    } finally {
      if (forPoll && identical(_pollHttp, http)) _pollHttp = null;
      http.close(force: true);
    }
  }
}

// ------------------------------------------------------------------ calls

/// Caller side of at-most-once delivery: sends the offer, then re-sends a
/// fresh copy (new ts, new signature, same SDP and call id) every
/// [OmniCastTimeouts.offerResendInterval] until the callee's answer or hangup
/// for this call arrives, or [OmniCastTimeouts.ringTimeout] passes.
///
/// [incoming] is the app's one [OmniSignalClient.messages] stream (make it a
/// broadcast stream if other code also listens). Returns the answer, or null
/// on hangup/timeout/cancel. ICE messages that arrive meanwhile are not
/// consumed; the app's own listener sees them too.
class OfferResender {
  final OmniSignalClient client;
  final Duration interval;
  final Duration timeout;
  final int maxSends;
  bool _cancelled = false;
  Completer<SignalMessage?>? _done;

  OfferResender(
    this.client, {
    this.interval = OmniCastTimeouts.offerResendInterval,
    this.timeout = OmniCastTimeouts.ringTimeout,
    this.maxSends = OmniCastTimeouts.offerMaxSends,
  });

  /// How many offer copies the hub accepted (for logs/tests).
  int sends = 0;

  void cancel() {
    _cancelled = true;
    final d = _done;
    if (d != null && !d.isCompleted) d.complete(null);
  }

  Future<SignalMessage?> sendUntilAnswered({
    required String to,
    required String callId,
    required String sdp,
    required Stream<SignalMessage> incoming,
  }) async {
    final done = Completer<SignalMessage?>();
    _done = done;
    late final StreamSubscription<SignalMessage> sub;
    sub = incoming.listen((m) {
      if (m.from != to || m.callId != callId || done.isCompleted) return;
      if (m.kind == SignalKind.answer) done.complete(m);
      if (m.kind == SignalKind.hangup) done.complete(null);
    }, onError: (_) {}, cancelOnError: false);
    final deadline = Timer(timeout, () {
      if (!done.isCompleted) done.complete(null);
    });
    Timer? resend;
    Future<void> once() async {
      if (done.isCompleted || _cancelled || sends >= maxSends) return;
      final r = await client.send(to, callId, SignalKind.offer, sdp);
      if (r.ok) sends++;
      if (!r.ok && !r.retryable && !done.isCompleted) done.complete(null); // refused for good
    }

    try {
      await once();
      resend = Timer.periodic(interval, (_) => once());
      return await done.future;
    } finally {
      resend?.cancel();
      deadline.cancel();
      await sub.cancel();
    }
  }
}

/// What to do with an incoming offer (see [CalleeOfferTracker]).
enum OfferDisposition {
  /// First copy of this call's offer: show the incoming call.
  fresh,

  /// A re-sent copy while we haven't answered yet: ignore it.
  duplicatePending,

  /// A re-sent copy after we answered: our answer was probably lost, so
  /// re-send it with [CalleeOfferTracker.resendAnswer].
  duplicateAnswered,
}

/// Callee side of offer re-sends: dedupes offer copies by (caller, call id)
/// and remembers the answer so it can be re-sent when the caller's copy shows
/// it never arrived.
class CalleeOfferTracker {
  final int Function() _nowMs;
  final Map<String, ({int at, String? answerSdp})> _calls = {};

  CalleeOfferTracker({int Function()? nowMs})
      : _nowMs = nowMs ?? (() => DateTime.now().millisecondsSinceEpoch);

  String _k(String from, String callId) => '$from/$callId';

  void _purge() {
    final cut = _nowMs() - OmniCastTimeouts.answerCacheTtl.inMilliseconds;
    _calls.removeWhere((_, v) => v.at < cut);
  }

  OfferDisposition onOffer(SignalMessage offer) {
    _purge();
    final k = _k(offer.from, offer.callId);
    final prev = _calls[k];
    if (prev == null) {
      _calls[k] = (at: _nowMs(), answerSdp: null);
      return OfferDisposition.fresh;
    }
    return prev.answerSdp == null ? OfferDisposition.duplicatePending : OfferDisposition.duplicateAnswered;
  }

  /// Sends our answer and remembers it for duplicate offers.
  Future<SignalSendResult> answer(OmniSignalClient client, SignalMessage offer, String answerSdp) {
    _calls[_k(offer.from, offer.callId)] = (at: _nowMs(), answerSdp: answerSdp);
    return client.send(offer.from, offer.callId, SignalKind.answer, answerSdp);
  }

  /// Re-sends the remembered answer for this offer's call (no-op if none).
  Future<SignalSendResult?> resendAnswer(OmniSignalClient client, SignalMessage offer) async {
    final a = _calls[_k(offer.from, offer.callId)]?.answerSdp;
    if (a == null) return null;
    return client.send(offer.from, offer.callId, SignalKind.answer, a);
  }

  /// Forget a call (after hangup).
  void end(String from, String callId) => _calls.remove(_k(from, callId));
}

// ------------------------------------------------------------------ helpers

String _hex(List<int> b) => b.map((x) => x.toRadixString(16).padLeft(2, '0')).join();

List<int> _unhex(String h) {
  if (h.length.isOdd) throw const FormatException('odd hex');
  return [for (var i = 0; i < h.length; i += 2) int.parse(h.substring(i, i + 2), radix: 16)];
}
