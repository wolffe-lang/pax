PAX wire stick: px89 (the wire on metal), pax branch px89 at f68505c6 (2026-11-04)

BOOT THIS ONE: pax-wire-f68505c6.img
Size:    241172480 bytes
SHA256:  ba06df597c9fac9ce1ffa40864a2fee2c15be16b47276ba63d7a7d75537358c7
Commit:  f68505c68ea4362376bc40b80fb1c52790f2810e (branch px89; not yet on trunk)
Kernel:  kmain_session (the live session kernel), /boot/pax on the stick's ESP
Root:    /boot/initramfs.cpio: pelt, cat, ls, echo, sleep, mkdir, paxfat, netstate, tcpprobe; /etc/pax-net "dhcp wait=60";
         /etc/pax-run: "/bin/pelt /etc/wire.sh" (the record, once), then "/bin/pelt -i" (a shell)
Conf:    boot/limine-usb.conf, unchanged: a three-second menu, default entry "PAX live (root, no password)".

What it does on the metal target, by itself, with no typing:
  1. The kernel finds the Intel I225-V (PCI 70:00.0, 8086:15f3), resets it, sets the link up, waits up to
     10 s for the link, and polls it every tick (PAX programs no interrupt for the I225 yet).
  2. kernel/dhcp asks the LAN's DHCP server (192.168.0.1) for a lease: DISCOVER, OFFER, REQUEST, ACK; the
     address, netmask and default route from the lease; /etc/resolv.conf from option 6; then the kernel
     sends one ICMP echo to the router (the ping to the gateway).
  3. /etc/wire.sh records the lease, resolv.conf, and one TCP connection per line of the stick's
     /pax/wire-target (none on this stick: then the router's port 80), and appends the record to
     /pax/logs/wire-1.txt on THIS stick only (the one disk whose ESP holds this stick's token). Every
     other disk is only read, never written: the stick mounts no volume (no /etc/fstab), and the script's
     search opens each /dev/sd? only to read one file from it (Q5 below: disks beside it unchanged).
  4. It prints the record on the screen and leaves a shell.

Qualified on the lane host (QEMU 8.2.2, KVM, q35, the exact image's copies as USB storage on qemu-xhci, QEMU's
82576 `-device igb` on its user network, a SATA disk and an NVMe disk of random bytes beside it):
  Four boots, BIOS and UEFI, each on the stick and on its twin with `cmdline: netpoll` (the controller polled
  every tick, as the I225 will be on the metal target); every row PASS on all four (the lane host, 2026-11-04 01:19-01:22Z):
    Q0 the controller's line (MSI-X vector 83 / polled every tick (line 11, netpoll asked))
    Q1 the lease and resolv.conf in the record (state bound, 10.0.2.15, nameserver 10.0.2.3)
    Q2 the router answered the kernel's echo (router-echo answered)
    Q3 tcpprobe connected to a server at 10.0.2.2 and read its first line
    Q4 the record on the stick's copy, /pax/logs/wire-1.txt (19 lines), read back from the image afterwards
    Q5 the SATA disk and the NVMe disk beside it byte-identical before and after (sha256 of every byte)
  The record as the qualification's stick holds it:
    px89 wire record
    == /var/lib/dhcp/pax.lease (waited 0 s)
    state bound / address 10.0.2.15 / netmask 255.255.255.0 / router 10.0.2.2 / dns 10.0.2.3 / server 10.0.2.2
    lease 86400 / t1 43200 / t2 75600 / since 0 / router-echo answered
    == /etc/resolv.conf
    nameserver 10.0.2.3
    == the stick: /dev/sdb
    == tcpprobe 10.0.2.2 47945
    tcpprobe: connected 10.0.2.15:58399 -> 10.0.2.2:47945 in 941 ms
    tcpprobe: the server's first line: px89-wire-qualify: hello from the host
  On the metal target expect 192.168.0.x from 192.168.0.1, the stick as /dev/sdc or later (after the SATA disks), and,
  with no /pax/wire-target, "== tcpprobe 192.168.0.1 80 (the router: ...)" and the router's HTTP status line.

BEFORE THE SESSION (optional: the TCP host, R-px89-3)
  The TCP connection goes to the router's port 80 unless the stick's ESP has a file pax/wire-target
  with lines "<ip> <port>" (for example "192.168.0.50 22", an address made up here). To name a host: after
  writing the stick, the computer mounts its first partition (FAT, about 227 MiB); create the folder "pax" if it is not there
  and the file "pax/wire-target" in it; eject. Nothing else on the stick needs changing.

THE SESSION
  0. Write the stick: balenaEtcher, pax-wire-f68505c6.img. Check its digest first:
       shasum -a 256 ~/pax-smoke/pax-wire-f68505c6.img   (must print ba06df597c9fac9ce1ffa40864a2fee2c15be16b47276ba63d7a7d75537358c7)
  1. The metal target: the Ethernet cable in the port CachyOS calls enp112s0 (the I225-V, MAC 7c:10:c9:3f:cb:9c; it is
     the port cabled today). The other wired port (the Aquantia 10 GbE) stays empty.
  2. The stick in a USB port. Power on, press F8, choose the stick's UEFI entry. Limine's menu: let the
     default boot (3 s). Take a phone VIDEO from the menu to the end of the record.
  3. PHOTOGRAPH these lines (they scroll; the video catches them):
       net: Intel I225/I226 8086:15f3 at 70:00.0, bar0 0x...a4900000, reset in ... us, address from RAL0/RAH0
       net: link up after ... ms: ... (STATUS ...)            or   net: NO link after 10000 ms (STATUS ...)
       net: regs CTRL ... STATUS ... (one long line: what the controller holds)
       net: 7c:10:c9:3f:cb:9c, polled every tick (line ..., an I225: polled by design), 66 frames held
       dhcp: started on 7c:10:c9:3f:cb:9c ...
       dhcp: +... s DISCOVER / OFFER / REQUEST / ACK ... / bound 192.168.0.x netmask ... gateway 192.168.0.1
       dhcp: the router 192.168.0.1 answers the kernel's echo     (or "does NOT answer")
  4. The record, printed at the end ("px89 wire record", the lease file, resolv.conf, "== the stick: /dev/sd?",
     "== tcpprobe ...", "tcpprobe: connected ... in ... ms", "== written to /pax/logs/wire-1.txt on /dev/sd?").
     PHOTOGRAPH the whole record. The line "== written to ..." means the record is on the stick (synced).
  5. Done: hold the power button to turn the metal target off (this stick has no reboot program). Remove the stick.
  6. Back on the build Mac: plug the stick in; its first partition mounts; copy pax/logs/wire-1.txt to
     ~/pax-smoke/wire-f68505c6-record.txt (or leave the stick for the lane to read).

IF IT GOES WRONG (photograph the screen each time; nothing here can write the metal target's disks)
  - No "net: Intel I225/I226" line: photograph the "pci 70:00.0 ..." line and any "net:" line.
  - "net: refused: ...": photograph it; the network is off for this boot.
  - "net: NO link after 10000 ms": check the cable is in the I225-V's port; photograph the regs line.
  - "dhcp: no lease after 60 s": photograph the dhcp: lines (each DISCOVER is retried at 4, 8, 16, 32, 64 s).
  - The screen stops with "PANIC ...": photograph it.

NEVER: run an installer or a formatter; boot anything but the stick's entry; write any disk.
