/* Linux x86-64 ABI membrane: open(2), ioctl(2), fstat(2), close(2),
   fsync(2). No policy or formatting here. The path is filled by bounded
   Wolf calls, never interpreted by a shell. ioctl's output slot starts
   zeroed so both int and unsigned-long requests have a defined width.
   References: Linux syscall table, psABI, ioctl(2), stat(2), open(2). */
.text
.globl install_path_byte
.type install_path_byte,@function
install_path_byte:
    leaq install_path(%rip), %rax
    movb %sil, (%rax,%rdi)
    ret
.size install_path_byte,.-install_path_byte
.globl install_open
.type install_open,@function
install_open:
    movq %rdi, %rsi
    leaq install_path(%rip), %rdi
    xorl %edx, %edx
    movl $2, %eax
    syscall
    ret
.size install_open,.-install_open
.globl install_query
.type install_query,@function
install_query:
    subq $16, %rsp
    movq $0, (%rsp)
    movq %rsp, %rdx
    movl $16, %eax
    syscall
    testq %rax, %rax
    js 1f
    movq (%rsp), %rax
1:  addq $16, %rsp
    ret
.size install_query,.-install_query
.globl install_rdev
.type install_rdev,@function
install_rdev:
    subq $144, %rsp
    movq %rsp, %rsi
    movl $5, %eax
    syscall
    testq %rax, %rax
    js 1f
    movq 40(%rsp), %rax
1:  addq $144, %rsp
    ret
.size install_rdev,.-install_rdev
.globl install_close
.type install_close,@function
install_close:
    movl $3, %eax
    syscall
    ret
.size install_close,.-install_close
.globl install_sync
.type install_sync,@function
install_sync:
    movl $74, %eax
    syscall
    ret
.size install_sync,.-install_sync
.globl install_peak_kb
.type install_peak_kb,@function
install_peak_kb:
    subq $144, %rsp
    movq $0, 32(%rsp)
    movq %rsp, %rsi
    movl $98, %eax
    syscall
    testq %rax, %rax
    js 1f
    movq 32(%rsp), %rax
1:  addq $144, %rsp
    ret
.size install_peak_kb,.-install_peak_kb
.bss
.align 16
install_path: .zero 4096
.section .note.GNU-stack,"",@progbits
