#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE BLE DISCOVERY ENGINE [v1.0.0]
==============================================================================
Encodes and decodes 31-byte BLE Advertisement payload frames for offline
proximity discovery and 3-step handshake protocol (SYN, SYN-ACK, ACK).
==============================================================================
"""

import struct
import time
import hashlib

OMNI_BLE_SERVICE_UUID = 0xFFA0

class BLEAdvertisementFrame:
    @staticmethod
    def encode(node_id: str, state_flags: int = 0x01) -> bytes:
        """
        Encodes a 31-byte BLE Advertisement payload:
        [1 Byte Flags][2 Bytes Service UUID][16 Bytes Short Node Hash][1 Byte Status][11 Bytes Reserved]
        """
        node_hash_16 = hashlib.sha256(node_id.encode('utf-8')).digest()[:16]
        header = struct.pack(">B H", 0x02, OMNI_BLE_SERVICE_UUID)
        status_byte = struct.pack("B", state_flags & 0xFF)
        padding = b'\x00' * 11
        return header + node_hash_16 + status_byte + padding

    @staticmethod
    def decode(raw_bytes: bytes) -> dict:
        if len(raw_bytes) < 20:
            return {"error": "PAYLOAD_TOO_SHORT"}

        flag, service_uuid = struct.unpack(">B H", raw_bytes[:3])
        if service_uuid != OMNI_BLE_SERVICE_UUID:
            return {"error": "INVALID_SERVICE_UUID"}

        short_node_hash = "0x" + raw_bytes[3:19].hex()
        status_flag = raw_bytes[19]

        return {
            "service_uuid": hex(service_uuid),
            "short_node_hash": short_node_hash,
            "status_flag": status_flag,
            "timestamp": time.time()
        }

class BLEHandshakeSession:
    def __init__(self, local_node_id: str):
        self.local_node_id = local_node_id
        self.sessions = {}

    def create_syn(self, remote_node_hash: str) -> dict:
        syn_id = f"syn_{int(time.time())}"
        self.sessions[syn_id] = {"remote_hash": remote_node_hash, "state": "SYN_SENT"}
        return {"type": "SYN", "syn_id": syn_id, "from": self.local_node_id}

    def process_syn_ack(self, syn_ack_data: dict) -> dict:
        syn_id = syn_ack_data.get("syn_id")
        if syn_id in self.sessions:
            self.sessions[syn_id]["state"] = "CONNECTED"
            return {"type": "ACK", "syn_id": syn_id, "status": "HANDSHAKE_COMPLETE"}
        return {"error": "UNKNOWN_SYN_ID"}

if __name__ == "__main__":
    encoded = BLEAdvertisementFrame.encode("0xNODE_CHARLIE_789")
    print(f"Encoded BLE Frame ({len(encoded)} bytes): {encoded.hex()}")
    decoded = BLEAdvertisementFrame.decode(encoded)
    print("Decoded BLE Payload:")
    print(decoded)
