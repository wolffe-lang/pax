/* sound.S — the sound device's storage (px30): no routines, only the
   .bss kernel/sound keeps its state in.

   Listed under `asm` in kernel/wolf.pkg like every file here. The
   device's interrupt writes these words behind every thread's back and
   no interrupt handler allocates (kernel/sched, "Regions"), so the
   state is words, named with `extern "c" let` and read and written
   volatile:

     pax_snd_state   128 eight-byte words: the transport's eight
                     (kernel/virtio's, selected with `virtio.use_words`),
                     the device (its line, vector, features, frames),
                     the three queues' records, the stream (format,
                     channels, rate, phase), the periods' books
     pax_snd_stats   64 eight-byte words: the counters (kernel/sound's
                     C_* constants)

   No Linux source; no other kernel's source. */

        .section .bss
        .p2align 6
        .globl pax_snd_state
pax_snd_state:
        .zero 1024
        .globl pax_snd_stats
pax_snd_stats:
        .zero 512

        .section .note.GNU-stack, "", @progbits
