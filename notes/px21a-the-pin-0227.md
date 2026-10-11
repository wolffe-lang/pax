# px21a — pax at wolf 0.2.27; a region across a switch; /dev/tty0 and /dev/console

Contract: px21a's, `sprints/pax/21a-the-pin-0227/` in wolffe-lang/wolf
(read 2026-10-11). Branch `px21a` in pax, cut from pax trunk `638ecaa`
(px22 merged). §1–§3 are committed before either 0.2.27 archive is
fetched or unpacked and before the first change to the kernel.

One deliverable: pax pinned to wolf 0.2.27 / lupin 0.1.50 by archive
digest with the `ffi` capability its C declarations now need; the
freestanding runtime's ambient-region slot saved and restored at every
switch, so a `region` may stay open across one; `/dev/tty0` and
`/dev/console`; three lines of wording.

## 1. Forbidden, absolutely

- No kernel's, libc's or network stack's source is read (ruling #22);
  the refs clone's sparse checkout is never widened. This lane reads
  wolf's own CHANGELOG, release API and PR #646's text, pax, man-pages,
  the uapi headers already named in `docs/SOURCES.md`, QEMU's
  documentation, and black-box runs of Linux programs under strace.
- `kernel/tcp`, `kernel/socket`, `kernel/udp`, `kernel/ip` and the
  `mpx4-*` tests are another lane's: touched only where the pin forces
  it (predicted: nowhere).
- Test binaries for PAX are built in the Ubuntu 24.04 container on
  kasumi (`px13-ubuntu`) or on the CI runner, never with kasumi's own
  glibc.
- The pin comes from the RELEASE ARCHIVES by digest (`tools/fetch-wolf`,
  `tools/fetch-lupin`), never a clone or an installed copy.
- No `rm` outside `~/lanes/px21a/` on any host; no scratch in `/tmp` on
  any host; no `git add -A`; nothing under `~/.claude`; no merge, no
  tag; no `2>/dev/null` on a checkout; no trailers; no "seen red"
  without a run id, sha, path or digest. No build on nomad-1.
- kasumi: `CARGO_INCREMENTAL=0` where cargo runs (it does not here),
  one cache under `~/lanes/px21a/`, trees pruned as the lane goes;
  jobs detached with a pid file and ended by pid.
- `user/boreutils.pin` and `user/pelt.pin` stay as they are.
- Strict evidence (wolf-lang#571): every suite with
  `PAX_REQUIRE_UEFI=1` and `WOLF_PAIRING_REQUIRE_SIBLING=1`, full output
  kept, `SKIP` lines counted; a `wolf build` that exits 2 is a compile
  error.

## 2. Inputs, verified (2026-10-11, from origin and the release API)

| input | found |
|---|---|
| wolf 0.2.27 | release **409367590**, tag `v0.2.27` (annotated `d5f9597a`) → wolf-lang **`0ddda6b7`**, published 2026-10-11T04:12Z. Digests from the release API: linux x86-64 `5e17eebe…`, linux aarch64 `c475e5dc…`, macOS arm64 `ea461a76…`, windows `ac784416…`. As the contract says |
| lupin 0.1.50 | release **409303515**, tag `v0.1.50` (annotated `b30a6d16`) → wolf-interp **`32b970da`**. linux x86-64 `e2867a35…`, aarch64 `a0c0c707…`, macOS `2cbd192d…`, windows zip `420e02c0…`, `lupin.exe` `b37b13bf…`. As the contract says |
| 0.2.27 for a downstream | CHANGELOG at `v0.2.27`, "Read this before you bump the pin". (a) A package that declares C (a bodyless `extern "c" fn`, an `extern "c" let`) needs `capabilities: [ffi]` or is E1504 (s221); it names `kernel/wolf.pkg` and `tests/mkw.d/kernel/wolf.pkg`. (b) The archive carries `std/` beside `wolf`; a freestanding build reads no default std. `tools/fetch-wolf` moves the whole unpacked archive under `.pax-cache/wolf-<version>/` and stages no std of its own, so there is no mixed tree to make. (c) `libwolf_rt_none.a` gains `wolf_rt_ambient_get`/`wolf_rt_ambient_set` (s223, wolf-lang PR #646); a call to either links the archive, which imports `wolf_alloc`, `wolf_free` and `wolf_trap`. (d) Seventeen new prelude names |
| **drift: a third and a fourth manifest** | `user/play/wolf.pkg` (`capabilities: [env, fs]`) declares `extern "c" fn play_kd` (its one assembly routine): a hosted package that declares C, which the CHANGELOG says no downstream has. Predicted E1504 until it lists `ffi` (§3) |
| W0304 in pax | grep for a `fn`/`let`/`var`/`const`/`type`/`struct`/`enum` named any of the seventeen in every `.lu`: **none** |
| wolf-lang#660 in pax | the shape is a call `f(mut outer, s)` under `in r { … }` inside a region block. pax has no `in` block anywhere; its only `region` blocks are `kmain_heap`'s (`work`, `inner`) and `kernel/heapthreads`' (`ra`, `rb`), which pass no region-built string to a callee that keeps it: **not present** |
| wolf-lang#665 in pax | the shape is a callee that sends its argument on a channel. pax has no `channel`, `spawn` or `scope` in any `.lu` (kernel or `user/play`): **not present** |
| pax trunk | `638ecaa` (px22 merged, PR #25); CI green there (run 38110409863 on trunk, 38108167891 on the PR, 20 jobs) |
| `kernel/wolf.pin` | wolf **0.2.26** (`05acdc5e…`, pin `89dc1394`), lupin **0.1.49** (`84911a35…`) |
| the #653 workaround | `kernel/net/net.lu`: `const WANT: u64 = 0x100000020` (a literal for `virtio.F_VERSION_1 \| F_MAC`). wolf-lang#653 is open and 0.2.27's CHANGELOG does not name it |
| the ambient-slot rule | "no `region` across a yield, a switch or a return to user mode" in `kernel/README.md`, 10 module headers and `boot/*.S` comments, and the inherit lists of `notes/px09`–`px22`; `tests/mpx2-heap` H11 reports where A's List landed and does not assert it |
| every switch | `kernel/sched`'s `run_next` is the one place a thread is switched in (`preempt`, `switched`, `sleep_current`, `block_input`, `kick`, `end_with`, `vfork_wait`, `block_pipe_until`, `wait_child` all end in it), with IF clear |
| which kernels link the scheduler | `kernel/interrupts` imports `kernel/sched`, so every kernel but `kmain_tour_text` links it (29 of 30) |
| `/dev` today | `kernel/files`: `/dev/stdin`, `stdout`, `stderr`, `null`. The console is descriptors 0–2; `KIOCSOUND`/`KDMKTONE` are answered on a console descriptor (px18) |
| **drift: Ubuntu's `beep` is a dynamic program** | `notes/px18/beep.strace` shows it opening `/etc/ld.so.cache` and `libc.so.6`: it has a `PT_INTERP`, and `kernel/elf` refuses `PT_INTERP` and `ET_DYN` by name (px10). The packaged binary cannot run on PAX until PAX has a dynamic loader, which is not this lane. What this lane can run is §3's Q4 |
| the wording | `docs/CENSUS.md` lines 56 and 640, `docs/SOURCES.md` line 77; the same two words in four comments under `tools/census/` (`inside/pins.sh` ×2, `inside/stage.sh`, `workloads/lobo.sh`). `stage.sh`'s path argument is lobo's own directory name and is not prose |
| kasumi | `/home` 95% (52 GB free); `px13-ubuntu` present; QEMU 11.1.1 (TCG; no `/dev/kvm`) |

## 3. Prediction (committed before either archive is fetched)

Method: kasumi, per stage a `git archive` under `~/lanes/px21a/`, every
suite with the strict env; kernels compared ELF for ELF (sha256, then
every `SHF_ALLOC` section; `objcopy --strip-debug --remove-section
.note.gnu.build-id` first, since native objects name the compiler in
DWARF); serial logs compared with addresses and counts masked. On the
release tier a source change is compared by behaviour, never bytes
(px16).

### Q1. The pin (the two archives and the `ffi` lines, one commit)

- **Without the lines nothing builds**: every kernel, both `tests/mkw.d`
  kernels and `user/play` are E1504 (`wolf build` exit 2). With
  `capabilities: [ffi]` in `kernel/wolf.pkg`, `tests/mkw.d/kernel/wolf.pkg`
  and `user/play/wolf.pkg` everything builds. Falsified if `user/play`
  builds without it.
- **Which kernels' loaded bytes move at the pin: only those that link
  `libwolf_rt_none.a`** (the kernels beside which wolf writes
  `NAME.rt-none.a`: `kmain_heap` and `kmain_heap_threads` at px16; any
  of `kmain_net`, `kmain_sockets` and the heap fault kernels that
  allocate). The archive is one member, so the linker takes the pair
  with it: `.text` grows by two small functions (under 64 bytes) and
  what follows them shifts. **Every other kernel: no `SHF_ALLOC` byte
  moves on either tier** — the compiler's freestanding output for a
  program that names none of the new forms is unchanged, and the `ffi`
  line is a manifest fact. Falsified by one loaded section moving in a
  kernel with no archive, or by an archive kernel moving by more than
  the pair.
- **Verdicts: all unchanged except tour R1 on its eight legs**, which
  holds the banner's `wolf 0.2.26` to `kernel/wolf.pin` (as at px10 and
  px16). The literal moves in the next commit; the two are pushed
  together, so CI never sees the pin alone.
- `tests/mkw` step 6: lupin 0.1.50 answers the `--target` row as 0.1.49
  did; 16 PASS.
- `wolf-hello` (the pinned wolf's hosted runtime) changes bytes; its
  census on PAX stays `273 334`. Falsified by a new `-ENOSYS` number
  (0.2.27's runtime gained signal and terminal code; the claim is that
  a program that only prints calls none of it).
- wolf-lang#653 is **not fixed**: `const WANT: u64 = virtio.F_VERSION_1
  | F_MAC` is still refused at comptime. The literal stays, citing the
  issue.

### Q2. The ambient slot adopted

- The change: a word `amb` in each thread's record; in `run_next`, when
  the thread changes, `wolf_rt_ambient_get()` into the outgoing record
  and `wolf_rt_ambient_set()` from the incoming one (0, the root, for a
  thread that has not run); the pair reached through `kernel/heap`,
  which already supplies the runtime's hooks.
- **Loaded bytes: all 29 kernels that link the scheduler move, on both
  tiers**, because each now links `kernel/heap` and the runtime archive
  where most linked neither. Native `.text` grows by the heap module and
  the archive (predicted +16 to +96 KiB); image-derived lines move (the
  image's size, section ranges, frame counts, table-frame counts,
  addresses in faults). `kmain_tour_text` does not move. No verdict
  moves.
- **H11 flips**: `region ra 1008 bytes, region rb 0 bytes`, "the List
  landed in ra", on both tiers, BIOS and UEFI (it reads `ra 0, rb 1008`
  today). H11 becomes an assertion.
- **Cost per switch**: zero when the same thread keeps the CPU (the
  save and restore sit under `s != from`). On a real switch the added
  path is straight-line: predicted **40 to 100 executed instructions on
  the native tier** (two record accesses and four calls, none inlined)
  and **6 to 30 on the release tier**. Measured in the kernel: a
  ping-pong of yields timed with RDTSC under QEMU's `-icount shift=0`
  (one instruction per virtual nanosecond), with and without the two
  lines. Falsified outside those ranges.
- **Syscall entry and exit need no save**: a return to ring 3 switches
  no thread, and a handler that returns has left every region it
  entered, so the slot is the root again. What stays forbidden is a
  region left open where a system call gives up its kernel stack for
  good (the waits that rewind the `syscall`, `sleep_current`, exit,
  `execve`): the code after the wait never runs, so the region's exit
  would not either. Interrupt handlers still allocate nothing.
- **The witness** (`kmain_heap_threads`, new rows in `tests/mpx2-heap`):
  a region held across a preemption (two threads that never yield, each
  allocating in its own region before and after the timer takes the
  CPU from it) and across a blocking wait (the main thread blocked in
  `wait_all` inside a region while another thread sleeps inside its
  own): every region's byte count equals a single-threaded control's,
  and the heap's ledger ends at 0 live blocks with allocs = frees, on
  both tiers. With the restore removed (the planted break) H11 and the
  new rows are red within the `mpx2-heap` job, minutes not tens.

### Q3. `/dev/tty0` and `/dev/console`

- Both open (any access mode), answer the console's ioctls (termios,
  `TIOCGWINSZ`, `KIOCSOUND`, `KDMKTONE`) and `write` to the console;
  `fstat` says a character device, 4:0 and 5:1 (to be confirmed against
  a Linux `stat`). `/dev` lists them. `mpx3-speaker` gains rows; no
  other suite's verdicts move (`ls /dev` is in no session).

### Q4. `beep`

- The packaged binary is dynamic and is refused by name (`PT_INTERP`),
  as §2 says. This lane runs **the same program, statically linked**:
  Ubuntu's `beep` source package built in CI with `-static`, not
  committed. Predicted: it opens `/dev/tty0` or `/dev/console`
  write-only, asks `KIOCSOUND`, and its tone on PAX measures within
  0.5% of the frequency asked (px18's `play` bound: 0.28%), on both
  tiers. If the static build needs a system call PAX lacks, that is
  named and the witness falls back to a static program making the
  calls the strace records.

### Q5. The wording

- Three lines in `docs/` and four comments in `tools/census/` say
  "lobo's live site" where they named the site otherwise; no test reads
  them.

## §2 and §3 corrected after they were committed

- Three manifests declare C, not four: `kernel/wolf.pkg`,
  `tests/mkw.d/kernel/wolf.pkg` and `user/play/wolf.pkg`. The third is
  the one wolf's CHANGELOG does not name ("nothing hosted downstream
  declares C this way"): `user/play` is hosted and declares `play_kd`.
- Q4 says the beep source comes through `apt-get source`. It comes
  from Launchpad's archive of the source package, the two files by
  digest (`tools/mkbeep`), so no host's apt configuration is involved.
- §2's "29 of 30 kernels link the scheduler" counted imports. wolf
  compiles every module of the package into each kernel, so all 30
  link `kernel/sched` (and now `kernel/heap` and the archive).

## §3 against what was measured

Gauntlets on kasumi (QEMU 11.1.1 TCG, clang 23.1.1, strict env), each a
`git archive` of its commit: `base` `638ecaa` (wolf 0.2.26), `pin`
`88cb343` (the pin, the `ffi` lines and the banner), `head` `76c4d28`
(everything but the two test commits after it, which change no kernel:
`notes/px21a/kasumi-*.summary`). Every suite exit 0 at each stage, 0
FAIL, 0 SKIP lines; `base` and `pin` have the same PASS count in every
suite; `head` differs in two: mpx2-heap 56 → 64 (H12 and H13, four
legs each) and mpx3-speaker 24 → 40 (the beep session's four rows on
four legs).

| prediction | measured |
|---|---|
| Q1: without the `ffi` lines nothing builds; `user/play` needs one too | **right**: E1504, `wolf build` exit 2, for `kernel/kmain.lu`, `kernel/kmain_sched.lu`, `tests/mkw.d/kernel/kmain.lu` and `user/play` with the lines taken out (`notes/px21a/e1504.txt`) |
| Q1: only the kernels that link the runtime archive move at the pin, by the pair (under 64 bytes) | **right**: 77 ELFs (`elfcmp-base-pin.txt`): 35 byte-identical, 34 identical once stripped of debug and build-id (the native ones), 8 with loaded bytes moved. Four are `kmain_heap` and `kmain_heap_threads` on both tiers, `.text` +16 bytes each (the archive `11708550…` → `46544be6…`); the heap's fault kernels, `kmain_net` and `kmain_sockets` link no archive and do not move. The other four are the tour's two kernels on both tiers: one loaded byte each, the banner's `6` → `7` (`cmp -l` on the loaded images) |
| Q1: every verdict unchanged; tour R1 red at the pin alone | **verdicts right** (same PASS count in all 22 rows of the two summaries). **R1's red was not taken**: the banner moved in the next commit and the two were pushed and run together |
| Q1: mkw step 6 as before | **right**: 16 PASS, `lupin 0.1.50 (wolf-interp, reference interpreter at pin 294d626)` |
| Q1: wolf-hello changes bytes; its census stays `273 334` | **right**: `53cedb0f…` (12,069,704 bytes) → `fc861bf0…` (12,753,360); L8 `2 system calls PAX lacks (273 334)` on all four legs |
| Q1: wolf-lang#653 not fixed | **right**: `const WANT: u64 = virtio.F_VERSION_1 \| F_MAC` is still "an unresolved name at comptime", exit 4, both tiers (`wolf-lang-653-at-0.2.27.txt`). The literal stays |
| Q2: 29 kernels' loaded bytes move; native `.text` +16 to +96 KiB | **wrong twice**: all 30 move (70 of 77 ELFs; the seven that do not are M-KW's frozen kernels and the stub), and native `.text` grows by 158,782 bytes on average (+1,456 in the two kernels that already linked the archive, up to +171,107): the freestanding runtime is about 165 KiB of code and every kernel now carries it, used or not. Release: −21,264 to +179,611 (`elfcmp-pin-head.txt`) |
| Q2: image-derived lines move, no verdict | **right**: 190 of 231 logs differ; the shapes that moved are frame counts, table-frame counts, the image's and the initramfs module's addresses, section ranges, `gdt`/`idt` addresses, fault addresses, and timing (`logcmp-pin-head.txt`) |
| Q2: H11 reads `ra 1008, rb 0` | **right**, all four legs, kasumi TCG, CI and hasu KVM |
| Q2: 40 to 100 instructions a switch on native, 6 to 30 on release | **right**: under `-icount shift=0` (two RDTSC reads in a row are 9 ticks apart on native, 7 on release; two runs of each build give one number) 4,000 yields cost 10,436,976 instructions with the save and restore and 10,080,709 without on native, **89.1 a switch**; 2,861,978 and 2,769,901 on release, **23.0 a switch** (`bench-at-head.txt`, `bench-without-the-save-and-restore.txt`). The release figure is one tree's: the tree at the witness's commit measured 2,809,936 with them (`bench-at-the-witness-commit.txt`; its run without them was not kept), so LLVM's inlining around the two lines moves the figure by ten instructions or more |
| Q2: the witness holds on both tiers; the plant is red within minutes | **right**: H12 `C 4032 bytes, D 4032, control 4032`, each seeing the other run three times; H13 `main 2016, E 2016, control 2016`; the ledger `24 allocs = 24 frees, live 0`. With the restore removed (`241a849`): CI run **38113305491**, job 114393153763 (mpx2-heap) red in 5 min 53 s, H11, H12 and H13 FAIL on all four legs (`ra 0, rb 1008`; `C 1008, D 6048`; `E 1008`), and the other 19 jobs green (`ci-38113305491-mpx2-heap-plant-241a849.txt`) |
| Q3: both nodes open, answer the console's ioctls and take writes; 4:0 and 5:1 | **right as far as tested**: `beep` opens each write-only and its KIOCSOUND is answered; pelt's `echo … > /dev/tty0` and `> /dev/console` reach the console (K1). 4:0 and 5:1 are Linux's (`stat` on kasumi). **Not predicted**: beep also asks `EVIOCGSND` of the device, which PAX reported as a refused terminal ioctl (K5 red on kasumi's first run); a Linux terminal answers that plain `ENOTTY` (measured on a pty), and so does `kernel/console` now |
| Q4: the static beep runs; pitch within 0.5% | **right**: 440 Hz and 880 Hz, kernel counts 2711 and 1355, each held 31 ticks (310 ms for the 300 asked: beep's own sleep, rounded up to the tick); worst pitch error 0.214% on kasumi, 0.252% on the CI runner, 0.248% under KVM on hasu. No system call PAX lacks beyond glibc's two (273, 334) |
| Q5 | **done**; `tests/census` C2 still regenerates `docs/CENSUS.md` byte for byte |

### What was not verified

- `fstat` of the two nodes (4:0, 5:1, mode 0620, inodes 5 and 6) and
  their names in `getdents64` of `/dev` are written and run by no
  test: beep's `newfstatat` proves only that the call succeeds.
- The packaged `beep` binary itself never ran on PAX (it cannot: no
  dynamic loader). What ran is its source, unmodified, linked static.
- No Linux reference run of `beep` reaching a real console was taken
  (a container has no `/dev/tty0`); its calls are known from the
  strace of its refusals and from what it did on PAX.
- The rule's second half (no region left open where a system call
  gives up its stack) is stated, not checked by the kernel.
- The two folders of prebuilt images outside this repository were not
  refreshed; every kernel's bytes moved, so they are older builds.
- kasumi's `head` gauntlet is at `76c4d28`; the two commits after it
  (`tests/mpx2-heap` making `build/`, the beep session's two writes)
  ran on kasumi as `tests/mpx3-speaker --images` only
  (`kasumi-72a746b-mpx3-speaker-beep.txt`) and in CI.

## 4. Evidence index

- **Archives** (release API; re-hashed by `tools/fetch-wolf` and
  `tools/fetch-lupin` on every run): wolf 0.2.27 linux x86-64
  `5e17eebe…` (release 409367590, wolf-lang `0ddda6b7`; the unpacked
  `wolf` `6f5713a2…`, `libwolf_rt_none.a` `46544be6…`, `std/STD-REV`
  `87ba1620`), lupin 0.1.50 `e2867a35…` (release 409303515,
  wolf-interp `32b970da`).
- **The prediction**: `8797483`, pushed before the first fetch of
  either archive (kasumi's first 0.2.27 fetch followed it).
- **The comparison table**: §3, from `notes/px21a/kasumi-base.summary`,
  `kasumi-pin.summary`, `kasumi-head-76c4d28.summary`,
  `elfcmp-base-pin.txt`, `elfcmp-pin-head.txt`, `logcmp-base-pin.txt`,
  `logcmp-pin-head.txt`.
- **The region across a switch**: `kernel/heapthreads`,
  `tests/mpx2-heap` H11 to H13;
  `notes/px21a/kasumi-head-mpx2-heap-H11-H13.txt` (12 rows, TCG),
  `hasu-kvm-k1-76c4d28.log` (three rounds under KVM).
- **The cost**: `bench-at-head.txt` against
  `bench-without-the-save-and-restore.txt` (the same tree with
  `run_next`'s two lines and the import taken out).
- **beep's pitch**: `kasumi-72a746b-mpx3-speaker-beep.txt` (K1, K7,
  K4, K5 on four legs), the hasu log's K7 rows, CI job 114393153800
  (in run 38113305491) and the run at the head. Its source's digests
  are in `tools/mkbeep`; the packaged binary's facts in
  `beep-default.strace`, `beep-console.strace` and `docs/SOURCES.md`.
- **Boots**: kasumi TCG 229 at `base`, 229 at `pin`, 233 at `head`
  (the suites' own run lists; mpx2-frames and the proof keep none);
  hasu KVM (QEMU 11.1.0, the combined OVMF.fd, i7-12700KF): three
  rounds of mpx2-heap (24), mpx2-sched (8) and mpx3-speaker (9), 123
  boots, every round rc 0, every boot `accel=kvm`; one more round of
  mpx3-speaker (9), mpx3-user (12), mpx3-console (20) and mpx3-shell
  (28) at `72a746b`, 69 boots, rc 0 (`hasu-kvm-k2-72a746b.log`; the
  last two first exited 2 for want of their `linux/` reference trees,
  which had not been sent, and passed with them). 192 KVM boots in
  all. CI: the PR body names the run.
- **Seen red**: the planted break `241a849` (the restore removed), CI
  run **38113305491**, job 114393153763, red in 5 min 53 s; reverted in
  `dd2d1fd`. And on kasumi before CI, the same numbers
  (`kasumi-plant-rows.txt`).
- **CI at the head**: in the PR body (the head is this note's commit).

### Drift from the contract, reported

1. Ubuntu's packaged `beep` is a PIE with a `PT_INTERP`; PAX loads
   static `ET_EXEC` only. The witness is its source package, built
   static by `tools/mkbeep` in CI and never committed.
2. `user/play/wolf.pkg` needed `ffi` too; wolf's CHANGELOG names two
   pax manifests.
3. Four comments under `tools/census/` carried the same two words as
   the three lines named; they are reworded with them.
4. Adopting the pair costs every kernel about 165 KiB of runtime code
   (the archive is one member and the pair lives in it): the price of
   ruling #58's option A that s223's PR named, now with its size.

## 5. Done-when

- Branch `px21a` in pax, PR #26 open and unmerged, the five sections
  in its body, commit shas as bullets, a test checklist.
- CI green at the head (the run is in the PR body).
- kasumi's and hasu's trees under `~/lanes/px21a/` removed, build
  outputs pruned, no process left. Close nothing; what to close is in
  the PR body.
