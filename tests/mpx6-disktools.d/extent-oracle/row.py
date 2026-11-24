#!/usr/bin/env python3
"""Check existing paxext2 --extents output with two pinned black-box e2fsprogs readers.

This is a host/container row, not a kernel boot. Run only on the pool, with a
fresh work directory on its second disk and a formatter built from the recorded
unchanged baseline. No recorded oracle fallback and no repair of the good image.
The script is intentionally independent of the existing E4 rows and their goldens.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

BASE = "d87560427ce449ae076b54adbcbc45dfa1c8e1fb"
POOL = Path("/mnt/lanes2/px172")
EPOCH = "1700000000"


class Failure(Exception):
    pass


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition, why):
    if not condition:
        raise Failure(why)


def pool_path(value):
    path = Path(value).resolve()
    if path == POOL or POOL not in path.parents:
        raise argparse.ArgumentTypeError("all row trees and formatter inputs must be below /mnt/lanes2/px172")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", required=True, type=pool_path)
    parser.add_argument("--paxext2", required=True, type=pool_path)
    parser.add_argument("--paxext2-sha256", required=True)
    parser.add_argument("--formatter-head", required=True, choices=[BASE])
    parser.add_argument("--engine", required=True)
    parser.add_argument("--image", required=True, help="immutable local image ID, sha256:<64hex>")
    parser.add_argument("--dry", action="store_true", help="one real six-run depth-1 image/read/control, not a mock")
    args = parser.parse_args()
    if sys.platform != "linux":
        print("REFUSED oracle-row requires the Linux pool", flush=True)
        return 75
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", args.image):
        print("REFUSED oracle-image requires an immutable image ID", flush=True)
        return 75
    if not re.fullmatch(r"[0-9a-f]{64}", args.paxext2_sha256):
        print("REFUSED formatter-digest", flush=True)
        return 75
    if not args.paxext2.is_file() or digest(args.paxext2) != args.paxext2_sha256:
        print("REFUSED formatter-input digest or file mismatch", flush=True)
        return 75
    if args.work.exists():
        print("REFUSED work-directory must be fresh", flush=True)
        return 75
    args.work.mkdir(parents=True)
    work = args.work
    (work / "tmp").mkdir()
    (work / "home").mkdir()
    env = dict(os.environ, SOURCE_DATE_EPOCH=EPOCH, E2FSPROGS_FAKE_TIME=EPOCH,
               TMPDIR=str(work / "tmp"), HOME=str(work / "home"), SHELL="/bin/sh")
    row = "ORACLE-PIN"
    count = 0

    def run(argv, tag, limit=180):
        result = subprocess.run([str(x) for x in argv], env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=limit)
        (work / (tag + ".log")).write_bytes(result.stdout)
        return result

    def oracle(tag, *command):
        return run([args.engine, "run", "--rm", "--network", "none", "--read-only",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                    "--memory", "512m", "--memory-swap", "512m", "--pids-limit", "64",
                    "-e", "HOME=/work/home", "-e", "TMPDIR=/work/tmp", "-e", "SHELL=/bin/sh",
                    "-e", "E2FSPROGS_FAKE_TIME=" + EPOCH, "-e", "SOURCE_DATE_EPOCH=" + EPOCH,
                    "-v", str(work) + ":/work", "-w", "/work", args.image, *command], tag)

    def passed(name, text):
        nonlocal count
        count += 1
        print(f"PASS {name} {text}", flush=True)

    def stat(name, target):
        result = oracle("stat-" + name, "debugfs", "-R", "stat " + target, "/work/extent.img")
        text = result.stdout.decode(errors="replace")
        ino = re.search(r"\bInode:\s*(\d+)", text)
        flags = re.search(r"\bFlags:\s*(0x[0-9a-fA-F]+)", text)
        require(result.returncode == 0 and ino and flags, "debugfs stat did not name inode/flags: " + name)
        require(int(flags[1], 16) & 0x80000, "debugfs found no EXTENTS_FL: " + name)
        return int(ino[1])

    def inode_offset(number):
        with image.open("rb") as stream:
            stream.seek(1024)
            sb = stream.read(1024)
            word = lambda offset, width=4: int.from_bytes(sb[offset:offset + width], "little")
            require(word(24) == 2 and word(88, 2) == 256, "unexpected baseline geometry")
            ipg = word(40)
            require(ipg > 0, "zero inodes per group")
            group, index = divmod(number - 1, ipg)
            stream.seek(4096 + group * 32 + 8)
            table = int.from_bytes(stream.read(4), "little")
            at = table * 4096 + index * 256
            require(0 < at and at + 256 <= image.stat().st_size, "inode location outside image")
            return at

    try:
        identity = oracle("oracle-identity", "--identity")
        if identity.returncode != 0 or b"e2fsprogs=1.47.0-2.4~exp1ubuntu4.1" not in identity.stdout:
            print("REFUSED oracle-identity; formatter not run; see oracle-identity.log", flush=True)
            return 75
        passed(row, args.image + " e2fsprogs=1.47.0-2.4~exp1ubuntu4.1")
        tree = work / "source"
        tree.mkdir()
        patterns = {"six": (6, 1)}
        if not args.dry:
            patterns["many"] = (1500, 2)
            (tree / "empty").write_bytes(b"")
            (tree / "small").write_bytes(b"existing paxext2 extent output\n")
            with (tree / "long").open("wb") as stream:
                for n in range(2049):
                    stream.write(bytes([n % 251 + 1]) * 4096)
        for name, (runs, _depth) in patterns.items():
            with (tree / name).open("wb") as stream:
                stream.truncate((runs * 2 - 1) * 4096)
                for n in range(runs):
                    stream.seek(n * 8192)
                    stream.write(bytes([n % 251 + 1]) * 4096)
        expected = {path.name: {"bytes": path.stat().st_size, "sha256": digest(path)}
                    for path in sorted(tree.iterdir())}
        (work / "inputs.json").write_text(json.dumps({"formatter_head": args.formatter_head,
            "formatter_sha256": args.paxext2_sha256, "oracle_image": args.image,
            "fixtures": expected}, indent=2) + "\n")
        row = "EO-format"
        image = work / "extent.img"
        made = run([args.paxext2, "--from", tree, "--label", "extent-oracle", "--seed", "extent-oracle",
                    "--journal", "4096", "--extents", "96M", image], "paxext2")
        require(made.returncode == 0 and image.is_file(), "unchanged baseline formatter failed; see paxext2.log")
        before = digest(image)
        with image.open("rb") as stream:
            stream.seek(1024 + 92)
            features = [int.from_bytes(stream.read(4), "little") for _ in range(3)]
        require(features == [4, 0x42, 3], "profile words are not has_journal/filetype+extent/sparse_super+large_file")
        passed(row, f"formatter_head={BASE} image_sha256={before} features=4,66,3")
        row = "EO-fsck"
        check = oracle("e2fsck-good", "e2fsck", "-fn", "/work/extent.img")
        require(check.returncode == 0 and b"WARNING" not in check.stdout,
                f"baseline e2fsck -fn exit={check.returncode}; see e2fsck-good.log")
        passed(row, "e2fsck -fn exit=0")
        row = "EO-journal"
        require(stat("journal", "<8>") == 8, "journal inode is not 8")
        ex = oracle("journal-extents", "debugfs", "-R", "ex <8>", "/work/extent.img")
        require(ex.returncode == 0 and re.search(rb"\b4095\b", ex.stdout),
                "debugfs ex did not show the 4096-block journal")
        passed(row, "debugfs stat/ex inode=8 EXTENTS_FL set, logical end=4095")
        for name, want in expected.items():
            row = "EO-read-" + name
            ino = stat(name, "/" + name)
            out = work / (name + ".dump")
            dump = oracle("dump-" + name, "debugfs", "-R", f"dump /{name} /work/{name}.dump", "/work/extent.img")
            require(dump.returncode == 0 and out.is_file() and out.stat().st_size == want["bytes"]
                    and digest(out) == want["sha256"], "debugfs dump differs from source: " + name)
            passed(row, f"bytes={want['bytes']} sha256={want['sha256']}")
            if name in patterns:
                row = "EO-depth-" + name
                with image.open("rb") as stream:
                    stream.seek(inode_offset(ino) + 40)
                    header = stream.read(12)
                depth = int.from_bytes(header[6:8], "little")
                require(header[:2] == b"\x0a\xf3" and depth == patterns[name][1],
                        f"fixture depth={depth}, expected={patterns[name][1]}")
                ex = oracle("extents-" + name, "debugfs", "-R", "ex /" + name, "/work/extent.img")
                require(ex.returncode == 0 and b"Logical" in ex.stdout, "debugfs ex did not print its extent table")
                passed(row, f"depth={depth}; debugfs dumped all {patterns[name][0]} data runs and holes")
        row = "EO-unchanged"
        require(digest(image) == before, "read-only oracle commands changed the image")
        passed(row, "good image SHA-256 unchanged")
        row = "EO-negative-control"
        broken = work / "bad-magic.img"
        shutil.copyfile(image, broken)
        ino = stat("negative-six", "/six")
        with broken.open("r+b") as stream:
            stream.seek(inode_offset(ino) + 40)
            stream.write(b"\x34\x12")
        bad_before = digest(broken)
        bad = oracle("e2fsck-bad-magic", "e2fsck", "-fn", "/work/bad-magic.img")
        require(bad.returncode == 4 and b"extent" in bad.stdout.lower()
                and str(ino).encode() in bad.stdout and digest(broken) == bad_before,
                f"negative control not detected unchanged (exit={bad.returncode}); see e2fsck-bad-magic.log")
        passed(row, f"copy only: inode={ino} bad extent magic; e2fsck exit=4; neither image repaired")
        require(digest(image) == before, "control changed the good image")
        print(f"ORACLE-END baseline={BASE} rows={count} exit=0", flush=True)
        return 0
    except (Failure, OSError, subprocess.TimeoutExpired) as error:
        print(f"FAIL {row} {error}", flush=True)
        print(f"ORACLE-END baseline={BASE} exit=1; preserve {work}; report before further work", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
