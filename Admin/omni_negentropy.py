"""omni_negentropy.py - range-based set reconciliation (negentropy protocol v1) in pure Python.

Used by the daemon's catch-up sync (Admin/docs/CATCHUP_SYNC.md): two nodes find out which events
each one lacks by exchanging fingerprints over ranges of their (timestamp, event_id) sets and
splitting only the ranges that differ, then fetch just the missing events.

Credit: the protocol is Doug Hoyte's negentropy (https://github.com/hoytech/negentropy, MIT
licence, (C) 2023-2024 Doug Hoyte and contributors). This file is an independent implementation
written from the published v1 spec (docs/negentropy-protocol-v1.md in that repo); no code was
copied from the reference implementations. It follows the v1 wire format (version byte 0x61,
MSB-first varints, delta-encoded bounds, Skip/Fingerprint/IdList modes, sum-mod-2^256 + count
SHA-256 fingerprints, 16 buckets, IdList below 32 items). Checked in the sandbox against the JS
reference implementation (hoytech/negentropy js/Negentropy.js) in both directions, with
byte-identical messages; tests/test_negentropy.py pins vectors taken from that run.
Not implemented: frame size limits (messages are unbounded; the daemon caps request bodies at 5 MB).

Items are (timestamp: int, id: 32 bytes). The daemon uses timestamp = signed event time in whole
SECONDS (the JS reference mishandles timestamps above 2^32, so ms would break interop) and
id = the 32-byte content hash behind "0x<64 hex>" event ids.

No dependencies beyond the standard library.
"""
import bisect
import hashlib

PROTOCOL_VERSION = 0x61          # v1
ID_SIZE = 32
FINGERPRINT_SIZE = 16
MAX_TIMESTAMP = 2 ** 64 - 1      # reserved "infinity"
MODE_SKIP, MODE_FINGERPRINT, MODE_IDLIST = 0, 1, 2
BUCKETS = 16                     # split a mismatched range into this many sub-ranges
_MOD = 2 ** 256
_ZERO_ID = bytes(ID_SIZE)


# --- varints (base 128, most significant digit first, high bit set on all but the last byte) ---

def encode_varint(n: int) -> bytes:
    if n < 0:
        raise ValueError("varint must be non-negative")
    digits = [n & 0x7F]
    n >>= 7
    while n:
        digits.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(digits))


class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def at_end(self) -> bool:
        return self.pos >= len(self.data)

    def take(self, n: int) -> bytes:
        if n < 0 or self.pos + n > len(self.data):
            raise ValueError("negentropy message truncated")
        out = self.data[self.pos:self.pos + n]
        self.pos += n
        return out

    def varint(self) -> int:
        n = 0
        for _ in range(10):          # 10 * 7 bits covers u64; more is malformed
            b = self.take(1)[0]
            n = (n << 7) | (b & 0x7F)
            if not b & 0x80:
                return n
        raise ValueError("negentropy varint too long")


# --- items, bounds, fingerprints ---------------------------------------------------------------

def bound_key(ts: int, prefix: bytes) -> tuple:
    """A bound sorts like an item whose id is the prefix padded with zero bytes."""
    return (ts, prefix + bytes(ID_SIZE - len(prefix)))


def minimal_bound(prev: tuple, curr: tuple) -> tuple:
    """Shortest bound that separates item prev (just below) from item curr (at/above)."""
    if curr[0] != prev[0]:
        return (curr[0], b"")
    shared = 0
    while shared < ID_SIZE and prev[1][shared] == curr[1][shared]:
        shared += 1
    return (curr[0], curr[1][:shared + 1])


def fingerprint_of(ids_sum: int, count: int) -> bytes:
    return hashlib.sha256((ids_sum % _MOD).to_bytes(ID_SIZE, "little") + encode_varint(count)).digest()[:FINGERPRINT_SIZE]


class Storage:
    """Sorted, sealed vector of (timestamp, id) with prefix sums so any range's fingerprint is O(1)."""

    def __init__(self, items=()):
        seen = set()
        clean = []
        for ts, id_ in items:
            if isinstance(id_, str):
                id_ = bytes.fromhex(id_[2:] if id_.startswith("0x") else id_)
            if not isinstance(ts, int) or isinstance(ts, bool) or not 0 <= ts < MAX_TIMESTAMP:
                raise ValueError(f"bad timestamp {ts!r}")
            if len(id_) != ID_SIZE:
                raise ValueError("ids must be 32 bytes")
            if id_ in seen:
                continue
            seen.add(id_)
            clean.append((ts, bytes(id_)))
        clean.sort()
        self.items = clean
        self._sums = [0]
        acc = 0
        for _, id_ in clean:
            acc = (acc + int.from_bytes(id_, "little")) % _MOD
            self._sums.append(acc)

    def __len__(self):
        return len(self.items)

    def find_lower_bound(self, bound: tuple, lo: int = 0) -> int:
        """Index of the first item >= bound, searching from lo."""
        return bisect.bisect_left(self.items, bound_key(*bound), lo)

    def fingerprint(self, begin: int, end: int) -> bytes:
        return fingerprint_of(self._sums[end] - self._sums[begin], end - begin)


# --- messages ----------------------------------------------------------------------------------

def _encode_message(ranges) -> bytes:
    """ranges: list of (bound, mode, payload). Timestamps are delta-encoded from the start of the message."""
    out = bytearray([PROTOCOL_VERSION])
    last_ts = 0
    for (ts, prefix), mode, payload in ranges:
        if ts == MAX_TIMESTAMP:
            out += encode_varint(0)
            last_ts = MAX_TIMESTAMP
        else:
            out += encode_varint(1 + ts - last_ts)
            last_ts = ts
        out += encode_varint(len(prefix)) + prefix
        out += encode_varint(mode)
        if mode == MODE_FINGERPRINT:
            out += payload
        elif mode == MODE_IDLIST:
            out += encode_varint(len(payload)) + b"".join(payload)
    return bytes(out)


class Negentropy:
    """One side of a reconciliation. The client calls initiate() then feeds each server reply to
    reconcile() until it returns None as the next message. The server just answers each message
    with reconcile() (it keeps no state between messages)."""

    def __init__(self, storage: Storage):
        self.storage = storage
        self.is_initiator = False

    def initiate(self) -> bytes:
        if self.is_initiator:
            raise RuntimeError("already initiated")
        self.is_initiator = True
        ranges = []
        self._split_range(0, len(self.storage), (MAX_TIMESTAMP, b""), ranges)
        return _encode_message(ranges)

    def reconcile(self, msg: bytes):
        """Returns (next_message_or_None, have_ids, need_ids). have/need are only filled on the client:
        have = ids this side has and the server lacks; need = ids the server has and this side lacks."""
        r = _Reader(bytes(msg))
        version = r.take(1)[0]
        if version != PROTOCOL_VERSION:
            if self.is_initiator:
                raise ValueError(f"server wants unsupported negentropy version 0x{version:02x}")
            return bytes([PROTOCOL_VERSION]), [], []   # tell the client which version we speak

        st = self.storage
        have, need, ranges = [], [], []
        prev_bound = (0, b"")
        prev_index = 0
        last_ts_in = 0
        pending_skip = False

        def flush_skip():
            nonlocal pending_skip
            if pending_skip:
                pending_skip = False
                ranges.append((prev_bound, MODE_SKIP, None))

        while not r.at_end():
            enc_ts = r.varint()
            if enc_ts == 0:
                ts = MAX_TIMESTAMP
            else:
                ts = MAX_TIMESTAMP if last_ts_in == MAX_TIMESTAMP else last_ts_in + enc_ts - 1
                if ts >= MAX_TIMESTAMP:
                    raise ValueError("negentropy bound timestamp overflow")
            last_ts_in = ts
            plen = r.varint()
            if plen > ID_SIZE:
                raise ValueError("negentropy bound prefix longer than 32 bytes")
            curr_bound = (ts, r.take(plen))
            if bound_key(*curr_bound) < bound_key(*prev_bound):
                raise ValueError("negentropy ranges out of order")
            mode = r.varint()

            lower = prev_index
            upper = st.find_lower_bound(curr_bound, lower)

            if mode == MODE_SKIP:
                pending_skip = True
            elif mode == MODE_FINGERPRINT:
                theirs = r.take(FINGERPRINT_SIZE)
                if theirs != st.fingerprint(lower, upper):
                    flush_skip()
                    self._split_range(lower, upper, curr_bound, ranges)
                else:
                    pending_skip = True
            elif mode == MODE_IDLIST:
                n = r.varint()
                if n > (len(r.data) - r.pos) // ID_SIZE:
                    raise ValueError("negentropy IdList longer than the message")
                their_ids = {r.take(ID_SIZE) for _ in range(n)}
                if self.is_initiator:
                    for _, id_ in st.items[lower:upper]:
                        if id_ in their_ids:
                            their_ids.discard(id_)
                        else:
                            have.append(id_)
                    need.extend(sorted(their_ids))
                    pending_skip = True
                else:
                    flush_skip()
                    ranges.append((curr_bound, MODE_IDLIST, [id_ for _, id_ in st.items[lower:upper]]))
            else:
                raise ValueError(f"unknown negentropy mode {mode}")

            prev_index = upper
            prev_bound = curr_bound

        out = _encode_message(ranges)   # a trailing skip is implicit, never sent
        if self.is_initiator and len(out) == 1:
            return None, have, need
        return out, have, need

    def _split_range(self, lower: int, upper: int, upper_bound: tuple, ranges: list):
        items = self.storage.items
        n = upper - lower
        if n < BUCKETS * 2:
            ranges.append((upper_bound, MODE_IDLIST, [id_ for _, id_ in items[lower:upper]]))
            return
        per, extra = divmod(n, BUCKETS)
        curr = lower
        for i in range(BUCKETS):
            size = per + (1 if i < extra else 0)
            fp = self.storage.fingerprint(curr, curr + size)
            curr += size
            bound = upper_bound if curr == upper else minimal_bound(items[curr - 1], items[curr])
            ranges.append((bound, MODE_FINGERPRINT, fp))


def reconcile_local(client: Storage, server: Storage, max_rounds: int = 64):
    """Runs a full exchange in memory (for tests and tooling). Returns (have, need, rounds, bytes_sent)."""
    c, s = Negentropy(client), Negentropy(server)
    msg = c.initiate()
    have, need, rounds, sent = [], [], 0, len(msg)
    while True:
        rounds += 1
        if rounds > max_rounds:
            raise RuntimeError("negentropy did not converge")
        reply, _, _ = s.reconcile(msg)
        sent += len(reply)
        msg, h, nd = c.reconcile(reply)
        have += h
        need += nd
        if msg is None:
            return have, need, rounds, sent
        sent += len(msg)
