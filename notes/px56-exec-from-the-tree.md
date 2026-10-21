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

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | a copy, a page rewritten in place, an archive text overwritten, a copy unlinked and run by `/proc/self/fd/N` (exe `<path> (deleted)`, name `N`) and by `execveat(N, "", AT_EMPTY_PATH)` (AT_EXECFN `/dev/fd/N`, name `N`, weak), a link (AT_EXECFN and name the link's, exe the target's): all run, root and 1000:1000 | every row as predicted on real root's guest, twice, the same bytes, root and 1000:1000, and the container's the same — **but `execveat(N, "", AT_EMPTY_PATH)` names the program by its file (`gone`), not `N`**: the weak point; and for a script so run, by its interpreter's file (`execs`) | right but the weak point |
| P2 | the refusal table, root \| user (below, §B); ETXTBSY for a file held open for writing, for `open(O_WRONLY)`/`O_RDWR` and `truncate` of a running program's file, `unlink` 0 (weak); ENOEXEC for text, empty and `\x7fELF` alone; execveat's EINVAL, ELOOP, ENOTDIR, EBADF | every row as predicted, the weak point held (7.2.8 still refuses writes to a running program: ETXTBSY) | right |
| P3 | `#!` as `execve(2)` says: argv[0] dropped, `interp [arg] path args`; blanks and tabs; no newline the same; CR in the word; `#!` alone, `#!\n`, `#!` and blanks ENOEXEC; past 256 bytes the interpreter cut ENOEXEC, the argument cut (weak: the byte); missing ENOENT, a directory EACCES, no x EACCES, text ENOEXEC, out of reach EACCES; relative from the working directory; five scripts run, six ELOOP (weak: four); 0711 runs, 0644 EACCES; `/dev/fd/<dirfd>/s1`, `/dev/fd/<fd>`, close-on-exec ENOENT; a script open for writing ETXTBSY (weak); a set-ID script leaves the effective id 1000 | every row as predicted, the weak points: the cut is at byte 255 (a newline at byte 255 ends the line; at 256 it is not read), five scripts run and the sixth is ELOOP, a script open for writing ETXTBSY — **but `#!` alone (and `#!` and blanks with no newline, in a file that short) is EACCES**, not ENOEXEC: with no newline and no interpreter the empty name is looked up, the working directory; with a newline, or cut, ENOEXEC (the rows added in the second round, §C); and NUL: it ends the interpreter (`/bin/ex`: ENOENT) and the argument's text (`a\0b` is `a`; a NUL first gives the empty argument `""`) | right but `#!` alone |
| P4 | PAX byte-identical to P1–P3 at the first boot, root and user | **107 and 107 lines byte-identical at the first boot of the change**, root and `pax`, and the user's to the container's (J12, J3, `notes/px56/kasumi-first-mpx5-jobs-execs.out`) | right |
| P5 | the tree's read within 2% of the archive's: not kept | trunk's archive read 26.90 ms and 27.17 ms a round (600 rounds of the 0.8 MB probe, 180 of boreutils' `true`), the tree's 26.75 and 26.78: within 1.5%, the tree's the faster, inside the run-to-run spread (23.7 to 30.0 ms a batch on either kernel) (`notes/px56/kasumi-speed.txt`) | right |
| P6 | the typed session as the guest's at PAX's first boot, root and `pax`, the user's as the container's | 50 lines each, byte-identical at the first boot, root and `pax` and the container's (J12, J3) | right |

## A. What loads: exec from the tree (pax#95, items 1 and 4)

Linux 7.2.8 (real root's guest: kasumi's own kernel image `f4c00d5d…`
under QEMU 11.1.1, `notes/px52/vmjob.c` unchanged as pid 1, the suite
build's own execs archive; recorded twice, the same bytes,
`notes/px56/kasumi-recordings-twice.out`), as root and as 1000:1000, and
the container's user the same (J3): a copy of the probe written since
boot with `read` and `write` runs, AT_EXECFN the path as given (`./copy`
from its directory), `/proc/self/exe` the copy's path, the name its last
component cut to 15 bytes (`a-name-longer-t`); an archive copy of the
probe with the page holding its marker rewritten by `pwrite` runs the
new marker (`px56 marker B`: the rest of the file still the archive's);
an archive text file (0755, ENOEXEC as it is) overwritten with the
probe runs; a copy opened, unlinked and run by `/proc/self/fd/9` runs,
`/proc/self/exe` `…/gone (deleted)`, AT_EXECFN `/proc/self/fd/9`, the
name `9`; by `execveat(9, "", AT_EMPTY_PATH)` AT_EXECFN `/dev/fd/9` and
**the name `gone`**, the file's own; by a link, AT_EXECFN and the name
the link's, `/proc/self/exe` the copy's. The typed session (both): `cp
/bin/true t; ./t` 0, `cp /bin/false f; ./f` 1, `cat f > t; ./t` 1.

PAX: `kernel/elf` reads every byte through `tree.span`, so a file is
loaded from wherever its pages are (the archive in place, a written
page's frame, a hole); `kernel/files`' `exec_open` finds it and makes it
an open file of the process's (`A_EXE`), which is what `/proc/self/exe`
reads (px50's fd/ text: the directory and the name it has now, `<path>
(deleted)` once gone), what a fork shares and what a process's end lets
go; kernel-started programs (`exec_span`) are the tree's too
(`exec_kernel`). **Byte-identical at the first boot of the change**
(`notes/px56/kasumi-first-mpx5-jobs-execs.out`: J12 107 and 107 lines,
50 and 50; J3; J4; J6 nothing refused, -ENOSYS only 273 and 334).

**The archive's fast case (P5)**: trunk `241b322`'s loader against this
branch's, one archive (`notes/px56/speed.run`: `execs time 100
/bin/execs`, `execs time 30 /bin/true`, twice), three boots each,
interleaved, TCG, `taskset -c 0-3`: the archive's 26.90 ms (the probe)
and 27.17 ms (`true`) a round, the tree's 26.75 and 26.78 (780 rounds a
kernel; `notes/px56/kasumi-speed.txt`). Not kept.

## B. The refusals (the mode rule; items 1 and 3)

Real root's guest and the container, root | 1000:1000; PAX the same at
the first boot (`user/elf/execs.c`'s E, T and X rows):

| case | root | 1000:1000 |
|---|---|---|
| a missing file; a missing directory on the way; an empty path | ENOENT | ENOENT |
| a file on the way | ENOTDIR | ENOTDIR |
| a component of 256 bytes | ENAMETOOLONG | ENAMETOOLONG |
| a loop of links | ELOOP | ELOOP |
| a directory; `/dev/null`; a 0644 file | EACCES | EACCES |
| root's 0744 file | runs (7) | EACCES |
| root's 0701 file (execute, no read) | runs | runs |
| 0:1000's 0710 file | runs | runs |
| a 0755 file in root's 0700 directory | runs | EACCES |
| a 0755 text file with no `#!`; an empty 0755 file; `\x7fELF` alone | ENOEXEC | ENOEXEC |
| a file the caller holds open for writing | ETXTBSY | ETXTBSY |
| while it runs: `open` O_WRONLY, O_RDWR; `truncate` | ETXTBSY | ETXTBSY |
| while it runs: `open` O_RDONLY; `unlink` | 0 | 0 |
| a script open for writing; a script whose interpreter is | ETXTBSY | ETXTBSY |
| while a script runs: the script O_WRONLY / its interpreter O_WRONLY | 0 / ETXTBSY | 0 / ETXTBSY |
| execveat: an unknown flag | EINVAL | EINVAL |
| execveat: AT_SYMLINK_NOFOLLOW at a link (at a file: runs) | ELOOP | ELOOP |
| execveat: a file's descriptor and a name / and "" without AT_EMPTY_PATH | ENOTDIR / ENOENT | ENOTDIR / ENOENT |
| execveat: a closed descriptor, a name or AT_EMPTY_PATH | EBADF | EBADF |

ETXTBSY is PAX's now: a regular file's twelfth inode word (a
directory's parent's, a socket's record's; no file used it) counts the
programs running from it, `open` for writing and `truncate` answer
-ETXTBSY after the class rule while it is not 0, and `execve` of a file
some open file has for writing is -ETXTBSY.

## C. `#!` and ENOEXEC (pax#96, items 2 and 3)

Linux (the same guest, both actors; S rows): `#!/bin/execs say` run
with argv `zero a1 a2` gives the interpreter `/bin/execs say <path> a1
a2`, AT_EXECFN the script's path, `/proc/self/exe` the interpreter's,
the name the script's; no argument, no `say`; blanks and tabs after `#!`
skipped, the argument ONE string with its inner blanks and tabs (`one
two`, `x\ty`), stripped at both ends; no newline at the end the same; a
carriage return stays in its word (`/bin/execs\r` ENOENT, an argument
`x\r`); `#!\n` and `#!` and blanks and a newline ENOEXEC — **`#!` alone
and `#!` and blanks with no newline EACCES** (with no newline in a file
shorter than what is read, the empty name is looked up: the working
directory), `#!` and 298 blanks with no newline (cut) ENOEXEC; the line
is the first 256 bytes: a newline at byte 255 ends it, at 256 it is not
read and the line is cut at 255 (an interpreter ending at 252 to 255
runs, at 256 to 258 ENOEXEC; an argument ending at 252 to 255 is 239 to
242 bytes, past it 242); a NUL ends the interpreter (`/bin/ex`: ENOENT)
and the argument's text (`a\0b` is `a`, a NUL first `""`); an
interpreter missing ENOENT, a directory EACCES, with no execute bit
EACCES, text with no `#!` ENOEXEC, in root's 0700 directory runs for root
and EACCES for a user; a relative interpreter from the working
directory (from `/bin` runs, from `/` ENOENT); a chain of scripts:
**five run**, each level's interpreter, argument and path before the
ones after (`/bin/execs say c1 arg2 c2 arg3 … c5 z`), **six and seven
ELOOP**; root's 0711 script runs for a user; a 0644 script EACCES;
root's 04755 script leaves the effective id the caller's;
`execveat(dirfd, "s1")` hands `/dev/fd/8/s1`, AT_EMPTY_PATH `/dev/fd/9`
(the name then the interpreter's file's, `execs`), a close-on-exec fd or
dirfd ENOENT, an ELF by a close-on-exec dirfd runs.

PAX (`kernel/process`: `shebang`, `interp_args`, `run_file`): those
rules, measured, and no others; ENOEXEC for a file with no ELF magic or
shorter than an ELF header **with no `refused:` line**, so pelt's XCU
2.9.1.4 fallback fires; the `refused:` lines stay for an ELF PAX does not
run (ET_DYN, PT_INTERP, a 32-bit file). **Byte-identical at the first
boot**, root and `pax`, every S row (J12), and the session's: `#!/bin/cat
-n` numbers its own two lines, `#!/bin/sh` runs pelt on `s.sh` (`sh ran
./s.sh with 2 args: one two`), `#!/g/t/n.sh` (a script whose interpreter
is a script) numbers both, `./d4` (five deep) all six lines, `./d5`
`cannot be run`, 126; `nx.sh` without `x` `cannot be run`, 126; `#!/nope`
`not found`, 127; and the maintainer's three commands `hi`, 0.

## D. The suites that held px27's refusal (P7)

On kasumi (native, BIOS, TCG, every build in `px13-ubuntu`, each boot on
four cpus of its own; `notes/px56/kasumi-regress.out`):

- **mpx5-jobs**, every image: PASS (the execs image's J12 at the first
  boot, §A; every older image's recordings held: nothing they type
  moved).
- **mpx3-tree**: PASS once T2 moved: `~exec: a program copied since
  boot, run: status 7` (Linux's answer; 113, -EACCES, before), the
  `syscall 59` refusal out of `REFUSALS` (eight, not nine; the kernel
  counts eight) and out of `tests/mpx3-tree.d/probes-user.pax`.
- **mpx3-shell**: PASS once procs' S4 moved: its execve of `/etc/script`
  (text, mode 0755) is -ENOEXEC with no `refused:` line, Linux's own
  answer (px14 to px55 named it twice).
- **mpx5-users**: perm **382 of 382 lines Linux's** (339 before: A's 43
  `execve` rows, 13 of them root's, are Linux's now; `perm.pax` is the
  recording's bytes), no refusal; setid's copies run, 72 lines: the plain
  copy, 02745, the owner's own 06755 and the script (`#!` the plain copy)
  Linux's, every row that asks a set-ID bit PAX's (R5: no id raised,
  AT_SECURE 0, dumpable 1), no refusal; sig's set-ID target runs (as
  1000, R5) and settles, so its `!` line is gone (144 lines, Linux's
  count), its five reader rows of that target read a 1000 process's
  `/proc/<pid>`, its three sender rows stay PAX's (R5), six targets ended
  by the session, not five; `setid.pax`, `sig.pax` and the counts move
  with it.
- **mpx3-loader** (px10's, `exec_span` through the tree now): PASS, its
  six refusals by the same names.
- mpx5-accounts, mpx3-boreutils, mpx3-user, mpx3-threads: PASS
  unchanged. The network suites, mpx3-console, -screen, -speaker,
  -sound, -orchestra, the tour and the core suites: CI's (`kernel/sched`
  is in ruling #76's core list, so the pull request's run is every
  suite on the one leg).

## E. Plants (P8)

Each a branch never to be merged, one commit on the head
(`1475941`), run by dispatch on one leg, `-f tier=pr -f suites=mpx5-jobs
-f jobs_boots=execs:serial`. (A first dispatch of all three, runs
39613240023, 39613244187 and 39613248775, was red at the plan job, not
the suite: `tools/mkexecs` named `tools/mkcred` in a comment, so the CI
plan counted mpx5-users' credential probes as mpx5-jobs' too
(`tests/ci-plan` P2). Fixed in `1475941`, the plants rebased, run
again.)

| plant | branch, commit | break | CI |
|---|---|---|---|
| A (#95) | `px56-plant-a` `ea99b07` | `exec_open` refuses a file that is not still the archive's whole (px27's limit back) | run **39615469293**, mpx5-jobs job 119275479233: J12 red at every F row written since boot (the copy, its relative run, the long name, the page rewritten, the text overwritten, the unlinked copy by `/proc/self/fd/9` and by AT_EMPTY_PATH, the link), every S row (the scripts are written since boot), root and `pax`, J3 at the user's, J4; the session red at `./Script/greet.sh` (`cannot be run`, 126: the maintainer's own symptom), the copied `true` and `false`; J6 green (`notes/px56/ci-39615469293-plant-a.txt`) |
| B (#96) | `px56-plant-b` `4d0a371` | `#!` not read | run **39615475341**, job 119275491594: J12 red at the S rows (ENOEXEC where the interpreter ran), root and `pax`, J3, J4 (`#!/bin/execs say`, the chain's ELOOP); the session red at `#!/bin/cat -n` (pelt reads it as shell: `line: not found`, 127) and the chain (`ci-39615475341-plant-b.txt`) |
| C (ENOEXEC) | `px56-plant-c` `7e0343c` | a file with no ELF magic answers EACCES again | run **39615480343**, job 119275499871: J12 red at the archive text file and the three ENOEXEC rows (EACCES), root and `pax`, J3, J4; the session red at `./Script/greet.sh` (`cannot be run`, 126) (`ci-39615480343-plant-c.txt`) |

## F. CI

- The pull request's runs: named in the pull request and the hand-back
  (a commit naming them would move the head). `kernel/sched` and
  `boot/sched.S` are in ruling #76's core list, so the pull request's own
  run is every suite on the one leg (`tier pr`); under ruling #92 the
  lane hands back once it is green at the final head and `full-matrix`
  is on, and the orchestrator holds the `tier full` run.
- The plants' runs: §E. `tests/ci-plan` at the head: PASS, every one of
  the tracked paths known (the new probe, tool and keys derived from
  mpx5-jobs' and `tools/mkexecs`' own text).

## G. The playground (item 4)

The orchestrator's `~/lanes/orch-paxplay/build.sh` and `assemble.sh` on
kasumi, run unchanged but for the pax commit: the playground's pax tree
was px54's `39f8597` (`tools/mklope`, `user/shrc`: px54's, not on trunk),
so it moved to **`19f24e8`, a local merge of `39f8597` and this branch's
`b32a791`** (made in `~/lanes/px56/play`, never pushed; `kernel/` and
`boot/` byte-identical to `b32a791`'s), and `assemble.sh`'s one motd
line to `PAX playground: pax px54 39f8597 + px56 b32a791 (19f24e8),
wolf 0.2.33, pelt 90d7c64, boreutils cc64f68.` (it named `pax px54
39f8597` before; the script as it was: kasumi
`~/lanes/px56/ev/orch-assemble.sh.before`). Every step rc 0 (pelt, lope,
the 47 boreutils, `as`, su, play, the zone, kmain_console native).
**`pax-playground.iso`
`c9ce2cdacb3a5a1612710eedf20526fa2c6e092c45ef9470a92a9b072006f606`**
(71,782,400 bytes; px54's was `cc15c602…`, 71,751,680), `pax-smoke.iso`
`6b87d8f8…`. Booted once on kasumi (TCG) with
`notes/px56/playground.keys` typed at the console's pelt: `su pax`, `cd
/home/pax`, `mkdir Script`, then the maintainer's line — **`hi`, st=0**
— a `#!/bin/cat -n` script and a copied `/bin/true` (0); halted
(`notes/px56/kasumi-playground-session.txt`). Copied to nomad-1
`~/pax-playground/pax-playground.iso` over px54's, hashed there twice,
the same digest.

## 4. Evidence index

Shas are this branch's (`px56`, on pax trunk `241b322`); kasumi paths
are under `~/lanes/px56/`.

### What was written

- The prediction: `2b6faf0` (§1 to §3, before any change or
  measurement).
- The probe and its inputs: `cbd7a98` (`user/elf/execs.c`,
  `tools/mkexecs`), `173a056` (`user/console/execs.keys`), `1475941`
  (`tools/mkexecs`' comment: the CI plan reads names).
- Linux's recordings: `e0c5fea` (`tests/mpx5-jobs.d/linux/execs*`,
  `xsh*`, `vm-*.meta`), `e08fa73` (the scripts; the two recordings
  compared).
- The kernel: `d273284` (`kernel/tree`), `f1b483a` (`kernel/sched`),
  `e2e019e` (`kernel/files`), `d48ad8c` and `11ad9db` (`kernel/process`),
  `64dfe3b` (`kernel/user`), `afdb007` (`kernel/elf`), `6cb3efe`
  (`boot/sched.S`'s comment).
- The suites: `195c584` (`tests/mpx5-jobs`: the execs image, J12),
  `77e3eb3` (`tests/mpx3-tree`), `4d6c2e5` (`tests/mpx3-shell`),
  `79de2d8`, `3ed64de`, `5fed40e` (`perm.pax`, `setid.pax`, `sig.pax`),
  `2afa474` (`tests/mpx5-users`' counts and refusals).
- The words: `02db6c4`, `ed455b8` (`kernel/README.md`), `2a90093`
  (`docs/SOURCES.md`), `6fef3b1` (CHANGELOG), `0729d10` (README), and
  this note's.
- The scripts: `notes/px56/*.sh` (launch, build, boot, kbuild, sync,
  vm-rec, speed, regress, playground-boot).

### What was measured, and where it is

- **Linux's answers**: `tests/mpx5-jobs.d/linux/execs.tty`,
  `execs-user.tty` (107 lines each), `xsh.tty`, `xsh-user.tty` (50) and
  their `vm-*.meta` (kasumi's 7.2.8 `f4c00d5d…`, vmjob `2a3a7f57…` from
  `notes/px52/vmjob.c`, the execs archive `7627e1e7…`), made twice, the
  same bytes (`notes/px56/kasumi-recordings-twice.out`); round one (the
  first 101 lines, before §C's added rows) kasumi `vm/r1/`.
- **PAX's first boot**: `notes/px56/kasumi-first-mpx5-jobs-execs.out`
  (J12, J3, J4, J6, the container's J0).
- **The speed**: `notes/px56/kasumi-speed.txt`, `speed.run`.
- **The suites at the head on kasumi**: `notes/px56/kasumi-regress.out`
  (§D: mpx5-users' perm, setid and sig rows, and every suite's verdict).
- **The plants**: `notes/px56/ci-*-plant-*.txt`.
- **The playground**: `notes/px56/kasumi-playground-session.txt`.

### Measured, inferred, not verified

**Measured**: everything in §A to §G but what follows.

**Inferred**:
- That the archive's fast case would stay within the spread on a
  faster machine (KVM, real hardware): the tree's read adds a lookup a
  page to a copy of the page, measured only under TCG.
- That PAX's empty-interpreter answer (-EACCES, the working directory
  looked up as the empty name) is Linux's reason as well as its
  answer: black-box, only the answer was seen (a working directory is
  always a directory).

**Not verified**:
- Real root was one kernel build (kasumi's 7.2.8); CI's runner's kernel
  is the container's for the user's rows (J3), not measured here.
- `execve` of `/proc/self/exe` and `/proc/<pid>/exe` (to file, above);
  a `noexec` mount (PAX has none); whether a program run without read
  permission is dumpable; argv NULL; E2BIG past 64 KiB of vectors: none
  asked of Linux.
- UEFI, the release tier and more than one CPU: CI's full tier only; no
  hasu (KVM) run.

### Issues

- **To close at merge, by hand**: pax#95 (any file of the tree runs,
  the mode rule and the refusals measured, root and user; plant A
  39615469293), pax#96 (`#!` as Linux reads it, ENOEXEC; plants B
  39615475341 and C 39615480343).
- **Would file (none filed)**:
  1. pax: `execve` of `/proc/self/exe` (and `/proc/<pid>/exe`), the way
     a program re-runs itself on Linux (`proc(5)`: a link to the
     program's file): PAX's walk answers `/proc/self/exe` only to
     `readlink` and O_NOFOLLOW (px26), so, by its code, such an
     `execve` is -ENOENT; not measured here, not asked by any suite.

## 5. Done-when

- Branch `px56` on origin; the pax pull request (number in the
  hand-back), open, unmerged; `full-matrix` added at the final head once
  its `tier pr` run is green.
- The five sections §1 to §5; the items §A to §G.
- The test checklist:
  - [x] Linux measured first: the probe as root and as 1000:1000 and
        the typed session as both on real root's guest (twice, the same
        bytes) and in a container (the user's)
  - [x] PAX byte-identical at the first boot: execs, execs-user (107
        lines), xsh, xsh-user (50) (J12, J3, J4, J6)
  - [x] the archive's fast case measured against the tree's (780
        rounds a kernel): not kept
  - [x] `tests/mpx5-jobs` on kasumi, every image
  - [x] `tests/mpx3-tree`, `mpx3-shell`, `mpx5-users` (their
        expectations moved, §D), `mpx3-loader`, `mpx5-accounts`,
        `mpx3-boreutils`, `mpx3-user`, `mpx3-threads` on kasumi, native
        BIOS
  - [x] `tests/ci-plan`, every case
  - [x] plants A, B and C red in CI (39615469293, 39615475341,
        39615480343)
  - [x] the playground rebuilt (`c9ce2cda…`), the maintainer's session
        typed on it, copied to nomad-1 and hashed twice
  - [ ] `tier pr` green at the final head, `full-matrix` on: named in
        the pull request; `tier full` held by the orchestrator (ruling #92)
- `wolf/tools/lane-audit.sh pax px56 <PR>` exit status: named in the
  hand-back.
- Trees: kasumi `~/lanes/px56/` keeps `out/`, `ev/`, `vm/`, `bin/`,
  `cache/`; build directories and the `head`, `trunk`, `plant-*` and
  `play` worktrees removed at the end. Plant branches stay on origin,
  never to be merged.
