# px98 — den as an ordinary user: `fatal: denied` at the console

An ordinary user logged in at PAX's console, through the installed system's login, gets `fatal: denied` from `den
status`, in a fresh directory under `/tmp` and in their own repository, though the home directory, the repository and
every file in it are theirs and the modes are ordinary. PAX's own den rows run as root, or as a user whose standard
output is a file of their own, so nothing had exercised a user writing to the terminal.

## 1. Forbidden, and what was read

- **Clean room.** No kernel, firmware or driver source of any other system, and no Git source. den (version control in
  wolf, pinned at `13bc2caa` in `user/den.pin`) was read read-only for its file reads and their error rows only; on
  Linux it was run as a black box under `strace`.
- **Read:** `kernel/files/files.lu` (the walk, `openat`'s class check, `may`, `changeable`, `fchmodat`,
  `fchownat`, the console's nodes), `kernel/cred/cred.lu`, `user/su/su.lu`, `user/install/prepare.lu`
  (`installed_login`), `user/usb-login.sh`, `tests/mpx5-den`, `tests/mpx5-den.d/`, `tests/mpx5-users`,
  `tests/mpx5-accounts`, `tests/mpx6-install.d/den.py`, `user/elf/as.c`.
- **References:** `open(2)`, `chown(2)`, `chmod(2)`, `proc_pid_fd(5)` (a descriptor's entry reopens the file it
  names, asked of that file's owner and mode), `login(1)` and `login.defs(5)` (`TTYGROUP`, `TTYPERM`: a login gives
  its terminal to the user, by default the user's primary group and mode 0600), `su(1)`.

## 2. Inputs, verified

(Filled in as the lane runs: the base, the den pin, the hosts, the images.)

## 3. Prediction, scored

Written before the first change (2026-11-04), from black-box runs of the live medium under QEMU (§4.1):

- **P1, the call.** den's `status` writes its report by opening `/dev/stdout` by name, write, create and append
  (wolf's `fs_open_mode(path, 2)`), where every other verb writes descriptor 1. `check-ignore` does the same when it
  prints a match. On PAX, `/dev/stdout` is a link to `/proc/self/fd/1`, which reopens the console's terminal, and the
  terminal is root's, mode 0600. `openat`'s class rule answers -EACCES to any other user, den names it `denied`, and
  prints `fatal: denied` with status 128. A user's shell gets the same for `echo x > /dev/stdout` and for
  `> /dev/stderr`.
- **P2, Linux.** The same den binary on Linux, as a non-root user, opens `/dev/stdout` the same way. It gets the same
  -EACCES whenever its standard output is a terminal or a file the user may not open, as after `su` from root's
  terminal. A Linux console login does not see it, because `login` gives the terminal to the user first.
- **P3, the rows, red first.** A new image in `tests/mpx5-den` boots the installed system's login (the text
  `pax-install` writes as `/etc/pax-login`) with `su`, an account `pax` (1000:1000) and the ext2 home disk. It logs in
  as `pax` and types, on the terminal, with nothing redirected: the terminal's owner and mode; `echo > /dev/stdout` and
  `> /dev/stderr`; `den init`, `status`, `add`, `commit`, `log --no-decorate` and `status` again, in a fresh directory
  under `/tmp` and under the home directory. Then it logs in as root. At the base these rows are red by name: the
  terminal `0 0 600` where `1000 1000 600` is held, `Permission denied` for the two streams, and `fatal: denied` from
  `den status`. Every other den verb is already green.
- **P4, the kernel.** The console's terminal nodes, the console's own descriptors with `/dev/ttyS0`, `/dev/tty0` and
  `/dev/console`, each keep an owner and a mode, root's and 0600 at boot. File-system user id 0 may `chown` and
  `fchown` them, and their owner or root may `chmod` and `fchmod` them, by the rules a file of the tree has. A user's
  `chown` of one is -EPERM. `/dev/tty` and every other node of `/dev` stay fixed (-EROFS, by name). Nothing else
  moves: every suite that lists `/dev` sees the same owners and modes at boot.
- **P5, the logins.** The installed login hands the terminal to the account before `su` drops to it: the account's
  user id, its primary group, mode 0600, as `login.defs(5)`'s default. A root login hands it back to root. The live
  login (root only) hands it to root. With P4 and P5, the rows of P3 go green with den unchanged.
- **P6, the plant.** The kernel's per-terminal owner taken away (the console nodes answer root's again) turns the
  terminal row and the den row red by name, and nothing else in the suite.
- **P7, the installed disk.** On a disk `pax-install` wrote, `den init` and `den log --no-decorate` already work for
  the user at the terminal. Only `status` (and `check-ignore` with a match) fails.

## 4. Evidence index

(Filled in as the lane runs.)

## 5. Done-when

(Filled in at the final head.)
