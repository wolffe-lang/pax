# px56 — Exec from the tree, and `#!` (pax#95, #96)

Contract: px56's, `sprints/pax/56-exec-from-the-tree/px56-exec-from-the-tree.md`
in wolffe-lang/wolf (planning trunk `809e40f`, read 2026-10-21), under
`sprints/RULES.md`. Branch `px56` in pax, cut from pax trunk `241b322`
(px55). §1 to §3 are committed before the first change to the kernel, a
tool, a probe, a test or CI, and before the first measurement.

The maintainer, in the 0.2.33 playground as `pax`: `echo 'echo hi' >
Script/greet.sh; chmod +x Script/greet.sh; ./Script/greet.sh` answered
`refused: a program written since boot (the loader reads the archive's
own bytes), -13` three times and `pelt: … cannot be run`. Two kernel
gaps: **#95** `execve` loads only an archive file whole (px27's loader
reads the initramfs module's bytes); **#96** no `#!` lines, and a text
file answers EACCES where Linux answers ENOEXEC, so pelt's XCU 2.9.1.4
fallback (a script with no `#!` is the shell's to run) never fires.

## 1. Forbidden, absolutely

- No kernel's source is read or searched for, Linux's above all, nor
  any libc's, shell's, container runtime's, init system's or QEMU's
  (ruling #22; RULES.md §1). Facts come from the man pages (`execve(2)`
  and its "Interpreter scripts" paragraph and NOTES, `execveat(2)`,
  `fexecve(3)`, `proc(5)`'s `/proc/pid/exe` and `comm`,
  `proc_pid_exe(5)`, `prctl(2)`'s PR_GET_NAME, `getauxval(3)`'s
  AT_EXECFN, `path_resolution(7)`, `open(2)`'s ETXTBSY, `truncate(2)`),
  POSIX.1-2024 (XCU 2.9.1.4, XSH `exec`), the allowed uapi headers
  (`linux/fcntl.h`: AT_EMPTY_PATH, AT_SYMLINK_NOFOLLOW;
  `asm-generic/errno*.h`), the syscall table (execveat 322), pax's own
  source, px50's to px55's notes, the org's own repositories read as the
  maintainer's code (pelt `be1a75d`'s `src/sh/exec.lu`: `is_script`, the
  fallback at `-125`; wolf-lang `v0.2.33`'s runtime as documentation of
  what wolf programs ask), and black-box runs: kasumi's own kernel
  image under QEMU with a static program as pid 1 (real root, px48's
  `vmjob` way, `notes/px52/vmjob.c` unchanged), a rootless container on
  kasumi for a user's rows, and CI's runner. `wolf/refs/repos/linux`
  stays sparse and is not opened.
- Every check gets a user row; every existing suite stays green as root
  and as a user. Signals, id changes and core dumps only inside QEMU or
  a container, never on a host; nothing in this lane signals a host
  process but the lane's own jobs, by recorded pid.
- Probe and test binaries static, built in `px13-ubuntu`, never with
  kasumi's CachyOS glibc (AVX-512). No build on nomad-1. kasumi under
  `bash`, long jobs `setsid -f` with a pid file, ended by that pid only
  (never by name, pattern or process group); work under `~/lanes/px56/`,
  pruned; never `/tmp`. Process, signal and terminal tests under
  `taskset -c 0-3`; SigBlk and SigIgn read before a signal row is
  called red. Ports 8080 and 8088 unused; nothing installed on any host;
  every other lane's directory untouched; `~/lanes/orch-paxplay/` only
  at the end, its `build.sh` and `assemble.sh` run unchanged but for the
  pax commit; px54's `user/` lope work not touched.
- Toolchains as pinned (px55's): wolf 0.2.33 `85dab5d7` (`4f955e8d…`),
  lupin 0.1.54, pelt `be1a75d`, boreutils `cc64f68`; none moved here
  (the 0.2.34 pins are px57's).
- No `rm` outside `~/lanes/px56/` and this worktree; no `git add -A`;
  nothing under `~/.claude`; no merge, no tag; no issue filed or closed
  (listed); no `2>/dev/null` on a checkout; no trailer on a commit or
  the PR. No other lane's run cancelled; plants by dispatch on one leg
  (`-f tier=pr -f suites=…`, mpx5-jobs with `-f jobs_boots=…`);
  `full-matrix` only once the head is final, never at open. "Seen red"
  cites a run. No assertion deleted or weakened, no timeout or retry as
  a fix. Nothing says "secure"; no word implying filming. If the harness
  refuses an action I stop and report.

## 2. Inputs, verified (2026-10-21)

| input | found |
|---|---|
| pax trunk | `241b322` (px55, PR #98 merged); its push run 39529980286 green, nightly 39594140929 green |
| planning repo | `809e40f` (crawl 54, batch 11: the contract) |
| open pax PRs | #99 (px54, lope, head `840728c` on `c8b48cb`, blocked on the org secret); px57 not launched |
| open pax issues | #55, #56, #62, #67, #90, #95, #96, #100–#104 |
| #95 | `kernel/process`' `execve` asks `kernel/files`' `exec_lookup` for the file: the walk, then -EACCES for a directory or a node that is not the tree's, the class's execute bit (px43, `may`), and then `tree.archive_entry` (the inode still the archive's bytes, whole): anything else is refused by name, R_EXEC, -EACCES. The loader (`kernel/elf`) reads one contiguous image (`initramfs.data(e)`), `build_stack`'s auxv and `image_top` read it too; the name is the archive entry's base name (`base_name(e)`, a pointer into the module); `/proc/self/exe` (`A_EXE`) is the archive entry + 1, its text `/` + the entry's name. Kernel-started programs (`exec_span`: init, the run list) look the path up in the archive (`initramfs.lookup_span`). `execveat` (322) is not dispatched (-ENOSYS) |
| #96 | nothing in `kernel/` reads `#!`. An archive file that is not an ELF answers -ENOEXEC with two `refused:` lines (`user: exec <path>: refused: not an ELF file`, `syscall 59: refused: not a static x86-64 ELF executable PAX runs, -8`; `tests/mpx3-shell`'s procs S4 holds them for `/etc/script`); a file written since boot answers R_EXEC's -EACCES before its format is read. pelt `be1a75d` `src/sh/exec.lu`: `spawn_fds`' `io` (wolf's word for ENOEXEC, wolf-lang#682) is `-125`, and then `is_script(path)` (text, no `#!`, no NUL in its first 256 bytes) runs `os_exe()` (pelt, by `/proc/self/exe`) on the script; `denied` (EACCES) is 126, `cannot be run` |
| suites that hold the refusal | `tests/mpx3-tree` T2 (`~exec: … status 113`, and `syscall 59: refused: a program written since boot …, -13` among probes-user's refusals: `tests/mpx3-tree.d/probes-user.pax`); `tests/mpx5-users`: perm (43 `execve` rows of section A and 43 refusal lines, `PERM_LINUX_LINES` 339 of 382), setid (14 refusals; its copies' rows `execve -13`, `tests/mpx5-users.d/setid.pax`), sig (one refusal; the set-ID target, `sig.pax`); `tests/mpx3-shell` procs S4 (`/etc/script`'s two lines) |
| pelt | `be1a75d` (px53's pin; static `7be05ec0…`, 15,200,336 bytes, built with pelt's own wolf 0.2.32 toolchain) |
| kasumi | Linux 7.2.8-1-cachyos (`vmlinuz` `f4c00d5d…`, the recordings' guest), 16 cpus, QEMU 11.1.1, `px13-ubuntu` `ad8964505189`, `/home` 24 GB free, load 6–10 (shared); `core_pattern` pipes to systemd-coredump |
| the playground | kasumi `~/lanes/orch-paxplay/`: `build.sh` and `assemble.sh`; its pax tree at px54's `39f8597` (it needs `tools/mklope` and `user/shrc`, px54's); `out/pax-playground.iso` 71,751,680 bytes of 2026-10-20 |

## 3. Prediction (committed before the first change and measurement)

A new probe, `user/elf/execs.c` (static, glibc; `tools/mkexecs`), runs
as root and as 1000:1000 (`as`) on real root's guest, in a container
(the user) and on PAX, in a new mpx5-jobs image `execs` whose archive
carries the cases with their owners and modes. Every line is `case:
answer`; a program it runs prints one `run:` line (its argv, AT_EXECFN,
`/proc/self/exe`, PR_GET_NAME's name) or exits with a status.

**P1. Linux, what loads (#95)**, the same as root and as 1000:1000: a
copy of the probe written since boot (read and write, 0755) runs: its
argv as given, AT_EXECFN the path as given, `/proc/self/exe` the copy's
path, its name the path's last component (15 bytes at most); an archive
ELF with one page rewritten in place (`pwrite`) runs the rewritten
bytes; an archive text file overwritten (O_TRUNC) with the probe's
bytes runs; a copy opened, unlinked and run by `/proc/self/fd/N` runs,
`/proc/self/exe` `<path> (deleted)`, AT_EXECFN `/proc/self/fd/N`, its
name `N`; by `execveat(N, "", argv, envp, AT_EMPTY_PATH)` runs,
AT_EXECFN `/dev/fd/N`, its name `N` (weak: a later kernel may name it
by the file); by a symbolic link, AT_EXECFN and the name the link's,
`/proc/self/exe` the target's.

**P2. Linux, the refusals (the mode rule)**, root | 1000:1000: a missing
file ENOENT | ENOENT; a missing directory on the way ENOENT | ENOENT; a
file on the way ENOTDIR | ENOTDIR; an empty path ENOENT; a component of
256 bytes ENAMETOOLONG; a loop of links ELOOP; a directory EACCES |
EACCES; `/dev/null` EACCES | EACCES; a 0644 file EACCES | EACCES (root:
some execute bit or none); root's 0744 file runs | EACCES; root's 0701
runs | runs (execute without read); 0:1000's 0710 runs | runs (the
group's class); a 0755 file in root's 0700 directory runs | EACCES;
**ETXTBSY** for a file the caller holds open for writing, and for
`open(O_WRONLY)` and `truncate` of a file a running process was loaded
from, `unlink` of it 0 (weak: whether 7.2.8 still denies writes to a
running program); ENOEXEC for a 0755 text file with no `#!`, an empty
0755 file and a file of `\x7fELF` alone; `execveat` with a flag it does
not know EINVAL, AT_SYMLINK_NOFOLLOW at a link ELOOP, a relative path
with a dirfd that is a file ENOTDIR, a closed dirfd EBADF.

**P3. Linux, `#!` (#96)**: a script `#!/bin/execs say` run with argv
`zero a1 a2`: the interpreter's argv `/bin/execs say <the script's path
as given> a1 a2` (argv[0] `zero` gone), AT_EXECFN the script's path,
`/proc/self/exe` `/bin/execs`, the name the script's last component; with
no argument the same without `say`; blanks and tabs after `#!` skipped,
the interpreter ends at the first blank or tab, the rest (blanks and
tabs at both ends stripped) is ONE argument with its inner blanks; a
last line with no newline the same; a carriage return before the newline
stays in the word it ends (`/bin/execs\r`: ENOENT; an argument `x\r`);
`#!` alone, `#!` and a newline, `#!` and blanks: ENOEXEC; a line longer
than the 256 bytes read: an interpreter cut by the end ENOEXEC, an
argument cut there passed cut (weak: the exact byte); an interpreter
that is missing ENOENT, a directory EACCES, without an execute bit
EACCES, a text file with one but no `#!` ENOEXEC, in a directory a user
may not search EACCES (root: runs); a relative interpreter from the
working directory; a chain of scripts, each the next one's interpreter,
the last one's an ELF: five run (each level's interpreter, argument and
path before the ones after), six ELOOP (weak: the limit may be four);
root's 0711 script run by a user runs (the kernel reads it; its
interpreter here does not); a 0644 script EACCES; `execveat(dirfd,
"s1")` hands the interpreter `/dev/fd/<dirfd>/s1`, AT_EMPTY_PATH
`/dev/fd/<fd>`, AT_EMPTY_PATH with a close-on-exec fd ENOENT; a script
open for writing ETXTBSY (weak); root's 04755 script run by a user:
the effective id stays 1000.

**P4. PAX after the change, byte-identical to P1–P3 at the first boot**
as root and as a user. The design: `kernel/elf` reads a file through the
tree (`tree.span`, a page at a time: an archive page in place, a written
page's frame, a hole's page of zeros), so every exec is the tree's;
`exec_lookup` answers the inode and the directory it was found in;
`#!` read from the first 256 bytes with `tree.span`, recursion to
Linux's limit, the argument vector rebuilt in `pax_argbuf`; ENOEXEC
with no `refused:` line for a file with no ELF magic and no `#!` (it is
Linux's answer), the `refused:` lines kept for what Linux runs and PAX
does not (ET_DYN, PT_INTERP, a 32-bit file); the running program an
open file of its own (`A_EXE` an open file + 1: `/proc/self/exe` its
path by px50's rules, `(deleted)` included; a fork shares it; ETXTBSY by
a count in the inode's twelfth word, which a regular file never used);
the name the path's last component, 15 bytes at most, in two new words
of the thread record (kernel/sched: copied by fork and threads);
`execveat` (322). Kernel-started programs (init, the run list) are
looked up in the tree too, not asked their mode (as before), refused by
the same names.

**P5. The speed (the archive's fast case).** The tree path costs a span
lookup a page and a lookup a header byte, against the archive's one
contiguous read: an archive program's exec, measured on PAX (TCG,
`taskset -c 0-3`, N fork–exec–wait rounds of boreutils' 14 MB `true` and
of the probe) at trunk and at the branch, **within 2% of trunk's**,
inside the run-to-run noise: the archive path is not kept.

**P6. The typed session, root and `pax`**, pelt at the prompt, in the
execs image (`user/console/execs.keys`, typed twice): the maintainer's
three commands (`mkdir Script` first) print `hi`; a copied `/bin/true`
and `/bin/false` 0 and 1; `cat f > t` (a program rewritten) 1; `#!/bin/cat
-n` (an interpreter with an argument) numbers its own lines; `#!/bin/sh`
runs pelt on it; a script whose interpreter is a script; a chain past
the limit `cannot be run`; a script without `x` `cannot be run`, 126; an
interpreter missing 127: **byte-identical to real root's recording at
PAX's first boot of it, root and `pax`, and the user's to the
container's**. pelt's three `refused:` lines are gone.

**P7. Existing suites move, and only these.** mpx3-tree T2: `~exec`
`status 7` (Linux's), the `syscall 59` refusal out of probes-user's
lines (`probes-user.pax` moves); mpx5-users: perm's 43 A rows Linux's
(`PERM_LINUX_LINES` 382 of 382), its 43 refusal lines gone; setid's 14
refusals gone and its copies run: the plain copy, root's runs of the
plain one, `02745` and the owner's own 06755 Linux's lines, the script
row Linux's (its interpreter the plain copy), every row that asks a
set-ID bit PAX's (R5: no id raised, AT_SECURE 0, dumpable 1); sig's
refusal gone, its set-ID target's three rows still PAX's (R5), `sig.pax`
moves; mpx3-shell's procs S4: `/etc/script`'s two refusal lines gone
(ENOEXEC is Linux's answer). Every other suite and every other
recording unchanged; `kernel/sched`'s change makes the PR's run every
suite (ruling #76's core list).

**P8. Plants**, each a branch never merged, one commit, by dispatch on
one leg: **A** (#95) `exec_lookup` refusing a file that is not the
archive's whole again: mpx5-jobs (`jobs_boots=execs:serial`) J12 red
at the copy, rewrite and unlinked rows, root and `pax`, and at the
session's copied-program rows; **B** (#96) `#!` not read (every script
ENOEXEC): J12 red at the script rows and the session's `#!` rows; **C**
(ENOEXEC) a text file EACCES again: J12 red at the ENOEXEC rows and the
session's `greet.sh` (`cannot be run`).
