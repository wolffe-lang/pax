# px73 — the USB stick

_Materialised from the body of pax#218 at the merge (`c4d2b3c0`)._

## Forbidden

No third-party bootloader, firmware, kernel, driver or disk-tool implementation source read; PAX's own sources were read. No kernel-driver edits, physical-device writes, installed-account changes, pin changes, labels or merges. Specifications and black-box inputs are cited in docs/SOURCES.md. Planning and home configuration remain untouched.

## Inputs, verified

Base `187aafdf`; kernel source unchanged. Wolf 0.2.35 archive SHA256 4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a and Limine 12.9.1 archive SHA256 5cdebc518daa3af30b22c2322ba0dba2e0e2046fa8b087b9e13071b8dbcdcff4 read twice on kasumi. Kernel ELF SHA256 0487a8e9d65f66caa359ea0bb14a82b953af65f480bb59e9def8c297f36f0766. QEMU 11.1.2, Linux 7.3.0-4-cachyos; Ubuntu-baseline build container 8ba042cb51b75ddc0c1c801a547144363c50844429e9df64ba6d15b8f0eff648. Assigned cores 0–3 under flock.

- `d34914b5` — commit predictions before implementation.
- `7d1e4a7a` — USB-only QEMU topology and launcher tests.
- `ac594ca5` — reproducible raw GPT stick and independent validator.
- `a8caeec6` — guarded manual writer; Linux/macOS synthetic dry runs.
- `98b43f02` — real Linux USB/ESP differential; existing virtio path retained.
- `bfba1f86` — live-only root login and console CI gate.
- `faca970b` — boot documentation and sources.
- `0f5fe306` — README refresh.
- `791b3059` — retain the kernel build's provenance when reusing fixtures.
- `16061dc7` — clarify that the clean-room restriction concerns third-party source.

## Prediction

Committed in notes/px73-prediction.txt: approximately 256 MiB for a larger live payload, fixtures below 128 MiB; OVMF removable boot without a saved entry and SeaBIOS GPT/MBR boot; ten console sessions per compiler tier unchanged from ISO. Measured fixture: 67 MiB (70,254,592 bytes), both firmware paths work, ISO 50/50 and USB 50/50 assertions, ten sessions per medium, zero skips. The builder sizes larger payloads rather than claiming the fixture size for a complete distribution.

Recommendations, implemented but not decided:
- R-px73-1 A: keep the games/installer payload inside the supplied initramfs; the builder preserves its bytes and needs no kernel USB-storage driver.
- R-px73-2 A: retain BIOS support. Limine's documented GPT path uses reserved BIOS partition 3 at sectors 2048–4095, not GPT header/array sectors in the MBR gap.
- R-px73-3 A: passwordless root-only login on the LIVE medium only; installed startup/accounts are unchanged. This is not authentication.

## Evidence index

All local paths below are on kasumi under /home/mfwolffe/lanes/px73/.

- evidence/final-test.log and runs/final-test.exit: final exit 0, 2026-10-27 03:32:40–03:35:53 -0400; USB suite 142 seconds. Twelve host tests; ISO/USB console parity; both live-login boots; Linux mounted the USB ESP and matched all five files.
- evidence/native-iso.log, evidence/native-usb.log: 50/50 each, BIOS and UEFI, no skips. Existing Limine boot line identifies partition 1 and GPT disk/partition UUIDs; no invented USB media type.
- evidence/linux-usb-guest.txt: sda/sda1/sda3, PTTYPE=gpt, TYPE=vfat, five digest checks OK.
- evidence/native-efi.red.log: missing /EFI/BOOT/BOOTX64.EFI rejected by name. evidence/native-mbr.red.log: protective MBR coverage rejected by name. Launcher tests seen red before implementation in evidence/usb-tools-red.log; unknown mount status seen red in evidence/usb-write-red.log before the fail-closed fix.
- evidence/ci-plan-final.log: PASS. The legacy --gpt builder produces byte-identical output to the base builder; the existing Linux virtio oracle still sees vda2 (final-test.log).
- evidence/inputs-verified.log: two matching reads of the input digests.
- Narrow CI plants dispatched, not waited on: [missing EFI file, 40467220955](https://github.com/wolffe-lang/pax/actions/runs/40467220955), branch px73-plant-efi, commit `5257919b`; [short MBR coverage, 40467226718](https://github.com/wolffe-lang/pax/actions/runs/40467226718), branch px73-plant-mbr, commit `086db988`. Both select only mpx3-console at tier=pr (reported as partial); their conclusions still require verification.

Stick: /home/mfwolffe/lanes/px73/out/pax-stick-2ca52f5d1c07876ae0a510a54e4786e2752d156ba3a51270385e1e0a5b816515.img

SHA256 2ca52f5d1c07876ae0a510a54e4786e2752d156ba3a51270385e1e0a5b816515, 70,254,592 bytes, read twice. Its .inputs.json records base kernel provenance and initramfs SHA256 b6fed1c806044d822b3312164e8a79ea244fb5b4eb777e24545f6a42ce6ffa96. This staged artifact is the base-kernel/live-shell fixture, not a claim that the complete installer/games distribution is staged. px82's complete kernel/archive pair can be wrapped unchanged later; its banner is separate from the unchanged medium line.

### CI timeout correction (2026-10-27)

The cancelled retry of run 40468983321, job 122140184536, never reached the USB boot step. Its new Linux provisioning step spent 11:01:18–12:08:56Z downloading the 839 MB `linux-image-generic` dependency closure from the Azure mirror, including unrelated wireless/graphics firmware. The original 142-second local witness was already TCG; retained `.meta` files confirm that.

- `2db9340d`: replace installation with exactly two binary .deb downloads from the main Ubuntu archive, checked against authenticated apt metadata, and bound every provisioning/USB phase. No packages or maintainer scripts are installed/run.
- `bfe2ec5b`, `a291d880`: document the provisioning interface and bounds; refresh README.
- `c4d2b3c0`: keep nested USB deadlines inside the outer guard and record Linux guest acceleration/status/time.

New complete local rig: **186 seconds**, 12:29:41–12:32:47Z, on kasumi under the cores 0–3 lock and `taskset -c 0-3`, with a 16 GiB address-space ceiling. Cold download/extraction: **6 seconds**, 54,095,180 bytes, no firmware. USB suite: **143 seconds**, including ISO sessions **47 s**, USB sessions **49 s**, BIOS/UEFI live login **10/11 s**, and the Ubuntu Linux USB/ESP phase **7 s** (QEMU itself **6 s**). All **23** QEMU metadata records explicitly say **TCG**; PAX guests use 256 MiB, the Linux guest 1 GiB, matching CI. ISO and USB each pass 50/50 assertions; 12 existing plus 6 new host tests pass; zero skips; planner passes. The staged stick is byte-identical to the original.

Evidence is retained at `/home/mfwolffe/lanes/px73/evidence/timeout-fix/`: `resume-test.log`, `resume-test.exit` (0), phase logs, `qemu.meta`, `guest.txt`, and `inputs.json`. The two Ubuntu 6.8.0-147.147 .deb digests were each read twice:
- linux-image-6.8.0-147-generic: SHA256 08432502e565a8a3b4ab13bd8b01788a0a83c9398c8a1e9350f1225991bc4fbb (14,845,068 bytes).
- linux-modules-6.8.0-147-generic: SHA256 3b9188304d600fc35a4f4d1f99751f7ea485bb7f9e0cb87831d4ebf2d3423d9d (39,250,112 bytes).

Provisioning has an 11-minute command / 12-minute CI bound; the entire USB suite has a 20-minute command / 21-minute CI bound, with shorter named phase limits and preserved timeout failures. Every USB-path boot now explicitly requests TCG. The existing 90-minute console job bound is unchanged. The unrelated mpx5-pelt F0 remains pax#196.

### Rebase after px83

Rebased once onto trunk `3481e980` (px83 through `4441676d` plus its materialized note). The workflow merged automatically; the only conflict was the two appended SOURCES sections, both preserved. Range-diff confirms every functional px73 patch is unchanged. This inherits px83's F0/J4/K2/rootdisk fixes and updated job budgets; the prior run 40505003163 exhausted the old pelt budget. Historical local measurements above remain pre-rebase evidence, not a new kernel run.

## Done-when

- [x] GPT/FAT32 layout, five exact boot files, reproducibility and both named negative rows.
- [x] Both firmware paths, entire console suite, live root login and actual Linux USB mount/differential.
- [x] Linux/macOS writer policy and dry-run-only coverage; no physical device opened for writing.
- [x] Existing GPT bytes and Linux virtio oracle unchanged; planner and syntax checks pass.
- [x] BOOT/SOURCES and README refreshed; image and evidence retained on kasumi.
- [ ] Verify the two CI plants and the final-head merge gate; no CI waiting or label changes in this lane. Original-head run: [40468561272](https://github.com/wolffe-lang/pax/actions/runs/40468561272), in progress when audited.
- [ ] Materialize this five-section record as notes/px73-the-usb-stick.md at integration.

Issues to file/close: none. Real-machine USB keyboard/storage support, physical flashing/booting, and px82's complete payload/banner remain distinct work. The image wrapper intentionally adds no programs to the supplied archive.



