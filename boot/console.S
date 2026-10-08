/* console.S — the console's storage (px13): no routines, only the .bss
   kernel/console keeps its state in.

   Listed under `asm` in kernel/wolf.pkg like every file here. Module
   state holds scalars only ([mem.static.3]) and nothing near a return
   to ring 3 may allocate from wolf's heap or hold a `region`
   (wolf-lang#611), so the input queue and the terminal's settings are
   bytes here, named by kernel/console with `extern "c" let` and read
   and written volatile (an interrupt handler writes them behind every
   thread's back, wolf-lang#598's shape):

     pax_con_state  64 eight-byte words: the queue's three counters (read,
                    committed, edited), the pending end of file, the
                    termios flags and control characters, the window
                    size, the keyboard's shift state, the counters
                    kernel/console reports
     pax_con_ring   4096 bytes: the input queue, a ring indexed by the
                    counters modulo 4096
     pax_log_quiet  one eight-byte word (px15): 1 when the kernel command
                    line says `quiet` (kernel/log's `quiet`, set once by
                    kernel/user's `start`), 0 otherwise

   No Linux source; no other kernel's source. */

        .section .bss
        .p2align 6
        .globl pax_con_state
pax_con_state:
        .zero 512
        .p2align 12
        .globl pax_con_ring
pax_con_ring:
        .zero 4096
        .p2align 3
        .globl pax_log_quiet
pax_log_quiet:
        .zero 8

        .section .note.GNU-stack, "", @progbits
