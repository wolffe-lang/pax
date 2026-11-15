/* raw.S — dmesg's membrane (px130): open(2) of /dev/kmsg, read(2) into an
   8 KiB buffer, lseek(2), close(2) and syslog(2) (klogctl) into the same
   buffer, each the system call with nothing around it; the answer is the
   call's, a count or -errno. No policy and no formatting here: dmesg.lu
   reads the buffer a byte at a time. References: the Linux x86-64 system
   call table (open 2, read 0, close 3, lseek 8, syslog 103), the psABI,
   open(2), read(2), lseek(2), syslog(2). */
        .text
        .globl dmesg_open
        .type dmesg_open, @function
dmesg_open:                     /* dmesg_open(flags): open("/dev/kmsg", flags) */
        movq    %rdi, %rsi
        leaq    dmesg_path(%rip), %rdi
        xorl    %edx, %edx
        movl    $2, %eax
        syscall
        ret
        .size dmesg_open, . - dmesg_open

        .globl dmesg_read
        .type dmesg_read, @function
dmesg_read:                     /* dmesg_read(fd): read(fd, dmesg_buf, 8192) */
        leaq    dmesg_buf(%rip), %rsi
        movl    $8192, %edx
        xorl    %eax, %eax
        syscall
        ret
        .size dmesg_read, . - dmesg_read

        .globl dmesg_byte
        .type dmesg_byte, @function
dmesg_byte:                     /* dmesg_byte(i): dmesg_buf[i], i < 8192 */
        leaq    dmesg_buf(%rip), %rax
        movzbl  (%rax,%rdi), %eax
        ret
        .size dmesg_byte, . - dmesg_byte

        .globl dmesg_seek
        .type dmesg_seek, @function
dmesg_seek:                     /* dmesg_seek(fd, whence): lseek(fd, 0, whence) */
        movq    %rsi, %rdx
        xorl    %esi, %esi
        movl    $8, %eax
        syscall
        ret
        .size dmesg_seek, . - dmesg_seek

        .globl dmesg_close
        .type dmesg_close, @function
dmesg_close:                    /* dmesg_close(fd) */
        movl    $3, %eax
        syscall
        ret
        .size dmesg_close, . - dmesg_close

        .globl dmesg_klog
        .type dmesg_klog, @function
dmesg_klog:                     /* dmesg_klog(type, len): syslog(type, dmesg_buf, len) */
        movq    %rsi, %rdx
        leaq    dmesg_buf(%rip), %rsi
        movl    $103, %eax
        syscall
        ret
        .size dmesg_klog, . - dmesg_klog

        .section .rodata
dmesg_path:
        .asciz  "/dev/kmsg"

        .bss
        .p2align 4
dmesg_buf:
        .zero   8192

        .section .note.GNU-stack, "", @progbits
