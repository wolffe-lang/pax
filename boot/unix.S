/* unix.S — storage for AF_UNIX path sockets (px34): no routines, only
   the .bss kernel/unix keeps its state in.

   Listed under `asm` in kernel/wolf.pkg like every file here. Module
   state holds scalars only ([mem.static.3]), so the state is words
   here, named by kernel/unix with `extern "c" let` and read and written
   volatile:

     pax_unix_state  16 eight-byte words: kernel/unix's counts (sockets
                     live and made, connections made, refusals, the
                     last census)
     pax_unix        256 sockets of 34 eight-byte words (32 before
                     px45): the state, the type, the inode the name
                     is, the peer, the two buffers, a listener's
                     backlog and queue, a queued end's listener, the
                     shutdown bits, the pending error, the
                     connections ever queued, the name, its maker's
                     ids, and (px45) SO_PEERCRED's pid and ids

   No Linux source; no other kernel's source. */

        .section .bss
        .p2align 6
        .globl pax_unix_state
pax_unix_state:
        .zero 16 * 8
        .p2align 6
        .globl pax_unix
pax_unix:
        .zero 256 * 34 * 8

        .section .note.GNU-stack, "", @progbits
