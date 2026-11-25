#!/usr/bin/env python3
"""Pure identity-parser checks; no formatter, engine or image is run."""
from pathlib import Path
import runpy
import unittest

HERE = Path(__file__).resolve().parent
ROW = runpy.run_path(str(HERE / "row.py"))
LOCKS = [line.split() for line in (HERE / "binaries.sha256").read_text().splitlines()]
VERSION = ROW["VERSION"]


def native():
    return ("e2fsprogs=" + VERSION + "\n" +
            "".join(sha + "  " + path + "\n" for sha, path in LOCKS)).encode()


def wrapped():
    return ("e2fsprogs: " + VERSION + "\n" +
            "".join(Path(path).name + ": " + sha + "\n" for sha, path in LOCKS)).encode()


class Identity(unittest.TestCase):
    def test_native(self):
        self.assertTrue(ROW["identity_holds"](native()))

    def test_wrapper(self):
        self.assertTrue(ROW["identity_holds"](wrapped()))

    def test_version_required(self):
        self.assertFalse(ROW["identity_holds"](native().split(b"\n", 1)[1]))

    def test_wrong_version(self):
        self.assertFalse(ROW["identity_holds"](wrapped().replace(VERSION.encode(), b"1.47.1")))

    def test_each_digest_required(self):
        for sha, _path in LOCKS:
            with self.subTest(sha=sha):
                self.assertFalse(ROW["identity_holds"](native().replace(sha.encode(), b"0" * 64)))
                self.assertFalse(ROW["identity_holds"](wrapped().replace(sha.encode(), b"0" * 64)))

    def test_each_program_required(self):
        for _sha, path in LOCKS:
            with self.subTest(path=path):
                self.assertFalse(ROW["identity_holds"](native().replace(path.encode(), b"/other/program")))

    def test_unanchored_claim_rejected(self):
        self.assertFalse(ROW["identity_holds"](b"warning: " + native()))

    def test_empty(self):
        self.assertFalse(ROW["identity_holds"](b""))


if __name__ == "__main__":
    result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Identity))
    print(("PASS" if result.wasSuccessful() else "FAIL") + " EO-identity-selftest", flush=True)
    raise SystemExit(0 if result.wasSuccessful() else 1)
