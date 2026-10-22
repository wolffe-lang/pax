#!/usr/bin/env python3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / "tests/mpx5-wolf.d/native.py"

class NativeRows(unittest.TestCase):
    def run_case(self, pax, linux):
        with tempfile.TemporaryDirectory(prefix="px60-native-") as d:
            a, b = Path(d) / "pax", Path(d) / "linux"
            a.write_bytes(pax)
            b.write_bytes(linux)
            return subprocess.run([sys.executable, "-I", str(CHECK), str(a), str(b)], capture_output=True)

    def test_live_native_recordings(self):
        r = self.run_case((ROOT / "notes/px60/native-pax.log").read_bytes(),
                          (ROOT / "notes/px60/native-linux.tty").read_bytes())
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_equal_failures_do_not_pass(self):
        a = (ROOT / "notes/px60/native-pax.log").read_bytes()
        b = (ROOT / "notes/px60/native-linux.tty").read_bytes()
        for old, new in ((b"link-hello=0", b"link-hello=2"),
                         (b"native-loop=0", b"native-loop=1"),
                         (b"hello, wolf", b"wrong output"),
                         (b"uid=1000", b"uid=0")):
            with self.subTest(old=old):
                self.assertIn(old, a)
                self.assertIn(old, b)
                r = self.run_case(a.replace(old, new), b.replace(old, new))
                self.assertNotEqual(r.returncode, 0)

if __name__ == "__main__":
    unittest.main()
