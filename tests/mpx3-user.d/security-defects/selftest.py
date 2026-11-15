#!/usr/bin/env python3
"""The W-row parser rejects missing, partial and incorrect witnesses."""
import importlib.util
from pathlib import Path
import unittest
import sys
sys.dont_write_bytecode = True

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

    def test_credentials(self):
        text = ""
        for mode in range(4):
            text += (f"security: W2 ids mode {mode} uid 1000 euid {0 if mode == 0 else 1000} "
                     f"gid 1000 egid {42 if mode == 0 else 1000} nnp {int(bool(mode & 2))}\n")
            if mode & 1:
                text += f"security: W2 trace mode {mode} stop 1407 continue 0\n"
            text += f"security: W2 exit mode {mode} status 0\n"
        text += "security: attach-after-setid result -1\n"
        self.assertTrue(all(rows.evaluate("credentials", text).values()))
        for wrong in (text.replace("mode 1 uid 1000 euid 1000", "mode 1 uid 1000 euid 0"),
                      text.replace("mode 1 stop 1407", "mode 1 stop 0"),
                      text.replace("mode 3 status 0", "mode 3 status 99"),
                      text.replace("continue 0", "continue -3"), ""):
            self.assertFalse(rows.evaluate("credentials", wrong)["W2"])
        self.assertFalse(rows.evaluate("credentials", text.replace("result -1", "result 0"))["attach-after-setid"])


    def test_signals(self):
        text = "".join(f"security: W{mode} child status {status}\n"
                       for mode, status in ((3, 11), (4, 5632), (5, 5632), (6, 139), (0, 0)))
        self.assertTrue(all(rows.evaluate("signals", text).values()))
        for mode in (3, 4, 5, 6):
            line = next(line for line in text.splitlines(True) if line.startswith(f"security: W{mode} "))
            for wrong in (text.replace(line, ""), text + line,
                          text.replace(line, f"security: W{mode} child status 0\n"),
                          text + "PANIC overflow\n", text.replace("W0 child status 0", "W0 child status 99")):
                self.assertFalse(rows.evaluate("signals", wrong)[f"W{mode}"])

    def test_helper_parser(self):
        spec = importlib.util.spec_from_file_location("helper_rows", path.with_name("helper_rows.py"))
        helpers = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helpers)
        lines = ["PASS " + row + "\n" for row in helpers.ROWS]
        text = "".join(lines)
        self.assertTrue(helpers.evaluate(text))
        for line in lines:
            self.assertFalse(helpers.evaluate(text.replace(line, "")))
            self.assertFalse(helpers.evaluate(text + line))
        for wrong in ("", text + "PANIC page fault\n", text + "FAIL other\n"):
            self.assertFalse(helpers.evaluate(wrong))
        self.assertFalse(helpers.checked_api("pub fn put(p: u64) {}"))


if __name__ == "__main__":
    unittest.main()
