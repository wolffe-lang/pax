# px115 — upgrade PAX over ssh: the design, measured, before any code

The goal: from another machine on the network, send PAX an upgrade image, have PAX verify it, and upgrade the
installed system from it at the next boot, the machine coming back on the network by itself. The stick stays the
way back in. Not in scope: upgrading a running root in place, fetching from the internet, signatures, and
package-level upgrades.

The upgrade that runs today is px93's `pax-install --upgrade`: the stick's second Limine entry, "PAX: upgrade the
installed system", boots the stick's kernel with `pax.upgrade` and the stick's `/pax/install-targets` as a second
module; kernel/fstab's `mount_upgrade` mounts the listed disk's PAX root at `/mnt/target`; `/` is the stick's
archive in memory; the upgrade walks `/` as the new image and writes the target in a fixed order (its record, the
root, the ESP, the manifest, the record removed), and re-runs from its record after a cut (U7, Y11). This design
keeps that environment and that program, and changes where the environment boots from and who confirms.

This note is phase 1: the questions answered with evidence from the tree and from probes under QEMU, the decisions
that need a ruling (options, a recommendation each), what a first version cuts, and the prediction
(`notes/px115/prediction.txt`, committed before the probes' results were read). No feature code yet.

## 1. The probes and their records

Every probe ran under KVM on the lane host, as light jobs (two CPUs), in the rig container the upgrade legs use
(QEMU 8.2.2, OVMF, mtools, e2fsprogs, dnsmasq, OpenSSH 10.6p2 and 10.2p1), on copies of an installed 860-shaped
disk that px97's upgrade leg left (the 860's install chain, upgraded to px112's burrowd image `18544b79`), its QEMU
disk given a test model and serial. Scripts and records: `notes/px115/probes/`.

| probe | what | records |
|---|---|---|
| P1 | Limine 12.9.1 with a second entry made the default, BIOS and UEFI: unattended boot by index and by title, a kernel at another ESP path, a missing kernel, a missing module, a wrong blake2b hash, a key at the panic, the way back by the arrows (the last two and the marked reruns: P1b) | `p1-limine.py`, `p1/out/`, P1b `p1/out-b/` |
| P2 | `ssh USER@HOST 'cat > FILE' < FILE` into burrowd on the installed root: 16 MiB, 256 MiB, the whole 1.24 GB stick image; 64 MiB with 2, 10 and 30 ms added to the round trip; PAX's memory sampled during; `sudo` over ssh (P2c, P2d) | `p2-transfer.py`, `p2c-sudo.py`, `p2d-sudo-console.py`, `p2/` |
| P3 | the dev archive under gzip (Limine's `$` decompression) against the installed ESP's free space | `p3-gzip.txt` |
| P4 | the stick image's partitions and ESP: where its archive and kernel are, their sizes and digests | `p4-stick-esp.py`, `p4/` |

## 2. The five questions

### 2.1 Can the upgrade environment boot from the installed disk, unattended, one-shot, on BIOS and UEFI?

**Not as the stick's files.** Limine reads FAT12/16/32 and ISO 9660 only (its README, v12.9.1), so everything it
loads must sit on the installed disk's ESP, which is 64 MiB (`user/install/plan.lu`): 62,586,880 bytes free on an
installed disk (P1's `mdir`). The stick's archive (`0633f4d2`'s `/boot/initramfs.cpio`) is 608,078,908 bytes (P4);
gzip -9 makes the same image's dev archive 228,107,098 (P3), 3.6 times the free space. The kernel fits (2,820,168
bytes). So the kernel goes on the ESP and the archive stays on the root partition, read by PAX's own kernel
(decision 1).

**What Limine offers** (CONFIG.md, v12.9.1; P1, both firmwares):
- `default_entry` selects the entry booted when `timeout` runs out. P1: the installed `limine.conf` with a second
  entry and `default_entry: 2` booted entry 2 unattended (its `init=/bin/true` on PAX's serial) after the 3 s
  countdown, and at once with `timeout: 0` and `quiet: yes`; an entry named by its title the same; entry 2's kernel
  from another ESP path (`/pax-upgrade/pax`) the same.
- No one-shot of its own on BIOS. On UEFI the Boot Loader Interface's `LoaderEntryOneShot` variable takes
  precedence over `default_entry` for one boot, and `remember_last_entry` (UEFI only) restores the last entry. PAX
  writes no EFI variables (it calls no EFI runtime services), so neither is reachable from PAX today.
- A default entry whose kernel or module is missing, or whose blake2b hash does not match: `PANIC: limine: Failed to
  open executable with path ...`, `... module ...`, `PANIC: Blake2b hash for URI ... does not match!`, then `Press a
  key to return to menu.` It waits there for a key: no fallback to entry 1 and no reboot, `quiet` or not, BIOS and
  UEFI. A key at the panic returns to the menu with no countdown, the armed entry still highlighted: it waits,
  it does not loop (P1b); the up arrow and Enter then boot the installed entry to its login, BIOS and UEFI (P1b).
- So the one-shot is PAX's to make: the arm writes `default_entry`, and PAX consumes it (decision 2). The arm must
  write every file the armed entry names and read each back before it writes the configuration, and a cleanup must
  disarm before it removes any file the entry names.

**What the unattended mode needs that the menu path does not:**
1. the entry chosen with no key and no stick: an armed `limine.conf` on the installed ESP;
2. the archive from the root partition (decision 1);
3. the installed disk's own targets line, `/pax/install-targets` on the installed ESP (its model and serial as
   kernel/block reports them), so `mount_upgrade` mounts it at `/mnt/target` exactly as from the stick (the
   module path it looks for is already `/pax/install-targets`);
4. no typed confirmation: the arm is the confirmation (decision 5);
5. a program in place of the console's root shell: `init=` names it (kmain_console already reads `init=`);
6. an end with no one at the console: that program reboots, on success and on failure; under the staged word the
   kernel reboots, rather than halts, when that program ends or the kernel panics;
7. a verdict on the root, where the installed system's `pax-upgrade status` reads it;
8. the fallback (decision 2).

### 2.2 How a 1.2 GB image travels

burrowd has no sftp or scp subsystem, so the image goes as a command's standard input: `ssh USER@HOST 'cat >
FILE' < IMAGE`. P2: the rig's tap (a sub-millisecond round trip), PAX on its one CPU (`nproc` 1) with 4 GiB,
OpenSSH 10.2p1 by the client's key, each file read back by PAX's own `sha256sum` and held to the host's digest:

| sent | bytes | seconds | MB/s | read back equal | PAX's sha256sum |
|---|---:|---:|---:|---|---:|
| random, tap | 16,777,216 | 3.60 | 4.66 | yes | 12.1 MB/s |
| random, tap | 268,435,456 | 37.09 | 7.24 | yes | 13.8 MB/s |
| the stick image `0633f4d2`, tap | 1,242,562,560 | 148.59 | 8.36 | yes (`104d4869…`) | 17.9 MB/s |
| random, round trip 2.4 ms | 67,108,864 | 10.77 | 6.23 | yes | 10.3 MB/s |
| random, round trip 10.4 ms | 67,108,864 | 23.26 | 2.89 | yes | 11.8 MB/s |
| random, round trip 30.4 ms | 67,108,864 | 45.42 | 1.48 | yes | 15.1 MB/s |

(The round trips are TCP connects' to port 22 with netem's delay on the rig's side of the tap. A sampler of
`/proc/meminfo` and every `/proc/PID/status`, run over a second ssh session through the whole of each run, shared
PAX's one CPU.)

**Memory is not the limit.** PAX's MemAvailable fell by at most 44,472 kB during the 1.24 GB run (the sampler's
own processes included) and came back after it; the largest VmHWM of any burrowd process was 23,476 kB, `cat`'s
2,460 kB, flat whatever the size (the buffer cache is 512 frames; burrowd's channel is bounded).

**The limits found:**
1. **One CPU.** About 8.4 MB/s steady on the tap: burrowd's ChaCha20-Poly1305 in wolf, TCP, the pipe to `cat` and
   ext2's writes share PAX's one CPU.
2. **The 64 KiB TCP window, not overlapped with that work** (px108: PAX's TCP has no window scaling). The three
   delayed runs fit `t = N / 8.4 MB/s + (N / 64 KiB) x RTT` within 3 to 25 percent (10.5, 18.6 and 39.1 s
   predicted for 10.8, 23.3 and 45.4 measured): PAX's window stays shut while it works through what it holds, so
   each round trip is waited out in full.
3. Nothing else: 1.24 GB arrived exact in one connection.

What it means for a person: the archive alone (608 MB) takes about 75 s on a wired LAN, about 2 minutes on Wi-Fi
at 5 ms, about 6 minutes across 30 ms; the whole stick image twice that. Reading it back on PAX adds about
35 s per 608 MB (sha256sum at about 17 MB/s).

### 2.3 Root over ssh with no terminal

PAX's sudo (`user/sudo/sudo.lu`) reads the password from /dev/tty, or from standard input with `-S`
(`user/auth/secret.lu`'s `secret_read` takes one byte at a time up to a newline, so what follows the password's
line stays on standard input for the command). P2c and P2d found that over ssh this meets burrowd's sessions in a
way that matters before anything here ships:

- **burrowd's sessions are not sessions of their own.** A command run over ssh is in session 1, pid 1's, with the
  console as its controlling terminal (`/proc/self/stat`: session 1, tty_nr 1088, process group 2, the boot hook's;
  burrowd's server never calls setsid: `src/server/server.lu` at burrow `b6ecfd30`, the stick's, has none).
- **So a plain `sudo` over ssh asks on the machine's console** (`pax login: [sudo] password for wolf:` on the
  screen, P2c), and the ssh client waits with nothing shown. Keys typed at the console go to the login waiting
  there, not to sudo: the probe's typed password was echoed on the screen as a login name (P2d).
- **And burrowd stops answering.** From the moment that prompt appears, every new connection times out at the
  banner exchange (P2d: three tries while it waited, three more after the console was typed at, the machine never
  reachable again until QEMU was killed). Not diagnosed further; the likeliest cause is sudo turning the console's
  echo off from a background process group of the console's session, which stops that whole process group
  (burrowd's listener is in it) with SIGTTOU.
- **And sudo's timestamp is shared by every ssh session of the user.** Its key with a terminal is `tty NR sid SID`,
  the same for every ssh session (the console's, session 1): after one `sudo -S` with the password, a NEW ssh
  session's `sudo -n /bin/id` ran as root with no password (P2c), for the timestamp's 5 minutes. The same record
  makes `sudo -S` read no password at all, so the password's line goes to the command as data (P2c: `wc -c` saw
  1017 = 1000 + 17 bytes).
- `sudo -k -S` should be deterministic today, by the code: `-k` with a command sets the run's reset, so no record
  is read and none is written (`authenticate` in `user/sudo/sudo.lu`), and `-S` reads the password's line and opens
  no terminal. P2c held the parts with no record present (after `sudo -K`): a wrong line alone refused (`1 incorrect
  password attempt`), the right one run as root, `sudo -n` answered `a password is required`. `-k -S` with a fresh
  record present is not yet probed: a row of phase 2.

What must stay impossible, and does: root logs in over ssh by no means (P2: `root@` by the user's key, `Permission
denied (publickey,password)`, status 255; px112's B5 and Y13 by password); nothing here adds a sudoers rule or
changes burrowd's configuration. What must become impossible before this ships: an ssh command reaching the
console's terminal (decision 8).

### 2.4 Failure and power loss at each step

With the recommended decisions (1A, 2B, 3B, 4B, 5A):

| step | what it writes | a failure or a power cut there leaves | the way back |
|---|---|---|---|
| receive (the user, no root) | `~/.pax-upgrade/incoming` as it arrives, renamed to `received` only when its sha256 matches the one given | the installed system unchanged and a partial file; after a power cut a root not cleanly unmounted (PAX runs no fsck; the next boot says so once and mounts it) | send again; receive removes a partial file |
| arm, the checks (root) | the received file moved into `/var/lib/pax-upgrade/` (a rename, one file system), read back and hashed again; `/boot/pax` and `/etc/pax-release` read out of the archive; the age, space, disk and ESP checks | nothing armed | `pax-upgrade arm` again, or `pax-upgrade clean` |
| arm, the ESP | by `paxfat` through the disk's node: `/pax-upgrade/pax` and `/pax/install-targets`, each read back; then `/boot/limine/limine.conf` by `paxfat replace` (the old file or the new one, never a mix: px93's F5); the arm record on the root | before the configuration: not armed (files on the ESP that no entry names); after it: armed | `pax-upgrade disarm` |
| the staged boot, Limine | nothing | a file the entry names missing or damaged: Limine's panic, waiting for a key (P1); the arm's read-backs are there to make this unreachable | at the console: a key, then the installed entry (P1b) |
| the staged kernel, before the archive | the attempt count on the root (`/var/lib/pax-upgrade/attempts`), written through | a panic: under the staged word the kernel reboots and counts again; past two attempts it boots the installed root | automatic |
| the archive read and checked | nothing | missing, short, a digest that differs, or too little memory: the kernel boots the installed root instead; its boot hook disarms, records why, and reboots into its own kernel | automatic; `pax-upgrade status` says why |
| the upgrade (`pax-install --upgrade`, as qualified) | its record; the root's files, each to `.pax-tmp`, fsynced, checked, renamed; the ESP's kernel, Limine and `limine.conf` (which disarms); the manifest; the record removed | cut in the root phase: still armed, so the next boot resumes from the record (U7's, Y11's path) | automatic within the attempts; past them the installed system boots on a mixed root, and `pax-upgrade arm` again, or the stick's upgrade entry, finishes it from the record |
| | | cut after the ESP phase, before the record's removal: the new system boots with an incomplete record | its boot hook sees the record and arms once more |
| | | refused before any write (not PAX, too little space, an older image): nothing written | the program disarms and records the refusal by name |
| the verdict, the reboot | `/var/lib/pax-upgrade/status` | the upgraded system is complete; only the verdict is missing | `pax-upgrade status` reads the target's upgrade log instead |
| the upgraded system's first boot | its hook removes the staged files and the ESP's `/pax-upgrade/` | — | — |

What no row catches: a staged kernel that panics before it reaches the disk. It reboots under the staged word into
the same entry; while armed Limine's menu shows for 5 seconds, so a person at the console can choose the installed
entry; or the stick.

### 2.5 Staging: where, how much, what cleans it

- **Where.** The received file in the user's own `~/.pax-upgrade/` (no root needed to send it); staged, root's
  `/var/lib/pax-upgrade/` (0700) on the root partition, so the move is a rename. The staged kernel and the targets
  line on the ESP, at `/pax-upgrade/pax` and `/pax/install-targets`.
- **How much.** The archive alone (decision 3B): 608,078,908 bytes for `0633f4d2`; the kernel 2,820,168 on an ESP
  with 62.6 MB free. At apply `pax-install --upgrade` itself needs the bytes it writes, plus its largest file, plus
  8 MiB (`user/install/upgrade.lu`): at most about the archive's size again. So the arm refuses with less than about
  twice the archive free, 1.3 GB for this image. The whole stick image (decision 3A) would hold 1.24 GB more while it
  is received; the 860's root has hundreds of GB free.
- **What cleans it.** The upgraded system's first boot, after a verdict of success, removes the staged files and
  the ESP's `/pax-upgrade/` (the configuration already disarmed by the upgrade's ESP phase); after a failure they
  stay, so `arm` can run again; `pax-upgrade clean` (root, never while armed) removes them; a new receive replaces
  the last.

## 3. Decisions (options, a recommendation each)

**Decision 1: where the staged environment boots from.**
- A. Its kernel on the ESP (`/pax-upgrade/pax`), its archive on the root partition, read by PAX's kernel under a
  new word (`pax.staged=<sha256>`, beside the installed `root=`): after the disks come up the kernel reads the
  archive into memory mapped as one range, checks its digest, and kernel/initramfs serves it as `/`; then
  `mount_upgrade` mounts the root at `/mnt/target` as from the stick. The environment is the stick's, byte for
  byte, and the upgrade program is the qualified one. Cost: a kernel change in the boot path (kernel/fstab,
  kernel/initramfs, kmain_console), a few hundred lines and their rows.
- B. A small upgrade-only archive (init, the shell, pax-install, paxfat, paxgpt) on the ESP as a Limine module,
  and `pax-install --upgrade` reading the new image from the staged archive file instead of walking `/`. No kernel
  change for the archive, but a second source path in the upgrade, a new build artifact in every image, and an
  environment no row has qualified.
- C. The archive on the ESP, gzip-compressed for Limine's `$`: ruled out by P3 (228 MB against 62.6 MB free).
- **Recommended: A.**

**Decision 2: the one-shot.**
- A. Consumed first, in userland: the staged program's first act puts the installed `limine.conf` back (`paxfat
  replace`). Simple; but a failure before it (the archive unreadable, too little memory, a crash) boots the staged
  entry again at every boot, and a cut during the upgrade boots the installed system on a mixed root.
- B. Bounded attempts kept by the kernel: the staged kernel counts each attempt on the root before it reads the
  archive; past two, or on any problem with the archive, it boots the installed root instead, whose boot hook
  disarms, records why and reboots into the installed kernel. The upgrade's own ESP phase disarms on success; a cut
  during the upgrade resumes from pax-install's record at the next boot.
- C. A firmware one-shot: UEFI's `BootNext`, or Limine's `LoaderEntryOneShot`, EFI variables consumed before any
  kernel runs. Needs EFI runtime services in PAX, and covers UEFI only. Later, a lane of its own.
- **Recommended: B.** A is the cut if B's counter is judged too much for a first version.

**Decision 3: what is sent.**
- A. The stick image as published (1.24 GB, the README's sha256); `arm` reads the archive out of its ESP (`paxgpt`,
  `paxfat` on a file).
- B. The archive alone: the stick's own `/boot/initramfs.cpio`, published beside the stick with its own sha256
  (608 MB; P4: it is not byte for byte `tools/mkdistribution`'s `dev.cpio`, 1,632 bytes longer at `0633f4d2`, so the
  file published must be the stick's). Half the bytes and half the space; `arm` reads `/boot/pax` and
  `/etc/pax-release` out of it (a newc read).
- C. The dev ISO (615 MB): needs an ISO 9660 reader on PAX. No.
- **Recommended: B.**

**Decision 4: how the command gets root.**
- A. One stream: the password's line, then the image, into `sudo -k -S pax-upgrade stage`: the whole transfer runs
  as root, and a wrong password eats lines of the image before it refuses.
- B. Two steps: `pax-upgrade receive` as the user (no root: the 600 MB transfer never runs as root, and a failed
  one needs no password), then `sudo -k -S -p '' pax-upgrade arm` with the password's line alone on standard input.
- C. A `NOPASSWD:` rule for `/usr/sbin/pax-upgrade` in `/etc/sudoers.d`: PAX's sudoers subset matches a command by
  its path, not its arguments, so the rule covers every subcommand. Not shipped; a person may add it.
- **Recommended: B,** always with `-k`. Root over ssh stays refused whatever is chosen. When pseudo-terminals land
  (px111), `ssh -t USER@HOST sudo pax-upgrade arm` asks at the terminal as anywhere else.

**Decision 5: the confirmation.**
- A. The arm record is the confirmation: `pax-install --upgrade --armed RECORD` goes on without a typed line when
  the record names this target's PARTUUID, model and serial and the staged archive's sha256, and was written by
  root; the record and the plan go to the target's log as the typed line does.
- B. The staged program computes the scripted `--seed S --confirm LINE`: no change to pax-install, but it must
  reproduce `UPGRADE /dev/sdX <model> <serial> <seed>` exactly, its device letter the staged boot's.
- **Recommended: A.**

**Decision 6: an older image.**
- A. Refuse only the image already installed ("Nothing to change"), as the upgrade does now.
- B. A build-time line in `/etc/pax-release` (`built <SOURCE_DATE_EPOCH>`); `arm` refuses an image built before the
  installed one, by name; an install whose release has no such line is accepted, and the arm says so.
- C. No check.
- **Recommended: B.**

**Decision 7: who decides how a new image is booted.** The arm runs the installed (older) system's code; the boot
runs the new image's kernel. So the new archive carries its own entry template (`/usr/share/pax-upgrade/entry`),
which the arm fills (the paths, the digest, the root's PARTUUID); an archive without one is refused ("upgrade with
the stick"). A later image can then change its own words. Recommended, with no alternative worth a ruling.

**Decision 8: burrowd's sessions and sudo's timestamp (found by P2c and P2d).**
- A. Fixed in burrow before px112 merges: each session's command starts in a session of its own with no
  controlling terminal (setsid in the child before exec), as an ssh server does for a session with no
  pseudo-terminal; a plain `sudo` over ssh then refuses at once ("a terminal is required"), never the console, and
  burrowd keeps answering. With it, PAX's sudo keys a record with no terminal by `ppid PPID sid SID` plus the
  parent's start time, so a later process that reuses a pid matches no record. Rows in px112's suite (B-rows:
  `sudo` over ssh refused by name, a second session asked again, port 22 answering after) and in this lane's.
- B. Fixed here, in px115, as its first change.
- C. Not fixed; the README says `sudo -k -S` and never plain `sudo`.
- **Recommended: A.** It is a fault of burrowd today, on the stick the 860 runs: a person who types `ssh HOST sudo
  ...` loses ssh to the machine until it is power-cycled.

## 4. The commands, as the README would give them

    ssh YOU@HOST 'pax-upgrade receive --sha256 DIGEST' < pax-COMMIT.cpio
    read -s PASSWORD; printf '%s\n' "$PASSWORD" | ssh YOU@HOST "sudo -k -S -p '' pax-upgrade arm --reboot"
    ssh YOU@HOST pax-upgrade status

The first can be sent again after any failure. The second refuses by name: nothing received, a digest that
differs, an older image, too little space, an ESP configuration that is not the installer's, a second arm, a caller
that is not root. The third needs no root.

When it does not come back: at the console, Limine's menu shows for 5 seconds while armed; press a key, choose `PAX
ext2 developer preview` with the arrows and Enter (P1b); log in, `sudo pax-upgrade disarm`. Or boot the stick: its
upgrade entry mounts the root, and `pax-install --upgrade` finishes a cut upgrade from its record.

The first upgrade over ssh needs an installed system that already has `pax-upgrade`: the stick that brings it
installs or upgrades as today.

## 5. What a first version cuts

- Decision 2C (a firmware one-shot); a staged kernel that panics before the disk stays a console matter.
- Resuming a cut transfer: a failed receive is sent again whole.
- The stick image as the sent form (3A).
- An ESP configuration the user edited: refused by name, not merged.
- More than one staged image, and going back to the previous system after a successful upgrade (the stick is the
  way back).
- Progress over ssh beyond `pax-upgrade status`.
- The TCP window (px108's finding): a 608 MB archive over a LAN is minutes, not hours; not this lane's.
- Signatures (the package manager's signing keys come first) and fetching from the internet: out of scope.

## 6. The prediction's probe half, scored

| predicted | found |
|---|---|
| `default_entry: 2` boots entry 2 unattended; at once with `timeout: 0`/`quiet: yes`; by title the same; a kernel at another ESP path boots | **right**, both firmwares |
| a missing kernel or module: Limine stops on an error naming the path and waits for a key; no fallback, no reboot; `quiet` does not hide it | **right**: a `PANIC` and `Press a key to return to menu.` |
| a wrong blake2b hash: a panic that waits for a key | **right** |
| 256 MiB at 8 to 20 MB/s; 1.2 GB in 1 to 2.5 minutes, exact | **just under, then inside**: 7.24 MB/s; 148.6 s at 8.36 MB/s, exact |
| MemAvailable falls by under 32 MiB; burrowd's VmHWM under 64 MiB | **the first a little over** (43 MiB with the sampler's own processes); **the second right** (23 MB) |
| a 5 ms round trip: at most 13 MB/s, the window's own limit | **worse than the window alone**: 2.89 MB/s at 10.4 ms, where the window allows 6.3; the window's wait does not overlap PAX's work |
| the gzip'd archive several times the ESP's free space | **right**: 3.6 times |
| `sudo -S` over ssh: the password's line then data; the command sees the data's exact bytes | **wrong when a record is fresh** (the line goes to the command), **not predicted**: ssh commands share the console's session and terminal; a plain `sudo` asks on the console and burrowd stops answering; the record is shared by every ssh session |
