# PAX

A Linux-compatible operating system written in wolf: a kernel that runs Linux's userspace unmodified, and a userspace built in wolf.

PAX is a clean-room implementation of Linux's userspace ABI. It does not contain, translate or derive from Linux kernel source. See `CLAUDE.md` for the rule and `docs/SOURCES.md` for what each part was written from.

Status: the shell's image runs only programs built by wolf (px15: pelt and boreutils' `cat echo false head ls sleep tail true wc`, `ls` boreutils' own; `quiet` on the kernel command line keeps the per-program `user:` lines off the console; `tests/mpx3-shell`) on the console (px13: what a person types reaches a program — COM1's receive interrupt and the PS/2 keyboard (i8042, scancode set 1, a US layout) feed one line discipline, canonical and non-canonical, with echo, erase, kill, word erase and Ctrl-D, the settings a Linux pseudo-terminal starts with less ISIG and IXON; `read(0)` sleeps the thread until a line is ready; TCGETS, TCSETS, TIOCGWINSZ answered, other terminal ioctls refused by name; pelt, the POSIX shell in wolf, built static from its own tree, runs as PID 1 and answers its built-ins at a prompt, Ctrl-D ends it and the kernel halts; every typed session byte-identical to the same session on a Linux pseudo-terminal; `tests/mpx3-console`) on Linux programs (px12, M-PX3: boreutils' utilities, built from boreutils' own tree and linked static against a baseline glibc, run unmodified on PAX from the initramfs — `echo`, `cat` of a file, `wc`, `head`, `tail`, `pwd`, `sleep`, and `ls` of a directory (busybox-static's until px15) — their output and exit status byte-identical to the same binaries on Linux; `brk`, anonymous `mmap`/`munmap`/`mprotect`, `arch_prctl(ARCH_SET_FS)` with FS per thread, a descriptor table over the read-only initramfs and a synthetic `/dev`, `openat`/`read`/`pread64`/`lseek`/`fstat`/`statx`/`getdents64`, `getcwd`, `getrandom`, the clocks and `clock_nanosleep`; `tests/mpx3-boreutils`) on the loader (px10, M-PX3's next step: static x86-64 Linux executables, read from a `newc` initramfs Limine hands over as a module, run unmodified in ring 3 with the psABI's initial stack — argc, argv, envp and an auxiliary vector — and print what they print on Linux, byte for byte; `exit_group` 231; each thread's x87/SSE/AVX state saved and restored at every switch; a PIE, a dynamic program and a file that is not an x86-64 ELF are refused by name; wolf 0.2.25 and lupin 0.1.48 by archive digest; `tests/mpx3-loader`) on user mode (px09, M-PX3's first step: programs run in ring 3, each in an address space of its own with the kernel half shared, call the kernel through `syscall` with Linux's x86-64 numbers — `write` 1 to the serial console with every page of the buffer checked first, else -EFAULT; `exit` 60; anything else -ENOSYS — and return by `sysretq`; a page fault or a privileged instruction in ring 3 kills the program by name and the kernel goes on; SMEP and SMAP on; `tests/mpx3-user`) on preemptive kernel threads (px07, M-PX2's scheduler: the timer switches between threads, each on its own stack from frames above an unmapped guard; yield, sleep, exit; a spinlock on wolf's atomics; `tests/mpx2-sched`, wolf 0.2.24) and the kernel heap (px06: kernel code uses wolf's `List`, `Map`, string interpolation, capturing closures and `region`; wolf's freestanding runtime, `libwolf_rt_none.a` from the 0.2.24 archive, allocates through `wolf_alloc`/`wolf_free`, which PAX writes in wolf over its frames and paging, `kernel/heap`, PML4 slot 384: page runs and eight size classes; eight rounds of such code leave no block behind and the heap does not grow after the first, and a double free, a free outside the heap, running out and a page fault in the heap each panic by name, `tests/mpx2-heap`) on interrupts (kw10, M-PX2's interrupt and timer pieces) on paging (px03), physical frames (px02) and first light (M-PX1, px01). Every kernel loads its own GDT, TSS (with an IST1 stack for the double fault) and IDT before anything else (`kernel/gdt`, `kernel/idt`); all 32 exceptions and the 8259's 16 lines enter through `boot/isr.S`'s trampolines into wolf (`kernel/interrupts`, `[abi.interrupt]`), which panics by name (`PANIC page fault vector 14 error … cr2 …`), lets a breakpoint return, and counts the PIT's ticks (`kernel/timer`, through the local APIC's LINT0, `kernel/apic`) — each read back from the halted machine through QEMU's monitor (`tests/mpx2-interrupts`). wolf is the 0.2.23 release archive, fetched by digest (px05; kw08's packed structs and `offset_of`, kw09's module state and `extern "c" let`, all in a release), and `serial`, `frames` and `paging` use them: module `const`s, the allocator's state address in a module `var`, its header at `offset_of`. The kernel builds its own x86-64 four-level paging structures from its frame allocator (`kernel/paging`): its image mapped one permission per section (text read-execute, rodata read-only, data and bss read-write no-execute), Limine's HHDM kept for RAM (without a writable alias of the image), nothing in the lower half; it switches CR3 to them, maps and unmaps pages with INVLPG, and a write to its own text faults — each read back through QEMU's monitor (`tests/mpx2-paging`). The kernel's frame allocator (`kernel/frames`, two bitmaps over Limine's memory map, its state in frames it takes for itself) hands out every usable frame above 1 MiB exactly once and takes them back, and panics by name on a double free or a free of a frame never usable (`tests/mpx2-frames`). (From px02 to kw10 wolf was built from source, `eb955c3b` then `6a4e6151`, for features no release carried; px05 returned to the archive.) The wolf kernel owns the serial console (a 16550 driver in wolf), prints what Limine handed it (bootloader, firmware, memory map, HHDM offset) and halts; a trap reaches its panic path, which prints `PANIC <kind> <file>:<line>` and halts. Both of wolf's compiling tiers, under BIOS and UEFI (`tests/mpx1`). The harness's assembly proof (`tests/proof`) and M-KW's first wolf kernel (`tests/mkw`) still run. The plan lives in the wolf planning repository under `sprints/pax/`.

Licence: GPL-3.0, with the wolf Training Data Permission (`LICENSE-TRAINING-DATA`).

## Layout

    kernel/   the wolf kernel (serial, log, boot_info, frames, paging, panic;
              kernel/README.md), its wolf.pkg and the wolf/lupin pin
    boot/     boot-protocol glue: the Limine pin and config, the kernel's
              entry and requests, port I/O, the control registers, the
              interrupt trampolines and the descriptor tables' storage
              (start.S, io.S, cpu.S, isr.S, kernel.ld), and the assembly proof under
              boot/stub/
    user/     the first user programs (px09): flat assembly blobs the
              kernel copies into each process (programs.S); elf/ (px10);
              boreutils.pin and mpx3-boreutils.run (px12: the boreutils
              tree M-PX3 runs and the commands it runs); pelt.pin and
              console/ (px13: the shell PAX runs as PID 1, the typed
              sessions)
    tools/    the harness: fetch-limine, fetch-wolf, fetch-lupin,
              build-stub, build-kernel, mkimage, qemu-run, qemu-halt
              (--type: a typed session, px13), qemu-fault, qemu-gdb,
              expect-serial, mkuser, mkboreutils, mkpelt, linux-run,
              linux-tty
    tests/    scripted QEMU tests: proof, mkw (with M-KW's frozen kernels
              in mkw.d/), mpx1, mpx2-frames, mpx2-paging, mpx2-interrupts,
              mpx2-sched, mpx3-user, mpx3-loader, mpx3-boreutils, mpx3-console,
              gdb-attach,
              expect-serial-selftest
    docs/     BOOT.md (the boot protocol, argued), SOURCES.md (the
              consulted-sources log), ABI notes as they come
    notes/    one note per lane: its contract and evidence

## Booting it

PAX boots through the **Limine** protocol from one hybrid ISO that boots under BIOS and UEFI (`docs/BOOT.md` says why). Limine itself is fetched from its release by sha256 digest, never built here.

```sh
tools/fetch-limine                         # Limine 12.9.1, digest-checked, into .pax-cache/
tests/proof                                # build the stub + ISO, boot it under BIOS and UEFI, assert
tools/qemu-run --firmware uefi build/pax-stub.iso; echo $?    # 33 = the stub's success code
tools/expect-serial build/serial.log PAX "firmware: uefi"
tools/qemu-gdb build/pax-stub.iso build/stub/pax-stub.elf     # gdb, frozen at reset
PAX_WOLF=$(tools/fetch-wolf) tests/mpx1    # M-PX1: first light, both tiers, BIOS and UEFI
PAX_WOLF=$(tools/fetch-wolf) tests/mpx2-frames   # px02: the frame allocator, both tiers, BIOS and UEFI
tests/mpx2-frames --images build/mpx2      # boot them elsewhere (hasu under KVM)
PAX_WOLF=$(tools/fetch-wolf) tests/mpx2-paging   # px03: paging, read back through QEMU's monitor
PAX_WOLF=$(tools/fetch-wolf) tests/mpx2-interrupts   # kw10: named panics, int3, #DF on IST1, the timer
PAX_WOLF=$(tools/fetch-wolf) tests/mpx2-sched   # px07: threads switched by the timer, sleep, exit, the lock, the guard
PAX_WOLF=$(tools/fetch-wolf) tests/mpx3-user   # px09: ring 3 — syscall write/exit, faults killed by name, SMEP/SMAP
PAX_WOLF=$(tools/fetch-wolf) tests/mpx3-boreutils   # px12, M-PX3: boreutils (ls too, px15) on PAX against Linux (sudo for the chroot)
tests/mpx3-boreutils --images build/mpx3-boreutils  # boot them elsewhere (hasu under KVM), Linux's side carried along
PAX_WOLF=$(tools/fetch-wolf) tests/mpx3-console   # px13: typed sessions (ask, pelt as PID 1) through COM1 and PS/2, against Linux
tests/mpx3-console --images build/mpx3-console    # boot them elsewhere (hasu under KVM)
tools/qemu-halt --elf K.elf --marker halt --cmd 'info tlb' K.iso   # monitor answers on the halted machine (K.log.cmd1)
tools/qemu-fault --marker 'write: .*' K.iso                        # a kernel that must fault: CR2 from the stopped machine
tests/mpx1 --images build/mpx1             # boot ISOs built elsewhere (any host with QEMU)
tools/qemu-halt --elf build/mpx1/native/kmain.elf --marker halt build/mpx1/native/kmain.iso   # is it halted?
PAX_WOLF=$(tools/fetch-wolf) PAX_LUPIN=$(tools/fetch-lupin) tests/mkw   # M-KW: the first wolf kernel, both tiers
tests/mkw --images build/mkw               # boot ISOs built elsewhere (any host with QEMU)
```

`tools/qemu-run` runs QEMU headless (`-nographic`, COM1 to a file, `-no-reboot`, a timeout, `isa-debug-exit` at port `0xf4`) and returns QEMU's status: `(v << 1) | 1` when the kernel writes `v` to the exit port, 0 for a reset or triple fault, 124 for a timeout. A kernel that halts never exits QEMU, so `tools/qemu-halt` boots it with QEMU's monitor on a pipe and, after the kernel's last line, holds it to RIP inside `pax_halt`, IF clear and HLT=1 at two probes a second apart, with no further serial output. Each tool's header comment states its usage; `qemu-run` and `qemu-gdb` print it with `--help`.

## Hosts

| host | build an image | boot one (`qemu-run`, `tests/proof --image`) | gdb (`qemu-gdb`) |
|---|---|---|---|
| linux x86-64 (CI's ubuntu, the pool) | yes: binutils, cc, make, curl, xorriso | yes: `qemu-system-x86_64`; OVMF for UEFI; KVM used when `/dev/kvm` is usable | yes: gdb |
| macOS arm64 | **no**: no x86-64 ELF binutils or xorriso in the base system | **yes**, TCG: Homebrew's `qemu`, which ships its own UEFI firmware; CI's `macos-run` job boots the linux-built ISO on every push | no gdb in the base system; `tools/qemu-run --gdb 1234` and lldb's `gdb-remote 1234` by hand |

Where each runs today (2026-10-02, px00):

- **CI**: `ubuntu-latest` with QEMU 8.2.2, OVMF and xorriso from apt (TCG); the `macos-run` job boots the same ISO, checked by digest, with Homebrew's QEMU 11.1.1 (TCG).
- **hasu** (NixOS): nothing system-wide is needed. QEMU and xorriso come from a nix-shell, and the UEFI firmware from nixpkgs' OVMF; use the **combined** `OVMF.fd` with no separate vars file, because split `OVMF_CODE.fd` + `OVMF_VARS.fd` hangs in the firmware under KVM there (5 of 6 boots):

  ```sh
  ovmf=$(nix-build --no-out-link '<nixpkgs>' -A OVMF.fd)/FV
  PAX_OVMF_CODE=$ovmf/OVMF.fd PAX_OVMF_VARS= \
    nix-shell -p qemu xorriso --run 'PAX_QEMU=$(command -v qemu-system-x86_64) tests/proof'
  ```
- **kasumi** (CachyOS): QEMU 11.1.1, xorriso and OVMF since the 2026-10-02 upgrade; the kernel builds (wolf, the objects, the ISOs) and boots here (TCG); px01 booted the same ISOs on hasu under KVM (`tests/mpx1 --images`).
- **macOS** (nomad-1, arm64): `tests/proof --image` on an ISO built elsewhere, as CI's `macos-run` does.

The QEMU binary is `$PAX_QEMU` (default `qemu-system-x86_64` on `PATH`) and the UEFI firmware `$PAX_OVMF_CODE` / `$PAX_OVMF_VARS`, so every host supplies its own. `tools/mkimage` is reproducible: every date in the ISO is `SOURCE_DATE_EPOCH`, default the last commit's time, so one commit builds one digest.

The harness never installs anything. A missing tool is named and the tool stops. The UEFI leg looks for OVMF at the distro paths in `tools/lib.sh`, or `PAX_OVMF_CODE` / `PAX_OVMF_VARS`; without it `tests/proof` skips that leg loudly, unless `PAX_REQUIRE_UEFI=1` (CI), when it fails.
