/* speaker.S — the PC speaker's storage (px18): no routines, only the
   .bss kernel/speaker keeps its state in.

   Listed under `asm` in kernel/wolf.pkg like every file here. Module
   state holds scalars only ([mem.static.3]), the tick handler writes
   the state behind every thread's back (a KDMKTONE tone's end), and
   nothing near a return to ring 3 may hold a `region` (wolf-lang#611),
   so the state is words here, named by kernel/speaker with
   `extern "c" let` and read and written volatile:

     pax_spk_state  8 eight-byte words: the sounding count (0 silent),
                    the tick a timed tone ends at (0 none), the pid that
                    started the tone (0 none), the tones started, the
                    tones stopped at their process's end, the last value
                    written to port 0x61, the events logged
     pax_spk_ring   1024 eight-byte words: the speaker's last 1024 changes,
                    each `tick << 17 | sounding << 16 | count` (a ring
                    indexed by the event count modulo 1024), which a test
                    reads from the halted machine through QEMU's monitor
                    (tests/mpx3-speaker): the kernel's own timeline of
                    every note, at the PIT's tick

   No Linux source; no other kernel's source. */

        .section .bss
        .p2align 6
        .globl pax_spk_state
pax_spk_state:
        .zero 64
        .p2align 6
        .globl pax_spk_ring
pax_spk_ring:
        .zero 8192

        .section .note.GNU-stack, "", @progbits
