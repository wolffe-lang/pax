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

/* Independently addressed synchronous faults; old core offsets stay fixed. */
.org 0x40
.global trace_ud
trace_ud:
    ud2
.org 0x50
.global trace_segv, trace_segv_at
trace_segv:
    xor %eax, %eax
trace_segv_at:
    mov (%rax), %rax
.org 0x60
.global trace_div, trace_div_at
trace_div:
    xor %edx, %edx
    mov $1, %eax
    xor %ecx, %ecx
trace_div_at:
    div %rcx
.org 0x80
.global trace_recover
trace_recover:
    mov $37, %edi
    mov $60, %eax
    syscall
    ud2

.section .data
.balign 8
.global trace_value
trace_value:
    .quad 0x1122334455667788
.section .note.GNU-stack,"",@progbits
