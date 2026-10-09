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
- No word implying filming anywhere in pax. If the tour or shell ISOs
  change, `~/scratch/wolf/pax-demo/` and `~/scratch/wolf/pax-shell/`
  are refreshed (images, SHA256SUMS, src/, every quoted number in their
  SHOTLISTs) and both preflights run to GO.
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
