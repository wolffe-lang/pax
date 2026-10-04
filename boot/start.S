/* start.S — the Limine entry of the wolf kernel (M-KW; requests, px01).

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

   px01 adds four requests between the markers: bootloader info,
   firmware type, memory map and HHDM. Their response pointers are
   bootloader-written too, so wolf never reads them: boot/limine.S (on
   wolf's roster) reads them, a fresh load per call, and hands wolf
   plain integers until wolf has volatile access (kw07) and
   integer-to-pointer lowering (kw06). Each request is global so
   limine.S can name it; the layout is PROTOCOL.md's: four id words, a
   revision (0), a response pointer (0 until Limine writes it).

   px02 adds a sixth, the executable address (the kernel image's
   physical and virtual base), and moves the reading into wolf: since
   wolf-lang eb955c3b, kernel/boot_info follows each response pointer
   with `read_volatile` (kw07) through `N as *T` (kw06); limine.S only
   hands wolf each request's address (wolf-lang#529).

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

        .set LIMINE_MAGIC_0, 0xc7b1dd30df4c8b88
        .set LIMINE_MAGIC_1, 0x0a82e883a194f07b

        .globl limine_bootloader_info_request
limine_bootloader_info_request:
        .quad LIMINE_MAGIC_0, LIMINE_MAGIC_1, 0xf55038d8e2a1202f, 0x279426fcf5f59740
        .quad 0, 0

        .globl limine_firmware_type_request
limine_firmware_type_request:
        .quad LIMINE_MAGIC_0, LIMINE_MAGIC_1, 0x8c2f75d90bef28a8, 0x7045a4688eac00c3
        .quad 0, 0

        .globl limine_memmap_request
limine_memmap_request:
        .quad LIMINE_MAGIC_0, LIMINE_MAGIC_1, 0x67cf3d9d378a806f, 0xe304acdfc50c3c62
        .quad 0, 0

        .globl limine_hhdm_request
limine_hhdm_request:
        .quad LIMINE_MAGIC_0, LIMINE_MAGIC_1, 0x48dcf1cb8ad2b852, 0x63984e959a98244b
        .quad 0, 0

        .globl limine_executable_address_request
limine_executable_address_request:      /* px02: the image's physical base */
        .quad LIMINE_MAGIC_0, LIMINE_MAGIC_1, 0x71ba76863cc55f63, 0xb2644a48c516a487
        .quad 0, 0

        .globl limine_base_revision
        .set limine_base_revision, base_revision

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
