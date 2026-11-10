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

## Where it stands (2026-11-10, phase 2's third hand-back)

Light takes on the lane host (native tier), each read by its END lines:
- Step 1, sudo: red and green as the second hand-back said (4409352c red, 8dd84d84 green). The ssh row waits for
  burrow's session change.
- Step 3, the staged boot: green at 279da789 (T1-T6, both firmwares). Since then a refusal found after the attempts
  file writes its letter in the file's last byte (T two attempts, M no archive, E empty, N memory, P unmapped, R a
  read, D the digest, A no archive PAX reads; 6172829c), for the hook's reason: T3-T5 read it (rows f60379e6, red
  first). The rows' container must hold sfdisk (tools/mkdisk's oracle): the take image with it, not the net one.
- Step 4, pax-upgrade: tests/mpx6-install.d/pax-upgrade.py, rows P1-P28 on Linux (an image for the disk, a
  directory for the root, stand-ins for pax-install and reboot; `tests/mpx6-install --only pax-upgrade`, and in its
  ci path), red by name against a stub at 20498a98 (P1-P27; P28, pax-install's usage refusals, passes against the
  old pax-install too, which refuses any unknown option), green at bd875968 and again at the head. The program:
  user/install/pax-upgrade/main.lu (tools/mkinstall's mode `upgrade`), user/install/armed.lu (the record, both
  programs), `pax-install --upgrade --armed RECORD` (upgrade.lu), the entry template and the boot hook beside it.
  Installed as /bin/pax-upgrade (PATH and sudo's secure_path both hold /bin), so the entry's `init=/bin/pax-upgrade`:
  pid 1 with no arguments is `apply`.
  Where the design note's words became choices: the verdicts go to /var/log/pax-upgrade.log (0644, one line each),
  since the stage directory is root's 0700 and `status` needs no root; arm saves the ESP's configuration as it was
  (limine.conf.installed: every put-back writes those bytes) and the armed one (limine.conf.armed: the hook's re-arm
  after a cut past the ESP phase); the space check is the root's superblock free count against the archive's size
  plus 8 MiB (the received archive already holds its own bytes; "about twice the archive" before the send, as the
  README says); a fallback boot is known by the ESP still armed under the installed root, and reboots only when the
  kernel's letter says the staged kernel is the one running; a done upgrade with no verdict is known by the running
  /etc/pax-release being the record's; the ESP's kernel is emptied, not removed, by `clean` (paxfat removes no file).
- The CI wiring (the staged suite's job and the map; no step of its own above): the mpx6-staged job (needs plan, $PAX_LEGS; the suite takes --tier now), the tier job needs it, the
  map's lines; tests/ci-plan green at 2f5eac93 and the head. The P2 row "the GPT writer and the disk tools reach
  ..." lists mpx6-staged now (tools/mkdisk reaches it by the derivation); that changed line names an existing job
  whose name holds a host name, so the scrub grep counts it: held for a ruling, pushed only to the lane host.
- Step 5, the images: distribution-root installs /bin/pax-upgrade, /etc/pax-boot.d/pax-upgrade and
  /usr/share/pax-upgrade/entry (tests/distribution's rows first); mkdistribution builds pax-upgrade beside
  pax-install and links each archive as pax[-dev]-COMMIT.cpio, its sha256 in sha256.txt. Not yet run (a
  distribution build is a block take).
- Step 7, the README section: written (3ddc621e).
- Step 6, the leg: tests/mpx6-install.d/ssh-upgrade.py (rows S1-S4, below), in the net rig container on a copy of
  the probes' installed 860-shaped disk (the burrowd image) and that image's stick's archive repacked. BIOS, light
  take at ffa47874 (pre-reorder; the tree is the head's but for the held ci-plan line): S1 green (624 MB received
  in 37 s, armed with `sudo -k -S` over ssh, the staged boot's lines, the root at /mnt/target found by the arm's
  targets line on the AHCI disk, which is mount_upgrade's row under the staged word, the upgrade, the reboot,
  burrowd answering, status `upgraded` then `cleaned`); S2 green (the changed archive refused by the kernel, `D`, the
  installed system disarmed and rebooted, status says why); S3 green (QEMU killed 20 s into the send: nothing
  received; sent again whole); S4 green (QEMU killed once the upgrade's record was durable: the second staged boot
  finished it). The four in 570 s; UEFI the same four, green, in 557 s (light take at ffa47874). The kernel's
  mount line shows the AHCI model cut to 16 characters; the serial names the disk.
- The plant: px115-plant-age (the arm's age refusal taken out), predicted P10 red by name and every other row green.
  First at cc6c1e62: P10 red by name, and seven later rows red after it, since the rows shared the arm it left
  (predicted wrong); the rows now take back an arm a refusal row did not refuse (069cf95d), and at 70a3a00e (the
  plant on that) P10 alone is red, 27 of 28 held; the head green, 28 of 28 (853b15d0), the same take.
- Not yet: the final records (rebase after the queue ahead, every take again at the final head; the records into
  notes/px115/), a distribution build with the image's new files (a block take), the PR.
- Held: tests/ci-plan's one changed line names an existing CI job whose name holds a host name, so the public-text
  grep counts it. GitHub's px115 is the branch without that commit (a77d6f35, the history reordered so it is
  last); the lane's clone and the lane host hold it on top (ba974964). It goes up when that is ruled.

## The leg, as planned for the next session

A suite of its own (tests/mpx6-staged-ssh, or rows beside upgrade.py), in the net rig container (QEMU, OVMF, the
tap, dnsmasq, OpenSSH: notes/px115/probes/p2-transfer.py's harness is the pattern: wolf's password set by debugfs
at run time, the client's key in authorized_keys, igb on the tap, dnsmasq's lease):
1. The disk: a copy of an installed 860-shaped disk on the burrowd image (the probes' disk; burrowd and the
   /etc/pax-boot.d hooks are px112's, so the leg needs px112 merged, or its image), on ide-hd with the 860's model
   and a test serial. Onto it, on the host (debugfs, mtools): the head's /bin/pax-upgrade, /bin/pax-install, the
   hook, the entry, and the head's kernel at the ESP's /boot/pax (the installed system that "has pax-upgrade").
2. The archive sent: that stick's own archive repacked on the host with the head's kernel at /boot/pax, the head's
   pax-install, pax-upgrade, hook and entry, a marker file, and /etc/pax-release one second newer than the disk's.
3. Rows, BIOS and UEFI: receive over ssh (`ssh wolf@HOST 'pax-upgrade receive --sha256 D' < archive`), arm over
   ssh with `sudo -k -S` and --reboot; the staged boot (its serial lines: `staged: attempt 1 of 2`, `upgrade:
   ... on /mnt/target`: mount_upgrade's row on the AHCI disk); apply; the reboot; burrowd answers; `pax-upgrade
   status` says upgraded; the marker is on the root, the user's files kept, the staged files gone.
4. A failed apply falls back unchanged: the staged archive changed on the host after the arm (the kernel's `D`), the
   installed system boots, disarms, reboots into its own kernel; status says why; the root byte-identical in its
   files. A power cut during the receive (QEMU killed mid-send: nothing received, the system unchanged) and during
   the apply (QEMU killed after the staged boot began writing: the second attempt finishes it).
5. The plant: e.g. the hook's disarm removed, so the fallback row is red by name.
