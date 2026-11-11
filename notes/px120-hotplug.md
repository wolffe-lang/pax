# px120 — a USB device plugged in after boot gets a record (pax#348)

On a desktop with two xHCI controllers, a mouse plugged in after boot never arrived, and the console filled with
`xhci 1: no device record memory <hex>`, the number counting up, a line every fraction of a second. A pointer present
at boot worked. Now a device plugged in after boot is taken however long the system has run, on any controller:
mice, keyboards and composite devices (the reporter's is a gaming mouse: a boot mouse with keyboard and vendor
interfaces beside it); each unplug gives its record and slot back, so plugging and unplugging never runs out; and a
device that cannot be taken is named on one line a plug, never a stream.

Footprint: cross-cutting (`kernel/frames` is the kernel's core: every suite on one leg; `kernel/xhci`,
`kernel/kmain_frames.lu`; `tests/mpx2-frames`, `tests/mpx6-usb` and its `build-once.py`, new
`tests/mpx6-usb.d/hotplug-judge-selftest`, `tools/hotplug-session`, `user/elf/hotplugprobe.c`; `tools/ci-tiers.map`,
`tests/ci-plan`).

## 1. Forbidden, and what was read

- **The clean room.** No kernel's, firmware's, USB stack's, device model's or driver's source was read: not Linux's,
  not any BSD's, not QEMU's, not the usbredir library's, not any vendor's. The fix is written from xHCI 1.2, USB 2.0
  and PAX's own allocator. The test devices are written from USB 2.0, HID 1.11 and the USB redirection protocol's own
  description (its document only), which is how this lane's session plays a composite device to QEMU's `usb-redir`.
  QEMU was measured as a black box. `docs/SOURCES.md` (px120) lists every source with its digest.
- **Hosts.** A Linux build host (20 threads, 46 GB) for every build and boot, in an Ubuntu 24.04 container (QEMU
  8.2.2, OVMF, gcc 13.3, clang, lld 18) with KVM: smoke runs and the red and plant takes on two CPUs, the green
  take on a block of six. The real machine was never touched.
- **Not done:** no label, merge, tag, release or deploy; no issue filed or closed; no attribution trailer.

## 2. The cause, reproduced

**Reproduced on the first try** (the reproduction's logs, §5): the console kernel at pax#346's head, under QEMU,
on a q35 with 1536 MiB, 512 MiB of it below 4 GiB (`-machine max-ram-below-4g=512M`), two controllers, a usb-mouse
on the second at boot. A probe takes, touches and gives back 700 MiB; then a usb-mouse is plugged into controller 1 with
QMP's `device_add`. It never arrives, and in 6.5 s the log has 28 lines of `xhci 1: no device record memory
0x0000000000000001`. The mouse present at boot is pointer 1, as on the reporter's machine.

**Why no record can be had.** `kernel/xhci`'s `page` took `frames.alloc()`'s frame and, finding it at or above 4 GiB
(the driver keeps every DMA page low, for controllers that cannot address more), gave it back and answered 0.
kernel/frames is next-fit: `alloc` scans from a hint, the word it last took a frame from, and the hint only moves on,
wrapping at the top of memory. Freed frames behind it are not looked at again until it wraps. So once the kernel has
handed out more frames than lie below 4 GiB, counting every frame ever taken (the initramfs's tree, every program
loaded, every fork's copies, all of it freed or not), the hint is above 4 GiB and stays there; and since freeing the
refused frame does not move the hint, the next `alloc` returns the same frame, and `page` refuses it again, forever,
while hundreds of MiB below 4 GiB are free. The first `page` of an attach is the device record: reason 3, `no device
record memory`. The record of a device present at boot was taken during the boot, before the hint passed 4 GiB:
`/dev/mouse0` exists. CI never saw it: its machines have 256 MiB, all below 4 GiB. A desktop has gigabytes above.

**Why without end, and why the number counts.** An attach that fails before its record is made leaves nothing at the
port, so the enumeration thread, every 100 ms, finds a connected port with no device, debounces, resets the port and
attaches again, and says so again: about four lines a second under QEMU. The number is the slot Enable Slot gave
(the record's page is asked for after it, and the slot disabled again). QEMU's controllers give the lowest free slot,
so under QEMU the number stays 1 (0x1f on the session's second controller, whose first 30 are taken). xHCI lets a
controller choose any free slot; the reporter's evidently gives the next one each time, so the number counts up.
That last step is inferred from the report, not reproduced: no QEMU controller numbers slots so.

**The same on the hardware, from the code alone.** Reason 3 has one cause: `page` answering 0 for the record, which
with free memory happens only for a frame at or above 4 GiB. A desktop with more memory than lies below 4 GiB passes
the hint over 4 GiB after a boot and some use. The device does not matter: a plain mouse is refused the same way.

**The confirmation the machine can give now, without the fix.** `low4g` (px77d's triage word, with `triage`) keeps
every frame below 4 GiB. On the unfixed kernel, under the same QEMU machine and the same churn (350 MiB three times):
without it, 20 lines of `no device record memory` and no mouse; with `triage nodraw fullh low4g` on the command line,
the mouse attaches (§5: `run-plain`, `run-low4g`). See §6.

## 3. The fix

- **`frames.alloc_below(limit)`** hands out the lowest free frame below a physical address, scanning the free bitmap
  from frame 0, and leaves `alloc`'s hint where it is (O(limit / 64) word reads at worst: 16,384 for 4 GiB). Row
  `out_of_memory` when nothing below the limit is free. `tests/mpx2-frames`' F9: with every frame free and the hint at
  the top, `alloc_below` under `alloc`'s frame gives the lowest free frame, none is free below it nor below 1 MiB, and
  `alloc`'s next frame is the one it would have given without the call.
- **`kernel/xhci`'s `page`** asks `alloc_below(4 GiB)`. The policy (every page the controllers see below 4 GiB, for
  controllers without 64-bit addressing) is px74's, unchanged; only the way the page is asked for changed.
- **One line a port change.** A device that cannot be taken marks its port: a byte a root port in the controller's
  page (from byte 2048), a bit a hub port in the hub's record (word 368). A marked port is not tried again until the
  port reads empty or its connect change bit is set (PORTSC's CSC; a hub's C_PORT_CONNECTION), which a replug sets.
  So a refusal costs one line a plug. A refused device is not retried when a slot frees elsewhere: its port did not
  change (decision D3).
- **A slot past the enabled ones goes back.** QEMU's controllers answer Enable Slot with slots past CONFIG's
  MaxSlotsEn (measured: 33 and 34 with 32 enabled). PAX refused such a slot but kept it enabled on the controller, so
  each retry would have taken another; it is disabled again now.
- **Unplug already gave the record back** (Disable Slot, then every page of the record; kernel/mouse frees the
  pointer's entry and numbers on), and still does: the session's loops prove it past the 32 records a controller keeps.

## 4. The rows

`tests/mpx6-usb --topology hotplug` (run last in `all`, so CI's USB job runs it on every leg) drives
`tools/hotplug-session` over `user/elf/hotplugprobe.c`. The machine: 1536 MiB, 512 MiB below 4 GiB; controller 1 a
qemu-xhci (INTx) with nothing on it at boot, as the reporter's; controller 2 a nec-usb-xhci (MSI) with a usb-mouse,
four usb-hubs and 25 usb-ccid readers at boot: 30 of its 32 records. The probe churns 800 MiB first, then every plug
is made through QMP. Two composite HID devices are played by the session itself over `usb-redir` at full speed:
COMPOSITE_MOUSE (interface 0 a boot mouse with 5 buttons, 16-bit X and Y and a wheel; 1 a boot keyboard; 2
vendor-defined, the reporter's shape) and COMPOSITE_KEYBOARD (0 a boot keyboard; 1 subclass 0 with consumer keys and
an all-keys bitmap, no pointer; 2 vendor-defined).

| row | what | at the rows' tip (no fix) |
|---|---|---|
| churn, boot-pointer | the probe gave its memory back; controller 2's mouse at boot is pointer 1 | PASS |
| c1-mouse | a usb-mouse on controller 1: one pointer, its NEW record, a move only it made | FAIL: no pointer, 26 `no device record memory` lines |
| c1-keyboard | a usb-kbd: its line, the keys typed on it | FAIL |
| c1-composite-mouse | COMPOSITE_MOUSE: keyboard and pointer at full speed, its move, its key | FAIL |
| c1-composite-keyboard | COMPOSITE_KEYBOARD: the keyboard, its key; its HID interface refused as a pointer once by name | FAIL |
| c1-loop | the mouse unplugged, then plugged and unplugged 40 times, then plugged: 41 and 41, a new pointer each | FAIL |
| c1-composite-loop | COMPOSITE_MOUSE disconnected and connected 10 times: both interfaces each time | FAIL |
| c2-hub-mouse | a usb-mouse behind controller 2's hub (its 31st record) | FAIL |
| c2-composite-mouse | COMPOSITE_MOUSE on controller 2 (its 32nd) | FAIL |
| c2-refused-once | two usb-mice past the 32 (a hub port, a root port), held 3 s: one line each | FAIL: 20 lines |
| c2-free-hold | a record freed (the composite disconnected), held 3 s: the refused are not tried again | FAIL |
| c2-replug-taken | the root port's mouse unplugged and plugged: taken | FAIL |
| c2-loop | it unplugged and plugged 40 times at the full 32 | FAIL |
| no-stream | the whole log: the two lines of c2-refused-once, none about memory, one pointer refusal | FAIL: 564 lines |
| keyboard-path | every key came over USB (PAX's summary: 0 scancodes) | FAIL: the probe never ended |

`tests/mpx6-usb.d/hotplug-judge-selftest` shows the judge can say no by name, from transcripts in the shape of each
failure (H1 to H9: pax#348's stream, a retry on every pass, a retry when a record frees, a loop that runs out, a
composite's keyboard not driven, a refusal said twice, keys through PS/2, a pointer number back).

Under `PAX_USB_IRQ` (the firmware suite's MSI and INTx legs) the hot-plug session is not run again: it sets its own
two controllers, one on each.

## 5. Evidence index

Every take ran on the build host in the container, by the recorder in steps mode (`notes/px120/rig`: `take.sh`,
`step.sh`, a manifest each) from a clean worktree of the commit named. Records are kept beside the lane; their END
lines are below and in the PR.

| record | sha256 | what |
|---|---|---|
| `rows-26ffd255.log` (`short.manifest`) | `43f444f9…594fa6` | red at the rows' tip `26ffd255` (the rows and the rig, no kernel change): `END ci-plan exit=0`, `END build-once exit=0`, `END hotplug exit=1`, its 14 rows FAIL by name at column 0 (§4's table), 564 `no device record memory` lines |
| `plant-below-c0c5cebb.log` (`plant.manifest`) | `f8c117a2…30c14c` | plant `px120-plant-below`, one line over the head: `alloc_below` scans from `alloc`'s hint. `END hotplug exit=1` (every plug row FAIL, `no-stream` with 9 memory lines: the marks hold it to one a plug), `END frames exit=1` (`FAIL F9 …: alloc_below 0x0000000000000000`) |
| `plant-retry-4bc53106.log` (`plant.manifest`) | `19573d59…127281` | plant `px120-plant-retry`, one word over the head: a refused port is never marked. `END hotplug exit=1` (`FAIL c2-refused-once`: 17 lines in 3 s; `c2-free-hold`, `c2-replug-taken`, `c2-loop`, `no-stream`: 57 lines), `END frames exit=0` |
| `gauntlet-7efaacda.log` (`gauntlet.manifest`) | (pending) | green at the head `7efaacda`: the planner's test, build-once and the judge's selftest, `tests/mpx6-usb` on both tiers and firmwares, the hot-plug session under TCG, `tests/mpx2-frames` on both tiers and firmwares, `tests/mpx6-pointer` and `tests/mpx3-console` native BIOS. Queued on a block when this was written; its END lines follow here and in the PR |
| reproduction (`run-a`, `run-plain`, `run-low4g`, serial logs) | `6bbffa62…`, `43e83bba…`, `97c00c2b…` | §2: the console kernel at `309036ec`; 28 lines in 6.5 s; the same churn without and with `triage nodraw fullh low4g` |

Full digests: `rows-26ffd255.log` 43f444f9157e875d367c46bcd5879102c7db283b56b26dcb6041861595594fa6;
`plant-below-c0c5cebb.log` f8c117a26cacb25a27a803f721ab9d6fa72fcd60a2ecfa7af1ef600d5530c14c;
`plant-retry-4bc53106.log` 19573d596b163a3ad2a86fadc8f3d0cc79f6554cd6d32e99bd82736699127281;
`run-a.serial.log` 6bbffa6294c17b51d7312c1b64082527942cd2b3508e49cc0f0c1ef54d2148a9;
`run-plain.serial.log` 43e83bba5ad13a6c3e9a996a5b31bb8eef7cd08a3109b1b4643df8f7ab51bc77;
`run-low4g.serial.log` 97c00c2b3d8057bb8af93d93a02b8df7e36dd1f65c6186d79c755ab8beb06db8.

Smoke runs before the records (not evidence, named for the order of things): the session at the fix's tip on native
BIOS (16 of 16) and at the head on native UEFI (16 of 16); `tests/mpx2-frames` native BIOS with F9 (PASS).

## 6. For the person at the machine

**Now, on the kernel you have** (confirms the cause, no new build): boot the live stick, and in Limine's menu (it
waits five seconds) open the PAX entry's editor (E on the highlighted entry), add `triage nodraw fullh low4g` to its
`cmdline:` line and boot it; or boot a triage stick (`boot/limine-triage.conf`) at its entry "PAX triage low4g".
Log in, plug the mouse in. Expected: one line `xhci: mouse usb1-<port> speed <s> interface 0 ...; pointer <n>`
(and, for its keyboard interface, `xhci: keyboard usb1-<port> ...`) and no `no device record memory`. `low4g` hands
out no memory above 4 GiB, so it costs that memory: it is a witness, not the fix.

**With the fix:**

1. Boot normally, log in, use the machine a while, then plug the mouse in. Expected, on the console: the lines
   above, once; never `xhci N: no device record memory`.
2. Move it and click: `head -c 320 /dev/mouse0 | od -A d -t x1` prints ten records (`notes/px109-the-mouse.md` §5.4
   reads them); byte 12 is the pointer number the line named.
3. Unplug it: `xhci: mouse usb1-<port> removed; pointer <n> gone`. Plug it back: a new pointer number. Ten times over
   is fine.
4. Anything still refused prints one `xhci <controller>: <why> <hex>` line a plug and stays quiet until it is
   replugged. The line, the device and the port are what a fix needs; with `usbraw` on the command line the
   device's descriptors are logged too.

## 7. Decisions (the lane's, each open to review)

- **D1, the composite devices' source.** The session plays them over QEMU's `usb-redir`, written from the USB
  redirection protocol's document (a protocol description, not code; listed in `docs/SOURCES.md` with its digest).
  QEMU has no composite HID device of its own. The alternative is no composite row under QEMU.
- **D2, low pages kept.** Every xHCI page stays below 4 GiB, as px74 chose, now asked for as such. A controller with
  64-bit addressing could take any frame; that is a wider change and not needed for the fix.
- **D3, a refusal waits for its port.** A refused device is tried again only when its port changes, not when a slot
  frees elsewhere: one line a plug, as asked. Replugging it takes it.
- **D4, slots past MaxSlotsEn given back.** Measured on QEMU; harmless on a controller that keeps to MaxSlotsEn.
- **D5, the session's cost.** About a minute a leg under KVM (52 to 59 s measured on two CPUs: 30 devices
  enumerated at boot, two 40-plug loops). CI's USB job has run 17 to 19 minutes on four legs against its 30-minute
  limit; the session adds about 4. The limit is left as it is.

## 8. Bounds, and what is not done

- The counting slot number of the report is inferred, not reproduced (§2).
- A hub whose own port requests fail is still asked again on every pass, with a line each time (a hub's
  `GET_STATUS` failing by STALL; not seen in any test, and not this report's path).
- "One line" is one line of the attach's own: a device whose enumeration fails part way (reason 5, its record kept
  until it is unplugged, as before) also says the control transfer that failed, so two lines a plug; still never
  more until it is replugged.
- USB mass storage keeps its record after an unplug (px78: kernel/usb_storage names it) and four storage devices a
  boot remain the bound.
