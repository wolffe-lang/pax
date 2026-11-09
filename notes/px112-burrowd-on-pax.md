# px112 — burrowd on PAX (burrow's B6): started at boot, its host key made at the first boot, reached from the LAN

burrowd, burrow's ssh server, serves commands on Linux and macOS since burrow's B5. This lane puts it on PAX, started
at every boot by a hook pid 1 runs, with a host key the machine makes at its first boot and keeps; on an installed
system it listens on the LAN, and from another machine `ssh pax@<address> ls` and `git push <address>:repo` work, a
command through the account's shell and git through den's `upload-pack` and `receive-pack`. burrow's half (password
authentication against `/etc/shadow` with wolf-std's `$7$`, locked and expired accounts refused by every method) is
burrow's own PR, merged first; this PR pins it.

Footprint: cross-cutting (`.github/workflows/ci.yml` gains the `mpx5-burrowd` job; `tests/ci-plan` and
`tools/ci-tiers.map`; the pin `user/burrow.pin`; `tools/mkburrow`, `tools/install-burrow`, `tools/distribution-root`;
`user/login`, `user/usb-login.sh`, `user/install`).

## 1. Forbidden, and what was read

- **Clean rooms.** PAX's: no kernel, firmware or driver source; no kernel change was needed. burrow's: nothing of
  ssh is implemented here; burrow is built unmodified from its pin, and its README and notes were read as the
  organisation's own. den's: built unmodified from its pin; git ran only as a program. No ssh implementation's,
  shadow-utils', PAM's, C library's or init system's source was read. `docs/SOURCES.md` (px112) lists every source.
- **Secrets.** The rows' passwords are made per run by Python's `secrets` and live in the driver's memory: tools/mkauth's
  `mkshadow` hashes them on its standard input, the rig's ssh reads them from its askpass program's environment, and
  the console's login reads root's from the serial line with no echo. None was written to a file, an argument
  vector, a log or a record; every record was scanned for them in memory (B9's scan).
- **Hosts.** Linux host 1 (Intel Core i7-12700KF, 20 threads, 46 GB) for every build and boot, behind its lock names,
  in an Ubuntu 24.04 container (QEMU 8.2.2, OVMF, xorriso, clang, lld 18, OpenSSH 9.6p1's ssh and sshd, git 2.43.0,
  dnsmasq 2.91, iproute2, e2fsprogs) with KVM, `/dev/net/tun` and NET_ADMIN in its own network namespace; the build
  Mac for git. The metal target was never touched.
- **Not done:** no label, merge, tag, release or deploy; no issue filed or closed; no attribution trailer.

## 2. Inputs, verified

| input | identity | read |
|---|---|---|
| pax base | trunk `4d899ea4` | `git log` |
| burrow | `user/burrow.pin`, burrow's PR head (password authentication), wolf 0.2.37 / lupin 0.1.59 / wolf-std `2411d868`: `burrow`, `burrow-keygen` and `burrowd` static, burrow's own gate's digests in the pin | `tools/mkburrow`: two checkouts, one digest each |
| den, pelt, boreutils, the account programs | their pins, unchanged | their builders |
| the rig's image | Ubuntu 24.04, its package list (QEMU 8.2.2, OpenSSH 9.6p1, git 2.43.0, dnsmasq 2.91) | `dpkg-query` in the image |

## 3. Prediction, scored

`notes/px112/prediction.txt`, committed first (`a7a9aa96`).

| predicted | measured | score |
|---|---|---|
| burrowd runs unmodified on PAX, no kernel change | (the head's take) | |
| the images grow by about 17 MB | (burrowd's static size, the pin) | |
| the first boot's prompt about 0.2 s later, a later boot's about 0.1 s | (B1, B10) | |
| B1-B10 red at the rows tip, green at the head | at the rows tip `687288db` (native, BIOS): `FAIL B0` by name (no /bin/burrowd, no configuration, no hook in the tree), then `FAIL B1` (no host key line before the prompt), and the leg ends there: B2-B11 need the key B1 reads, so they were not reached rather than red each; B9's scan of every record ran and passed. At the head: (the takes) | red in kind, B2-B10 unreached in form |
| connect to the first byte through burrowd on PAX, 2x to 6x burrowd on Linux in the same container (publickey) | reported | |

## 4. Evidence index

Every take ran from a commit in a worktree of its own on the Linux host, in the rig's container
(`localhost/px112-net:1`, image `df1ae8c6e5de`), under a block's two lock names, its rig's files copied there
and their sha256s logged.

- **Red at the rows tip** `687288db` (`tests/mpx5-burrowd --tier native --firmware bios`, 1,372 s): `FAIL B0`,
  `FAIL B1`, `PASS B9-scan` (no password in 70 records), `END tests/mpx5-burrowd exit=1`.
- **The upgrade witness** (R-px112-14, B): `tests/mpx6-install.d/upgrade.py`'s U4d holds burrowd after the upgrade
  of the 8b4e98ae dev install (the metal target's): the LAN's configuration, the account appended, the host key made
  at the first boot. Its inputs are px93's, copied by value into the lane (the two sticks read twice on each side,
  `850ff60b…` and `665f815a…`, px93's figures; its built inputs, 325 files, and its sources, 33 files,
  byte-identical), with the two inputs px93's set predates built at the head (`tools/mkburrow`, `tools/mkroots`).
  A development take at `2feadbfd` (block C): `build` (the distribution, the live payload, the upgrade stick) exit 0;
  `legs-d` exit 0 in 493 s, `PASS` U1d-install, U2d-state, U3d-upgrade (the plan from the 8b4e98ae baseline, 8.3 s),
  U4d-after, U6d-again, U13d-sudo-upgrade-8b4e98ae. U4d's burrowd part: the configuration the LAN's, the account
  appended, the host key made at the first boot (root's 0600, the console's fingerprint), and burrowd's log
  `listening on 0.0.0.0:22` on a machine with no network card. The final head's take is in the PR.
- **The walk's run-time state** (pax#329, from px114's census): `user/install/snapshot.lu` leaves `/var/run`'s contents
  out of an install's and an upgrade's walk, the directory kept, as `/tmp`'s (sudo's `/var/run/sudo/ts`, burrowd's
  pid), and burrowd's host key, its `.pub` and its log. The snapshot unit's `I-runtime-state` row, on the light CPUs:
  red at `e0895b1e` (the row before the change: the walk listed `/var/run/sudo`, `/var/run/sudo/ts` and
  `/var/run/sudo/ts/0`), green at `95e52c0c` with the unit's other five rows.
- (The head's takes.)

## 5. Done-when

### 5.1 Rulings (answered 2026-11-09)

R-px112-1 to -6 are burrow's (its note). Here, all as recommended but R-px112-9, which was answered (C), and R-px112-14, asked later:

- **R-px112-7, the boot hook: A.** `/etc/pax-boot.d`: pid 1 runs each file there in name order before its first
  prompt (`/bin/login` on an installed system, the live entry on the stick), each in a process group of its own,
  standard input `/dev/null`, waited for at most 10 s. The kernel's wait for the network comes before pid 1, so before
  every hook; burrowd listens on an address, not on a lease, so a lease that comes later still reaches it. The dev
  and release images' root shell runs no hook.
- **R-px112-8, the host key: A.** Made by the hook with burrow-keygen at the first boot that finds none, root's 0600,
  its fingerprint on the console at every boot. Its bytes are `/dev/urandom`'s, PAX's getrandom: RDRAND. **A named
  gap:** on a CPU without RDRAND the kernel folds the TSC instead, which it names as not cryptographic, and no program
  can tell which it got (PAX has no `/proc/cpuinfo`). Every PAX host, the metal target's CPU among them, has RDRAND;
  a lane that gives getrandom a real pool closes it.
- **R-px112-9, where burrowd listens: C** (answered, not recommended: the recommendation was A, the LAN everywhere).
  The stick ships `ListenAddress 127.0.0.1`; an install writes `ListenAddress 0.0.0.0` into the installed root's
  `/etc/burrowd/burrowd_config` (a fresh install in `configure_tree`, an upgrade as a generated text, kept and put
  beside as `.pax-new` when its owner changed it). The stick refuses a LAN connection at connect; an installed system
  accepts one. **No account logs in until its owner sets a password with `passwd`, or lists a key:** an account an
  install left locked (`!`, the `n` at its password question) is refused every way, a key included (burrow's
  R-px112-3, `sshd(8)`'s rule), until it has a password. Root is refused always.
- **R-px112-10, the worker's account: A.** `burrowd:x:989:989:burrowd:/nonexistent:/bin/false` and `burrowd:x:989:`
  in the images; a fresh install copies them (and its `/etc/shadow` locks the account, as every other), an upgrade
  appends them. An upgrade never touches an `/etc/shadow` that is there (px106's rule), so an upgraded system's has no
  line for `burrowd`: the account has no password (burrowd refuses it, `auth_password_unset`), no home and no shell,
  and nothing logs in as it.
- **R-px112-11, the restart and the log: A.** The hook's loop starts burrowd again a second after it ends, or after a
  wait that doubles to five minutes while it refuses to start; `/var/log/burrowd.log`, root's 0600.
- **R-px112-12, one pin: A.** `user/burrow.pin` for the client and the server; `/bin/ssh` moves with it from
  `0d98ce92` to B5's client (the system known_hosts files by default), held by `tests/mpx4-console-push`.
- **R-px112-13, the rows' reach: A.** A tap in the rig's network namespace, dnsmasq leasing the guest its address,
  the rig's ssh and git reaching port 22 as a machine on the LAN would.
- **R-px112-14, the upgrade witness: B** (asked during the takes). The metal target gets px112 by an upgrade, so
  `tests/mpx6-install.d/upgrade.py`'s U4d holds what an upgrade leaves for burrowd (the configuration's LAN line, the
  account appended once, the host key made at the first boot, its fingerprint the console's, burrowd listening on
  0.0.0.0:22), and px106's witness rig (`notes/px106/rig`) runs its legs-d (U1d-U6d and U13d) at the final head,
  with px93's inputs and sticks copied into the lane by value. Making the witness ready found two gaps, each fixed
  before it ran: `tools/install-manifest` (the host's manifest, which the witness and the baselines use) did not
  list the configuration as installer-written, as `user/install/manifest.lu` does; and the boot hook's `mkdir -p
  /var/run` made a directory on a running stick that the image does not ship, which an upgrade's walk of the stick
  would have copied and listed. The images ship `/var/run` now.

### 5.2 The metal target

Nothing here ran on the metal target. **The owner's first check, from another machine on the LAN,** after an upgrade
(or a fresh install) from a stick that carries px112:

1. At the console, as root: `passwd -S pax`. If it says `L`, give pax a password with `passwd pax`: until then pax
   cannot log in over ssh at all, a key included. Note the fingerprint the console printed at boot
   (`burrow-keygen -l -f /etc/burrowd/ssh_host_ed25519_key` prints it again) and the address
   (`cat /var/lib/dhcp/pax.lease`).
2. From the other machine: `ssh pax@<address> ls`. ssh shows the host key's fingerprint: it is step 1's, or stop.
   Then pax's password, and the listing.
3. A key, then: `ssh pax@<address> 'mkdir -p .ssh && chmod 700 .ssh && cat >> .ssh/authorized_keys && chmod 600
   .ssh/authorized_keys' < ~/.ssh/id_ed25519.pub`, and `ssh pax@<address> ls` asks nothing.
4. git: `ssh pax@<address> 'den init -q --bare repo.git'`, then from a repository on the other machine
   `git push pax@<address>:repo.git main`, and `git clone pax@<address>:repo.git` reads it back.
5. At the console, `sudo cat /var/log/burrowd.log`: a line for each connection, `key password` for step 2,
   `key SHA256:…` for step 3.

### 5.3 Issues

None filed or closed by this lane. For the orchestrator to consider:
- wolf-std's `net.peer_address` (wolf-std#140): on PAX the log and `SSH_CONNECTION` say `UNKNOWN` port 0.
- A real entropy pool for getrandom, or a way to name the TSC fallback (R-px112-8's gap).
- The dev and release images' root shell runs no `/etc/pax-boot.d` hook.
- `/var/log/burrowd.log` is never rotated.
- Seen while readying the witness, not this lane's: the kernel writes `/var/lib/dhcp/pax.lease` on a stick that got a
  lease (px105), and `user/install/snapshot.lu` does not leave it out, so an install or an upgrade from a stick
  booted with a cable copies the stick's lease file to the target and lists it in the manifest. The witness's
  machine has no network card, so it cannot show this.

### 5.4 Checklist

- [x] The prediction, committed first (`a7a9aa96`).
- [ ] burrowd on the image, its account, its configuration; started at boot after the network; the host key at the
  first boot and kept.
- [ ] `authorized_keys` with sshd's mode checks; den's upload-pack and receive-pack through `exec`; the log at the
  console.
- [ ] B0-B11 under KVM, red at the rows tip, green at the head; the plant red by name.
- [ ] The stick leg (`notes/px112/stick-leg.txt`, B11 under QEMU); the metal target's first check (5.2).
- [ ] README, docs/SOURCES.md and CHANGELOG; tests/ci-plan and the map; the CI job.
- [ ] The gauntlet green at the final head, every END line in the PR body; the plant's record; the audit.
