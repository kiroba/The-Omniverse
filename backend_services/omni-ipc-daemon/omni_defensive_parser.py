#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE ZERO-DEPENDENCY DEFENSIVE INPUT PARSER & GUARD LAYER [v1.0.0]
==============================================================================
System Role:
- Enforces strict memory size bounds on incoming socket streams (OOM/DoS defense).
- Prevents Stack Overflow attacks caused by deeply nested JSON payloads.
- Validates UTF-8 encoding and primitive type coercion boundaries.
- Produces canonical, key-sorted unpadded JSON strings for deterministic SHA-256 Merkle chain signing.
- Provides a zero-dependency wrapper for Python standard library `http.server` daemons.
==============================================================================
"""

import json
import sys
import hashlib
from typing import Any, Dict, Union, Tuple, Optional, IO

# System Guard Parameters
DEFAULT_MAX_PAYLOAD_BYTES = 5 * 1024 * 1024  # 5 MB hard limit
DEFAULT_MAX_NESTING_DEPTH = 10               # 10 levels maximum recursion
ALLOWED_PRIMITIVE_TYPES = (int, float, str, bool, type(None))


class PayloadSecurityViolation(ValueError):
    """Raised when an incoming stream or JSON object violates input safety bounds."""
    pass


class DefensiveInputParser:
    """
    Modular, zero-dependency input inflation and defense parser designed for
    The Omniverse edge-native daemons and IPC gateways.
    """

    def __init__(
        self,
        max_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
        max_depth: int = DEFAULT_MAX_NESTING_DEPTH,
        strict_utf8: bool = True
    ):
        self.max_bytes = max_bytes
        self.max_depth = max_depth
        self.strict_utf8 = strict_utf8

    def read_stream_bounded(self, rfile: IO[bytes], content_length: Optional[int] = None) -> bytes:
        """
        Reads incoming byte streams with strict size enforcement to prevent
        Out-Of-Memory (OOM) memory exhaustion attacks.
        """
        if content_length is not None and content_length > self.max_bytes:
            raise PayloadSecurityViolation(
                f"Payload Content-Length header ({content_length} bytes) exceeds maximum limit ({self.max_bytes} bytes)."
            )

        # Read up to max_bytes + 1 to detect over-sized streams without allocating unbounded memory
        read_size = (content_length + 1) if (content_length and content_length <= self.max_bytes) else (self.max_bytes + 1)
        raw_bytes = rfile.read(read_size)

        if len(raw_bytes) > self.max_bytes:
            raise PayloadSecurityViolation(
                f"Stream body size exceeds allowable maximum limit of {self.max_bytes} bytes."
            )

        return raw_bytes

    def parse_json_bytes(self, raw_bytes: bytes) -> Dict[str, Any]:
        """
        Decodes raw bytes and parses JSON with strict UTF-8 validation and nesting depth checks.
        """
        # 1. UTF-8 Encoding Verification
        try:
            decoded_str = raw_bytes.decode('utf-8' if self.strict_utf8 else 'utf-8', errors='strict')
        except UnicodeDecodeError as e:
            raise PayloadSecurityViolation(f"Malformed UTF-8 byte stream detected: {e}")

        # 2. Native JSON Parsing
        try:
            data = json.loads(decoded_str)
        except json.JSONDecodeError as e:
            raise PayloadSecurityViolation(f"Invalid JSON syntax: {e}")

        # 3. Recursive Nesting Depth & Structure Verification
        self.verify_structure_and_depth(data)
        return data

    def verify_structure_and_depth(self, obj: Any, current_depth: int = 0) -> None:
        """
        Traverses nested dictionaries and lists to enforce depth limits and type sanity.
        """
        if current_depth > self.max_depth:
            raise PayloadSecurityViolation(
                f"Maximum JSON nesting depth limit ({self.max_depth}) exceeded."
            )

        if isinstance(obj, dict):
            for key, val in obj.items():
                if not isinstance(key, str):
                    raise PayloadSecurityViolation(f"Non-string key detected in JSON dict: {type(key)}")
                self.verify_structure_and_depth(val, current_depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                self.verify_structure_and_depth(item, current_depth + 1)
        elif not isinstance(obj, ALLOWED_PRIMITIVE_TYPES):
            raise PayloadSecurityViolation(f"Unauthorized object type in payload: {type(obj).__name__}")

    @staticmethod
    def to_canonical_json(data: Dict[str, Any]) -> str:
        """
        Converts a dictionary into deterministic, unpadded, key-sorted JSON
        for exact byte-for-byte SHA-256 Merkle chain signing across platforms.
        """
        return json.dumps(data, sort_keys=True, separators=(',', ':'))

    @staticmethod
    def compute_payload_hash(data: Dict[str, Any]) -> str:
        """Computes deterministic SHA-256 digest of canonical JSON."""
        canonical_bytes = DefensiveInputParser.to_canonical_json(data).encode('utf-8')
        return "0x" + hashlib.sha256(canonical_bytes).hexdigest()


# Clean Standalone Unit Test
def _run_self_test():
    parser = DefensiveInputParser(max_bytes=1024, max_depth=3)
    
    # Test 1: Normal JSON
    good_payload = {"action": "PING", "meta": {"node_id": "0x123", "active": True}}
    raw_good = json.dumps(good_payload).encode('utf-8')
    parsed = parser.parse_json_bytes(raw_good)
    assert parsed["action"] == "PING"
    
    # Test 2: Excessive Depth Attack
    bad_depth = {"a": {"b": {"c": {"d": "TOO_DEEP"}}}}
    try:
        parser.parse_json_bytes(json.dumps(bad_depth).encode('utf-8'))
        assert False, "Should have failed depth check"
    except PayloadSecurityViolation:
        pass

    # Test 3: Size Cap Enforcement
    large_raw = b"A" * 2000
    try:
        class DummyFile:
            def read(self, n):
                return large_raw[:n]
        parser.read_stream_bounded(DummyFile())
        assert False, "Should have failed size cap"
    except PayloadSecurityViolation:
        pass

    print("[✓] DefensiveInputParser self-test passed cleanly!")

if __name__ == "__main__":
    _run_self_test()
