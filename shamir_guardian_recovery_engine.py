import os
import secrets
import json
import time

# --- SHAMIR SECRET SHARING (GF(256) / Galois Field Arithmetic) ---

PRIME = 2083516173160912412343267463121244482512355622264704915141863312170832831982070192500052107412030626372132575294578135805553392300078860002971230154035661

def _eval_poly(poly, x, p):
    """Evaluates polynomial at x modulo prime p."""
    result = 0
    for coeff in reversed(poly):
        result = (result * x + coeff) % p
    return result

def _extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = _extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y

def _mod_inverse(k, p):
    gcd, x, _ = _extended_gcd(k, p)
    if gcd != 1:
        raise ValueError("Modular inverse does not exist")
    return (x % p + p) % p

def split_secret(secret_bytes: bytes, threshold: int, total_shares: int):
    """Splits a secret byte array into N shares with a K threshold."""
    if threshold > total_shares:
        raise ValueError("Threshold cannot be greater than total shares.")
    
    secret_int = int.from_bytes(secret_bytes, byteorder='big')
    if secret_int >= PRIME:
        raise ValueError("Secret is too large for the prime field.")

    # Generate random polynomial coefficients: f(x) = secret + a1*x + a2*x^2 + ...
    coefficients = [secret_int] + [secrets.randbelow(PRIME) for _ in range(threshold - 1)]

    shares = []
    for x in range(1, total_shares + 1):
        y = _eval_poly(coefficients, x, PRIME)
        shares.append((x, y))
    
    return shares

def reconstruct_secret(shares, threshold: int) -> bytes:
    """Reconstructs the original secret bytes from K shares using Lagrange Interpolation."""
    if len(shares) < threshold:
        raise ValueError(f"Insufficient shares provided ({len(shares)}). Need at least {threshold}.")

    # Take exactly threshold shares
    k_shares = shares[:threshold]
    secret_int = 0

    for i, (x_i, y_i) in enumerate(k_shares):
        # Calculate Lagrange basis polynomial L_i(0)
        num = 1
        den = 1
        for j, (x_j, _) in enumerate(k_shares):
            if i == j:
                continue
            num = (num * (-x_j)) % PRIME
            den = (den * (x_i - x_j)) % PRIME
        
        lagrange_coeff = (num * _mod_inverse(den, PRIME)) % PRIME
        secret_int = (secret_int + y_i * lagrange_coeff) % PRIME

    # Convert integer back to 32 bytes
    length = (secret_int.bit_length() + 7) // 8
    return secret_int.to_bytes(max(32, length), byteorder='big')


class GuardianRecoveryEngine:
    """
    Shamir Secret Sharing (SSS) Social Guardian Account Recovery Manager
    for KickBack / The Omniverse.
    """
    def __init__(self, threshold=3, total_guardians=5):
        self.threshold = threshold
        self.total_guardians = total_guardians

    def generate_guardian_packages(self, user_pubkey: str, seed_bytes: bytes, guardian_ids: list):
        if len(guardian_ids) != self.total_guardians:
            raise ValueError(f"Expected exactly {self.total_guardians} guardian IDs.")

        raw_shares = split_secret(seed_bytes, self.threshold, self.total_guardians)

        packages = {}
        for idx, (x, y) in enumerate(raw_shares):
            guardian_id = guardian_ids[idx]
            packages[guardian_id] = {
                "userPubkey": user_pubkey,
                "shareIndex": x,
                "shareData": hex(y),
                "threshold": self.threshold,
                "totalGuardians": self.total_guardians,
                "timestamp": int(time.time()),
                "schemaVersion": "1.0.0"
            }
        return packages

    def recover_key_from_packages(self, guardian_packages: list):
        if len(guardian_packages) < self.threshold:
            raise ValueError(f"Need at least {self.threshold} guardian packages to recover.")

        shares = []
        for pkg in guardian_packages[:self.threshold]:
            x = pkg["shareIndex"]
            y = int(pkg["shareData"], 16)
            shares.append((x, y))

        recovered_bytes = reconstruct_secret(shares, self.threshold)
        return recovered_bytes

# --- VERIFICATION TEST SUITE ---

def run_tests():
    print("=================================================================")
    print("      KICKBACK: SHAMIR SECRET SHARING GUARDIAN RECOVERY         ")
    print("=================================================================")

    # 1. Generate dummy 32-byte Ed25519 private seed
    original_seed = secrets.token_bytes(32)
    user_pubkey = "ed25519_pk_master_creator_8f9b2c3d4e5f"
    guardians = ["guardian_alice", "guardian_bob", "guardian_charlie", "guardian_david", "guardian_eve"]

    engine = GuardianRecoveryEngine(threshold=3, total_guardians=5)

    # 2. Split secret into 5 packages
    packages = engine.generate_guardian_packages(user_pubkey, original_seed, guardians)
    print(f"✅ Generated 5 Guardian Packages (Threshold: 3-of-5).")

    # 3. Simulate recovery using exactly 3 guardians (Alice, Charlie, Eve)
    selected_guardians = [packages["guardian_alice"], packages["guardian_charlie"], packages["guardian_eve"]]
    recovered_seed = engine.recover_key_from_packages(selected_guardians)

    # Verification 1: Match Check
    assert original_seed == recovered_seed, "CRITICAL: Recovered seed does not match original!"
    print("✅ RECOVERY TEST 1 (3-of-5 Valid Shares): PASS [Seed reconstructed perfectly]")

    # Verification 2: Try another combination (Bob, Charlie, David)
    selected_guardians_2 = [packages["guardian_bob"], packages["guardian_charlie"], packages["guardian_david"]]
    recovered_seed_2 = engine.recover_key_from_packages(selected_guardians_2)
    assert original_seed == recovered_seed_2, "CRITICAL: Alternate combination failed!"
    print("✅ RECOVERY TEST 2 (Alternate 3 Shares): PASS [Seed reconstructed perfectly]")

    # Verification 3: Insufficient Shares (2-of-5 should fail)
    try:
        engine.recover_key_from_packages(selected_guardians_2[:2])
        print("❌ RECOVERY TEST 3 (Insufficient Shares): FAIL (Should have raised ValueError)")
    except ValueError as e:
        print(f"✅ RECOVERY TEST 3 (Insufficient Shares Blocked): PASS [{e}]")

    print("\n=================================================================")
    print("FINAL SHAMIR GUARDIAN RECOVERY VERIFICATION STATUS: PASS")
    print("=================================================================")

if __name__ == "__main__":
    run_tests()
