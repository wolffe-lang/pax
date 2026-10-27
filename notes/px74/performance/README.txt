px74 release-build correction (wolf-lang#983 context)

Scope
  Address only mpx6-usb's 30-minute timeout. Do not change its timeout,
  compiler optimization flags, kernel pin, USB rows, or the unrelated
  mpx5-jobs/mpx2-heap/mpx5-pelt failures.

Cold release object builds, seconds
  Command in each time.json: wolf build ENTRY --no-cache --release
    --target x86_64-unknown-none --emit=obj -o ...
  Same pinned wolf 0.2.35, Ubuntu container, kasumi taskset 12-15 (4 CPUs),
  12GiB cap, core-block lock. WOLF_CLANG only copies the emitted IR shards
  before executing /usr/bin/clang with unchanged arguments.

  trunk invariant control      165.148
  old invariant kernel         321.787
  final isolated invariants      0.920
  trunk console                227.117
  reshaped console             210.332

  The console is back near trunk (0.93x in this pair); this is not a
  statistically established speedup over trunk. The invariant reduction
  is structural: 31 emitted functions instead of 1068, not weaker tests.
  The old invariant entry imported the whole OS through xHCI/interrupts.
  The final entry uses exactly the same HID and topology helpers as the
  driver, with fail-closed assembly-roster veneers and interrupts disabled.
  All sixteen assertions and all four invariant boots remain.

Control definition
  Trunk 187aafdf has no kmain_usbcheck. The control adds only the identical
  invariant entry and its pure HID/topology helpers to that tree; it keeps
  trunk's real interrupt dispatcher. The three added files are preserved
  under trunk-control/kernel/. No tracked trunk source was changed.
  The trunk-console measurement uses trunk's actual kmain_console entry.

IR evidence
  Every census.csv lists each emitted function's basic blocks, natural-loop
  headers, backedges, total branch instructions, conditional branches and
  instructions. The optional proxy is loops * conditional_branches^2, not
  an internal compiler timing measurement. Natural loops are found with
  dominators, not by treating label numbering as control flow.
  Object emission invokes clang on multiple shards: all shards are captured
  with distinct filenames. Definitions are unique across the recorded
  shards. before-console.csv comes from the previously validated 4bc5a08e
  console's complete --emit=llvm-ir output, on the same compiler.

  Comparable console functions (loops / conditional branches):
                          before          after
    attach setup          49 / 249        4 / 87 (try_attach)
    control               20 / 97         9 / 65
    root_scan              4 / 66        13 / 101
    hub_scan               3 / 54        12 / 89
    configure             18 / 216       18 / 216
    HID report             9 / 104        9 / 104
    controller            75 / 437       75 / 433

  Diagnostics were not removed: setup returns the failure tag/detail to
  one formatting site, which is inlined into the two smaller port scanners.
  Control completion/timeout likewise share one formatting site. Descriptor
  parsing, hub traversal and report decoding keep their algorithms.
  Unrelated code can change shape with the import/inlining graph: e.g.
  block.table_report is 135 loops/756 conditional branches in the trunk
  invariant control but 250/982 in the old USB invariant entry, despite no
  block source change. The full per-function files retain that evidence.

No redundant builds; no missing boots
  tests/mpx6-usbcheck now accepts a cached invariant image with a checked
  compiler-tier marker. The matrix bundles both invariant and console
  images, then reuses both for UEFI. Each kernel has one build-kernel call
  per compiler tier; build-kernel's object/IR/no-SSE checks remain intact.
  The full OS release kernel is consequently built once, not once for each
  invariant/typing phase. The tiny invariant kernel is a separate build.

  build-once-before.log: the new guard rejected the old six-build matrix.
  build-once-final.log: four builds, four invariant boots, twelve DISTINCT
  compiler/firmware/topology sessions; wrong-tier cache and build-failure
  propagation checks also pass.
  plant-rebuild-ci.log: commit 9026ca23, run 40518531386,
  job 122239294053, step 'USB matrix builds once without dropping boots'
  failed on the six-versus-four build assertion. This is an additional
  performance-regression plant; the original two USB plants remain.

Fresh functional gate
  perf-matrix.exit = 0. perf-matrix.log records the full updated matrix:
  native/release x BIOS/UEFI x root/hub/nested, all 18 byte rows, software
  repeat, hotplug, ring wrap and the undriven SuperSpeed witness. No row
  skipped. It includes the pure kernel's four boots and the CI planner.
  Entire step on kasumi: 814 seconds (13m34s), including the cold final
  invariant timing and planner. matrix/ preserves all hardware transcripts.
  Prior console/shell/pelt typing evidence remains at the earlier head;
  CI reruns those suites at the new head. This correction did not chase
  the unrelated cancelled/flaky rows assigned to px83.

Reproduction/data
  ir-census.py, time-build.py and capture-clang are beside this file.
  Remote immutable trees/results: /home/mfwolffe/lanes/px74/perf/.
  Raw IR shards remain in each measured result's ir/ directory; only
  censuses and timing JSON are committed to avoid vendoring megabytes of IR.
  The initial capture wrapper used one filename and raced parallel clang
  shards; that failed measurement is excluded. Its original failed log and
  exit remain remotely under perf/before-result; it was not a compiler bug.
