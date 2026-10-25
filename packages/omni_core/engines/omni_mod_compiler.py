# ============================================================================
# OMNIVERSE & LOCALSEND: PHASER 2D MOD COMPILER & PACKAGER
# Protocol Tag: [FUNDAMENTAL_FEATURE_TAG: LOCALSEND_PHASER_STUDIO_V1]
# ============================================================================

import os
import json
import zipfile
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple


class OmniModCompiler:
    """
    Automates compiling, hashing, Merkle root generation, Ed25519 signing,
    and packaging of Phaser 2D creator assets into signed `.omnimod` archives.
    """

    def __init__(self, private_key_hex: str = None):
        # Default mock Ed25519 key if none provided
        self.private_key_hex = private_key_hex or ("0x" + "a1" * 32)

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

    def sign_merkle_root(self, merkle_root_hex: str) -> str:
        """
        Simulates Ed25519 Hardware Enclave signing over the Merkle root.
        """
        msg_bytes = merkle_root_hex.encode("utf-8")
        key_bytes = self.private_key_hex.encode("utf-8")
        sig_hash = hashlib.sha256(msg_bytes + key_bytes).hexdigest()
        # Returns 128-char hex signature representation
        return "0x" + sig_hash + hashlib.sha256(sig_hash.encode("utf-8")).hexdigest()

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

        # 2. Compute Merkle Root & Enclave Signature
        merkle_root = self.build_merkle_root(file_hashes)
        signature = self.sign_merkle_root(merkle_root)

        # Update manifest integrity block
        manifest_data["integrity"] = {
            "file_hashes": file_hashes,
            "merkle_root": merkle_root,
            "signature_ed25519": signature
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


if __name__ == "__main__":
    # Test compilation flow
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

    compiler = OmniModCompiler()
    success, archive_path, final_manifest = compiler.compile_mod_package(str(sample_src))
    print(f"Compilation success: {success}")
    print(f"Archive path: {archive_path}")
    print(f"Merkle Root: {final_manifest['integrity']['merkle_root']}")
