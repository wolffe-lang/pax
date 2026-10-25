/* Linux x86-64 open(2), syscall ABI only. No libc or kernel source.
 * Wolf's open modes cannot express O_EXCL without O_CREAT. A block
 * device must be held exclusively for the entire offline repair.
 * The caller supplies at most 4095 bytes and a trailing NUL. */
.section .bss
.balign 16
path_buf: .skip 4096
.section .text
.global px72_path_byte
.type px72_path_byte,@function
px72_path_byte:
    lea path_buf(%rip), %rax
    mov %sil, (%rax,%rdi)
    ret
.global px72_open
.type px72_open,@function
px72_open:
    mov %rdi, %rsi
    lea path_buf(%rip), %rdi
    xor %edx, %edx
    mov $2, %eax
    syscall
    ret
.global px72_close
.type px72_close,@function
px72_close:
    mov $3, %eax
    syscall
    ret
.section .note.GNU-stack,"",@progbits
