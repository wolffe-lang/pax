/* kd.S — play's one system call wolf has no builtin for (px18).

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

        .section .note.GNU-stack, "", @progbits
