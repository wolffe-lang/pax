# px81 — pin friendly pelt and prove both consoles (pax#201, merged at 6e1623a1)

Materialised on trunk from the PR body by the orchestrator at the merge (a Codex lane writes no note file).

# Note
The lane wrapper prohibits report `.md` files; this is the complete note fallback. Evidence is tracked under `notes/px81/`.

## Prediction
Committed before implementation in `60ffbece`. Expected all five feature groups on the framebuffer; expected the history shadow alone to fail on serial at0x0. Framebuffer prediction5/5; serial prediction4/5: all five actually worked even at0x0. Direct TIOCGWINSZ measured50x160 on the framebuffer,0x0 on serial and24x80 after the explicitly typed `stty cols 80 rows 24`.

Exact opt-in command: `set -o friendly -o suggest -o histsearch`.
Default suggestions are SGR90 and resolving commands the default foreground. The contract's dim/green default premise was incorrect. A separate capture types `PELT_COLORS='command=green:shadow=brblack+dim'`; no shipped default changed.

## Forbidden
No third-party kernel, libc, shell, grep, filesystem-tool, bootloader or installer implementation source read. Pelt was built unmodified by `tools/mkpelt`, never read for design. Consulted pinned pelt documentation and typed test inputs/expectations, PAX's own code and px70 console rows. No Mac builds/boots/tests, package installation, pool-service changes, or writes to the existing playground disk/ISO. All execution on kasumi cores8–11. No issues filed/closed, merge, label, or attribution trailers.

## Inputs verified
- `PELT_REV=0b5eaa5394667c485de3a134f771c87024b68a3c`, launch trunk read twice.
- Pelt's own wolf0.2.35 / std2386522eb059cca5a84108562c2c0a0e72345d34. Wolf archive SHA256 `4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a`, read twice.
- Static pelt SHA256 `25ed3ef933731d44fcbdda4b9b549252e34d18288a2f7795cde177d2b841e127`,16,125,424bytes, read twice.
- Native console kernel SHA256 `b5dad1da4315dc671ae6ce92b397f1dfe13506623eed9ece03f9d07d4a5954af`, read twice. Rebased onto px71 merge88836816; no kernel/build-input change in that rebase.
- Existing baseline container `localhost/px80-ubuntu`. Unchanged px71 installer/account fixture binaries copied read-only into px81, not rebuilt on host glibc; new pelt replaces their shell.
- Dev base ISO SHA256 `893ae1b90446a05e8e4d607d56a7eca956d15f8848d7495ce433e798041a50de`, source read twice, before/after copy equality and copy read twice. Repack replaces only bin/sh, bin/pelt, etc/motd; all other payload bytes and metadata retained. Kernel replaced separately in ISO.

## Evidence index
Implementation and evidence chunks:
- `d52a54f1`: pin and census C4 identity gate.
- `08d21983`, `5dbf7127`, `e1185dab`, `211ef16e`: typed console row, direct size witness, framebuffer reference, independent reruns.
- `455aa25d`: retain friendly CI captures.
- `b1f29f8a`: README refresh.
- `534743c4`, `77e26ae9`, `49cb95ad`: verified dev repack and both-firmware smoke.
- `2310bb99`, `55f43d35`, `1a52c4b7`: measured console, installer, ISO, replay and account/gate evidence.

- `notes/px81/upstream/`: pinned pelt keys, transcript and screen expectations for Alt-dot, suggestions, colours, Space abbreviation, previous-command/last-word events.
- `notes/px81/final/mpx5-pelt-friendly-native-{bios,uefi}-{framebuffer,serial-zero,serial-sized}/`: raw `serial.log`, actual keys, checks and halt records. PS/2 captures include input logs and screenshot offsets.
- Framebuffer checks:7/7 screenshots and56,000/56,000 cells equal the established screen reference, on each firmware. Screenshots retained on kasumi in the corresponding `/home/mfwolffe/lanes/px81/build/` directories.
- All six short-line sessions pass default SGR90 shadow, custom SGR2 dim, default command foreground, custom green resolving command, bad command/open quote red, abbreviation execution, !!/!$/Alt-dot output, dimensions and clean pid1 exit.
- `notes/px81/first-pass/`: preserved first-run evidence. Only initial-size check failed on serial: BusyBox stty prints a diagnostic for zero size instead of numeric dimensions. A direct public-ABI ioctl witness fixed the measurement, not the kernel or pelt.
- `notes/px81/installer-smoke.log`: installer policy/UI/snapshot/executor/prepare, inventory, games no/vdb and yes/vdc, installed typed sessions, and named fault refusals;0 SKIP.
- `notes/px81/linux-first/`: first Linux replay failure. It waited for prompt24 BEFORE typing substitution-pipeline. Actual last typed step23 starts eight background `true` jobs and then `wait`; no SHAPE:true-background:8 appeared. Root shapes completed. The one permitted complete repeat passed, root and pax: one failure in two runs, tracked as pax#196. The step23 background-builtins/wait shape is the pelt-track candidate, not the untyped substitution-pipeline step24. No pelt implementation changed here.
- Plant draft#198, head289212d327321cca24d4199fac5d1b71a5269356, dispatch40229694635, PR-trigger40229683964. Observed by the orchestrator in failed-step logs of BOTH runs, job `census`:
  `C4 FAIL pelt image pin differs from launch-trunk census: https://github.com/wolffe-lang/pelt 70eec1437d04859504cae3d1382c7b51292cf2eb != https://github.com/wolffe-lang/pelt 0b5eaa5394667c485de3a134f771c87024b68a3c`.
  Left open for the orchestrator; no closure claimed. C4 compares image pin with the recorded launch-tree census, never a moving live upstream head.

R-px81-1 recommendationA implemented: serial stays0x0 until explicitly set; no fixed fabricated size. R-px81-2 opt-in/defaults unchanged. R-px81-3A accepted: preserve actual default palette and show requested custom palette separately. README read and refreshed for the new pin and friendly commands.

### Delivered ISO
- Kasumi: `/home/mfwolffe/lanes/px81/dev-iso/pax-dev-pelt-friendly.iso`
- Nomad: `/Users/mfwolffe/pax-playground/pax-dev-pelt-friendly.iso`
- SHA256 `a831d0253149a76f05565b8b70f61b6287c11a366d72a5eec92cfede3227f0d5`, read twice on each host.
- Stripped pelt in the ISO: SHA256 `d54a3f756f75e3b7ece1626c92024332a7838074bdb089f989201323701001c9`, read twice. Unstripped suite binary remains the digest above.
- Both BIOS and UEFI assert pelt pid1, friendly colour bytes and clean halt. Manifest proves exactly three cpio entries changed; kernel replaced separately. Layout discovery corrected the initramfs path to `/boot/initramfs.cpio`; first build failure is not disguised as a boot failure.

Three-line BIOS recipe (no playground disk attached):
```sh
cd ~/pax-playground
qemu-system-x86_64 -machine q35 -cpu max -m 2048M -nic none \
  -cdrom pax-dev-pelt-friendly.iso -serial mon:stdio
```
Type the opt-in command above. For UEFI add `-drive if=pflash,format=raw,unit=0,readonly=on,file=/opt/homebrew/share/qemu/edk2-x86_64-code.fd`. Complete recipe and digest record: `notes/px81/dev-iso/boot-nomad.txt`. No Mac boot was run by this lane.

### CI wording follow-up
Run40234163533 exposed two stale expectations after the pelt pin bump. The actual failure lines, measurements, negative checks and normalized recording diffs are retained under `notes/px81/wording/`.
- `7968750d`: scent A2 now requires the exact observed interactive refusal: `pelt: line 50: $'\377': a byte that is not UTF-8 cannot be carried yet (pelt#65)`. Fresh root and uid1000 container sessions prove status2, no command invocation, and shell continuation. This replaces old question-mark substitution, not a missing diagnostic. All49 rows remain; both CI PAX transcripts pass, and missing refusal/old substitution/wrong line number remain red. The independent #! byte-FF/runtime-abort row is unchanged.
- `08e1957d`: README describes that explicit refusal.
- `464384e0`: xsh root and user goldens were re-recorded, not text-substituted, from the pinned shell on real Linux root in QEMU using px52's vmjob and px48's recording recipe. Two takes of each role are byte-identical. The live container user and fresh native-BIOS PAX root/user sessions equal the new recordings. Exactly one normalized line changes in each: `pelt: line 15: ./nx.sh: cannot be run` becomes `pelt: line 15: ./nx.sh: Permission denied`; status126 and every other normalized byte remain unchanged.
- `a5c9f3db`: measured evidence, reproduction commands and negative witnesses. See `notes/px81/wording/verdict.txt`, `xsh.diff`, `xsh-user.diff`, `refusal-interactive.log` and `scent-check-final.log`.
No pelt implementation or binary, kernel or delivered ISO changed. No additional issue filing is needed for these measured diagnostic changes.

### Remaining merge checks
Final head: `a5c9f3db5e49cee666fcaa0092bc8e0d4a3f74bb`.
Local full PAX replay completed with exit0; the lane read the complete396-line log at `/home/mfwolffe/lanes/px81/runs/replay-pax.log` and marker `/home/mfwolffe/lanes/px81/runs/replay-pax.exit`. Native BIOS and UEFI each pass26 static replay boots (13 case groups as root and pax),52 static boots total, with140 byte-identical F1 comparisons including88 corpus parity rows (22 × two roles × two firmwares). The same run passes six friendly console sessions with74 F4 assertions, plus14/14 framebuffer screenshots and112,000/112,000 reference cells. Total58 boots;0 FAIL and0 SKIP lines. Final verdict: `mpx5-pelt: mpx5-pelt: PASS`. The full replay passed before this expectation-only follow-up; the fresh focused wording witnesses above cover the changed expectations.

`notes/px81/accounts.log`: A0–A4 pass for both firmware legs and both input paths. `notes/px81/quick-gates.log`: censusC1–C4, CI planner, negative comparator tests, shell syntax pass. Planner selects `tier pr`,50 suites on native BIOS, including `mpx5-accounts`, `mpx5-users`, `mpx5-pelt`, `mpx6-install`; only accounts among the first two types into pelt. The broader users suite is a CI obligation, not a claimed local run.

The serial measurements cover the short typed fixtures, not arbitrary host widths or long-line wrapping. F5's serial size probe is still unimplemented.

Pruned own transient Python bytecode, superseded remote transport bundles resume.bundle/resume2.bundle/resume3.bundle, and the two clean, pushed Mac worktrees `/Users/mfwolffe/lanes/px81/pax` and `/Users/mfwolffe/lanes/px81/plant` (explicit non-force removals). Build trees from the completed replay are retained for review; no other lane's data was pruned. Issues to file/close: no new filing requested; add the exact step23 first-take observation to pax#196. No issue closure claimed.

## Done-when
- [x] Launch pin and built inputs read twice; source/census updated
- [x] Six friendly console/firmware sessions; raw bytes and framebuffer reference checks
- [x] Installer smoke regression,0 SKIP
- [x] Assertion selftests include wrong-style/missing-output/size/exit counterexamples
- [x] Linux complete static replay repeat passes (first take failed as recorded, pax#196)
- [x] Full native BIOS+UEFI PAX replay exit0:52 static boots,140 F1 comparisons, six friendly sessions/74 F4 assertions,14 framebuffer screenshots;0 FAIL/0 SKIP. Log: `/home/mfwolffe/lanes/px81/runs/replay-pax.log`
- [x] Account regression: Linux plus native BIOS/UEFI, serial and PS/2; final lightweight gates pass
- [x] New dev ISO both-firmware boot, unique nomad copy, final digest read twice on both hosts
- [x] Wording-fix head pushed; immediate new-head run-list read returned no row. Mandatory new-head audit subsequently observed run40240014793 pending at a5c9f3db; no CI wait/poll.
- [x] lane-audit rerun at the wording-fix head; last line `AUDIT FAIL (footprint: cross-cutting)`. Only pending CI/tier-green checks fail; full-matrix label and all other checks pass.
- [ ] Audit's CI/tier gates clear before merge
- [ ] Orchestrator-owned CI/full-matrix gate before merge

Current audit evidence: `/Users/mfwolffe/lanes/px81/audit-wording.log` (exit1); original-head audit retained at `/Users/mfwolffe/lanes/px81/audit.log`. Command from the org root: `bash wolf/tools/lane-audit.sh pax px81 201`. The audit's default worktree probe is `/private/tmp/px81`; the actual two Mac worktrees were also explicitly removed before it ran. Current remote checkout and active replay fixtures remain under `/home/mfwolffe/lanes/px81/`.


