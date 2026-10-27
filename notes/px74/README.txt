px74 USB keyboard evidence

Scope
  xHCI INTx; USB 2 boot keyboards and hubs; shared physical-key feed with
  PS/2; hotplug; software repeat. No USB storage driver, SuperSpeed class
  driver, MSI/MSI-X route, LED report, or claim of a metal boot.

Validated source
  final/final-validation.inputs records the five exact source hashes used
  by the detached final gate. The Mac worktree and pax-final snapshot were
  independently re-hashed and matched before commits d2a8eecd, 31a6449f and
  77b9cfb8. The marker final/final-validation.exit is 0. The log records
  all four compiler/firmware legs, three topologies each, and a native build
  of kmain_session. Each leg runs 16 invariants plus its completion marker;
  each topology originally ran 15 console rows including all 300 ring-wrap
  keys. The later arrow-validation gate reuses those exact kernel ELFs,
  recompiles the original C probe, and adds Shift+Down/Left/Right beside
  Shift+Up. All 12 PAX legs and Linux pass all 18 rows. The three new rows
  also have independent expected-byte assertions; they are not equality
  alone. final/arrow-validation.log and .exit record this gate; final/arrows/
  carries its transcripts. final/usb-cli.log proves a supplied --images
  directory cannot falsely count as both compiler tiers.

  final/usb/<native|release>/<bios|uefi>-<root|hub|nested>/serial.log
    Full transcript: controller ownership, ports, speeds, keyboard paths,
    SuperSpeed enumeration without a class driver, hotplug and input bytes.
  final/usb/.../rows.txt
    Normalized comparison against the Linux record. Only repeat count is
    normalized; repeat bytes/count/timestamps have separate strict checks.
  final/usb/.../repeat.txt
    First-repeat delay, median/mean period and count.
  final/console-sibling.log and .exit
    Native BIOS/UEFI baseline and USB root/hub console suites; exit 0.
    USB-path assertions require positive key counts and zero i8042 bytes.
  final/shell-sibling2.log and .exit: unchanged shell gate, baseline plus
    USB root/hub, native BIOS/UEFI; exit 0 after sibling references.
  final/pelt-typing.log and .exit: friendly console rows (framebuffer,
    serial and explicitly sized serial), baseline plus USB root/hub,
    native BIOS/UEFI; exit 0. Not a local claim about the full fork replay.
  final/usb-typing-mpx3-console/, usb-typing-mpx3-shell/, usb-typing-mpx5-pelt/
    Twenty independently checked USB keyboard transcripts, each with
    positive key counts, zero COM1 bytes and zero i8042 scancodes.
    Console and shell contribute eight each, pelt's framebuffer four.

Linux oracle
  linux.rows is the final 18-row reference; linux6/ preserves its raw log.
  linux5/ is the 15-row recording before all four Shift+arrows were explicit;
  linux3/ is the earlier corrected 14-row run, before adding ring wrap.
  Each corrected gate independently requires b in after-unplug and c in after-replug;
  equality between two broken transcripts cannot pass these rows.
  Linux kernel: 7.3.0-4-cachyos, binary only, SHA256
    bd5b90c3ba79ce78839b77a0f5b4f798738d62dbc06f8b1be3e0eaf83e1a92fe
  Original static probe, built on Ubuntu, SHA256
    94b14a009c92c3844c1a3bfb6f8fde990bd784ec06e72bb780fa30959f00ded6
  The recorded and final-validation 15-row probe binaries were re-hashed
  equal. The final 18-row probe SHA256 is
    2e1e065b7ca7da807b2763e87cc2532b39abc3c8e6cda1e2333b9eb6851f0e79.
  Its Linux first-repeat delay is 254.660ms, median period 34.004ms.

Repeat and latency
  Linux EVIOCGREP: delay 250ms, period 33ms (not 33 characters/second).
  Corrected runs: first-repeat delays 253.509 and 257.321ms; median periods
  33.984 and 34.002ms. PAX implements the configured 250/33ms values.
  Its 10ms clock carries the fractional period: 30/40ms intervals, not a
  fixed 30ms period. Example final mean 33.182ms, median 30.000ms, 24 keys.
  Tests require first delay 220..320ms, mean period 31..37ms, median
  20..45ms, at least 15 repeat bytes, all the correct byte, and one timestamp
  per byte. Timing tolerance is not permission to omit byte/path checks.
  First noncanonical USB key-to-read: zero ticks, at 10ms resolution; not a
  zero-time or host wall-clock latency claim. The report is in serial.log.

Plants (smallest CI suite: mpx6-usb, tier=pr)
  plant-route-ci.log: 75f992e5, run 40470752239, job 122077887897,
    FAIL USB hub route first port.
  plant-sixth-ci.log: c7ee72f9, run 40470754883, job 122077823787,
    FAIL USB boot report sixth key.
  Neither plant is merged into px74. Both branches remain on origin.

Host/reference separation
  kasumi block 12..15 is held under kasumi-cores-12-15.lock. Builds and QEMU
  run inside the existing rootless px80-ubuntu image (ID
    8ba042cb51b75ddc0c1c801a547144363c50844429e9df64ba6d15b8f0eff648).
  Linux references run in separate rootless sibling containers launched
  from the host through tools/linux-tree. No engine socket and no host PID
  namespace is exposed to the build or probe. The existing Python image ID
    a33c10a97f11005523814c6eee013986119fe41f3122f444518117536675c8e1
  has repo digest
    docker.io/library/python@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704.
  Local scripts remain under /home/mfwolffe/lanes/px74/: reference-engine,
  console-sibling.sh, shell-sibling.sh, pelt-typing.sh. No package installed.

Rejected experiments (preserved, not reference data)
  runs/typing1.log: missing PID-namespace privilege in the build container;
    no Linux records, not a kernel regression. Replaced by sibling records.
  runs/shell-build.log: the legacy --only build still attempted root Linux
    references; seven /dev bind failures only. All binaries/images built;
    every root/user reference must be regenerated in siblings before the
    unchanged --images gate is accepted.
  runs/usb-linux1.log and usb-linux2.log: HMP's held-key timer delayed b/c
    across hotplug rows on both guests. Replaced by explicit QMP key events
    plus independent required-byte assertions (linux3 onward).
  runs/usb-linux4.log: Linux dropped 6ms input pulses; the ring-wrap injector
    now waits 20ms per transition and independently requires all 300 bytes.
  Those runs live under /home/mfwolffe/lanes/px74; failed Linux row copies
  also live under /Users/mfwolffe/lanes/px74/evidence, not in linux.rows.

Metal caveat
  kasumi-xhci.txt is read-only inspection under Linux, not UEFI handoff.
  BAR0 0x485a200000, 64KiB; config 0x3c bytes ff 01 00 00; Linux reports
  MSI(X) IRQ133..140 and INTx disabled. This driver requires a usable legacy
  IRQ line. px76 owns MSI/MSI-X or ACPI interrupt routing before the target
  keyboard is called ready. QEMU success proves no real-board route.

Bounds
  Four controllers; 32 slots/controller; five hub hops; 31 hub ports;
  one boot keyboard interface/device; 1024-byte configuration descriptors;
  4KiB DMA pages below 4GiB; default single-TT hub interface. High-speed TT
  parent/inheritance fields are covered by the QEMU invariant kernel;
  QEMU's usb-hub exercises full-speed hub transport, not a real high-speed
  transaction translator. Failed/timed-out DMA is not recycled while owned.

Reproduction
  PAX_WOLF=$(tools/fetch-wolf) tests/mpx6-usb
  PAX_WOLF=$(tools/fetch-wolf) tests/mpx6-usb --tier native --firmware bios \
      --linux-kernel /path/to/a/binary/kernel/with/built-in/xhci-and-hid
  python3 -I tools/usb-typing mpx3-console --tier native --firmware both
  python3 -I tools/usb-typing mpx3-shell --tier native --firmware both
  python3 -I tools/usb-typing mpx5-pelt --tier native --firmware both
  The typing wrappers reuse each suite's built images and Linux records;
  build/reference prerequisites must succeed first. CI runs these wrappers
  after each original suite and uploads their separate USB path evidence.
