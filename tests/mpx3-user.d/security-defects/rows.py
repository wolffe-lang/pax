#!/usr/bin/env python3
"""Isolated syscall-boundary witnesses, promoted from px146's W rows.

Each group gets its own boot. A kernel halt, missing answer, wrong errno,
wrong child status, or missing positive control is a named failure. Existing
suites call this runner with their selected tiers and firmware legs.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GROUPS = {"socket": ("udp",), "credentials": ("setid",), "signals": ("3", "4", "5", "6", "0")}
ROWS = {"socket": ("W1",), "credentials": ("W2", "traced-exec-setid", "attach-after-setid"),
        "signals": ("W3", "W4", "W5", "W6")}


def evaluate(group, text):
    """Return exact row verdicts; no missing or malformed result is a pass."""
    clean = "PANIC" not in text and "security: setup failed" not in text
    if group == "socket":
        got = re.findall(r"^security: W1 (recvfrom|recvmsg) cap (\d+) result (-?\d+) length (\d+) bounded ([01])$", text, re.M)
        expected = [(call, str(cap), "4", "16", "1")
                    for call in ("recvfrom", "recvmsg") for cap in (0, 1, 8, 16)]
        return {"W1": clean and got == expected}
    if group == "credentials":
        ids = re.findall(r"^security: W2 ids mode ([0-3]) uid (\d+) euid (\d+) gid (\d+) egid (\d+) nnp ([01])$", text, re.M)
        expected = [(str(mode), "1000", "0" if mode == 0 else "1000", "1000",
                     "42" if mode == 0 else "1000", str(int(bool(mode & 2)))) for mode in range(4)]
        stops = re.findall(r"^security: W2 trace mode ([0-3]) stop (\d+) continue (-?\d+)$", text, re.M)
        exits = re.findall(r"^security: W2 exit mode ([0-3]) status (\d+)$", text, re.M)
        traced = clean and ids == expected and stops == [("1", "1407", "0"), ("3", "1407", "0")] and exits == [(str(m), "0") for m in range(4)]
        attach = clean and re.findall(r"^security: attach-after-setid result (-?\d+)$", text, re.M) == ["-1"]
        return {"W2": traced, "traced-exec-setid": traced, "attach-after-setid": attach}
    if group == "signals":
        statuses = re.findall(r"^security: W([0-6]) child status (\d+)$", text, re.M)
        control = statuses.count(("0", "0")) == 1
        allowed = {"3": ("11", "139"), "4": ("11", "139", "5632"),
                   "5": ("5632",), "6": ("11", "139", "5632")}
        return {"W" + mode: clean and control and len([s for m, s in statuses if m == mode]) == 1
                and next((s for m, s in statuses if m == mode), "") in expected
                for mode, expected in allowed.items()}
    raise ValueError(group)


def command(argv):
    r = subprocess.run([str(a) for a in argv], stdout=subprocess.PIPE)
    if r.returncode:
        raise RuntimeError(f"{Path(argv[0]).name} exited {r.returncode}")
    return r.stdout.decode().strip()


def boot(work, elf, binary, group, mode, firmware):
    d = work / group / mode / firmware
    d.mkdir(parents=True, exist_ok=True)
    (d / "pax-run").write_text(f"/bin/wit {mode}\n")
    archive = d / "w.cpio"
    command([ROOT / "tools/mkinitramfs", archive, "/dev/", "/proc/", "/sys/",
             f"/bin/wit={binary}", f"/bin/euid={binary}:6755:0:42",
             f"/etc/pax-run={d / 'pax-run'}"])
    conf = d / "w.conf"
    conf.write_text("timeout: 0\nquiet: yes\n\n/PAX\n    protocol: limine\n"
                    "    path: boot():/boot/pax\n    module_path: boot():/boot/initramfs.cpio\n"
                    "    cmdline: nonet pax.nobeep pax.nomarks\n")
    iso = d / "w.iso"
    command([ROOT / "tools/mkimage", "--conf", conf, "--add", archive,
             "initramfs.cpio", elf, iso])
    log = d / "serial.log"
    kvm = os.access("/dev/kvm", os.R_OK | os.W_OK)
    if os.environ.get("PAX_REQUIRE_KVM") == "1" and not kvm:
        raise RuntimeError("KVM required but unavailable")
    if not kvm:
        print("SKIP security-kvm reason=no-usable-kvm; running TCG", flush=True)
    with (d / "qemu.log").open("w") as output:
        r = subprocess.run([str(x) for x in [ROOT / "tools/qemu-halt", "--firmware", firmware,
            "--accel", "kvm" if kvm else "tcg", "--serial", log, "--timeout", "300", "--no-screen",
            "--elf", elf, "--marker", "halt|PANIC .*", "--qemu", "-m", "--qemu", "512M",
            "--qemu", "-cpu", "--qemu", "host" if kvm else "max", iso]],
            stdout=output, stderr=subprocess.STDOUT)
    text = log.read_bytes().decode("latin-1").replace("\r", "") if log.exists() else ""
    for line in text.splitlines():
        if line.startswith(("security:", "PANIC")) or "killed:" in line:
            print("  " + line, flush=True)
    ended = bool(re.search(r"^user: wit pid \d+ (?:exit_group|exit) 0 after ", text, re.M))
    print(f"  {group}/{mode}/{firmware}: qemu-halt={r.returncode}, witness-exit-zero={ended}", flush=True)
    return text, r.returncode == 0 and ended


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", choices=["all", *GROUPS], default="all")
    parser.add_argument("--tiers", nargs="+", choices=["native", "release"], default=["native", "release"])
    parser.add_argument("--firmwares", nargs="+", choices=["bios", "uefi"], default=["bios", "uefi"])
    args = parser.parse_args()
    groups = list(GROUPS) if args.rows == "all" else [args.rows]
    base = Path(os.environ.get("PAX_BUILD", ROOT / "build")) / "security-defects" / args.rows
    bad = False
    command([ROOT / "tools/fetch-limine"])
    for tier in args.tiers:
        work = base / tier
        work.mkdir(parents=True, exist_ok=True)
        print(f"security: build {tier} console kernel", flush=True)
        try:
            elf = command([ROOT / "tools/build-kernel", *(["--release"] if tier == "release" else []),
                           "--src", ROOT / "kernel/kmain_console.lu", work / "kernel"])
        except RuntimeError as error:
            for group in groups:
                for row in ROWS[group]:
                    print(f"FAIL {row} {tier}: {error}", flush=True)
            bad = True
            continue
        for group in groups:
            binary = work / group / "wit"
            binary.parent.mkdir(parents=True, exist_ok=True)
            command(["cc", "-static", "-nostdlib", "-ffreestanding", "-fno-pie", "-no-pie",
                     "-fno-stack-protector", "-O1", "-Wall", "-Wextra", "-Wno-unused-function",
                     "-o", binary, HERE / f"{group}.c"])
            for firmware in args.firmwares:
                if firmware == "uefi":
                    ovmf = subprocess.run(["bash", "-c", '. "$1/tools/lib.sh"; find_ovmf >/dev/null', "bash", str(ROOT)])
                    if ovmf.returncode:
                        required = os.environ.get("PAX_REQUIRE_UEFI") == "1"
                        for row in ROWS[group]:
                            print(f"{'FAIL' if required else 'SKIP'} {row} reason=no-ovmf ({tier} uefi)", flush=True)
                        bad |= required
                        continue
                text, boot_ok = "", True
                for mode in GROUPS[group]:
                    try:
                        part, ok = boot(work, elf, binary, group, mode, firmware)
                        text += part + "\n"
                        boot_ok &= ok
                    except RuntimeError as error:
                        print(f"  {group}/{mode}: {error}", flush=True)
                        boot_ok = False
                for row, ok in evaluate(group, text).items():
                    ok &= boot_ok
                    print(f"{'PASS' if ok else 'FAIL'} {row} {tier} {firmware} {group}", flush=True)
                    bad |= not ok
    if args.rows in ("all", "signals"):
        helpers = subprocess.run([sys.executable, "-I", str(HERE / "helper_rows.py"),
                                  "--tiers", *args.tiers, "--firmwares", *args.firmwares])
        bad |= helpers.returncode != 0
    return int(bad)


if __name__ == "__main__":
    sys.exit(main())
