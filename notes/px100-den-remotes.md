# px100 — den's remotes on PAX: same-machine remotes, qualified at the console

The question was whether den's remotes can be set up on PAX. den's pin (`584b18a3`) carries `remote
add/remove/rename/-v/get-url/set-url`, `branch --set-upstream-to`, `clone`, configured `fetch`, `pull` and `push`,
`push -u`, leases, `--atomic` and `daemon`; nobody had run them on PAX. This lane types them at PAX's console, as
root and as `pax`, under `/tmp` and on the ext2 `/home`, and holds every answer, object id and ref to the same keys
typed on Linux. `file://` remotes go through two small wrappers PAX now installs; loopback `git://` goes through `den
daemon`. `ssh://` and real network remotes are out of scope (no ssh client on PAX, and no NIC driver for the target
machine yet).

**The answer:** yes, on one machine. `file://` remotes work at the console of every image (the wrappers and
`/etc/shrc` ship in the dev and release roots). `git://` through `den daemon` works on the session kernel; the
kernel the shipped images boot starts no network, so there a `git://` clone neither connects nor gives up
(R-px100-2).

Footprint: cross-cutting (`tests/ci-plan` and `tools/ci-tiers.map`, CI's own proof and map).

## 1. Forbidden, and what was read

- **Clean room.** No kernel, firmware or driver source of any other system, and no Git source (den's own rule).
  den is the org's code and was read where its behaviour had to be predicted; Git ran only as a program, reading
  what PAX wrote and, for den#58's witness, answering the same commands. `docs/SOURCES.md` (px100) lists every
  source.
- **den unchanged.** den is built from its pin by its own `tools/mkden` and installed byte for byte; nothing here
  works around a den limit inside den. Its limits that show (den#49, den#52, den#58) are den's, the same on Linux.
- **Disks.** QEMU only; no physical disk was read or written.
- **Hosts.** Two x86-64 Linux hosts, each run behind the host's lock names inside one slot's CPUs, in the baseline
  Ubuntu 24.04 container (clang, lld 18, QEMU 8.2.2, OVMF, xorriso, e2fsprogs), KVM. A build is a heavy step (both
  lock names, the slot's CPUs, 12 GiB); a Linux side or a boot leg is light (the host's light helper: two CPUs,
  6 GiB).

  | host | CPU | memory | here |
  |---|---|---|---|
  | Linux host 1 | Intel Core i7-10870H, 8 cores / 16 threads | 31 GB | the Linux dry runs, the red run |
  | Linux host 2 | Intel Core i7-12700KF, 20 threads (P- and E-cores) | 46 GB | the green runs, P3's probe, den#58's witness |

- **Not done:** no label, merge, tag, release or deploy; no issue closed; no attribution trailer. One issue filed,
  as asked: den#58. The plant is pushed without a PR.

## 2. Inputs, verified

| input | identity | read |
|---|---|---|
| pax base | trunk `411fc9f5` | `git merge-base --is-ancestor` |
| den | `584b18a35fe7373735b673601af71e1722f5af29` (`user/den.pin`, the pin px97's sweep moves it to; carried here as px97's own commit until the rebase) | `tools/mkden` refuses any other HEAD |
| den, static | `ac1ec5268869397f1f6c9d4b197dae2f3531f3742c8fd12e5198566ed39c5289`, 17,251,992 bytes; stripped `99fffc19…`, 3,074,744 (not installed) | four builds, one digest, on each host |
| pelt | `4683b3f5` (`user/pelt.pin`): friendly mode opt-in at this pin | its README |
| the wrappers | `user/den/upload-pack` `9f482f05…`, `user/den/receive-pack` `c6e2e052…` (two lines each) | `sha256sum`, in the session too |
| kernels (native, at `d38168b3`) | kmain_console `01fac5c6…`, kmain_session `5d861cb8…` | `tools/build-kernel` |

## 3. Prediction, scored

The prediction is `notes/px100/prediction.txt`, committed first (`43b7d704`).

| | predicted | measured | |
|---|---|---|---|
| P1 | file:// through the wrappers, both users, both places, byte-identical to Linux; no PAX change | R1: 476 lines identical each for root and `pax`; the typed pair (written since boot) and the installed pair alike | held |
| P2 | no variables: den names the failure, the same on both | `den: wire: io`, status 2, on both (`remote-no-variable`) | held |
| P3 | git:// on kmain_console red: the daemon prints its port, the SYN never leaves; the client fails at its 30 s deadline or waits longer | the daemon printed `port 9418` and exited 2; the client's clone was still waiting four minutes later, past its own 30 s deadline; no panic, nothing refused by name | held (the "waits longer" branch) |
| P4 | git:// on kmain_session identical; a second daemon binds the same port over TIME-WAIT | identical; `port 9418` twice in each place; the kernel's books `8 accepted, 8 made, 0 open` | held |
| P5 | a fetch with no daemon refused alike | `den: wire: io`, status 2, on both | held |
| P6 | `fsck --full` clean on every repository; the disk's whole to Linux's git | four `den fsck --full` a place silent, status 0; R3: e2fsck -fn clean, `git fsck --full` clean on all eight on the disk | held |
| P7 | no shell of these rows starts friendly at pelt `4683b3f5` | the rows type at `/bin/sh`; nothing here types through a `/bin/pelt` login shell | held |
| P8 | the layout, an R-px100 ruling | R-px100-1 = A, as implemented | held |
| P9 | -ENOSYS only 273 and 334, nothing refused | R4 | held |
| P10 | about 4–5 minutes a boot for both runs | about 4 minutes (17:09:17Z to 17:13:28Z) | held |
| P11 | the plant (an installed wrapper with no path) red by name at the session's own rows, the comparison green | in the plant record | |
| (not predicted) | | `den branch` (every listing form) refuses once a branch has an upstream, on Linux too: den#58 | a den limit |

## 4. Evidence index

### 4.1 The change

- **The wrappers** (`a07f21da`): `user/den/upload-pack` and `receive-pack`, `#!/bin/sh` and `exec /bin/den
  upload-pack "$1"` (receive-pack likewise). den's file:// transport runs `$DEN_UPLOAD_PACK` or
  `$DEN_RECEIVE_PACK` with the repository's path as its only argument, and `git-upload-pack` or
  `git-receive-pack` from PATH when the variable is unset; PAX has no Git.
- **Installed where the image's users get them** (`4a8fdda1`): `tools/install-den` copies them to
  `/usr/libexec/den/`, 0755, in every root it makes: mpx5-den's images and, through `tools/distribution-root`
  (`984c3825`), the dev and release roots and so the disk `pax-install` writes. `tests/distribution` (`11ebf071`)
  holds their bytes, modes and owners in both roots, and `/etc/shrc`'s two exports.
- **`/etc/shrc`** (`d9f83f84`): `user/shrc` exports `DEN_UPLOAD_PACK=/usr/libexec/den/upload-pack` and
  `DEN_RECEIVE_PACK=/usr/libexec/den/receive-pack`. Every console shell reads it (`ENV=/etc/shrc`), `su pax`
  keeps `ENV`, and a program a shell starts inherits the exports.
- **The keys** (`c04279b9`), `user/console/den-remote.keys`: den's pinned environment as `den.keys` sets it, then
  `den-session-begin`. The keys print the variables and the installed wrappers' bytes, then type a second pair at
  the console (written since boot, `chmod 755`; the same bytes). Then two places, each opened by its marker:
  - `den-place-tmp`: under `/tmp/den-UID/r`, the typed pair;
  - `den-place-home`: under the ext2 `$W/r`, the installed pair.

  In each place: `init src`, a commit, `clone -q --bare file://…/src hub.git`, `remote add origin`, `remote -v`, a
  commit and `push -u origin main`, `cat .git/config` and the hub's ref, a commit and `push`, `clone -q
  file://…/hub.git c2` and its `log --oneline`, a commit pushed from it, `fetch`, `log --oneline origin/main`,
  `pull --no-rebase` (a fast-forward), the log. Then git://:
  - `: > hub.git/git-daemon-export-ok`;
  - `dm | dc den clone -q git://127.0.0.1:$Q/hub.git c3`: `dm` runs `den daemon --enable-receive-pack $P $Q` and
    then echoes its status; `dc` reads the daemon's `port` line, so the client dials only after the listen, then
    runs `s` and `cat`s the rest of the pipe;
  - a commit in c3, then `dm | dc den push`: a second daemon on the same port, the push through the clone's
    configured remote;
  - `fetch` with no daemon, then `pull --no-rebase` in src and the log;
  - the hub's ref, the sha256 of each of its loose objects, and `fsck --full` in each of the four repositories.

  The port is 9418 for root and 9428 for `pax`, plus one at home. Every typed line is under 78 columns: the
  container's terminal wraps at 80, PAX's console does not, so a longer echo would differ.
- **The rows** (`8d27865f`, `6e6d1f2e`, `6f001738`, `c0e526bd`): `tests/mpx5-den` builds a third image (den's
  archive with `chmod`, `/etc/shrc` the two lines of `user/shrc`, read from the shipped file, and its own run list:
  `/bin/env ENV=/etc/shrc /bin/sh -i -m`, then the same through `as 1000 1000`), boots it on REMOTE_KERNEL
  (`kmain_session`, R-px100-2) with a fresh copy of the home disk, and holds:
  - R0 build: `/etc/shrc` names den's two service variables, the wrappers installed;
  - R1 each session byte-identical to the container's;
  - R2 `tests/mpx5-den.d/remote.py`'s 33 rows by name (the wrappers and the variables, den's refusal without
    them, every report's ids carried from `commit`'s lines, the daemon's `port` and status, den's named limits,
    `fsck`);
  - R3 the disk: e2fsck -fn, the four repositories of each session read back, Linux's `git fsck --full` on each,
    the hub's main the id the session printed;
  - R4 D4's end rows, and the kernel's books, `network: tcp connections 8 accepted, 8 made, 0 open`.

  The Linux side types the same keys into the same tree in a throwaway container (`tools/linux-tree`, its network
  namespace's loopback).
- **CI's routing** (`b6034cee`, then `d38168b3`): the remote keys and the wrappers reach mpx5-den, and the wrappers
  reach its installer's suites as well; mpx5-den is in `@net` (its remote image runs loopback TCP) and in
  `user/shrc`'s suites. `tests/ci-plan` was red first at `b6034cee`: two rows, mpx4-net's renew step (`@net`
  without mpx5-den) and the wrappers' row. It went green with the map.
- **README** (`681eead8`) and `docs/SOURCES.md` (`ed8cba30`).

### 4.2 The Linux side, dry (Linux host 1, before any PAX boot)

The keys were typed through `tools/linux-tree` into a probe tree with den `ac1ec526…`, pelt `04a72b78…`
(`4683b3f5`) and boreutils. The first take showed the 80-column wrap of the long daemon lines; the helpers `dm` and
`dc` fixed it. Then both sessions ran to their end, 476 lines each, with every `remote.py` row holding. Six
mutations of the transcript, one at a time, each turned exactly its own row red:
- the daemon's status;
- the wrapper's path;
- one push id;
- one fsck status;
- `/etc/shrc`'s value;
- the port.

### 4.3 Green at `d38168b3` (Linux host 2)

`tests/mpx5-den --tier native --firmware bios`, all three phases exit 0, 1681 s:
- D0, D1–D4, L1–L5: the existing sessions at den `584b18a3`, 859 lines each identical to Linux (`631f1649…`,
  `47cb3dd4…`);
- R0–R4:
  - R1: remote-root 476 lines (`5fca7214…`) and remote-user 476 lines (`eea1e1a7…`), identical to the container's;
  - R2: 33 rows each;
  - R3: the disk clean and git 2.43.0 reading all eight repositories whole;
  - R4: halted, -ENOSYS only 273 and 334, the books 8/8/0.

Serials: den `1faac1fe…`, login `8c2c7e44…`, remote `9bba0cb9…`.

### 4.4 P3: git:// on kmain_console (Linux host 2, a probe)

The remote archive of that green build (`198d7fe0…`, its wrappers and `/etc/shrc` in) was booted on the same
build's kmain_console (`01fac5c6…`) in place of kmain_session. It typed the same keys, with a 330 s bound. The
file:// half ran as on kmain_session. At `dm | dc den clone -q git://127.0.0.1:$Q/hub.git c3` the sequence was:
- the daemon printed `port 9418`;
- the client started;
- the daemon ended with status 2 (its message went to a file the boot lost);
- the client did not return; the serial log stopped there;
- four minutes later the bound ended QEMU (`QEMU ended before prompt 73`).

There was no panic and no `refused:` line. The red-first record of the same rows at `6e6d1f2e`, the commit before
the wrappers and the kernel switch, is §4.5.

### 4.5 Red at `6e6d1f2e` (Linux host 1)

The rows committed before the wrappers, `install-den`, `/etc/shrc` and the kernel switch: R0 and R2's
wrapper and variable rows red, and the git:// rows red on kmain_console. (The record goes here when it lands.)

### 4.6 The gauntlet, the plant, CI

At the final head, after the rebase onto the trunk the coordinator names, recorded by the org's
`gauntlet-record.sh` from a clean checkout:
- `wolf-pin`, `ci-plan`, `census`;
- `mpx5-den` native (BIOS and UEFI) and release BIOS;
- `mpx5-lope` native BIOS (`user/shrc` reaches it).

Each step's output is indented two spaces. The plant, `px100-plant-*`, is one hunk of `user/den/upload-pack`: the
wrapper passes no path (`exec /bin/den upload-pack`). Predicted red by name: `remote-wrappers` (the typed pair is
no longer the installed pair) and `remote-clone-bare-home` (the installed wrapper's clone fails). R1 stays green,
because the Linux side gets the same wrapper. The suites `user/shrc` and the wrappers reach that this gauntlet does
not run (mpx6-install, mpx6-disktools, mpx6-fsck, mpx6-kasumi) are CI's labelled run.

## 5. Done-when

### 5.1 Rulings

- **R-px100-1, the wrappers' layout: A** (ruled A). Options:
  - (A) `/usr/libexec/den/upload-pack` and `receive-pack`, installed by `tools/install-den`, with `/etc/shrc`
    exporting the two variables;
  - (B) `/usr/bin/den-upload-pack` and `den-receive-pack`, with the same exports;
  - (C) `/bin/git-upload-pack` and `/bin/git-receive-pack`: den's default names on PATH, so file:// would work
    with no variable at all, at the cost of Git-named programs that are den.
- **R-px100-2, git:// and the kernel: A** (ruled A). Options:
  - (A) the remote rows boot kmain_session, and the README says git:// needs the network kernel while file://
    covers same-machine remotes on the stick;
  - (B) kmain_console starts a loopback-only stack, a lane of its own after px89;
  - (C) the shipped images boot kmain_session.
- **What B would need, as far as read here** (PAX's own `kernel/kmain_session.lu`, `kernel/kmain_console.lu`,
  `kernel/socket`, `kernel/tcp`, `kernel/ip`, `kernel/netd`):
  - **The bring-up.** kmain_session starts the stack after `user.start()` and `clock.start()`:
    - `pci.scan()` and `net.start(pml4)` (a device if there is one; with none, loopback only);
    - `arp.start`, `ip.start(OWN_IP, NETMASK, GATEWAY)`, `icmp.start()`, `udp.start()`,
      `tcp.start(process.random_word(0))`, then their reports;
    - a check that the stack took its 333 frames;
    - the network clock thread (`pax_net_clock`), always: loopback's backstop and TCP's timers;
    - the receiving thread (`pax_netd`) only with a device;
    - the two loopback self-pings and their `loopback:` line;
    - since px89, DHCP when `/etc/pax-net` asks.

    kmain_console has none of it.
  - **What a never-started stack answers.** The socket calls are still served, because kernel/user reaches
    kernel/socket: `socket`, `bind` and `listen` succeed, so `den daemon` prints its port. But TCP's composing
    frame is never taken, so `emit` sends nothing, and nothing drains the loopback queue. A non-blocking connect
    answers -EINPROGRESS, and the wait that follows never ends (§4.4: past den's own 30 s deadline).
  - **B's work, then:**
    1. the loopback part of that bring-up in kmain_console (ip, udp, tcp, the clock thread and its frames); and
       whether the console kernel scans for a NIC at all, given px89's drivers and DHCP;
    2. every suite that boots kmain_console (most of the console, user and disk suites, the installer's and the
       stick's paths) reviewed for its kernel lines: the stack's reports, the frames, one more thread;
    3. tier all.

    Separately, and smaller: a stream connect on a stack that was never started could fail at once, so that a
    program's own deadline ends it. With B there is no such case on the shipped kernel.
- **The friendly prompt (item 5):** nothing to rule. At pelt `4683b3f5` friendly mode is opt-in, and the rows type
  at `/bin/sh`, which is never friendly. If shipped-image legs type the remote session later (with B), their `su
  pax` login shell opts out first in `/etc/shrc`, as R-px97-14 did.

### 5.2 Issues

- Filed: den#58, `den branch` (every listing form) refused once a branch has an upstream, with its Linux witness.
- Met and already filed: den#49 (`status` with an upstream), den#52 (a plain local path).
- Nothing closed.

### 5.3 Checklist

- [x] The prediction, committed first (`43b7d704`), scored above.
- [x] file:// through the wrappers and git:// through `den daemon`, typed at PAX as root and as `pax`, under `/tmp`
  and on the ext2 `/home`, byte-identical to Linux, `fsck --full` clean on every repository (§4.3).
- [x] PAX's gap measured (§4.4) and ruled (R-px100-2 A; B its own lane).
- [x] The rows stay: `tests/mpx5-den` R0–R4, routed to CI with den's other rows.
- [x] The wrappers where the image's users get them (R-px100-1 A), `/etc/shrc`, the README.
- [ ] The red record at `6e6d1f2e` (§4.5).
- [ ] The gauntlet green at the head, every END line in the PR.
- [ ] The plant red by name in its own record.
- [ ] The audit, once.
