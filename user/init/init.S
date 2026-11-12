/* init.S — init's system calls wolf has no builtin for (px124): a session
   of its own, the console's ioctls, any child's wait, a signal to a pid,
   and /run's mount. Each is the x86-64 `syscall` instruction made
   directly (user/termwolf/tio.S's shape): the kernel's answer as is, a
   negative errno on failure.

     init_setsid()                setsid(2), 112: the caller leads a new
                                  session and group (the session child,
                                  before it takes the console)
     init_ioctl(fd, req, arg)     ioctl(2), 16: TIOCSCTTY and TIOCNOTTY
     init_kill(pid, sig)          kill(2), 62
     init_wait(pid, options)      wait4(2), 61, the status kept here and
                                  read by init_status(); no rusage
     init_status()                the last init_wait's status word
     init_tcsave(fd)              ioctl(fd, TCGETS) into the saved termios
     init_tcrestore(fd)           ioctl(fd, TCSETSW) from it: the console's
                                  modes as the boot left them, put back
                                  after each session (output drained first)
     init_mount_run()             mount("tmpfs", "/run", "tmpfs",
                                  MS_NOSUID | MS_NODEV, "mode=755"), 165

   Listed under `asm` in user/init/wolf.pkg; wolf has the link's `cc`
   assemble it ([abi.asm.link]). Written from the x86-64 psABI (the
   argument registers, the `syscall` convention: %rcx and %r11
   clobbered, the fourth argument in %r10), the syscall table's numbers,
   setsid(2), ioctl_tty(2) (TIOCSCTTY 0x540E, TIOCNOTTY 0x5422, TCGETS
   0x5401, TCSETSW 0x5403), termios(3) (the kernel's structure, 36 bytes,
   as px13 measured it: notes/px13), wait4(2), kill(2) and mount(2). No
   libc source; no kernel source. */

        .text
        .globl init_setsid
        .type init_setsid, @function
init_setsid:
        movl    $112, %eax
        syscall
        ret
        .size init_setsid, . - init_setsid

        .globl init_ioctl
        .type init_ioctl, @function
init_ioctl:
        movl    $16, %eax
        syscall
        ret
        .size init_ioctl, . - init_ioctl

        .globl init_kill
        .type init_kill, @function
init_kill:
        movl    $62, %eax
        syscall
        ret
        .size init_kill, . - init_kill

        .globl init_wait
        .type init_wait, @function
init_wait:
        movq    %rsi, %rdx              /* options */
        leaq    init_st(%rip), %rsi     /* the status word */
        xorl    %r10d, %r10d            /* no rusage */
        movl    $61, %eax
        syscall
        ret
        .size init_wait, . - init_wait

        .globl init_status
        .type init_status, @function
init_status:
        movl    init_st(%rip), %eax     /* zero-extends into %rax */
        ret
        .size init_status, . - init_status

        .globl init_tcsave
        .type init_tcsave, @function
init_tcsave:
        movl    $0x5401, %esi           /* TCGETS */
        leaq    init_tc(%rip), %rdx
        movl    $16, %eax
        syscall
        ret
        .size init_tcsave, . - init_tcsave

        .globl init_tcrestore
        .type init_tcrestore, @function
init_tcrestore:
        movl    $0x5403, %esi           /* TCSETSW */
        leaq    init_tc(%rip), %rdx
        movl    $16, %eax
        syscall
        ret
        .size init_tcrestore, . - init_tcrestore

        .globl init_mount_run
        .type init_mount_run, @function
init_mount_run:
        leaq    init_tmpfs(%rip), %rdi  /* source */
        leaq    init_run(%rip), %rsi    /* target */
        leaq    init_tmpfs(%rip), %rdx  /* type */
        movl    $6, %r10d               /* MS_NOSUID | MS_NODEV */
        leaq    init_mode(%rip), %r8    /* data */
        movl    $165, %eax
        syscall
        ret
        .size init_mount_run, . - init_mount_run

        .section .rodata
init_tmpfs:
        .asciz  "tmpfs"
init_run:
        .asciz  "/run"
init_mode:
        .asciz  "mode=755"

        .bss
        .balign 16
init_tc:
        .zero   64
init_st:
        .zero   8

        .section .note.GNU-stack,"",@progbits
