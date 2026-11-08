# px106 — passwords (P5 U8, the second half)

Base: pax trunk `7e65c2ce`. The claim, here and wherever this lane writes:
**enforced for honest programs; not a boundary against an attacker**
(ruling #75 R6). The kernel has never been fuzzed or audited and loads
programs at fixed addresses. R1 stands: no password in any published image.

## 1. What this lane does

- **`/etc/shadow`**, root's, 0600 (R-px106-1), one line an account, locked
  by default; the hash is wolf-std's scrypt in crypt(5)'s `$7$` form (sc80),
  named in one module, `user/auth/pwhash.lu`.
- **`user/auth/`**, three modules four programs share: `pwhash.lu` (the
  binding), `shadow.lu` (the file read and written whole, a lock, the
  first-boot rule's question) and `secret.lu` (a password read from
  /dev/tty with the echo off, the mode put back; the terminal's number and
  session from /proc/self/stat).
- **`passwd`** (`user/passwd`, 04755), **`login`** (`user/login`, 0755: the
  installed console, pid 1), **`su`** (04755 now: the target's password,
  one try) and **`sudo`** (the caller's password, three tries, `-S`, `-n`,
  `-p`; the timestamp at `/var/run/sudo/ts/<uid>`; the log's refusals), all
  built by `tools/mkauth` with one toolchain file (wolf 0.2.36,
  `user/auth/wolf-toolchain.toml`).
- **The installer** writes `/etc/shadow` with every account locked, and its
  guided form asks for root's and the user's passwords (`passwd -R` on the
  accounts it will write); it makes the user a member of group `sudo`
  (`sudo:x:27:NAME`). **The upgrade** never touches `/etc/shadow`, and
  makes one, every account locked, when the install has none. No manifest
  lists it. It makes uid 1000 a member of `sudo` in the user's
  `/etc/group` (`user/install/sudogroup.lu`, R-px106-6 B3).
- **`/etc/sudoers`** is Ubuntu's shape (R-px106-6 B3): `root
  ALL=(ALL:ALL) ALL` and `%sudo ALL=(ALL:ALL) ALL`, so the user is asked
  their own password.
- **The images** carry the four programs and no `/etc/shadow`.
- **`tests/mpx5-sudo`** gains six typed sessions with passwords made at run
  time (`pw`, `login`, `login-max`, `login-first`, `admin`, `login-trap`),
  typed at PAX's console and, with the same keys, at PAX's programs and
  Ubuntu's own in a container (`notes/px106/auth-ct.sh`); `login-first` and
  `login-trap` have no Ubuntu side. The differences are named in
  `notes/px106/named.txt`.

## 2. Rulings

- **R-px106-1 (ruled A):** `/etc/shadow` is 0600 root:root. Ubuntu's is
  0640 root:shadow, read through the group by `unix_chkpwd`, `chage` and
  `expiry` (2755 root:shadow); PAX has no set-group-ID reader, every reader
  is root (login run by root; su, sudo and passwd set-user-ID root).
- **R-px106-2 (ruled A):** a wolf `/bin/login` is the installed system's
  `/etc/pax-run`, pid 1 and the leader of the console's session. **The
  first-boot rule:** while no account in `/etc/shadow` has a password PAX can
  check (every line locked, or no file), login lets `root` in with no
  password and prints one line saying so; once one exists, the normal rules
  hold. The dev and release images keep R2's root shell; the stick keeps its
  live root entry. An unconfigured system is exactly as open as an installed
  PAX was before px106 until its owner sets a password (the README says so).
  R-px106-9 narrows "an account" to the accounts that can reach root.
- **R-px106-3 (ruled):** login gives 5 tries and Ubuntu's words (`Maximum
  number of tries exceeded (5)`), and times out after 60 s (`Login timed
  out after 60 seconds.`).
- **R-px106-4 (ruled):** a locked or unknown account is asked for a password
  and answers `Login incorrect`, so the console never says which accounts
  exist; the rows name the locked case.
- **Accepted as listed:** su with one try, at 04755; mpx5-accounts'
  real-root recording made again under QEMU with the build host's own
  kernel; the timestamp at `/var/run/sudo/ts/<uid>` in PAX's own format,
  keyed by terminal and session, void across reboots; the toolchain; the
  installer writing an all-locked shadow, then `passwd -R`; Ubuntu's
  per-attempt delays and caps.
- **R-px106-5 (the cost), ruled (accepted as recommended): N = 2^17, r = 8,
  p = 1** (128 MiB a hash; the cap is the shipped cost's working memory by
  wolf-std's own account, `scrypt.memory`, 134,238,240 octets, so PAX checks
  no string dearer than its own; a flat 128 MiB refused the shipped strings
  themselves, which P2 `pw`, P2 `login-first` and U15 caught). Measured by P7 on PAX under KVM on a laptop
  i7-10870H (the 860's machine is an i9-11900K, the same era, a little
  faster a thread), three runs each, in ms:

  | N, r, p | memory | PAX, KVM | PAX, TCG | Linux, native |
  |---|---|---|---|---|
  | 2^14, 8, 1 | 16 MiB | 90-100 | 480-510 | 46-53 |
  | 2^15, 8, 1 | 32 MiB | 200 | 960-970 | |
  | 2^16, 8, 1 | 64 MiB | 370-380 | 1930-1950 | 214-233 |
  | **2^17, 8, 1** | **128 MiB** | **620-740** | **3280-3700** | **429-433** |
  | 2^15, 8, 4 | 32 MiB | 440 | 3290-3310 | |
  | 2^16, 8, 2 | 64 MiB | 440-450 | 3300-3390 | |
  | 2^16, 8, 4 | 64 MiB | 870-880 | 6530-6570 | 782-786 |

  (TCG and Linux on the other build host's E-cores, a light job; the
  Linux peak RSS is the cost's memory plus about 1 MiB: 17, 65, 65 and
  129 MiB.) Options: (A) 2^17, 8, 1 — in the band, and the memory grows
  with the time, which is what makes a guess dear; (B) 2^16, 8, 4 — in the
  band at half the memory, the time bought with p, which costs a guesser
  no memory; (C) 2^16, 8, 1 — mkpasswd's memory, under the band; (D) the
  2^14 of the first draft, a tenth of the band. Every test machine that
  hashes a password has 512 MiB or more.
- **R-px106-6 (the user's sudo rule), ruled B, as B3: sudo asks for the
  password, as Ubuntu does.** As first built, uid 1000
  kept px103's `#1000 ALL=(ALL:ALL) NOPASSWD: ALL`. (B), the same line
  asking a password, was a stop before it was built: an install whose owner
  answered `n` at both password questions, and every install upgraded from
  before px106, has root and uid 1000 locked, and its user would have no way
  to root but the console's open door, which any password (lobo's) shut.
  **B3** is Ubuntu's own shape: the shipped policy is `root ALL=(ALL:ALL)
  ALL` and `%sudo ALL=(ALL:ALL) ALL` (Ubuntu's stock `/etc/sudoers` has
  both, measured in the container), and group `sudo` is gid 27, Ubuntu's.
  Ubuntu's `%admin ALL=(ALL) ALL` is left out: PAX has never had an `admin`
  group, and a rule for a group nobody can be in is a rule nobody reads. A
  fresh install writes `sudo:x:27:NAME`. An upgrade makes uid 1000 (named by
  `/etc/passwd`) a member in the user's `/etc/group`: the line appended when
  there is none, the name added to its members when it lacks it, nothing when
  it is there, every other line byte for byte; a second upgrade changes
  nothing. gid 27 held by a group not named `sudo` refuses the upgrade by
  name, before anything is written, since the file is the user's. A `sudo`
  line at another gid is refused the same way (my choice, not ruled: merging
  would give `id` a `sudo` that is not Ubuntu's gid, and moving it would
  rewrite the user's line). The rows: the prepare unit's `I-sudo-group-*`
  (append, no final newline, add, add to an empty list, member, idempotent,
  the two refusals, the fresh install), `admin` in tests/mpx5-sudo (pax in
  sudo, each side on its own shipped policy: PAX's `user/sudo/sudoers`
  against Ubuntu's stock file), and U13 (the upgraded user in sudo, `sudo
  -n` refused, then `passwd`, then sudo asking).
- **R-px106-9 (the door, under B3), ruled A.** The first-boot rule's
  "an account" is the accounts that can reach root: root itself and every
  member of `sudo` (its `/etc/group` members, and each account whose
  `/etc/passwd` group is sudo's gid). While none has a password PAX can
  check, login lets root in with no password and says so (`PAX: no password
  is set for root or for group sudo, so root logs in without one; set one
  with passwd.`); a password for any other account leaves the door open, so
  the console never ends with no way to root. `login-trap` is the row: root
  sets lobo a password, `exec /bin/login`, and root is let in again; it was
  red at the old rule (`shadow_any_usable`).
- **R-px106-7 (a reboot voids sudo's records), ruled (accepted): (A).**
  wolf's monotonic clock counts from a process-local
  anchor (wolf-lang spec `[os.clock.ns]`), so the first draft's boot field
  (the wall clock less the monotonic) was each process's start, and a
  record went stale a few seconds after it was written (P2 caught it: sudo
  asked again at once). (A) the records keep only the wall clock's time,
  and the installed system's pid 1, /bin/login, empties
  `/var/run/sudo/ts` when it starts, as Linux's /run is a new tmpfs at
  each boot (the images hold /var in their RAM archive); a record from the
  future is void. (B) a boot id from the kernel (Linux's
  /proc/sys/kernel/random/boot_id), a kernel row of its own. (C) the wall
  clock alone: a reboot inside the timeout keeps the records.
- **R-px106-8 (the sessions' cost), ruled (accepted): (A).**
  (A) tests/mpx5-sudo makes its sessions' lines at 2^14 (`mkshadow
  --cost`); what passwd writes in a session is at the shipped cost (P5
  reads bob's line), and P7 measures the shipped cost. CI runs QEMU under
  TCG, where 2^17 takes 3-8 s a check and login-max's five tries would
  meet login's 60 s. (B) every line at the shipped cost, and login-max
  under TCG left to the runner's speed.

## 3. Named differences

PAX's programs against Ubuntu 24.04's, by session (`notes/px106/named.txt`
holds the rules the comparison reads; px103's `notes/px103/ctnamed.txt`
loses its three password names: PAX's sudo asks now):

- the first-boot rule (login-first) and pid 1's new login after five
  failures or the timeout (login-max): no Ubuntu side, held to PAX's own
  rows (`tests/mpx5-sudo.d/*.pax`);
- `/etc/shadow`'s mode (R-px106-1); the terminal's group (Ubuntu's `tty`);
- `passwd -S` of an account with no shadow line (PAX: locked; Ubuntu reads
  `x` and says `P`); pam_unix's other `obscure` checks;
- the timestamp's file format (Ubuntu's is binary records); sudo's prompt
  never times out (`passwd_timeout` is not built);
- wolf-std's: a zero byte in a password is hashed (crypt(3) stops there).
- the shipped policy (R-px106-6 B3): Ubuntu's `%admin` line is left out;
  `admin` compares PAX's sudo on PAX's sudoers with Ubuntu's on its stock
  one, with the user in sudo on each side, and the sessions are the same.
- the first-boot door (R-px106-9): Ubuntu has none (its installer makes the
  first user's password); `login-trap` is held to PAX's own row.
- an account in no rule refused under `-n` (`a password is required`): Ubuntu
  logs it only when the policy says `Defaults mail_badpass`, which its stock
  policy does (measured: PAX's shipped rules alone, then each stock line
  added; with a terminal or without, with a password or locked, at uid 990
  or 1502, the logfile line anywhere). PAX's sudo sends no mail and refuses
  that Default by name, so under any policy it reads the two agree: no
  entry (U14's lobo).
- the delays: Ubuntu's are PAM's, spread about their value (measured in
  the same container: su and login 2.77-3.33 s, sudo 1.66-2.61 s); PAX's
  are the nominal 3 s and 2 s every time, so P3's floors (2.9 s, 1.9 s)
  hold PAX's, and Ubuntu's are printed beside them, never judged.
- the upgrade (U14): px103's N1 is gone (lobo's two refusals under `-n`
  are Linux's words now, and neither side logs them).

**What the comparison found** (each fixed, the row that caught it named):
P2 `pw` caught passwd naming another user's account before the
permission (`passwd -l bob` as pax is `Permission denied.`, which
Ubuntu says for `-l`, `-u` and `-d` before it looks the name up, and the
usage before that when no name is given), and sudo asking again at once
after a good password (R-px106-7); P4 caught su's prompt on standard
output (Ubuntu's goes to standard error: the prediction was wrong) and
`sudo -S` at the end of its input (Ubuntu ends the prompt's line first);
L1 caught sudo asking `pax` for `-u pax -g pack` (the caller as themself
with one of their own groups asks nothing) and a race in px103's harness
(the shell's `Terminated` line, counted now, not placed); P1 caught the
log's `COMMAND=/bin/id` against the container's `/usr/bin/id` (the test
image has both now).
mpx5-accounts' A0 linux and A1 caught the container's /dev: a rootless
engine's `/dev/tty` is the host's node bound onto a placeholder file, which
linux-tree's plain bind of /dev leaves out, so su (as pax) was refused
/dev/tty there and took its no-terminal path, ending `Password: ` with no
newline, where real root's recording and PAX end the line. The Linux side
binds /dev whole now (`--rdev`). It also showed a code gap: Ubuntu's su
ends the line with a terminal on standard input and no controlling one
(measured under script(1) and setsid), and PAX's did not; P4's
`su-tty-no-ctty` row was committed first and is red at the programs
before the fix.

## 4. What is not done

(filled at the prepared head)

## 5. Evidence index

(filled at the prepared head)
