# px115 phase 2: the plan

The decisions as ruled (the design note's section 3): 1A, 2B, 3B, 4B (never a NOPASSWD rule), 5A, 6B, 7 as
recommended; 8 split: burrowd's sessions (setsid per session, no controlling terminal) are burrow's own change,
not this branch's; sudo's no-terminal record is this branch's first change. Nothing here waits on burrow's change
until it lands: pax-upgrade is driven at the console, or with `sudo -k -S` under a burrowd built from that change.

Each step: its rows first, seen red by name, then the change, then the rows green in a light take (native BIOS),
then both firmwares; records on the lane host; the final records last, after the queue ahead merges.

1. sudo's record with no terminal (decision 8, sudo's half).
   - rows: `notes/px106/auth-ct.sh` sudo-n-pid-reused (a planted record of an earlier holder of the parent's
     pid), sudo-k-S-fresh (`sudo -k -S` reads the password's line with a record fresh); `user/elf/procs.c`
     start (/proc/PID/stat's starttime, PAX against Linux).
   - change: kernel/sched and kernel/procfs (a process's start tick, field 22); user/sudo (`ppid P start T sid
     S`).
   - and, under burrow's change: a second ssh session gets no free sudo after the first's `sudo -k -S`.
2. Decision 6 needs no build change: `/etc/pax-release` has carried `source-date-epoch EPOCH -` since 5c57fc56
   (2026-10-27, before any install there is); `arm` holds the archive's row to the installed one's.
3. The staged boot in the kernel (decisions 1A, 2B), under `pax.staged=<sha256>` with the installed `root=`:
   - after the disks come up: the attempts file (`/var/lib/pax-upgrade/attempts`, a fixed-size file the arm
     makes; one byte rewritten in place a boot, through the block layer); past two, the installed root;
   - the archive (`/var/lib/pax-upgrade/staged/archive`) read into frames mapped as one range, its SHA-256
     held to the word's; kernel/initramfs serves that range; kernel/tree adopts it as `/`;
   - any problem (missing, short, digest, memory): one line why, and the installed root boots as `root=` says;
   - success: `mount_upgrade` mounts the root at /mnt/target as from the stick; the run list is the one
     command `/usr/sbin/pax-upgrade apply`; its end, and a panic, reboot rather than halt;
   - rows: a new suite (`tests/mpx6-staged`): an installed-shape disk made on the host with a staged archive,
     BIOS and UEFI: `/` the archive, the target mounted, the count kept; a wrong digest, a missing archive,
     the third attempt: the installed root, each by name.
4. pax-upgrade (user/install): `receive` (as the user: `~/.pax-upgrade/`, the digest given, read back), `arm`
   (root: the checks, the ESP's files by paxfat read back, the configuration last; the arm record; the entry
   from the archive's own `/usr/share/pax-upgrade/entry`), `disarm`, `status`, `clean`, `apply` (the staged
   program), and the boot hook (`/etc/pax-boot.d/pax-upgrade`: the fallback's disarm, a cut upgrade's re-arm,
   the cleanup after success). `pax-install --upgrade --armed RECORD` (decision 5A).
5. The images: distribution-root installs pax-upgrade, its hook and the entry template; mkdistribution
   publishes the stick's own archive and its sha256 beside the stick (decision 3B).
6. The leg (tests/mpx6-install.d, beside upgrade.py): on the 860's chain under QEMU, BIOS and UEFI: the stick
   that brings pax-upgrade, then an image sent over ssh (or at the console until burrow's change lands): stage,
   verify, arm, apply, back on the network, status; each refusal by name; a failed apply falls back unchanged;
   a power cut during the receive and during the apply. The plant, red by name.
7. The README section: the three commands, and what to do when it does not come back.

## Where it stands (2026-11-10, the first hand-back of phase 2)

- Step 1: the rows (af66bc8a, e853faa5, c0c959f8, 8dd84d84) and the change (e856a57e, cddede57). procs' `start`
  seen red by name at e853faa5 (`the parent's set no, the child's set no`); the sudo row's first take passed at the
  old key because bash exec'd the last command in its own place (8dd84d84 makes it fork). Its red witness is the
  branch px115-red-sudo (the old key on top of the fixed row; never merged). On PAX itself pids are never reused
  (kernel/sched's `take_pid`), so the start time changes no PAX answer until they are; it is what makes PAX's sudo
  right where the container rows run it, on Linux. The ssh row (a second session after the first's `sudo -k -S`)
  needs burrow's change: today every ssh command shares the console's session and terminal.
- Step 2: nothing to build (above).
- Step 3: tests/mpx6-staged (231b3ce8) first, then the kernel (0cd76b45..5301923a); it compiles; its takes are the
  first runs. Not yet: `mount_upgrade` at /mnt/target under the staged word in a row (tools/mkdisk drops a
  configuration's module lines: the row must put the targets module back with mtools), the CI job and plan wiring
  for the new suite, a panic's reboot under the staged word (the attempts file bounds the tries; a panic halts).
- Steps 4 to 7: not begun.
