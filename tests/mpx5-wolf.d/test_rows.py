#!/usr/bin/env python3
"""The independent witness checker must reject agreement on broken output."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / "tests/mpx5-wolf.d/rows.py"

# px65: the sessions are the PAX side of kasumi's mpx5-wolf run at the
# 0.2.35 pin (the version line the witness reads from user/wolf.pin).
class Rows(unittest.TestCase):
    def run_case(self, text, user="root"):
        with tempfile.TemporaryDirectory(prefix="px60-rows-") as d:
            p = Path(d) / "session"
            p.write_text(text)
            return subprocess.run([sys.executable, "-I", str(CHECK), str(p), user],
                                  text=True, capture_output=True)

    def test_live_root_and_user_recordings(self):
        for user, filename in (("root", "notes/px65/wolf-pax-root.tty"),
                               ("pax", "notes/px65/wolf-pax-user.tty")):
            result = self.run_case((ROOT / filename).read_text(), user)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_broken_witnesses_fail_even_if_a_linux_twin_agrees(self):
        text = (ROOT / "notes/px65/wolf-pax-root.tty").read_text()
        for before, after, named in (
            ("typecheck-std=0", "typecheck-std=2", "typecheck-std"),
            ("fmt-hello=0", "fmt-hello=1", "fmt-hello"),
            ("object=0", "object=2", "object=0"),
            ("std: wolf\\n", "std: broken\\n", "std"),
            ('"impl":"wolfgang"', '"impl":"other"', "identity"),
        ):
            with self.subTest(named=named):
                self.assertIn(before, text)
                result = self.run_case(text.replace(before, after))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(named, result.stdout)

if __name__ == "__main__":
    unittest.main()
