# px16 — pax at wolf 0.2.26

Contract: px16's, `sprints/pax/16-the-pin-0226/px16-the-pin-0226.md` in
wolffe-lang/wolf (planning trunk, read 2026-10-09). Branch `px16` in
pax, cut from pax trunk `f197e40` (px15 merged). §1–§3 are committed
before either 0.2.26 archive is unpacked and before the first change to
the kernel.

One deliverable: pax pinned to wolf 0.2.26 / lupin 0.1.49 by archive
digest, every suite green, and the workarounds 0.2.26 retires taken out
where they make the code plainer: constants exported as `pub fn` →
qualified `m.K` (wolf-lang#579), fields stored through `as *u64` at
`offset_of` → `p[i].f` (#577), masks written with `%` → `!` (#575), a
dead value after `panic.fail` → `-> never` (#572), each its own commits
with the suites green.

## 1. Forbidden, absolutely

- No Linux kernel, glibc, musl or any other kernel's or libc's source is
  read (ruling #22); the refs clone's sparse checkout is never widened.
  This lane reads wolf's own spec, CHANGELOG and release API, and pax.
- No `region` across a yield, a switch or a return to user mode
  (wolf-lang#611). Nothing here adds one.
- Test binaries for PAX (boreutils, pelt, wolf-hello) are built in the
  Ubuntu 24.04 container on kasumi (`px13-ubuntu`) or on the CI runner,
  never with kasumi's CachyOS glibc.
- The pin comes from the RELEASE ARCHIVES by digest (`tools/fetch-wolf`,
  `tools/fetch-lupin`), never a clone, Homebrew or `~/.local/bin`.
- No `rm` outside `~/lanes/px16/` (nomad-1 and kasumi) and this lane's
  worktree; no `git add -A`; nothing under `~/.claude`; no merge, no
  tag; no `2>/dev/null` on a checkout; no attribution trailers; no
  "seen red" without a run id, sha, path or digest. No build on
  nomad-1 (it only boots the finished ISOs, as the demo folders do).
- kasumi's disk is tight: `CARGO_INCREMENTAL=0` where cargo runs (it
  does not here), one cache and tree set under `~/lanes/px16/`, pruned
  as the lane goes.
- Nothing in pax names any use of the two folders outside it. If the
  tour or shell ISOs change, `~/scratch/wolf/pax-demo/` and
  `~/scratch/wolf/pax-shell/` are refreshed (images, SHA256SUMS, src/,
  every number their notes quote) and both preflights run to GO.
- Strict evidence (wolf-lang#571): every suite run with
  `PAX_REQUIRE_UEFI=1` and `WOLF_PAIRING_REQUIRE_SIBLING=1`, full
  output kept, `SKIP` lines counted.

## 2. Inputs, verified (2026-10-09, from origin)

| input | found |
|---|---|
| wolf 0.2.26 | release **408143286**, tag `v0.2.26` (annotated `fdc73f26`) → wolf-lang **`89dc1394`**, published 2026-10-09T17:48Z, not draft, not prerelease. Digests from the release API: linux x86-64 `05acdc5e…`, linux aarch64 `8b019b64…`, macOS arm64 `8ea7ef3b…`, windows `9cb6958d…`. **As the contract says.** |
| lupin 0.1.49 | release **408028965**, tag `v0.1.49` (annotated `5d14986a`) → wolf-interp **`f516a5f4`**. linux x86-64 `84911a35…`, aarch64 `e1f53d15…`, macOS `ad188d58…`, windows zip `ebff44ab…`, `lupin.exe` `64212006…`. **As the contract says.** |
| 0.2.26 for a downstream | CHANGELOG at `v0.2.26`, "Read this before you bump the pin": ten new prelude names (`fs_copy_chunk`, `os_spawn_fds`, `os_pipe`, `os_chdir`, `os_isatty`, `os_error`, `os_error_text`, `bytes_find`, `bytes_count`; `never` draws no W0304); s217's derived capabilities (the census at pax `94364ad` found no build that changes; pax's kernel manifest reaches no host builtin); `wolf audit --ci` refuses a codeless manifest (pax runs no `wolf audit`); #618 (a `str` call result held past a `region` is E1010); `copy region` (#56); `-> never` (#50), `!` on integers (#51), `m.K` (#579), `p[i].f = v` (#577). As the contract says. Ruling #55 (`extern "c" fn` needs `ffi`) is NOT in 0.2.26 (a lane after r31), so the kernel's manifest does not change here |
| W0304 in pax | `git grep` for a `fn`/`let`/`var`/`const`/`type`/`struct`/`enum` named any of the ten: **none** (the CHANGELOG's grep was at `396c5fb`; re-run at `f197e40`) |
| pax trunk | `f197e40` (px15 merged, PR #18), as the contract says; CI green at `f197e40` (run 37954959790, all 16 jobs): proof 4, census 3, mkw 16, mpx1 26, mpx2-frames 44, mpx2-paging 26, mpx2-interrupts 34, mpx2-sched 32, mpx2-heap 56, mpx3-user 38, mpx3-loader 34 (L8 census `273 334`), mpx3-boreutils 21, mpx3-console 101, mpx3-shell 129, tour 44, macos-run 2 PASS; 0 FAIL, 0 SKIP |
| `kernel/wolf.pin` | wolf **0.2.25** (`9d91f533…`, pin `6710f9e0`), lupin **0.1.48** (`81cfd77a…`) |
| `user/boreutils.pin` | `50d8907` (bu18's trunk; boreutils' own pin wolf 0.2.25). boreutils trunk is still `50d8907` today (bu19 has not merged): **the image keeps boreutils `50d8907`, built with its own 0.2.25**, whatever bu19 does meanwhile. `user/pelt.pin` `dd22a86` (its own pin 0.2.25), likewise unchanged |
| s213's retire list | wolf-lang #628's body (and #605's) names the four issues, not pax's files: **drift** — there is no by-file list in either body (s213's contract asked for one, item 3). The list below is re-derived from pax `f197e40` by grep |
| the demo folders | `~/scratch/wolf/pax-demo/` (`pax-tour.iso` `ad646ec1…`, `pax-tour-b.iso` `3ddf288b…`; built at px15's `8dde82d`, wolf 0.2.25) and `~/scratch/wolf/pax-shell/` (`pax-shell.iso` `6903ece1…`; kernel at `ee36b29`, wolf 0.2.25) |
| kasumi | `/home` 96% (38 GB free); `px13-ubuntu` podman image present; QEMU 11.1.1 (TCG) |

### The workaround sites at `f197e40`

- **#579, a constant exported as a `pub fn`** (19): `console.restart`,
  `refused`, `enotty`; `files.fds`; `heap.slot`, `base`;
  `initramfs.end`; `paging.present`, `writable`, `no_exec`, `user`,
  `user_top`; `sched.elf_prog`, `slots`; `timer.master_base`,
  `slave_base`, `divisor`; `user.programs`, `vector`. Each becomes a
  `pub const` read as `m.K` at its callers, and the fn goes.
- **#577, a field written at its `offset_of`**: the ordinary (plain)
  ones are `frames`' `FrameState` (`get`/`set(offset_of(…))` over
  `rd`/`wr`) and `heap`'s `HeapState` (the same shape): these become
  `p[0].f` / `p[0].f = v` through a `*FrameState` / `*HeapState`.
  **Not retired, by design**: `sched`'s `Thread` records, `user`'s and
  `process`' trampoline-frame words and `gdt`'s TSS `rsp0` halves are
  `read_volatile`/`write_volatile` (the scheduler's rule since px07;
  RSP0 is packed at byte 4 and written as two aligned halves), and
  `[mem.unsafe.raw.5]`'s field store is an ordinary raw access, which
  `[mem.unsafe.volatile]` leaves free to merge, drop or move. Their
  comments stop citing #577 and say why they stay. `interrupts`' comment
  about writing `rip` names a store no code makes; it is reworded.
- **#575, a mask spelled with `%` or as `0xffff… ^ x`**: align-down
  `a - a % P` (uaccess ×3, user, heap, paging ×2, initramfs, files,
  process ×2, elf ×2) and align-up `(a + P - 1) - (a + P - 1) % P`
  (vm, paging, elf) → `a & !(P - 1)`; `apic.phys` `(b - b % 4096) -
  ((b >> 52) << 52)` → a mask; `process` `0xffffffffffffffff ^ x` (×4)
  and `a0 - (a0 & CSIGNAL)` → `!x`, `a0 & !CSIGNAL`. Every operand is
  `u64` and every `P` a power of two. **Not retired**: the 32-bit
  `0xffffffff ^ K` / `0xffffffff - A - B - C` tests in `process` and
  `files` (a 64-bit `!` would also test the high half, which they
  ignore: behaviour would move), and `x % P != 0` alignment tests (a
  test, not a mask).
- **#572, a dead value after a call that never returns**:
  `panic.halt`, `panic.fail` and `pax_halt` become `-> never`; the
  dead `return`, `return 0`, `return false` and match-arm values after
  them go (apic 2, frames 7, heap 13, paging 6, kmain_heap_threads' dead
  `sync.irq_restore(s)`).

## 3. Prediction (committed before either archive is unpacked)

Method: kasumi, per tree a `git archive` under `~/lanes/px16/`, every
suite with the strict env; kernels compared ELF for ELF (sha256, then
every `SHF_ALLOC` section, and `objcopy --strip-debug
--remove-section .note.gnu.build-id` for the cross-release compare:
native binaries carry the compiler's version in DWARF); serial logs
compared raw; user programs built in `px13-ubuntu`.

### Q1. The pin (one commit, both halves)

- `kernel/wolf.pin` → 0.2.26 `05acdc5e…` pin `89dc1394`, lupin 0.1.49
  `84911a35…`. `fetch-wolf` stamps `wolf 0.2.26 (wolfgang, pin
  89dc139)`; `fetch-lupin` `lupin 0.1.49 (…)`.
- **Every suite's assertions hold except tour R1 on all eight legs**:
  `kmain_tour` prints `wolf 0.2.25` as a literal that `tests/tour`
  holds to `kernel/wolf.pin` (px10 met this at 0.2.25). The literal
  moves in its own commit after the pin; the pin's commit alone is red
  in CI on exactly R1's eight legs (36 PASS, 8 FAIL), which is the
  planted red for the gate this lane touches. Falsified by any other
  FAIL, or by R1 passing.
- **No loaded byte of any kernel moves** between 0.2.25 and 0.2.26 at
  the same source (every `SHF_ALLOC` section of every kernel ELF, both
  tiers): nothing pax writes uses a form 0.2.26 changed the lowering
  of; #618's new allocation site is a `str` call result inside a
  `region`, which only the heap kernels open, around no such call. The
  native ELFs all differ (DWARF names the compiler); the release ELFs
  are byte-identical except where `libwolf_rt_none.a`'s debug sections
  ride in (the heap kernels). Falsified by one loaded section moving.
- **lupin 0.1.49 answers `tests/mkw` step 6's `--target` row as 0.1.48
  did** (`unsupported`, naming the freestanding target): mkw 16 PASS.
- **wolf-hello** (`tools/mkwolf-hello`, the pinned wolf's hosted
  runtime) **changes bytes** (s200 serves descriptors 0–2 directly), and
  **its census on PAX stays `273 334`** (set_robust_list, rseq): the
  print is still one `write(1)`. Falsified by a new `-ENOSYS` line.
- Serial logs: byte-identical to 0.2.25's except timing (ticks, run
  counts, the spinners) and tour R1's version line.

### Q2. #579 (m.K)

- Behaviour identical; every suite's PASS count as Q1's.
- Native: every kernel whose code called one of the 19 fns moves in
  `.text` (a call becomes an immediate; the fns go), so the image can
  cross page boundaries: lines printing the image's extent, the
  section ranges, the frames it costs and the addresses of `.data`
  (tour's `image: … KiB`, `paging: text … to …`, `gdt:`/`idt:`
  addresses, the frame counts, ending b's `rip`) may move; nothing
  else does. Release: `.text` shrinks by at most the 19 bodies (LLVM
  already inlined the calls within one object).

### Q3. #577 (p[0].f)

- Behaviour identical; frames' and heap's serial lines identical
  (their counts are the same words read the same way). Native `.text`
  of every kernel linking `frames` or `heap` moves (a call to
  `get`/`set` becomes an access in place); release byte-identical or
  within a few instructions (LLVM inlined `get`/`set` already).
  Falsified by any frames or heap count moving.

### Q4. #575 (!)

- Behaviour identical. `0xffffffffffffffff ^ x` and `!x` both lower as
  xor with all ones: identical code. The `%` forms lower as a
  division's remainder and a subtract on native (moves) and as the same
  `and` on release (LLVM's canonical form): release `.text` unchanged
  for those, native moves.

### Q5. #572 (-> never)

- Behaviour identical (every refusal still prints its `PANIC` line and
  halts: mpx2-frames' and mpx2-heap's fault kernels, the tour's endings).
  Both tiers' `.text` shrink (the dead returns and the code after a
  never-returning call go).

### Q6. The ISOs

- **The tour ISOs change** (Q1's literal; then Q2–Q5's code): both
  rebuilt; on screen only the version line and the image-derived lines
  move (image size, section ranges, frame counts, gdt/idt addresses,
  ending b's `rip`); the countdown, the stages and the endings' text
  do not. PANIC timing on nomad-1 within ±0.5 s of px15's 28.47 s.
- **The shell ISO changes** (the kernel; the initramfs is byte-identical:
  boreutils and pelt keep their own 0.2.25 pins): the boot lines that
  can move are the paging line's table-frame count and `lstar` (an
  address in `boot/user.S`), nothing in the session; boot to the
  prompt on nomad-1 2.0 s ± 0.4; the Linux pane's tree unchanged
  (`c6379482…`).

## §2 corrected after it was committed

- `user/pelt.pin` `dd22a86` pins **wolf 0.2.24** (`501d6d3f…`) and
  wolf-std `2f389a7` in its own `wolf-toolchain.toml`, not 0.2.25 as
  §2 says (`tools/mkpelt`'s first lines on kasumi). The image's pelt is
  the same bytes either way: `1e2535d7…`, px15's.
- §1's line about the two folders outside pax was reworded after the
  prediction's commit (it named their purpose); no prediction moved.

## §3 against what was measured

Gauntlets on kasumi (QEMU 11.1.1 TCG, clang 23.1.1, strict env), one per
stage, each a `git archive` of the stage's commit: `base` `f197e40`
(0.2.25), `pin` `79a262a`, `lit` `3ca8b8f` (the tour's banner), `r579`
`b288e14`, `r577` `7bfe65b`, `r575` `6c60e9f`, `r572` `f1a46f1`. Every
stage after the pin: every suite exit 0, the same PASS counts as
`base`, 0 FAIL, 0 SKIP lines (`notes/px16/kasumi-*.summary`; the
suites with user programs build in `px13-ubuntu` and boot on kasumi, so
each counts its build step there and its boots here: mpx3-loader
32 + 2, mpx3-boreutils 20 + 1, mpx3-console 100 + 1, mpx3-shell
128 + 1, as CI's 34, 21, 101, 129).

| prediction | measured |
|---|---|
| Q1: the pin's stamps | **right**: `wolf 0.2.26 (wolfgang, pin 89dc139)`, `lupin 0.1.49 (wolf-interp, reference interpreter at pin 294d626)`; both archives re-hashed by `fetch-wolf`/`fetch-lupin` on every run, on kasumi and in CI |
| Q1: every suite holds except tour R1 on its eight legs | **right**: kasumi at `79a262a`: tour 36 PASS, 8 FAIL, all R1 (`wolf 0\.2\.26 … not found`), every other suite as `base`. CI run **37977981916** at `79a262a`: the tour job (113980983744) 36 PASS / 8 FAIL, the same eight (`notes/px16/ci-37977981916-tour.txt`); every other job green with trunk's counts. After `3ca8b8f` moved the literal: tour 44 |
| Q1: no loaded byte of any kernel moves; native ELFs differ in DWARF only; release byte-identical but for the heap kernels | **right**: 67 ELFs (`notes/px16/elfcmp-base-pin.txt`): 32 byte-identical (every release kernel but the heap's four, and the stub), 31 identical once stripped of debug and build-id (every native kernel), 4 differing only outside loaded sections (the heap kernels: `.debug_info`/`.debug_str` from `libwolf_rt_none.a`, `110f062a…` at 0.2.25, `11708550…` at 0.2.26). No `SHF_ALLOC` section moved anywhere |
| Q1: lupin 0.1.49 answers mkw step 6 as 0.1.48 | **right**: mkw 16 PASS |
| Q1: wolf-hello changes bytes; its census stays `273 334` | **right**: `a3ada54b…` (11,749,384 bytes) → `53cedb0f…` (12,069,704); L8 `2 system calls PAX lacks (273 334)` on all four legs at every stage |
| Q1: serial logs as 0.2.25's but timing and the version line | **wrong in two places, neither the kernel's code**: 20 of 170 logs differ once CRs and terminal escapes are dropped (`notes/px16/logcmp-base-pin.txt`): timing (run counts, ticks, the lock counters), as predicted; **mpx3-loader's** initramfs and exec lines, because wolf-hello is a bigger file (the module's size and address, its `PT_LOAD` ranges); and **kmain_double_fault's** `limine cr3`, one page apart on both firmwares in a kernel whose loaded bytes did not move (the ELF file around them did: its DWARF; not chased further) |
| Q2 (#579): behaviour identical, every PASS count as Q1's | **right** (`kasumi-r579.summary`) |
| Q2: native `.text` moves; image-derived lines may move, nothing else | **right**: native `.text` −889 bytes on average (−824 to −1,064) in all 30 kernels that link a caller; serial lines that moved are image-derived (frame counts, image, section, gdt/idt and fault addresses, `limine cr3`, the initramfs module's address) or timing, plus one PS/2 session's scancode count (53 → 54, a key's release timing; the session itself byte-identical) (`logcmp-lit-r579.txt`) |
| Q2: release `.text` shrinks by at most the 19 bodies | **wrong**: release `.text` moved by −8,123 to +25,795 bytes (mean +4,014; `elfcmp-lit-r579.txt`). LLVM sees one object per kernel and re-decides inlining when the call graph changes: in `kmain_timer` 281 functions became 273 and `.text` grew 19%, with functions both newly inlined (`boot_info.memmap_base`, `console.com1_vector`, `gdt.set_rsp0`, …) and newly outlined (`apic.start`, `files.statx`, …). A release-tier byte prediction from a source change is not one this lane can make |
| Q3 (#577): behaviour identical; frames' and heap's counts unchanged | **right** (`kasumi-r577.summary`; `logcmp-r579-r577.txt`: frame and heap counts moved only with the image) |
| Q3: native moves; release identical or within a few instructions | **native right, direction unpredicted** (+743 bytes in every kernel: the field accesses are emitted in place where `get`/`set` were calls); **release wrong**, −13,505 to +17,625 (Q2's mechanism) |
| Q4 (#575): behaviour identical | **right** (`kasumi-r575.summary`) |
| Q4: `0xffff… ^ x` and `!x` the same code; the `%` forms move on native only | **native right** (−1,736 bytes on average: a mask instead of a remainder and a subtraction); **release wrong** (−20,546 to +19,670; Q2's mechanism); the `^`-versus-`!` half was not isolated (it shares a commit with the `%` sites in `process`) |
| Q5 (#572): behaviour identical, every refusal's PANIC line as before | **right** (`kasumi-r572.summary`: mpx2-frames' and mpx2-heap's fault kernels, the tour's endings) |
| Q5: both tiers' `.text` shrink | **wrong**: native **grew** +1,121 bytes on average: a call to a `-> never` fn gets an unreachable edge after it (`ud2`: 775 → 819 in native `kmain_frames`), and the native tier deletes nothing behind it; release −23,224 to +22,987 (Q2's mechanism) |
| Q6: the tour ISOs change; only the version line and image-derived lines move on screen; PANIC on nomad-1 within ±0.5 s of 28.47 s | **right**: `pax-tour.iso` `51772fe7…`, `pax-tour-b.iso` `850c4bc2…`; against px15's transcript the version line, the image's physical address (one page up, still 408 KiB), the frame counts (+1) and ending b's `rip` (`0xffffffff80022c05`) moved; section ranges and gdt/idt addresses did not. PANIC at 28.49 s headless (`notes/px16/nomad1-tour-a.times`) and 28.42 s in a pseudo-terminal (`nomad1-tour-a-pty.times`); ending b chosen with keys at 2.0/2.7 s: PANIC at 26.11 s, as px15's (`nomad1-tour-b-keys-pty.times`) |
| Q6: the shell ISO changes, the initramfs does not; the paging line and `lstar` may move; prompt in 2.0 s ± 0.4 | **right, and more so**: `pax-shell.iso` `99b34dec…`; **every boot line is byte-identical to px15's image** (`nomad1-shell-boot.serial.log` against px15's preflight log: no difference, `lstar 0xffffffff8000045c` and `65 table frames` included); the prompt 2.06 s after Enter; both sessions cut as before hash to `1934ecd0…` (24 lines), as px15's; the Linux tree on kasumi unchanged (`c6379482…`) |

### What the measurement says about the next pin

On the native tier a source change moves `.text` by a predictable
sign and size; on the release tier any change to the call graph
re-decides LLVM's inlining across the kernel, so release bytes and
sizes are not predicted from source and a release-tier compare across
a source change is a behaviour compare, never a byte compare.

## 4. Evidence index

- **Archives** (from the release API, re-hashed by `tools/fetch-wolf`
  and `tools/fetch-lupin` on every run): wolf 0.2.26 linux x86-64
  `05acdc5e…` (release 408143286, wolf-lang `89dc1394`; the unpacked
  `wolf` `272e0888…`), lupin 0.1.49 linux x86-64 `84911a35…` (release
  408028965, wolf-interp `f516a5f4`; `lupin` `6d057eb1…`).
  `kernel/wolf.pin` at `79a262a`.
- **The prediction**: `4bac09a` (before either archive was fetched;
  kasumi's first 0.2.26 fetch was the lane's first build check, after
  it).
- **The move table**: §3 above, from `notes/px16/kasumi-*.summary`,
  `elfcmp-*.txt` (every kernel ELF, stage to stage) and `logcmp-*.txt`
  (every serial log, stage to stage, with the shapes of the lines that
  moved).
- **Seen red**: (1) the pin alone, CI run **37977981916** at `79a262a`:
  tour job 113980983744, R1 FAIL on its eight legs
  (`notes/px16/ci-37977981916-tour.txt`), the gate this lane moved the
  literal for; (2) a planted break in the #577 retirement, `30df0d4`
  (`frames.free` stores its count in `hint`): CI run **37983337784**,
  mpx2-frames job 113999058481 F2–F5 and F8 FAIL on kmain_frames, both
  tiers and firmwares (`notes/px16/ci-37983337784-mpx2-frames.txt`);
  mpx2-sched, mpx3-user, mpx3-loader, mpx3-boreutils, mpx3-shell and
  tour red with it; reverted in `decf34d`.
- **CI at the head**: in the PR body (the head is this note's last
  commit).
- **The two folders outside pax**: `~/scratch/wolf/pax-demo/` (ISOs
  `51772fe7…`, `850c4bc2…`; `src/` at `f1a46f1`; its preflight GO,
  29.42 s) and `~/scratch/wolf/pax-shell/` (`99b34dec…`; its preflight
  GO, prompt 2.1 s, the Linux pane's tree matching); every number they
  quote re-measured on nomad-1 on 2026-10-09.

### Drift from the contract, reported

1. s213's retire list is not by file in wolf-lang #628's body (nor
   #605's); it was re-derived here by grep (§2).
2. Two of s213's four shapes are only partly retired, by judgment:
   **#577** only in `frames` (the header's 16 accesses); `heap`'s books
   keep one unsafe site for forty-odd accesses, and every volatile
   field word (`sched`'s records, `user`/`process` frame words, `gdt`'s
   RSP0 halves) stays volatile, because `p[i].f = v` is an ordinary
   access ([mem.unsafe.raw.5] vs [mem.unsafe.volatile]); their comments
   now say so. **#575**: the 32-bit `0xffffffff ^ K` flag tests stay (a
   64-bit `!` would also test the high half).
3. `pax_tour`'s closing line still says "Next: Linux binaries,
   unmodified." (true at px08, done since px12): the tour's text, not
   this lane's; noted for a later tour change.

## 5. Done-when

- Branch `px16` in pax, PR #19 open and unmerged, the five sections in
  its body, commit shas as bullets, a test checklist.
- CI green at the head (the run is in the PR body).
- Worktree and kasumi trees removed, `~/lanes/px16` build outputs pruned,
  no orphans. Close nothing; to close: none (s213's issues were closed
  at r31).
