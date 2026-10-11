/* tree.S — the file tree's storage and its two block moves (px27).

   Listed under `asm` in kernel/wolf.pkg like every file here. Module
   state holds scalars only ([mem.static.3]) and a system call that
   waits gives up its stack (kernel/sched, "Regions"), so kernel/tree's
   state is words here, named with `extern "c" let` and read and
   written volatile; everything else the tree keeps is in frames.

     pax_tree_state   32 eight-byte words: whether the tree is made,
                      the inode table's frame, the inodes live, the
                      frames held and the cap, the free inodes' list,
                      the page of zeros a hole reads as, the refusals
                      counted (kernel/tree names each word)

     pax_tree_copy(dst, src, bytes)   copy `bytes` from src to dst,
                                      upwards (the two never overlap: a
                                      frame, the archive, a user page
                                      through the HHDM): REP MOVSQ for
                                      bytes / 8, REP MOVSB for the rest
     pax_tree_zero(dst, bytes)        store `bytes` zero bytes from dst
                                      upwards: REP STOSQ, REP STOSB

   Both take kernel addresses only (the HHDM), so SMAP is never relaxed
   for them. The direction flag is clear: SYSCALL's FMASK clears it on
   entry and the psABI keeps it clear at a call.

   Written from the Intel SDM vol. 2 (MOVS, STOS, the REP prefix) and the
   x86-64 psABI (%rdi %rsi %rdx the arguments, %rcx %rax caller-saved).
   No Linux source; no other kernel's source. */

        .text
        .globl pax_tree_copy
        .type pax_tree_copy, @function
pax_tree_copy:
        movq    %rdx, %rcx
        shrq    $3, %rcx
        rep movsq
        movq    %rdx, %rcx
        andq    $7, %rcx
        rep movsb
        ret
        .size pax_tree_copy, . - pax_tree_copy

        .globl pax_tree_zero
        .type pax_tree_zero, @function
pax_tree_zero:
        xorl    %eax, %eax
        movq    %rsi, %rcx
        shrq    $3, %rcx
        rep stosq
        movq    %rsi, %rcx
        andq    $7, %rcx
        rep stosb
        ret
        .size pax_tree_zero, . - pax_tree_zero

        .section .bss
        .p2align 6
        .globl pax_tree_state
pax_tree_state:
        .zero 256

        .section .note.GNU-stack, "", @progbits
