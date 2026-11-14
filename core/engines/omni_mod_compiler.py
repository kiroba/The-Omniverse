# ============================================================================
# OMNIVERSE & LOCALSEND: PHASER 2D MOD COMPILER & PACKAGER
# Protocol Tag: [FUNDAMENTAL_FEATURE_TAG: LOCALSEND_PHASER_STUDIO_V1]
# ============================================================================
#
# Signing (S1, Nov 13, 2026): REAL Ed25519 (RFC 8032) over the package
# Merkle root, via the vendored zero-dependency implementation in
# ed25519_rfc8032.py. Before S1 this step was a SIMULATION (S0: two
# SHA-256 passes keyed with a mock secret). The simulation is gone. A
# compiler built without a private key compiles UNSIGNED packs
# (integrity.signature_ed25519 is null and the manifest signing block
# says so) rather than faking one. A compiler built with a key signs
# and stamps author.pubkey_ed25519 with the key it actually signed
# with; verify_mod_package() checks a compiled pack end to end —
# every file hash, the Merkle root, and the Ed25519 signature.
# File hashing and the Merkle computation are byte-identical to the
# S0 era: packs compiled before S1 keep the same Merkle roots (their
# signatures, being simulations, do not verify — that is the point).

import os
import sys
import json
import zipfile
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

try:
    from . import ed25519_rfc8032 as _ed25519
except Exception:
    try:
        import ed25519_rfc8032 as _ed25519
    except Exception:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import ed25519_rfc8032 as _ed25519


def _normalize_hex(value: str) -> str:
    v = value.strip().lower()
    if v.startswith("0x"):
        v = v[2:]
    return v


class OmniModCompiler:
    """
    Automates compiling, hashing, Merkle root generation, Ed25519 signing,
    and packaging of Phaser 2D creator assets into signed `.omnimod` archives.
    """

    def __init__(self, private_key_hex: str = None):
        """
        Builds a compiler. With a 32-byte Ed25519 seed (hex, optional
        0x prefix) the compiler signs for real and derives the matching
        public key. Without one it compiles unsigned packs — it never
        simulates a signature.
        """
        self.private_key_hex: Optional[str] = None
        self.public_key_hex: Optional[str] = None
        if private_key_hex:
            seed = bytes.fromhex(_normalize_hex(private_key_hex))
            if len(seed) != 32:
                raise ValueError("Ed25519 private key seed must be 32 bytes")
            self.private_key_hex = seed.hex()
            self.public_key_hex = _ed25519.publickey(seed).hex()

    def calculate_file_sha256(self, file_path: Path) -> str:
        """Calculates SHA-256 digest of a single file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def build_merkle_root(self, file_hashes: Dict[str, str]) -> str:
        """
        Constructs a deterministic Merkle tree root over sorted relative file paths
        and their SHA-256 hashes.
        """
        sorted_pairs = sorted(file_hashes.items(), key=lambda x: x[0])
        combined_leaves = "".join([f"{path}:{h}" for path, h in sorted_pairs])
        return "0x" + hashlib.sha256(combined_leaves.encode("utf-8")).hexdigest()

    def sign_merkle_root(self, merkle_root_hex: str) -> Optional[str]:
        """
        Produces a REAL Ed25519 signature over the Merkle root string —
        the exact message bytes the S0 simulation claimed to sign, so
        the signed statement is unchanged; only the cryptography became
        real. Returns "0x" + 128 hex chars, or None when this compiler
        holds no key (unsigned compile).
        """
        if self.private_key_hex is None:
            return None
        sig = _ed25519.signature(
            merkle_root_hex.encode("utf-8"),
            bytes.fromhex(self.private_key_hex),
            bytes.fromhex(self.public_key_hex),
        )
        return "0x" + sig.hex()

    @staticmethod
    def verify_signature(merkle_root_hex: str, signature_hex: str,
                         public_key_hex: str) -> bool:
        """True iff signature_hex is a valid Ed25519 signature of the
        Merkle root string under public_key_hex. Never raises."""
        try:
            return _ed25519.checkvalid(
                bytes.fromhex(_normalize_hex(signature_hex)),
                merkle_root_hex.encode("utf-8"),
                bytes.fromhex(_normalize_hex(public_key_hex)),
            )
        except Exception:
            return False

    def compile_mod_package(
        self,
        source_dir: str,
        output_dir: str = "/workspace/scratch",
        manifest_override: Dict[str, Any] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Compiles a raw workspace directory into a signed `.omnimod` archive.
        """
        src_path = Path(source_dir)
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        if not src_path.exists() or not src_path.is_dir():
            return False, f"Source directory {source_dir} does not exist.", {}

        manifest_file = src_path / "manifest.json"
        if not manifest_file.exists():
            return False, "Missing required manifest.json in source directory.", {}

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        if manifest_override:
            manifest_data.update(manifest_override)

        # 1. Scan directory and compute file hashes
        file_hashes = {}
        total_uncompressed_bytes = 0

        for file_item in src_path.rglob("*"):
            if file_item.is_file() and file_item.name != "manifest.json":
                rel_path = file_item.relative_to(src_path).as_posix()
                file_hash = self.calculate_file_sha256(file_item)
                file_hashes[rel_path] = file_hash
                total_uncompressed_bytes += file_item.stat().st_size

        # Include manifest hash baseline
        file_hashes["manifest.json"] = "0" * 64  # Placeholder before final signature

        # 2. Compute Merkle Root & Ed25519 Signature (real, when a key is held)
        merkle_root = self.build_merkle_root(file_hashes)
        signature = self.sign_merkle_root(merkle_root)

        # Update manifest integrity block
        manifest_data["integrity"] = {
            "file_hashes": file_hashes,
            "merkle_root": merkle_root,
            "signature_ed25519": signature
        }

        # The pack names the key that actually signed it — never a key
        # the manifest merely claims. Unsigned compiles say so instead.
        if signature is not None:
            author = manifest_data.get("author")
            if isinstance(author, dict):
                author["pubkey_ed25519"] = "0x" + self.public_key_hex
            manifest_data["signing"] = {
                "status": "ed25519",
                "note": "Real Ed25519 signature (RFC 8032) over the Merkle "
                        "root in integrity.signature_ed25519; verify "
                        "against author.pubkey_ed25519."
            }
        else:
            manifest_data["signing"] = {
                "status": "unsigned",
                "note": "Compiled without a private key: file hashes and "
                        "Merkle root only, no signature."
            }

        # Update distribution byte estimates
        if "distribution" not in manifest_data:
            manifest_data["distribution"] = {}

        manifest_data["distribution"]["chunk_size_bytes"] = 524288  # 512 KB
        manifest_data["distribution"]["total_bytes"] = total_uncompressed_bytes

        # Save finalized manifest back to memory/temp
        mod_id = manifest_data.get("mod_id", "omnimod.default.sample")
        omnimod_filename = f"{mod_id}.omnimod"
        target_archive_path = out_path / omnimod_filename

        # 3. Create Zip Archive Container
        with zipfile.ZipFile(target_archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Write updated manifest.json
            zipf.writestr("manifest.json", json.dumps(manifest_data, indent=2))

            # Write all other source files
            for rel_path in file_hashes.keys():
                if rel_path != "manifest.json":
                    file_full_path = src_path / rel_path
                    zipf.write(file_full_path, arcname=rel_path)

        # Compute final compressed size for distribution block
        archive_size = target_archive_path.stat().st_size
        manifest_data["distribution"]["total_bytes"] = archive_size

        return True, str(target_archive_path), manifest_data

    def verify_mod_package(self, archive_path: str,
                           public_key_hex: str = None) -> Tuple[bool, str]:
        """
        Verifies a compiled .omnimod end to end: every packed file's
        SHA-256 against the manifest's integrity block, the Merkle root
        rebuilt from those hashes, and the Ed25519 signature over the
        root — against public_key_hex when given, else the pack's own
        author.pubkey_ed25519. Returns (ok, human-readable reason).
        """
        try:
            zipf = zipfile.ZipFile(archive_path, "r")
        except Exception as e:
            return False, f"Cannot open archive: {e}"

        with zipf:
            names = [n for n in zipf.namelist() if not n.endswith("/")]
            if "manifest.json" not in names:
                return False, "Archive carries no manifest.json."
            try:
                manifest_data = json.loads(zipf.read("manifest.json").decode("utf-8"))
            except Exception as e:
                return False, f"Manifest does not parse: {e}"

            integrity = manifest_data.get("integrity")
            if not isinstance(integrity, dict):
                return False, "Manifest carries no integrity block."
            recorded = integrity.get("file_hashes")
            if not isinstance(recorded, dict):
                return False, "Integrity block carries no file hashes."

            recomputed: Dict[str, str] = {}
            for name in names:
                if name == "manifest.json":
                    continue
                recomputed[name] = hashlib.sha256(zipf.read(name)).hexdigest()
            recomputed["manifest.json"] = "0" * 64

            if recomputed != recorded:
                for path in sorted(set(recomputed) | set(recorded)):
                    if recomputed.get(path) != recorded.get(path):
                        return False, f"File hash mismatch: {path}."
                return False, "File hash set mismatch."

            merkle_root = self.build_merkle_root(recomputed)
            if merkle_root != integrity.get("merkle_root"):
                return False, "Merkle root mismatch."

            signature = integrity.get("signature_ed25519")
            if not signature:
                return False, ("File hashes and Merkle root verify, but "
                               "the pack is unsigned.")

            pubkey = public_key_hex
            if not pubkey:
                author = manifest_data.get("author")
                if isinstance(author, dict):
                    pubkey = author.get("pubkey_ed25519")
            if not pubkey:
                return False, ("Pack is signed but no public key is "
                               "available to verify against.")

            if not self.verify_signature(merkle_root, signature, pubkey):
                return False, "Ed25519 signature does NOT verify."
            return True, (f"Verified: file hashes, Merkle root "
                          f"{merkle_root[:18]}..., and Ed25519 signature "
                          f"under key {_normalize_hex(str(pubkey))[:16]}...")


if __name__ == "__main__":
    # Test compilation flow — uses a THROWAWAY key generated fresh each
    # run (never a real author key), then verifies its own output.
    sample_src = Path("/workspace/scratch/sample_phaser_game")
    sample_src.mkdir(parents=True, exist_ok=True)
    (sample_src / "src").mkdir(exist_ok=True)
    (sample_src / "assets").mkdir(exist_ok=True)

    # Dummy files
    with open(sample_src / "src" / "game_logic.js", "w") as f:
        f.write("console.log('Phaser 3 Game Init');")
    with open(sample_src / "assets" / "tilemap.json", "w") as f:
        f.write('{"layers": [], "width": 10, "height": 10}')

    sample_manifest = {
        "schema_version": "1.0.0",
        "mod_id": "omnimod.alex_creative.cyber_runner_2d",
        "version": "1.0.0",
        "title": "Cyber Runner 2D",
        "category": "arcade_game",
        "author": {
            "handle": "@alex.creative",
            "pubkey_ed25519": "0x8F92A1B439C0E71D000000000000000000000000000000000000000000000001",
            "attestation_badge": "HUMAN_VERIFIED_CREATOR"
        },
        "engine_target": {
            "framework": "phaser_3_canvas",
            "min_framework_version": "3.80.0",
            "entrypoint": "src/game_logic.js",
            "sandbox_permissions": ["CANVAS_RENDER_2D", "AUDIO_PLAYBACK"]
        },
        "assets": {"spritesheets": [], "tilemaps": [], "audio_banks": []}
    }

    with open(sample_src / "manifest.json", "w") as f:
        json.dump(sample_manifest, f, indent=2)

    compiler = OmniModCompiler(private_key_hex=os.urandom(32).hex())
    print(f"Demo author public key: 0x{compiler.public_key_hex}")
    success, archive_path, final_manifest = compiler.compile_mod_package(str(sample_src))
    print(f"Compilation success: {success}")
    print(f"Archive path: {archive_path}")
    print(f"Merkle Root: {final_manifest['integrity']['merkle_root']}")
    ok, reason = compiler.verify_mod_package(archive_path)
    print(f"Verification: {ok} — {reason}")
