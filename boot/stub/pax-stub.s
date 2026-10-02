# pax-stub.s — the harness proof.
#
# THIS IS NOT WOLF, AND IT IS THE ONLY NON-WOLF CODE IN PAX. It exists
# so the harness (tools/qemu-run, tools/expect-serial, tests/proof) has
# something to boot before wolf can write a kernel (campaign KWC). It
# is retired when px01's wolf kernel prints its own first light.
#
# What it does, and nothing more: Limine (base revision 6) enters it in
# 64-bit long mode, in the higher half, on a bootloader stack. It checks
# that Limine honoured the base revision, writes "PAX" and the firmware
# type to COM1, and leaves QEMU through isa-debug-exit with 0x10, which
# QEMU reports as exit status 33.
#
# Written from: the Limine protocol (PROTOCOL.md, limine-protocol
# 3a0526b7: request delimiters, base revisions, x86-64 machine state at
# entry, the firmware type feature), the Intel SDM (IN/OUT, HLT), the
# 16550 UART register map (THR at base+0, LSR at base+5, bit 5 = THR
# empty) and QEMU's isa-debug-exit device. No Linux source.
#
# The UART is not initialised here: both firmwares QEMU offers leave
# COM1 usable, and QEMU's 16550 ignores the baud divisor. A kernel that
# meets real hardware programs it itself.

        .set COM1,          0x3f8
        .set COM1_LSR,      COM1 + 5
        .set LSR_THR_EMPTY, 0x20
        .set EXIT_PORT,     0xf4        # tools/qemu-run's isa-debug-exit iobase
        .set EXIT_OK,       0x10        # QEMU exits (0x10 << 1) | 1 = 33
        .set EXIT_BAD_REV,  0x11        # QEMU exits 35

# --- Limine requests, between the start and end markers --------------
        .section .data.limine, "aw"
        .balign 8
requests_start:
        .quad 0xf6b8f4b39de7d1ae, 0xfab91a6940fcb9cf
        .quad 0x785c6ed015d3e316, 0x181e920a7852b9d9

base_revision:                          # Limine zeroes the third word
        .quad 0xf9562b2d5c95a6c8, 0x6a7b384944536bdc, 6

firmware_type_request:
        .quad 0xc7b1dd30df4c8b88, 0x0a82e883a194f07b
        .quad 0x8c2f75d90bef28a8, 0x7045a4688eac00c3
        .quad 0                         # revision
firmware_type_response:
        .quad 0                         # filled in by Limine

requests_end:
        .quad 0xadc0e0531bb10d03, 0x9572709f31764c62

# --- strings ----------------------------------------------------------
        .section .rodata
msg_banner:     .asciz "PAZ\n"
msg_bios:       .asciz "firmware: bios\n"
msg_uefi:       .asciz "firmware: uefi\n"
msg_other:      .asciz "firmware: other\n"
msg_none:       .asciz "firmware: no response\n"
msg_bad_rev:    .asciz "PAX: Limine did not honour base revision 6\n"

# --- code ---------------------------------------------------------------
        .section .text
        .globl _start
_start:
        cli
        cmpq    $0, base_revision+16(%rip)
        jne     bad_revision

        leaq    msg_banner(%rip), %rsi
        call    puts

        movq    firmware_type_response(%rip), %rax
        leaq    msg_none(%rip), %rsi
        testq   %rax, %rax
        jz      1f
        movq    8(%rax), %rax           # firmware_type
        leaq    msg_bios(%rip), %rsi
        cmpq    $0, %rax                # LIMINE_FIRMWARE_TYPE_X86BIOS
        je      1f
        leaq    msg_uefi(%rip), %rsi
        cmpq    $2, %rax                # LIMINE_FIRMWARE_TYPE_EFI64
        je      1f
        leaq    msg_other(%rip), %rsi
1:      call    puts

        movb    $EXIT_OK, %al
        outb    %al, $EXIT_PORT
        jmp     halt

bad_revision:
        leaq    msg_bad_rev(%rip), %rsi
        call    puts
        movb    $EXIT_BAD_REV, %al
        outb    %al, $EXIT_PORT

halt:                                   # reached only without isa-debug-exit
        cli
        hlt
        jmp     halt

# puts: write the NUL-terminated string at %rsi to COM1, polling LSR.
puts:
        movzbl  (%rsi), %ecx
        testb   %cl, %cl
        jz      3f
        movw    $COM1_LSR, %dx
2:      inb     %dx, %al
        testb   $LSR_THR_EMPTY, %al
        jz      2b
        movw    $COM1, %dx
        movb    %cl, %al
        outb    %al, %dx
        incq    %rsi
        jmp     puts
3:      ret
