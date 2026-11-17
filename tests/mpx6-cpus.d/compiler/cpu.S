/* Build-only witness: not linked into PAX and never executed. */
.text
.globl cpu_self
.type cpu_self, @function
cpu_self:
    movq %gs:0, %rax
    ret
.size cpu_self, .-cpu_self
.globl cpu_swap
.type cpu_swap, @function
cpu_swap:
    swapgs
    ret
.size cpu_swap, .-cpu_swap
.section .note.GNU-stack,"",@progbits
