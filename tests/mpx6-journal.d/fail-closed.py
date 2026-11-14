#!/usr/bin/env python3
"""QEMU failure rows; filesystem oracles use unmounted image files.

By default tools/e2fs supplies the pinned oracle container. A runner already
inside a pinned toolchain image may set PAX_E2FS_NATIVE=1; its recorder must
identify that image. The oracle version is saved alongside the image facts.
"""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import signal
import struct
import subprocess
import time


def process(argv, **kw):
    argv = list(map(str, argv))
    if argv[0] in ("mke2fs", "debugfs", "dumpe2fs", "e2fsck") and os.environ.get("PAX_E2FS_NATIVE") != "1":
        root = Path(__file__).resolve().parents[2]
        argv = [str(root / "tools/e2fs"), str(Path(argv[-1]).resolve().parent), *argv]
    return subprocess.run(argv, **kw)


def run(argv, **kw):
    r = process(argv, capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError(f"command failed ({r.returncode}): {argv}\n{r.stdout}\n{r.stderr}")
    return r.stdout + r.stderr


def sha(path, limit=None):
    h = hashlib.sha256()
    with path.open("rb") as f:
        left = path.stat().st_size if limit is None else limit
        while left:
            b = f.read(min(left, 1024 * 1024))
            if not b:
                raise RuntimeError("short hash input")
            h.update(b)
            left -= len(b)
    return h.hexdigest()


def at(path, off, count):
    with path.open("rb") as f:
        f.seek(off)
        b = f.read(count)
    if len(b) != count:
        raise RuntimeError("short image read")
    return b


def put(path, off, data):
    with path.open("r+b") as f:
        f.seek(off)
        f.write(data)


def geometry(path):
    sb = at(path, 1024, 1024)
    bs = 1024 << struct.unpack_from("<I", sb, 24)[0]
    if bs != 4096:
        raise RuntimeError("fixture block size")
    bb, _, table = struct.unpack_from("<III", at(path, bs, 32))
    isize = struct.unpack_from("<H", sb, 88)[0]
    ino = at(path, table * bs + 7 * isize, isize)
    journal = struct.unpack_from("<I", ino, 40)[0]
    return bb, journal


def file_blocks(path, name):
    """The direct block numbers of a root-directory file in the 4 KiB fixture."""
    sb = at(path, 1024, 1024)
    per_group = struct.unpack_from("<I", sb, 40)[0]
    isize = struct.unpack_from("<H", sb, 88)[0]

    def inode(number):
        group, index = divmod(number - 1, per_group)
        table = struct.unpack_from("<I", at(path, 4096 + group * 32, 32), 8)[0]
        return at(path, table * 4096 + index * isize, isize)

    directory = at(path, struct.unpack_from("<I", inode(2), 40)[0] * 4096, 4096)
    offset = 0
    while offset < 4096:
        number, length, size = struct.unpack_from("<IHB", directory, offset)
        if length == 0:
            break
        if number and directory[offset + 8:offset + 8 + size] == name:
            return [b for b in struct.unpack_from("<12I", inode(number), 40) if b]
        offset += length
    raise RuntimeError("fixture file not found: " + name.decode())


def value(text, name):
    m = re.search(r"^JF " + re.escape(name) + r" rc=(-?\d+) errno=(\d+)$", text, re.M)
    return tuple(map(int, m.groups())) if m else None


def flush_error_rule(target):
    if target < 1:
        raise RuntimeError("a flush fault needs a measured backing-flush ordinal")
    stages = []
    for state in range(1, target):
        stages.append('[set-state]\nevent = "flush_to_disk"\n'
                      f'state = "{state}"\nnew_state = "{state + 1}"\n')
    stages.append('[inject-error]\nevent = "flush_to_disk"\niotype = "flush"\n'
                  f'state = "{target}"\nerrno = "5"\nonce = "on"\nimmediately = "off"\n')
    return "\n".join(stages)


def write_error_rule(target, sector):
    if target < 1:
        raise RuntimeError("a write fault needs a measured write ordinal")
    stages = []
    for state in range(1, target):
        stages.append('[set-state]\nevent = "write_aio"\n'
                      f'state = "{state}"\nnew_state = "{state + 1}"\n')
    stages.append('[inject-error]\nevent = "write_aio"\niotype = "write"\n'
                  f'state = "{target}"\nsector = "{sector}"\nerrno = "5"\nonce = "on"\nimmediately = "off"\n')
    return "\n".join(stages)


class Rows:
    def __init__(self, args):
        self.a = args
        self.root = Path(__file__).resolve().parents[2]
        self.out = args.out.resolve()
        self.out.mkdir(parents=True, exist_ok=False)
        self.failed = 0
        self.probe = self.out / "probe"
        run(["cc", "-static", "-O2", "-Wall", "-Wextra", "-Werror",
             self.root / "tests/mpx6-journal.d/fail-closed.c", "-o", self.probe])
        self.base = self.out / "base.img"
        with self.base.open("wb") as f:
            f.truncate(64 * 1024 * 1024)
        seed = self.out / "seed"
        seed.mkdir()
        (seed / "pressure").write_bytes(b"P" * (16 * 1024 * 1024))
        (seed / "old").write_bytes(b"A" * 4096)
        (seed / "two").write_bytes(b"A" * 8192)
        run(["mke2fs", "-q", "-F", "-t", "ext3", "-b", "4096", "-J", "size=16", "-d", seed, self.base])
        (self.out / "oracle-versions.txt").write_text(run(["dumpe2fs", "-h", self.base]))

    def row(self, name, ok, why):
        print(("PASS " if ok else "FAIL ") + name + " " + why, flush=True)
        if not ok:
            self.failed += 1

    def requests(self, name):
        pending, events = {}, []
        rw = re.compile(r"virtio_blk_handle_(write|read) vdev \S+ req (0x[0-9a-f]+) sector (\d+) nsectors (\d+)")
        complete = re.compile(r"virtio_blk_req_complete vdev \S+ req (0x[0-9a-f]+) status (\d+)")
        for line in (self.out / name / "requests.log").read_text().splitlines():
            m = rw.search(line)
            if m:
                pending[m[2]] = (m[1], int(m[3]), int(m[4]))
                continue
            m = complete.search(line)
            if m:
                # This kernel submits only read, write and flush requests,
                # one at a time. Only flush lacks a read/write handle event.
                kind, sector, count = pending.pop(m[1], ("flush", 0, 0))
                events.append((kind, sector, count, int(m[2])))
        if pending or not any(e[0] == "read" for e in events):
            raise RuntimeError("incomplete virtio request trace: " + name)
        return events

    def fault(self, name, disk, kind, sector, stage, sequence=1, descriptor=None, prior_sequence=None):
        events = self.requests(name)
        errors = [(i, e) for i, e in enumerate(events) if e[3] != 0]
        valid = len(errors) == 1
        detail = f"hits={len(errors)}"
        if valid:
            index, event = errors[0]
            detail += f" request={event[0]} sector={event[1]} status={event[3]}"
            valid = event[0] == kind and event[3] == 1 and (sector is None or event[1] == sector)
            _, journal = geometry(disk)
            commit_sectors = {(journal + j) * 8 for j in range(1, 64)
                              if at(disk, (journal + j) * 4096, 12) == struct.pack(">III", 0xC03B3998, 2, sequence)}
            before = events[:index]
            commits = [i for i, e in enumerate(before) if e[0] == "write" and e[1] in commit_sectors and e[3] == 0]
            descriptor_sector = (journal + (1 if descriptor is None else descriptor)) * 8
            descriptors = [i for i, e in enumerate(before) if e[0] == "write" and e[1] == descriptor_sector and e[3] == 0]
            if prior_sequence is not None:
                prior = {(journal + j) * 8 for j in range(1, 64)
                         if at(disk, (journal + j) * 4096, 12) == struct.pack(">III", 0xC03B3998, 2, prior_sequence)}
                preceding = [i for i, e in enumerate(before) if e[0] == "write" and e[1] in prior and e[3] == 0]
                durable = bool(preceding) and any(e[0] == "flush" and e[3] == 0 for e in before[preceding[-1] + 1:])
                detail += f" earlier-commit-durable={durable}"
                valid = valid and durable
            if stage == "pre-mount":
                valid = valid and any(e[0] == "write" and e[1] == 64 * 1024 * 1024 // 512 and e[3] == 0 for e in before)
                valid = valid and not any(e[0] == "write" and e[1] < 64 * 1024 * 1024 // 512 for e in before)
            elif stage in ("mount-state", "mount-write"):
                valid = valid and not descriptors and not commits
                if stage == "mount-state":
                    valid = valid and any(e[0] == "write" and e[1] == 0 and e[3] == 0 for e in before)
            elif stage in ("late-superblock", "late-final-barrier"):
                clears = [i for i, e in enumerate(before) if e[0] == "write" and e[1] == journal * 8 and e[3] == 0]
                superblocks = [i for i, e in enumerate(before) if e[0] == "write" and e[1] == 0 and e[3] == 0]
                closed = bool(clears) and any(e[0] == "flush" and e[3] == 0 for e in before[clears[-1] + 1:])
                valid = valid and closed and not descriptors and bool(superblocks)
                if stage == "late-final-barrier":
                    valid = valid and len(superblocks) >= 2 and clears[-1] < superblocks[-1]
                    valid = valid and bool(before) and before[-1][0:2] == ("write", 0)
                detail += f" journal-close-barrier={closed}"
            elif stage == "remount-rw-state":
                valid = valid and not any(e[0] == "write" for e in before)
                valid = valid and any(e[0] == "flush" and e[3] == 0 for e in before)
            elif stage == "data-overwrite":
                valid = valid and not descriptors and not commits
            elif stage == "precommit":
                valid = valid and bool(descriptors) and not commits
            elif stage in ("checkpoint", "cache-home"):
                valid = valid and bool(commits)
                if commits:
                    last = commits[-1]
                    valid = valid and not any(e[0] == "write" and e[1] == journal * 8 for e in before[last + 1:])
                    if kind == "flush":
                        valid = valid and any(e[0] == "write" and not journal * 8 <= e[1] < (journal + 64) * 8
                                              and e[3] == 0 for e in before[last + 1:])
                if stage == "cache-home":
                    retries = sum(e[0] == "write" and e[1] == event[1] and e[3] == 0 for e in events[index + 1:])
                    detail += f" successful-retries={retries}"
                    valid = valid and retries > 0
            elif stage != "descriptor":
                raise RuntimeError("unknown fault stage")
            if stage in ("late-superblock", "remount-rw-state") and kind == "write":
                # The call's own sync retried the failed superblock write successfully.
                retries = sum(e[0] == "write" and e[1] == event[1] and e[3] == 0 for e in events[index + 1:])
                detail += f" successful-retries={retries}"
                valid = valid and retries > 0
        detail += " stage=" + stage + " verified=" + str(bool(valid))
        (self.out / name / "fault.txt").write_text(detail + "\n")
        print("FAULT " + name + " " + detail, flush=True)
        return bool(valid)

    def boot(self, name, disk, case, cfg=None, extra=None):
        work = self.out / name
        work.mkdir()
        (work / "case").write_text(case)
        archive = work / "initramfs.cpio"
        run([self.root / "tools/mkinitramfs", archive, "/bin/", "/etc/", "/volume/",
             f"/bin/journal-failure={self.probe}:755", f"/case={work / 'case'}:644"])
        conf = work / "limine.conf"
        conf.write_text("timeout: 0\nquiet: yes\n/PAX\n    protocol: limine\n"
                        "    path: boot():/boot/pax\n"
                        "    cmdline: init=/bin/journal-failure\n"
                        "    module_path: boot():/boot/initramfs.cpio\n")
        iso = work / "boot.iso"
        run([self.root / "tools/mkimage", "--conf", conf, "--add", archive,
             "initramfs.cpio", self.a.kernel, iso])
        serial, pidfile = work / "serial.txt", work / "qemu.pid"
        cmd = [str(self.root / "tools/qemu-run"), "--firmware", self.a.firmware,
               "--serial", str(serial), "--timeout", "120", "--drive", str(disk),
               str(iso), "--", "-pidfile", str(pidfile), "-m", "512M",
               "-trace", "virtio_blk_handle_write", "-trace", "virtio_blk_handle_read",
               "-trace", "virtio_blk_req_complete", "-D", str(work / "requests.log")]
        if cfg:
            cmd += ["-set", f"drive.d0.file=blkdebug:{cfg}:{disk}"]
        if extra:
            cmd += extra
        with (work / "runner.txt").open("w") as output:
            p = subprocess.Popen(cmd, stdout=output, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 115
            text = ""
            try:
                while p.poll() is None and time.monotonic() < deadline:
                    text = serial.read_text(errors="replace").replace("\r", "") if serial.exists() else ""
                    if "JF DONE" in text:
                        break
                    time.sleep(0.05)
                if "JF DONE" not in text:
                    raise RuntimeError(f"guest did not reach DONE: {work}\n{text[-3000:]}")
            finally:
                if p.poll() is None and pidfile.exists():
                    qpid = int(pidfile.read_text())
                    # This pid belongs to this invocation's unique ISO, not a name search.
                    argv = Path(f"/proc/{qpid}/cmdline").read_bytes()
                    if str(iso).encode() not in argv:
                        raise RuntimeError("QEMU pid identity mismatch")
                    os.kill(qpid, signal.SIGKILL)
                p.wait(timeout=10)
        return text

    def image(self, name):
        p = self.out / (name + ".img")
        shutil.copyfile(self.base, p)
        return p

    def refusal(self, name, offset=None, data=None, extra=None, words="", filesystem=False):
        disk = self.image(name)
        _, journal = geometry(disk)
        if offset is not None:
            put(disk, (1024 if filesystem else journal * 4096) + offset, data)
        before = sha(disk)
        text = self.boot(name, disk, "refuse", extra=extra)
        mount = value(text, "mount")
        self.row(name, mount is not None and mount[0] == -1 and sha(disk) == before
                 and words in text, "named refusal before writes: " + words)

    def eio(self, name, mode, sector):
        disk = self.image(name)
        bb, journal = geometry(disk)
        cfg = self.out / (name + ".cfg")
        if sector.startswith("flush-"):
            target = int(sector.split("-", 1)[1])
            cfg.write_text(flush_error_rule(target))
        else:
            selected = (journal + 1) * 8 if sector == "log" else bb * 8
            cfg.write_text('[inject-error]\nevent = "write_aio"\niotype = "write"\n'
                           f'errno = "5"\nsector = "{selected}"\nonce = "on"\nimmediately = "off"\n')
        text = self.boot(name, disk, mode, cfg=cfg)
        kind = "flush" if sector.startswith("flush-") else "write"
        selected_sector = None if kind == "flush" else selected
        stage = "cache-home" if mode == "cache-error" else "checkpoint" if mode.startswith("checkpoint") else "precommit" if kind == "flush" else "descriptor"
        fault_ok = self.fault(name, disk, kind, selected_sector, stage)
        start = struct.unpack(">I", at(disk, journal * 4096 + 28, 4))[0]
        if mode in ("checkpoint", "checkpoint-barrier", "cache-error"):
            first_sync = mode == "checkpoint-barrier" or value(text, "fsync") == (0, 0)
            ok = fault_ok and first_sync and value(text, "unmount") == (-1, 5) and start != 0
            if mode == "cache-error":
                ok = ok and "JF pressure-bytes=16777216" in text and value(text, "fsync-after") == (-1, 5)
                later = value(text, "open-after")
                ok = ok and later is not None and later[0] == -1
            self.row(name, ok, "failed home write/barrier keeps recovery log and sticky failure")
            recovered = self.boot(name + "-recover", disk, "recover")
            check = process(["e2fsck", "-fn", str(disk)], capture_output=True, text=True)
            (self.out / (name + ".fsck.txt")).write_text(check.stdout + check.stderr)
            self.row(name + "-replay", value(recovered, "unmount") == (0, 0)
                     and "JF recovered-bytes=1" in recovered and check.returncode == 0,
                     "reboot replays full committed file and independent fsck is clean")
        else:
            after = [value(text, key) for key in ("write-after", "fsync-after", "open-after")]
            # Fresh fixture's journal blocks are contiguous through the first transaction.
            committed = any(at(disk, (journal + i) * 4096, 12) == struct.pack(">III", 0xC03B3998, 2, 1)
                            for i in range(1, 64))
            self.row(name, fault_ok and value(text, "fsync") == (-1, 5)
                     and all(v and v[0] == -1 for v in after) and not committed,
                     "write failure is sticky and publishes no commit")

    def no_flush(self):
        self.refusal("JF-no-flush", extra=["-global", "virtio-blk-pci.config-wce=off",
                     "-global", "virtio-blk-pci.write-cache=off"], words="flush")

    def mount_barrier(self):
        disk = self.image("mount-flush-EIO")
        length = disk.stat().st_size
        before = sha(disk)
        # Prime the backend with a raw write beyond the filesystem. Otherwise
        # QEMU can optimize an initial flush without calling blkdebug at all.
        with disk.open("r+b") as f:
            f.truncate(length + 4096)
        cfg = self.out / "mount-flush-EIO.cfg"
        cfg.write_text('[inject-error]\nevent = "flush_to_disk"\niotype = "flush"\nerrno = "5"\nonce = "on"\nimmediately = "off"\n')
        text = self.boot("mount-flush-EIO", disk, "pre-mount-barrier", cfg=cfg)
        fault_ok = self.fault("mount-flush-EIO", disk, "flush", None, "pre-mount")
        self.row("JF-mount-flush-EIO", fault_ok and value(text, "prime-write") == (4096, 0)
                 and value(text, "mount") == (-1, 5) and sha(disk, length) == before
                 and "flush barrier" in text,
                 "primed outside filesystem: failed barrier refuses mount before its first filesystem write")

    def mount_state(self, kind):
        name = "JF-mount-state-" + kind + "-EIO"
        disk = self.image(name)
        cfg = self.out / (name + ".cfg")
        if kind == "write":
            rule = 'event = "write_aio"\niotype = "write"\nsector = "0"\n'
            case = "mount-error"
        else:
            rule = 'event = "flush_to_disk"\niotype = "flush"\n'
            case = "mount-state-flush"
        cfg.write_text('[inject-error]\n' + rule + 'errno = "5"\nonce = "on"\nimmediately = "off"\n')
        text = self.boot(name, disk, case, cfg=cfg)
        stage = "mount-write" if kind == "write" else "mount-state"
        fault_ok = self.fault(name, disk, kind, 0 if kind == "write" else None, stage)
        self.row(name, fault_ok and value(text, "mount") == (-1, 5)
                 and value(text, "mount-after") == (-1, 16),
                 "a failed mounted-state write/barrier refuses mount and retains its device claim")

    def incomplete(self):
        control = self.image("prefix-control")
        text = self.boot("prefix-control", control, "prefix-control")
        _, journal = geometry(control)
        def positions(kind, sequence):
            return [j for j in range(1, 64) if at(control, (journal + j) * 4096, 12)
                    == struct.pack(">III", 0xC03B3998, kind, sequence)]
        descriptors, commits = positions(1, 2), positions(2, 2)
        events = self.requests("prefix-control")
        check = process(["e2fsck", "-fn", control], capture_output=True, text=True)
        (self.out / "prefix-control.fsck.txt").write_text(check.stdout + check.stderr)
        layout = (len(descriptors) == 1 and len(commits) == 1 and bool(positions(2, 1))
                  and value(text, "anchor-fsync") == (0, 0) and value(text, "fsync") == (0, 0)
                  and value(text, "unmount") == (0, 0) and check.returncode == 0
                  and all(e[3] == 0 for e in events))
        self.row("JF-prefix-control", layout,
                 "two healthy transactions define the measured descriptor and barrier positions")
        if not layout:
            raise RuntimeError("no measured two-transaction layout for incomplete-log rows")
        descriptor, commit = descriptors[0], commits[0]
        dindex = next(i for i, e in enumerate(events) if e[0] == "write" and e[1] == (journal + descriptor) * 8)
        cindex = next(i for i, e in enumerate(events) if e[0] == "write" and e[1] == (journal + commit) * 8)
        barriers = [i for i in range(dindex + 1, cindex) if events[i][0] == "flush"]
        if len(barriers) != 1:
            raise RuntimeError("the measured second transaction has no unique precommit barrier")
        backing, dirty = 0, False
        for event in events[:barriers[0] + 1]:
            if event[0] == "write":
                dirty = True
            elif event[0] == "flush":
                if dirty:
                    backing += 1
                dirty = False
        for kind in ("log", "flush"):
            name = "JF-incomplete-" + kind + "-EIO"
            disk = self.image(name)
            cfg = self.out / (name + ".cfg")
            sector = (journal + descriptor) * 8
            if kind == "log":
                cfg.write_text('[inject-error]\nevent = "write_aio"\niotype = "write"\n'
                               f'sector = "{sector}"\nerrno = "5"\nonce = "on"\nimmediately = "off"\n')
            else:
                cfg.write_text(flush_error_rule(backing))
            text = self.boot(name, disk, "prefix-failure", cfg=cfg)
            fault_ok = self.fault(name, disk, "write" if kind == "log" else "flush",
                                  sector if kind == "log" else None,
                                  "descriptor" if kind == "log" else "precommit",
                                  sequence=2, descriptor=descriptor, prior_sequence=1)
            published = any(at(disk, (journal + j) * 4096, 12) == struct.pack(">III", 0xC03B3998, 2, 2)
                            for j in range(1, 64))
            after = [value(text, key) for key in ("write-after", "fsync-after", "open-after")]
            self.row(name, fault_ok and value(text, "anchor-fsync") == (0, 0)
                     and value(text, "fsync") == (-1, 5) and not published
                     and all(v is not None and v[0] == -1 for v in after),
                     "a failed second transaction keeps the earlier committed transaction durable")
            recovered = self.boot(name + "-recover", disk, "prefix-recover")
            check = process(["e2fsck", "-fn", disk], capture_output=True, text=True)
            (self.out / (name + ".fsck.txt")).write_text(check.stdout + check.stderr)
            self.row(name + "-replay", fault_ok and "JF anchor-bytes=1" in recovered
                     and value(recovered, "uncommitted-open") == (-1, 2)
                     and value(recovered, "later-open") == (-1, 2)
                     and value(recovered, "unmount") == (0, 0) and check.returncode == 0,
                     "reboot replays only the earlier full transaction; incomplete names absent and fsck clean")

    def no_flush_boundaries(self):
        extra = ["-global", "virtio-blk-pci.config-wce=off", "-global", "virtio-blk-pci.write-cache=off"]
        disk = self.image("no-flush-ro")
        before = sha(disk)
        text = self.boot("no-flush-ro", disk, "ro-control", extra=extra)
        self.row("JF-no-flush-read-only", value(text, "mount") == (0, 0)
                 and "JF old-bytes=1" in text and value(text, "unmount") == (0, 0)
                 and sha(disk) == before and not any(e[0] == "write" for e in self.requests("no-flush-ro")),
                 "a clean journal can be read-only without a barrier, with no filesystem write")
        disk = self.image("no-flush-remount")
        before = sha(disk)
        text = self.boot("no-flush-remount", disk, "ro-remount", extra=extra)
        self.row("JF-no-flush-remount", value(text, "mount") == (0, 0)
                 and value(text, "remount") == (-1, 5) and "flush barrier" in text
                 and sha(disk) == before and not any(e[0] == "write" for e in self.requests("no-flush-remount")),
                 "writable remount is refused by name before writes when its barrier is absent")
        disk = self.image("no-flush-replay")
        prepared = self.boot("no-flush-replay-prepare", disk, "committed-cut")
        _, journal = geometry(disk)
        start = struct.unpack(">I", at(disk, journal * 4096 + 28, 4))[0]
        committed = any(at(disk, (journal + j) * 4096, 12) == struct.pack(">III", 0xC03B3998, 2, 1)
                        for j in range(1, 64))
        self.row("JF-no-flush-replay-fixture", value(prepared, "fsync") == (0, 0) and start != 0 and committed
                 and all(e[3] == 0 for e in self.requests("no-flush-replay-prepare")),
                 "a healthy cut leaves a committed transaction for the read-only replay refusal")
        before = sha(disk)
        text = self.boot("no-flush-replay", disk, "ro-replay-refuse", extra=extra)
        self.row("JF-no-flush-replay", value(text, "mount") == (-1, 5) and "flush barrier" in text
                 and sha(disk) == before and not any(e[0] == "write" for e in self.requests("no-flush-replay")),
                 "even a read-only mount refuses needed replay without a barrier, before home or journal writes")

    def late_layout(self, kind):
        """A healthy write-through late operation: the write ordinal of its
        superblock write and the backing-flush ordinal of the barrier after it."""
        name = "JF-late-" + kind + "-control"
        disk = self.image(name)
        text = self.boot(name, disk, "late-" + kind + "-control")
        events = self.requests(name)
        check = process(["e2fsck", "-fn", str(disk)], capture_output=True, text=True)
        (self.out / (name + ".fsck.txt")).write_text(check.stdout + check.stderr)
        _, journal = geometry(disk)
        writes = [i for i, e in enumerate(events) if e[0] == "write"]
        clears = [i for i in writes if events[i][1] == journal * 8]
        if kind == "rw":
            # The read-only mount writes nothing: the remount's first write is its mounted state.
            targets = [i for i in writes if events[i][1] == 0]
        else:
            # The superblock written after the journal's emptied superblock.
            targets = [i for i in writes if events[i][1] == 0 and clears and i > clears[-1]]
        barriers = [i for i in range(targets[0] + 1, len(events)) if events[i][0] == "flush"] if targets else []
        ok = (value(text, "mount") == (0, 0) and value(text, "late-operation") == (0, 0)
              and (kind == "unmount" or value(text, "late-cleanup") == (0, 0))
              and check.returncode == 0 and all(e[3] == 0 for e in events)
              and bool(targets) and bool(barriers))
        self.row(name, ok, "a healthy " + {"unmount": "unmount", "ro": "read-only remount",
                                            "rw": "writable remount"}[kind]
                 + " measures its late superblock write and barrier; fsck clean")
        if not ok:
            return None
        backing, dirty = 0, False
        for event in events[:barriers[0] + 1]:
            if event[0] == "write":
                dirty = True
            elif event[0] == "flush":
                if dirty:
                    backing += 1
                dirty = False
        return sum(1 for i in writes if i <= targets[0]), backing

    def late(self):
        layouts = {kind: self.late_layout(kind) for kind in ("unmount", "ro", "rw")}
        for kind, fault_kind, stage, words in (
                ("unmount", "write", "late-superblock", "an unmount's final superblock write"),
                ("ro", "write", "late-superblock", "a read-only remount's final superblock write"),
                ("rw", "write", "remount-rw-state", "a writable remount's mounted-state write"),
                ("ro", "flush", "late-final-barrier", "a read-only remount's final barrier")):
            name = "JF-late-" + kind + ("-barrier-EIO" if fault_kind == "flush" else "-superblock-EIO")
            layout = layouts[kind]
            if layout is None:
                self.row(name, False, "needs its healthy control's measured layout")
                continue
            disk = self.image(name)
            cfg = self.out / (name + ".cfg")
            cfg.write_text(write_error_rule(layout[0], 0) if fault_kind == "write" else flush_error_rule(layout[1]))
            case = "late-" + kind + ("-flush" if fault_kind == "flush" else "") + "-error"
            text = self.boot(name, disk, case, cfg=cfg)
            fault_ok = self.fault(name, disk, fault_kind, 0 if fault_kind == "write" else None, stage)
            self.row(name, fault_ok and value(text, "late-operation") == (-1, 5)
                     and value(text, "late-unmount-after") == (-1, 5)
                     and value(text, "late-rw-after") == (-1, 5)
                     and value(text, "late-excl-after") == (-1, 16)
                     and value(text, "late-mount-after") == (-1, 16)
                     and value(text, "late-create-after") is None,
                     words + (" fails with EIO although the sync's retry of it succeeded" if fault_kind == "write"
                              else " fails with EIO")
                     + "; the volume stays failed, its device claimed against an exclusive open and a second mount")

    def overwrite(self):
        control = self.image("overwrite-control")
        blocks = file_blocks(control, b"two")
        if len(blocks) != 2:
            raise RuntimeError("the overwrite fixture is not two blocks")
        sectors = [b * 8 for b in blocks]
        text = self.boot("overwrite-control", control, "overwrite-control")
        events = self.requests("overwrite-control")
        check = process(["e2fsck", "-fn", str(control)], capture_output=True, text=True)
        (self.out / "overwrite-control.fsck.txt").write_text(check.stdout + check.stderr)
        data = [e[1] for e in events if e[0] == "write" and e[1] in sectors]
        self.row("JF-overwrite-control", value(text, "overwrite-write") == (8192, 0)
                 and value(text, "overwrite-sync") == (0, 0) and value(text, "unmount") == (0, 0)
                 and data[:2] == sectors and all(at(control, b * 4096, 4096) == b"N" * 4096 for b in blocks)
                 and check.returncode == 0 and all(e[3] == 0 for e in events),
                 "a healthy write-through overwrite writes both allocated blocks in order; fsck clean")
        name = "JF-overwrite-EIO"
        disk = self.image(name)
        cfg = self.out / (name + ".cfg")
        cfg.write_text('[inject-error]\nevent = "write_aio"\niotype = "write"\n'
                       f'sector = "{sectors[0]}"\nerrno = "5"\nonce = "on"\nimmediately = "off"\n')
        text = self.boot(name, disk, "overwrite-error", cfg=cfg)
        fault_ok = self.fault(name, disk, "write", sectors[0], "data-overwrite")
        events = self.requests(name)
        failed = [i for i, e in enumerate(events) if e[3] != 0]
        later = bool(failed) and any(e[0] == "write" for e in events[failed[0] + 1:])
        after = value(text, "overwrite-after")
        self.row(name, fault_ok and value(text, "overwrite-write") == (-1, 5)
                 and after is not None and after[0] == -1 and value(text, "overwrite-sync") == (-1, 5)
                 and not later and at(disk, blocks[1] * 4096, 4096) == b"A" * 4096,
                 "a failed first data block fails the write with EIO; nothing, the second block included, is written after it")

    def punch(self):
        control = self.image("punch-control")
        blocks = file_blocks(control, b"two")
        if len(blocks) != 2:
            raise RuntimeError("the punch fixture is not two blocks")
        sectors = [b * 8 for b in blocks]
        text = self.boot("punch-control", control, "punch-control")
        events = self.requests("punch-control")
        check = process(["e2fsck", "-fn", str(control)], capture_output=True, text=True)
        (self.out / "punch-control.fsck.txt").write_text(check.stdout + check.stderr)
        data = [e[1] for e in events if e[0] == "write" and e[1] in sectors]
        self.row("JF-punch-control", value(text, "punch") == (0, 0)
                 and value(text, "punch-sync") == (0, 0) and value(text, "unmount") == (0, 0)
                 and data[:2] == sectors and all(at(control, b * 4096, 4096) == bytes(4096) for b in blocks)
                 and check.returncode == 0 and all(e[3] == 0 for e in events),
                 "a healthy write-through punch over two allocated blocks zeroes both in order; fsck clean")
        name = "JF-punch-EIO"
        disk = self.image(name)
        cfg = self.out / (name + ".cfg")
        cfg.write_text('[inject-error]\nevent = "write_aio"\niotype = "write"\n'
                       f'sector = "{sectors[0]}"\nerrno = "5"\nonce = "on"\nimmediately = "off"\n')
        text = self.boot(name, disk, "punch-error", cfg=cfg)
        fault_ok = self.fault(name, disk, "write", sectors[0], "data-overwrite")
        events = self.requests(name)
        failed = [i for i, e in enumerate(events) if e[3] != 0]
        later = bool(failed) and any(e[0] == "write" for e in events[failed[0] + 1:])
        after = value(text, "punch-after")
        self.row(name, fault_ok and value(text, "punch") == (-1, 5)
                 and after is not None and after[0] == -1 and value(text, "punch-sync") == (-1, 5)
                 and not later and at(disk, blocks[1] * 4096, 4096) == b"A" * 4096,
                 "a failed first punched block fails fallocate with EIO; nothing, the second block included, "
                 "is written after it, and a later punch fails")

    def plain(self):
        disk = self.out / "plain-no-flush.img"
        with disk.open("wb") as f:
            f.truncate(64 * 1024 * 1024)
        run(["mke2fs", "-q", "-F", "-t", "ext2", "-b", "4096", disk])
        text = self.boot("plain-no-flush", disk, "plain-control", extra=[
            "-global", "virtio-blk-pci.config-wce=off", "-global", "virtio-blk-pci.write-cache=off"])
        check = process(["e2fsck", "-fn", str(disk)], capture_output=True, text=True)
        (self.out / "plain-no-flush.fsck.txt").write_text(check.stdout + check.stderr)
        self.row("JF-plain-no-flush-compatibility", value(text, "mount") == (0, 0)
                 and value(text, "fsync") == (0, 0) and value(text, "unmount") == (0, 0)
                 and check.returncode == 0,
                 "plain ext2 retains its existing no-flush behavior; no durability is inferred")
        self.row("JF-plain-no-flush-warning", "no flush barrier; sync is not a durability guarantee" in text,
                 "the plain volume's mount line names the absent barrier")

    def exhaustion(self):
        disk = self.image("guard-exhaustion")
        work = self.out / "guard-exhaustion"
        work.mkdir()
        iso = work / "boot.iso"
        run([self.root / "tools/mkimage", self.a.guard_kernel, iso])
        serial = work / "serial.txt"
        run([self.root / "tools/qemu-halt", "--firmware", self.a.firmware,
             "--serial", serial, "--timeout", "120", "--elf", self.a.guard_kernel,
             "--marker", "JG DONE|PANIC .*", "--qemu", "-m", "--qemu", "512M",
             "--qemu", "-drive", "--qemu", f"file={disk},if=none,id=d0,format=raw",
             "--qemu", "-device", "--qemu", "virtio-blk-pci,drive=d0", iso])
        text = serial.read_text(errors="replace").replace("\r", "")
        self.row("JF-guard-exhaustion", all("JG " + item + "=1" in text
                 for item in ("exhausted", "truncate-EIO", "read-only", "sync-EIO"))
                 and "aborted" in text,
                 "real frame exhaustion aborts before a block loses its reuse guard; the truncate answers EIO")
        recovered = self.boot("guard-exhaustion-recover", disk, "reuse-recover")
        check = process(["e2fsck", "-fn", str(disk)], capture_output=True, text=True)
        (work / "after.fsck.txt").write_text(check.stdout + check.stderr)
        self.row("JF-guard-exhaustion-replay", "JF old-bytes=1" in recovered
                 and value(recovered, "unmount") == (0, 0) and check.returncode == 0,
                 "power cut after abort keeps the old committed file and a clean filesystem")

    def large(self):
        fixture = self.out / "large-volume"
        run(["python3", "-I", self.root / "tests/mpx6-journal.d/large-fixture.py", fixture])
        facts = (fixture / "facts.txt").read_text()
        high = int(re.search(r"old_block=(\d+)", facts)[1])
        group = int(re.search(r"old_group=(\d+)", facts)[1])
        disk = fixture / "full.img"
        committed_disk = fixture / "after-commit.img"
        run(["cp", "--reflink=auto", "--sparse=always", disk, committed_disk])
        _, journal = geometry(disk)
        text = self.boot("large-reuse", disk, "reuse")
        start = struct.unpack(">I", at(disk, journal * 4096 + 28, 4))[0]
        before = at(disk, high * 4096, 4096)
        recovered = self.boot("large-recover", disk, "reuse-recover")
        check = process(["e2fsck", "-fn", str(disk)], capture_output=True, text=True)
        (fixture / "after.fsck.txt").write_text(check.stdout + check.stderr)
        self.row("JF-large-reuse", group > 511 and value(text, "unlink-old") == (0, 0)
                 and value(text, "reuse-write") == (-1, 28) and start == 0
                 and "JF pressure-bytes=16777216" in text and before == b"A" * 4096
                 and "JF old-bytes=1" in recovered and value(recovered, "unmount") == (0, 0)
                 and check.returncode == 0,
                 f"group {group}: freed block not reused before commit; cut/reboot keeps old bytes and clean fsck")
        text = self.boot("large-reuse-committed", committed_disk, "reuse-commit")
        start = struct.unpack(">I", at(committed_disk, journal * 4096 + 28, 4))[0]
        reused = at(committed_disk, high * 4096, 4096)
        recovered = self.boot("large-committed-recover", committed_disk, "recover-reuse")
        check = process(["e2fsck", "-fn", committed_disk], capture_output=True, text=True)
        (fixture / "after-commit.fsck.txt").write_text(check.stdout + check.stderr)
        self.row("JF-large-reuse-after-commit", group > 511 and value(text, "unlink-old") == (0, 0)
                 and value(text, "free-fsync") == (0, 0) and value(text, "reuse-write") == (4096, 0)
                 and value(text, "reuse-fsync") == (0, 0) and start != 0 and reused == b"N" * 4096
                 and "JF recovered-bytes=1" in recovered and value(recovered, "old-after") == (-1, 2)
                 and value(recovered, "unmount") == (0, 0) and check.returncode == 0,
                 f"group {group}: commit releases reuse guard; a cut after the new commit preserves new bytes and clean fsck")

    def main(self):
        if self.a.only == "boundaries":
            self.incomplete()
            self.no_flush_boundaries()
            if self.a.large:
                self.large()
            return 1 if self.failed else 0
        if self.a.only == "large":
            self.large()
            return 1 if self.failed else 0
        if self.a.only == "no-flush":
            self.no_flush()
            return 1 if self.failed else 0
        if self.a.only == "plain":
            self.plain()
            return 1 if self.failed else 0
        if self.a.only == "late":
            self.late()
            self.overwrite()
            self.punch()
            if self.a.guard_kernel:
                self.exhaustion()
            return 1 if self.failed else 0
        self.plain()
        for name, features in (("JF-control", 0), ("JF-revoke-control", 1)):
            disk = self.image(name)
            _, journal = geometry(disk)
            put(disk, journal * 4096 + 40, struct.pack(">I", features))
            text = self.boot(name, disk, "control")
            check = process(["e2fsck", "-fn", str(disk)], capture_output=True, text=True)
            (self.out / (name + ".fsck.txt")).write_text(check.stdout + check.stderr)
            self.row(name, value(text, "mount") == (0, 0) and value(text, "fsync") == (0, 0)
                     and value(text, "unmount") == (0, 0) and check.returncode == 0,
                     "compatible journal writes, unmounts and checks clean")
        self.refusal("JF-compatible", 36, struct.pack(">I", 1), words="compatible features")
        self.refusal("JF-ro-compatible", 44, struct.pack(">I", 1), words="read-only-compatible features")
        self.refusal("JF-incompatible", 40, struct.pack(">I", 0x80000000), words="incompatible features")
        self.refusal("JF-uuid", 48, bytes(16), words="journal UUID")
        self.refusal("JF-persistent-error", 32, struct.pack(">I", 5), words="journal records an error")
        self.refusal("JF-v1", 4, struct.pack(">I", 3), words="journal version")
        self.refusal("JF-users", 64, struct.pack(">I", 2), words="not private to one filesystem")
        self.refusal("JF-external-uuid", 0xd0, b"X" * 16, words="external journal UUID", filesystem=True)
        self.refusal("JF-external-device", 0xe4, struct.pack("<I", 1), words="external journal device", filesystem=True)
        self.no_flush()
        self.mount_barrier()
        self.mount_state("write")
        self.mount_state("flush")
        self.eio("JF-log-EIO", "write-error", "log")
        # blkdebug counts backing flushes, not virtio requests. QEMU elides
        # the pristine qualification flush; the row verifies the actual
        # failed request and its position relative to log/commit/home writes.
        self.eio("JF-precommit-flush-EIO", "write-error", "flush-2")
        self.eio("JF-checkpoint-EIO", "checkpoint", "home")
        self.eio("JF-checkpoint-flush-EIO", "checkpoint-barrier", "flush-4")
        self.eio("JF-cache-EIO", "cache-error", "home")
        self.incomplete()
        self.no_flush_boundaries()
        self.late()
        self.overwrite()
        self.punch()
        if self.a.guard_kernel:
            self.exhaustion()
        if self.a.large:
            self.large()
        return 1 if self.failed else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--kernel", type=Path, required=True)
    p.add_argument("--guard-kernel", type=Path)
    p.add_argument("--firmware", choices=("bios", "uefi"), default="bios")
    p.add_argument("--large", action="store_true")
    p.add_argument("--only", choices=("large", "plain", "no-flush", "boundaries", "late"))
    p.add_argument("out", type=Path)
    args = p.parse_args()
    try:
        raise SystemExit(Rows(args).main())
    except Exception as exc:
        print("FAIL JF-infrastructure " + str(exc), flush=True)
        raise SystemExit(2)
