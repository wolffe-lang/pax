/* console.S — the console's storage (px13): no routines, only the .bss
   kernel/console keeps its state in.

   Listed under `asm` in kernel/wolf.pkg like every file here. Module
   state holds scalars only ([mem.static.3]) and a system call that
   waits gives up its kernel stack, so it may hold no `region` there
   (kernel/sched, "Regions"), so the input queue and the terminal's settings are
   bytes here, named by kernel/console with `extern "c" let` and read
   and written volatile (an interrupt handler writes them behind every
   thread's back, wolf-lang#598's shape):

     pax_con_state  128 eight-byte words: the queue's three counters (read,
                    committed, edited), the pending end of file, the
                    termios flags and control characters, the window
                    size, the keyboard's shift state, the counters
                    kernel/console reports; (px117, words 64 on) the
                    pointer: the mouse reader, the position, the buttons
                    held, the modes' owner, the record being read
     pax_con_ring   4096 bytes: the input queue, a ring indexed by the
                    counters modulo 4096
     pax_log_quiet  one eight-byte word (px15): 1 when the kernel command
                    line says `quiet` (kernel/log's `quiet`, set once by
                    kernel/user's `start`), 0 otherwise
     pax_pty_table  px111: 256 records of 32 eight-byte words, kernel/pty's
                    ptys (word 0 the physical address of the frame that
                    holds a pty's state, read by kernel/console too)
     pax_tty_table  px111: 258 pairs of eight-byte words, each terminal's
                    session and foreground group by its id (1 the
                    console, 2 + n pty n): kernel/sched's

   No Linux source; no other kernel's source. */

        .section .bss
        .p2align 6
        .globl pax_con_state
pax_con_state:
        .zero 1024
        .p2align 12
        .globl pax_con_ring
pax_con_ring:
        .zero 4096
        .p2align 3
        .globl pax_log_quiet
pax_log_quiet:
        .zero 8
        .p2align 6
        .globl pax_pty_table
pax_pty_table:
        .zero 65536
        .p2align 6
        .globl pax_tty_table
pax_tty_table:
        .zero 4128

        .section .note.GNU-stack, "", @progbits
