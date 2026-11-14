# Tests for the OmniMod compiler's S1 (real Ed25519) signing.
# Run: python3 -m unittest test_omni_mod_compiler -v   (from core/engines)
#
# The cryptography itself is additionally proven against OpenSSL
# (independent implementation, both directions) — see the S1 change
# notes. These tests pin the compiler-level contract: a signed pack
# verifies, one flipped byte fails, an unsigned pack is honestly
# unsigned, and the Merkle computation is byte-identical to the S0
# era (fixture root pinned below).
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from omni_mod_compiler import OmniModCompiler

TEST_SEED = "42" * 32
# Pinned from the S0-era algorithm: the fixture below hashed and
# Merkle-rooted with the pre-S1 code produces exactly this root.
# If this test ever fails, the Merkle computation changed — which
# would silently re-root every pack ever compiled.
FIXTURE_ROOT = "0x2596a7436b55562ed79477fbda3b4f4444660e93f14a7145c1bbd251f60b4a4e"


def _make_fixture(root: Path) -> Path:
    src = root / "fixture_src"
    (src / "sprites").mkdir(parents=True)
    (src / "sprites" / "a.txt").write_text("alpha asset bytes", encoding="utf-8")
    (src / "readme.txt").write_text("fixture pack", encoding="utf-8")
    (src / "manifest.json").write_text(json.dumps({
        "mod_id": "omnimod.test.fixture", "version": "0.1.0",
        "author": {"handle": "s1-proof", "pubkey_ed25519": None},
        "assets": {},
    }, indent=2), encoding="utf-8")
    return src


def _rezip(src_archive, dst_archive, transform):
    zin = zipfile.ZipFile(src_archive)
    with zipfile.ZipFile(dst_archive, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in zin.namelist():
            zout.writestr(name, transform(name, zin.read(name)))
    zin.close()


class OmniModCompilerS1Tests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.src = _make_fixture(self.root)
        self.compiler = OmniModCompiler(private_key_hex=TEST_SEED)

    def tearDown(self):
        self._tmp.cleanup()

    def _compile(self, compiler=None, out="out"):
        return (compiler or self.compiler).compile_mod_package(
            str(self.src), str(self.root / out))

    def test_fixture_root_matches_s0_pin(self):
        ok, _, manifest = self._compile(compiler=OmniModCompiler())
        self.assertTrue(ok)
        self.assertEqual(manifest["integrity"]["merkle_root"], FIXTURE_ROOT)

    def test_signed_pack_verifies(self):
        ok, archive, manifest = self._compile()
        self.assertTrue(ok)
        self.assertIsNotNone(manifest["integrity"]["signature_ed25519"])
        self.assertEqual(manifest["signing"]["status"], "ed25519")
        # The manifest names the key that actually signed.
        self.assertEqual(manifest["author"]["pubkey_ed25519"],
                         "0x" + self.compiler.public_key_hex)
        ok_v, _ = self.compiler.verify_mod_package(archive)
        self.assertTrue(ok_v)

    def test_wrong_pubkey_rejected(self):
        _, archive, _ = self._compile()
        other = OmniModCompiler(private_key_hex="43" * 32)
        ok_v, _ = other.verify_mod_package(
            archive, public_key_hex="0x" + other.public_key_hex)
        self.assertFalse(ok_v)

    def test_flipped_file_byte_fails(self):
        _, archive, _ = self._compile()
        def flip(name, data):
            if name == "sprites/a.txt":
                b = bytearray(data)
                b[0] ^= 0xFF
                return bytes(b)
            return data
        tampered = str(self.root / "tampered.omnimod")
        _rezip(archive, tampered, flip)
        ok_v, reason = self.compiler.verify_mod_package(tampered)
        self.assertFalse(ok_v)
        self.assertIn("hash mismatch", reason)

    def test_flipped_signature_char_fails(self):
        _, archive, _ = self._compile()
        def flip(name, data):
            if name == "manifest.json":
                m = json.loads(data)
                s = m["integrity"]["signature_ed25519"]
                m["integrity"]["signature_ed25519"] = (
                    s[:10] + ("0" if s[10] != "0" else "1") + s[11:])
                return json.dumps(m, indent=2).encode()
            return data
        tampered = str(self.root / "tampered_sig.omnimod")
        _rezip(archive, tampered, flip)
        ok_v, _ = self.compiler.verify_mod_package(tampered)
        self.assertFalse(ok_v)

    def test_unsigned_compile_is_honestly_unsigned(self):
        ok, archive, manifest = self._compile(compiler=OmniModCompiler())
        self.assertTrue(ok)
        self.assertIsNone(manifest["integrity"]["signature_ed25519"])
        self.assertEqual(manifest["signing"]["status"], "unsigned")
        ok_v, reason = OmniModCompiler().verify_mod_package(archive)
        self.assertFalse(ok_v)
        self.assertIn("unsigned", reason)


if __name__ == "__main__":
    unittest.main()
