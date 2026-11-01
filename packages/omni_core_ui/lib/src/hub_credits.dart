import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'omni_hub_client.dart';

/// Client for the hub daemon's TEST credits ledger (daemon v8.10.0+, signed
/// sends v8.15.0+). Test credits only: no cash value, not redeemable.
///
/// The ledger lives on the hub (Admin/docs/CREDITS_LEDGER.md in
/// kiroba/Omni-Daemon). Apps never keep their own balance: they read it with
/// [balance] / [history] and move credits with [send], a transfer signed by the
/// sender's own key (StargateIdentity.signBytes).
///
///   GET  :5000/api/credits/balance?pubkey=<64 hex>
///   GET  :5000/api/credits/history?pubkey=<64 hex>&limit=1..200
///   POST :5000/api/credits/send   {type, from, to, amount, kind, memo, [ref], nonce, ts, sig}
///
/// Which hub and which token come from the [OmniHubClient] the app already
/// builds from its Hub setting: on loopback the token is Omni Node's local
/// token (Omni Node > Connect apps), sent as "Authorization: Bearer <token>"
/// (daemon v8.20.0+); for a remote hub it is that hub's bearer token.
///
/// Nothing here ever falls back to a local number: when the hub can't be
/// reached the result says so ([CreditsState.unreachable]).
class HubCreditsClient {
  final OmniHubClient hub;

  const HubCreditsClient(this.hub);

  /// Balance for [pubkey]. On loopback the hub issues the one-time 1,000
  /// welcome grant on first lookup; over a remote hub it reports it as
  /// [CreditBalance.welcomePending] and counts it in [CreditBalance.available].
  Future<CreditsResult<CreditBalance>> balance(String pubkey) async {
    final r = await _request('GET', '/api/credits/balance', query: {'pubkey': pubkey});
    return r.map(CreditBalance.fromJson);
  }

  /// Ledger entries touching [pubkey], newest first.
  Future<CreditsResult<CreditHistory>> history(String pubkey, {int limit = 50}) async {
    final r = await _request('GET', '/api/credits/history',
        query: {'pubkey': pubkey, 'limit': '${limit.clamp(1, 200)}'});
    return r.map(CreditHistory.fromJson);
  }

  /// Sends a transfer built by [buildSignedCreditTransfer]. An unreachable hub
  /// is retried once with the identical body: the hub applies a (from, nonce)
  /// pair at most once and answers ALREADY_APPLIED to an identical retry, so
  /// re-sending never spends twice.
  Future<CreditsResult<CreditSendReceipt>> send(Map<String, dynamic> signedTransfer) async {
    var r = await _request('POST', '/api/credits/send', body: signedTransfer);
    if (r.state == CreditsState.unreachable) {
      r = await _request('POST', '/api/credits/send', body: signedTransfer);
    }
    return r.map(CreditSendReceipt.fromJson);
  }

  Future<CreditsResult<Map<String, dynamic>>> _request(String method, String path,
      {Map<String, String>? query, Map<String, dynamic>? body}) async {
    final uri = Uri(scheme: 'http', host: hub.host, port: hub.ipcPort, path: path, queryParameters: query);
    final client = HttpClient()..connectionTimeout = hub.timeout;
    int? code;
    try {
      final req = await (method == 'POST' ? client.postUrl(uri) : client.getUrl(uri)).timeout(hub.timeout);
      final t = hub.token;
      if (t != null && t.isNotEmpty) {
        req.headers.set(HttpHeaders.authorizationHeader, 'Bearer $t');
      }
      if (body != null) {
        req.headers.contentType = ContentType.json;
        // Content-Length, never chunked (see OmniHubClient._post).
        final bytes = utf8.encode(jsonEncode(body));
        req.contentLength = bytes.length;
        req.add(bytes);
      }
      final res = await req.close().timeout(hub.timeout);
      code = res.statusCode;
      final text = await res.transform(utf8.decoder).join().timeout(hub.timeout);
      Map<String, dynamic>? json;
      try {
        final d = jsonDecode(text);
        if (d is Map<String, dynamic>) json = d;
      } catch (_) {}
      return CreditsResult.fromHttp(code, json);
    } catch (e) {
      if (code != null) {
        return CreditsResult(CreditsState.error, statusCode: code, message: 'HTTP $code: $e');
      }
      return CreditsResult(CreditsState.unreachable, message: '$e');
    } finally {
      client.close(force: true);
    }
  }
}

/// How a credits call went.
enum CreditsState {
  /// The hub answered 200.
  ok,

  /// Nothing answered (Omni Node off, Tailscale off, wrong address).
  unreachable,

  /// The hub refused the token (401 "local token" / "bearer token").
  unauthorized,

  /// The hub refused the call (403: remote mode off, or a loopback-only path).
  forbidden,

  /// The hub's ledger failed its integrity check (409 with integrity FAILED).
  integrity,

  /// The hub refused this request: bad input (400), bad signature or stale ts
  /// (401 without a token problem), overdraft or nonce reuse (409).
  rejected,

  /// The hub is too old to have the credits ledger (404).
  unsupported,

  /// Anything else.
  error,
}

class CreditsResult<T> {
  final CreditsState state;
  final T? value;
  final int? statusCode;
  final String? message;
  final Map<String, dynamic>? raw;

  const CreditsResult(this.state, {this.value, this.statusCode, this.message, this.raw});

  bool get ok => state == CreditsState.ok && value != null;

  /// The hub could not be used at all (as opposed to refusing one request).
  bool get hubProblem =>
      state == CreditsState.unreachable ||
      state == CreditsState.unauthorized ||
      state == CreditsState.forbidden ||
      state == CreditsState.unsupported ||
      state == CreditsState.integrity;

  factory CreditsResult.fromHttp(int code, Map<String, dynamic>? json) {
    final msg = json?['message']?.toString();
    switch (code) {
      case 200:
        if (json == null) {
          return CreditsResult(CreditsState.error, statusCode: code, message: 'unexpected reply');
        }
        return CreditsResult(CreditsState.ok, value: json as T?, statusCode: code, raw: json);
      case 401:
        // remote_gate: "missing or invalid local token" / "missing or invalid bearer token".
        // credits_send: "bad signature ..." / "stale or future 'ts' ...".
        final tokenProblem = (msg ?? '').contains('token');
        return CreditsResult(tokenProblem ? CreditsState.unauthorized : CreditsState.rejected,
            statusCode: code, message: msg ?? 'HTTP 401', raw: json);
      case 403:
        return CreditsResult(CreditsState.forbidden, statusCode: code, message: msg ?? 'HTTP 403', raw: json);
      case 404:
        return CreditsResult(CreditsState.unsupported,
            statusCode: code, message: 'this hub has no credits ledger (daemon older than v8.10.0)', raw: json);
      case 409:
        final integrity = json?['integrity'] == 'FAILED';
        return CreditsResult(integrity ? CreditsState.integrity : CreditsState.rejected,
            statusCode: code, message: msg ?? 'HTTP 409', raw: json);
      case 400:
        return CreditsResult(CreditsState.rejected, statusCode: code, message: msg ?? 'HTTP 400', raw: json);
      default:
        return CreditsResult(CreditsState.error, statusCode: code, message: msg ?? 'HTTP $code', raw: json);
    }
  }

  CreditsResult<R> map<R>(R Function(Map<String, dynamic>) f) {
    if (state != CreditsState.ok || raw == null) {
      return CreditsResult<R>(state, statusCode: statusCode, message: message, raw: raw);
    }
    try {
      return CreditsResult<R>(CreditsState.ok, value: f(raw!), statusCode: statusCode, raw: raw);
    } catch (e) {
      return CreditsResult<R>(CreditsState.error, statusCode: statusCode, message: 'unexpected reply: $e', raw: raw);
    }
  }
}

int _int(Object? v) => v is int ? v : (v is num ? v.toInt() : int.tryParse('$v') ?? 0);

/// GET /api/credits/balance.
class CreditBalance {
  final String pubkey;
  final int balance;

  /// What the key can spend: [balance] plus an unclaimed welcome grant
  /// (remote-hub lookups only). Show this one.
  final int available;
  final bool welcomePending;

  /// Treasury fee in basis points the hub takes from what a recipient gets.
  final int feeBps;
  final String? hubVersion;

  const CreditBalance({
    required this.pubkey,
    required this.balance,
    required this.available,
    this.welcomePending = false,
    this.feeBps = 0,
    this.hubVersion,
  });

  factory CreditBalance.fromJson(Map<String, dynamic> j) {
    if (j['balance'] == null) throw const FormatException('no balance');
    final bal = _int(j['balance']);
    return CreditBalance(
      pubkey: '${j['pubkey'] ?? ''}',
      balance: bal,
      available: j.containsKey('available') ? _int(j['available']) : bal,
      welcomePending: j['welcome_pending'] == true,
      feeBps: _int(j['fee_bps']),
      hubVersion: j['version']?.toString(),
    );
  }
}

/// One ledger entry as /api/credits/history returns it, from the caller's side.
class CreditEntry {
  final String eventId;
  final String kind; // grant | transfer | purchase | tip | reset
  final String from;
  final String to;
  final int amount;
  final int fee;
  final String memo;
  final String? ref;

  /// Change to the asked-about key's balance (negative = spent).
  final int delta;
  final int balanceAfter;
  final int tsMs;

  /// True when the entry carries the sender's own signature (signed send).
  final bool signedBySender;

  const CreditEntry({
    required this.eventId,
    required this.kind,
    required this.from,
    required this.to,
    required this.amount,
    required this.fee,
    required this.memo,
    this.ref,
    required this.delta,
    required this.balanceAfter,
    required this.tsMs,
    this.signedBySender = false,
  });

  DateTime get time => DateTime.fromMillisecondsSinceEpoch(tsMs);

  factory CreditEntry.fromJson(Map<String, dynamic> j) => CreditEntry(
        eventId: '${j['event_id'] ?? ''}',
        kind: '${j['kind'] ?? ''}',
        from: '${j['from'] ?? ''}',
        to: '${j['to'] ?? ''}',
        amount: _int(j['amount']),
        fee: _int(j['fee']),
        memo: '${j['memo'] ?? ''}',
        ref: j['ref']?.toString(),
        delta: _int(j['delta']),
        balanceAfter: _int(j['balance_after']),
        tsMs: _int(j['ts_ms']),
        signedBySender: j['auth'] is Map,
      );
}

/// GET /api/credits/history.
class CreditHistory {
  final int balance;
  final List<CreditEntry> entries;
  final bool hasMore;

  const CreditHistory({required this.balance, required this.entries, this.hasMore = false});

  factory CreditHistory.fromJson(Map<String, dynamic> j) {
    final list = j['entries'];
    if (list is! List) throw const FormatException('no entries');
    return CreditHistory(
      balance: _int(j['balance']),
      entries: [for (final e in list) if (e is Map<String, dynamic>) CreditEntry.fromJson(e)],
      hasMore: j['has_more'] == true,
    );
  }
}

/// POST /api/credits/send answer (200).
class CreditSendReceipt {
  final String eventId;

  /// The sender's balance after the send.
  final int? balance;

  /// Treasury fee the hub took from what the recipient got (not signed: the
  /// hub sets it from OMNI_TREASURY_FEE_BPS). Null on an ALREADY_APPLIED retry.
  final int? fee;
  final int? amount;

  /// The hub had already applied this exact signed transfer (a safe retry).
  final bool alreadyApplied;

  const CreditSendReceipt({required this.eventId, this.balance, this.fee, this.amount, this.alreadyApplied = false});

  factory CreditSendReceipt.fromJson(Map<String, dynamic> j) {
    final entry = j['entry'];
    return CreditSendReceipt(
      eventId: '${j['event_id'] ?? ''}',
      balance: j['balance'] == null ? null : _int(j['balance']),
      fee: entry is Map ? _int(entry['fee']) : null,
      amount: entry is Map ? _int(entry['amount']) : null,
      alreadyApplied: j['result'] == 'ALREADY_APPLIED',
    );
  }
}

/// The type string the hub expects on a signed send.
const String kCreditTransferType = 'omni.credits.transfer.v1';

/// Kinds a person may sign. A tip needs [ref] and a pubkey recipient.
const Set<String> kSignedCreditKinds = {'transfer', 'purchase', 'tip'};

/// What the hub calls its own account (fees, credits sent to the platform).
const String kCreditTreasury = 'treasury';

final RegExp _pubkeyRe = RegExp(r'^[0-9a-f]{64}$');
final RegExp _refRe = RegExp(r'^[A-Za-z0-9_.:\-]{1,80}$');
final RegExp _nonceRe = RegExp(r'^[0-9a-f]{16,64}$');

/// The exact bytes the sender signs: every field except "sig", keys sorted,
/// compact, raw UTF-8. Mirrors the daemon's credit_signing_bytes
/// (json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)).
/// Dart's jsonEncode writes the same bytes for these scalar fields once the
/// keys are inserted in sorted order (same rule as omni_signal_client.dart).
List<int> creditTransferSigningBytes(Map<String, dynamic> transfer) {
  final keys = transfer.keys.where((k) => k != 'sig').toList()..sort();
  final sorted = <String, dynamic>{for (final k in keys) k: transfer[k]};
  return utf8.encode(jsonEncode(sorted));
}

/// A random 32-hex nonce for one transfer.
String newCreditNonce([Random? rnd]) {
  final r = rnd ?? Random.secure();
  return List<int>.generate(16, (_) => r.nextInt(256)).map((b) => b.toRadixString(16).padLeft(2, '0')).join();
}

bool _hasLoneSurrogate(String s) {
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

/// Builds and signs a POST /api/credits/send body. [sign] is the sender's
/// StargateIdentity.signBytes. Throws [ArgumentError] for anything the hub
/// would refuse (so the user sees it before a round trip).
Future<Map<String, dynamic>> buildSignedCreditTransfer({
  required String from,
  required String to,
  required int amount,
  required String kind,
  required Future<String> Function(List<int> message) sign,
  String memo = '',
  String? ref,
  String? nonce,
  int? tsMs,
}) async {
  if (!_pubkeyRe.hasMatch(from)) throw ArgumentError('from must be a lowercase 64-hex pubkey');
  if (to != kCreditTreasury && !_pubkeyRe.hasMatch(to)) {
    throw ArgumentError('to must be a lowercase 64-hex pubkey or "treasury"');
  }
  if (from == to) throw ArgumentError('from and to are the same account');
  if (amount < 1 || amount > 1000000) throw ArgumentError('amount must be 1 to 1,000,000 credits');
  if (!kSignedCreditKinds.contains(kind)) throw ArgumentError('kind must be transfer, purchase or tip');
  final m = memo.split('').where((c) => c.codeUnitAt(0) >= 0x20).join().trim();
  if (m.length > 200) throw ArgumentError('memo is longer than 200 characters');
  if (_hasLoneSurrogate(m)) throw ArgumentError('memo has an unpaired surrogate');
  if (ref != null && !_refRe.hasMatch(ref)) throw ArgumentError("ref must be 1-80 chars of A-Z a-z 0-9 _ . : -");
  if (kind == 'tip' && (ref == null || to == kCreditTreasury)) {
    throw ArgumentError('a tip goes to a pubkey and names what it tips (ref)');
  }
  final n = nonce ?? newCreditNonce();
  if (!_nonceRe.hasMatch(n)) throw ArgumentError('nonce must be 16-64 lowercase hex chars');
  final body = <String, dynamic>{
    'type': kCreditTransferType,
    'from': from,
    'to': to,
    'amount': amount,
    'kind': kind,
    'memo': m,
    if (ref != null) 'ref': ref,
    'nonce': n,
    'ts': tsMs ?? DateTime.now().millisecondsSinceEpoch,
  };
  body['sig'] = await sign(creditTransferSigningBytes(body));
  return body;
}
