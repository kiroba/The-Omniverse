"""omni_signing.py - persistent Ed25519 identity + event signing for the Omniverse daemon.
pip install cryptography
"""
import json
import os
import time
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

KEY_FILE = Path.home() / ".omniverse" / "node_ed25519.key"


def load_or_create_key(path: Path = KEY_FILE) -> Ed25519PrivateKey:
    """Same key every restart. Created once, readable only by you."""
    if path.exists():
        return Ed25519PrivateKey.from_private_bytes(path.read_bytes())
    path.parent.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    raw = key.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    )
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
    return key


def pubkey_hex(key: Ed25519PrivateKey) -> str:
    raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return raw.hex()  # 64 hex chars. This IS the node id / author_pubkey now.


def canonical_bytes(action, author_pubkey, payload, previous_hash, timestamp) -> bytes:
    """Legacy (float-seconds) canonical bytes. Unchanged, so existing ids, signatures and the
    Dart interop vectors in packages/omni_core_ui keep matching byte for byte."""
    return json.dumps(
        {"action": action, "author_pubkey": author_pubkey, "payload": payload,
         "previous_hash": previous_hash, "timestamp": timestamp},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


# --- Timestamps -------------------------------------------------------------------------------
# Two canonical forms, told apart by which key the event carries (never both):
#   legacy:  "timestamp": <float seconds>   e.g. 1793042651.19   (pre-8.5.1 daemons, Dart today)
#   new:     "ts":        <int milliseconds> e.g. 1793042651190  (daemon-stamped events from 8.5.1)
# Integer ms serialises identically in every language, so it avoids float repr drift between
# Python and Dart. The legacy struct is byte-for-byte what it always was.

def now_ms() -> int:
    return time.time_ns() // 1_000_000


def _is_int_ms(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def canonical_event_struct(event: dict) -> dict:
    """The dict that gets hashed and signed. Raises ValueError for an ambiguous or bad time field."""
    has_ts, has_legacy = "ts" in event, "timestamp" in event
    if has_ts and has_legacy:
        raise ValueError("event carries both 'ts' and 'timestamp'; send exactly one")
    struct = {"action": event["action"], "author_pubkey": event["author_pubkey"],
              "payload": event["payload"], "previous_hash": event["previous_hash"]}
    if has_ts:
        if not _is_int_ms(event["ts"]):
            raise ValueError("'ts' must be a non-negative integer (milliseconds since epoch)")
        struct["ts"] = event["ts"]
    elif has_legacy:
        struct["timestamp"] = event["timestamp"]
    else:
        raise ValueError("event has no 'ts' or 'timestamp'")
    return struct


def canonical_event_bytes(event: dict) -> bytes:
    """Exactly the bytes compute_canonical_event_id hashes. Sign these, hash these."""
    return json.dumps(canonical_event_struct(event), sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def sign_event(key: Ed25519PrivateKey, event: dict) -> str:
    return key.sign(canonical_event_bytes(event)).hex()


def verify_event(event: dict) -> bool:
    """True only if 'signature' was made by the private key behind 'author_pubkey'."""
    try:
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(event["author_pubkey"]))
        sig = bytes.fromhex(event["signature"])
        pub.verify(sig, canonical_event_bytes(event))  # raises if anything was changed
        return True
    except (KeyError, ValueError, TypeError, InvalidSignature):
        return False


# --- Trusted-key allowlist --------------------------------------------------------------------
TRUSTED_KEYS_ENV = "OMNI_TRUSTED_KEYS_FILE"


def _normalise_pubkey(k) -> str:
    if not isinstance(k, str):
        raise ValueError(f"trusted key is not a string: {k!r}")
    k = k.strip().lower()
    if len(k) != 64 or any(ch not in "0123456789abcdef" for ch in k):
        raise ValueError(f"trusted key is not 64 hex chars (raw Ed25519 public key): {k!r}")
    return k


def load_trusted_keys(path=None):
    """Allowlist of hex Ed25519 public keys, or None when no allowlist is configured.

    path defaults to $OMNI_TRUSTED_KEYS_FILE. File is JSON: either ["<hex>", ...] or
    {"keys": ["<hex>", ...]}. A configured-but-missing or malformed file raises, so a typo
    never silently turns the allowlist off.
    """
    if path is None:
        path = os.environ.get(TRUSTED_KEYS_ENV, "").strip() or None
    if path is None:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("keys")
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON list of hex keys or {{\"keys\": [...]}}")
    return frozenset(_normalise_pubkey(k) for k in data)


def is_trusted(author_pubkey: str, trusted) -> bool:
    """No allowlist (None) means every validly signed key is accepted (legacy behaviour)."""
    if trusted is None:
        return True
    return isinstance(author_pubkey, str) and author_pubkey.strip().lower() in trusted
