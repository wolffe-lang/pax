# px114 — the live system's run-time state stays home (pax#329)

Base: pax trunk `68d52145` (written on `4d899ea4`, rebased after pax#331 put trash on the image).
The census is `notes/px114/census.txt`, the prediction `notes/px114/prediction.txt` (with its
revision 1, the rulings as given, and revision 2, `/Trash` after the rebase), the census rig
`notes/px114/rig/`.

## 1. What this lane does

An install or an upgrade builds its target from a walk of the live tree
(`user/install/snapshot.lu`, `source_walk`). Until now the walk left out only the contents of
`/dev`, `/proc`, `/sys`, `/tmp`, `/usr/share/pax-install` and `/mnt/target`, so whatever the
running stick had written by the time the installer ran went to the target and into its
`/etc/pax-install/manifest`.

The census booted the last metal stick's dev image under KVM twice, with a lease and with no
network device, typed a short session (`cd`, `sudo -n true`, `pax-install --check`), and held
the listed tree to the image's 497 archive rows (each with mtime 0, so anything written at run
time stands out). It found, besides the installer's own scratch in `/tmp` and the kernel's
`/dev`:

- `/var/lib/dhcp/pax.lease` with its two directories and `/etc/resolv.conf`, from kernel/dhcp,
  only with a lease;
- `/.sh_history` (pelt) and `/.local/share/lope/store` with its directories (lope's `cd` hook),
  root's files at the top of the tree because root's home is `/`;
- `/var/log/sudo.log`, one line for each `sudo`.

After the rebase, trash (on the image since pax#331) adds one more: root's `~/Trash` is `/Trash`.

The fix is one function beside `excluded()`, `runtime_state(path)`, checked before the walk makes
a row, so a path it names is never copied, never in the attrs, never in a manifest, and never a
change of the source if it is rewritten during the install. Each entry names its writer:

- `/var/lib/dhcp` (kernel/dhcp's lease and its directory; the rest of `/var/lib` is carried);
- `/etc/resolv.conf` (kernel/dhcp, from the lease or a static `/etc/pax-net`);
- `/var/log/sudo.log` (sudo, the stick's uses);
- `/Trash` (trash: root's trash can, since root's home is `/`);
- every top-level name that starts with a dot (root's home is `/`).

The installed kernel never reads a copied lease: kernel/dhcp has no INIT-REBOOT
(`kernel/dhcp/dhcp.lu:108`), `start` begins at INIT, and the lease file is only ever written.
The installed system makes the directory and both files itself at its first lease (or, for a
`static` address, `/etc/resolv.conf` at boot).

## 2. Rulings

- **R-px114-1, the shape: A.** `runtime_state(path)`, the same name, place and hook as px112's
  for burrowd's paths on its branch; its rebase meets one conflict in this function, resolved by
  keeping both lists.
- **R-px114-2, `/var/lib`: B.** `/var/lib/dhcp` only, never `/var/lib` whole: package state will
  live under `/var/lib/<name>`, and an install must carry it. Each `/var/lib/<x>` gets its own
  ruling. `/var/lib` itself is copied, an empty directory on an install made from a stick that
  took a lease.
- **R-px114-3, root's dotfiles: A.** Every top-level name that starts with a dot. Safe only
  while no image ships one; the follow-on guard (R-px114-5) holds that.
- **R-px114-4, sudo's log: A.** `/var/log/sudo.log` only; `/var/log` itself is the image's and
  is copied.
- **R-px114-5, the image's side: B.** A follow-on issue, not this lane: a `tests/distribution`
  row that no image ships a top-level dot name, `/var/lib/dhcp`, `/etc/resolv.conf` or
  `/var/log/sudo.log` (beside `image-no-sudo-log`), seen red and green at an image build.
- **R-px114-6, root's `/Trash`: A.** Left out whole, its writer named, red first; it is not a
  dot name, so the dot-name rule does not reach it.
- `/var/run`'s contents (sudo's timestamp, burrowd's pid) are px112's, not here.

## 3. What changes for an install and an upgrade

- A fresh install from a stick that took a lease is the same, path for path, as one from a stick
  that did not, but for an empty `/var/lib` (R-px114-2).
- Root's console history, lope's directory store and trash can from the stick no longer become
  the installed root's.
- An upgrade no longer writes the stick's run-time files beside the installed system's own as
  `PATH.pax-new` (`/.sh_history.pax-new`, `/.local/share/lope/store.pax-new`,
  `/var/lib/dhcp/pax.lease.pax-new`, `/etc/resolv.conf.pax-new`): it never plans them.
- An install made before this change lists the stick's copies in its manifest. Its next upgrade
  plans each as a path the new image drops: deleted where the target still holds the stick's
  bytes, kept (and said so) where the installed system rewrote it, and a directory removed only
  when it is empty (`upgrade.lu`, plan_paths and its `rmdir`).
- A lease renewed between the installer's two walks no longer stops the install with
  `source_changed`.

## 4. What is not done

- No row with the network on in `tests/mpx6-install`: its installs walk `--source /source`, not
  the live root the DHCP client writes. The walk of `/` is the metal leg's (`metal.py`), in the
  full and all tiers.
- The image-side guard (R-px114-5) is a follow-on issue.
- The upgrade cases in section 3 are read from the code; no row of this lane runs an upgrade.
- `/var/run` (px112's).

## 5. Evidence index

- The census: `notes/px114/census.txt`, from `notes/px114/rig/census.sh`, `census.keys` and
  `census-diff.py` at `4225f887` (before the rebase; the rig's files are unchanged by it), on a
  Linux host under KVM. `/Trash` is from the source, after the rebase (the census image predates
  trash).
- The rows, red before the fix (`tests/mpx6-install.d`):
  - `snapshot.py`: I-runtime-lease, I-runtime-resolv, I-runtime-root-home, I-runtime-sudo-log,
    I-runtime-root-trash, I-runtime-renewal (the witness's `renewal` mode rewrites the lease and the resolver file
    between the walks), and I-runtime-neighbours (package state under `/var/lib`, `/var/libx`,
    `/etc/resolv.conf.d`, a dot name inside a home and another log: copied and listed, before and
    after);
  - `prepare.py`: I-runtime-install (the prepared tree, its attrs and the manifest
    `install_manifest` writes, which `prepare.lu` now calls after `configure_tree` as
    `execute_plan` does).
- The records: red takes of the snapshot and prepare units at the rows' heads (before the first
  fix, and before `/Trash`'s entry); the green record
  at the final head (fetch-wolf, the six units, `tests/mpx6-install`'s smoke inputs and rows,
  native, BIOS); the plant record (`px114-plant-lease`: `/var/lib/dhcp`'s entry taken out,
  I-runtime-lease and I-runtime-renewal red by name). The PR quotes every `END` line.
