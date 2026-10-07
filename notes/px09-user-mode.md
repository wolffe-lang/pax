# px09 — user mode (PAX P3's first step)

Contract: `sprints/pax/09-user-mode/px09-user-mode.md` in wolffe-lang/wolf
(planning trunk `c5fd1e3` at the time of reading; the contract at `a3ccbb7`, its only
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

## 4. Evidence index

(filled as it lands)

## 5. Done-when

(filled at the end)
