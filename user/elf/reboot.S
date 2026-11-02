/* reboot.S — px63: PAX's `reboot`. sync(2), then reboot(2) with
   LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2 and LINUX_REBOOT_CMD_RESTART
   (uapi linux/reboot.h; reboot(2)): the kernel writes every mounted
   volume, marks it clean and resets the machine. With an argument it
   halts instead (LINUX_REBOOT_CMD_HALT), `reboot -h` or any word; px78:
   `reboot -p` powers off (LINUX_REBOOT_CMD_POWER_OFF; reboot(8)'s -p,
   --poweroff), the end pax-install offers on a machine with no serial
   console.

   px87 (pax#243): run as `poweroff` (argv[0]'s base name: the image's
   /bin/poweroff is this program under a second name, as reboot(8),
   halt(8) and poweroff(8) are one program on Linux), it powers off,
   whatever its arguments.

   px87 (pax#265): reboot(2) is root's alone. A refused call is said on
   standard error as Linux's tools say it, measured black-box as uid 1000
   (notes/px87/linux/reboot-as-user.log: Ubuntu 24.04's busybox-static
   1.36.1, `reboot -f` -> `reboot: Operation not permitted`, `poweroff -f`
   -> `poweroff: Operation not permitted`, each exit 1): the program's
   base name, `: `, strerror's text of the errno (EPERM, EINVAL and EFAULT
   by name, any other `Unknown error`), and the program exits 1. px63's
   version exited 1 saying nothing.

   Built by tools/mkdiskprobe: cc -nostdlib -static -no-pie, ET_EXEC
   with no PT_INTERP. */
        .globl  _start
        .text
_start:
        movl    $162, %eax              /* sync */
        syscall
        /* %r12..%r13: argv[0]'s base name (after its last '/'), or
           "reboot" when there is no argv[0]. */
        leaq    dname(%rip), %r12
        leaq    dname_end(%rip), %r13
        cmpq    $0, (%rsp)              /* argc */
        je      2f
        movq    8(%rsp), %rdi           /* argv[0] */
        testq   %rdi, %rdi
        jz      2f
        movq    %rdi, %r12
1:      movb    (%rdi), %al
        testb   %al, %al
        jz      3f
        incq    %rdi
        cmpb    $'/', %al
        jne     1b
        movq    %rdi, %r12              /* the byte after a slash */
        jmp     1b
3:      movq    %rdi, %r13              /* argv[0]'s NUL */
2:      movl    $0x01234567, %edx       /* LINUX_REBOOT_CMD_RESTART */
        movq    %r13, %rax
        subq    %r12, %rax
        cmpq    $8, %rax                /* named `poweroff`? */
        jne     4f
        movabsq $0x66666f7265776f70, %rax /* "poweroff", little-endian */
        cmpq    %rax, (%r12)
        jne     4f
        movl    $0x4321fedc, %edx       /* LINUX_REBOOT_CMD_POWER_OFF */
        jmp     9f
4:      cmpq    $1, (%rsp)              /* argc */
        jbe     9f
        movl    $0xcdef0123, %edx       /* LINUX_REBOOT_CMD_HALT */
        movq    16(%rsp), %rcx          /* argv[1] */
        cmpb    $'-', (%rcx)
        jne     9f
        cmpb    $'p', 1(%rcx)
        jne     9f
        cmpb    $0, 2(%rcx)
        jne     9f
        movl    $0x4321fedc, %edx       /* LINUX_REBOOT_CMD_POWER_OFF */
9:      movl    $169, %eax              /* reboot */
        movl    $0xfee1dead, %edi
        movl    $672274793, %esi
        xorl    %r10d, %r10d
        syscall
        /* Refused (it returned): -errno in %rax. */
        movq    %rax, %r14
        negq    %r14
        movl    $1, %eax                /* write(2, name, len) */
        movl    $2, %edi
        movq    %r12, %rsi
        movq    %r13, %rdx
        subq    %r12, %rdx
        syscall
        movl    $1, %eax                /* write(2, ": ", 2) */
        movl    $2, %edi
        leaq    colon(%rip), %rsi
        movl    $2, %edx
        syscall
        leaq    eother(%rip), %rsi
        movl    $eother_end - eother, %edx
        cmpq    $1, %r14                /* EPERM */
        jne     5f
        leaq    eperm(%rip), %rsi
        movl    $eperm_end - eperm, %edx
5:      cmpq    $22, %r14               /* EINVAL */
        jne     6f
        leaq    einval(%rip), %rsi
        movl    $einval_end - einval, %edx
6:      cmpq    $14, %r14               /* EFAULT */
        jne     7f
        leaq    efault(%rip), %rsi
        movl    $efault_end - efault, %edx
7:      movl    $1, %eax                /* write(2, text, len) */
        movl    $2, %edi
        syscall
        movl    $231, %eax              /* exit_group(1): the reboot was refused */
        movl    $1, %edi
        syscall
        hlt

        .section .rodata
dname:  .ascii  "reboot"
dname_end:
colon:  .ascii  ": "
eperm:  .ascii  "Operation not permitted\n"
eperm_end:
einval: .ascii  "Invalid argument\n"
einval_end:
efault: .ascii  "Bad address\n"
efault_end:
eother: .ascii  "Unknown error\n"
eother_end:

        .section .note.GNU-stack, "", @progbits
