/* event.S — storage for eventfd counters and epoll objects (px24): no
   routines, only the .bss kernel/event keeps its state in.

   Listed under `asm` in kernel/wolf.pkg like every file here. Module
   state holds scalars only ([mem.static.3]), so the state is words
   here, named by kernel/event with `extern "c" let` and read and
   written volatile:

     pax_event_state  32 eight-byte words: kernel/event's counts (what
                      is live, what was made and freed, waits, calls
                      run again, refusals)
     pax_eventfds     64 counters of 4 eight-byte words: in use, the
                      value, how often it was added to, how often taken
     pax_epolls       16 epoll objects of 8 eight-byte words: in use,
                      the four frames that hold its registrations
                      (physical), how many it holds, the first slot
                      never used, where the next answer starts

   No Linux source; no other kernel's source. */

        .section .bss
        .p2align 6
        .globl pax_event_state
pax_event_state:
        .zero 32 * 8
        .p2align 6
        .globl pax_eventfds
pax_eventfds:
        .zero 64 * 4 * 8
        .p2align 6
        .globl pax_epolls
pax_epolls:
        .zero 16 * 8 * 8

        .section .note.GNU-stack, "", @progbits
