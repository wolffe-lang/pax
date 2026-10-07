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

### §3 against what was measured

**The pin.**

| predicted | measured |
|---|---|
| Q1: every gate's assertions hold, one exception (mkw's `lupin-target` row) | **wrong once more**: two exceptions. mkw's row, as predicted (kasumi gauntlet at the pin, `ev/pin`: mkw 15 PASS 1 FAIL), and px08's suite R1 on all eight legs (36 PASS 8 FAIL): its kernel prints the wolf version as a literal (`wolf 0.2.24`) and its test checks it against `kernel/wolf.pin`. CI at the head: run 37702508398, job 113069055939, the same 8. That literal is px08's file and now px11's; it moves after px11 lands (§2 drift 3). Every other suite: PASS counts as px09's head (mkw 16, mpx1 26, mpx2-frames 44, mpx2-paging 26, mpx2-interrupts 34, mpx2-sched 32, mpx2-heap 56, mpx3-user 38, proof 2 on kasumi, census 3) |
| Q2: every kernel ELF moves, native and release (reloads after calls); kmain_user's text grows 0.5–5% | **wrong**: **no loaded byte of any kernel moved.** 31 of 59 ELFs differ (`ev/elfdiff-base-pin.txt`): all 29 native ones and px08's two native ones only in `.debug_info`, `.symtab`, `.strtab` (and `.debug_str`/`.debug_aranges`); 26 of 28 release ELFs are byte-identical, and the two that move (kmain_heap, kmain_heap_threads) move only through wolf's runtime archive's debug sections (`kmain_heap.rt-none.a` `50da6b26…` → `110f062a…`; every release `.o` byte-identical). kmain_user `.text` 59,696 bytes at both pins (native), 65,068 (release). Why: #598/#601 change plain loads and stores of foreign memory that a call may write; PAX reads and writes every such word volatile since px07 (the scheduler's rule), so no plain foreign load sits across a call for the fix to reload |
| Q3: no behaviour moves; transcripts move only in addresses and image-derived counts | **right on behaviour, wrong on the mechanism**: S7 `module var 1 -> 2`, H10 unchanged; 10 of 16 compared transcripts moved, and only in timing (mpx2-sched's lock/nolock increments, mpx3-user's spinner runs, px08's suite's ticks: TCG run-to-run noise), none in an address: the code did not move |
| Q4: lupin 0.1.48 answers `unsupported` for `--target` | **right**: `"verdict":"unsupported","x-unsupported":"the freestanding target x86_64-unknown-none"`; the no-target row unchanged |
| Q5: `pin 6710f9e` | right: `wolf 0.2.25 (wolfgang, pin 6710f9e)`, `lupin 0.1.48 (wolf-interp, reference interpreter at pin 294d626)` |

**The loader.**

| predicted | measured |
|---|---|
| the first build fails on one or two refusals | **right, three**: E0008 (`copy` is a reserved keyword, `kernel/elf`'s byte copier), then E0805 (`byte as u64` is outside the cast set: `b as int as u64`), then E0401 (an error-set alias is a spelling, not a value type, `[type.err.alias.transparent]`: a `why(e: ElfError)` cannot take the row; refusals became numbered codes). `notes/px10/kasumi-first-build.out` |
| the first boot does not print hello's first line (an off-by-a-word stack, or `#UD` on SSE) | **wrong**: the first boot that built passed every check, all 20 of hello's lines `ok`, both spinners `xmm ok`, six refusals, every frame back (`notes/px10/kasumi-tcg-first-boot-native-bios.serial.log` `e0da17cf…`) |
| L1 the initramfs listed and found | right |
| L2 hello byte-identical to Linux | right: kasumi (CachyOS, 7.2.8) 20 lines `e535b398…`; CI (Ubuntu) 20 lines `612c0697…` (its binutils give 5 program headers, kasumi's 7: `AT_PHNUM 5 ok` there); exit 0 on both, on every leg |
| L3 4 PT_LOAD r-- r-x r-- rw- from 0x400000 | right on kasumi's binutils and CI's (different sizes, same shape) |
| L4 six refusals by name | **right, one moved**: the first boot's `/etc/motd` (21 bytes) was refused `too small for an ELF header`; the gate's motd is 81 bytes so the magic is what refuses it (`not an ELF file`) |
| L5 `xsave 1, xcr0 0x7, area 832` everywhere; both `xmm ok`, ≥ 2 runs; the plant gives `xmm BAD` | right on CI QEMU 8.2 TCG, kasumi QEMU 11.1.1 TCG and hasu KVM (§4); runs 57–144 under TCG; the plant: `spin 1: xmm BAD xmm0`, exit 1 |
| L6, L7 | right |
| wolf-hello: ET_EXEC static, PT_TLS, no PT_INTERP | right (and a PT_PHDR, which names AT_PHDR) |
| 13 ± 3 distinct calls under strace, all in px04's M-PX3 static set | right: 12 with `execve` (`brk`, `arch_prctl`, `set_tid_address`, `set_robust_list`, `rseq`, `prlimit64`, `readlinkat`, `getrandom`, `mprotect`, `write`, `exit_group`), all in the set; kasumi and CI agree but for `getrandom`'s count (`notes/px10/kasumi-strace-wolf-hello.txt`, CI's in the run's artifact) |
| on PAX it dies at `arch_prctl`, killed by a page fault with cr2 below 0x1000 | **wrong**: it never reaches `arch_prctl`. Its first three calls are `brk(NULL)`, `brk`, `mmap`, each `-ENOSYS`; glibc writes `Fatal glibc error: Cannot allocate TLS block` (its own `write(2)` reaches the console) and calls `exit_group(127)`: a clean exit, not a fault |
| — (not predicted) | **a wolf binary linked on kasumi cannot be the subject**: kasumi's glibc is CachyOS's x86-64-v4 build (`pacman -Si glibc`: repository `cachyos-v4`, architecture `x86_64_v4`), so its static start-up holds AVX-512; on PAX that binary is killed `invalid opcode` at its first instruction of `_dl_aux_init` (`vmovdqu8 %zmm0,(%rsp)`), before any system call, because no PAX host's CPU offers AVX-512 to the guest (QEMU's TCG `-cpu max`; hasu's i7-12700KF has none, so the binary would not run on hasu's Linux either). The subject is therefore built on the CI runner against Ubuntu's baseline glibc (`tools/mkwolf-hello`, wolf-hello `a3ada54b…`), and kasumi's and hasu's runs use that file |
| the gap: 11 calls, the first fatal `arch_prctl` | **11 right, the first fatal one wrong**: `brk` (or anonymous `mmap`) is first |

## 4. Evidence index

### Archives and the pin

- wolf 0.2.25 `wolf-0.2.25-x86_64-unknown-linux-gnu.tar.gz` `9d91f533…` (release 406122367, wolf-lang `6710f9e0`); lupin 0.1.48 linux x86-64 `81cfd77a…` (release 405340127, wolf-interp `531bf058`): `kernel/wolf.pin`, the pin's commit (§5); fetch-wolf and fetch-lupin re-hash both on every run.
- The prediction: `d323de2`, pushed before either archive was unpacked.

### The move table (kasumi, QEMU 11.1.1 TCG, strict env; `~/lanes/px10/ev/`)

| suite | 0.2.24 (`ev/base`, tree `d323de2`) | 0.2.25 (`ev/pin`, the pin's tree) |
|---|---|---|
| expect-serial-selftest | rc 0 | rc 0 |
| proof | 2 PASS | 2 PASS |
| census | 3 | 3 |
| mkw | 16 | **15 / 1 FAIL** (`lupin-target`: Q4) → 16 with the row re-recorded (`ev/pin2`) |
| mpx1 | 26 | 26 |
| mpx2-frames | 44 | 44 |
| mpx2-paging | 26 | 26 |
| mpx2-interrupts | 34 | 34 |
| mpx2-sched | 32 | 32 |
| mpx2-heap | 56 | 56 |
| mpx3-user | 38 | 38 |
| px08's suite | 44 | **36 / 8 FAIL** (R1, the version literal) |

ELFs: 59 compared, 28 byte-identical, 31 moved in non-loaded sections only (`ev/elfdiff-base-pin.txt`). 0 FAIL elsewhere; 0 SKIP lines in any suite's full output.

### Red, then green (CI)

- **Red** at `ae0212f` (the gate, its tools and its CI job; no kernel): run **37701781024**, job 113066677789 (log `473f302a…`): mpx3-loader 0 PASS, 30 FAIL, 0 SKIP lines (L0 both tiers `tools/build-kernel`, L1–L7 `no image` on all four legs).
- **Green** at `5ca6572` (the kernel): run **37702508398**, job 113069056009 (log `919d12c5…`): mpx3-loader **34 PASS, 0 FAIL, 0 SKIP**; every other job green but px08's suite (job 113069055939, R1: drift 3).

### The planted breaks (each its own push and CI run)

- **A** `675619b`: `fpu.switch` moves no state. Run **37703267001**, job 113071518881 (log `29afe0db…`): 30 PASS, 4 FAIL, 0 SKIP lines: only L5, all four legs, `spin 1: xmm BAD xmm0` and its exit_group 1 (spin 2 ends with its own pattern loaded last); hello's L2 still passes (the live state at its start was already the init state). Reverted.
- **B** `0fa333d`: the auxv carries `AT_IGNORE` where AT_PHNUM was. Run **37703912172**, job 113073631063 (log `8cb444bf…`): 30 PASS, 4 FAIL, 0 SKIP lines: only L2, all four legs (`AT_PHNUM 0 BAD` where the runner's Linux printed `AT_PHNUM 5 ok`; exit_group not 0). L8 still passes (wolf-hello fails on `brk` first). Reverted.

### Runs off CI

- **kasumi** (QEMU 11.1.1 TCG, `PAX_REQUIRE_UEFI=1`, `WOLF_PAIRING_REQUIRE_SIBLING=1`, lupin 0.1.48 present): §5's head.
- **hasu** (nix-shell QEMU, **KVM**, i7-12700KF): §5's head.

### The loader's transcript (kasumi TCG, native, BIOS, the first boot: `notes/px10/kasumi-tcg-first-boot-native-bios.serial.log`)

    PAX loader: static ELF from the initramfs
    paging: limine cr3 0x000000000ff15000, pax cr3 0x0000000000104000, 8 table frames
    initramfs: module 0xffff80000ff26000, 66884 bytes, 8 entries
    initramfs: dir 0 bin
    initramfs: file 11456 bin/hello
    …
    fpu: xsave 1, xcr0 0x0000000000000007, area 832 bytes, cr0.em 0, cr0.ts 0, cr4.osfxsr 1, cr4.osxsave 1
    user: exec pid 2 cr3 0x0000000000127000 entry 0x0000000000401000 rsp 0x00007fffffffee60 argc 3 envc 3, 4 PT_LOAD: 0x0000000000400000-0x00000000004001c8 r-- 0x0000000000401000-0x0000000000401a25 r-x 0x0000000000402000-0x0000000000402120 r-- 0x0000000000403120-0x0000000000414140 rw-, stack 32 pages below 0x00007ffffffff000
    argc 3
    argv[0] /bin/hello
    argv[1] one
    argv[2] two
    envp[0] HOME=/
    envp[1] TERM=linux
    envp[2] PAX=1
    AT_PAGESZ 4096
    AT_PHENT 56
    AT_PHNUM 7 ok
    AT_PHDR ok
    AT_ENTRY ok
    AT_RANDOM ok
    rsp 16-aligned
    rdx 0
    fcw 0x037f mxcsr 0x1f80
    data ok
    bss ok
    rodata ok
    xmm ok
    user: hello pid 2 exit_group 0 after 1 runs
    user: frames free 64984 before, 64920 with 1 processes, 64984 after
    user: exec pid 3 … (spin 1) / user: exec pid 4 … (spin 2)
    spin 1: xmm ok
    user: hello pid 3 exit_group 0 after 58 runs
    spin 2: xmm ok
    user: hello pid 4 exit_group 0 after 58 runs
    user: exec /bin/hello-pie: refused: ET_DYN: a PIE or shared object (PIE is later)
    user: exec /bin/hello-dyn: refused: PT_INTERP: a dynamic program (needs ld.so)
    user: exec /bin/hello32: refused: not ELFCLASS64 (a 32-bit file)
    user: exec /bin/hello-arm: refused: not for x86-64 (e_machine)
    user: exec /etc/motd: refused: too small for an ELF header
    user: exec /bin/nothing: refused: no such file
    user: ticks in ring 3 231
    halt

(frames lines between the refusals elided; every batch `A / A / A`.)
And the census subject on PAX (CI, every leg):

    user: exec pid 5 cr3 0x0000000000180000 entry 0x0000000000237740 rsp 0x00007fffffffee70 argc 1 envc 3, 4 PT_LOAD: 0x0000000000200000-0x0000000000236720 r-- 0x0000000000237740-0x00000000002ef2b0 r-x 0x00000000002f02b0-0x00000000002f7000 rw- 0x00000000002f7380-0x00000000002feff8 rw-, stack 32 pages below 0x00007ffffffff000
    user: wolf-hello pid 5 syscall 12: -ENOSYS
    user: wolf-hello pid 5 syscall 12: -ENOSYS
    user: wolf-hello pid 5 syscall 9: -ENOSYS
    Fatal glibc error: Cannot allocate TLS block
    user: wolf-hello pid 5 exit_group 127 after 1 runs

### The gap to M-PX3, by system call

What PAX answers after px10: `write` (1), `exit` (60), `exit_group`
(231); every other number `-ENOSYS`; a process's start is the kernel's
own (`execve`'s role). Measured with the census subject (a wolf 0.2.25
`print` program linked static against Ubuntu's glibc), in the order it
makes them on Linux (strace) and what PAX does with each:

| # | call | nr | on Linux | on PAX now | px04's verdict for the static boreutils suite | needed for wolf-hello to print |
|---|---|---|---|---|---|---|
| 1 | `brk` | 12 | `brk(NULL)`, then +0xd80: the TLS block and the thread control block | `-ENOSYS` | tolerated (with `mmap`) | **yes**: one of `brk` or anonymous `mmap`; with both `-ENOSYS` glibc stops here, exit 127 |
| 2 | `arch_prctl` | 158 | `ARCH_SET_FS` | not reached | required | **yes**, and FS base saved per thread (IA32_FS_BASE at the switch, beside the FPU state) |
| 3 | `set_tid_address` | 218 | | not reached | tolerated | no |
| 4 | `set_robust_list` | 273 | | not reached | tolerated | no |
| 5 | `rseq` | 334 | | not reached | tolerated | no |
| 6 | `prlimit64` | 302 | `RLIMIT_STACK` | not reached | tolerated | no |
| 7 | `readlinkat` | 267 | `/proc/self/exe` | not reached | tolerated | no |
| 8 | `getrandom` | 318 | 8 bytes (16 on kasumi's glibc too) | not reached | degraded (`sort`) | not to print |
| 9 | `brk` ×2 | 12 | the heap | | | (as 1) |
| 10 | `mprotect` | 10 | RELRO read-only | not reached | required | **yes** |
| 11 | `write` | 1 | | **implemented** | degraded | — |
| 12 | `exit_group` | 231 | | **implemented** | degraded (fatal in practice) | — |

So **wolf-hello needs three calls PAX lacks: `brk` (or anonymous
`mmap`), `arch_prctl(ARCH_SET_FS)` with FS per thread, and `mprotect`**;
the other five it makes may answer `-ENOSYS`. The static boreutils
suite (docs/CENSUS.md's 14) needs those three plus `read`, `openat`,
`close`, `fstat`, `getcwd`, `getdents64`, `getrandom`,
`clock_nanosleep`: **11 calls** between PAX and M-PX3, the first fatal
one `brk`/`mmap`. Beyond calls: `/proc/self/exe` (tolerated), the
files lane's paths, and AVX-512 state (XCR0 bits 5–7) for a glibc built
for x86-64-v4, on a CPU that has it.

### Filed

Nothing upstream: every wolf refusal met is a documented rule (E0008
reserved words, E0805 `byte`'s cast set, E0401 with
`[type.err.alias.transparent]`). No pax issue names this work.
