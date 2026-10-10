/* screen.S — the screen's storage and its two block moves (px19).

   Listed under `asm` in kernel/wolf.pkg. Module state holds scalars
   only ([mem.static.3]), and kernel/screen is written from interrupt
   context too (kernel/console's echo, behind every thread's back,
   wolf-lang#598's shape), so its state is bytes here, named by
   kernel/screen with `extern "c" let` and read and written volatile:

     pax_screen_state  64 eight-byte words: the framebuffer's address
                       and geometry, the grid's size, the cursor, the
                       pending wrap, the colours, the escape parser,
                       the UTF-8 decoder, the palette's 16 pixel values,
                       the counters kernel/screen reports
     pax_screen_cells  256 x 128 four-byte cells, the text grid (the
                       glyph's code point in bits 0-7, the foreground
                       colour in bits 8-11, the background in 12-15),
                       row by row, `cols` cells a row
     pax_screen_early  16384 bytes: what the kernel wrote before the
                       screen was attached, replayed onto it at attach

   The routines (System V: arguments in %rdi, %rsi, %rdx):

     pax_fb_copy(dst, src, bytes)   copy `bytes` from src to dst,
                                    upwards (dst below src, or apart):
                                    REP MOVSQ for bytes / 8, REP MOVSB
                                    for the rest; the direction flag is
                                    clear (the psABI's state at a call)
     pax_fb_fill(dst, v, qwords)    store the 64-bit `v` `qwords` times
                                    from dst upwards: REP STOSQ

   Written from the Intel SDM vol. 2 (MOVS, STOS, the REP prefix) and the
   x86-64 psABI (the direction flag clear at a call and on return, %rdi
   %rsi %rcx caller-saved). No Linux source; no other kernel's source. */

        .text
        .globl pax_fb_copy
        .type pax_fb_copy, @function
pax_fb_copy:
        movq    %rdx, %rcx
        shrq    $3, %rcx
        rep movsq
        movq    %rdx, %rcx
        andq    $7, %rcx
        rep movsb
        ret
        .size pax_fb_copy, . - pax_fb_copy

        .globl pax_fb_fill
        .type pax_fb_fill, @function
pax_fb_fill:
        movq    %rsi, %rax
        movq    %rdx, %rcx
        rep stosq
        ret
        .size pax_fb_fill, . - pax_fb_fill

        .section .bss
        .p2align 6
        .globl pax_screen_state
pax_screen_state:
        .zero 512
        .p2align 12
        .globl pax_screen_cells
pax_screen_cells:
        .zero 256 * 128 * 4
        .p2align 12
        .globl pax_screen_early
pax_screen_early:
        .zero 16384

        .section .note.GNU-stack, "", @progbits
