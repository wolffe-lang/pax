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
