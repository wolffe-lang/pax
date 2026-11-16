/* raw.S — logd's membrane (px133): the system calls logd.lu cannot make with wolf's
   builtins, each the call with nothing around it; the answer is the call's, a count or
   -errno. open(2) of /dev/kmsg and read(2) into an 8 KiB buffer (read a byte at a time by
   logd_byte), close(2); poll(2) on that descriptor and on the read end of a pipe the
   SIGTERM handler writes a byte to (the self-pipe: a SIGTERM that arrives before poll is
   still seen by it); rt_sigaction(2) of SIGTERM with SA_SIGINFO, whose handler keeps the
   sender's si_code and si_pid (SI_KERNEL, 0x80, is the kernel's end of the run; SI_USER
   is a kill(2)); clock_gettime(2) in microseconds; uname(2)'s release. No policy here.
   References: the Linux x86-64 system call table (read 0, open 2, close 3, poll 7,
   rt_sigaction 13, rt_sigreturn 15, uname 63, clock_gettime 228, pipe2 293), the psABI,
   sigaction(2) (siginfo_t: si_signo 0, si_errno 4, si_code 8, si_pid 16), poll(2),
   uname(2) (struct utsname: six fields of 65 bytes, the release the third). */
        .text
        .globl logd_kmsg_open
        .type logd_kmsg_open, @function
logd_kmsg_open:                 /* logd_kmsg_open(flags): open("/dev/kmsg", flags) */
        movq    %rdi, %rsi
        leaq    logd_path(%rip), %rdi
        xorl    %edx, %edx
        movl    $2, %eax
        syscall
        ret
        .size logd_kmsg_open, . - logd_kmsg_open

        .globl logd_read
        .type logd_read, @function
logd_read:                      /* logd_read(fd): read(fd, logd_buf, 8192) */
        leaq    logd_buf(%rip), %rsi
        movl    $8192, %edx
        xorl    %eax, %eax
        syscall
        ret
        .size logd_read, . - logd_read

        .globl logd_byte
        .type logd_byte, @function
logd_byte:                      /* logd_byte(i): logd_buf[i], i < 8192 */
        leaq    logd_buf(%rip), %rax
        movzbl  (%rax,%rdi), %eax
        ret
        .size logd_byte, . - logd_byte

        .globl logd_close
        .type logd_close, @function
logd_close:                     /* logd_close(fd) */
        movl    $3, %eax
        syscall
        ret
        .size logd_close, . - logd_close

        .globl logd_poll
        .type logd_poll, @function
logd_poll:                      /* logd_poll(fd, ms): poll {fd, the SIGTERM pipe} for input;
                                   bit 0 fd ready, bit 1 a SIGTERM came; 0 at the timeout */
        leaq    logd_pfds(%rip), %rax
        movl    %edi, (%rax)                    /* pfds[0].fd */
        movw    $1, 4(%rax)                     /* .events = POLLIN */
        movw    $0, 6(%rax)
        movl    logd_pipe_r(%rip), %ecx
        movl    %ecx, 8(%rax)                   /* pfds[1].fd: the pipe's read end, or -1 */
        movw    $1, 12(%rax)
        movw    $0, 14(%rax)
        movq    %rsi, %rdx                      /* timeout */
        movq    %rax, %rdi
        movl    $2, %esi
        movl    $7, %eax
        syscall
        testq   %rax, %rax
        jle     1f                              /* -errno, or 0 at the timeout */
        xorl    %eax, %eax
        leaq    logd_pfds(%rip), %rcx
        cmpw    $0, 6(%rcx)
        je      2f
        orl     $1, %eax
2:      cmpw    $0, 14(%rcx)
        je      1f
        orl     $2, %eax
1:      ret
        .size logd_poll, . - logd_poll

        .globl logd_term_setup
        .type logd_term_setup, @function
logd_term_setup:                /* the pipe (O_NONBLOCK|O_CLOEXEC), then SIGTERM's handler */
        leaq    logd_pipe_r(%rip), %rdi         /* logd_pipe_r, logd_pipe_w: two ints */
        movl    $0x80800, %esi                  /* O_NONBLOCK 0x800 | O_CLOEXEC 0x80000 */
        movl    $293, %eax
        syscall
        testq   %rax, %rax
        jne     1f
        leaq    logd_act(%rip), %rsi
        leaq    logd_on_term(%rip), %rax
        movq    %rax, (%rsi)                    /* sa_handler */
        movq    $0x04000004, 8(%rsi)            /* SA_RESTORER | SA_SIGINFO */
        leaq    logd_restore(%rip), %rax
        movq    %rax, 16(%rsi)                  /* sa_restorer */
        movq    $0, 24(%rsi)                    /* sa_mask: none */
        movl    $15, %edi                       /* SIGTERM */
        xorl    %edx, %edx
        movl    $8, %r10d
        movl    $13, %eax
        syscall
1:      ret
        .size logd_term_setup, . - logd_term_setup

        .type logd_on_term, @function
logd_on_term:                   /* handler(sig, si, uc): the sender kept, a byte to the pipe */
        movslq  8(%rsi), %rax
        movq    %rax, logd_code(%rip)
        movslq  16(%rsi), %rax
        movq    %rax, logd_pid(%rip)
        movq    $1, logd_flag(%rip)
        movl    logd_pipe_w(%rip), %edi
        leaq    logd_one(%rip), %rsi
        movl    $1, %edx
        movl    $1, %eax
        syscall
        ret
        .size logd_on_term, . - logd_on_term

        .type logd_restore, @function
logd_restore:                   /* the handler's return: rt_sigreturn */
        movl    $15, %eax
        syscall
        .size logd_restore, . - logd_restore

        .globl logd_term_flag
        .type logd_term_flag, @function
logd_term_flag:                 /* 1 once a SIGTERM came, else 0 */
        movq    logd_flag(%rip), %rax
        ret
        .size logd_term_flag, . - logd_term_flag

        .globl logd_term_code
        .type logd_term_code, @function
logd_term_code:                 /* the SIGTERM's si_code */
        movq    logd_code(%rip), %rax
        ret
        .size logd_term_code, . - logd_term_code

        .globl logd_term_pid
        .type logd_term_pid, @function
logd_term_pid:                  /* the SIGTERM's si_pid */
        movq    logd_pid(%rip), %rax
        ret
        .size logd_term_pid, . - logd_term_pid

        .globl logd_clock
        .type logd_clock, @function
logd_clock:                     /* logd_clock(id): clock_gettime(id) in microseconds, or -errno */
        leaq    logd_ts(%rip), %rsi
        movl    $228, %eax
        syscall
        testq   %rax, %rax
        jne     1f
        leaq    logd_ts(%rip), %rsi
        movq    8(%rsi), %rax                   /* tv_nsec */
        xorl    %edx, %edx
        movl    $1000, %ecx
        divq    %rcx
        movq    %rax, %r8
        movq    (%rsi), %rax                    /* tv_sec */
        imulq   $1000000, %rax, %rax
        addq    %r8, %rax
1:      ret
        .size logd_clock, . - logd_clock

        .globl logd_uname
        .type logd_uname, @function
logd_uname:                     /* logd_uname(): uname(logd_uts), 0 or -errno */
        leaq    logd_uts(%rip), %rdi
        movl    $63, %eax
        syscall
        ret
        .size logd_uname, . - logd_uname

        .globl logd_uname_byte
        .type logd_uname_byte, @function
logd_uname_byte:                /* logd_uname_byte(i): the release's byte i, i < 65 */
        leaq    logd_uts(%rip), %rax
        movzbl  130(%rax,%rdi), %eax
        ret
        .size logd_uname_byte, . - logd_uname_byte

        .section .rodata
logd_path:
        .asciz  "/dev/kmsg"
logd_one:
        .byte   1

        .data
        .p2align 3
logd_pipe_r:
        .long   -1
logd_pipe_w:
        .long   -1
logd_code:
        .quad   -1
logd_pid:
        .quad   0
logd_flag:
        .quad   0

        .bss
        .p2align 4
logd_buf:
        .zero   8192
logd_pfds:
        .zero   16
logd_act:
        .zero   32
logd_ts:
        .zero   16
logd_uts:
        .zero   390

        .section .note.GNU-stack, "", @progbits
