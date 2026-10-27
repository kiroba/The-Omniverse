"""omni_signing.py - persistent Ed25519 identity + event signing for the Omniverse daemon.
pip install cryptography
"""
import json
import os
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
    """Exactly the bytes compute_canonical_event_id already hashes. Sign these, hash these."""
    return json.dumps(
        {"action": action, "author_pubkey": author_pubkey, "payload": payload,
         "previous_hash": previous_hash, "timestamp": timestamp},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def sign_event(key: Ed25519PrivateKey, event: dict) -> str:
    msg = canonical_bytes(event["action"], event["author_pubkey"], event["payload"],
                          event["previous_hash"], event["timestamp"])
    return key.sign(msg).hex()


def verify_event(event: dict) -> bool:
    """True only if 'signature' was made by the private key behind 'author_pubkey'."""
    try:
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(event["author_pubkey"]))
        sig = bytes.fromhex(event["signature"])
        msg = canonical_bytes(event["action"], event["author_pubkey"], event["payload"],
                              event["previous_hash"], event["timestamp"])
        pub.verify(sig, msg)  # raises if anything was changed
        return True
    except (KeyError, ValueError, TypeError, InvalidSignature):
        return False
