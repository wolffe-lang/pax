# PAX

A Linux-compatible operating system written in wolf: a kernel that runs Linux's x86-64 userspace unmodified, and a
userspace built in wolf.

PAX is a clean-room implementation of Linux's userspace ABI. It contains, translates and derives from no Linux kernel
source; `CLAUDE.md` states the rule and `docs/SOURCES.md` lists what each part was written from. Every behaviour claim
below is a scripted QEMU test that CI runs, and where the behaviour is Linux's, the test holds PAX byte for byte to a
real Linux booted the same way.

Licence: GPL-3.0, with the wolf Training Data Permission (`LICENSE-TRAINING-DATA`).

## At a glance

| Area | What PAX does today | Held to |
|---|---|---|
| Boot | Limine 12.9.1 from one hybrid ISO (BIOS and UEFI), from a GPT disk, or from a live USB stick; a guided installer onto the one disk the stick's allow-list names, its log written to the stick | both firmwares under QEMU, every push; the whole install on a machine shaped like kasumi |
| Programs | Static x86-64 ELF run in ring 3 with Linux's syscall numbers; `fork` (glibc's and wolf's `clone`, and musl's `fork` itself), `vfork`, `posix_spawn`, `execve`, `#!` lines, threads (`clone3`, `futex`), signals with the full frame restored, job control and sessions; `getrusage` (user and system time, the peak resident set, the context switches, a process's and its children's); `ptrace` (TRACEME, ATTACH, SEIZE, stops and events, registers, memory, single-step, hardware watchpoints), the requests a debugger uses; a fixed 1 MiB initial stack | the same binaries on Linux, byte for byte |
| Users | `root`, `pax` and the service account `lobo`; real, effective, saved and file-system ids; every path walk, mode, owner and signal checked by Linux's rules; set-user-ID and set-group-ID honoured as `execve(2)` says (`no_new_privs`, `nosuid`); `login`, `su`, `sudo` and `passwd` in wolf; passwords in `/etc/shadow` as scrypt `$7$`, none in any image | Linux as root and as a user; Ubuntu's `login`, `su`, `sudo` and `passwd` for the commands |
| Files | A writable in-memory tree seeded from the initramfs: links, modes, times, holes, `rename`; `mmap` private and shared, `mremap`, FIFOs, `flock`; `/dev`, `/proc`, `/sys`, `/tmp` | Linux's tmpfs in a throwaway container |
| Disks | Up to eight disks: virtio (four), NVMe (`nvme0n1`, major 259), SATA AHCI (`sda`, major 8, LBA48; a controller in RAID mode named and left alone), or USB mass storage (`sdX`, Bulk-Only Transport), with GPT or MBR tables and `/dev` nodes; ext2 read and written, file data past 2 TiB on every bus; ext3's journal written and replayed; `/` on the disk, `mount(2)`, `/etc/fstab`; an offline `fsck.ext2` in wolf | Linux 7.3.0 under QEMU (NVMe and AHCI: 7.2.4) and e2fsprogs |
| Network | virtio-net, and Intel's 82576 (by MSI-X) and I225/I226 (polled) on one ring model; ARP, IPv4, ICMP, UDP, TCP (RFC 9293, 6298, 5681), Unix sockets, `poll`, `epoll`, `eventfd`; 256 TCP connections; a DHCP client (RFC 2131) when `/etc/pax-net` says `dhcp`, with `/etc/resolv.conf` from the lease, or a static address when it says `static`; the console every image boots takes its address so, bounded: a missing device, a cable with no link or a server that never answers never stops the boot; names resolve through the C library's resolver as on Linux (`/etc/hosts`, then DNS) | Linux in a namespace, captures rebuilt byte by byte, and dnsmasq as a black box for every lease event |
| Console | A 16550 serial console when present, PS/2 and USB keyboards over xHCI with MSI or INTx, one line discipline; a firmware-sized framebuffer with the Linux VT's colours and 560 glyphs | typed sessions on a Linux pseudo-terminal; screendumps against a reference renderer |
| Firmware | Checksummed ACPI tables, one boot line each; a local APIC tick calibrated against the HPET (checked against the ACPI PM timer), else the PM timer, else the PIT; the xHCI on MSI where it offers it; ACPI reset and static S5 power-off; every boot line on the screen with no serial port | QEMU BIOS and UEFI, including machines with no HPET, no PIT, no COM1, a 3840×2160 GOP and BARs above 4 GiB |
| Sound | The PC speaker through Linux's console ioctls; virtio sound behind OSS `/dev/dsp`; `/bin/play`, an orchestra of 17 timbres | QEMU's capture, every pitch within 1% |
| Shipped programs | pelt (the shell, PID 1), boreutils (107 utilities), scent as `grep`, den as `git`, burrow as `ssh`, yew, lope, aspen, lupin, lobo, clef, three wolf games | the same binaries in a Linux container |

What PAX is not: a security boundary. The permission checks hold for honest programs; the kernel has never been fuzzed
or audited, it loads programs at fixed addresses, the live USB entry accepts `root` with no password, and so does an
installed console until its owner sets a password.


## Passwords, `login`, `su` and `sudo`

PAX honours the set-user-ID and set-group-ID bits of a program as Linux does
(`execve(2)`: the file's owner becomes the effective user id; a set-group-ID
file needs group execute; a script's own bits are ignored; a `nosuid` mount
and `no_new_privs` switch them off). Four programs, written in wolf, keep the
accounts, and all four read one password file:

- **`/etc/shadow`**, root's, mode 0600 (Ubuntu's is 0640 with a `shadow`
  group, read by helpers PAX does not have; every reader here is root). One
  line an account, locked by default (`!`, or `*` for root). A password is
  stored as scrypt in crypt(5)'s `$7$` form (N = 2^17, r = 8, p = 1: 128 MiB
  and about 0.6-0.7 s a check on PAX on a laptop i7 under KVM), the
  string Ubuntu's own crypt reads, made with a fresh 16-byte salt from the
  kernel's random source. `/etc/passwd`'s second field stays `x`.
- **`passwd`** (`user/passwd`, set-user-ID root) sets a password: root
  anyone's, a user only their own after the current one. `passwd -S` shows the
  state (`L`, `NP` or `P`), and root can lock (`-l`), unlock (`-u`) or empty
  (`-d`) an account.
- **`login`** (`user/login`) is an installed system's console: `pax login: `,
  then `Password: ` with no echo. A failure waits 3 seconds and says `Login
  incorrect`, the same words for a wrong password, a locked account and one
  that does not exist; five failures end the try, and 60 seconds end an
  unfinished one. Then it starts again, since nothing else would.
- **`su`** (set-user-ID root) asks for the target's password, once. A wrong
  one waits 3 seconds and says `su: Authentication failure`. Root is never
  asked.
- **`sudo`** (set-user-ID root) asks for **your** password for a rule that
  does not say `NOPASSWD:`: `[sudo] password for NAME: `, three tries, 2
  seconds after each wrong one. It asks before it refuses, too, as Linux's
  does. A right password is remembered for 5 minutes on that terminal (`sudo
  -v` renews it, `sudo -k` forgets it, `sudo -K` removes the record; a reboot
  forgets it). `-S` reads the password from standard input, and `-n` refuses
  rather than ask.

**No image ships a password.** The live USB and the dev and release images
have no `/etc/shadow`, so every account is locked. The dev and release images
boot to a root shell, as they always have, and the live USB's entry still lets
`root` in with no password. **An installed system lets `root` in at the
console with no password, and says so, while no account that can reach root
has one** (root itself and every member of group `sudo`): `PAX: no password is
set for root or for group sudo, so root logs in without one; set one with
passwd.` An unconfigured system is exactly as open as an installed PAX was
before passwords, until its owner sets one. A password for root or for a member
of `sudo` closes that door: from the next login on, root needs its own
password, or stays out if it is locked. A password for any other account
(`lobo`'s, say) leaves it open, so the console never ends with no way to root.

**Installing and upgrading.** The guided `pax-install` asks, after the
confirmation and before it writes anything, `Set a password for root now?` and
the same for the new account. Each `y` runs `passwd` for that account (the
password goes to the new system's `/etc/shadow` and never to the install
log), and each `n` leaves it locked. The scripted install leaves both locked.
Either way the new account is made a member of group `sudo` (gid 27), as
Ubuntu's installer makes its first user. **An upgrade never touches
`/etc/shadow`.** An install made before passwords has none, and its upgrade
makes one with every account locked. An upgrade also makes the installer's
account (uid 1000, by `/etc/passwd`) a member of `sudo` in `/etc/group`: it
appends `sudo:x:27:NAME` when there is no `sudo` line, adds the name when the
line lacks it, and changes nothing when it is already there; every other line
stays byte for byte. An `/etc/group` that gives gid 27 to a group not named
`sudo`, or has `sudo` at another gid, refuses the upgrade by name before
anything is written: that file is yours to fix. On the 860, that means: boot
the new stick's upgrade entry, run `pax-install --upgrade`, type the line it
prints, and power off. Boot the disk and log in as `root` with no password (the
console says why). Run `passwd NAME` with your account's name, then log in as
that account: `sudo` asks for your password. From then on root's door is shut,
and root at the console needs a password of its own (`sudo passwd root` sets
one).

**`sudo`'s policy.** The image ships `user/sudo/sudoers`, two of Ubuntu's rules:

    root ALL=(ALL:ALL) ALL
    %sudo ALL=(ALL:ALL) ALL

The second lets **every member of group `sudo`** (gid 27) run anything as
anyone after their own password, as on Ubuntu. The installer's account is one,
and another administrator is made one the same way, by adding their name to
`/etc/group`'s `sudo` line. Ubuntu's third rule, for a group `admin`, is left
out: PAX has never had one. The service account `lobo` (990) has no rule.
`sudo -i` gives a root shell,
`sudo -u lobo CMD` runs as another user, and `sudo -l` shows what you may run.
Every use, allowed or refused, appends a line to `/var/log/sudo.log` (root's,
mode 0600; sudo's format, `Mon DD HH:MM:SS : user : ...`, with the time in
**UTC**, since PAX keeps no zone, and the failures `3 incorrect password
attempts`). A rule's command matches by an equal path or by naming the same
real file (a symbolic link is fine); a relative path, `..` or `//` in a rule
is refused by name. `sudo` reads `/etc/sudoers` and files in `/etc/sudoers.d`
only when they are root's and not group- or world-writable, as Linux's `sudo`
does. The subset it implements, and what it refuses by name, are in
`user/sudo/sudo.lu`'s header.

`tests/mpx5-sudo` holds all of it to Ubuntu 24.04's own `login`, `su`, `sudo`
and `passwd`. Sessions typed at PAX's console are compared with the same keys
typed at PAX's programs and at Ubuntu's in a container. The rows where PAX
differs on purpose are named in `notes/px106/named.txt` and
`notes/px103/ctnamed.txt`.

All of this is **enforced for honest programs; not a boundary against an
attacker**: the kernel has never been fuzzed or audited and loads programs at
fixed addresses.

## Quick start

On a Linux x86-64 host with binutils, cc, make, curl, xorriso and `qemu-system-x86_64` (the Hosts table below says what
each machine can do):

```sh
tools/fetch-limine                          # Limine 12.9.1 by digest, into .pax-cache/
tests/proof                                 # the harness's own proof: build the stub, boot it under BIOS and UEFI
PAX_WOLF=$(tools/fetch-wolf) tests/mpx1     # first light: the wolf kernel on both compiler tiers, both firmwares
PAX_WOLF=$(tools/fetch-wolf) tests/mpx3-shell   # pelt at a prompt, typed sessions held to Linux
PAX_WOLF=$(tools/fetch-wolf) tests/mpx6-nvme    # NVMe disks held to Linux on QEMU: names, bytes, errors, / on NVMe
PAX_WOLF=$(tools/fetch-wolf) tests/mpx6-ahci    # SATA identity, DMA, large LBAs, no-write live boot, / on AHCI
tools/qemu-halt --elf K.elf --drive a.img --nvme n.img --marker halt K.iso   # vda and nvme0n1 beside the ISO; --boot-nvme boots from NVMe
PAX_ROOTDISK_BUS=nvme tools/rootdisk-leg mpx5-users --tier native --firmware bios   # a suite again with / on nvme0n1p2
tools/qemu-run --ahci disk.img,serial=MY-SATA-DISK,model=Test-SSD K.iso  # a SATA disk beside the ISO; --boot-ahci boots from SATA
```

Then, to use it rather than test it:

1. Build the disk that boots: `tools/mkdisk --gpt --kernel K.elf --root I.cpio 512M pax-disk.img`.
2. Boot it in a terminal with the SeaBIOS line under [A disk that boots](#a-disk-that-boots).
3. Type at pelt's prompt; `reboot` restarts on the same disk, `poweroff` powers off, `exit` (or Ctrl-D) writes `/`
   and halts. As a user, `reboot` and `poweroff` say `Operation not permitted`, as Linux's do.

The harness never installs anything: a missing tool is named and the tool stops. `tools/qemu-run` boots an image
headless and returns QEMU's status, `(v << 1) | 1` when the kernel writes `v` to the exit port, 0 for a reset or
triple fault, 124 for a timeout; `tools/qemu-halt` holds a kernel that halts to RIP inside `pax_halt` through QEMU's
monitor. Each tool's header comment states its usage; `qemu-run` and `qemu-gdb` print it with `--help`.

## What is in the image

The release and dev images carry the programs below. `/etc/pax-release` prints their exact input identities (the pin
files' digests, the games' source archives, the kernel's own ELF digest and `SOURCE_DATE_EPOCH`), and the boot banner
shows the kernel commit and the first eight digits of that file's SHA256. The kernel names itself on every boot, on the
line under `PAX: the console`: `kernel: <commit> sha256 <digest>, <n> bytes`, the commit `tools/build-kernel` wrote into
it and the SHA-256 of the file the boot loader loaded, so a transcript or a photo says which kernel ran; before its
first program it prints how long its boot took and how much of that the console spent drawing (`boot: …`).

| Program | What it is | Pin |
|---|---|---|
| wolf | the build compiler (`kernel/wolf.pin`) | 0.2.35 |
| wolf, dev | the dev image's compiler, `/usr/bin/wolf` (`user/wolf.pin`) | 0.2.36, `5adf3d9` |
| lupin | the reference interpreter for wolf, `/bin/lupin` | 0.1.59, `668fb752` |
| wolf-std | the standard library beside lupin, `/usr/share/wolf/std` | `3111d39f` |
| pelt | the POSIX shell, PID 1 at the console | `4683b3f5` |
| boreutils | coreutils in wolf, 107 command binaries in `/bin` (`df` not yet) | `ff5396ad` |
| scent | grep in wolf: `/bin/scent`, with `grep` a link to it and `egrep` and `fgrep` its wrappers | `eb888dfc` |
| den | version control in wolf, Git's repository formats byte for byte: `/bin/den`, with `git` a link to it, and its wire over `file://`, `git://`, SSH and HTTPS | `ac2332bf` (wolf 0.2.36) |
| burrow | the ssh client in wolf: `/bin/ssh` and `/bin/burrow-keygen` (Ed25519) | `0d98ce92` (wolf 0.2.37) |
| trash | a reversible rm in wolf: `/bin/trash` puts files in the user's `~/Trash`, and `trash-list`, `trash-restore`, `trash-rm` and `trash-empty` look after it | `c027df83` (wolf 0.2.38) |
| the root set | Mozilla's root store, as curl extracts it: `/etc/ssl/certs/ca-roots.der`, the roots den's HTTPS trusts | `cacert-2026-10-20` (`user/roots.pin`) |
| yew | the editor | `2eb9cb9b` |
| lope, aspen, lobo | the directory jumper, tree(1), the web server | `d65bb03c`, `096245c8`, `39788b86` |
| clef | the assembler in wolf, opt-in at `/usr/bin/clef` of the dev image | `user/clef.pin` |
| pack, cub, trail | three wolf games, installed by the installer into `~/Games/` with their source | `27848095`, `6a1db765`, `24099a81` (engines `aa6c4dc0`, `74b89744`, `57870143`) |

Every program is built from its own tree, static, and pinned by commit or by digest (`user/*.pin`); `tools/mk*` builds
each. `tools/mkdistribution VERIFIED_BASE.cpio BUILT_INPUTS NEW_OUT` assembles both image variants at one clean
commit: it rebuilds the kernel and the installer, verifies the supplied program outputs, and keeps only the unchanged
compiler and linker bundle from the digest-pinned prior dev payload. Every packed file has a build-time digest
inventory. trail is held at its pin until the [glyph-probe mismatch](https://github.com/wolffe-lang/trail/issues/8)
is resolved. Every ELF process starts with a fixed 1 MiB initial stack, which `RLIMIT_STACK` reports.

Two things the shipped `grep` says that GNU's would not: `--help` and `--version` are scent's own prose, and a
diagnostic names the program as `grep:` whatever path ran it. `-r` and colour are refused by name until scent's next
milestone. Everything else on its first-milestone options is byte-identical to GNU grep 3.12 in the C locale.

`git` is den. `/bin/git` is a symbolic link to `/bin/den`, and den does not read argv[0] yet, so `git` behaves
exactly as `den` does: `git --version` prints den's own line, `den 0.0.0 (built with wolf 0.2.36)`, and `git` or
`den` alone prints den's own usage text, `den: not yet implemented: <command> (unplanned command)`, with status 2.
den reads and writes Git's repositories byte for byte on its local verbs: `init`, `add`, `rm`, `mv`, `status`,
`commit`, `log`, `show`, `diff`, `restore`, `branch`, `switch`, `tag`, `reset`, `merge`, `rebase` (linear),
`cherry-pick`, `revert`, `blame`, `stash`, `notes`, `repack`, `verify-pack`, `fsck` and Git's plumbing. Its wire
(`clone`, `fetch`, `pull`, `push` over `file://`, `git://`, SSH and HTTPS, with `upload-pack`, `receive-pack` and
a one-session `daemon`) is in the binary within den's own limits; on PAX it works on one machine and, over the
network the console starts, with GitHub (both below). `config` writes a repository's settings as well as reading
them; set `user.name` in `~/.gitconfig` or with `GIT_AUTHOR_NAME`. It has no `ls-remote`, no `gc`
and no hooks, and it never runs an editor or a pager: give a message
with `-m` or `-F` (with `GIT_EDITOR=false` the attempt fails as Git's does, and any other editor is refused by
name). One thing to know at the console: den prints a date only from the zone database (`$TZDIR/$TZ`, by default
`/usr/share/zoneinfo/UTC`, which the images carry as the bytes of `/etc/localtime`); at the terminal `den log` draws
its decorations as Git does (`--no-decorate` leaves them out). `tests/mpx5-den` types a whole session at PAX, as root and as a user, in repositories on an ext2 `/home`, and
holds every verb's status, output and error to the same den on Linux; it also logs in as a user through the
installed system's console login and runs den at the terminal, with nothing redirected. `tests/distribution-den`
commits on a disk the installer wrote, reboots, and reads the repository back clean, every object file Linux's
bytes.

**Remotes on one machine.** den's `file://` remotes work at the console. den runs a remote's service as a program,
`$DEN_UPLOAD_PACK` or `$DEN_RECEIVE_PACK` with the repository's path, and Git's `git-upload-pack` and
`git-receive-pack` from `PATH` when they are unset. PAX has no Git, so it installs those two names as den's own
wrappers, `/bin/git-upload-pack` and `/bin/git-receive-pack`, each two lines (`exec /bin/den upload-pack "$1"`,
and `receive-pack` likewise), and sets neither variable, so every shell finds them:

```sh
den clone -q --bare file:///home/pax/src /home/pax/hub.git   # a bare repository to push to
cd /home/pax/src
den remote add origin file:///home/pax/hub.git
den push -u origin main
den clone -q file:///home/pax/hub.git /home/pax/work         # then fetch, pull --no-rebase and push
```

Name a remote by a `file:///absolute/path` URL (den refuses a plain path), and push only to a bare repository
(den's receive-pack takes no other). Once a branch tracks a remote, `status` and `branch -vv` name it as Git does
(`Your branch is up to date with 'origin/main'.`).
`git://` remotes go over the network stack, which the console kernel every image boots starts: `den daemon
--enable-receive-pack BASE PORT` serves one connection on 127.0.0.1 from a bare repository holding
`git-daemon-export-ok`, and a clone or push through `git://127.0.0.1:PORT/…` then works at the console.
`tests/mpx5-den` types all of this at PAX as root and as `pax`, under `/tmp` and on the ext2 `/home`, and holds
every answer, object id and ref to the same keys typed on Linux.

Until px104 the wrappers lived in `/usr/libexec/den` and `/etc/shrc` exported the two variables naming them, as px100
decided; px104 changed that decision. den's ssh transport sends the same program word to the far side, so a console
shell asked the server to run `/usr/libexec/den/receive-pack '…'` where a Git server expects `git-receive-pack '…'`.
An upgrade replaces an `/etc/shrc` you never changed; if you
changed yours, the upgrade keeps it and writes the new one beside it as `/etc/shrc.pax-new`: delete these two lines
from yours (the new text is in the `.pax-new` file):

```sh
export DEN_UPLOAD_PACK=/usr/libexec/den/upload-pack
export DEN_RECEIVE_PACK=/usr/libexec/den/receive-pack
```

**Pushing to GitHub.** den pushes over HTTPS and over SSH from the console, through the network it starts (below).
Names resolve as on Linux: the lease (or `/etc/pax-net`'s static line) writes `/etc/resolv.conf`, and the C
library reads `/etc/hosts` first, so a line there (`140.82.112.3 github.com`, an address of GitHub's
published ranges) is the fallback when no DNS server answers.

- **HTTPS** checks the server against `/etc/ssl/certs/ca-roots.der`, Mozilla's root store as curl publishes it
  (dated 2026-10-20, 118 certificates; the Mozilla Public License 2.0; `user/roots.pin`), which `/etc/shrc` names
  as `DEN_TLS_ROOTS`; a server whose chain reaches no root in it is refused by the TLS client's own name (`TLS
  issuer_mismatch`). The credential is a GitHub token: den reads `DEN_HTTP_TOKEN`, or asks for it at the terminal
  (`Token: `, with no echo) when stdin is one, and never writes it anywhere.

  ```sh
  den clone -q https://github.com/OWNER/REPO.git repo
  cd repo && den commit -a -m '…' && den push -q origin main   # asks `Token: ` unless DEN_HTTP_TOKEN is set
  ```
- **SSH** goes through burrow, the org's ssh client, installed as `/bin/ssh` with `/bin/burrow-keygen`: den runs
  `ssh` from `PATH` (it reads no `GIT_SSH` or `core.sshCommand`). Make a key on PAX and add its public line to
  GitHub (a deploy key or your account's), or copy a key you have (an unencrypted Ed25519 key in OpenSSH's format,
  mode 0600). GitHub's published host key is pinned in `/etc/ssh/ssh_known_hosts`; burrow reads known_hosts files
  only from `~/.ssh`, so name it in `~/.ssh/config`. A server answering for github.com with another key is refused
  by name (`host_key_changed`).

  ```sh
  mkdir -p ~/.ssh && chmod 700 ~/.ssh
  burrow-keygen -t ed25519 -f ~/.ssh/id_ed25519      # then: burrow-keygen -y -f ~/.ssh/id_ed25519 to GitHub
  printf 'Host github.com\n\tUserKnownHostsFile ~/.ssh/known_hosts /etc/ssh/ssh_known_hosts\n' > ~/.ssh/config
  den clone -q git@github.com:OWNER/REPO.git repo
  ```

Nothing secret ships: the images carry no token and no key, and a key made on the live medium is gone at reboot
unless `~` is on a disk. den has no `ls-remote` and no `rev-parse` yet: `den fetch origin`, then `den log -n 1
--pretty=oneline --no-decorate origin/BRANCH`, shows what a push left, and `den fetch --prune origin` drops a branch
the far side no longer has. `tests/mpx4-console-push` types these steps at the console against fixtures that answer as
github.com (den's own HTTPS fixture and OpenSSH's sshd, a DNS server of the suite's own), holds each to Git's
answers for the same steps on Linux, and, given a repository on GitHub in its environment, pushes there.

## Booting PAX

PAX boots through the Limine protocol (`docs/BOOT.md` says why). Limine is fetched from its release by digest, never
built here. There are four ways to boot, from least to most durable.

### From the ISO

The default: everything the image holds is in memory and gone at the next boot.

```sh
tools/qemu-run --firmware uefi build/mpx1/native/kmain.iso; echo $?
tools/expect-serial build/serial.log PAX "firmware: uefi"
tools/qemu-gdb build/pax-stub.iso build/stub/pax-stub.elf     # gdb, frozen at reset
```

### A disk beside the image

Give QEMU an ext2 image as a virtio block device and the kernel mounts it where the image's `/etc/fstab` says, the
playground's at `/home`:

```sh
tools/mkdisk --home 128M pax-home.img
qemu-system-x86_64 -machine q35 -cpu max -m 512M -display cocoa \
    -serial file:serial.log -nic none -cdrom IMAGE.iso \
    -drive file=pax-home.img,if=none,id=d0,format=raw -device virtio-blk-pci,drive=d0
```

Without `-no-reboot`, root's `reboot` restarts the machine and the same disk boots again. Between boots, `e2fsck -fn
pax-home.img` and `debugfs` read it on the host: the file is the file system, with no partition table.

### A disk that boots

One file, no ISO. `tools/mkdisk --gpt` writes a GPT disk with an EFI system partition (Limine, the kernel, the
initramfs), a BIOS boot partition for Limine's stage 2 and an ext2 partition 2; with `--root` the whole system is
installed onto partition 2 at build time, every mode, owner and time from the archive's own headers, and the kernel
mounts it as `/` from `root=` on Limine's command line (`/dev/vda2`, `PARTUUID=`, `UUID=`, `ro`, `rw`, in Linux's
spellings) with no initramfs. The root is ext3 by default since the journal was added; `--no-journal` makes an ext2 one.

```sh
tools/mkdisk --gpt --kernel K.elf --root I.cpio 512M pax-disk.img
```

Under BIOS (SeaBIOS):

```sh
qemu-system-x86_64 -machine q35 -cpu max -m 512M -nographic -nic none \
    -drive file=pax-disk.img,if=none,id=d0,format=raw -device virtio-blk-pci,drive=d0,bootindex=0
```

Under UEFI, with the edk2 firmware Homebrew's QEMU ships as a read-only flash (`-bios` with this file is refused):

```sh
qemu-system-x86_64 -machine q35 -cpu max -m 512M -nographic -nic none \
    -drive if=pflash,format=raw,unit=0,readonly=on,file=/opt/homebrew/share/qemu/edk2-x86_64-code.fd \
    -drive file=pax-disk.img,if=none,id=d0,format=raw -device virtio-blk-pci,drive=d0,bootindex=0
```

What to know at the prompt:

- `-nographic` puts COM1 and QEMU's monitor on the terminal: Ctrl-A x quits QEMU, Ctrl-A c switches to the monitor
  and back, and Ctrl-C reaches PAX.
- `/` is the disk, so what you change anywhere lasts (`/etc`, `/root`, `/home/pax`, `/bin`), but for `/tmp`, which is
  memory. Try `echo hello > /etc/motd`, `lope add /usr/share/tunes`, `cat > notes.txt`, then `reboot`: all three are
  there on the next boot. `cat /proc/self/mounts` shows `/dev/root` at `/`; `cat /proc/partitions` shows the table
  PAX read.
- `exit` (or Ctrl-D at the prompt) sends every process SIGTERM, then SIGKILL after two seconds, writes every volume and
  unmounts it, `/` last, marked clean. On the host, `dumpe2fs -h` of partition 2 then says `clean`.
- **Closing QEMU without `exit` (Ctrl-A x, the window, the terminal) is a power cut.** What the last five seconds wrote
  may be lost. A journalled root is replayed at the next boot before anything reads it; an ext2 root stays `not cleanly
  unmounted` until an offline check repairs it: `fsck.ext2 -y /dev/vda2` from the rescue archive, or `e2fsck -fy` of
  partition 2 on the host (it starts at `--esp` + 2 MiB).
- A second and third disk: `tools/qemu-run --drive a.img --drive b.img` (repeatable; `FILE,ro` for read-only). PAX
  names them `vdb` and `vdc` in PCI slot order, and `/dev` holds a node for every disk and partition.

### The live USB stick

`tools/mkdisk --usb` writes a reproducible raw GPT image with one FAT32 EFI system partition and a reserved Limine BIOS
partition; the supplied initramfs is preserved byte for byte, so the whole live system and any installer or games
payload stay in memory. The live entry accepts `root` with no password and starts pelt; it changes no installed
account and provides no authentication. It boots `quiet`: no line for a program's ordinary life on the screen the
installer draws on.

```sh
tools/mkdisk --usb --kernel K.elf --initramfs I.cpio --conf boot/limine-usb.conf pax-stick.img
tools/qemu-run --firmware uefi --usb-stick pax-stick.img       # xHCI mass storage, no CD-ROM, no virtio disk
tools/usb-write --dry-run pax-stick.img /dev/sdX               # inspect a removable target; the write is yours to do
PAX_WOLF=$(tools/fetch-wolf) tests/usb-stick --tier native     # BIOS and UEFI, the quiet live login, Linux mounting the ESP
```

Physical writes and real-machine boots are not tested here. See
[The live USB stick](docs/BOOT.md#the-live-usb-stick).

For a machine that resets with nothing on the screen, `boot/limine-triage.conf` builds a triage stick (px77d): with
the command-line word `triage` the kernel installs its own exception table on an interrupt stack and turns machine
checks on as its first act, draws a numbered box at each early step and the firmware's handover in a band under the
console, and draws any fault in large hex and halts instead of resetting; further words turn one suspect off at a
time (`nofb`, `fxsave`, `low4g`, `keeplint0`, `noxhci`, `noblock`, `nosound`) or one of triage's own effects
(`noidt`, `nomce`, `nodraw`, `fullh`, `boot/limine-bisect.conf`). Without the word nothing of it runs.
`tests/mpx6-triage` (the firmware suite's F10) boots every word under QEMU. Since px77d the live kernel loads its own
exception table, with the NMI and the machine check on stacks of their own, and turns machine checks on as its first
act, so an NMI arriving during the boot is logged and survived and a machine check is a named panic with its banks,
never a silent reset (`tests/mpx6-nmi`, F11; `boot/limine-fix.conf` builds the stick that carries it).

**When a boot goes black** (px118, `notes/px118-boot-diagnosis.md`, its last section the page for a person at the
machine). Limine's menu shows for five seconds on the stick and on an installed disk, with its verbose loading lines
(and on a serial port where there is one), so a screen black before the menu is told from one black after it. The
console kernel beeps twice: high at its entry, before it touches the framebuffer, and low when its console has drawn
its first line; one beep and black means it ran and never drew, none that it never started (`pax.nobeep` silences
both). At each stage (entered, drawn, memory, framebuffer, devices, root, init, end) it writes the stage to port
0x80 (a board's POST-code display shows `11` to `88`), to eight bytes of CMOS (0x78-0x7f, claimed only when they
read zero, never written when they hold another's bytes; `pax.nomarks` turns that off) and to a log of its console
kept in memory a reset may leave. The next boot says on the screen how the previous one ended (`marks: boot N; the
previous boot, N-1, stopped at STAGE`), offers it as `/proc/pax-boot` and `/proc/pax-bootlog`, and its first program
writes it to `/var/log/boot.log` (root's, with the previous boot's console when it survived) and
`/var/log/boot.summary`; `pax-boot-status` lists the last ten boots for anyone. `tests/mpx6-bootlog` holds all of it
under QEMU, both firmwares.

### The guided installer

`pax-install` inventories the real block nodes, shows a read-only plan, names the target by model, serial, size and node,
and writes only after the word `yes` (anything else cancels). It is an explicit ext2 developer preview, not a journalled installation:

- whole-disk fresh installs only, 512-byte sectors, root volumes up to 16 TiB less one 4 KiB block;
  larger targets keep that root size and name the remaining space as unused in the plan;
- the running root's disk, mounted disks, read-only targets and disks of 4096-byte logical sectors are refused by name;
- it asks for a user name and whether to install the three games, staged offline with their source and their engine's,
  and, after the confirmation, whether to set root's password and the user's (each a `passwd` run, or the account
  left locked), and makes the user a member of group `sudo` ([Passwords](#passwords-login-su-and-sudo));
  neither answer fetches anything; the games answer alone decides the install from the verified payload (the live
  demo's marked Games directory is never copied implicitly), and a custom source tree with a Games directory already
  present is still refused;
- it writes with `paxgpt`, `paxfat` and `paxext2`, PAX's own disk tools (below), not embedded formatters;
- a used disk is fine: after the new table and before any formatter or Limine, it zeroes the BIOS boot partition
  whole (an older install's first partition at sector 2048 leaves its file system there, and Limine refuses to
  install over one), the first and last MiB of the EFI partition and the root, the first MiB outside the table and
  the log, and the sectors before the backup table, each a phase of the plan and the log
  ([A used disk](docs/BOOT.md#a-used-disk-px86));
- it writes only to a disk whose model and serial are on the install allow-list, `/pax/install-targets` on the boot
  stick (shipped naming no disk; one `model=… serial=…` line a disk, copied from Linux's
  `/sys/block/sdX/device/{model,serial}`); every other disk is listed and refused by name, and the running root, a
  mounted or read-only disk and the stick are refused before the list is read; `pax-install --check` shows it all
  and writes nothing;
- it appends its transcript to `/pax/logs/install-<n>.txt` on the stick after every step, ending with the SHA-256 of
  the first MiB of each partition it wrote, for a machine with no serial port;
- what the stick wrote while it ran stays on the stick: its DHCP lease (`/var/lib/dhcp`), `/etc/resolv.conf`,
  `sudo`'s log, and root's dotfiles and `/Trash` (root's home is `/`: the shell's history, lope's store, what `trash`
  put aside) are never copied to an
  install or an upgrade, nor listed in its manifest; the installed system writes its own;
- an install made from the live stick boots to `/bin/login`, not the stick's passwordless entry: root or the new
  user, with their passwords, or root with none while every account is locked (the first-boot rule above). As
  Linux's `login` does, the login gives the terminal to the account it logs in (its user, its primary group, mode
  0600), so what the user opens by name, such as `/dev/stdout` or `/dev/stderr`, is theirs to open.

The installer and the installed tree are tested on separate QEMU virtio disks under BIOS and UEFI, including reboot
persistence, and on used ones (an old ESP and root, an old root and swap, an old live image; `tools/used-disk`), each
left with no signature but PAX's. The merge gate (`tier full`) also installs onto a sparse 500 GB disk and `tier all`
onto 4 TB, each target then booted alone under both firmwares. `tests/mpx6-kasumi` (`tier full`) runs the whole path
on a QEMU machine shaped like kasumi: OVMF, no serial port, the stick and the keyboard on one xHCI controller, an NVMe
disk for CachyOS and three SATA disks; it installs to the listed disk through the keyboard, boots it alone, logs in
and reads back a file written before the reboot, and holds every other disk byte-identical, then does it all again
onto a used 1 TB disk shaped like kasumi's own target. Nothing here is a claim about a real machine:
[docs/INSTALL-METAL.md](docs/INSTALL-METAL.md) is the runbook for kasumi. See
[Guided installation](docs/BOOT.md#guided-installation).

### Upgrading over ssh

An installed PAX that already has `pax-upgrade` (the stick that brings it installs or upgrades as before) takes a
newer image from another machine on the network and upgrades itself from it at the next boot, the stick staying in the
drawer. What is sent is the image's archive, `pax-dev-COMMIT.cpio` (or `pax-COMMIT.cpio` for the release image), the
same bytes a stick from that build carries at `/boot/initramfs.cpio`; its sha256 is in the build's `sha256.txt`. The
installed root needs about twice the archive's size free. Three commands, from the other machine, as your own account
(a member of group `sudo` with a password):

    ssh YOU@HOST 'pax-upgrade receive --sha256 DIGEST' < pax-dev-COMMIT.cpio
    read -s PASSWORD; printf '%s\n' "$PASSWORD" | ssh YOU@HOST "sudo -k -S -p '' pax-upgrade arm --reboot"
    ssh YOU@HOST pax-upgrade status

- `receive` needs no root. It writes what arrives to `~/.pax-upgrade/`, hashes it as it arrives and again when it
  reads it back, and keeps it only when both are the digest you gave; anything else keeps nothing, so send it again.
- `arm` is root's. It moves the archive into `/var/lib/pax-upgrade/` (root's alone), reads it back, and refuses by
  name before it changes anything: nothing received, a digest that differs, too little space, an image older than the
  installed one or the same one, an archive with no boot entry of its own, a disk that reports no model or serial,
  an EFI partition whose `limine.conf` is not the installer's text (an edited one is never merged), a second arm, a
  caller that is not root. Then it puts the archive's kernel on the EFI partition and makes the archive's own entry,
  `PAX: upgrade from the staged image`, Limine's default for the next boot, with a five-second menu.
- The next boot reads the archive from the root, checks its sha256, and upgrades the installed system from it exactly
  as the stick's upgrade entry does (`pax-install --upgrade`: your files kept, a new version beside each one you
  changed as `.pax-new`, `/home` and `/root` never touched), with the arm as the confirmation. Then it reboots into the
  upgraded system, which comes back on the network as before and removes the staged files at its first boot.
- `status` needs no root: what you received, and the last lines of `/var/log/pax-upgrade.log` (armed, applying,
  upgraded, refused, stopped, not applied, and why).
- `sudo -k -S pax-upgrade disarm` takes the arm back before the reboot; `sudo -k -S pax-upgrade clean` removes a
  staged archive that is no longer wanted.
- **Over ssh, always `sudo -k -S`, the password on standard input.** A bare `sudo` over ssh is unsafe with the
  current burrowd: it asks for the password on the machine's own console, not yours, and burrowd stops answering
  until the machine is powered off and on.

**When it does not come back.** First wait: the staged boot is tried twice at most. A staged kernel that cannot read
or check the archive, or a third try, boots the installed system instead; it puts Limine's configuration back,
writes why to the log, and reboots into its own kernel, so `pax-upgrade status` says what happened. If the screen
stops instead, go to the console:

- Limine shows `PANIC` and `Press a key to return to menu.`, or the staged kernel stops on a panic. **A kernel panic
  in the staged boot halts the machine: nothing restarts it, and a person must choose the installed entry at the
  console or boot the stick.** Press a key, or power the machine off and on, and in Limine's menu choose `PAX ext2
  developer preview` with the arrow keys and Enter. The installed system sees that it booted while armed, disarms and says so
  (or log in and run `sudo pax-upgrade disarm`). Each power cycle into the staged entry counts as a try, so after two
  the installed system boots by itself.
- The installed system does not boot either (an upgrade cut after it began writing): boot the stick. Its entry `PAX:
  upgrade the installed system` mounts the root, and `pax-install --upgrade` finishes the cut upgrade from its
  record.

### The network at the console

The console kernel every image boots brings its network up before the first program: a virtio network device, or
one of Intel's gigabit controllers (QEMU's `-device igb`, the I225-V and I226), and over it ARP, IPv4, ICMP, UDP and
TCP. With no device the console still has 127.0.0.1. The image's `/etc/pax-net` (on an installed system, the copy
on its own disk) says how the address is taken; the release and dev images ship `dhcp wait=10`:

```
dhcp [wait=<1-600>]                                          # a lease; wait at most that long for it (30 s without)
static <a.b.c.d>/<prefix> [gateway <a.b.c.d>] [dns <a.b.c.d>]...   # this address, up to three DNS servers
```

Without the file the address is 10.0.2.15/24, gateway 10.0.2.2 (QEMU's user network). The lease or the static
address is on the console before the prompt (`dhcp: … bound …`, or `net: static …`), with the router's answer to
the kernel's echo, and `/var/lib/dhcp/pax.lease` and `/etc/resolv.conf` say the same to any program; a program's
resolver reads them (and `/etc/hosts` first), so den and burrow reach a host by name. A missing or
silent network never stops the boot: the console waits for the first lease at most `wait` seconds, not at all when
the cable has no link (the client goes on asking), and an Intel controller's own start at most 12 s; one line,
`net: the console waited <w> ms for the network (bound <b> ms: …)`, says how long it took and the bound it held.
Under `quiet` (every shipped image boots with it) a renewal prints nothing. `nonet` on the kernel command line
starts no device at all. To try it under QEMU, give the ISO a NIC:

```sh
tools/qemu-run --firmware uefi pax.iso -- -netdev user,id=n0 -device igb,netdev=n0
```

## Seeing the screen

The harness boots headless. To see PAX's screen, give QEMU a window; on macOS (Homebrew's QEMU, TCG):

```sh
qemu-system-x86_64 -machine q35 -cpu max -m 256M -display cocoa \
    -serial file:serial.log -nic none -no-reboot -cdrom IMAGE.iso
```

(`-display gtk` or `-display sdl` on Linux, where `-accel kvm` makes it fast.) Limine hands PAX its framebuffer, PAX
draws the console there from its first line, and the window's keyboard is the PS/2 keyboard the console reads, so a
shell image is typed into from the window while COM1 still gets every byte. With `-display none` the screen is drawn
where nobody sees it; `-vga none` (`tools/qemu-run --no-screen`) boots a machine with no display at all.

The framebuffer uses the firmware's width, height, row pitch and RGB masks. It draws before the allocator starts, even
without COM1. Spleen's 8×16 glyphs give 160×50 cells at 1280×800; above 2560 pixels wide they are doubled, giving
240×67 cells at 3840×2160. Its cell grid in RAM is the screen's shadow. Where reading the framebuffer is slow (a GPU's
write-combining mapping: such reads are the slowest thing a user would see), a scroll redraws only the cells that
changed and never reads it; where reading is cheap (an emulator's framebuffer is host memory) it copies the framebuffer
onto itself. The screen times framebuffer reads against writes once, when it attaches, to choose, and the boot line
names the way and why.
The console supports:

- the Linux VT's colour renditions (dim, italic, underline, RGB mapped to its small palette), `OSC P` and `OSC R` for
  the palette, sixteen CSI parameters, scroll margins, character and line insertion and deletion;
- 560 glyphs: every braille pattern, the block elements and the other code points the wolf games use
  (`font/extent.txt`); anything else above U+00FF is `?`;
- the keypad's navigation with NumLock off and digits with it on, decimal entry with Alt and hexadecimal with AltGr;
- USB keyboards over xHCI, directly or behind hubs, sharing the PS/2 keyboard's mapping; unplugging one releases its
  held keys, and a replacement can be attached while the system runs; repeat at 250 ms then 33 ms, as measured on Linux.

Blink attributes are recorded but drawn steadily, and `DECSCUSR` is consumed without changing the cursor's shape, as
on the measured Linux VT.

`tools/qemu-run` accepts `--usb-irq=msi|intx`, `--no-hpet`, `--no-pit`, `--no-serial`, `--high-bar` (UEFI: OVMF's
64-bit window, so 64-bit BARs land above 4 GiB) and `--display-mode=3840x2160`; `PAX_USB_IRQ`, `PAX_NO_HPET=1`,
`PAX_NO_PIT=1` and `PAX_HIGH_BAR=1` say the same for every boot of a suite. A display mode also needs the matching
`resolution:` in the image's Limine configuration. Explicit interrupt tests use `nec-usb-xhci` on QEMU 8.2, whose
`qemu-xhci` lacks MSI configuration properties; QEMU 11.1 uses `qemu-xhci`. Neither substitutes a claim about a
physical controller. With no COM1 the kernel keeps its transcript in memory (64 KiB), which `tools/usb-session
--no-serial` reads back through QEMU's monitor.

## Friendly shell editing

Pelt adds opt-in suggestions, syntax colours, abbreviations, history events and extra editing keys. At the prompt:

```sh
set -o friendly -o suggest -o histsearch
```

1. Type `echo prefix_suffix`, then `echo prefix`: the history suffix appears. Enter runs only what you typed; Right
   accepts the suggestion.
2. `abbr add hi 'echo hello'`, then type `hi` and Space.
3. `!!` repeats the previous command, `!$` recalls its last word, and Alt-. inserts the last argument while editing.

Scripts keep POSIX behaviour, and `set +o friendly` turns the additions off. Suggestions default to bright black
(SGR 90); `PELT_COLORS='command=green:shadow=brblack+dim'` dims them and colours resolving commands green. The
framebuffer console reports its current grid; a serial-only console starts with an unknown (0×0) size.

## The dev image

The dev variant adds to the base image, which it leaves unchanged:

| Addition | Where | Notes |
|---|---|---|
| a musl-static `wolf` | `/usr/bin/wolf` | the v0.2.36 tag built unpatched, so it says the release's own line; the first whose static musl programs read their arguments (wolf-lang#962) |
| the compiler's paired standard library | `/usr/share/wolf/compiler-std` | the tag's own, `78b9d3cb`; lupin's stays at `/usr/share/wolf/std`; the shell selects it through `WOLF_STD` |
| a static `ld.lld` 18.1.8 and a link-only `cc` | `/usr/bin` | built from LLVM's release tarball with zlib and zstd (`notes/px80/build-lld.sh`); not a C or assembly compiler |
| musl's binary CRT and libc inputs | | recorded in `user/wolf-link.sums` |
| scent as `grep`, with its fixture | `/usr/share/scent` | `cd /usr/share/scent; grep -n -C1 cat words.txt` |
| clef, the assembler in wolf (opt-in, `tools/mkdev --clef DIR`) | `/usr/bin/clef` | `clef --64 -o x.o x.S`, `clef --expand x.S` |

At the dev console, write a program in your home directory and use:

```sh
wolf fmt hello.lu
wolf fmt --check hello.lu
wolf conform-run --json --phase=typecheck hello.lu
wolf conform-run --json --checked hello.lu
wolf build hello.lu
./hello
```

Three things px65 measured at 0.2.35 (not measured again at 0.2.36): there is no `wolf check` command; `wolf run --checked` is a native build, not the
checked machine, and needs the native link step; and `--release` still needs an external clang, which the image does
not carry. `wolf build --no-cache --emit=obj hello.lu -o hello.o` emits a native object with no linker. The dev ISO is
tested with 2 GiB of RAM. `tests/mpx5-wolf` holds root and `pax` sessions byte for byte to the same binaries on Linux
and checks independent command and verdict witnesses, so agreement on a broken compiler cannot pass; its fast CI root
omits the link bundle on purpose and checks the missing-tool errors.

`wolf lsp`, the compiler's language server, runs on PAX unchanged: it speaks the Language Server Protocol on its
standard input and output, so an editor starts it as a child on pipes. `tests/mpx5-lsp` starts it that way from a
client of its own (`user/elf/lspc.c`, C with no libc: three pipes and an exec-status pipe, `fork`, `setpgid`, one
`poll` over the terminal, the pipes and a SIGCHLD self-pipe) and types a session: `initialize`, a file with a type
error opened (its E0401 published), an unsaved edit that fixes it (the diagnostics cleared after the server's 100 ms
debounce), `shutdown` and `exit`, status 0; and a server made to hang, killed by its process group after 3 s. Every
frame, both ways, is byte-identical to the same client and server on Linux, as root and as `pax`. PAX's monotonic
clock advances with its 100 Hz tick, so a program's own timings there read in steps of 10 ms
([#299](https://github.com/wolffe-lang/pax/issues/299)).

## Disks and rescue

AHCI uses one polled command slot per disk, with reads and writes up to 128 KiB and explicit cache flushes.
Logical sectors must be 512 bytes; 512e disks report their physical sector size through the block ioctls.
Disk names follow controller and port order, not identity: adding a disk on a lower port can rename later disks.
AHCI and NVMe expose hardware model and serial strings under `/sys/block/<disk>/device/`; internal spaces in serials
are preserved. A SATA disk's `model` is its whole ATA model, where Linux shows the first 16 characters (its SCSI
product field). The boot log prints each SATA controller and each disk's port, model, serial, capacity and sector sizes.
AHCI's waits run on the firmware's clock (the HPET, else the ACPI PM timer, else the 8254 PIT), so a gated PIT no
longer stops them; only where none of the three advances is each AHCI controller refused by name, the boot going on
without its disks.
No SATA hotplug, NCQ or interrupt-driven completion is implemented.

Three programs in wolf write disks, built as static Linux executables and run unchanged on PAX:

| Tool | Writes | Compared with |
|---|---|---|
| `paxgpt` | a GPT | sgdisk, sfdisk |
| `paxfat` | FAT32 and VFAT | dosfstools, mtools |
| `paxext2` | an ext2 tree with modes, owners, times, symbolic and hard links (no journal) | e2fsprogs |

`paxext2` formats volumes through 16 TiB less one 4 KiB block, with fully initialized inode tables and sparse
superblock backups. Its large-volume inode density follows Linux's defaults. File data beyond 2 TiB is written and
read back through virtio, NVMe and AHCI, with the same bytes read by a Linux guest.

The tests compare each tool's output with the host's, then build a second disk entirely on PAX through its `/dev/vdb`
node and boot it alone under SeaBIOS and OVMF. Limine's pinned installer is linked statically with no source change,
and its Linux and PAX runs write identical bytes. See `docs/BOOT.md`, "Writing a disk on PAX".

`tools/mkfsck` builds `fsck.ext2` in wolf for Linux and PAX. It checks inodes, blocks, directories, connectivity,
references and allocation summaries; repairs counts, bitmaps, links, orphans and duplicate data blocks; and replays
supported ext3 journals. A separate rescue archive repairs an unmounted `/dev/vda2` without Linux. Unsupported formats
and ambiguous damage are refused, never marked clean, and a mounted volume is never repaired. The current checker
also refuses more than 4,194,304 blocks, 1,048,576 inodes or 512 groups by name; large installed volumes need Linux's
`e2fsck` until the checker is extended. See `docs/BOOT.md`, "Checking a volume from rescue".

## Tests

Every suite is a script under `tests/` that builds images, boots them under QEMU and asserts the serial log, the exit
status and, where the behaviour is Linux's, the same session on a real Linux. Each runs as
`PAX_WOLF=$(tools/fetch-wolf) tests/NAME`; `--images DIR` boots images built elsewhere (a KVM host, a Mac under TCG),
and `--tier native --firmware bios` picks one leg.

| Group | Suites | What they hold |
|---|---|---|
| The harness's own proofs | `proof`, `expect-serial-selftest`, `paxtcp-selftest`, `lobo-session-selftest`, `gdb-attach`, `ci-plan`, `fetch-retry-selftest`, `usb-session-selftest`, `pipe-shape-selftest`, `census`, `kernel-as`, `mkw` | that the harness can fail, that CI's plan covers the change, every syscall by name, both assemblers' identical kernels, the first wolf kernel |
| The kernel's core | `mpx1`, `mpx2-frames`, `mpx2-paging`, `mpx2-interrupts`, `mpx2-sched`, `mpx2-heap` | first light, the frame allocator, paging, named panics and the timer, threads, the heap: read back through QEMU's monitor |
| Programs and the console | `mpx3-user`, `mpx3-loader`, `mpx3-boreutils`, `mpx3-console`, `mpx3-shell`, `mpx3-screen`, `mpx3-threads`, `mpx3-tree`, `mpx3-maps`, `mpx3-speaker`, `mpx3-sound`, `mpx3-orchestra` | ring 3, the ELF loader, boreutils and pelt against the same binaries on Linux, screendumps against the reference renderer, no framebuffer read under a QEMU read watchpoint, the kernel's own identity line, threads and signals, the writable tree, mappings, sound captures |
| The network | `mpx4-net`, `mpx4-udp`, `mpx4-tcp`, `mpx4-ready`, `mpx4-unix`, `mpx4-session`, `mpx4-lobo`, `mpx4-dhcp`, `mpx4-igb`, `mpx4-console-net`, `mpx4-console-push` | captures rebuilt byte by byte, the witnesses against `tools/net-peer` and QEMU's user network (root for the Linux side), `poll` and `epoll`, Unix sockets, lobo serving; the DHCP client against QEMU's server and dnsmasq on a tap (root, dnsmasq), the tick clock held to the clock over the lease, and the UDP and TCP rows again on QEMU's 82576; the console's network: a lease on igb and virtio-net, a static address, no device, no link, a server that never answers, a quiet renewal, and den's clone over https from den's own fixture (git and OpenSSL as black boxes); den pushing from the console over https and through burrow over ssh to fixtures that answer as github.com, names through a DNS server of the suite's own, the resolver's datagram calls against Linux, a scrubbed transcript proven on fake secrets (root, sshd, mke2fs) |
| Users and the shipped programs | `mpx5-users`, `mpx5-accounts`, `mpx5-jobs`, `mpx5-forks`, `mpx5-rates`, `mpx5-pelt`, `mpx5-bore`, `mpx5-scent`, `mpx5-den`, `mpx5-lope`, `mpx5-aspen`, `mpx5-lupin`, `mpx5-yew`, `mpx5-wolf`, `mpx5-lsp`, `mpx5-clef`, `mpx5-screen` | every rule as root and as `pax`, job control typed byte for byte, static musl programs that fork and ask `getrusage`, the rates a clone leans on against the host's Linux, each program's typed session against the same binary in a container, the language server's frames both ways |
| Disks | `mpx6-blk`, `mpx6-ext2`, `mpx6-part`, `mpx6-root`, `mpx6-journal`, `mpx6-nodes`, `mpx6-nvme`, `mpx6-ahci`, `mpx6-disktools`, `mpx6-fsck`, `mpx6-install`, `mpx6-games` | Linux 7.3.0 on QEMU with the same disks, e2fsprogs, the formatters' differentials, a power cut repaired, the installer (and what it tells a user who is not root), the games' frames cell for cell |
| USB | `mpx6-usb`, `mpx6-usbcheck`, `usb-tools`, `usb-stick`, `usb-linux-fetch` | xHCI, hubs, keyboard bytes and hotplug; the stick's boot files, both firmwares, Linux mounting the ESP; the oracle's two pinned Ubuntu packages |
| Firmware and display | `mpx6-firmware` | independent tick-rate checks with and without the HPET and the PIT, the clock's answers to a reading behind the last, a torn read of the HPET and the rollovers of a 32-bit HPET and of the PM timer, the tick timed by the PM timer after a stall inside its calibration (with the PM timer beside the clock, without it, and standing still with it), the timer and scheduler suites on those machines, MSI and INTx keyboard sessions, both MSI layouts, BARs above 4 GiB, reset and S5, a padded pitch, serial-less early panic pixels at 1280×800 and 4K, a serial-less 4K session shaped like the target machine, the metal triage's boxes, fault screens and words, an NMI survived and a machine check named anywhere in the boot (`tests/mpx6-nmi`) |

Suites that need something of the host say so and stop: root for the Linux network side (`tools/linux-net`), docker or
podman for the throwaway containers (`tools/linux-tree`, e2fsprogs), KVM for speed. `tools/mkimage` is reproducible:
every date in an ISO is `SOURCE_DATE_EPOCH`, default the last commit's time, so one commit builds one digest.

## Continuous integration

- A pull request's push runs the suites its change can affect (`tools/ci-plan`, `tools/ci-tiers.map`) on one leg,
  native BIOS; a change to the kernel's core or to CI itself runs every suite on that leg.
- The `full-matrix` label runs every suite on the merge leg (`tier full`); a push to trunk, the nightly and a dispatch
  run every suite on every compiler and firmware leg (`tier all`). Merging needs a green `tier full` or `tier all` run
  at the head.
- Long jobs have budgets: 75 minutes for interrupts, 90 for the heap, 210 each for pelt and users, 90 for users again
  with `/` on AHCI (`mpx5-users-ahci`, a job of its own), and for the installer 110 in `tier full` and 175 in `tier all`
  (its 500 GB and 4 TB installs); the measured stage timings and their headroom are in
  [CI budgets](tests/ci-budgets.d/README.md). The root-disk `chk-soak` has 1200 seconds for its 100,000 rounds.
- A test is seen red before it is trusted: the break is planted in a commit and run of its own, then fixed.
- One known stall of the Linux reference shell ([#196](https://github.com/wolffe-lang/pax/issues/196),
  [pelt#98](https://github.com/wolffe-lang/pelt/issues/98)) gets one retry of its Linux leg only, with a warning that
  names the issue and the first log uploaded beside the retry; a second failure stays red, and nothing else a test
  decides is ever retried. The exception lives in `tools/ci-retry` and goes when the upstream fix is pinned.
- A source fetch is not a test: `tools/fetch-retry` tries a pinned `git fetch` again when the network dropped it (a
  reset, a failed connect, a timeout or a stalled transfer, an HTTP 5xx or 429), three attempts at most, 10 and then
  30 seconds apart, the pinned commit checked after the fetch; an unknown revision or a refusal stops at once. Every
  `tools/mk*` source fetch, `tools/fetch-wolf` and the census go through it (`tests/fetch-retry-selftest`).

## Hosts

| host | build an image | boot one (`qemu-run`, `tests/proof --image`) | gdb (`qemu-gdb`) |
|---|---|---|---|
| linux x86-64 (CI's ubuntu, the pool) | yes: binutils, cc, make, curl, xorriso | yes: `qemu-system-x86_64`; OVMF for UEFI; KVM used when `/dev/kvm` is usable | yes: gdb |
| macOS arm64 | **no**: no x86-64 ELF binutils or xorriso in the base system | **yes**, TCG: Homebrew's `qemu`, which ships its own UEFI firmware; CI's `macos-run` job boots the linux-built ISO on every push | no gdb in the base system; `tools/qemu-run --gdb 1234` and lldb's `gdb-remote 1234` by hand |

- **CI**: `ubuntu-latest` with QEMU 8.2.2, OVMF and xorriso from apt (TCG); the `macos-run` job boots the same ISO,
  checked by digest, with Homebrew's QEMU 11.1.1 (TCG).
- **NixOS**: nothing system-wide is needed. QEMU and xorriso come from a nix-shell and the UEFI firmware from nixpkgs'
  OVMF; use the **combined** `OVMF.fd` with no separate vars file, because the split `OVMF_CODE.fd` + `OVMF_VARS.fd`
  pair hangs in the firmware under KVM there:

  ```sh
  ovmf=$(nix-build --no-out-link '<nixpkgs>' -A OVMF.fd)/FV
  PAX_OVMF_CODE=$ovmf/OVMF.fd PAX_OVMF_VARS= \
    nix-shell -p qemu xorriso --run 'PAX_QEMU=$(command -v qemu-system-x86_64) tests/proof'
  ```
- **Arch-family Linux**: QEMU 11.1.1, xorriso and OVMF from the repositories build and boot everything (TCG or KVM).
- **macOS** (arm64): `tests/proof --image` on an ISO built elsewhere, as CI's `macos-run` does.

The QEMU binary is `$PAX_QEMU` (default `qemu-system-x86_64` on `PATH`) and the UEFI firmware `$PAX_OVMF_CODE` /
`$PAX_OVMF_VARS`, so every host supplies its own. The UEFI leg looks for OVMF at the distro paths in `tools/lib.sh`;
without it `tests/proof` skips that leg loudly, unless `PAX_REQUIRE_UEFI=1` (CI), when it fails.

## Layout

| Directory | Holds |
|---|---|
| `kernel/` | the wolf kernel, one module per subsystem (`kernel/README.md`), its `wolf.pkg` and the wolf and lupin pins |
| `boot/` | the Limine pin and configs, the kernel's entry and requests, port I/O, the control registers, the interrupt trampolines and the descriptor tables' storage (`start.S`, `io.S`, `cpu.S`, `isr.S`, `kernel.ld`), and the harness's assembly proof under `boot/stub/` |
| `user/` | what the images carry: the pins of every shipped program (`*.pin`), the typed sessions (`console/`), `su`, the probes (`elf/`, `net/`), `play/` and `tunes/`, `disktools/` (paxgpt, paxfat, paxext2), `install/` (the guided installer), the fstabs and the shell's `$ENV` file |
| `tools/` | the harness: the fetchers by digest (`fetch-limine`, `fetch-wolf`, `fetch-lupin`, `fetch-usb-linux`) and the source fetches' one retry (`fetch-retry`), the builders (`build-kernel`, `mkimage`, `mkdisk`, `mkdistribution`, `mkinstall`, `mkgames`, `mkfsck`, `mk*` for each program), the QEMU drivers (`qemu-run`, `qemu-halt`, `qemu-fault`, `qemu-gdb`, `expect-serial`), the Linux sides (`linux-run`, `linux-net`, `linux-tree`, `linux-blk`, `linux-part`), the network tools (`net-peer`, `pcap-net`, `pcap-dhcp`, `dhcp-wire`, `gateway-probe`, `paxnet.py`, `paxtcp.py`), the metal stick for the network (`mkwire`), the font tools (`mkfont`, `screen-ref`), the USB tools (`check-usb`, `usb-write`, `usb-typing`), the installer tests' used disks (`used-disk`) and CI's planner (`ci-plan`, `ci-tiers.map`, `ci-retry`) |
| `font/` | the screen's font: Spleen 8×16 (BSD-2-Clause, with its licence), `extent.txt` (the code points drawn above U+00FF), `pax-extra.bdf` (PAX's own rows for the glyphs Spleen lacks) and `games-glyphs.txt` |
| `tests/` | the suites above, each with its fixtures in `NAME.d/`; `ci-budgets.d/` |
| `docs/` | `BOOT.md` (the boot protocol, the disks, the installer and rescue, argued), `SOURCES.md` (the consulted-sources log), `CENSUS.md` (every system call PAX serves, by name), `HISTORY.md` (how PAX got here, lane by lane) |
| `notes/` | one note per lane: its contract and evidence |

The plan lives in the wolf planning repository under `sprints/pax/`. How PAX came to be, in the order it was built, is
[docs/HISTORY.md](docs/HISTORY.md).
