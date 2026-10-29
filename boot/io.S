/* io.S — the port I/O, the halt and the exits a wolf kernel calls
   (M-KW; px01).

   Listed under `asm` in kernel/wolf.pkg, so wolf assembles it for the
   kernel's target and the kernel's calls into it are on its roster
   ([abi.asm.link], [abi.asm.roster]). Each routine is reached from wolf
   through a bodyless `extern "c" fn`, under the x86-64 SysV convention:
   arguments in %edi, %esi, …, a result in %rax.

     pax_outb(port: u16, v: u8)   one `outb` of v to port.
     pax_inb(port: u16) -> u8     one `inb` from port (px01: the UART
                                  driver's LSR polling and loopback
                                  read, kernel/serial).
     pax_outl(port: u16, v: u32)  one `outl` of v to port (px20: PCI
                                  configuration mechanism #1's address
                                  port 0xCF8, kernel/pci).
     pax_inl(port: u16) -> u32    one `inl` from port (px20: its data
                                  port 0xCFC).
     pax_halt()                   `cli; hlt`, forever: the kernel's
                                  normal end and the panic path's
                                  (px01). Never returns. Sized, so
                                  tools/qemu-halt can find it in the
                                  ELF's symbol table. px18: first it
                                  silences the PC speaker (port 0x61
                                  bits 0 and 1 cleared, bits 2-3 kept),
                                  so no halt, a panic's included,
                                  leaves a tone sounding.
     pax_exit(code: u8)           `outb` of code to isa-debug-exit
                                  (iobase 0xf4, tools/qemu-run); QEMU
                                  ends with status (code << 1) | 1.
     pax_big() -> i64             i64::MAX, an operand no tier can fold
                                  (the panic kernel's overflow).

   The trap hook `wolf_trap` was here for M-KW; since px01 it is wolf's
   own (kernel/panic), and M-KW's assembly hook is kept with M-KW's
   kernels in tests/mkw.d/boot/io.S.

   Written from: the x86-64 psABI (argument registers), the Intel SDM
   (IN, OUT, CLI, HLT), QEMU's isa-debug-exit device and the PC's port
   0x61 (px18, kernel/speaker). No Linux
   source; no other kernel's source. */

        .set EXIT_PORT,     0xf4

        .text
        .globl pax_outb
        .type pax_outb, @function
pax_outb:
        movl    %edi, %edx
        movl    %esi, %eax
        outb    %al, %dx
        ret
        .size pax_outb, . - pax_outb

        .globl pax_inb
        .type pax_inb, @function
pax_inb:
        movl    %edi, %edx
        xorl    %eax, %eax
        inb     %dx, %al
        ret
        .size pax_inb, . - pax_inb

        .globl pax_outl
        .type pax_outl, @function
pax_outl:
        movl    %edi, %edx
        movl    %esi, %eax
        outl    %eax, %dx
        ret
        .size pax_outl, . - pax_outl

        .globl pax_inl
        .type pax_inl, @function
pax_inl:
        movl    %edi, %edx
        inl     %dx, %eax
        ret
        .size pax_inl, . - pax_inl

        .globl pax_inw
        .type pax_inw, @function
pax_inw:
        movl %edi, %edx
        xorl %eax, %eax
        inw %dx, %ax
        ret
        .size pax_inw, . - pax_inw

        .globl pax_outw
        .type pax_outw, @function
pax_outw:
        movl %edi, %edx
        movl %esi, %eax
        outw %ax, %dx
        ret
        .size pax_outw, . - pax_outw

        /* A zero-limit IDT cannot service INT3 or the following #GP/#DF.
           Intel SDM vol.3A §6.15: shutdown after failed double-fault delivery. */
        .globl pax_triple_fault
        .type pax_triple_fault, @function
pax_triple_fault:
        cli
        subq $16, %rsp
        /* xorl, not xorq: a 32-bit result is zero-extended into %rax
           (Intel SDM vol.1 §3.4.1.1), and clef (user/clef.pin) knows
           xorl but has no xorq. */
        xorl %eax, %eax
        movq %rax, (%rsp)
        movq %rax, 8(%rsp)
        lidt (%rsp)
        int3
        jmp pax_halt
        .size pax_triple_fault, . - pax_triple_fault

        .globl pax_halt
        .type pax_halt, @function
pax_halt:
        cli
        inb     $0x61, %al
        andb    $0x0c, %al
        outb    %al, $0x61
1:      hlt
        jmp     1b
        .size pax_halt, . - pax_halt

        .globl pax_exit
        .type pax_exit, @function
pax_exit:
        movl    %edi, %eax
        outb    %al, $EXIT_PORT
        jmp     pax_halt                /* reached only without isa-debug-exit */
        .size pax_exit, . - pax_exit

        .globl pax_big
        .type pax_big, @function
pax_big:
        movabsq $0x7fffffffffffffff, %rax
        ret
        .size pax_big, . - pax_big

        /* px78: pax_call5(target, a, b, c, d, e): the routine at `target`
           called with the next five arguments (x86-64 psABI §3.2.3: each
           moves down one register; a tail jump leaves the stack as the
           caller's call left it, so the callee returns to the caller).
           For a module that cannot import the one it calls (wolf refuses
           an import cycle): kernel/usb_storage reaching kernel/xhci's
           exports. */
        .globl pax_call5
        .type pax_call5, @function
pax_call5:
        movq    %rdi, %rax
        movq    %rsi, %rdi
        movq    %rdx, %rsi
        movq    %rcx, %rdx
        movq    %r8, %rcx
        movq    %r9, %r8
        jmp     *%rax
        .size pax_call5, . - pax_call5

        /* px76: bounded diagnostic transcript when no UART exists.
           QEMU qualification reads these bytes through its monitor. */
        .section .bss
        .p2align 3
        .globl pax_serial_log_count
pax_serial_log_count:
        .zero 8
        .globl pax_serial_log
pax_serial_log:
        .zero 65536

        .section .note.GNU-stack, "", @progbits
