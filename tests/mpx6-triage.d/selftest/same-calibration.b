[2J[01;01H[=3h[2J[01;01H[2J[01;01H[=3h[2J[01;01H[2J[01;01H[=3h[2J[01;01HBdsDxe: loading Boot0001 "UEFI QEMU DVD-ROM QM00001 " from PciRoot(0x0)/Pci(0x1F,0x2)/Sata(0x0,0xFFFF,0x0)
BdsDxe: starting Boot0001 "UEFI QEMU DVD-ROM QM00001 " from PciRoot(0x0)/Pci(0x1F,0x2)/Sata(0x0,0xFFFF,0x0)
[01;01H[01;01HPAX: the console
kernel: 22f0860b2a3f3e5d52fc86467ba181e05aff20f5 sha256 d5096319e00e8114129eae7c2ffedd590309b066bacb6be03f501b20d78b9939, 3790408 bytes
paging: limine cr3 0x000000000bf96000, pax cr3 0x0000000000104000, 14 table frames
screen: 1280x800 32 bpp pitch 5120 rgb 8:16 8:8 8:0 at 0xffff800080000000, wc (pat 0x0000010500070406), 1000 pages 3 tables; font spleen 8x16, 160x50 cells; 239 bytes replayed, 0 lost
initramfs: module 0xffff80000bfa6000, 420 bytes, 2 entries
initramfs: dir 0 etc
initramfs: file 55 etc/pax-run
firmware: uefi64 vendor Ubuntu distribution of EDK II revision 0x0000000000010000
memory: 32 entries, total 13429669888 bytes, usable 213004288, largest unmapped hole 1082331758592
acpi: XSDT OEM BOCHS  length 84
acpi: FACP OEM BOCHS  length 244
acpi: SCI 9 PM timer 0x0000000000000608 mask 0x0000000000ffffff PM1a 0x0000000000000604 PM1b 0x0000000000000000
acpi: APIC OEM BOCHS  length 120
acpi: LAPIC id 0 flags 0x0000000000000001
acpi: IOAPIC id 0 address 0x00000000fec00000 GSI 0
acpi: ISO bus 0 IRQ 0 GSI 2 flags 0x0000000000000000
acpi: ISO bus 0 IRQ 5 GSI 5 flags 0x000000000000000d
acpi: ISO bus 0 IRQ 9 GSI 9 flags 0x000000000000000d
acpi: ISO bus 0 IRQ 10 GSI 10 flags 0x000000000000000d
acpi: ISO bus 0 IRQ 11 GSI 11 flags 0x000000000000000d
acpi: NMI UID 255 LINT 1 flags 0x0000000000000000
acpi: HPET OEM BOCHS  length 56
acpi: HPET address 0x00000000fed00000
acpi: MCFG OEM BOCHS  length 60
acpi: MCFG base 0x00000000e0000000 segment 0 buses 0..255
acpi: WAET OEM BOCHS  length 40
acpi: BGRT OEM INTEL  length 56
acpi: DSDT OEM BOCHS  length 8321
clock: HPET 10000000 fs/tick, checked against the PM timer
timer: LAPIC calibration: windows 1 and 2 disagree: 62437425 and 62500543 Hz
timer: LAPIC calibration: windows 2 and 3 of 6 agree
timer: LAPIC calibrated by HPET divide16 62502026 Hz, tick 100 Hz vector 32; PIT IRQ masked
fpu: xsave 1, xcr0 0x0000000000000007, area 832 bytes, cr0.em 0, cr0.ts 0, cr4.osfxsr 1, cr4.osxsave 1
trace-layout: Thread=512 thread-capacity=512 TraceState=232 trace-capacity=256 slots=64
sched: main 0, idle 1, 64 slots, stacks 16 KiB above a 48 KiB guard from 0xffffd00000000000, quantum 2 ticks
user: syscall star 0x0013000800000000 lstar 0xffffffff8000193c fmask 0x0000000000044700, efer.sce 1, smep 1, smap 1
console: com1 irq 4 vector 36, i8042 0x67 -> 0x65 irq 1 vector 33, 8259 master mask 0xed; iflag 0x100 oflag 0x05 cflag 0xbf lflag 0x8a3b
net: no virtio network device among 5 PCI functions; the network is off
ip: 10.0.2.15 netmask 255.255.255.0 gateway 10.0.2.2, MTU 1500, TTL 64, DF set, no fragments either way
udp: 16 sockets, a 65536-byte queue each, ports 32768-60999 from a random start, 1472 bytes a datagram, loopback by kernel/ip
tcp: 1024 blocks, 65536 bytes each way a connection, MSS 1460, ports 32768-60999 from a random start, RTO 200 ms to 60 s, time-wait 60 s in 32768 entries
ahci0: 8086:2922 at 00:1f.2, CAP.NP=5 CAP.NCS=31 S64A=1 PI=0x000000000000003f BOH=0; ports idled; one slot, polled
ahci0: 8086:2922 at 00:1f.2 port 0: ATAPI skipped (0x00000000eb140101)
ahci0: 8086:2922 at 00:1f.2 port 2: ATAPI skipped (0x00000000eb140101)
loopback: 127.0.0.1 answers the kernel's echo, 10.0.2.15 answers, 0 frames on the wire
net: the console waited 1 ms for the network (bound 10 ms: device 10, lease 0, echo 0)
marks: boot 1; the previous boot: none; CMOS 0x78-0x7f claimed; log none; framebuffer 1280x800 32 bpp pitch 5120 rgb 8:16 8:8 8:0 at 0x80000000, drawn
kernel: 22f0860b2a3f3e5d52fc86467ba181e05aff20f5 sha256 d5096319e00e8114129eae7c2ffedd590309b066bacb6be03f501b20d78b9939, 3790408 bytes
boot: 3253 ms from the kernel's entry to its first program; the console drew for 43 ms of it (0 scrolls by redraw (read 67007, write 13990 cycles; copy when read <= 4 x write), 3848 bytes)
run: 0 commands
console: 0 bytes from com1, 0 keys (0 scancodes) from the keyboard, 0 reads, 0 waited, 0 dropped
PAX: init  ended without an exit status; nothing left to run
halt
