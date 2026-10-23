# px62 — mremap, file-backed and shared mmap, FIFOs and flock

Crawl 54, Opus 5.5. pax#127 (mremap), pax#128 (file-backed and shared
mmap), pax#108 (flock and a FIFO's mknodat). PR pax#130. The prediction
was committed first, `932f9985` (`notes/px62/prediction.txt`).

## 1. Forbidden, and what was read

No Linux kernel source, no other kernel's, no musl's or glibc's source.
What was read is in `docs/SOURCES.md` (px62): man pages (`mmap(2)`,
`mremap(2)`, `msync(2)`, `mprotect(2)`, `madvise(2)`, `fork(2)`,
`execve(2)`, `truncate(2)`, `flock(2)`, `fifo(7)`, `pipe(7)`, `mknod(2)`,
`mkfifo(3)`, `open(2)`, `sigaction(2)`, `tmpfs(5)`), POSIX.1-2024's
`mmap()`, `msync()`, `munmap()`, `mkfifo()` and `open()`, the uapi
headers in the refs clone for every constant (`linux/mman.h`,
`asm-generic/mman-common.h`, `asm-generic/fcntl.h`, `linux/stat.h`,
`asm-generic/siginfo.h`, `asm-generic/errno.h`) and `syscall_64.tbl`, the
Intel SDM vol. 3A §4.5 and AMD APM vol. 2 §5.4.1 for the PTE's software
bits. Linux was a black box: two probes (`user/elf/maps.c`, `fifos.c`)
ran on it before the kernel was written, and every rule in the kernel is
a row they measured. The org's own trees read: pax's copy of pelt's FIFO
fixture, wolf-lang's s254 fixtures
(`crates/wolf_driver/tests/fixtures/fs_gaps/{lock,fifo}_rows.lu`), and
lope's pelt hook as `lope init pelt` prints it (§5). QEMU was a black box
too: its trace events and a `perf` profile of the running binary (§5),
no QEMU source. Builds in `px13-ubuntu` and `px57-rust` on kasumi, QEMU
under `taskset -c 0-3`, cores off; nothing installed on any host. No
merge, tag, issue filed or closed; no filming words.

## 2. Inputs, re-derived

| input | found |
|---|---|
| pax trunk | `c0d394ee` (px61), as the contract says |
| `docs/MAP.md` | does not exist at any commit; the VM and the writable tree are described in `kernel/vm/vm.lu`'s and `kernel/tree/tree.lu`'s headers, which stood in for it |
| px60's census | `mremap` 25 unserved (MREMAP_MAYMOVE, 151552 to 299008, in spawn's and std's typechecks and checked runs, `notes/px60/census/*.trace`); ld.lld's file-backed and MAP_SHARED mmaps refused by name |
| px61's 21/22 row | `builtin/c_s_dot_special_file` (busybox `mkfifo`, a background subshell writing into the FIFO, `.` reading it), named apart by R-px61-1 |
| s254's rows | wolf-lang `3c7ac0e6`, in trunk, **not in v0.2.34** (the newest tag): no released wolf builds them |
| pins at the head | wolf 0.2.34 (kernel), pelt `57ffef96`, boreutils `12de639`, lope `bc38867`, aspen `476edee`, yew `77c1083`, lupin 0.1.55: none moved |
| the Linux guest | the suites' `tools/linux-tree` container (kasumi 7.2.8-1-cachyos; CI's runner kernel), a tmpfs root, the same binaries |

## 3. Prediction, scored

| predicted | measured | score |
|---|---|---|
| the page cache exists: kernel/tree's frames are the only copy of a file's bytes, so mappings reuse them; what must be written is records, a fault path, a page-table bit and the edges | so: no cache was written. Records (192 a process), `fault`, the BORROWED and COW leaf bits, `cut_maps`, `inherit`, `drop_all` | right |
| a page still the initramfs's is copied into a frame at its first fault | `tree.page` is `frame_for`, as a first write | right |
| mremap is the first of the four calls wolf's own session reaches, at `conform-run --phase=typecheck` of spawn.lu, the session's 18th command | CI run 39890012763, mpx5-wolf's serial (native BIOS, root): the first census line is `user: wolf pid 30 mremap: 1 served, 0 grown in place, 1 moved`, that command's process; then 1, 2, 2 for spawn's run and std's typecheck and run, as px60's Linux trace counted (8 lines, 12 calls, both roles) | right |
| wolf itself asks no file mapping, MAP_SHARED, flock or FIFO in that session | px60's W3 already held its unserved set to `25 273 334` with no refusal line (a file or shared mapping was refused by name then, flock was -ENOSYS 73); at px62's head no refusal and no new number | right |
| the FIFO alone takes px61's 21/22 row to 22/22 | 22 of 22 per role with no flock (kasumi, `PAX_PELT_CASES=corpus`; CI's full corpus at the final head, §8) | right (the row itself read from px61's note, not predicted) |
| mremap on PAX moves the allocator's mapping, in place only when the pages above are free | wolf's 12 calls all moved (no page above free); the probe's 11 calls: 2 in place, 5 moved | right |
| a failed LOCK_NB conversion drops the held lock | Linux: `a to exclusive with LOCK_NB -11; b unlocked 0; c exclusive 0` | right |
| kmain_console .text +30 KiB native (15 to 60) | +37,696 bytes native at the final tree (+37,280 at `06122b4b`'s), +26,816 release (§7) | right within the range, 23% over the point |
| existing suites unchanged but mpx5-wolf's W3 and mpx5-pelt | also **mpx5-users** (priv.pax recorded PAX's refusal of a FIFO's `mknod`, root's and the user's; two rows and two refusal lines moved, PRIV_LINUX_LINES 19 to 20), and **mpx5-lope**, red at `d6e32446` for a reason none of this lane's calls is (§5) | wrong: two suites missed |
| ld.lld's two refusal lines leave the native M2 session | the dev image's session (§9): `wolf build` then `./hello` with no `refused:` line | right |

Two things the first boots taught, both measured, neither predicted:

- **A waiting FIFO open counts as its end from the start.** The first
  design counted only completed opens and let a waiting reader go on
  when the writers' count of opens moved; on the first boot the reader
  went on before its writer finished opening and read end of file at
  once. Linux keeps the reader's read waiting, so the writer is counted
  while it waits. Now a waiting open adds its end to the buffer's count
  at once and gives it back when a signal ends the wait or its process
  ends (`fifo_abandon`, `take_group_fifo`).
- **In place or moved is each kernel's choice.** PAX grew a
  MAP_NORESERVE range in place (a range freed above it), Linux moved it;
  the probe row asked where it had been. The row now asks only that a
  moved range's old address is gone; the census line still counts which
  PAX did.

## 4. What was built

**kernel/vm** keeps a record for each mapping of a file or of shared
memory: range, inode (held), file offset, protection, shared or private,
and whether a shared one may be made writable. A record's page is filled
at its first touch (`fault`, from the page-fault path and from
kernel/uaccess before a system call copies), never at the call:

- shared: the file's frame itself (`tree.page`), read-write when the
  mapping asks;
- private: the file's frame read-only, COW when the mapping may be
  written; the first write copies it into a frame of the process's own
  (`unshare`); a first write to a page never touched copies at once with
  no tree frame made (`tree.read_page`).

So a private page not yet written shows a later `write(2)` and a written
one does not (Linux's answer; POSIX leaves it open). A page wholly past
the file's end is SIGBUS with BUS_ADRERR (kernel/user's U_BUS word,
kernel/signal). `MAP_SHARED|MAP_ANONYMOUS` and MAP_SHARED of /dev/zero are
records of an inode with no name (`tree.anon`) that goes with its last
record. `munmap`, MAP_FIXED, `mprotect` (which splits a record at the
range's ends and refuses PROT_WRITE on a shared mapping of a descriptor
not open for writing), `madvise` (MADV_DONTNEED unmaps a record's page,
so it is read from the file again) and `brk` know the records. A fork's
child holds every record's file again; `execve` and the end of a
process let them go. A file cut by `ftruncate`, `truncate` or O_TRUNC is
unmapped past its new end in every process first (`cut_maps`, called by
kernel/files' `resize`), copied private pages too, as Linux unmaps them
(measured: `the copy signal 7 code 2`). A process that has made no
record pays nothing per page for them: `map_at` scans only up to the
highest record made since the last `drop_all` (`c338e7c8`; measured
4.335 s against 4.535 s for 40 lope runs, three boots each, every boot
within 2 ms of the others).

**kernel/paging** gives a user leaf two of the three bits the processor
leaves to software: BORROWED (bit 9: the frame is a file's; `free_user`
leaves it, `copy_user` maps it again) and COW (bit 10).

**mremap** takes an old range that is one mapping (inside one record,
inside one reservation, or present anonymous pages with one leaf's
flags; else -EFAULT), rounds both sizes up to pages, answers the same
size at once, unmaps a shrunk tail, grows in place when every page to
the new size is free (zeroed frames, or the reservation's or record's
range extended), and otherwise with MREMAP_MAYMOVE moves the leaves to a
range `pick` chooses: no byte is copied. **msync** checks its flags and
that every page is mapped, and has nothing to write.

**kernel/files**: `mknodat` (and `mknod`) makes a FIFO or a regular file;
a FIFO's open ends are a pipe's ends over one buffer the FIFO keeps while
an end is open (or waits to be), by fifo(7)'s rules (`fifo_open`); `fstat`
of an end answers the FIFO; a listing calls it DT_FIFO. `flock` keeps a
lock in the open file's word 7 (a socket's is its owner, so a socket
keeps none: refused by name, -ENOLCK), finds a conflict among the open
files on the same node, waits like a pipe's read, and drops the lock at
the open file's last close. `map_target` says what a descriptor gives
`mmap`.

**kernel/sched**: the process area grows from 40,960 to 49,152 bytes (the
records after the reservations; `boot/sched.S`), a thread keeps its FIFO
wait word, and `space_of`, `self_owns` and `take_group_fifo` serve vm and
files. And a slot's kernel stack is zeroed when it is made (§5).

## 5. The slow slot: a kernel stack on a frame that held code

`tests/mpx5-lope` went red at `d6e32446` (CI run 39890012763, the
`lope-user` session): the menu's digit, typed 2 s after `gi`, was echoed
before `gi`'s menu. It reproduced on kasumi every time with the head's
kernel and never with the base's, the same images
(`notes/px62/lope-kernels.sh`, `notes/px62/tcg-stack/kasumi-bisect.out`);
with the digit typed 6 s after, it passed. So something in the user's
`gi` took 2 to 6 s, and only at the head.

- `gi` (lope's pelt hook, as `lope init pelt` prints it) runs
  `$(__lope_menu)`: a subshell that runs `lope query --all` twice and a
  pipeline. Sampling QEMU's RIP through a second monitor
  (`tcg-stack/qemu-wrap`, `sample.py`, `window.py`) between `$ gi` and
  the menu: 83 of 141 samples in `paging.copy_user` (the fork's copy),
  2.84 s. Each fork by that subshell (pid 74) copied 1277 frames, as
  every fork by the session's shell did, but took twenty times longer;
  and every one of its system calls, `close` and the -ENOSYS
  `set_robust_list` among them, took about 150 ms, the debug lines that
  timed them included.
- QEMU's own time there (`tcg-stack/qemu-perf`): GLib tree lookups,
  `malloc`/`free`, `bitmap_set_atomic`, `physical_memory_set_dirty_range`,
  `tb_invalidate_phys_range_fast`: its path for a write to a page it
  holds translated code for. Its trace event for that path
  (`memory_notdirty_write_access`, `tcg-stack/qemu-trace`,
  `notdirty-pages.py`, `kasumi-notdirty.out`): **17,126,406 writes to one
  frame, at 0xffffd0000004fed0**, the top page of slot 4's kernel stack,
  and 6,110,393 to that slot's stack page at another time. Every page
  written through the HHDM saw at most 512 such writes: written whole
  once, it is code no more.
- `sched.make_stack` mapped four fresh frames unzeroed. A stack writes
  only the top of its pages, so a frame that had held a program's code
  kept the rest of its old bytes, and under TCG their translations, for
  the thread's life: every push and call went through that path.
- Why only at the head: the bisect (the same debug patch on each tree)
  is slow at `ce3a1133` and fast before it, and slow with nothing of
  px62 but the area's 49,152 bytes; 45,056 or 57,344 are fast, a page of
  padding after the areas leaves it slow. The kernel's size moves which
  frame each later allocation gets; base's frames happened not to land a
  stack on a code page in this session. The substitution timing
  (`notes/px62/lope-ab.sh`) is noisy for the same reason: base's 20
  loops took 8.55 s in one boot and 5.14 s in the next.

**The fix** (`23231b6d`): `make_stack` zeroes each frame before mapping
it. Measured on kasumi: mpx5-lope's two sessions byte-identical with the
2 s pause (`kasumi-bisect.out`), and at the final tree (`lope2`). On a
machine this is a 16 KiB write a thread made; under TCG it is the
difference between a code page and a data page. The latent cost was the
base's too: any slot whose stack landed on a frame that had held code
ran every system call that slowly.

## 6. Rulings asked (recommended, implemented, not decided)

- **R-px62-1, the page-cache shape.** Recommendation: **read-at-fault
  into the tree's own frames**, which are already the page cache (a
  shared mapping maps them, a private one maps them read-only and copies
  at the first write). Against a whole-file read at `mmap`: it copies the
  whole file at the call (a 44.8 MB `libwolf_rt.a` under ld.lld), cannot
  give MAP_SHARED its sharing at all, and a file ftruncated large and
  mapped shared would take every frame at once. Cost named: a page still
  the initramfs's gets a tree frame at its first fault and keeps it while
  the file lives (PAX has no eviction), so mapping a large archive file
  uses the tree's cap; at the cap a private read fault copies instead,
  and a shared one is SIGBUS.
- **R-px62-2, MREMAP_FIXED's errno.** Recommendation: **-EINVAL, refused
  by name** (`MREMAP_FIXED (PAX moves a mapping only to where it
  chooses)`), and MREMAP_DONTUNMAP the same way. EINVAL is what
  `mremap(2)` gives for a flag the call does not take, so a caller sees a
  call that exists and a flag it was refused; -ENOSYS would say there is
  no `mremap` at all, for every call after.

## 7. Witnesses and measurements

**tests/mpx3-maps** (new; four boots on the PR leg): `maps` and `fifos`
as pid 1, root and 1000:1000 through `as`, against the same binaries in a
throwaway Linux container.

| session | lines byte-identical to Linux | PAX's own lines (T2) | refusals (T3) | frames free before / after | mremap census (T5) |
|---|---:|---|---|---|---|
| maps | 90 | `~fixed: … -22`, `~dontunmap: … -22` | MREMAP_FIXED, MREMAP_DONTUNMAP | 59,208 / 59,208 | 11 served, 2 grown in place, 5 moved |
| fifos | 50 | none | none | 59,210 / 59,210 | none |
| maps-user | 90 | as root's | as root's | 59,016 / 59,016 | 11, 2, 5 |
| fifos-user | 50 | none | none | 59,018 / 59,018 | none |

(kasumi, native BIOS, TCG, the final tree, `maps5`; CI: §8.)

**pelt's FIFO row, 22 of 22.** `tests/mpx5-pelt` with
`PAX_PELT_CASES=corpus` on kasumi: every one of the 22 corpus rows and
the whole envelope byte-identical for root and for `pax`, the FIFO row
`builtin/c_s_dot_special_file` among them (`from the fifo`, `fifo: 0`).
The pelt pin did not move.

**s254's rows, as wolf runs them.** `notes/px62/s254-rows.sh` built
wolf-lang trunk `06cff722` (a read-only `git archive`; `wolf 0.2.34+dev.unknown`)
in `px57-rust`, compiled `lock_rows.lu` and `fifo_rows.lu` statically,
and ran each as pid 1 on Linux and on PAX: lock_rows' 19 rows and
fifo_rows' 9 rows are the same on both, no refusal
(`notes/px62/kasumi-s254-rows.out`). These are evidence, not a CI row:
no released wolf has `fs_lock` yet. `fifos.c`'s `s254` rows make the same
system calls and are in CI.

**The allocator's grow path.** On Linux, px60's strace shows each
`mremap(…, 151552, 299008, MREMAP_MAYMOVE)` answered with a new address,
nothing copied. On PAX, `tests/mpx5-wolf`'s W3 now requires the unserved
set `273 334` (no 25) and at least four census lines of wolf's with at
least four calls served; CI's first run read 8 lines, 12 calls (§3).

**Kernel size** (`notes/px62/text-delta.sh`, kmain_console, `size -A`):

| | base `c0d394ee` | `06122b4b`'s tree | final tree | delta, final |
|---|---:|---:|---:|---:|
| native .text | 979,339 | 1,016,619 | 1,017,035 | +37,696 |
| release .text | 852,235 | 872,811 | 879,051 | +26,816 |
| .bss | 4,399,224 | 4,923,512 | 4,923,512 | +524,288 |

## 8. CI

Plants, each a branch never merged, dispatched at `tier=pr` with its
suite alone; each red for its own reason (extracts in `notes/px62/`):

- `px62-plant-maps` (`05176cc3`, a private page written straight into
  the file): run 39890099894, mpx3-maps T1 red, lines 47 and 58
  (`ci-39890099894-plant-maps.log`).
- `px62-plant-pelt` (`78412c13`, a FIFO refused again): run 39890102006,
  mpx5-pelt F1 red for root and `pax`: `mkfifo: pipe: Operation not
  permitted` in the FIFO row (`ci-39890102006-plant-pelt.log`).
- `px62-plant-wolf` (`c822f819`, mremap -ENOSYS): run 39890103914,
  mpx5-wolf W3 red: `unserved calls: 25 273 334` and `0 lines, 0 served`
  (`ci-39890103914-plant-wolf.log`). The census check's served count read
  0 at any head until `53881a76` (an edit had turned its backreferences
  into control bytes); its line count, 0 here, is what the plant turned.

The PR's first run, 39890012763 at `d6e32446`: 41 jobs, two red.
mpx5-wolf W3 by that census parse (`8 lines, 0 served`; fixed
`53881a76`), mpx5-lope by the slow slot (§5; fixed `23231b6d`). Every
other job green, mpx3-maps and mpx5-pelt's corpus among them. The run at
the final head is in the PR.

## 9. The dev image, rebuilt (the orchestrator's addition)

px60's recipe (`notes/px60/build.sh`, `assemble.sh`, `tools/mkdev`) made
lane-local in `notes/px62/dev-iso/`: the base userspace built at the
head's pins on kasumi's CPUs 4-7; px60's static wolf, its runtime and
worker (`user/wolf.sums`) and the native link stack
(`user/wolf-link.sums`) reused from `~/lanes/px60/`, every file's sha256
read twice against the recorded digest before it was copied
(`verify.sh`); mkwolf not run. Booted with 2 GiB under TCG on CPUs 0-3
and typed px60's session plus `cd /bin; ../home/pax; pwd`
(`dev.keys`), checked by `check-dev-session.py`.

| | |
|---|---|
| tree | `23231b6d`'s kernel and recipe (the commits after it are the changelog, notes and the PR) |
| kmain_console.elf | `cec74b3f0a29b894c9cb24bc1b886fb31c3b33411abeb60e9061189f32b1df24`, the same bytes kasumi's own build of the tree made (`kbuild.sh`, `text-delta.sh`) |
| `pax-dev.iso` | `393249a4e462c6b5d1e28ea9f574dbfb1f1f264322fec5a25d7a07a5fbfdece3`, 223,815,680 bytes: read twice on kasumi (`boot.sh`), twice after the copy to `~/pax-playground/pax-dev.iso` on nomad-1 |
| `pax-dev-smoke.iso` | `a95ae58ad35e5b07684cf1e316b7ea38d87ded907a6d2c349c810a7943cd4fee` (kasumi only) |
| px60's image | kept as `~/pax-playground/pax-dev.iso.px60`, `9af2565afda15312fee8c463203d746995d86cab613bb81feed71f0e705e9bb7` as px60 recorded it |
| px60's inputs | wolf `fe45d431…` 15,831,600; worker `06a58258…`; `libwolf_rt.a` `2d2b14c5…` 44,800,284; ld.lld `1217ca75…`; cc `3161aea2…`; crt1/crti/crtn, libc.a `8e69a73c…`, libunwind.a: each read twice against `user/wolf.sums` and `user/wolf-link.sums` (`verify.sh`), `verify-bins` W0 PASS |
| the session | `check-dev-session.py`: PASS (`su pax`, `id`, `whoami`, `wolf --version`, a typed `hello.lu`, `wolf fmt`, `conform-run --phase=typecheck` and `--checked`, `--emit=obj`, `wolf build` and `./hello` (native, the link with no `refused:` line), the release tier's named clang wall, `cd /bin; ../home/pax; pwd` printing `/home/pax`, a clean exit) |

The checker's first run failed on a correct session: Python's
`read_text()` turns the serial log's `\r\r\n` into two lines, so the line
after `$ pwd` read empty; it reads bytes now (`a19968a9`).

The pelt in the image is the head's pin, `57ffef96` (px61's, with sh20's
fork and sh23's autocd, which `../home/pax` exercises), not pelt trunk
`9d4f56cb`: the contract holds the pelt pin still.

## 10. Limits named

- A mapping record per process: 192; past that `mmap` of a file or of
  shared memory is -ENOMEM, refused by name.
- A file or shared mapping in a vfork child is refused by name (-ENOMEM;
  its space is its parent's, and its records would not be).
- MREMAP_FIXED, MREMAP_DONTUNMAP and an old size of 0 of a shared
  mapping are refused by name (-EINVAL).
- No eviction: a page of an initramfs file mapped once keeps a tree frame
  while the file lives.
- MADV_FREE on a record's page is a hint.
- `flock` of a socket, an eventfd, an epoll object, /dev/null or the
  console as a process starts with it is refused by name (-ENOLCK).
- A FIFO end's `/proc/self/fd` link reads `pipe:[N]`, not the FIFO's path.
- A FIFO open waiting in one thread when another thread of its process
  calls `execve` keeps its count until the FIFO's buffer goes.
- `mknod` of a socket's name is refused by name (-EPERM); Linux makes one.
- `/proc/self/maps` is not served (it was not before).
- `F_GETFL` answers no O_LARGEFILE for what `open` made, where Linux on
  x86-64 sets it (pre-existing, every opened file; fdinfo has it since
  px50). A FIFO's end met it, and the probe row was dropped.

## 11. Issues and what to prune

To close (the orchestrator's): pax#127, pax#128, pax#108. To file
(listed, not filed): in pax, `F_GETFL`'s missing O_LARGEFILE (§10). None
in wolf-lang: no wolf limitation was met; s254's rows wait only for a
release that has them.

To prune once merged: on kasumi, `~/lanes/px62/` whole (`s254/` holds a
container-owned `target/`: `podman unshare rm -rf`; `dev/` once the
orchestrator has the image; the debug trees `dbg*`, `ab*`, `td*`, `kb`,
`kc`, `build/`, `wolf-06cff722.tar`); on nomad-1, the plant worktrees
`~/lanes/px62/plant-{maps,pelt,wolf}` and their branches `px62-plant-*`
(local and on origin), then `~/lanes/px62/pax`.
