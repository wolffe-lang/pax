/* net.S — the network's storage (px20): no routines, only the .bss
   kernel/pci, kernel/virtio, kernel/net and kernel/arp keep their state
   in.

   Listed under `asm` in kernel/wolf.pkg like every file here. Module
   state holds scalars only ([mem.static.3]), the device's interrupt
   writes its words behind every thread's back, and nothing here may
   hold a `region` (wolf-lang#611), so the state is words, named with
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
     pax_arp_state   32 eight-byte words: kernel/arp's (the gateway's
                     address once resolved, its counters)

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
        .zero 256

        .section .note.GNU-stack, "", @progbits
