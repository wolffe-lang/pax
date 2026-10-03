/* start.S — the Limine entry of the wolf kernel (M-KW).

   Limine (base revision 6, docs/BOOT.md) enters `_start` in 64-bit long
   mode, in the higher half, on a bootloader stack of at least 64 KiB
   with a zero return address pushed, interrupts off. `_start` checks
   that Limine honoured the base revision, aligns the stack to the
   psABI's 16 bytes at a call, and calls wolf's `kmain` (an `export fn`,
   [abi.target.entry]). Nothing here is wolf's business beyond that.

   Limine's response pointers are written by the bootloader after the
   image is built (docs/BOOT.md clause 5). The only one M-KW needs — the
   base revision's third word — is read here, in assembly, so no wolf
   code has to read a bootloader-written word before wolf has volatile
   access (KWC kw07).

   Not listed in kernel/wolf.pkg: the boot code is the consumer's, and
   links wolf's object (K6(b)); tools/build-kernel assembles it.

   Written from: the Limine protocol (PROTOCOL.md, limine-protocol
   3a0526b7: request delimiters, base revisions, x86-64 machine state at
   entry), the x86-64 psABI (stack alignment at a call), the Intel SDM
   (OUT, CLI, HLT) and QEMU's isa-debug-exit. No Linux source. */

        .set EXIT_PORT,     0xf4
        .set EXIT_BAD_REV,  0x11        /* QEMU exits 35 */
        .set EXIT_RETURNED, 0x12        /* QEMU exits 37: kmain came back */

/* --- Limine requests, between the start and end markers -------------- */
        .section .data.limine, "aw"
        .balign 8
requests_start:
        .quad 0xf6b8f4b39de7d1ae, 0xfab91a6940fcb9cf
        .quad 0x785c6ed015d3e316, 0x181e920a7852b9d9

base_revision:                          /* Limine zeroes the third word */
        .quad 0xf9562b2d5c95a6c8, 0x6a7b384944536bdc, 6

requests_end:
        .quad 0xadc0e0531bb10d03, 0x9572709f31764c62

/* --- code --------------------------------------------------------------- */
        .text
        .globl _start
_start:
        cli
        cmpq    $0, base_revision+16(%rip)
        jne     bad_revision
        andq    $-16, %rsp
        call    kmain
        movb    $EXIT_RETURNED, %al
        outb    %al, $EXIT_PORT
        jmp     halt

bad_revision:
        movb    $EXIT_BAD_REV, %al
        outb    %al, $EXIT_PORT

halt:                                   /* reached only without isa-debug-exit */
        cli
        hlt
        jmp     halt

        .section .note.GNU-stack, "", @progbits
