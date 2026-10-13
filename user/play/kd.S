/* kd.S — play's system calls wolf has no builtin for (px18: ioctl;
   px30: /dev/dsp; px41: the monotonic clock and a sleep to an absolute
   time, below).

   `play_kd(fd, request, arg) -> result` is `ioctl(2)` (x86-64 system
   call 16) made directly: %rax 16, the arguments in %rdi, %rsi, %rdx as
   the psABI's C convention already put them, `syscall`, and the kernel's
   answer returned as is (a negative errno on failure, as the raw call
   answers; no libc `errno`). wolf 0.2.26's prelude has no ioctl, and
   the C library's `ioctl` is variadic, which a bodyless `extern "c" fn`
   must not declare without its varargs ([abi.c.import]); a routine of
   our own is the smallest membrane. play asks it only for KIOCSOUND
   (0x4B2F) on a console descriptor.

   Listed under `asm` in user/play/wolf.pkg; wolf has the link's `cc`
   assemble it ([abi.asm.link]). Written from the x86-64 psABI (the
   argument registers, the `syscall` convention: %rcx and %r11
   clobbered) and the syscall table's number for ioctl. No libc source;
   no kernel source. */

        .text
        .globl play_kd
        .type play_kd, @function
play_kd:
        movl    $16, %eax
        syscall
        ret
        .size play_kd, . - play_kd

/* px41: the speaker's clock and its sleep. play's schedule is absolute
   (every tone's start is the first one's plus the lengths before it),
   and so must its sleep be: read the clock, subtract, and ask for a
   relative sleep (wolf's `time_sleep_ms`, all the prelude has), and a
   timer tick that falls between the read and the kernel's own reading
   makes the sleep one tick longer than the schedule asked. On PAX,
   whose sleep ends the tick after its target, that one tick puts a tone
   on the next tone's target, which is then started in the same tick: a
   pitch of an arpeggio held 0 ticks (pax#45; notes/px41). A sleep to
   an absolute time has no such window.

     play_now_ms()              clock_gettime(CLOCK_MONOTONIC): the
                                clock in milliseconds, or -errno
     play_sleep_until_ms(t)     clock_nanosleep(CLOCK_MONOTONIC,
                                TIMER_ABSTIME, t): 0 at or after t (at
                                once when t has passed), or -errno;
                                tried again after EINTR

   Written from the x86-64 psABI and syscall table (clock_gettime 228,
   clock_nanosleep 230), clock_gettime(2), clock_nanosleep(2) (the raw
   call answers a negative errno) and the uapi linux/time.h
   (CLOCK_MONOTONIC 1, TIMER_ABSTIME 1). No libc source; no kernel
   source. */

        .text
        .globl play_now_ms
        .type play_now_ms, @function
play_now_ms:
        subq    $24, %rsp               /* a timespec, the stack kept at 16 */
        movl    $1, %edi                /* CLOCK_MONOTONIC */
        movq    %rsp, %rsi
        movl    $228, %eax
        syscall
        testq   %rax, %rax
        js      1f
        movq    8(%rsp), %rax           /* nanoseconds */
        xorl    %edx, %edx
        movl    $1000000, %ecx
        divq    %rcx
        imulq   $1000, (%rsp), %rcx     /* seconds */
        addq    %rcx, %rax
1:      addq    $24, %rsp
        ret
        .size play_now_ms, . - play_now_ms

        .globl play_sleep_until_ms
        .type play_sleep_until_ms, @function
play_sleep_until_ms:
        subq    $24, %rsp
        movq    %rdi, %rax
        xorl    %edx, %edx
        movl    $1000, %ecx
        divq    %rcx                    /* seconds; %rdx the milliseconds left */
        movq    %rax, (%rsp)
        imulq   $1000000, %rdx, %rdx
        movq    %rdx, 8(%rsp)
1:      movl    $1, %edi                /* CLOCK_MONOTONIC */
        movl    $1, %esi                /* TIMER_ABSTIME */
        movq    %rsp, %rdx
        xorl    %r10d, %r10d            /* no remainder: the time is absolute */
        movl    $230, %eax
        syscall
        cmpq    $-4, %rax               /* EINTR: again, to the same time */
        je      1b
        addq    $24, %rsp
        ret
        .size play_sleep_until_ms, . - play_sleep_until_ms

/* px30: /dev/dsp, for play's mixed mode. wolf's file handles are its
   own table's indices, not descriptors (measured: a reopened file's
   handle 5 was descriptor 3), and OSS's requests take a pointer to an
   int, so the device is opened, asked and written here, on a raw
   descriptor kept in .bss, through a buffer of one period (4096 bytes)
   that play fills a frame at a time:

     play_dsp_open()            openat(AT_FDCWD, "/dev/dsp", O_WRONLY |
                                O_CLOEXEC): the descriptor, or -errno
     play_dsp_ask(req, value)   ioctl(fd, req, &value): the value the
                                device wrote back, or -errno
     play_dsp_frame(l, r)       two signed 16-bit samples into the
                                buffer (r ignored with one channel); a
                                full buffer is written out: 0, or -errno
     play_dsp_channels(n)       1 or 2: how many samples a frame holds
     play_dsp_flush()           write what the buffer holds: 0 or -errno
     play_dsp_close()           close(fd) (Linux and PAX play out what
                                is queued first): 0 or -errno

   A write is retried after EINTR and continued after a short count.
   Written from the x86-64 psABI and syscall table (read 0, write 1,
   close 3, ioctl 16, openat 257), open(2), write(2) and the uapi
   linux/soundcard.h. No libc source; no kernel source. */

        .text
        .globl play_dsp_open
        .type play_dsp_open, @function
play_dsp_open:
        movl    $257, %eax
        movq    $-100, %rdi             /* AT_FDCWD */
        leaq    play_dsp_path(%rip), %rsi
        movl    $0x80001, %edx          /* O_WRONLY | O_CLOEXEC */
        xorl    %r10d, %r10d
        syscall
        testq   %rax, %rax
        js      1f
        movq    %rax, play_dsp_fd(%rip)
        movq    $0, play_dsp_used(%rip)
1:      ret
        .size play_dsp_open, . - play_dsp_open

        .globl play_dsp_ask
        .type play_dsp_ask, @function
play_dsp_ask:
        subq    $8, %rsp
        movl    %esi, (%rsp)
        movq    %rdi, %rsi              /* the request */
        movq    play_dsp_fd(%rip), %rdi
        movq    %rsp, %rdx
        movl    $16, %eax
        syscall
        testq   %rax, %rax
        js      1f
        movslq  (%rsp), %rax
1:      addq    $8, %rsp
        ret
        .size play_dsp_ask, . - play_dsp_ask

        .globl play_dsp_channels
        .type play_dsp_channels, @function
play_dsp_channels:
        movq    %rdi, play_dsp_chans(%rip)
        xorl    %eax, %eax
        ret
        .size play_dsp_channels, . - play_dsp_channels

        .globl play_dsp_frame
        .type play_dsp_frame, @function
play_dsp_frame:
        movq    play_dsp_used(%rip), %rax
        leaq    play_dsp_buf(%rip), %rcx
        movw    %di, (%rcx,%rax)
        addq    $2, %rax
        cmpq    $2, play_dsp_chans(%rip)
        jne     1f
        movw    %si, (%rcx,%rax)
        addq    $2, %rax
1:      movq    %rax, play_dsp_used(%rip)
        cmpq    $4096, %rax
        jb      2f
        jmp     play_dsp_flush
2:      xorl    %eax, %eax
        ret
        .size play_dsp_frame, . - play_dsp_frame

        .globl play_dsp_flush
        .type play_dsp_flush, @function
play_dsp_flush:
        pushq   %rbx
        xorl    %ebx, %ebx              /* bytes written */
1:      movq    play_dsp_used(%rip), %rdx
        subq    %rbx, %rdx
        jle     3f
        movq    play_dsp_fd(%rip), %rdi
        leaq    play_dsp_buf(%rip), %rsi
        addq    %rbx, %rsi
        movl    $1, %eax
        syscall
        cmpq    $-4, %rax               /* EINTR: again */
        je      1b
        testq   %rax, %rax
        js      4f
        jz      5f
        addq    %rax, %rbx
        jmp     1b
3:      movq    $0, play_dsp_used(%rip)
        xorl    %eax, %eax
        popq    %rbx
        ret
5:      movq    $-5, %rax               /* a write that took nothing: EIO */
4:      movq    $0, play_dsp_used(%rip)
        popq    %rbx
        ret
        .size play_dsp_flush, . - play_dsp_flush

        .globl play_dsp_close
        .type play_dsp_close, @function
play_dsp_close:
        call    play_dsp_flush
        testq   %rax, %rax
        js      1f
        movq    play_dsp_fd(%rip), %rdi
        movl    $3, %eax
        syscall
1:      ret
        .size play_dsp_close, . - play_dsp_close

        .section .rodata
play_dsp_path:
        .asciz  "/dev/dsp"

        .bss
        .p2align 4
play_dsp_buf:
        .zero   4096
play_dsp_fd:
        .zero   8
play_dsp_used:
        .zero   8
play_dsp_chans:
        .zero   8

        .section .note.GNU-stack, "", @progbits
