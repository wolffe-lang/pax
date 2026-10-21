/* tio.S — termwolf's system calls wolf has no builtin for (px58): the
   terminal ioctls with any request and a buffer, so the probe can read
   and set every bit of `struct termios` and `struct winsize`, where wolf
   0.2.33's `os_term_set_mode` reaches five bits and VMIN/VTIME only
   ([os.term.mode]).

     tw_ioctl(fd, request, arg)   ioctl(2), x86-64 system call 16, made
                                  directly (user/play/kd.S's shape): the
                                  kernel's answer as is, a negative errno
                                  on failure
     tw_buf()                     the address of a 64-byte buffer in .bss:
                                  a termios at 0 (36 bytes: four 32-bit
                                  flag words, c_line, c_cc[19]), a
                                  winsize at 40 (four 16-bit words)
     tw_get32(off), tw_put32(off, v)   a 32-bit little-endian word of it
     tw_get8(off), tw_put8(off, v)     a byte of it
     tw_get16(off), tw_put16(off, v)   a 16-bit word of it

   Listed under `asm` in user/termwolf/wolf.pkg; wolf has the link's `cc`
   assemble it ([abi.asm.link]). Written from the x86-64 psABI (the
   argument registers, the `syscall` convention: %rcx and %r11
   clobbered), the syscall table's number for ioctl, ioctl_tty(2) and
   termios(3) (the structure's layout as TCGETS writes it, measured by
   px13: notes/px13). No libc source; no kernel source. */

        .text
        .globl tw_ioctl
        .type tw_ioctl, @function
tw_ioctl:
        movl    $16, %eax
        syscall
        ret
        .size tw_ioctl, . - tw_ioctl

        .globl tw_buf
        .type tw_buf, @function
tw_buf:
        leaq    tw_area(%rip), %rax
        ret
        .size tw_buf, . - tw_buf

        .globl tw_get32
        .type tw_get32, @function
tw_get32:
        leaq    tw_area(%rip), %rax
        movl    (%rax,%rdi), %eax       /* zero-extends into %rax */
        ret
        .size tw_get32, . - tw_get32

        .globl tw_put32
        .type tw_put32, @function
tw_put32:
        leaq    tw_area(%rip), %rax
        movl    %esi, (%rax,%rdi)
        xorl    %eax, %eax
        ret
        .size tw_put32, . - tw_put32

        .globl tw_get16
        .type tw_get16, @function
tw_get16:
        leaq    tw_area(%rip), %rax
        movzwl  (%rax,%rdi), %eax
        ret
        .size tw_get16, . - tw_get16

        .globl tw_put16
        .type tw_put16, @function
tw_put16:
        leaq    tw_area(%rip), %rax
        movw    %si, (%rax,%rdi)
        xorl    %eax, %eax
        ret
        .size tw_put16, . - tw_put16

        .globl tw_get8
        .type tw_get8, @function
tw_get8:
        leaq    tw_area(%rip), %rax
        movzbl  (%rax,%rdi), %eax
        ret
        .size tw_get8, . - tw_get8

        .globl tw_put8
        .type tw_put8, @function
tw_put8:
        leaq    tw_area(%rip), %rax
        movb    %sil, (%rax,%rdi)
        xorl    %eax, %eax
        ret
        .size tw_put8, . - tw_put8

        .bss
        .balign 16
tw_area:
        .zero   64

        .section .note.GNU-stack,"",@progbits
