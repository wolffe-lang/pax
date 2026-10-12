/* net.S — the network's storage (px20, px21, px22, px23): no routines, only
   the .bss kernel/pci, kernel/virtio, kernel/net, kernel/arp,
   kernel/ip, kernel/icmp and kernel/udp keep their state in.

   Listed under `asm` in kernel/wolf.pkg like every file here. Module
   state holds scalars only ([mem.static.3]), the device's interrupt
   writes its words behind every thread's back, and no interrupt
   handler allocates (kernel/sched, "Regions"), so the state is words, named with
   `extern "c" let` and read and written volatile:

     pax_pci_table   64 records of 8 eight-byte words, one per PCI
                     function kernel/pci's scan found (its layout is
                     kernel/pci's), and pax_pci_count, how many
     pax_net_state   64 eight-byte words: the device (where its
                     registers are mapped, its line and vector, its
                     address, the features), the two queues, the
                     interrupt's pending word (kernel/virtio,
                     kernel/net)
     pax_net_stats   32 eight-byte words: the counters (frames and
                     bytes each way, drops by cause, interrupts)
     pax_arp_state   128 eight-byte words: kernel/arp's (its address,
                     its counters, the cache's eight entries and where
                     each keeps the frames that wait for it; px21)
     pax_ip_state    64 eight-byte words: kernel/ip's (the address,
                     netmask and gateway, the identification counter,
                     the frame a datagram is composed in, the counters;
                     px21)
     pax_ip_loop     128 eight-byte words: the loopback queue's 64
                     frames and the length of the datagram in each
                     (px23)
     pax_icmp_state  64 eight-byte words: kernel/icmp's (the echo the
                     kernel waits for, the limiter's clock, the
                     counters; px21)
     pax_udp_state   64 eight-byte words: kernel/udp's (the frame a
                     datagram is composed in, the next ephemeral port,
                     the counters; px22)
     pax_udp_socks   16 sockets of 32 eight-byte words: each one's
                     address, port, peer, timeout, its queue's counts
                     and the 16 frames the queue lives in (px22)

     pax_tcp_state   128 eight-byte words: kernel/tcp's (the frame a
                     segment is composed in, the next ephemeral port,
                     the key of the initial sequence numbers, the
                     counters; px23)
     pax_tcp_conns   1024 control blocks (px34; 256 since px24, 64 before) of 128 eight-byte words: each
                     one's addresses, ports, state, sequence numbers,
                     timers and the 32 frames of its two buffers (px23)
     pax_tcp_tw      256 eight-byte words: the frames of the time-wait
                     table (px23)

   No Linux source; no other kernel's source. */

        .section .bss
        .p2align 6
        .globl pax_pci_table
pax_pci_table:
        .zero 4096
        .globl pax_pci_count
pax_pci_count:
        .zero 64
        .globl pax_net_state
pax_net_state:
        .zero 512
        .globl pax_net_stats
pax_net_stats:
        .zero 256
        .globl pax_arp_state
pax_arp_state:
        .zero 1024
        .globl pax_ip_state
pax_ip_state:
        .zero 512
        .globl pax_ip_loop
pax_ip_loop:
        .zero 1024
        .globl pax_icmp_state
pax_icmp_state:
        .zero 512
        .globl pax_udp_state
pax_udp_state:
        .zero 512
        .globl pax_udp_socks
pax_udp_socks:
        .zero 4096

        .globl pax_tcp_state
pax_tcp_state:
        .zero 1024
        .globl pax_tcp_tw
pax_tcp_tw:
        .zero 2048
        .globl pax_tcp_conns
pax_tcp_conns:
        .zero 1024 * 1024

        .section .note.GNU-stack, "", @progbits
