#!/usr/bin/env python3
"""The W-row parser rejects missing, partial and incorrect witnesses."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).with_name("rows.py")
spec = importlib.util.spec_from_file_location("security_rows", path)
rows = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rows)


class Verdicts(unittest.TestCase):
    def test_socket(self):
        lines = [f"security: W1 {call} cap {cap} result 4 length 16 bounded 1\n"
                 for call in ("recvfrom", "recvmsg") for cap in (0, 1, 8, 16)]
        text = "".join(lines)
        self.assertEqual(rows.evaluate("socket", text), {"W1": True})
        for line in lines:
            self.assertFalse(rows.evaluate("socket", text.replace(line, ""))["W1"])
        for wrong in (text + lines[0], text.replace("bounded 1", "bounded 0", 1),
                      text.replace("result 4", "result -14", 1),
                      text.replace("length 16", "length 0", 1), text + "PANIC overflow\n",
                      text + "security: setup failed\n", ""):
            self.assertFalse(rows.evaluate("socket", wrong)["W1"])


if __name__ == "__main__":
    unittest.main()
