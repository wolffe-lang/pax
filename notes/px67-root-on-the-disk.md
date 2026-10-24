# px67 — root on the disk: `/` on the ext2 partition, the system installed onto it, and an end that leaves it clean

Crawl 54, Opus 5.5. Contract `sprints/pax/67-root-on-the-disk`
(pax#133). The prediction was committed first (`0d23fcd2`, `52a9b964`
before the rebase: `notes/px67/prediction.txt`). Branch `px67` from
`origin/trunk` `f0617320` (px66's merge), rebased onto `8dd80667`
(px65's merge: the 0.2.35 pins) near the end; commit hashes here are the
rebased ones unless named as before the rebase. The plants and the CI
dispatches of §8 and §9 ran on the branch before the rebase (their
bases stay reachable from the plant branches); the gates of §6 and the
playground of §7 were run again after it.

## 1. Forbidden, and what was read

No kernel's source: none of Linux's `init/do_mounts*.c`,
`fs/namespace.c`, `fs/ext2`, `fs/ext4` or `block/partitions/`, and no
other kernel's mount, boot or file-system code. No source of any init
system or mount tool (systemd, sysvinit, util-linux, busybox), of
e2fsprogs, dosfstools or Limine. What was read is in `docs/SOURCES.md`
(px67): the man pages `mount(2)`, `umount2(2)`, `mount(8)`, `fstab(5)`,
`proc_pid_mounts(5)`, `proc_pid_mountinfo(5)`, `bootparam(7)`,
`statfs(2)`, `statvfs(3)`, `reboot(2)`, `pause(2)`, `kill(2)`,
`signal(7)`, `systemd-system.conf(5)` and `systemd-shutdown(8)` (pages
only); the uapi headers for numbers only (`linux/mount.h`,
`asm-generic/signal.h`); Limine's `CONFIG.md` at v12.9.1; the ext2
layout documentation (`s_state`, `s_mnt_count`, `s_mtime`, `s_wtime`).
kasumi's Linux 7.2.8 on QEMU (`tools/linux-root`, the probe as its
init), its own mount tables, e2fsprogs 1.47.0 from the pinned image and
QEMU ran as black boxes. Builds in `px13-ubuntu` on kasumi CPUs 0-3
under `flock ~/lanes/kasumi-cores-0-3.lock`; QEMU under `taskset -c
0-3`, `ulimit -c 0`; long jobs by `setsid -f` with pid files; nothing
installed on any host; nothing built on nomad-1. No merge, tag, label,
issue filed or closed; no other repository's trunk changed; no
filming words.

## 2. Inputs, re-derived

| input | found |
|---|---|
| pax trunk | `f0617320` (px66's merge) at the start; px65 (the 0.2.35 pins) merged as `8dd80667` while this lane ran, and the branch was rebased onto it: seven files both changed (CHANGELOG, README, docs/CENSUS.md, docs/SOURCES.md, ci.yml, tools/ci-tiers.map, tests/ci-plan), every conflict an addition beside another (px65's `mpx5-bore` and this lane's `mpx6-root` in @user, the two SOURCES sections, the two README and CHANGELOG paragraphs, px67's first); no kernel file of px65's; every user program now of the 0.2.35 generation, so the playground was rebuilt (§7) |
| `kernel/tree` | two stores: the memory's inodes (ROOT the initramfs's tree) and ext2 volume records with a side table; a mount covers a memory directory (`is_point`), and its lookup returns the volume's root record; `/` always the memory's ROOT (R-px63-2 the plan) |
| `kernel/files` | every path walk starts at `root_node()` (ROOT); `/dev`, `/proc` and `/sys` synthetic children of ROOT, intercepted by name |
| `kernel/fstab` | px66's: `/etc/fstab` read from the initramfs, `/dev/vdaN`, `PARTUUID=`, `PARTLABEL=`, `UUID=`, `LABEL=` |
| `kernel/ext2` | mounts mark the volume in use on the disk at once (px66's fix); unmount writes the clean state after every other block is flushed |
| `kernel/boot_info` | Limine's `cmdline`, `cmdline_has(word)` only |
| the end | kmain waited for every process after each run-list line; init's end or root's `reboot(2)` wrote the volumes; nothing sent a signal; pid 1 immune to default-action signals (Linux's rule: `sched.inert`, `signal.act`) |
| `mount(2)`, `umount2(2)` | px45's: EPERM for a user, refused by name for root |
| `tools/mkinitramfs` | newc, every entry's mode, uid, gid and mtime in its header (mtime 0); the list the `--attrs` file is generated from |
| `tools/mkdisk` | `--from DIR --attrs FILE` (px63, sorted debugfs); `--gpt` (px66) |
| the guest | kasumi's 7.2.8-1-cachyos under QEMU 11.1.1 TCG, `-kernel`, no initramfs, virtio_blk and the ext4 driver built in (it mounts ext2) |
| CI | `tools/ci-plan` and `tools/ci-tiers.map`: `kernel/boot_info/*` and `kernel/sched/*` are ALL paths, so this PR's `tier pr` runs every suite on native BIOS; no FULL path is touched (`tools/qemu-run`, `qemu-halt`, `mkimage` and `lib.sh` unchanged), so it is not an `all` run |

## 3. Prediction, scored

| predicted | measured | score |
|---|---|---|
| about 220 kernel lines for the root switch (tree ~60, files ~40, fstab and boot_info ~100, kmain_console ~20); about 800 in all, with mount(2), umount2(2), the remounts, the tables and the end | the root switch's commits insert 922 kernel lines, comments included (kernel/tree's root record and mount table 453, kernel/fstab's `root=` 308 and its numbers 74, boot_info 50, files' walk 22, kmain_console 15); the lane's kernel diff against trunk is 1,986 inserted, 155 deleted, over 13 files (files 532, tree 453, fstab 378, user 238, kmain_session 89) | wrong: four times the guess for the switch, two and a half for the whole; the shares (tree and fstab the largest) right |
| the suite that fails first with `/` on the disk: mpx3-boreutils, on directory sizes and device numbers (ext2's 4096-byte directories on 254:2 where the tmpfs reference says 40 and 0:1) | mpx3-boreutils passes on the disk, every row, both boots (CI 40059322645); the first to fail was mpx3-shell (§6): its log's end (the disk's books printed after init's line, which a suite holds last: fixed in the kernel, `9434d97f`), its frames census, and ext2's indirect blocks in `ls -l`'s total and stat's `%b`. The predicted kind appeared in mpx3-tree, whose probe prints a directory's size and blocks (4096 and 8 on the disk, 40 and 0 on Linux's tmpfs): why it has no disk leg | wrong on the suite, right on the kind; the end's order unforeseen |
| @@P3@@ | @@M3@@ | @@S3@@ |
| the crash row's commonest class: lost writes only; second, bitmap and count differences; orphans rare; nothing worse | 24 kills: 20 lost writes, 4 counts (a free-blocks count, and the same two blocks marked in use three times after one flusher turn), 0 orphans, 0 worse, 0 none (§6) | right |
## 4. What was built

**The root record** (`kernel/fstab`'s `mount_root`, `kernel/boot_info`'s
`cmdline_value`, `kernel/tree`'s `mount_root`). Before the first program,
`root=` is read from Limine's command line (up to `--`) and resolved in
bootparam(7)'s spellings: `/dev/vda2` or `vda2`; the device's numbers in
hex (`0xfe02`, `fe02`: the major above the low byte) or as
`major:minor` (`254:2`); `PARTUUID=` in either case; `UUID=` (the ext2
UUID, served where Linux's kernel alone panics: a named drift);
`rootfstype=` `ext2` or absent; `rw`, else read-only (the guest's
default, measured, where bootparam(7) says `rw`). The volume becomes the
root mount: `tree.top()` is its root record from then on, the memory's
ROOT is covered, and `/etc/fstab` and the run list are read from it
(`tree.small_file`). One line:

    root: PARTUUID=bf7607d6-… (vda2) on /: ext2, read-write, write-back

A `root=` that names nothing panics by name (`root: /dev/vda9: no such
disk; no initramfs to stay on`), unless an initramfs was loaded, which
stays `/` (`… / stays the initramfs in memory`: R-px67-2's rescue).
Without `root=` nothing changes: the ISO path's every suite runs as
before (R10, and the batches of §6).

**Paths on the volume** (`kernel/files`, `kernel/tree`). The walk starts
at `top()`; `/dev`, `/proc` and `/sys` are intercepted at `top()` (the
kernel's own trees over the disk's empty directories); getcwd, the
`/proc/self/exe` text, chroot's root check and `exec` resolve from it.
`..` of a mount's root is the covered directory's parent, but the root
mount's root is its own parent: the fix the dotdot plant takes out (§9).
`name_of` gives a mount root its covered directory's name. rmdir and
rename of a mount point answer EBUSY.

**The mount table** (`kernel/tree`). Eight mounts, each with its point,
root, volume (or none: a memory mount), device, sequence number, flags
(nosuid, nodev, noexec, sync, the root's) and mode. `mount` and
`mount_mem` attach, `unmount` sheds a volume's records (EBUSY while
anything of it is held: a working directory, an open file; a tmpfs
that still has entries is EBUSY too, a limit: §10), `remount` flips
read-only (EBUSY while a file is open for writing). The halt unmounts in
the reverse of the sequence, `/` last.

**ext2 remount** (`kernel/ext2`'s `remount`). Read-only: every dirty
block written and flushed, then the clean state (when it was clean at
the mount and no error since) and the write time, flushed. Read-write:
the state cleared, the mount count up one (as the guest counts a
remount), the mount time written, flushed.

**The tables** (`kernel/procfs`, `kernel/files`' `mounts_of`).
`/proc/self/mounts` and `/proc/<pid>/mounts`, `mountinfo` beside them,
`/proc/mounts` a link to `self/mounts` (11 bytes, as the guest's):

    /dev/root / ext2 rw,relatime 0 0
    devtmpfs /dev devtmpfs rw,nosuid,noexec,relatime,mode=755 0 0
    proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0
    sysfs /sys sysfs rw,nosuid,nodev,noexec,relatime 0 0
    tmpfs /tmp tmpfs rw,nosuid,nodev,relatime 0 0

(`rootfs / rootfs rw,size=…,nr_inodes=…` first when `/` is the
initramfs, as the guest's initramfs root reads). mountinfo's ids and
the anonymous devices' numbers are the kernel's own (the suite folds
them); its root, point, options, type, source and super options are the
guest's. Paths escaped as proc(5) says (space, tab, newline, backslash
in octal).

**mount(2) and umount2(2)** (`kernel/files`' `mount_call` and
`umount_call`, dispatched from `kernel/user` for privileged callers;
docs/CENSUS.md has each answer). The census found no caller (§6), so
what is served is what an operator and a boot ask: `/` remounted both
ways, an ext2 volume or a tmpfs mounted at a directory and unmounted,
and every error the guest gave the probe, in the guest's order.
`umount2("/")` remounts `/` read-only and answers 0, as the guest's
does. MNT_DETACH is refused by name (`R_MOUNT`).

**The end** (`kernel/user`'s `end_processes` and `the_end`, used by
kmain_console and, new here, kmain_session; `kernel/sched`,
`kernel/signal`). The last run-list line (init) is waited for alone
(`wait_pid_or_down`); when it ends, up to a second for what it left to
end of itself (`SETTLE_TICKS`: a shell's stopped jobs, hung up as an
orphaned group when it exits, end so, and are not signalled); then, or
at once when root's `reboot(2)` asks (the caller suspended, kmain
woken), every process left is sent SIGTERM
(and SIGCONT, so a stopped one sees it); up to 2 s (`GRACE_TICKS`,
R-px67-4) for them to end, early when they all have; SIGKILL to the
rest; pid 1's immunity lifted for the end (`sched.ending`, the rule
Linux keeps for init until then). Then the volumes in reverse mount
order, `/` last, written, flushed and marked clean, the disk's books,
init's line last before `halt` (so a log ends the same way from a disk
as from the ISO), and the halt or the reset. One line when anything was
signalled:

    PAX: the end: SIGTERM to 2 processes, 1 ended within 10 ms; SIGKILL to 1 after the 2000 ms grace

**kmain_session** gains what kmain_console had since px63: the disk
after the network, `/` on it when `root=` says so, `/etc/fstab`, the
flusher, the run list from the tree, and the end.

**tools/mkdisk --gpt --root ARCHIVE.** The archive's entries (newc) are
unpacked into a stage and `--attrs` is written from their headers (mode,
uid, gid, mtime; a link 777), never by hand; the kernel's mount points
(`/dev` 755, `/proc` 555, `/sys` 555, `/tmp` 1777) are added when the
archive lacks them; partition 2 is made by `mkdisk --from` with them
(OUT.root-attrs kept). The ESP holds Limine and the kernel; the entry's
`module_path` is dropped unless `--initramfs` keeps it (R-px67-2), and
`root=PARTUUID=<partition 2> rw` is added to its `cmdline` unless the
configuration names a root already (then `@PARTUUID@`,
`@PARTUUID-UPPER@` and `@UUID@` are filled in: the suite's spellings).
`--home-size SIZE` adds a partition 4 (R-px67-3's other way). Every
byte follows from SOURCE_DATE_EPOCH: the suite's disks and the
playground's are reproducible.

**user/fstab-root**: `/dev/vda2 / ext2 rw 0 1` and `tmpfs /tmp tmpfs
nosuid,nodev 0 0` (R-px67-1); the playground's and the suite's.

**The probe** (`user/elf/mounts.c`, `tools/mkrootprobe`): static glibc,
the same binary as the guest's init and in PAX's archives: `table`,
`root`, `calls`, `user`, `twice`, `churn`, `linger`, `term`, `end`,
`init`.

**tools/linux-root**: the guest booted with its root on partition 2 of
a GPT disk laid out as PAX's, the probe as `/sbin/init`, `--kill ERE` for
a power cut, `--initrd` for the initramfs shape, the host's
dumpe2fs and e2fsck of partitions 2 and 4.

**tools/qemu-rootdisk**: a stand-in for QEMU (`PAX_QEMU`) that boots any
suite's ISO from a disk instead: the ISO's kernel, configuration and
initramfs taken apart (xorriso), `mkdisk --gpt --root` of them (the
initramfs kept as the module, so kernels that read no `root=`, the
loader's and boreutils', boot from the disk as before), cached by the
ISO's sha256, a copy a boot; runs that bring a virtio disk of their own
(mpx6-blk, -ext2, -part) are left as they are. `--prepare` makes the
disks before a suite's timeouts start.

**tools/root-crash**: the crash row (§6).

## 5. Rulings asked (recommended, implemented, not decided)

Each is implemented as recommended and reversible: a line of
`user/fstab-root`, a flag of `tools/mkdisk`, a constant of kernel/user,
a branch of kernel/ext2.

**R-px67-1: `/tmp` on the disk or in memory.** Recommended, implemented:
**in memory**, a tmpfs mounted by `/etc/fstab`'s second line (`tmpfs
/tmp tmpfs nosuid,nodev 0 0`), as distributions keep /tmp (kasumi's
is a tmpfs, by its own fstab line, `rw,noatime`; nosuid,nodev are the
flags its systemd gives the tmpfs at /run and /dev/shm, measured in
its mountinfo); what a session leaves
in /tmp is gone at the next boot (R5: `/tmp/px67-tmp` written before
the reboot, absent after) and never fills the disk. The other way: no
line, /tmp a directory of `/` (1777, `tools/mkdisk --root` makes it),
kept across boots. Reversible by the fstab line.

**R-px67-2: the initramfs when `root=` is given.** Recommended,
implemented: **none**. Limine loads no module; the kernel has its block
and ext2 drivers built in (as kasumi's Linux has virtio_blk and ext4),
so an initramfs would only be a second copy of the system (59 MB for
the playground) read through the firmware at every boot (px66 measured
that read as SeaBIOS's slow path: +36% to the first line from the disk
against the ISO). The other way, built and tested: `tools/mkdisk
--initramfs` keeps the archive as the entry's module, and a `root=` that
names nothing then leaves `/` the initramfs instead of a panic (R1
root-rescue). A rescue entry is reachable only through Limine's menu,
which `timeout: 0` hides (CONFIG.md: a key during a non-zero timeout
shows it); that is a second entry and a non-zero timeout, a change to
boot/ and not made here.

**R-px67-3: one partition or a separate `/home`.** Recommended,
implemented: **one partition**: `/home` is a directory of `/` (the
playground's `/home/pax`, 1000:1000), so the whole system is one volume
the host reads with one `dumpe2fs`, and nothing is split by guesswork
between two sizes. The other way, built and tested: `tools/mkdisk
--home-size SIZE` adds partition 4 (`tests/mpx6-root`'s disks have it,
for the mount rows) and an fstab line mounts it at `/home`. The
maintainer's px66 disk had `/home` on partition 2; the new image is
fresh, and px66's is kept as `pax-disk.img.px66` (§7 says how to carry
its files over).

**R-px67-4: the grace between SIGTERM and SIGKILL.** Recommended,
implemented: **2 s, ended early** when every process has ended
(`GRACE_TICKS` 200), after the settle (above). Measured on PAX (§6,
the probe's `term`): `sleep`, pelt running a script and yew each end
20 ms after SIGTERM (two timer ticks: the signal's default action);
an interactive pelt ignores it, as POSIX asks, and is still there after
10 s; the probe's daemon that sets SIG_IGN likewise. What PAX runs ends
at once or never, so a longer grace would only delay every halt that
has such a process. systemd's
90 s (`DefaultTimeoutStopSec=`, systemd-system.conf(5)) is for services
with stop logic of their own, which nothing on PAX has yet. Reversible
by the constant; lobo, the one program with a stop path of its own, is
not measured here (§10).

**R-px67-5: an unclean root at boot.** Recommended, implemented:
**mount it read-write with one warning**, as the guest's ext2 does
(measured: `EXT4-fs (vda2): warning: mounting unchecked fs, running
e2fsck is recommended`, then a read-write mount; its clean unmount
leaves it `not clean`, mount count 6). PAX says `not cleanly
unmounted` once in the root's `ext2:` line, mounts it read-write, and
its clean end leaves it not clean (R8), so the host's `dumpe2fs -h`
keeps saying what happened until `e2fsck` repairs it. The other way:
read-only until the host repairs it (safer for what is on it, but the
playground then has no writable `/` and every session after a power
cut starts with the host's e2fsck). PAX has no fsck (an issue: §11).

## 6. Witnesses and measurements

**tests/mpx6-root on kasumi** (native BIOS, every row, the Linux side
live and then recorded): 28 rows PASS (batch r3, at `a1a2fd72` with
the CI wiring then uncommitted). The first run (r2) had 25 PASS and 3
FAIL: R6's `mounts:` lines inside `calls` were compared unfolded (the
fold `tab` used was not applied to them), and R4's tree diff read a
link's target as bytes and counted mkfs's `/lost+found`; both fixed in
the suite before it was committed. In CI, the control dispatch at
`2a07bde2` (run 40053057349) is green.

**The guest, measured** (tools/linux-root, kasumi's 7.2.8-1-cachyos):
the root's source reads `/dev/root`; the kernel mounts devtmpfs at /dev
itself; neither `ro` nor `rw` mounts the root read-only (bootparam(7)
says `rw`); `root=0xfe02`, `fe02` and `254:2` mount vda2; `UUID=` and a
missing device panic (`VFS: Cannot open root device … error -6`); a
remount read-write counts a mount; `umount2("/")` remounts it read-only
and answers 0; an unclean root mounts read-write with `warning: mounting
unchecked fs, running e2fsck is recommended` and stays not clean through
a clean unmount (mount count 3 to 6 over the two boots:
`tests/mpx6-root.d/linux/notclean.txt`); an initramfs root reads
`rootfs / rootfs rw,size=…,nr_inodes=…`.

**The other suites, ISO path, this lane's kernel** (kasumi, native BIOS,
`notes/px67/run-suite.sh`: the build in `px13-ubuntu`, the Linux side on
the host, the boots under TCG on CPUs 0-3):

| suite | rows | batch |
|---|---|---|
| mpx6-part | 93 PASS | r1 |
| mpx6-blk | 14 PASS | r1 |
| mpx3-console | 26 PASS | r1 |
| mpx6-ext2 | 18 PASS | r3 |
| mpx3-threads | 11 PASS | r3 |
| mpx3-boreutils | 12 PASS | r3 |
| mpx5-accounts | 10 PASS | r3 |
| mpx3-tree | 64 PASS | r3 |
| mpx5-users | 110 PASS (two recordings of PAX's own lines updated: setid's and sig's first lines now name the mounts /proc/self/mountinfo lists, where they found no table) | r4 |
| mpx3-shell | 70 PASS | r4 |
| mpx5-jobs (kmain_session, its new end) | 238 PASS | r4 |

r3's first mpx3-shell and mpx5-users and mpx5-jobs results were runner
artifacts, not the kernel's: the runner then ran the suites' Linux side
inside the build container, which has no container engine and no
busybox (S0/J0: `tools/linux-tree …`, `no busybox`); the runner now
builds with `--only build`, runs `--only linux` on the host (px62's
order) and boots, and r4's runs are those.

**The root-on-disk legs** (tools/rootdisk-leg, every suite's ISOs
booted again with `/` on a disk; CI dispatches on the branch before the
rebase, and kasumi):

| suite | boots through a disk | what the leg found | now |
|---|---|---|---|
| mpx3-boreutils | 2 | every row (CI 40059322645) | PASS |
| mpx3-console | 5 | every row (CI 40059322645) | PASS |
| mpx3-threads | 1 | T4, the frames census: the block layer's cache keeps what it read (CI 40059322645) | T4 says SKIP by name; PASS (CI 40060313107) |
| mpx3-maps | 1 | T4 likewise (CI 40059322645) | likewise; PASS (CI 40060313107) |
| mpx3-shell | 12 | S5 every boot: the log ended with the disk's books, not init's line and `halt` (kasumi r4/c1); S1 the frames census; S2 shell-long: `ls -l /bin`'s total and stat's `%b` (ext2 counts a file's indirect blocks: 28424 sectors for /bin/ls where tmpfs says 28384) | S5 fixed in the kernel (`9434d97f`: the books before init's line); S1 SKIP; S2 folds the two block counts in copies of both sides, said (12 SKIP lines, CI 40060313107 then S6 read the folded copy: fixed, `81456932`) |
| mpx5-users | 4 | U3, the census; then setid's first line: `/` is ext2 `rw,relatime` where the ISO's rootfs says `rw` (CI 40060313107) | U3 SKIP; setid's line expected with the volume's options |
| mpx3-tree | 1 | T1: a directory's size and blocks (4096 and 8, Linux's tmpfs 40 and 0); T2 the limits; T4 the census (CI 40059322645) | **no leg**: its stores are the memory tree's; on a disk its probes measure ext2 against Linux's tmpfs, and mpx6-ext2 holds ext2 to Linux's ext2 |
| mpx4-lobo | 2 | every row; the leg's own count read no boot (lobo-session keeps QEMU's output as `qemu.log`, not `*.qemu.log`) (CI 40060313107) | qemu-rootdisk books each boot in its cache, and the leg counts that (`f9c043e7`) |
| mpx5-pelt | — | the ISO run itself: `c_jc_mixed_pipeline`'s session ends with `PAX: the end: SIGTERM to 2 processes, 2 ended within 10 ms`, which Linux's does not print: pelt exits with two stopped jobs, which its exit hangs up as an orphaned group, and the end signalled them first (CI 40060313107) | the end now waits up to a second for what is ending of itself (`a349d930`) |
| mpx5-jobs | 12 | every row, ISO and disk (CI 40060313107: 477 PASS lines over both runs) | PASS |

The legs' skips are counted on the leg's last line (`… N rows said SKIP
for the disk`) and each names its row and `rootdisk`. The final head's
`tier pr` runs every leg but the long three (§8).

**R-px67-4, measured** (the probe's `term WAIT PROG`, kmain_console from
the playground's build, its programs; notes/px67/play/kasumi-repro-term.out):

| program | SIGTERM to its end | how |
|---|---|---|
| `/bin/sleep 100` | 20 ms | signal 15 (the default action) |
| `/bin/sh /etc/px67-sleep.sh` (pelt running a script) | 20 ms | signal 15 |
| `/bin/sh -i` (pelt, interactive) | still there after 10,000 ms; SIGKILL | signal 9 (an interactive shell ignores SIGTERM: POSIX) |
| `/bin/yew /tmp/px67.txt` | 20 ms | signal 15 |

**The crash row** (`tools/root-crash --n 24 --seed 67 --ops 1500`, SeaBIOS,
`notes/px67/crash.txt`): a 1500-operation session in `/churn` (files of
1 to 16 KiB made, appended to, renamed, removed, cut in half;
directories with a file), 10 ms apart, no fsync, so the 5 s flusher is
all that reaches the disk; one uncut boot timed it (30.09 s, clean,
every name the replay expects), then 24 copies of the disk each killed
at a seeded point and read on the host:

| class | kills | what |
|---|---|---|
| none | 0 | |
| lost writes | 20 | e2fsck clean; the tree short of the operations' (10 to 135 names: what came after the flusher's last turn) |
| counts | 4 | one `Free blocks count wrong for group #0` (kill 11); three `Block bitmap differences: -1942 -1973` (kills 22-24, all after the same flusher turn: two blocks marked in use that no inode points at, so the turn wrote the state between two steps of one call, an allocation or a free half done) |
| orphans | 0 | |
| worse | 0 | |

Every kill left `/` not clean, as it should. The counts class is what
a journal (ext3) removes; the lost writes are what a shorter flusher
period or an fsync bounds.

## 7. The playground

**The file is `~/pax-playground/pax-disk.img.px67`**, not
`pax-disk.img`: the orchestrator's rule for a lane not yet merged (its
candidate as `pax-disk.img.<lane>`, no other lane's file touched; the
merged one is put at `pax-disk.img` at its merge). When this lane built
it, `pax-disk.img` was px65's candidate (the 0.2.35 pins, px66's layout,
sha `edb02ddf…`, open PR) and `pax-disk.img.px66` px66's, open and
being written by the maintainer's own QEMU (pid 39991, lsof): both left
exactly as they were. Built at the 0.2.34 pins, trunk's while px65 is
unmerged.

## 8. CI

- **The plan.** This branch touches `kernel/boot_info/*` and
  `kernel/sched/*`, ALL paths of `tools/ci-tiers.map` (the kernel's
  core) and `.github/*`, so its `tier pr` runs every suite on native
  BIOS. It touches no FULL path (`tools/qemu-run`, `qemu-halt`,
  `mkimage`, `lib.sh`, the pins and boot/ are unchanged), so unlike
  px66's it is not an `all` run. `Footprint: cross-cutting`: the merge
  gate is `tier full` under the orchestrator's label.
- **mpx6-root**, a job of its own (`PAX_ROOT_ROWS` `pr` in `tier pr`:
  R0 to R4, R6, R7, R9's halt and R11 on the first leg; every row in
  the full and all tiers); the Linux side is the record made on kasumi
  (`tests/mpx6-root.d/linux/`, Linux 7.2.8-1-cachyos), as mpx6-ext2's
  and mpx6-part's are; e2fsprogs and the disk tools from the pinned
  image under docker.
- **The root-on-disk legs.** Nine suites' jobs gain a step after their
  own, `tools/rootdisk-leg SUITE --tier native --firmware bios`: the
  ISOs the suite just built booted again with `/` on a disk
  (`PAX_ROOTDISK=1`: a row that measures the memory tree itself says
  SKIP by name, counted on the leg's last line; §6 lists them), the leg
  failing when no boot went through a disk. In every tier the suite runs
  in: mpx3-boreutils, -console, -shell, -threads, -maps and mpx5-users;
  outside `tier pr` only: mpx5-pelt, mpx4-lobo and mpx5-jobs (the
  contract's long ones; by the trunk all run's costs mpx5-users, 71
  minutes, is as long as mpx5-jobs, and mpx4-lobo, 21, is short: the
  contract's split is kept). mpx3-tree has none (§6). Native BIOS in
  every tier: the root's code is the same on the release tier and under
  OVMF, which mpx6-root's own legs cover in the full and all tiers.
- **tools/ci-tiers.map and tests/ci-plan.** mpx6-root joins @user and
  @disk and the ext2, fstab and procfs lines; `user/fstab-root` and the
  suite's tools are its own by the derivation; tools/root-crash maps to
  NONE (run by hand, reported). The derivation hands tools/mkdisk,
  tools/e2fs, tools/mkgpt and tools/disktools to the nine suites with a
  disk leg too (their jobs name the leg's tool, which names them); the
  expectations say so (`ROOTDISK`). One trap met and fixed on the way: a
  comment in tools/mkdisk naming `tests/mpx6-root` by its path made the
  derivation give that suite's changes to every suite that names
  mkdisk; and a step's title naming `tools/ci-tiers.map` made three
  suites read every path. Both now in prose. A third: a step's name
  with a colon and a space made ci.yml no YAML at all (GitHub then saw
  no `workflow_dispatch`, and refused a dispatch: 422); tests/ci-plan's
  own reader did not notice. Fixed (`f47042a5` before the rebase); the
  workflow now checked with a YAML parser before each push.
- **Dispatches on the branch before the rebase:** the control,
  mpx6-root at `2a07bde2`, green (40053057349); the three plants (§9);
  five fast suites with their legs (40059322645: boreutils and console
  green, threads, maps and tree red on the census and tree's rows); the
  long three and four fixed ones (40060313107: threads, maps and jobs
  green; shell, users, lobo and pelt red on what §6 says, each fixed).
## 9. Seen red

### The plants

Each plant is px67's head `2a07bde2` plus one commit on a branch of its
own, dispatched `-f tier=pr -f suites=mpx6-root` (a partial run, every
row of the suite on native BIOS), never merged; the control is the same
dispatch on `px67` itself, green (run 40053057349). Extracts in
`notes/px67/ci-<run>-plant-<name>.log`.

| plant | the break | run | red | the rest |
|---|---|---|---|---|
| `px67-plant-dotdot` `289df3a8` | kernel/tree's `parent`: the root mount's root no longer its own parent, so `..` at `/` falls through to the covered directory's parent, the memory's ROOT | 40053029963 | **R2**: `dotdot: / and /.. one directory: no` where the guest says `yes`, and `getcwd after chdir(/..) = -1 ENOENT` where it says `/` | 27 rows PASS |
| `px67-plant-clean` `966558b7` | kernel/tree's `halt_volumes`: `/` written back but its unmount (the clean flag) skipped | 40053032136 | **R7**: `partition 2: 'not clean 3' (want 'clean 3')`; and every other row that reads the flag after an end: R9 (`not clean 1`), R9 reboot(2), R5 (`not clean 2`) | 24 rows PASS |
| `px67-plant-attrs` `d5f17b2f` | tools/mkdisk's `root_tree`: the generated `--attrs` file loses `/etc/motd`'s line | 40053034315 | **R4**: `treediff: /etc/motd: mtime 0 in the archive, 1700000000 on the volume` (mkdisk's default time for a path the attrs do not list) | 27 rows PASS |

### Environment events

Two resets of kasumi while this lane's batches ran on CPUs 0-3. Neither
left a kernel line: no OOM, no panic, no machine check in the journal
of the boot that ended. The orchestrator traced both to a model being
loaded onto kasumi's GPU from hasu by the pool, not to this lane's
containers or QEMUs (one QEMU of 256 MiB to 512 MiB at a time, /home at
57 GB free). What each one cost:

| reset | the journal's last line (read after the reboot) | rebooted | running then | lost, and what was done |
|---|---|---|---|---|
| 1 | 21:40:05, the kernel's overlayfs lines for this lane's e2fsck and debugfs containers (`journalctl -b -1 --since 21:36`, read at 21:45) | 21:41:17 | batch r1 (mpx6-ext2 rerun, mpx3-shell, then mpx3-tree, ...) and root1 (mpx6-root's first run), one after the other under the lock: mkdisk's containers for mpx6-root's disks | mpx3-shell's first result (its boot log stops at 21:39, no verdict line): **absent, not red**; root1 and the rest of r1 never ran. Both restarted as one batch (r2) from a snapshot at 21:56 |
| 2 | 22:00:32, systemd-logind removing a session (`sudo journalctl -b -1`, read at 22:05) | 22:01:54 | batch r2: mpx6-root had finished (25 PASS, 3 FAIL: fixed in the suite before its commit, §8), mpx6-ext2 half run | mpx6-ext2's half run deleted with its snapshot, the rest of r2 never ran; restarted as r3 at 22:05. The reset also emptied 25 loose objects of the kasumi clone's `.git` written in the seconds before it (the commits `dacfb98e` and `a1a2fd72`, both already pushed): the `.git` was replaced by a fresh clone of `origin/px67`, nothing lost; commits there are followed by `sync` since |

The journal's index, read again at 22:07, no longer lists either ended
boot (the resets left its files unclosed): the timestamps above are the
ones read at the time.

## 10. Limits named

- **UUID=** is served (the ext2 UUID), where Linux's kernel alone
  panics (`VFS: Cannot open root device "UUID=…"`, measured): Linux
  serves it only through an initramfs's userspace. A named drift, kept:
  it costs nothing and the suite's spellings test it. `LABEL=` and
  `PARTLABEL=` are not root spellings here (nor Linux's kernel's).
- **A non-empty tmpfs** cannot be unmounted (EBUSY): Linux unmounts it
  and drops its files. Nothing mounts one but the probe, which unmounts
  it empty; kernel/tree frees a memory mount only when it holds nothing.
- **MNT_FORCE and MNT_EXPIRE** are taken as a plain unmount, not
  measured on the guest; MNT_DETACH is refused by name.
- **The mount table** holds eight mounts (`MOUNTS`), the root's
  included. mountinfo's ids and the anonymous devices' numbers are
  PAX's own (the suite folds them), and so are devtmpfs's and tmpfs's
  size options (PAX's trees have no `size=` or `nr_inodes=`: folded too).
- **/dev** is the kernel's synthetic tree, not a devtmpfs: `mount(2)` of
  devtmpfs, proc or sysfs is refused by name (-EINVAL), and the disk's
  /dev, /proc and /sys are empty directories nothing reaches while the
  kernel's trees cover them.
- **The root's file system** is ext2 only (`rootfstype=` anything else
  is refused by name), mounted write-back with the 5 s flusher: a power
  cut loses up to the last turn's writes (the crash row, §6). No
  journal (ext3: an issue, §11).
- **No fsck on PAX** (the contract's; an issue): an unclean `/` stays
  unclean until the host's `e2fsck -fy`.
- **No `pivot_root(2)`**, and one root for the machine's life: nothing
  asks.
- **The end's grace** is fixed at 2 s (R-px67-4): a program that needs
  longer to stop (none on PAX today) is killed.
- **tools/qemu-rootdisk** installs an ISO's first module as the system
  (`module_path`); an ISO with two modules gets only the first.

## 11. Issues and what to prune

Issues to file (none filed here: RULES §1):

1. **pax: a journal for `/` (ext3).** The crash row's table (§6) is the
   case: what a power cut at a random point leaves with ext2 and the 5 s
   flusher; a journal turns the counts and orphans into replays. The
   contract names it.
2. **pax: fsck on PAX.** An unclean `/` stays unclean until the host's
   `e2fsck -fy` (R-px67-5); a boot-time check (or a `fsck` in wolf)
   would close it. The contract names it.
3. **pax: an installer that writes the disk from PAX (P6).** Today the
   system reaches the disk only at build time (`tools/mkdisk --root`);
   an installer needs the ESP readable and writable (FAT: R-px66-3's
   `/boot`) and the root's tree copied from a running system. The
   contract names it.
4. **boreutils: `df`.** None at the pin `12de639`; PAX now answers
   `statfs`, `fstatfs` and `statvfs` for `/` and every volume as Linux
   does (docs/CENSUS.md), so a `df` has what it needs. Witness: `ls
   build/*/bore/` has no df; `tests/mpx6-root`'s R3 rows.
5. **pax: a rescue entry for Limine** (R-px67-2's other way made
   reachable): a second entry that loads the initramfs, and a non-zero
   `timeout` so its menu can be reached; a change to boot/ and to every
   disk's boot.
6. **pax: unmounting a tmpfs that holds files** answers EBUSY (§10);
   Linux drops the files and unmounts.
7. **pax: lobo's stop path under the end's grace** (R-px67-4): lobo is
   the one program PAX runs with a stop path of its own; its time from
   SIGTERM to exit was not measured (its image needs the network), so the
   2 s grace is unproven for it.

Environment, for the orchestrator (not a repository's issue): kasumi
reset twice in 20 minutes while a model was loaded onto its GPU from
hasu (§9); the second reset emptied freshly written git objects in a
lane clone (`sync` after commits now).

To prune once this merges:

- kasumi `~/lanes/px67/` (the clone and its worktrees `plant-dotdot`,
  `plant-clean`, `plant-attrs`; `build/`, `snap/`, `play/` but for what
  §7 keeps, `kb/`, `smoke/`, `guest/`, `probe/`, `cache/`, `tmp/`, the
  batch logs): about 6 GB at the end;
- the branches `px67-plant-dotdot`, `px67-plant-clean`,
  `px67-plant-attrs` on origin (and `px67` after the merge);
- this Mac's worktree `/Users/mfwolffe/lanes/px67/pax`;
- nothing on nomad-1 but the playground files the maintainer keeps
  (`~/pax-playground/pax-disk.img`, `pax-disk.img.px66`).

