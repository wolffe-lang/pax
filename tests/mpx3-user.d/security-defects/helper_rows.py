#!/usr/bin/env python3
"""Direct user-copy helper contract. Missing error-return APIs fail by name;
when present, boot calls each helper on private test mappings and bad ranges.
The API check prevents the old, unchecked helpers from touching an unmapped
or kernel-half address during the negative tests.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[3]
ROWS = ["UACCESS-positive", *[f"UACCESS-{name}-refusal" for name in ("put", "zero", "get", "get64")]]

def checked_api(text):
    return all(re.search(r"pub fn " + name + r"\([^\n]*\) -> u64 ! \{fault\}", text)
               for name in ("put", "zero", "get", "get64"))

def evaluate(text):
    # OVMF can leave cursor-position controls adjacent to the first verdict.
    # Remove CSI only; unrelated prefixes and malformed controls still fail
    # the exact-line match, and normalized FAIL/PANIC remain fatal.
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    return "PANIC" not in text and "FAIL " not in text and all(text.splitlines().count("PASS " + row) == 1 for row in ROWS)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tiers", nargs="+", default=["native", "release"])
    p.add_argument("--firmwares", nargs="+", default=["bios", "uefi"])
    args = p.parse_args()
    if not checked_api((ROOT / "kernel/uaccess/uaccess.lu").read_text()):
        for row in ROWS[1:]: print(f"FAIL {row} missing-fallible-helper-api", flush=True)
        return 1
    def command(argv):
        return subprocess.check_output([str(x) for x in argv]).decode().strip()
    bad = False
    command([ROOT / "tools/fetch-limine"])
    for tier in args.tiers:
        work = Path(os.environ.get("PAX_BUILD", ROOT / "build")) / "uaccess-refusal" / tier
        work.mkdir(parents=True, exist_ok=True)
        try:
            elf = command([ROOT / "tools/build-kernel", *(["--release"] if tier == "release" else []),
                           "--src", ROOT / "kernel/kmain_uaccess.lu", work / "kernel"])
            iso = work / "test.iso"
            command([ROOT / "tools/mkimage", elf, iso])
            for firmware in args.firmwares:
                kvm = os.access("/dev/kvm", os.R_OK | os.W_OK)
                if not kvm and os.environ.get("PAX_REQUIRE_KVM") == "1": raise RuntimeError("KVM required")
                if not kvm: print("SKIP helper-kvm reason=no-usable-kvm; running TCG", flush=True)
                log = work / f"{firmware}.serial"
                r = subprocess.run([str(x) for x in [ROOT / "tools/qemu-halt", "--firmware", firmware,
                    "--accel", "kvm" if kvm else "tcg", "--serial", log, "--timeout", "60", "--no-screen", "--elf", elf,
                    "--marker", "halt|PANIC .*", "--qemu", "-cpu", "--qemu", "host" if kvm else "max", iso]],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (work / f"{firmware}.qemu-halt.stdout").write_bytes(r.stdout)
                (work / f"{firmware}.qemu-halt.stderr").write_bytes(r.stderr)
                if r.returncode:
                    for stream in (r.stdout, r.stderr):
                        for line in stream.decode(errors="replace").splitlines():
                            print("  qemu-halt: " + line, flush=True)
                text = log.read_bytes().decode("latin-1").replace("\r", "") if log.exists() else ""
                for line in text.splitlines(): print("  " + line, flush=True)
                ok = r.returncode == 0 and evaluate(text)
                for row in ROWS: print(f"{'PASS' if ok else 'FAIL'} {row} {tier} {firmware}", flush=True)
                bad |= not ok
        except (subprocess.CalledProcessError, RuntimeError) as e:
            for row in ROWS: print(f"FAIL {row} {tier} {e}", flush=True)
            bad = True
    return int(bad)

if __name__ == "__main__": sys.exit(main())
