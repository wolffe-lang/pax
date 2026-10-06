# px07 — the scheduler (M-PX2's preemptive kernel threads)

Contract: `sprints/pax/07-the-scheduler/px07-the-scheduler.md` in
wolffe-lang/wolf (planning trunk `c4f30dc`). Branch `px07` off pax
`e53018d`; PR pax#9. The five sections were committed whole in `58a11bb`,
an empty commit pushed before the first change. This note carries §2's
drift, §3 against what was measured, §4 and §5.

## 1. Forbidden

As committed in `58a11bb`, and kept:
- No Linux, glibc or other kernel's or libc's source was read. The
  switch, the frames and the lock come from the Intel SDM vol. 3A ch. 6
  and §9.1.2, vol. 2, and the AMD64 APM vol. 2 §8.9, by section, in
  `docs/SOURCES.md`.
- Nothing was installed on any host, and nothing was built on nomad-1
  (it edited, committed, pushed and read CI).
- kasumi was used under `~/lanes/px07/` only, with jobs started by
  `setsid` and their pids recorded (`gauntlet-head{1,2}.pid`), waited on
  by done-file.
- hasu was used under `~/lanes/px07/` through `nix-shell -p qemu nasm`,
  plus `nix-build '<nixpkgs>' -A OVMF.fd`, as px01–px05 did.
- No issue was closed.

## 2. Inputs, verified (drift)

Re-derived 2026-10-06 and stated in `58a11bb`. No drift in the shas: pax
trunk `e53018d`; wolf v0.2.24 = `294d626d`, archive `501d6d3f…`; lupin
v0.1.47 = `b3228cb5`, `0ddc4ff3…`. Found while working:

- **`spawn` is a reserved keyword** (`[gram.inv.kw]`, E0008), so the
  contract's "thread create" is `sched.create(body, arg)`.
- **wolf 0.2.24 adds W0604** ("this `get` declares no absence row") on
  `kernel/frames`' private `get`, px02's code. It is a warning, the
  build is unaffected, and it was left alone; `sched`'s accessors are
  named `field`/`put_field`.
- **wolf-lang#598**, sent mid-lane by the orchestrator as a P0: wolf
  0.2.24's compiled tiers forward a module `var`'s value, and a store
  through an `extern "c" let` pointer, across a call that writes it.
  The changes:
  - The scheduler's scalars moved from module `var`s into
    `boot/sched.S`'s `pax_sched_state`, read and written volatile
    (`7c25414`).
  - The tick count moved into `boot/isr.S`'s `pax_tick_count` (`812424c`;
    kw10's `kernel/timer`).
  - Every site is commented `// #598`.
  - S7 was added as the witness (`598601f`, `a32ab6a`).
  Before the change, S2 (which reads the tick count before and after a
  switch) passed on every leg, so the bug had not fired here yet; that
  was luck, not design.
- **QEMU 8.2's TCG (pax CI) left a tick pending through S4's locked
  loop.** PR run 37522542792 (`c8f35e1`) hung after S3 on all four legs,
  with no `lock:` line in 240 s; S1–S3 and S5 passed. QEMU 11.1's TCG
  (kasumi) and KVM (hasu) took every tick.
  - In that loop IF is set only between `release`'s STI and the next
    `acquire`'s CLI.
  - That emulator recognizes the pending request only when it returns to
    its main loop with IF set; PAUSE is an instruction it executes by
    returning there.
  - `pax_irq_restore` now ends `sti; nop; pause` (`4fd4587`), a no-op on
    hardware, and CI is green.
  - This is black-box behaviour, measured; no QEMU source was read.
- The contract's thread-body question has a wolf answer only by
  workaround: wolf has no C function-pointer value (wolf-lang#520). An
  `extern "c" let NAME: *u8` beside `export fn NAME` is E0302; in another
  module it links. Thread bodies are therefore `export fn`s in
  `kernel/schedtest` that the kernels name.

## 3. Prediction against measurement

| predicted (`58a11bb`) | measured |
|---|---|
| pin 0.2.24; every existing suite unchanged and green | as predicted: CI run 37520987765 (`81391f3`, pin moved, no kernel change), every pre-existing job green; kasumi gauntlets at `b2a3501` and `4fd4587`, every suite's assertions unchanged |
| `pax_interrupt(f) -> *Frame`; the common path `movq %rax, %rsp` before the pops | as predicted (S0: the instruction after `call <pax_interrupt>` is `mov %rax,%rsp`; I0 still sees `iretq` last) |
| `pax_switch` builds the 22-word frame (SS, RSP after return, RFLAGS then CLI, CS, RIP, 0, 0x81) and jumps to the common path | as predicted; vector 0x81 routed in `pax_interrupt` to `sched.switched` |
| `#[repr(c)] Thread`, 9 u64 fields, `size_of` 72, words at `offset_of` | as predicted (`pax_threads` is 16 × 72 bytes) |
| stacks: slot s at `0xffffd00000000000 + s·64 KiB`, low 48 KiB guard, high 16 KiB four frames RW NX | as predicted: S5 reads thread 2's stack `0xffffd0000002c000`–`…30000`, guard from `0xffffd00000020000` |
| quantum one tick | **changed to two.** A thread switched in voluntarily, part-way through a tick, would otherwise be preempted at once at the next tick, before it could act; two ticks guarantee every run at least one whole tick. Transcript: runs start every 2 ticks |
| dead stacks reaped "at the next scheduler entry from another thread" | **narrowed**: reaped by the next `create` or `wait_all` (thread context, IF clear), never in a handler, so `frames` and `paging` are never entered from an interrupt |
| S1 15 lines cycling, k strictly rising | the cycle as predicted; k strictly rises **until the first exit**. An exit hands the CPU over mid-tick, so the last three lines share tick 24. The test says so (`b2a3501`) |
| S2 wake order 3, 5, 7, b = a + n exactly; idle ran | as predicted: `24 -> 27`, `24 -> 29`, `24 -> 31`; idle ran 3 times |
| S3 B = A − 12, C = A, 3 of 3 unmapped | as predicted, e.g. 65052 / 65040 / 65052 (BIOS), 54582 / 54570 / 54582 (UEFI, CI) |
| S4 locked total exact; the unlocked control loses updates | as predicted, e.g. locked 8029 + 10080 = 18109 exactly; control 12022 of 18944, lost 6922 (CI, native BIOS) |
| S5 `PANIC stack overflow thread 2 cr2 … guard …` via a double fault on IST1 | as predicted: cr2 `0xffffd0000002bfe8` (native) and `…bff8` (release), inside the guard |
| plant: `acquire` takes no lock and leaves IF on → S4 red, everything else green | as predicted (below) |
| wolf limitations: #520, #577, #572, #579 | met: #520, #577, #572, **#597** (a lock word needs an address); #579 not needed. Not predicted: **#598** (above) |

## 4. Evidence index

### Assertions, red then green

`tests/mpx2-sched`, CI job `mpx2-sched`, per tier and firmware.

- **Red** at `81391f3` (the test and its job, before any kernel change):
  run **37520987765**, job 112466018260 (log `8afdba94…`): 28 FAIL lines
  (S0 ×4 for no `kernel/kmain_sched*.lu`, S1–S6 ×4 for no image, "no
  boot ran"), 0 PASS, 0 SKIP. The other eight jobs were green on the
  0.2.24 pin.
- **Green** at `4fd4587`: run **37524942827**, job 112479453886,
  32 PASS (S0 ×4, S1–S7 ×4), 0 FAIL, 0 SKIP lines; every other Linux job
  green. The revert's tree is identical to `4fd4587` (`git diff 4fd4587
  a539d95` is empty).

| | red at `81391f3` (37520987765) | `c8f35e1` (37522542792) | green at `4fd4587` (37524942827) |
|---|---|---|---|
| S0 build, trampoline shape | FAIL ×4: no kernel | PASS ×4 | PASS ×4 |
| S1 three threads alternate by preemption alone | FAIL ×4: no image | PASS ×4 | PASS ×4 |
| S2 sleep wakes on the tick, idle ran | FAIL ×4: no image | PASS ×4 | PASS ×4 |
| S3 exit reclaims the stacks | FAIL ×4: no image | PASS ×4 | PASS ×4 |
| S4 lock exact, control loses | FAIL ×4: no image | FAIL ×4: hung, QEMU 8.2 (§2) | PASS ×4 |
| S5 overflow into the guard by name | FAIL ×4: no image | PASS ×4 | PASS ×4 |
| S6 halted | FAIL ×4: no image | FAIL ×4: never reached `halt` | PASS ×4 |
| S7 fresh across a switch (#598) | (not yet written) | (not yet written) | PASS ×4 |

S7 was added after the red run. It was seen red on kasumi with the two
asserted reads planted stale (`let t1 = t0`, `let got: u64 = 1`):
`~/lanes/px07/s7plant.out` (`91e9a7aa…`), S7 FAIL on both tiers, 16 PASS,
2 FAIL, 0 SKIP. That run also showed #598 firing on the module-var probe
(below).

### The planted break

`f0fc57e` (pushed alone): `sync.acquire` takes no lock and leaves IF on.
Run **37526347980**, job 112484206312 (log `e4d61141…`), red: S4 FAIL on
all four legs, the locked counter short of the threads' own sum (native
BIOS 11520 of 17931, release BIOS 10019 of 16090, native UEFI 11567 of
18042, release UEFI 9458 of 14233). Every other S passed: 28 PASS,
4 FAIL, 0 SKIP lines. Reverted in `a539d95`.

### Runs

- **CI** (ubuntu-latest, QEMU 8.2, TCG): the runs above.
- **kasumi** (QEMU 11.1.1, TCG), the whole gauntlet, strict
  (`PAX_REQUIRE_UEFI=1`), wolf from `tools/fetch-wolf`:
  - at `b2a3501` (`~/lanes/px07/ev/head1/`): proof 2, mkw 16, mpx1 26,
    mpx2-frames 44, mpx2-paging 26, mpx2-interrupts 34, mpx2-sched 28
    PASS; every suite rc 0; 0 FAIL; 0 SKIP lines (mpx2-sched.out
    `1780125e…`);
  - at `4fd4587` (`ev/head2/`): the same, with mpx2-sched 32 PASS
    (`26b7a1b3…`).
- **hasu** (nix-shell QEMU 11.1.0, **KVM**, the combined `OVMF.fd`),
  `--images` from kasumi:
  - `b2a3501`'s images (`images-head1.tar` `2c62e454…`): mpx2-sched
    3 rounds × 8 boots, 24 PASS each; mkw 12, mpx1 12, mpx2-frames 16,
    mpx2-paging 4, mpx2-interrupts 20 boots; all rc 0, 0 FAIL, 0 SKIP
    lines; **88/88 boots under KVM** (`hasu-kvm.log` `2740527f…`).
  - `4fd4587`'s images (`images-head2.tar` `69f6336d…`, the head's
    kernels): mpx2-sched 3 rounds × 8 boots, 28 PASS each (S1–S7 × 4; S0
    is the build, not run with `--images`); mkw 12, mpx1 12, mpx2-frames
    16, mpx2-paging 4, mpx2-interrupts 20 boots; all rc 0, 0 FAIL, 0
    SKIP lines; **88/88 boots under KVM** (`hasu-kvm.log` `334b0598…`).
    S7 under KVM read `ticks 75 -> 77` or `76 -> 78`, storage 1 -> 2, and
    module var 1 -> 2 on every boot.

### The transcript (CI run 37524942827, native BIOS, artifact `pax-mpx2-sched-linux`, `.norm` `c1e799e3…`)

    PAX sched: threads
    paging: limine cr3 0x000000000ff5b000, pax cr3 0x0000000000105000, 8 table frames
    sched: main 0, idle 1, 16 slots, stacks 16 KiB above a 48 KiB guard from 0xffffd00000000000, quantum 2 ticks
    preempt: 3 threads spin, none yields
    t2: run 1 at tick 0
    t3: run 1 at tick 2
    t4: run 1 at tick 4
    t2: run 2 at tick 6
    t3: run 2 at tick 8
    t4: run 2 at tick 10
    t2: run 3 at tick 12
    t3: run 3 at tick 14
    t4: run 3 at tick 16
    t2: run 4 at tick 18
    t3: run 4 at tick 20
    t4: run 4 at tick 22
    t2: run 5 at tick 24
    t2: done, 5 runs, 0 yields
    t3: run 5 at tick 24
    t3: done, 5 runs, 0 yields
    t4: run 5 at tick 24
    t4: done, 5 runs, 0 yields
    preempt: 3 exited
    t5: slept 3 ticks, tick 24 -> 27
    t7: slept 5 ticks, tick 24 -> 29
    t6: slept 7 ticks, tick 24 -> 31
    sleep: idle ran 3 times
    exit: frames free 65052 before, 65040 with 3 stacks, 65052 after, 3 of 3 stacks unmapped
    lock: t8 8029 increments in 6 runs
    lock: t9 10080 increments in 6 runs
    lock: counter 18109
    nolock: t10 8644 increments in 6 runs
    nolock: t11 10300 increments in 6 runs
    nolock: counter 12022, lost 6922
    t12: across a yield: ticks 75 -> 77, storage 1 -> 2, module var 1 -> 2
    halt

kmain_sched_overflow, the same run (`e631c58e…`):

    PAX sched: stack overflow
    paging: limine cr3 0x000000000ff5d000, pax cr3 0x0000000000105000, 8 table frames
    sched: main 0, idle 1, 16 slots, stacks 16 KiB above a 48 KiB guard from 0xffffd00000000000, quantum 2 ticks
    overflow: t2 stack 0xffffd0000002c000 to 0xffffd00000030000, guard 0xffffd00000020000 to 0xffffd0000002c000
    PANIC stack overflow thread 2 cr2 0xffffd0000002bfe8 guard 0xffffd00000020000 to 0xffffd0000002c000

t2, t3 and t4 never yield or sleep: each spins and prints only when it
finds its own run count moved. The timer's preemption alone makes the
alternation.

### Filed (wolf-lang; comments with this lane's witnesses, all open)

- **#520** (no C fn pointer): a thread body's address; E0302 for the
  `extern "c" let` beside the export, and the child-module form that
  links.
- **#597** (a module var has no address): the lock words and the
  scheduler's scalars live in assembly `.bss`.
- **#577** (store to a field of a raw element): the Thread record and the
  first frame are written word by word at `offset_of`.
- **#572** (no never-returning fn): `exit`'s and `pax_interrupt`'s dead
  values.
- **#598** (store forwarded across a writing call): pax's sites and S7.
  The first comment said the module-var probe read fresh across the
  switch. The **correction** (second comment): with S7's volatile reads
  planted away, the probe reads the stale 1 on both tiers, so #598 does
  reach across a cross-module call that switches threads. Only an
  intervening `read_volatile` had masked it.
- No new issue: every limitation met was already open.

## 5. Done-when, and what comes next

Close nothing. To close: none (no pax issue names this work; #598 stays
with s214).

**User mode (ring 3, the TSS RSP0, `syscall`) inherits:**
- **RSP0 is still 0.** An interrupt from ring 3 switches to RSP0, so
  `run_next` must write the switched-in thread's `stack_hi` into the
  TSS's RSP0 (`kernel/gdt`'s `pax_tss`) on every switch.
- **The frame is already privilege-complete.** CS, SS and RSP are in
  every frame and `iretq` pops all five. A user thread's first frame
  needs CS 0x23, SS 0x1b and a user RSP; `pax_switch` builds kernel
  frames only (CS 0x08), so it stays kernel-side.
- **`syscall` does not switch stacks** (SDM vol. 3A §5.8.8). Its entry
  needs the current kernel stack's top from a scheduler word
  (`pax_sched_state`) on one CPU, or from a per-CPU area on SMP.
  STAR/LSTAR/SFMASK are unset.
- **No FPU or SSE state is saved** (the kernel uses none). User threads
  need FXSAVE/XSAVE per thread.
- **One address space.** Slot 416's stacks and the kernel half must
  appear in every process's PML4.
- **#598's rule stands:** state a switch rewrites stays out of module
  `var`s until s214 lands.

**SMP inherits:**
- **One `current` and one run queue.** They become per-CPU (a GS-based
  area). The queue operations are protected only by IF-off today and
  need `sync`'s lock, which is already SMP-correct: a CAS acquire, a
  release store, and spinning on a relaxed load with PAUSE.
- **The PIT's single tick** gives way to each CPU's local APIC timer,
  calibrated against the PIT (kw10's note).
- **`unmap` INVLPGs only the local TLB**, so reaping a stack needs a
  shootdown.
- **The idle thread** is one per CPU.
- **`pax_irq_restore`'s PAUSE** (§2) stays for QEMU 8.2.
- **A lock taken twice by one holder spins forever** with IF clear: not
  detected.
