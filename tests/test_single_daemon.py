"""Issue #6: only one daemon implementation; the old path redirects to it.

Run: python -m unittest tests/test_single_daemon.py -v
"""
import ast
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "Admin" / "omni_live_daemon_server.py"
SHIM = ROOT / "backend_services" / "omni-ipc-daemon" / "omni_live_daemon_server.py"


class SingleDaemonTests(unittest.TestCase):
    def test_shim_has_no_daemon_code(self):
        tree = ast.parse(SHIM.read_text(encoding="utf-8"))
        names = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        self.assertEqual(names, set(), "redirect must not define its own handlers or servers")
        self.assertLess(len(SHIM.read_text(encoding="utf-8").splitlines()), 40)

    def test_shim_points_at_existing_canonical(self):
        code = ("import runpy,sys; g=runpy.run_path(%r, run_name='not_main'); "
                "print(g['CANONICAL'])") % str(SHIM)
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(Path(out.stdout.strip()), CANONICAL)
        self.assertTrue(CANONICAL.is_file())

    def test_no_other_full_daemon_copies(self):
        copies = [p for p in ROOT.rglob("omni_live_daemon_server.py")
                  if ".git" not in p.parts and p not in (CANONICAL, SHIM)
                  and "ThreadingHTTPServer" in p.read_text(encoding="utf-8", errors="ignore")]
        self.assertEqual(copies, [], f"extra daemon copies: {copies}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
