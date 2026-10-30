# px78b — the one-word confirmation (P6, the maintainer's ruling), and pax#254

Contract: `wolf/sprints/pax/78b-the-one-word-confirmation/px78b-the-one-word-confirmation.md` (crawl 54), launched
2026-10-30 on the maintainer's ruling at kasumi mid-install (R-P6-confirm): "Let's remove that step. Manually typing
that hash is a chore. Confirm another way." The guided installer no longer asks for the typed token or for
`ext2-preview`: after the plan it prints one summary naming the disk by model, serial, size and node with the ext2
notice folded in, and installs only on the word `yes`. Two additions from the coordinator during the lane: first (before
the PR), build, qualify and stage a test stick for the maintainer with this change and pax#252's
early IDT; then (the addendum at planning `0c6ebc3`), pax#254, the serial-less unattended install row red on trunk
since px78. Footprint: module (`user/install`, the installer's tests, `tools/qemu-halt`, docs, notes).

## 1. Forbidden, and what was read

No kernel's, firmware's, bootloader's, emulator's or driver's source was read, nor any awk's, nm's or shell's. Read:
the contract and its addendum, RULES §1–§10, PAX's `CLAUDE.md`, `user/install/{ui,plan,main,allow,execute}.lu`,
`tests/mpx6-install`, `tests/mpx6-install.d/{ui.lu,ui.py,planner.lu,install.py,metal.py,root-nvme.py}`,
`tests/mpx6-kasumi`, `tools/{qemu-halt,qemu-run,lib.sh,mkinstall,mkdisk,build-kernel}`, `tests/mpx6-disktools{,.d/pax}`,
`sym()` in `tests/mpx2-*` and `tests/mpx3-*`,
`.github/workflows/ci.yml` (its triggers and the noserial step), `docs/{INSTALL-METAL,BOOT}.md`, the README, the
px71, px77b, px77c and px78 notes and px77c's recipe scripts, pax#254's text, CI's job log of run 40993542282 and its
`pax-mpx6-install` artifact, the runner image's published package list (`actions/runner-images`
`images/ubuntu/Ubuntu2404-Readme.md`), and the planning repo's `wolf/tools/lane-audit.sh`. Run as black boxes only:
GNU nm 2.42 (the containers') and 2.46 (hasu's), mawk (Ubuntu 24.04's), GNU awk 5.4.1 (hasu's, mounted read-only
from `/nix`), strace, QEMU 8.2.2, Ubuntu's OVMF, Limine 12.9.1. kasumi was not touched; hasu's
`:9364` and `:9308` and the maintainer's hasu data were not touched; nothing was installed; no label, dispatch,
merge, issue or release; no attribution trailers. On nomad only `~/lanes/px78b/` and one new file in `~/pax-smoke/`
were written.

The maintainer's disk serial (the test stick's allow-list line) is written `<kasumi-serial>` in every file under
`notes/px78b/`: this repository is public. The staged image carries it, as its sha256 below covers.

## 2. Inputs, verified

- **Base** pax trunk `3958c5a031dc471d16f31e99e93795baccdf0795`; a fresh clone on hasu at
  `/home/mfwolffe/lanes/px78b/pax` (branch `px78b` fetched from origin); the Mac worktree `~/lanes/px78b/pax` on
  `px78b`, the branch asserted before every commit. pax#252 was still open at the final head, so no rebase.
- **Toolchain** wolf 0.2.35 (`4cc4045b…`, read twice: `notes/px78b/archive-reads.txt`), Limine 12.9.1
  (`limine-binary.tar.gz` `5cdebc51…`, `limine-read-{1,2}.sha256`), both from px77c's cache, copied (never moved).
- **Containers** `localhost/px75-ubuntu:2` for the units, the inputs and the release pair; `localhost/px78-ubuntu:1`
  (px75 plus gdisk, fdisk, strace) for every row that runs `sgdisk` (`verify.py`, M10) and the noserial rig. Every
  container `--memory 12g`, `taskset -c 0-5` inside, block A held by
  `flock /home/mfwolffe/lanes/hasu-block-A.lock` for each job alone (`scripts/ctr.sh`; each `acquired`/`RELEASED`
  line in the logs). px77d shares the block; its job held it for one of this lane's waits.
- **The test stick's inputs** px77b's recipe as px77c ran it: px77c's `build/inputs`, `base-dev.cpio`
  (`098b918e…`, read at the copy), `limine-download` and px77d's `lope-local`, all copied; the build head
  `197330ad4042dd349ad698a5e60f3c66f65c9c2c`, a local merge of this branch at `da1db7de` with pax#252's head
  `23d25bfa` (no conflict; README.md merged by git), asserted by `scripts/sbuild-inside.sh` and by
  `tools/mkdistribution` (`stick-commit`). The merge is not pushed: the PR carries only this lane's commits.

Commits on `px78b` (tests first, then the change; the prediction after the change, see §3):

- `b92b0daa` tests/mpx6-install.d/ui: the one summary and yes; every other word cancels
- `d828f1c8` tests/mpx6-install.d/planner.lu: the summary's size and the plan's record
- `266dadb2` tests/mpx6-install: guided rows type yes; cancel-words in QEMU, target byte-identical
- `415122c7` tests/mpx6-install.d/metal.py: M3-summary names the target; yes installs
- `a27a71ad` user/install: one summary naming the disk and the word yes; no typed token
- `0eed9600`, `a6454777`, `da1db7de`, `bd9d29d2` the runbook, the README (a README-only commit), docs/BOOT.md (twice)
- `54aaf431`, `17c549aa` the test stick's prediction and its stamp
- `44fb33ea` tools/qemu-halt: nm lookups read nm to its end; no SIGPIPE exit 141 (pax#254)
- `9a645508`, `47d3db98`, `8382358b`, `4de33501` the evidence under `notes/px78b/`; then this note

## 3. Prediction, scored

`notes/px78b/prediction.txt` (`54aaf431`, 07:31Z) was written after the change was green locally and before the
test stick's build finished and its leg ran. **Departure:** not before the first change, as RULES §5 asks; the
coordinator's priority change put the stick first and the prediction covers only it.

| predicted | found |
|---|---|
| 795,869,184 bytes (px77c's), or one MiB more | **wrong**: 794,820,608, one MiB *less* (px77d's fix stick's size) |
| a second build byte-identical | **right** (`PASS second stick build byte-identical`, `logs/schain.log`) |
| six ESP files: the five boot files, the list as `boot/install-targets` plus one line | **right** (`logs/stick-kasumi-usb-check.log`; the list `c21b04ae…`) |
| the leg on a copy under KVM: M0–M10 PASS, the summary naming the 860 and its serial | **right** (`logs/schain.log`, `leg-stick/04-plan.txt`) |
| the install 20–35 s from the yes; the leg 55–90 s | **right**: 26.27 s; 71.6 s |
| the plant: I-ui-confirmation red at `y`; I-cancel-words red | **right on the unit** (by name); **the QEMU row red, but not by name**: a `y` that installs leaves the typed keys out of step, and the row ended at qemu-halt's 1200 s deadline (§4) |

## 4. Evidence index

### The change (R-P6-confirm)

After the plan the guided installer prints, then asks (pasted from the branch's own kasumi leg under KVM,
`leg-branch/04-plan.txt`; kernel `user:` lines between them omitted):

```
Erase Samsung SSD 870, serial PX78-TARGET-0001 (500.1 GB, /dev/sdc), and install PAX?
The root file system is ext2 without a journal.
Type yes to install; anything else cancels: pax-install>
```

`yes`, exactly, installs; anything else, empty, `q` and EOF included, returns `cancelled` from `guided_plan`, so the
stop is the token path's own, `pax-install: cancelled/refused before writes: cancelled`, exit 1. The size is decimal
GB, TB from 1000.0 GB, one decimal, the nearest tenth, as a disk's label counts (`plan.lu` `size_text`, divided
before rounding: the planner's INT_MAX disk prints `9223372.0 TB`); a disk with no model (virtio) prints `(no model)`.
The plan's `token` field stays, for two readers only: the scripted path, `pax-install --install --ext2-preview
--confirm TOKEN` (unchanged, the non-interactive path every unattended row and `tests/distribution-install` use, its
token from `--dry-run`), and the install log, whose copy of the plan keeps the `confirmation …` line as the record of
what was erased (`plan_text`); the screen's plan (`plan_body`) has no confirmation line. No other prompt changed.
`tools/usb-write`'s own typed confirmation (the host-side stick writer, not the installer) is unchanged.

### Rows, red then green (hasu block A)

| row | at `415122c7` (tests only) | at `a27a71ad` |
|---|---|---|
| planner I-size, I-plan-record | red: `nothing named size_text`/`plan_body` is in scope (wolf build exit 2) | PASS |
| ui I-ui-eof, I-ui-answers, I-ui-confirmation, I-ui-resize | red: I-ui-answers' assertion (the old prompts) | PASS: `y`, `YES`, `Yes`, `q`, empty, the old token, `ext2-preview`, the old `confirmation` line each cancel |
| I-cancel-words (QEMU, TCG) | | PASS: `y`, `YES`, `q`, empty and the old token each cancel at the summary; target byte-identical (`logs/cancel-words.serial`) |
| guided-yes (`PAX_INSTALL_GUIDED=1`, `verify.py`) | | PASS: install, oracles, tree, boot files |
| kasumi leg (`tests/mpx6-install --only metal`, KVM) | | M0–M10 and I-metal PASS; install 26.66 s, the leg 66.8 s (`leg-branch/result.json`) |

Logs: `logs/units.log`, `logs/chain.log` (the rows' first run stopped at `verify.py`: `sgdisk` is not in
`px75-ubuntu:2`), `logs/chain2.log` (the rows in `px78-ubuntu:1`, then the leg).

**The plant** `px78b-plant-y` (`b4faadb8`, pushed, never merged): `y` accepted as yes. Run locally, a module lane's
way (RULES §7), `logs/plant.log`: the ui unit red by name, `AssertionError: ('y', …` in I-ui-confirmation,
`UNIT-UI-EXIT=1`; the QEMU cancel-words row red (`ROW-CANCEL-WORDS-EXIT=1`) but at qemu-halt's deadline, `NOT HALTED:
no line matching /halt/ within 1200s`, its transcript showing why (`logs/plant-cancel-words.serial`: `y` installed,
`phase gpt: durable`, `Installation complete`, `CANCEL-EXIT-0`, then the keys out of step).

### The test stick (the coordinator's addition)

`~/pax-smoke/pax-install-kasumi-197330ad.img` on nomad, read-only, 794,820,608 bytes, sha256
`0a769a37f26f8bde194b1ee2523fddc4af4c987478cbd2e1c78bd351ccbfd827`, read six times, all equal: twice after the build
and twice at staging on hasu (`kasumi-hasu-{build,stage}-read-{1,2}.sha256`), twice on nomad (`shasum -a 256`).
Built by px77b's recipe at `197330ad` (`scripts/sbuild*.sh`, `scripts/sstick.sh`): the release pair, the live payload
(`live-payload.txt`), `tools/mkdisk --usb` with `boot/limine-usb.conf`, `tools/check-usb` with six expectations
(`logs/stick-usb-check.log`), a second build byte-identical, the EFI and MBR corruptions refused by name
(`logs/stick-usb-{efi,mbr}-red.log`); the plain stick `c69ecd63…` (`stick-plain-read-{1,2}.sha256`). The kernel
carries pax#252 (18 `triage` symbols in its symbol table, `_Wtriage.start` among them: `logs/stick-kernel-triage-symbols.txt`). Then `scripts/sline.sh`: the
maintainer's line `model=Samsung SSD 860 serial=<kasumi-serial>` appended to `/pax/install-targets` on a copy by the
stick's own `paxfat`, the file read back equal to `boot/install-targets` plus that line (`install-targets.expected`,
one entry), `check-usb` again with that file (`logs/stick-kasumi-usb-check.log`), the copy renamed to the staged name
and made read-only.

Qualified on a copy (`leg-stick/stick-at-start.sha256`, equal to the staged sha) by `scripts/sleg.sh` under KVM in
`px78-ubuntu:1`: the branch's `metal.py` through `make-variant.py` (seven edits, each asserted once: the target an
ide-hd "Samsung SSD 860 EVO 500GB" with the maintainer's serial, which PAX shows as "Samsung SSD 860"; no append, the
stick already carrying the line). M0–M10 and I-metal PASS; the install 26.27 s from the `yes`, the leg 71.6 s
(`leg-stick/result.json`); the witnesses `23e7b466…`, `e1203a73…`, `303fd56e…` before and after. The screen:

```
Erase Samsung SSD 860, serial <kasumi-serial> (500.1 GB, /dev/sdc), and install PAX?
The root file system is ext2 without a journal.
Type yes to install; anything else cancels: pax-install>
```

(`/dev/sdc` in px78's machine; on kasumi, the SSD alone, it is `/dev/sda`.) `~/pax-smoke/INSTALL.txt` is px77c's and
was not edited; its lines 1 (NOT YET), 13 (the candidate's name) and 175–177 (the typed `ext2-preview` and
confirmation) are stale for this stick.

### pax#254: the serial-less unattended install (the addendum)

**Reproduced** on hasu block A under TCG, the row as CI runs it (`tests/mpx6-install --only noserial`, in
`px78-ubuntu:1`), with GNU awk first on PATH (`scripts/ns-all.sh`, `logs/ns-all.log`): from trunk's
`tools/qemu-halt` (the worktree at `415122c7`) red 2 of 3 with CI's exact line, `install.py:149`
`AssertionError: (141, b'', b'')`, the third green. With Ubuntu's mawk the same row is green (`logs/noserial-repro.log`,
44 s); the red needs the reader that acts at once.

**The cause, witnessed.** `tools/qemu-halt` runs under `set -euo pipefail`, and with `--no-serial` it looks up the
transcript's two symbols unguarded: `cnt_addr=$(nm "$elf" | awk '$3 == "pax_serial_log_count" { print "0x" $1;
exit }')` (and `log_addr` likewise). nm writes its sorted table in 4096-byte writes (`scripts/nm-writes-witness.sh`,
`logs/nm-writes-witness.log`: the head's native kernel, 65 writes of 4096 bytes and a last of 2145). When awk reaches the symbol and
exits while nm still has a write to make, nm dies of SIGPIPE, pipefail makes the assignment's status 141, and `set -e`
ends qemu-halt with 141 before QEMU starts, printing nothing. The witnesses:
- **CI's red is that window**: in run 40993542282's artifact (`pax-mpx6-install`, `noserial-uefi/`) the install took
  0.115 s (`install-timing.json`) and `install.serial` is empty: qemu-halt had emptied the log (it does so just before
  the lookups) and ended before QEMU, for the artifact keeps every `*.log` and holds no `install.serial.qemu.log`
  (`tools/qemu-run` writes it as QEMU starts). The lookups are the only unguarded commands in that stretch that end
  without a word. The local red leaves the same footprint (`logs/ns-red-footprint.txt`): 0.044 s, an empty
  `install.serial`, and neither `install.serial.halt` (made just after the lookups) nor `install.serial.qemu.log`.
- **The lookup alone** (`scripts/sigpipe-witness5.sh`, `logs/k-all.log`, the head's native kernel, 200 runs each in a
  `set -euo pipefail` subshell): trunk's line with GNU awk 5.4.1 died 23 times, each `status 141`; the fixed line 0;
  with mawk both 0.
- **Why mawk hides it** (`scripts/awk-hold-witness.sh`, `logs/awk-hold-witness.log`): a writer prints the match, waits
  2 s, prints one more line: mawk holds the matching record until more input comes (the pipeline ends after 2 s, status
  0); GNU awk acts at once and exits, and the writer's second line dies (status 141).
- **Why since px78** (`scripts/k-all.sh`, `logs/k-all.log`, the native kernels built as `tests/mpx6-disktools` builds
  them): at `f2aa9fd8` (last green) both symbols' lines fall in nm's last write (64 of 64), so no write can follow the
  reader's exit: GNU awk 0 of 100 died. At `56b9f554` (px78, first red) px78's new symbols moved them into the
  next-to-last write (65 of 66): GNU awk 25 of 100 died, mawk 0. The head's kernel has 56b9f554's layout (18 of 100).
  (`logs/sigpipe-witness3.log` is the same measure on the release-tier stick kernels, which this row never boots.)
- **Not witnessed**: which awk the GitHub runner runs, or why the race goes the reader's way there every time
  (3 of 3 reds: 40980361168, 40993542282, 41014032632). The fix does not depend on either.

**The fix** (`44fb33ea`): qemu-halt's three nm lookups (the halt routine's `nm -S` too, which was guarded but shares
the shape) keep the first match and read nm's output to its end (`&& !f { …; f = 1 }`, no `exit`), so nm never
writes into a closed pipe, whatever awk. **Green**: the row from the fix 3 of 3 with GNU awk and 1 of 1 with mawk
(`logs/ns-all.log`), `PASS I-noserial` each time. The same `nm | awk … exit` shape remains in the `sym()` helpers of
`tests/mpx2-interrupts`, `mpx2-paging`, `mpx2-sched`, `mpx3-loader` and `mpx3-user`, which run without `set -e`, so a
141 there changes no status and no value (listed below as owed, not changed here). pax#254 is to be closed by hand at
the merge.

## 5. Done-when

- [x] Item 1: the summary and `yes` (`ui.lu`, `plan.lu`); the token kept as the scripted path's and the log's record
  (said above); the non-interactive path `--install --ext2-preview --confirm TOKEN` kept and named.
- [x] Item 2: every row that typed the token or `ext2-preview` types `yes` (the ui unit, the guided rows,
  `metal.py`); new rows: `yes` installs, `y`, `YES`, `q`, empty and the old token each cancel with the target
  byte-identical (I-cancel-words), the summary names the allow-listed disk's model and serial (M3-summary); red first.
- [x] Item 3: `docs/INSTALL-METAL.md` step 4–5, the README's installer paragraph, `docs/BOOT.md` (the guided flow, the
  scripted path, the kasumi leg). `INSTALL.txt`'s source in the tree is px77c's record (`notes/px77c/staged-INSTALL.txt`),
  not this lane's to rewrite; the staged copy's stale lines are listed above.
- [x] Item 4: this note, one plant (`px78b-plant-y`), the PR, the audit.
- [x] The coordinator's stick: built, qualified on a copy, staged, six digest reads.
- [x] The addendum: pax#254 reproduced, its cause witnessed, fixed red-then-green (above). To close by hand at the
  merge: pax#254.
- [x] README read against the pass: its installer paragraph moved and is refreshed (`a6454777`, a README-only commit);
  nothing else in it moved.

Departures: the prediction after the change (§3); the plant's QEMU row red at the deadline rather than by name;
the leg for the stick through a lane-local variant of `metal.py` (diffless by construction: `make-variant.py` is the
diff); the test stick's merge commit kept local.

Issues filed or closed: none. Owed to file (pax):
- The `sym()` helpers of `tests/mpx2-{interrupts,paging,sched}` and `tests/mpx3-{loader,user}` keep the `nm | awk … exit`
  shape; harmless without `set -e` today, a 141 the day one of them gains it.
- `tests/mpx6-kasumi` still cannot be pointed at a given image with its line already written (px77c's owed item);
  this lane's `make-variant.py` is the second lane-local copy.
- The I-cancel-words row cannot fail fast: a word that installs leaves qemu-halt waiting for a prompt until its
  deadline; a per-row timeout or a guest-side stop on `CANCEL-EXIT-0` would name the row in seconds.
