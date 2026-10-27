import 'dart:convert';

import 'package:crypto/crypto.dart';

/// Canonical JSON that matches the daemon byte for byte:
/// Python `json.dumps(obj, sort_keys=True, separators=(',', ':'))`
/// (ensure_ascii on, so non-ASCII becomes \uXXXX).
///
/// Event hashes and signatures are computed over these bytes on both sides,
/// so a Dart-built event and a Python-built event get the same id.
String canonicalJson(Object? value) {
  final out = StringBuffer();
  _write(value, out);
  return out.toString();
}

/// "0x" + sha256 of the canonical event struct, exactly like the daemon's
/// compute_canonical_event_id().
String canonicalEventId({
  required String action,
  required String authorPubkey,
  required Map<String, dynamic> payload,
  required String previousHash,
  required double timestamp,
}) {
  final bytes = utf8.encode(canonicalJson(eventStruct(
    action: action,
    authorPubkey: authorPubkey,
    payload: payload,
    previousHash: previousHash,
    timestamp: timestamp,
  )));
  return '0x${sha256.convert(bytes)}';
}

Map<String, dynamic> eventStruct({
  required String action,
  required String authorPubkey,
  required Map<String, dynamic> payload,
  required String previousHash,
  required double timestamp,
}) =>
    {
      'action': action,
      'author_pubkey': authorPubkey,
      'payload': payload,
      'previous_hash': previousHash,
      'timestamp': timestamp,
    };

void _write(Object? v, StringBuffer out) {
  if (v == null) {
    out.write('null');
  } else if (v is bool) {
    out.write(v ? 'true' : 'false');
  } else if (v is int) {
    out.write(v.toString());
  } else if (v is double) {
    out.write(_pyFloat(v));
  } else if (v is String) {
    _writeString(v, out);
  } else if (v is Map) {
    final keys = v.keys.map((k) => k.toString()).toList()..sort();
    out.write('{');
    for (var i = 0; i < keys.length; i++) {
      if (i > 0) out.write(',');
      _writeString(keys[i], out);
      out.write(':');
      _write(v[keys[i]], out);
    }
    out.write('}');
  } else if (v is Iterable) {
    out.write('[');
    var first = true;
    for (final e in v) {
      if (!first) out.write(',');
      first = false;
      _write(e, out);
    }
    out.write(']');
  } else {
    throw ArgumentError('Not JSON-encodable: ${v.runtimeType}');
  }
}

/// Python float repr for the values events actually carry (timestamps etc).
String _pyFloat(double d) {
  if (d.isNaN) return 'NaN';
  if (d.isInfinite) return d > 0 ? 'Infinity' : '-Infinity';
  final s = d.toString(); // shortest round-trip digits, like Python repr
  if (s.contains('e')) return _pyExp(s);
  // Python switches to exponent form at >= 1e16; Dart waits until 1e21.
  if (d.abs() >= 1e16) return _pyExp(d.toStringAsExponential());
  return s;
}

/// Dart "1e+21" / "1.5e-7" -> Python "1e+21" / "1.5e-07".
String _pyExp(String e) {
  final parts = e.split('e');
  var mant = parts[0];
  if (mant.endsWith('.0')) mant = mant.substring(0, mant.length - 2);
  var exp = parts[1];
  final sign = exp.startsWith('-') ? '-' : '+';
  exp = exp.replaceAll(RegExp(r'^[+-]'), '');
  if (exp.length < 2) exp = '0$exp';
  return '${mant}e$sign$exp';
}

void _writeString(String s, StringBuffer out) {
  out.write('"');
  for (final rune in s.runes) {
    if (rune == 0x22) {
      out.write(r'\"');
    } else if (rune == 0x5C) {
      out.write(r'\\');
    } else if (rune == 0x0A) {
      out.write(r'\n');
    } else if (rune == 0x0D) {
      out.write(r'\r');
    } else if (rune == 0x09) {
      out.write(r'\t');
    } else if (rune == 0x08) {
      out.write(r'\b');
    } else if (rune == 0x0C) {
      out.write(r'\f');
    } else if (rune < 0x20 || (rune >= 0x7F && rune <= 0xFFFF)) {
      out.write('\\u${rune.toRadixString(16).padLeft(4, '0')}');
    } else if (rune > 0xFFFF) {
      final v = rune - 0x10000;
      final hi = 0xD800 + (v >> 10);
      final lo = 0xDC00 + (v & 0x3FF);
      out.write('\\u${hi.toRadixString(16)}\\u${lo.toRadixString(16)}');
    } else {
      out.writeCharCode(rune);
    }
  }
  out.write('"');
}
