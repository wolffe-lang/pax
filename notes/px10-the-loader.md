# px10 — the loader (pax at 0.2.25, ELF and initramfs)

Contract: `sprints/pax/10-the-loader/px10-the-loader.md` in wolffe-lang/wolf
(planning trunk `f6a6f343` at the time of reading; the contract's only
commit is wolffe-lang/wolf `4766fff`, 2026-10-07). Branch `px10` in pax, cut from px08's head
`7c42f5b` (pax#11, rebased on pax trunk `a01e2e4` and green;
it merges first, and this branch is rebased on trunk once it lands).
This note is committed whole, §1–§3 first, before either release archive
is unpacked; §4 and §5 are filled in as the evidence lands.

## 1. Forbidden, absolutely

- No Linux kernel, glibc, musl or any other kernel's or libc's source is
  read (ruling #22). Used, all allowed: the uapi headers
  `include/uapi/linux/auxvec.h` (AT_* numbers),
  `arch/x86/include/uapi/asm/auxvec.h`, `include/uapi/linux/elf.h`
  where a number is needed, `include/uapi/asm-generic/errno-base.h` /
  `errno.h`; `arch/x86/entry/syscalls/syscall_64.tbl` (exit 60,
  exit_group 231, arch_prctl 158); `Documentation/driver-api/
  early-userspace/buffer-format.rst` (the initramfs `newc` format); the
  System V gABI's ELF chapter and the x86-64 psABI (§3.4.1 the initial
  process stack, §3.4.2/A.2.1 the kernel convention); the Intel SDM
  (vol. 1 ch. 10 and 13: FXSAVE, XSAVE, the init state; vol. 3A
  §2.5–2.6: CR0, CR4, XCR0) and the AMD64 APM vol. 2 §11.5; Limine's
  PROTOCOL.md (limine-protocol `3a0526b7`, the module feature and
  `struct limine_file`) and CONFIG.md (Limine v12.9.1, `module_path`);
  man-pages (`execve(2)`, `exit_group(2)`, `getauxval(3)`,
  `elf(5)`, `cpio(5)`); black-box Linux on kasumi (the test program run
  natively and under `strace`). The refs clone's sparse checkout is
  never widened.
- No `region` is held open across a yield, a switch or a return to user
  mode (wolf-lang#611): this lane allocates nothing from wolf's heap; the
  initramfs is read in place and every process's pages are frames.
- px08's and px11's files are not touched (px11, launched after this
  contract, renames px08's work and merges before this lane): this lane
  edits none of `kernel/reel`, `kernel/kmain_reel*`,
  `boot/limine-reel.conf`, `tools/reel`, `tests/reel`, `demo/`, and
  uses px08's `tools/mkimage` options (`--conf`, `--add`) as written.
  Shared files this lane must edit: `.github/workflows/ci.yml` (a new
  job), `docs/SOURCES.md`, `kernel/README.md`, `README.md` (appended
  sections).
- No `rm` outside `~/lanes/px10/` and this lane's worktrees; no deletion
  in a tree this lane did not create; no `git add -A`; nothing under
  `~/.claude`; no merge, tag or release; no attribution trailers.
- No "seen red" without a run id, sha, path or digest. Gate results
  under the strict env (`PAX_REQUIRE_UEFI=1`,
  `WOLF_PAIRING_REQUIRE_SIBLING=1`, lupin present for mkw), SKIP lines
  counted in the full output.
- Builds on kasumi (`bash -c`, `scp`, `setsid` with recorded pids,
  done-files, `command ls`, `build/` pruned); KVM on hasu
  (`nix-shell -p qemu`). Nothing installed anywhere; nothing built on
  nomad-1.

## 2. Inputs, verified (2026-10-07, from the release API and origin)

| input | found |
|---|---|
| wolf 0.2.25 | release **406122367**, tag `v0.2.25` (annotated tag `90f1c11e`) → wolf-lang **`6710f9e0`**; published 2026-10-07T20:18:34Z. Asset digests from the API: linux x86-64 `9d91f533…` (74,979,974 bytes), linux aarch64 `6b0bb90d…`, macOS arm64 `202c8d6c…`, windows `9debee73…`. **As the contract says.** |
| lupin 0.1.48 | release **405340127**, tag `v0.1.48` (annotated `469352f5`) → wolf-interp **`531bf058`**. Digests: linux x86-64 `81cfd77a…`, aarch64 `a5c30957…`, macOS `27d86060…`, windows zip `9e4ea090…`, `lupin.exe` `6a6eb6e9…`. **As the contract says.** |
| 0.2.25 for a downstream | CHANGELOG at `v0.2.25`, "Read this before you bump the pin": no new prelude names; #598/#601 (loads and stores of foreign memory are no longer forwarded across a call that may write it: binaries gain reloads after calls), #600 (release no longer deletes a branch on the top half of `u64 >> k`). As the contract says. |
| pax trunk | `a01e2e4` (px09), as the contract says |
| px08 (pax#11) | open, head `7c42f5b`, rebased on `a01e2e4`; its CI run 37698421725 in progress at the time of reading (37690284791 green before). It edits `tools/mkimage` (`--conf`, `--add ELF NAME`), which this lane uses as written |
| `kernel/wolf.pin` | wolf **0.2.24** (`501d6d3f…`, pin `294d626d`), lupin **0.1.44** (held there by px05 and px07 for tests/mkw step 6's clap row, wolf-interp#182) |
| what user mode owes (px09's note) | FXSAVE/XSAVE per thread, `exit_group`, argv/envp/auxv, an NMI IST, SWAPGS for SMP; this lane takes the first three |
| `docs/CENSUS.md` | M-PX3 needs 14 calls (`execve`, `exit_group`, `arch_prctl` SET_FS, `mprotect`, `brk` or `mmap`, `read`, `write`, `openat`, `close`, `fstat`, `getcwd`, `getdents64`, `getrandom`, `clock_nanosleep`); a static binary needs `AT_PHNUM` alone of the auxv (dies of SIGSEGV without it); `AT_PHDR`, `AT_ENTRY` for a dynamic one |
| Limine's machine state at entry (PROTOCOL.md) | "All other cr0, cr4 and EFER bits beyond those specified are cleared": **CR4.OSFXSR is clear**, so today any SSE instruction in ring 3 is `#UD` |
| Limine modules | `LIMINE_MODULE_REQUEST_ID` { common magic, `0x3e7e279702be32af`, `0xca1c4f3bd1280cee` }; response {revision, module_count, modules → `struct limine_file *`}, the file's `address` a virtual (HHDM) address at base revision 6, 4 KiB aligned, its pages its own; memory-map type 6 (executable and modules) |
| PAX's HHDM (px03) | maps types 0, 2, 3, 5, 8 and **leaves type 6 out**: after `paging.start` a module is unreachable, so its pages must be mapped (read-only, no-execute) |
| kasumi | QEMU 11.1.1, gcc, binutils, ld.lld, python3, cpio; `/home` 96% used (43 GB free) |
| hasu | `/dev/kvm` present (crw-rw-rw-) |

**Drift, reported and not absorbed:**

1. "The pin, both halves by digest": lupin moves too, 0.1.44 → 0.1.48,
   which changes what tests/mkw step 6 asserts (its `lupin-target` row
   records 0.1.44's clap error for `--target`, fixed in 0.1.46 by
   wolf-interp#182). px05 and px07 deferred that move to "a lane of its
   own"; this contract makes it this lane's, so the row is re-recorded
   in the pin's commit and the move is in §3.
2. px08 merged (trunk `7c42f5b`) while §1–§3 were being written: this
   branch was already cut from that commit. The orchestrator then
   launched px11 (it renames px08's suite and removes `demo/`), which
   merges before this lane; this branch is rebased on it when it lands.
3. (Found after §3, by the pin's gauntlet, `notes/px10/` §4) px08's suite
   checks that its kernel prints the pinned wolf version, and its kernel
   spells the version as a literal (`wolf 0.2.24`): the pin bump reds
   it until that literal moves, which is px08's file and now px11's.
   The move is made after px11 lands, in its renamed file, as the one
   line the bump needs (§4).

## 3. Prediction (committed before either archive is unpacked)

### The pin (item 1)

- **Q1.** Every gate's assertions hold unchanged at 0.2.25 / 0.1.48, PASS
  counts per job identical to px09's head run (mkw 16, mpx1 26,
  mpx2-frames 44, mpx2-paging 26, mpx2-interrupts 34, mpx2-sched 32,
  mpx2-heap 56, mpx3-user 38, proof 4, census 3, and px08's suite as it
  stands), with **one** exception: tests/mkw step 6's `lupin-target`
  row, which must be re-recorded (Q4).
- **Q2. Every kernel ELF moves**, native and release, every kernel in
  every suite: #598/#601 add a reload after each call that may write
  foreign memory, and PAX reads raw pointers, `extern "c" let` storage
  and HHDM words after calls everywhere (frames, paging, sched, user).
  Falsified by one kernel ELF byte-identical across the bump. Text
  grows: kmain_user's `.text` by 0.5–5% on native.
- **Q3. No behaviour moves**: #600's shape is avoided in PAX by ranges
  (kernel/interrupts, kernel/heap say so), and #598's by volatile
  words; S7's reported module var stays `1 -> 2` (px07 measured 2 on
  0.2.24 already), H10 stays `598: up false -> true, pages 0 -> 16,
  live 0 -> 1 -> 0`. Transcripts move only in addresses (lstar, rips,
  frame pointers) and in the image-derived counts (table frames, free
  frames), as px05's 21 of 64 did.
- **Q4. tests/mkw step 6 on lupin 0.1.48**: the no-target row is
  unchanged (`"verdict":"unsupported"`, no `main` in its root module);
  the `--target x86_64-unknown-none` row stops being clap's
  `unexpected argument '--target'` and becomes a JSON verdict
  `unsupported` (0.1.46 learned the flag). Falsified if 0.1.48 still
  refuses the flag, or answers anything but `unsupported`.
- **Q5.** fetch-wolf's stamp check: `wolf --version` names `pin 6710f9e`.

### The loader (items 2–5)

**The pieces.**

| piece | where | shape |
|---|---|---|
| module request | `boot/start.S` | a seventh request, Limine's module id, revision 0 |
| module response | `kernel/boot_info` | `module_count()`, `module_addr(i)`, `module_size(i)` (the file's HHDM address and size) |
| module pages | `kernel/paging.build` | every module's 4 KiB pages mapped in PAX's HHDM, read-only no-execute; nothing else of type 6 |
| initramfs | `kernel/initramfs` | a read-only view of a `newc` archive (`070701`, and `070702` without checking the sum) in the module's own pages: `start`, `report` (entries, bytes), `find(path) -> (data, size)`, regular files only; refusals by name: no module, a bad magic, a compressed archive (gzip `1f 8b`, zstd, xz…), a name or size past the end, no trailer |
| ELF64 loader | `kernel/elf` | validates the header (magic, ELFCLASS64, ELFDATA2LSB, EV_CURRENT, EM_X86_64 62, `e_phentsize` 56), then each `PT_LOAD`: page-aligned congruence (`p_vaddr ≡ p_offset` mod 4096), `p_filesz ≤ p_memsz`, the file range inside the file, the memory range inside the user half and above the first page; maps each page with the segment's permissions (R → present, W → RW, no X → NX), copies `p_filesz` bytes, zeroes the rest (the `.bss`); returns the entry, `AT_PHDR` (`PT_PHDR`'s `p_vaddr`, else the load segment holding `e_phoff`), `AT_PHNUM`, `AT_PHENT`. Refusals by name: `ET_DYN` ("a PIE or shared object: later"), `PT_INTERP` ("dynamic: needs an interpreter"), anything not `ET_EXEC`, two segments on one page with different permissions, a segment overlapping another, `PT_TLS` is accepted (userspace's business) |
| process start | `kernel/user.exec` | a stack of 32 pages below 0x7ffffffff000, the guard below it; from the top: the path (AT_EXECFN), the envp and argv strings, 16 random bytes (AT_RANDOM, RDRAND when CPUID has it, else a TSC mix: named, not cryptographic), padding to 16, then auxv (AT_PHDR, AT_PHENT, AT_PHNUM, AT_PAGESZ 4096, AT_BASE 0, AT_FLAGS 0, AT_ENTRY, AT_UID/EUID/GID/EGID 0, AT_CLKTCK 100, AT_SECURE 0, AT_RANDOM, AT_EXECFN, AT_NULL), envp NULL, argv NULL, argc at RSP, RSP 16-aligned (psABI §3.4.1); `%rdx` 0 (no exit function), every other register 0 |
| `exit_group` (231) | `kernel/user.syscall` | ends the process (one thread a process): `user: <name> pid <id> exit_group <code> after <r> runs` |
| FPU state per thread | `kernel/fpu` + `boot/fpu.S`; `kernel/sched.run_next` | `fpu.start`: CR0.EM clear, MP set, TS clear; CR4.OSFXSR and OSXMMEXCPT set; with CPUID.1:ECX.XSAVE, CR4.OSXSAVE and XCR0 = x87 \| SSE (\| AVX when CPUID.1:ECX.AVX); area size from CPUID.(0xD,0).EBX; a template area (FCW 0x037f, MXCSR 0x1f80, XSTATE_BV x87 \| SSE, all else zero) copied into each new thread's area; at every switch between two threads, XSAVE (or FXSAVE) the outgoing thread's state into its slot's area and XRSTOR (or FXRSTOR) the incoming one's. The kernel itself is built with no SSE (build-kernel asserts it), so the registers at a switch are the outgoing thread's. Kernels that never call `fpu.start` switch exactly as before |
| the thread record | `kernel/sched` | gains the ELF process's entry, initial RSP and name (a pointer into the initramfs and a length): 88 → 120 bytes |
| the test program | `user/elf/hello.S` | assembly, no libc (`-nostdlib -static`), one source built three ways: `hello` (`-no-pie`), `hello-pie` (`-static-pie`, ET_DYN), `hello-dyn` (`-no-pie` with `-dynamic-linker`, a PT_INTERP) |
| the image | `tools/mkinitramfs` | a `newc` archive from a list of (path, file), every mtime 0, inodes numbered in order: reproducible; `boot/limine-initramfs.conf` names it as a module; built with px08's `mkimage --conf … --add` |
| the kernel | `kernel/kmain_loader.lu` | boots, maps, starts the FPU, lists the initramfs, runs the programs below, checks every frame came back, halts |
| the gate | `tests/mpx3-loader` (CI job `mpx3-loader`) | L0 build … L8 (below), both tiers, BIOS and UEFI; plus the program run on the runner's own Linux and its output compared |

**What the kernel runs, in order**, from the initramfs:

1. `/bin/hello one two` (envp `HOME=/ TERM=linux PAX=1`): prints argc, each
   argv and envp string, `AT_PAGESZ 4096`, `AT_PHNUM <n> ok` (against
   its own ELF header, `__ehdr_start`), `AT_PHDR ok`, `AT_ENTRY ok`,
   `AT_RANDOM ok` (16 bytes readable), `rsp 16-aligned`, `rdx 0`,
   `fcw 0x037f mxcsr 0x1f80`, `data ok` (an initialised word), `bss ok`
   (a zeroed 64 KiB, so the zeroing crosses pages past `p_filesz`),
   `rodata ok`, `xmm ok`, then `exit_group(0)` (the number of failed
   checks).
2. `/bin/hello spin 1` and `/bin/hello spin 2` at once: each loads all
   sixteen xmm registers with a pattern of its own, spins long enough to
   be preempted many times, checks every register, prints `spin <k>: xmm
   ok` (or `xmm BAD` and exits 1): FXSAVE/XSAVE per thread.
3. The refusals, each a kernel line by name and the kernel going on:
   `/bin/hello-pie` (ET_DYN), `/bin/hello-dyn` (PT_INTERP),
   `/bin/hello32` (hello with EI_CLASS patched to 1), `/bin/hello-arm`
   (e_machine patched to 183), `/etc/motd` (not an ELF), `/bin/nothing`
   (not in the initramfs).
4. `/bin/wolf-hello` when the initramfs holds it (a wolf 0.2.25 program
   built static: the gap census below); every system call PAX lacks is
   a `-ENOSYS` line, so its log is the census.

**The numbers.**

- **L1.** The initramfs line names every entry with its size; `find`
  answers each path the archive holds and refuses one it does not.
- **L2.** `hello` runs **byte-identical** to the same binary run on
  Linux with the same argv and envp (kasumi natively and the CI runner),
  CRs stripped from PAX's serial; exit 0 on both.
- **L3.** `/bin/hello` (built on kasumi, Arch binutils 2.45-ish, default
  `-z separate-code`) has **4 PT_LOAD** segments (r--, r-x, r--, rw-)
  from 0x400000 plus PT_GNU_STACK; PAX maps them with exactly those
  permissions (a W^X user image: no page both W and X). Falsified by any
  other count.
- **L4.** The refusals: six named lines, no fault, no panic, nothing
  mapped left behind (frames back to the count before).
- **L5.** FPU: `xsave 1, xcr0 0x7, area 832 bytes` on all three hosts
  (CI QEMU 8.2 TCG `-cpu max`, kasumi QEMU 11.1 TCG `-cpu max`, hasu KVM
  on the i7-12700KF): AVX is in every one of them, AVX-512 is not
  enabled (XCR0 bits 0–2 only). Both spinners print `xmm ok`, each
  switched in ≥ 2 times; with the save removed (the planted break) at
  least one prints `xmm BAD`.
- **L6.** Every batch's frames come back (`A / B / A`).
- **L7.** The existing suites hold (Q1) with the record grown to 120
  bytes and run_next's FPU branch (not taken without `fpu.start`).

**The first boot, and what fails first.** The first loader kernel builds
after one or two wolf refusals (a shape I have not met: a guess, a
`u32`/`u16` store or a narrowing cast in the ELF header reads). Once it
builds, the first boot **does not** print hello's first line: the
process start is wrong first — a ring-3 page fault inside hello's first
32 instructions from an argv/envp/auxv layout off by a word, or a `#UD`
on its first SSE instruction if the FPU enabling is wrong. The
falsifier is the first boot's serial log, kept in §4 either way.

**The wolf-built static program (the gap census).** A wolf 0.2.25
`println` program built `--release` and linked static (the census's
`cc -static` shape) is an ET_EXEC static non-PIE glibc 2.44 binary with
**no PT_INTERP and a PT_TLS**; PAX loads it and it enters ring 3. Its
first system calls on PAX answer `-ENOSYS` until `arch_prctl`
(ARCH_SET_FS, 158), after which it dies: **killed by a page fault with
cr2 below 0x1000** (an `%fs`-relative access with FS base 0), not by an
exit. Under strace on kasumi it makes **13 ± 3 distinct calls** for a
one-line print, all inside px04's M-PX3 static set. The gap PAX has
after this lane is the census's 14 minus `write` and `exit_group` (and
`execve`'s role, which the kernel's own start plays): **11 calls**, the
first fatal one `arch_prctl`.
