/* io.S — the port I/O and the exits a wolf kernel calls (M-KW).

   Listed under `asm` in kernel/wolf.pkg, so wolf assembles it for the
   kernel's target and the kernel's calls into it are on its roster
   ([abi.asm.link], [abi.asm.roster]). Each routine is reached from wolf
   through a bodyless `extern "c" fn`, under the x86-64 SysV convention:
   arguments in %edi, %esi, …, a result in %rax.

     pax_outb(port: u16, v: u8)   one `outb` of v to port. No LSR poll:
                                  QEMU's 16550 takes a byte at once; a
                                  kernel that meets real hardware polls.
     pax_exit(code: u8)           `outb` of code to isa-debug-exit
                                  (iobase 0xf4, tools/qemu-run); QEMU
                                  ends with status (code << 1) | 1.
     pax_big() -> i64             i64::MAX, an operand no tier can fold
                                  (the trap kernel's overflow).
     wolf_trap(kind: i32, file: *u8, file_len: i64, line: i64, col: i64)
                                  the freestanding target's trap hook
                                  ([abi.target.none.hooks]): writes
                                  "TRAP <kind>\n" to COM1, then exits
                                  with 1, so QEMU ends with status 3.
                                  It never returns.

   Written from: the x86-64 psABI (argument registers), the Intel SDM
   (IN, OUT, CLI, HLT, DIV), the 16550 UART register map (THR at base+0,
   LSR at base+5, bit 5 = THR empty) and QEMU's isa-debug-exit device.
   No Linux source. */

        .set COM1,          0x3f8
        .set COM1_LSR,      COM1 + 5
        .set LSR_THR_EMPTY, 0x20
        .set EXIT_PORT,     0xf4
        .set EXIT_TRAP,     0x01        /* QEMU exits (1 << 1) | 1 = 3 */

        .section .rodata
trap_prefix:    .asciz "TRAP "
trap_newline:   .asciz "\n"

        .text
        .globl pax_outb
pax_outb:
        movl    %edi, %edx
        movl    %esi, %eax
        outb    %al, %dx
        ret

        .globl pax_exit
pax_exit:
        movl    %edi, %eax
        outb    %al, $EXIT_PORT
1:      cli                             /* reached only without isa-debug-exit */
        hlt
        jmp     1b

        .globl pax_big
pax_big:
        movabsq $0x7fffffffffffffff, %rax
        ret

        .globl wolf_trap
wolf_trap:
        cli
        movl    %edi, %r8d              /* the kind; puts keeps %r8 */
        leaq    trap_prefix(%rip), %rsi
        call    puts
        subq    $32, %rsp               /* the kind in decimal, built backwards */
        leaq    31(%rsp), %rdi
        movb    $0, (%rdi)
        movl    %r8d, %eax
        movl    $10, %r9d
2:      xorl    %edx, %edx
        divl    %r9d
        addb    $'0', %dl
        decq    %rdi
        movb    %dl, (%rdi)
        testl   %eax, %eax
        jnz     2b
        movq    %rdi, %rsi
        call    puts
        leaq    trap_newline(%rip), %rsi
        call    puts
        movb    $EXIT_TRAP, %al
        outb    %al, $EXIT_PORT
3:      cli
        hlt
        jmp     3b

/* puts: write the NUL-terminated string at %rsi to COM1, polling LSR.
   Clobbers %rax, %rcx, %rdx, %rsi. */
puts:
        movzbl  (%rsi), %ecx
        testb   %cl, %cl
        jz      5f
        movw    $COM1_LSR, %dx
4:      inb     %dx, %al
        testb   $LSR_THR_EMPTY, %al
        jz      4b
        movw    $COM1, %dx
        movb    %cl, %al
        outb    %al, %dx
        incq    %rsi
        jmp     puts
5:      ret

        .section .note.GNU-stack, "", @progbits
