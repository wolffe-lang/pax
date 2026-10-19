# PAX — agent guidance

## The clean-room rule (read before writing a line)

**Never read, copy or translate Linux kernel source** (`.c`, `.S`, `.h` outside the uapi trees, Kconfig, Makefiles). PAX implements Linux's userspace ABI; it is not a port.

Allowed sources:
- the uapi headers (`include/uapi/`, `arch/*/include/uapi/`), GPL-2.0 WITH Linux-syscall-note;
- the syscall tables (`arch/x86/entry/syscalls/*.tbl`);
- `Documentation/`, the man-pages project, POSIX.1-2024, the x86-64 psABI;
- the Intel and AMD manuals, the UEFI, ACPI and virtio specifications;
- black-box behaviour of a real Linux under QEMU.

Permissively licensed kernels (the BSDs, seL4, Redox, Asterinas, Maestro, Kerla) are design references only, never copied. Record in `docs/SOURCES.md` what each change consulted.

The planning repo's refs clone (`wolf/refs/repos/linux`) is a sparse checkout of the allowed paths only.

## Where the plan is

`sprints/pax/index.md` in the planning repo (`wolffe-lang/wolf`). Contracts there are binding. When this file and the wolf spec disagree, the spec wins.

## The repository

- **Layout**: `kernel/` (wolf, from px01), `boot/` (the Limine pin and config; the kernel's assembly ring — `start.S`, the Limine entry and requests, and `io.S`, `cpu.S` and `isr.S` (the interrupt trampolines and the descriptor tables' storage, kw10), listed under `asm` in `kernel/wolf.pkg` — and `boot/stub/`, the harness's assembly proof, retired by px01; assembly is whole routines reached through `extern "c" fn`, never more), `tools/` (the harness), `tests/` (scripted QEMU tests), `docs/` (`BOOT.md`, `SOURCES.md`, ABI notes), `notes/` (one note per lane: contract and evidence).
- **The boot protocol is Limine**, base revision 6 (`docs/BOOT.md`, ruled by px00). Limine is fetched from its release BY DIGEST (`boot/limine.pin`, `tools/fetch-limine`), never vendored and never built from source. Bump the pin's three lines together.
- **Every behaviour claim is a QEMU test** run by CI: `tools/qemu-run` boots, `tools/expect-serial` asserts the serial log, QEMU's exit status carries the kernel's verdict through `isa-debug-exit` (status `(v << 1) | 1`). Where the behaviour is Linux's, the test is differential against a real Linux under QEMU.
- **A test is seen red before it is trusted**: plant the break in a commit and CI run of its own, then fix it. `tests/expect-serial-selftest` is the harness's own proof that it can fail. A plant's run needs only its suite, on one leg unless the gate needs another (ruling #92): `gh workflow run ci -r <branch> -f tier=pr -f suites=<job>`. mpx5-jobs boots its images from one process and qemu-halt's fail-fast refuses every typed boot after one whose first prompt never came, so a plant there also names the images its rows live in, `-f jobs_boots='<image>:<keyboard> …'` (its `PAX_JOBS_BOOTS`, px52, pax#85), and a later image's red is not hidden behind the probe's.
- **CI runs in tiers** (px37, px40; `notes/px37-the-ci-tiers.md`): a pull request's push runs the suites its change can affect (`tools/ci-plan`, `tools/ci-tiers.map`) on one leg, `--tier native --firmware bios`; a change to the kernel's core (px40, ruling #76: `kernel/{serial,log,panic,boot_info,frames,paging,gdt,idt,interrupts,apic,timer,heap,sync,sched,fpu}` and `boot/{io,cpu,isr,sched,fpu}.S`) or to CI itself runs every suite on that one leg; a push to trunk, the nightly and the `full-matrix` label run every suite on every leg, as does a change to the pins, the harness tools or the kernel's entry (`boot/start.S`, `boot/kernel.ld`, `boot/limine.conf`). **Merge needs a green `tier full` run at the head**: add the `full-matrix` label when the head is the one to merge (not when opening the PR). A new suite's job is wired like the others (`tests/ci-plan` checks it); a new place a suite reads gets a line in `tools/ci-tiers.map` (until then a change there runs full).

## Hard rules

- Commits chunked, terse, imperative. Never `git add -A`. No commit or PR trailers of any kind.
- Branch per lane, PR left unmerged; the orchestrator audits and fast-forwards.
- The repository is public (since 2026-10-06, on the maintainer's word); no secret or credential goes in it.
- The harness never installs packages; lanes never install on the pool.
- A gap in wolf is filed upstream (wolf-lang) with a witness, and the track index names it as a blocker.
- A `region` may stay open across a yield, a preemption or a wait: `kernel/sched` saves the runtime's ambient-region slot in the outgoing thread's record and restores the incoming thread's at every switch (px21a, wolf 0.2.27; `tests/mpx2-heap` H11 to H13). Two things are still refused: an interrupt handler allocates nothing, and a system call's handler holds no `region` open where it gives up its kernel stack for good (a wait that runs the `syscall` again, `clock_nanosleep`'s sleep, an exit, `execve`), because the code after that point never runs and the region would never be left.

