#!/usr/bin/env python3
"""Keep the random report and the two log settings in separate proc slots."""
import re
import sys
from pathlib import Path


def check(text):
    constants = dict((name, int(value)) for name, value in re.findall(
        r"^(?:pub )?const (\w+): u64 = (\d+)\b", text, re.M))
    errors = []
    for names in (("PAXRAND", "DMESG_RESTRICT", "PRINTK"),
                  ("G_PAXRAND", "G_DMESG", "G_PRINTK")):
        values = [constants.get(name) for name in names]
        if None in values or len(set(values)) != len(names):
            errors.append("colliding or missing " + ", ".join(names))
    entries = constants.get("ENTRIES", -1)
    if entries <= max(constants.get(name, entries) for name in
                      ("PAXRAND", "DMESG_RESTRICT", "PRINTK")):
        errors.append("ENTRIES does not include every entry")
    if constants.get("NONE") != entries:
        errors.append("NONE differs from ENTRIES")
    return errors


def selftest():
    good = "\n".join("const %s: u64 = %d" % pair for pair in (
        ("PAXRAND", 59), ("DMESG_RESTRICT", 60), ("PRINTK", 61),
        ("ENTRIES", 62), ("NONE", 62), ("G_PAXRAND", 31),
        ("G_DMESG", 32), ("G_PRINTK", 33)))
    assert not check(good)
    for old, new in (("DMESG_RESTRICT: u64 = 60", "DMESG_RESTRICT: u64 = 59"),
                     ("G_DMESG: u64 = 32", "G_DMESG: u64 = 31"),
                     ("ENTRIES: u64 = 62", "ENTRIES: u64 = 61"),
                     ("NONE: u64 = 62", "NONE: u64 = 60"),
                     ("G_PRINTK: u64 = 33", "G_PRINTK_missing: u64 = 33")):
        assert check(good.replace(old, new)), (old, new)
    print("PASS M4-selftest: valid slots and five invalid maps")


def main():
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        return 0
    if len(sys.argv) != 2:
        print("usage: proc-slots.py PROCFS.lu | --selftest", file=sys.stderr)
        return 2
    errors = check(Path(sys.argv[1]).read_text())
    for error in errors:
        print("FAIL M4: " + error)
    if not errors:
        print("PASS M4: three distinct entries and generators, sentinel past all three")
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
