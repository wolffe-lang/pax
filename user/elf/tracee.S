/* px102: fixed-address, no-libc tracee for trace.c. mktrace checks the
 * symbols and the segment permissions after linking. No ASLR-dependent
 * address enters the transcript. Intel SDM: INT3, TF and debug traps;
 * x86-64 psABI A.2.1: Linux's syscall convention. */
.section .text
.global _start, trace_break, trace_setnr, trace_syscall
.global trace_store, trace_after_store, trace_exit
_start:
    int3
trace_break:
    nop
trace_setnr:
    mov $39, %eax                  /* getpid */
trace_syscall:
    syscall
trace_store:
    mov %rdi, trace_value(%rip)
trace_after_store:
    int3
trace_exit:
    mov $60, %eax                  /* exit(37) */
    mov $37, %edi
    syscall
    ud2

.section .data
.balign 8
.global trace_value
trace_value:
    .quad 0x1122334455667788
.section .note.GNU-stack,"",@progbits
