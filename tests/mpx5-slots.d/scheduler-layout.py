#!/usr/bin/env python3
"""Check scheduler scalar/bitmap storage when the thread table grows."""
import re
import sys
from pathlib import Path


def check(source, assembly):
    values = {k: int(v) for k, v in re.findall(
        r"^(?:pub )?const (\w+): u64 = (\d+)\b", source, re.M)}
    errors = []
    scalars = [v for k, v in values.items() if k.startswith("S_")]
    if len(scalars) != len(set(scalars)) or any(v >= 32 for v in scalars):
        errors.append("scheduler scalars alias or exceed their 32-word reservation")
    words = values.get("BITMAP_WORDS", 0)
    if words * 64 < values.get("SLOTS", 1):
        errors.append("scheduler bitmap does not cover every slot")
    if values.get("B_URGENT") != 0 or values.get("B_QUEUED") != words or words == 0:
        errors.append("urgent and queued bitmap ranges overlap or are missing")
    match = re.search(r"^pax_sched_bits:\s*\n\s*\.zero ([0-9 *]+)$", assembly, re.M)
    reserved = 0
    if match:
        reserved = 1
        for factor in match[1].replace(" ", "").split("*"):
            reserved *= int(factor)
    if reserved < words * 2 * 8 or reserved == 0:
        errors.append("assembly does not reserve both complete bitmaps")
    if "s / 64" not in source or "s % 64" not in source:
        errors.append("slot bitmap access is not split into word and bit")
    if re.search(r"1 << (?:s|from|c)\b|1 << \(h - 1\)", source):
        errors.append("a slot is shifted directly into one word")
    if source.count("clear_masks()") < 2:
        errors.append("bitmap reset is missing from scheduler start")
    # px166 (step 5b): every slot word inside its slot's share of pax_slot_words, none aliased
    per = values.get("SLOT_WORDS", 0)
    slot_words = [int(v) for v in re.findall(r"^const W_\w+: u64 = (\d+) // [^\n]*slot word", source, re.M)]
    if not slot_words or len(slot_words) != len(set(slot_words)) or any(w >= per for w in slot_words):
        errors.append("slot words alias or reach past SLOT_WORDS")
    match = re.search(r"^pax_slot_words:\s*\n\s*\.zero ([0-9 *]+)$", assembly, re.M)
    reserved = 0
    if match:
        reserved = 1
        for factor in match[1].replace(" ", "").split("*"):
            reserved *= int(factor)
    if reserved < values.get("SLOTS", 1) * per * 8 or reserved == 0:
        errors.append("assembly does not reserve SLOT_WORDS words for every slot")
    return errors


def main():
    args = sys.argv[1:]
    selftest = args[:1] == ["--selftest"]
    if selftest:
        args = args[1:]
    if len(args) != 2:
        return 2
    source, assembly = (Path(p).read_text() for p in args)
    errors = check(source, assembly)
    if selftest and not errors:
        variants = [(source.replace("const S_TOP: u64 = 28", "const S_TOP: u64 = 25"), assembly),
                    (source.replace("const BITMAP_WORDS: u64 = 16", "const BITMAP_WORDS: u64 = 1"), assembly),
                    (source.replace("const B_QUEUED: u64 = 16", "const B_QUEUED: u64 = 0"), assembly),
                    (source, assembly.replace(".zero 2 * 16 * 8", ".zero 16 * 8")),
                    (source + "\nfn invalid() { let x = 1 << s }\n", assembly),
                    (source.replace("const SLOT_WORDS: u64 = 5", "const SLOT_WORDS: u64 = 4"), assembly),
                    (source, assembly.replace(".zero 1024 * 5 * 8", ".zero 1024 * 4 * 8"))]
        assert all(check(s, a) for s, a in variants), "a broken layout was accepted"
        print("PASS slots-scheduler-layout-selftest: seven invalid layouts rejected")
    for error in errors:
        print("FAIL slots-scheduler-layout: " + error)
    if not errors:
        print("PASS slots-scheduler-layout: distinct scalars and full-width slot bitmaps")
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
