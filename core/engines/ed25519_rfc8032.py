# ============================================================================
# Ed25519 — pure-Python implementation of RFC 8032.
#
# Adapted from the reference implementation published in RFC 8032, section 6
# (the RFC's own sample code). It exists so the OmniMod compiler stays
# zero-dependency Python stdlib — a hard ecosystem rule — while producing
# REAL Ed25519 signatures. The signatures are standard Ed25519 and verify
# with any conforming implementation (proven against OpenSSL at introduction;
# the daemon-side engines independently use the `cryptography` package and
# interoperate, because the scheme is the scheme).
#
# Honest cost: this reference code favours auditability over speed. A sign
# or verify takes on the order of seconds in CPython. That is fine for a
# build-time compiler and a verify command; it would not be fine in a hot
# path, and nothing here is a hot path.
#
# API (bytes in, bytes out):
#   publickey(seed32)            -> 32-byte public key
#   signature(msg, seed32, pk32) -> 64-byte signature
#   checkvalid(sig64, msg, pk32) -> bool (raises on malformed input)
# ============================================================================

import hashlib

b = 256
q = 2 ** 255 - 19
l = 2 ** 252 + 27742317777372353535851937790883648493


def _H(m):
    return hashlib.sha512(m).digest()


def _expmod(b_, e, m):
    if e == 0:
        return 1
    t = _expmod(b_, e // 2, m) ** 2 % m
    if e & 1:
        t = (t * b_) % m
    return t


def _inv(x):
    return _expmod(x, q - 2, q)


d = -121665 * _inv(121666) % q
I = _expmod(2, (q - 1) // 4, q)


def _xrecover(y):
    xx = (y * y - 1) * _inv(d * y * y + 1)
    x = _expmod(xx, (q + 3) // 8, q)
    if (x * x - xx) % q != 0:
        x = (x * I) % q
    if x % 2 != 0:
        x = q - x
    return x


_By = 4 * _inv(5) % q
_Bx = _xrecover(_By)
B = [_Bx % q, _By % q]


def _edwards(P, Q):
    x1, y1 = P
    x2, y2 = Q
    x3 = (x1 * y2 + x2 * y1) * _inv(1 + d * x1 * x2 * y1 * y2)
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - d * x1 * x2 * y1 * y2)
    return [x3 % q, y3 % q]


def _scalarmult(P, e):
    if e == 0:
        return [0, 1]
    Q = _scalarmult(P, e // 2)
    Q = _edwards(Q, Q)
    if e & 1:
        Q = _edwards(Q, P)
    return Q


def _encodeint(y):
    bits = [(y >> i) & 1 for i in range(b)]
    return bytes(
        [sum([bits[i * 8 + j] << j for j in range(8)]) for i in range(b // 8)]
    )


def _encodepoint(P):
    x, y = P
    bits = [(y >> i) & 1 for i in range(b - 1)] + [x & 1]
    return bytes(
        [sum([bits[i * 8 + j] << j for j in range(8)]) for i in range(b // 8)]
    )


def _bit(h, i):
    return (h[i // 8] >> (i % 8)) & 1


def _secret_expand(seed32):
    h = _H(seed32)
    a = 2 ** (b - 2) + sum(2 ** i * _bit(h, i) for i in range(3, b - 2))
    return h, a


def publickey(seed32):
    """Derives the 32-byte public key for a 32-byte seed."""
    if len(seed32) != 32:
        raise ValueError("Ed25519 seed must be 32 bytes")
    _, a = _secret_expand(seed32)
    A = _scalarmult(B, a)
    return _encodepoint(A)


def signature(msg, seed32, pk32):
    """Produces the 64-byte Ed25519 signature of msg for the given keypair."""
    if len(seed32) != 32:
        raise ValueError("Ed25519 seed must be 32 bytes")
    if len(pk32) != 32:
        raise ValueError("Ed25519 public key must be 32 bytes")
    h, a = _secret_expand(seed32)
    r = _Hint(h[b // 8:b // 4] + msg)
    R = _scalarmult(B, r)
    S = (r + _Hint(_encodepoint(R) + pk32 + msg) * a) % l
    return _encodepoint(R) + _encodeint(S)


def _Hint(m):
    h = _H(m)
    return sum(2 ** i * _bit(h, i) for i in range(2 * b))


def _isoncurve(P):
    x, y = P
    return (-x * x + y * y - 1 - d * x * x * y * y) % q == 0


def _decodeint(s):
    return sum(2 ** i * _bit(s, i) for i in range(0, b))


def _decodepoint(s):
    y = sum(2 ** i * _bit(s, i) for i in range(0, b - 1))
    x = _xrecover(y)
    if x & 1 != _bit(s, b - 1):
        x = q - x
    P = [x, y]
    if not _isoncurve(P):
        raise Exception("decoding point that is not on curve")
    return P


def checkvalid(sig64, msg, pk32):
    """Returns True iff sig64 is a valid signature of msg under pk32.

    Raises on malformed lengths or points; callers that need a plain
    yes/no for untrusted input should catch and treat as invalid.
    """
    if len(sig64) != b // 4:
        raise Exception("signature length is wrong")
    if len(pk32) != b // 8:
        raise Exception("public-key length is wrong")
    R = _decodepoint(sig64[0:b // 8])
    A = _decodepoint(pk32)
    S = _decodeint(sig64[b // 8:b // 4])
    h = _Hint(sig64[0:b // 8] + pk32 + msg)
    return _scalarmult(B, S) == _edwards(R, _scalarmult(A, h))
