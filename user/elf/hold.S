/* hold.S — px18's test program for the speaker's end: a static x86-64
   Linux ELF with no libc that starts a tone and exits without stopping
   it.

   `hold` asks KIOCSOUND (0x4B2F) of descriptor 1 with the count 1356
   (1193182 / 1356 = 879.9 Hz), writes one line,

       hold: KIOCSOUND 1356 answered <rc>, exiting with the tone on

   and exits 0 (exit_group). On Linux's console the tone would go on
   sounding; on PAX the speaker stops when the process that started it
   ends (kernel/speaker's `ended`), which tests/mpx3-speaker holds it
   to: the kernel's `user: speaker off at the end of pid <n>` line, port
   0x61's bits 0 and 1 clear, and the capture's 880 Hz tone ending with
   the process.

   Written from: the x86-64 psABI, syscall_64.tbl (write 1, ioctl 16,
   exit_group 231) and the uapi linux/kd.h request number. No libc; no
   Linux source. */

        .set SYS_WRITE, 1
        .set SYS_IOCTL, 16
        .set SYS_EXIT_GROUP, 231
        .set KIOCSOUND, 0x4b2f
        .set COUNT, 1356

        .text
        .globl _start
_start:
        movl    $SYS_IOCTL, %eax
        movl    $1, %edi                /* descriptor 1, the console: pelt
                                           gives a child /dev/null as its
                                           standard input (px14) */
        movl    $KIOCSOUND, %esi
        movl    $COUNT, %edx
        syscall
        movq    %rax, %r12              /* the answer, kept for the line */

        /* "hold: KIOCSOUND 1356 answered " then the answer then the tail */
        leaq    msg(%rip), %rsi
        movl    $msg_len, %edx
        call    put
        /* the answer: 0, or '-' and the errno's decimal digits */
        leaq    num(%rip), %rdi
        movq    %r12, %rax
        testq   %rax, %rax
        jns     1f
        movb    $'-', (%rdi)
        incq    %rdi
        negq    %rax
1:      leaq    digits_end(%rip), %rcx  /* digits built backwards */
        movl    $10, %r8d
2:      xorl    %edx, %edx
        divq    %r8
        addb    $'0', %dl
        decq    %rcx
        movb    %dl, (%rcx)
        testq   %rax, %rax
        jnz     2b
        leaq    digits_end(%rip), %r9
3:      cmpq    %r9, %rcx
        je      4f
        movb    (%rcx), %al
        movb    %al, (%rdi)
        incq    %rdi
        incq    %rcx
        jmp     3b
4:      leaq    num(%rip), %rsi
        movq    %rdi, %rdx
        subq    %rsi, %rdx
        call    put
        leaq    tail(%rip), %rsi
        movl    $tail_len, %edx
        call    put

        movl    $SYS_EXIT_GROUP, %eax
        xorl    %edi, %edi
        syscall
        hlt                             /* never reached */

/* put: write(1, %rsi, %rdx) */
put:
        movl    $SYS_WRITE, %eax
        movl    $1, %edi
        syscall
        ret

        .section .rodata
msg:    .ascii  "hold: KIOCSOUND 1356 answered "
        .set msg_len, . - msg
tail:   .ascii  ", exiting with the tone on\n"
        .set tail_len, . - tail

        .bss
num:    .zero   24
digits: .zero   24
digits_end:

        .section .note.GNU-stack, "", @progbits
