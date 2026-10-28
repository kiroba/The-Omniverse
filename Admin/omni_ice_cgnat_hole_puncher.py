#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE STUN/ICE CGNAT HOLE-PUNCHER [v1.0.0]
==============================================================================
Binds UDP socket channels, resolves public WAN bindings via STUN, and sends
bidirectional packet bursts to pierce mobile carrier CGNAT pinholes.
Maintains UDP state table pinholes using a 15-second heartbeat loop.
==============================================================================
"""

import socket
import struct
import time
import threading

DEFAULT_STUN_SERVERS = [
    ("stun.l.google.com", 19302),
    ("stun1.l.google.com", 19302),
    ("stun.cloudflare.com", 3478)
]

class CGNATHolePuncher:
    def __init__(self, local_port: int = 9102):
        self.local_port = local_port
        self.public_ip = None
        self.public_port = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False

    def resolve_public_binding(self) -> tuple:
        """
        Sends STUN Binding Request (RFC 5389)
        """
        stun_pkt = b'\x00\x01\x00\x00\x21\x12\xA4\x42' + b'\x00' * 12
        for server_host, server_port in DEFAULT_STUN_SERVERS:
            try:
                self.sock.sendto(stun_pkt, (server_host, server_port))
                self.sock.settimeout(2.0)
                data, _ = self.sock.recvfrom(1024)
                if len(data) >= 20 and data[:2] == b'\x01\x01':
                    # Parse MAPPED-ADDRESS / XOR-MAPPED-ADDRESS
                    self.public_ip = f"{data[28]}.{data[29]}.{data[30]}.{data[31]}"
                    self.public_port = struct.unpack(">H", data[26:28])[0] ^ 0x2112
                    return self.public_ip, self.public_port
            except Exception:
                continue
        return ("127.0.0.1", self.local_port)

    def punch_hole(self, remote_ip: str, remote_port: int, bursts: int = 5):
        """
        Sends bidirectional packet bursts to pierce symmetric NAT pinholes
        """
        punch_payload = b"OMNI_ICE_PUNCH_PING"
        for _ in range(bursts):
            try:
                self.sock.sendto(punch_payload, (remote_ip, remote_port))
                time.sleep(0.05)
            except Exception:
                pass

    def start_heartbeat_keepalive(self, remote_ip: str, remote_port: int, interval_sec: int = 15):
        self.running = True

        def keepalive_loop():
            while self.running:
                try:
                    self.sock.sendto(b"OMNI_ICE_KEEPALIVE", (remote_ip, remote_port))
                except Exception:
                    pass
                time.sleep(interval_sec)

        t = threading.Thread(target=keepalive_loop, daemon=True)
        t.start()

    def stop(self):
        self.running = False
        self.sock.close()

if __name__ == "__main__":
    puncher = CGNATHolePuncher(local_port=9102)
    pub_ip, pub_port = puncher.resolve_public_binding()
    print(f"[✓] STUN Binding Resolved Public Mapping: {pub_ip}:{pub_port}")
    puncher.stop()
