# px116 — a command over ssh has the console's environment (pax#334)

A command run over ssh on PAX gets burrowd's bare environment (`HOME`, `USER`, `LOGNAME`, `PATH`, `MAIL`,
`SHELL`, `SSH_CONNECTION`). The console's shell also has what `/etc/shrc` exports, `WOLF_STD`, `LUPIN_STD` and
`DEN_TLS_ROOTS`, because `/etc/pax-run` (or `/bin/login`) starts it with `ENV=/etc/shrc`. So `ssh host wolf build`
resolves another standard library than the console's and fails to compile, unless the caller puts `. /etc/shrc;`
before it. burrow's half of the fix gives burrowd `sshd_config(5)`'s `SetEnv` (burrow's own PR, its note
`notes/px116-setenv.md` in burrow); this is PAX's half.

Footprint: cross-cutting (`.github/workflows/ci.yml`: the burrowd suite's job builds the dev compiler; the pin
`user/burrow.pin`; `tests/ci-plan` and `tools/ci-tiers.map`; the new shared tool `tools/system-env`, which
`tools/distribution-root` runs).

## 1. Prediction

Written 2026-11-10 before the first change, at pax#340's head `2dd649f0` (branch `px112`), with burrow's SetEnv at
its branch head and the pinned `sshd`'s answers measured there (burrow's note).

### What changes

- **One list.** `tools/system-env` writes both texts the distribution's roots carry:
  - `shrc dev|release`: `/etc/shrc`, the same bytes `tools/distribution-root` writes today (`user/shrc`, and in
    the dev image `export PATH=/usr/bin:/bin` and `export WOLF_STD=/usr/share/wolf/compiler-std`);
  - `burrowd-config SHRC`: `user/burrowd/burrowd_config` with one `SetEnv` line appended, written from SHRC's own
    `export NAME=VALUE` lines, every one but `PATH` (burrowd's default PATH, `sshd`'s, stands). For the dev image:
    `SetEnv LUPIN_STD=/usr/share/wolf/std DEN_TLS_ROOTS=/etc/ssl/certs/ca-roots.der
    WOLF_STD=/usr/share/wolf/compiler-std`; for the release image the first two.
  - It refuses (by name, exit 1) an `export` line whose value `SetEnv` would have to quote or expand, a name
    exported twice, and a shipped configuration that already has a `SetEnv` line. So a variable the console gains,
    ssh gains in the same build, and a value the line cannot carry stops the build.
- **The distribution's roots** (`tools/distribution-root`) write `/etc/shrc` and `/etc/burrowd/burrowd_config`
  through it.
- **Install and upgrade:** nothing in the installer changes. A fresh install writes the stick's configuration with
  its `ListenAddress` line made the LAN's (`installed_burrowd_config`), and every other line, the `SetEnv` line
  among them, as the stick has it; an upgrade writes the new image's the same way, unless its owner changed the
  file (then the new text goes beside it as `.pax-new`, as for every generated text).
- **The burrow pin** moves to burrow's SetEnv head: a burrowd that refuses `SetEnv` would refuse the image's
  configuration and never listen.
- **The README:** the prefix is no longer needed from this image on.

### The rows

- `tests/mpx5-burrowd` **B17**, red at the rows tip, green after: its image gains the dev compiler and its std
  where the dev image has them (`/usr/bin/wolf`, `/usr/share/wolf/compiler-std`; no native link stack, which is
  the base payload's and which CI does not have) and the dev image's `/etc/shrc`. Over ssh, with no prefix:
  `printf` of the three variables answers the values `/etc/shrc` exports, byte for byte as the rig's `sshd` does
  when given the same `SetEnv` line, and `wolf build --no-cache --emit=obj` of a one-line program in pax's home
  succeeds. Red at the rows tip (the image's configuration still `user/`'s, burrowd at the old pin): the three
  variables `unset`. The same build with `WOLF_STD` taken away (`env -u`) is recorded, not held.
- `tests/mpx6-install` (the prepare unit) **I-burrowd-setenv-yes/no**: the installed configuration keeps the
  stick's one `SetEnv` line.
- `tests/distribution`: each image's configuration is `user/`'s bytes and one `SetEnv` line that is that image's
  own `/etc/shrc`'s exports (WOLF_STD in the dev image only).
- The upgrade witness's U4d: the upgraded configuration is the new dev image's text with the LAN's
  `ListenAddress`, its `SetEnv` line kept.
- `tests/ci-plan`: `tools/system-env` and `user/shrc` reach the burrowd suite and the distribution's checks;
  the compiler's pin reaches the burrowd suite.
- **The plant**, off the line: `tools/system-env` writes no `SetEnv` line. B17 goes red by name (the variables
  unset over ssh).

### Unchanged

Every other mpx5-burrowd row (B0-B16): the image only grows by the compiler, its std and `/etc/shrc`, and the
configuration by one line. The console's `/etc/shrc` bytes, in both images.

## 2. Decisions (recommended, implemented)

1. **Which variables:** (A) every variable `/etc/shrc` exports but `PATH`, so the list is the file's own; (B) the
   three names alone. Recommended (A): one list, nothing to keep in step by hand. `PATH` stays burrowd's
   (`/usr/bin:/bin:/usr/sbin:/sbin`, `sshd`'s default), which holds the console's `/usr/bin:/bin`.
2. **Generate or compare:** (A) generate the configuration's line from `/etc/shrc` when the image is built; (B)
   write the line by hand in `user/burrowd/burrowd_config` and have a test compare the two. Recommended (A): the
   release image exports no `WOLF_STD`, so one hand-written line would be wrong for one of the two images.
3. **B17's build:** (A) `wolf build --no-cache --emit=obj`, the compile pax#334 broke, in an image with the
   compiler and its std and no link stack; (B) a full `wolf build` and link, which needs the base payload's
   68 MB `ld.lld`, which neither CI nor the suite's image has. Recommended (A).

## 3. A row elsewhere that turns

The stick's integration rows (the stick lane's tree, not this repository) hold pax#334 as the last stick's README
states it, its M4b: over ssh `WOLF_STD` unset, and the console's value after `. /etc/shrc;`. From an image with
this change that row turns: `ssh HOST 'printf "%s\n" "${WOLF_STD:-unset}"'` answers, with no prefix, the same value
as after `. /etc/shrc;`, a path (it starts with `/`); the README's prefix line goes.

## 4. Evidence

Development takes on the Linux build host, each in the rig's container (`localhost/px116-net:1`, px112's image
`df1ae8c6e5de` under this lane's tag: Ubuntu 24.04, QEMU 8.2.2, OpenSSH 9.6p1, git 2.43.0, dnsmasq 2.91) with KVM
and the rig's tap, under a block's two lock names, `tests/mpx5-burrowd --tier native --firmware bios`. The dev
compiler and its std were px112's copies of the distribution's inputs, held to `user/wolf.sums` and `user/wolf.pin`
by the suite (`PAX_DEV_WOLF_DIR`, `PAX_DEV_STD_DIR`); CI builds them with `tools/mkwolf` and `tools/mkwolf-std`.

- **Red at the rows tip** `86a8a8fc` (burrow at the old pin, the image's configuration `user/`'s; log sha256
  `30af766c…`): every row green but `FAIL B17 over ssh the variables are b'unset\nunset\nunset\n', the console's
  b'/usr/share/wolf/compiler-std\n/usr/share/wolf/std\n/etc/ssl/certs/ca-roots.der\n'`. The rig's sshd answered
  `unset` alike (no `SetEnv` line in the image to give it). B8 and B9, at the console as root, held with `/etc/shrc`
  now in the image.
- **Green at the fix's head** `932657d5` (burrow `16858a5`, burrowd `b35bcd3c…` as the pin records; log
  `4c7c5cee…`): `tests/ci-plan`, the installer's prepare unit (I-burrowd-setenv-yes/no beside I-burrowd-lan) and
  every mpx5-burrowd row, B0-B17 and B9's scan (no password in 273 records). **Not predicted:** B17's build of the
  one-line program also succeeded with `WOLF_STD` taken away (`status=0`): in the suite's image the compiler found
  a std of its own without the variable, so the build half of the row could not tell the two apart.
- **The row made to tell them apart** (`fd938957`): the image gains lupin's std at `/usr/share/wolf/std`, as both
  images have it (`tools/fetch-std`), and the program calls `std.fs.write_text`, the call pax#334's failed build
  named. At `fd938957` (log `85fd56cf…`): the build with `WOLF_STD` taken away failed as pax#334 did (status 2,
  E0301, `write_text` not found in the module), and the build with no prefix exited 0 but left no `px116.o` (a
  program that imports std, measured at `18d5ae05`, log `757e66cc…`: `wolf=0`, `ls: cannot access 'px116.o'`), so
  B17 held what it should not have. It now holds wolf's own status and records the listing (`79506fb1`).
- **Green at `79506fb1`** (a boot-only take on `fd938957`'s images, whose tree is unchanged since): B0-B17 and the
  scan, `PASS B17 WOLF_STD=/usr/share/wolf/compiler-std, LUPIN_STD=/usr/share/wolf/std,
  DEN_TLS_ROOTS=/etc/ssl/certs/ca-roots.der over ssh as the console has them (sshd's answer too); wolf build of a
  program calling std.fs, no prefix: status 0; without WOLF_STD: status=2`.
- **The plant** (`tools/system-env` writes no `SetEnv` line, one line; on `fd938957`, branch
  `px116-plant-setenv2`, no PR): B17 red by name (log `7e9277c3…`): `FAIL B17 over ssh the variables are
  b'unset\nunset\nunset\n'`, and the record beside it shows pax#334 whole: `wolf build` over ssh with no prefix
  exits 2, `write_text` `not found in the module` (E0301), the compiler resolving lupin's std.

**The prediction, scored:** the one list, the configuration's line for each image, nothing changed in the installer
(I-burrowd-setenv held at the first green take), the pin's move, B17 red at the rows tip and green at the head, and
the other rows unchanged: as predicted. Not predicted: the one-line program built without the variable in the
suite's image, which made the row's build half blind until it carried lupin's std and a call into std; and
`--emit=obj` leaves no object for a program that imports std (recorded, not held). The final records wait for the
head the merge queue gives.
