# px09 — user mode (PAX P3's first step)

Contract: `sprints/pax/09-user-mode/px09-user-mode.md` in wolffe-lang/wolf
(wolffe-lang/wolf trunk `c5fd1e3` at the time of reading; the contract at wolffe-lang/wolf `a3ccbb7`, its only
commit, 2026-10-07). Branch `px09` off pax
`94364ad`. This note is committed whole, §1–§3 first, before any change;
§4 and §5 are filled in as the evidence lands.

## 1. Forbidden, absolutely

- No Linux kernel, glibc, musl or any other kernel's or libc's source is
  read (ruling #22). Used: the syscall table
  `arch/x86/entry/syscalls/syscall_64.tbl` (write 1, getpid 39, exit 60)
  and `include/uapi/asm-generic/errno-base.h` / `errno.h` (EBADF 9,
  EFAULT 14, ENOSYS 38) from the sparse refs clone, never widened; the
  Intel SDM and AMD64 APM; the System V x86-64 psABI (A.2.1, the kernel
  calling convention); man-pages section 2 (`write(2)`, `_exit(2)`,
  `syscall(2)`).
- No `region` is held open across a yield, a switch or a return to user
  mode (wolf-lang#611): this lane allocates nothing from wolf's heap.
- No ELF loader: the user programs are flat, position-independent
  assembly blobs the kernel embeds and copies into frames. The loader and
  the initramfs are px10's.
- px06 (pax#10) and px08 (pax#11): their files are not touched where it
  can be avoided; the unavoidable shared ones are `.github/workflows/ci.yml`
  (a new job), `docs/SOURCES.md` and `kernel/README.md` (appended
  sections) and `kernel/interrupts/interrupts.lu` (a routing branch away
  from px06's hunk). Rebased on whichever merges first.
- No `rm` outside `~/lanes/px09/` and this lane's worktrees; no deletion in
  a tree this lane did not create; no `git add -A`; nothing under
  `~/.claude`; no merge, tag or release; no attribution trailers.
- No "seen red" without a run id, sha, path or digest. Gate results under
  the strict env (`PAX_REQUIRE_UEFI=1`, `WOLF_PAIRING_REQUIRE_SIBLING=1`,
  lupin present for mkw).
- kasumi: `bash -c`, `scp`, `setsid` with recorded pids, done-files,
  `command ls`, `target/`/`build/` pruned. hasu: `nix-shell -p qemu` for
  KVM. Nothing installed anywhere; nothing built on nomad-1.

## 2. Inputs, verified (2026-10-07)

| input | found |
|---|---|
| pax trunk | `94364ad` (px07), as the contract says; px06 (pax#10) and px08 (pax#11) open, unmerged |
| wolf | 0.2.24 = wolf-lang `294d626d`, archive `wolf-0.2.24-x86_64-unknown-linux-gnu.tar.gz` sha256 `501d6d3f…` (release asset digest), `kernel/wolf.pin` agrees |
| `[abi.interrupt]` | no interrupt calling convention (K7 = B): trampolines in assembly call `pax_interrupt(f) -> *Frame` (kw10, px07) |
| inline `asm` (kw13) | **not available**: wolf-lang#526 open ("inline asm has a grammar and no meaning; unsupported on every machine"). Every privileged instruction (WRMSR, STAC/CLAC, SYSRET, IRETQ to ring 3) is an assembly routine on the package's `asm` roster |
| MSRs | `boot/cpu.S` reads/writes IA32_EFER and reads IA32_APIC_BASE only; STAR/LSTAR/FMASK need a general RDMSR/WRMSR pair (added there) |
| GDT | **already user-ready** (kw10): 0x18 user data DPL 3, 0x20 user code DPL 3 (L), in SYSRET's order (STAR[63:48] = 0x10 gives SS 0x1b, CS 0x23) |
| TSS | RSP0 = 0 (px07's note), IST1 for #DF; I/O map base 104 (no port access from ring 3) |
| paging | upper-level entries are made supervisor (`TABLE = P \| RW`): a user page needs U/S at every level, so the user half's tables need their own flags |
| scheduler | one CPU, frames saved on the thread's own stack, `pax_isr_common` resumes the frame `pax_interrupt` returns; one address space (CR3 never changes after `paging.start`) |
| wolf-lang#598 | fixed on wolf-lang trunk by s214 (`85de08ff`), **not** in 0.2.24: px07's rule stands (switched state in volatile storage words, never module `var`s) |
| wolf-lang#611 | open: no `region` across a switch (this lane uses none) |
| CPUs | CI: QEMU 8.2 TCG `-cpu max`; kasumi: QEMU 11.1.1 TCG `-cpu max` (no /dev/kvm since 10-04); hasu: KVM `-cpu max` on an i7-12700KF whose `/proc/cpuinfo` lists `smep` and `smap` |

**Drift, reported and not absorbed:**

1. **A bad pointer to `write` returns `-EFAULT`; it does not kill.** The
   contract's item 4 lists "a bad pointer to `write`" among the cases that
   kill the program. Linux does not: `write(2)` returns `-1`/`EFAULT`
   ("buf is outside your accessible address space"), and ruling #22 makes
   PAX ABI-compatible. This lane follows Linux: the kernel refuses the
   call by name in its log, returns `-14`, and the program decides (the
   test program exits 14 when all three of its bad pointers came back
   `-14`). The two real faults (a user page fault, a privileged
   instruction) kill by name. If the orchestrator wants the kill anyway it
   is a one-line change in `user.write`, and the drift is stated in the PR.
2. The user segments the contract lists as a piece to build already exist
   (kw10 wrote them for this lane); what is new is STAR/LSTAR/FMASK,
   EFER.SCE and RSP0.
3. `exit` (60) only, as the contract says; `exit_group` (231), which
   M-PX3's census needs, answers `-ENOSYS` here and is px10's.

## 3. Prediction (committed before the first change)

**The pieces.**

| piece | where | shape |
|---|---|---|
| user GDT segments | `kernel/gdt` (kw10, unchanged) | CS 0x23, SS 0x1b |
| TSS RSP0 per thread | `kernel/gdt.set_rsp0`, called from `sched.run_next` | the switched-in thread's `stack_hi`, written as two aligned u32 halves (RSP0 sits at TSS offset 4; a misaligned u64 store is a UB row, ruling #36) |
| syscall's kernel stack | `boot/user.S` `pax_syscall_state` word 0, written beside RSP0 | `syscall` switches no stack (SDM vol. 3A §5.8.8): the entry saves the user RSP in word 1 and loads word 0 |
| STAR/LSTAR/FMASK, EFER.SCE | `kernel/user.start` through `cpu.S`'s new `pax_rdmsr`/`pax_wrmsr` | STAR = 0x0010_0008 << 32; LSTAR = `pax_syscall_entry`; FMASK clears TF, IF, DF, NT, AC (0x44700) |
| the entry trampoline | `boot/user.S` `pax_syscall_entry` | builds the 22-word frame (SS 0x1b, user RSP, R11 as RFLAGS, CS 0x23, RCX as RIP, error 0, vector 0x100 = PAX_SYSCALL, a number the CPU never raises) and joins `pax_isr_common`; dispatch in wolf (`user.syscall`) |
| the return | `boot/isr.S` `pax_isr_common`'s tail | a resumed frame with vector 0x100, CS 0x23 and a RIP below 0x7ffffffff000 leaves by `sysretq` (RCX = RIP, R11 = RFLAGS, RSP = the user RSP, as Linux's callers see); every other frame by `iretq` |
| SMEP/SMAP | `kernel/user.start` | CR4.SMEP (bit 20) and CR4.SMAP (bit 21) set when CPUID.(7,0):EBX bits 7 and 20 say so; the kernel's one read of user bytes (`write`'s copy) brackets each read with STAC/CLAC in `pax_peek_user` |
| the user half | `kernel/paging.map_user`, `paging.user_ok`, `paging.free_user` | a fresh PML4 per process, entries 256–511 copied from the kernel's (shared tables), 0–255 private; upper levels P \| RW \| US; code at 0x400000 r-x US, stack 16 KiB below 0x7ffffffff000 rw- NX US, the page below it (0x7fffffffa000) never mapped: the guard |
| per-thread CR3 | `sched`: Thread gains `cr3` and `prog` (72 → 88 bytes) | `run_next` loads the thread's CR3 (the kernel's for a kernel thread) when it differs |
| the programs | `user/programs.S`, in the kernel's .rodata (so never executable in ring 0) | flat PIC blobs: `hello` (write, a computed CPL digit on its own stack, two unknown syscalls), the fault cases, `badptr`, two spinners, and `after` (the hello blob under another name) |
| entering ring 3 | `boot/user.S` `pax_enter_user(rip, rsp)` from a kernel thread body (`user.pax_user_thread`) | an `iretq` frame (SS 0x1b, RSP, RFLAGS 0x202, CS 0x23, RIP), every general register zeroed first |
| exit and kill | `sched.end_current(f)` from the handler (not `sched.exit`, which switches by `pax_switch` and is for thread context); the address space freed by `reap` with the stack (thread context, IF clear, as px07 reaps) | `user: <name> pid <id> exit <code>` / `user: <name> pid <id> killed: <exception> vector <v> error 0x… rip 0x…[ cr2 0x…]` |

**The numbers.**

- **P1.** Each one-page process costs **12 frames** (PML4 1; PDPT, PD and
  PT two each, one chain for 0x400000 and one for the stack; code 1;
  stack 4), plus its kernel thread's 4: free frames after each `wait_all`
  return exactly to the count before the process was made.
- **P2.** `hello` prints `hello from ring 3: cpl 3` (the digit computed
  from CS in ring 3 and stored on the user stack), its `write` returns the
  length, both unknown numbers (39 and 500) come back `-38`, and it exits
  0.
- **P3.** The faults: the null read is `page fault` error 0x4 cr2 0; the
  read of the kernel image error 0x5; the write to its own text error 0x7;
  the push into the guard error 0x6 with cr2 in 0x7fffffffa000–…afff; the
  `hlt` is `general protection` error 0. Each kills the program by name
  and the next program runs.
- **P4.** `badptr`'s three writes (a kernel-half pointer, an unmapped user
  pointer, a mapped buffer whose length runs into the unmapped page) each
  return -14 and print nothing: it exits 14.
- **P5.** Two spinners run at once and each is switched in at least twice
  (preempted in ring 3 and resumed by `iretq`), both exit 0: RSP0 and CR3
  follow the thread.
- **P6.** SMEP and SMAP are on in all three places (QEMU 8.2 TCG and 11.1
  TCG `-cpu max` emulate both; KVM passes the host's). A kernel that reads
  a user byte without STAC panics `page fault` error 0x1 with cr2 the user
  address; one that jumps into a user page panics error 0x11.
- **P7.** Every existing suite is unchanged in what it asserts (the
  scheduler's records grow by two words; the trampoline's tail gains one
  compare before `iretq`, and mpx2-sched S0's "the last instruction is
  iretq" still holds because the sysret tail is a separate block after
  it).

**The first boot, and what fails first.** The first build fails on a
wolf 0.2.24 refusal I have not met before (a guess at the shape: a cast
or a constant in the user module). Once it builds, the first boot does
not reach the hello line: the first failure is in the return to ring 3 —
a `#GP` on `sysretq`/`iretq` from a selector or RFLAGS bit I got wrong,
or a `#PF` with error 0x15 if a user-half table is supervisor. The
falsifier is the first boot's serial log, kept in §4 either way.

### §3 against what was measured

| predicted | measured |
|---|---|
| P1: 12 frames a process + 4 for its kernel stack, all back after `wait_all` | as predicted: every batch `A / A - 16n / A` on every leg, three hosts (e.g. `65047 / 65031 / 65047`, the pair `65047 / 65015 / 65047`) |
| P2: hello line, write = len, 39 and 500 → -38, exit 0 | as predicted |
| P3: segv 0x4 cr2 0; kread 0x5; textwrite 0x7 cr2 0x400000; guard 0x6 in 0x7fffffffa000–afff; priv #GP 0 | as predicted (guard cr2 `0x00007fffffffaff0`; rips 0x400000, 0x40000a, 0x400007, 0x400000, 0x400000) |
| P4: three -EFAULT, nothing written, exit 14 | as predicted |
| P5: two spinners each switched in ≥ 2 times, exit 0 | as predicted: 54–60 runs each under TCG (215–236 ring-3 ticks), 6–7 under KVM (22–24 ticks) |
| P6: SMEP and SMAP on in all three places; U7 error 0x1, U8 0x11 rip 0x400000 | as predicted on CI QEMU 8.2.2 TCG, kasumi 11.1.1 TCG, hasu 11.1.0 KVM |
| P7: every existing suite unchanged | **wrong once**: `tests/mpx1` A6 copies `kernel/` and `boot/` to build its spin variant and the new `../user/programs.S` was not there (kasumi gauntlet at `8ec780a`: mpx1 20 PASS 8 FAIL, `notes/px09/kasumi-gauntlet-8ec780a-prerebase.summary`). Fixed by copying `user/` too (the test's assertions unchanged); green since |
| first build fails on a refusal | **right, the shape guessed wrong**: `shared` and `spawn` are reserved keywords (px07 had noted `spawn`), then an unused `u64` value, then `str` comparison needs the hosted runtime (programs go by number). `notes/px09/kasumi-first-build.out` |
| first boot does not reach the hello line (a #GP on the return to ring 3, or #PF 0x15) | **wrong**: the first boot that built passed every assertion, U1–U8, both tiers, BIOS and UEFI (kasumi, `~/lanes/px09/out/boot1-first.out` `4f626da9…`) |

Not predicted: GNU grep reads a serial log holding a NUL as binary and
answers "binary file matches" instead of the line; under plant A (the
kernel image written to the console) U1–U3 went red for that reason
alone (run 37686356366, before the rebase). `tests/mpx3-user` now greps
with `-a` (`1a837bf`), and plant A was re-run on the fixed test: only
U4–U6 red (R2 below).

## 4. Evidence index

### Red then green

Shas are the branch's after the rebase onto px06 (`bc86ea5`). Runs
before it tested the same commits' pre-rebase twins (same content but
for px06's files): `6f4a0dd`, `8ec780a`, `128355e` here stand for them,
and the run ids are the artifacts.

- **Red** at `128355e` (the test and its CI job, no kernel): run
  **37690204213**, job 113028128778 (log `f7ee1f03…`): 0 PASS, 38 FAIL,
  0 SKIP lines (U0 ×6 "no kernel/kmain_user*.lu", U1–U8 "no image").
  Before the rebase onto px06 the same tree was red in run 37677944220,
  job 112986175039 (the same commit before the rebase, now `128355e`), 0/38/0.
- **Green** at `6f4a0dd`'s tree before the rebase onto px06 (its pre-rebase twin; the rebase moved no line of it): run **37681206949**,
  attempt 2: mpx3-user 38 PASS (job 113013553505); mkw 16, mpx1 26,
  mpx2-frames 44, mpx2-paging 26, mpx2-interrupts 34, mpx2-sched 32,
  proof 4, census 3, macos-run 2 PASS; 0 FAIL, 0 SKIP lines. Attempt 1's
  mpx2-sched and mpx2-frames jobs, and the red run's mpx2-sched, hung in
  `apt-get update` (the last line `Get:5 … noble-security InRelease`,
  then nothing until the cancel): the runner's mirror, not a test.
- **Green at the head**: see §5.

### The planted breaks (each pushed alone, CI run of its own)

- **A** `b2b0e1a`: `write` checks no user pointer. Run **37690385812**,
  job 113028741911 (log `64cff4b4…`): 26 PASS, 12 FAIL, 0 SKIP lines:
  U4, U5, U6 red on all four legs (the kernel writes its own image to
  the console, then reads 0x10 in ring 0: `PANIC page fault … cr2
  0x0000000000000010`), U0–U3, U7, U8 green. Reverted `3048a93`.
- **B** `3cb590e`: RSP0 written at the first switch only. Run
  **37692653466**, job 113036422375 (log `64090179…`): 34 PASS, 4 FAIL,
  0 SKIP lines: only U5, all four legs (`spin1 exit 3`, its mark lost;
  spin2 killed `invalid opcode` at 0x400069, its frame resumed with the
  other process's registers). Reverted `197fb4f`. The same plant on
  kasumi first: `notes/px09/kasumi-tcg-native-bios-kmain_user-plantB-rsp0-once.serial.log`.

### Runs off CI

- **kasumi** (QEMU 11.1.1 TCG, strict `PAX_REQUIRE_UEFI=1`,
  `WOLF_PAIRING_REQUIRE_SIBLING=1`, lupin present), every suite on the
  `git archive` of one commit:
  - `6f4a0dd`: all rc 0, 0 FAIL, 0 SKIP lines
    (`notes/px09/kasumi-gauntlet-6f4a0dd-prerebase.summary`);
  - `197fb4f` (rebased on px06's `bc86ea5`, the code of the head): proof
    2, mkw 16, mpx1 26, mpx2-frames 44, mpx2-paging 26, mpx2-interrupts
    34, mpx2-sched 32, mpx2-heap 56, mpx3-user 38 PASS; all rc 0, 0 FAIL,
    0 SKIP lines (`notes/px09/kasumi-gauntlet-197fb4f.summary`
    `84070966…`; images `b7a5a697…`).
- **hasu** (nix-shell QEMU 11.1.0, **KVM**, i7-12700KF with smep and
  smap), the kasumi images by `--images`:
  - `6f4a0dd`: mpx3-user 4 rounds × 12 boots (32 PASS each), mkw 12,
    mpx1 12, mpx2-frames 16, mpx2-paging 4, mpx2-interrupts 20,
    mpx2-sched 8: **120/120 boots, all accel=kvm**, 0 FAIL, 0 SKIP
    (`notes/px09/hasu-kvm-6f4a0dd-prerebase.log`);
  - `197fb4f`: the same plus mpx2-heap 24: **144/144 boots, all
    accel=kvm**, 0 FAIL, 0 SKIP (`notes/px09/hasu-kvm-197fb4f.log`
    `73038635…`).

### Ring 3, the serial log (kasumi TCG, native, BIOS; `notes/px09/kasumi-tcg-native-bios-kmain_user.serial.log`; KVM's in `hasu-kvm-native-bios-kmain_user.serial.log`)

    PAX user: ring 3
    user: syscall star 0x0010000800000000 lstar 0xffffffff800003ac fmask 0x0000000000044700, efer.sce 1, smep 1, smap 1
    user: hello pid 2 cr3 0x0000000000117000 code 0x0000000000400000 1 pages r-x, stack 0x00007fffffffb000 to 0x00007ffffffff000 rw- nx, guard 0x00007fffffffa000, kernel half 4 of 4 entries shared
    hello from ring 3: cpl 3
    user: hello pid 2 syscall 39: -ENOSYS
    user: hello pid 2 syscall 500: -ENOSYS
    user: hello pid 2 exit 0 after 1 runs
    user: frames free 65047 before, 65031 with 1 processes, 65047 after
    user: segv pid 3 killed: page fault vector 14 error 0x0000000000000004 rip 0x0000000000400000 cr2 0x0000000000000000 after 1 runs
    user: kread pid 4 killed: page fault vector 14 error 0x0000000000000005 rip 0x000000000040000a cr2 0xffffffff80000000 after 1 runs
    user: textwrite pid 5 killed: page fault vector 14 error 0x0000000000000007 rip 0x0000000000400007 cr2 0x0000000000400000 after 1 runs
    user: guard pid 6 killed: page fault vector 14 error 0x0000000000000006 rip 0x0000000000400000 cr2 0x00007fffffffaff0 after 1 runs
    user: priv pid 7 killed: general protection vector 13 error 0x0000000000000000 rip 0x0000000000400000 after 1 runs
    user: badptr pid 8 write fd 1 buf 0xffffffff80000000 len 16: -EFAULT
    user: badptr pid 8 write fd 1 buf 0x0000000000000010 len 16: -EFAULT
    user: badptr pid 8 write fd 1 buf 0x00007fffffffeff8 len 16: -EFAULT
    user: badptr pid 8 exit 14 after 1 runs
    spin1: begin
    spin2: begin
    spin2: end
    user: spin2 pid 10 exit 0 after 59 runs
    spin1: end
    user: spin1 pid 9 exit 0 after 60 runs
    hello from ring 3: cpl 3
    user: after pid 11 exit 0 after 1 runs
    user: ticks in ring 3 236
    halt

(space and frames lines between batches elided; the file has them all.)

### Filed

Nothing new: every wolf limitation met was already open (#526 no inline
asm, #577, #579, #598, #611) or a documented refusal (reserved
keywords; `str` comparison on the freestanding target).

## 5. Done-when

- Branch `px09` on origin, rebased on pax trunk `bc86ea5` (px06 merged);
  PR wolffe-lang/pax#12, open, unmerged.
- CI green at the head: the run id is in the PR body (the head is this
  note's commit; the kernel code is `197fb4f`'s).
- Close nothing. To close: none (no pax issue names this work).
- Worktrees: kasumi `~/lanes/px09/` and hasu `~/lanes/px09/` hold the
  lane's clones, trees and evidence; `build/` and the gauntlet trees
  pruned at the end. One stray: the first `scp` to hasu wrote
  `~/lanes/px09-hasu-kvm.sh` outside the lane's directory; it was moved
  into `~/lanes/px09/` at once (no `rm`).
