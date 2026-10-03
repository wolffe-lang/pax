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
     pax_halt()                   `cli; hlt`, forever: the kernel's
                                  normal end and the panic path's
                                  (px01). Never returns. Sized, so
                                  tools/qemu-halt can find it in the
                                  ELF's symbol table.
     pax_exit(code: u8)           `outb` of code to isa-debug-exit
                                  (iobase 0xf4, tools/qemu-run); QEMU
                                  ends with status (code << 1) | 1.
     pax_big() -> i64             i64::MAX, an operand no tier can fold
                                  (the panic kernel's overflow).

   The trap hook `wolf_trap` was here for M-KW; since px01 it is wolf's
   own (kernel/panic), and M-KW's assembly hook is kept with M-KW's
   kernels in tests/mkw.d/boot/io.S.

   Written from: the x86-64 psABI (argument registers), the Intel SDM
   (IN, OUT, CLI, HLT) and QEMU's isa-debug-exit device. No Linux
   source. */

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

        .globl pax_halt
        .type pax_halt, @function
pax_halt:
        cli
        hlt
        jmp     pax_halt
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

        .section .note.GNU-stack, "", @progbits
