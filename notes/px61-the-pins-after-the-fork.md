# px61 — The pins after the fork

Implementation and rerun index for [pax#125](https://github.com/wolffe-lang/pax/pull/125).
The scored prediction, commit map and acceptance checklist live in that PR.
The original prediction is [px61/prediction.txt](px61/prediction.txt).

## Source and staging

- The four program revisions are in `user/pelt.pin`, `user/lope.pin`,
  `user/aspen.pin` and `user/boreutils.pin`. Each builder uses the
  program's own toolchain, not the kernel's toolchain.
- `user/std.pin` selects the source subtree installed at
  `/usr/share/wolf/std`. `tools/fetch-std OUTDIR` creates `OUTDIR/std`,
  `std.sha256` (every file, sorted by relative path), and `sums.txt`.
  `user/shrc` exports `LUPIN_STD` for the console and its children.
- `tools/mkpelt OUTDIR selfcheck` builds the same table-check program
  as pelt's `tools/self-check`, linked statically for PAX.

## Replay entry points

- `tests/mpx5-pelt`: pelt's fork corpus, interactive sessions, shape
  rows, probe scripts and table checks, root and `pax`.
  `user/console/fork/manifest.txt` names the upstream fixtures.
- `tests/mpx5-pelt.d/selftest.py` checks that missing output and a
  nonzero table-check result are rejected. `compare.py` retains each
  transcript and compares it after the existing job-pid normalization.
- `tests/mpx5-lope`: startup hook, autocd and stored-path jumps.
- `tests/mpx5-aspen`: listing and metadata options.
- `tests/mpx5-lupin`: the interpreter session and
  `user/lupin/std.lu`'s imports of `std.fs` and `std.str`.
- `tests/mpx3-boreutils`: the program run lists, root and `pax`.

The FIFO corpus row remains explicit, not silently skipped:
`builtin/c_s_dot_special_file` exercises PAX's refused FIFO creation
(pax#108, R-px61-1). The full root listing is also retained without
suppressing `/proc` (pax#113). R-px61-2 requires a fresh PAX boot per
replay group and role, matching the Linux references; the same bounds
and assertions apply. `PAX_PELT_CASES=corpus` selects that group for a
focused dispatch; an empty value runs every group.

## Rerun on kasumi

The scripts under `notes/px61/` use the lane's own directory and the
assigned four CPUs, 8–11. Compiles run in `px13-ubuntu`; the musl
interpreter uses the existing Rust image. The session recipes print
load and wait below 16 where the timing retake requires it.

- `run-suite.sh SUITE`: container build, live Linux reference, PAX.
- `guest-replay.sh`: the same inputs under a real Linux kernel, twice;
  `linux-vm.sh` and `notes/px52/vmjob.c` supply that guest method.
- `cost-and-std.sh`: both kernel entry points and compiler tiers, plus
  two independent std manifests.
- `census.sh` and `init-cost.sh`: syscall names, fork flags and the
  guarded init's process-launch cost. Hook source is not published.
- `playground-build.sh`, `playground-assemble.sh` and
  `playground-boot.sh`: lane-local copies of the playground recipes,
  then the keys in `playground.keys`. The shared recipes are not edited.

Long jobs use `setsid -f` and a PID file. Keep the first bundled replay
logs when rerunning the partitioned harness; they are distinct inputs,
not replacements for the fresh-boot records.

## Raw evidence

The adjacent `px61/` directory holds the raw build sums, std manifest,
section tables, syscall census, interpreter and tool sessions, planner
checks and both CI plant logs. The complete 47-program static manifest
is `boreutils-static.sums`; the std tree's is `std.sha256`.

`ci-39796594629-plant-first.log` is the first old-pin attempt, which
stopped in the Linux FIFO fixture. `ci-39801704202-plant-fork.log` is
the focused semantic witness. Keep both: the first attempt is not a
substitute for the second assertion.
