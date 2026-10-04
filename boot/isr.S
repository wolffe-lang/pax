/* isr.S — interrupt and exception entry, the descriptor tables' storage
   and the routines that load them (kw10).

   Listed under `asm` in kernel/wolf.pkg, so the routines below whose
   `.globl` is written out are on wolf's roster ([abi.asm.roster]) and
   the kernel reaches them through bodyless `extern "c" fn` declarations
   (x86-64 SysV: arguments in %rdi, %rsi; the result in %rax). The
   tables are named in wolf with `extern "c" let` ([abi.link.extern]):
   wolf's module state holds scalars only ([mem.static.3]), so the
   storage is reserved here, in .bss, and every byte in it is computed
   and written by wolf (kernel/gdt, kernel/idt).

   ENTRY ([abi.interrupt], wolf-lang kw10). Wolf has no interrupt calling
   convention. Each vector 0-47 has a trampoline made by one macro: a
   vector whose exception pushes no error code pushes a zero in its
   place, so every frame has one shape; then the vector. The common path
   saves the fifteen general registers (%rax first, %r15 last), passes
   the frame's address in %rdi to wolf's `export fn pax_interrupt(f:
   *Frame)` (kernel/interrupts) with %rsp 16-aligned and DF clear,
   restores the registers, drops the vector and the error code and
   returns with `iretq`. The frame, lowest address first:

       r15 r14 r13 r12 r11 r10 r9 r8 rbp rdi rsi rdx rcx rbx rax   (0..112)
       vector (120)  error (128)                                   (ours)
       rip (136)  cs (144)  rflags (152)  rsp (160)  ss (168)      (the CPU's)

   176 bytes. The vectors whose exceptions push an error code: 8 #DF,
   10 #TS, 11 #NP, 12 #SS, 13 #GP, 14 #PF, 17 #AC, 21 #CP (Intel SDM
   vol. 3A §6.13 and Table 6-1), 29 #VC and 30 #SX (AMD64 APM vol. 2
   §8.2, Table 8-1). 32-47 are the 8259's sixteen lines, remapped there
   by kernel/timer (no error code). No x87/SSE state is saved: the
   kernel is built with none ([abi.target.none.codegen]); and it keeps
   no red zone, so an interrupt in kernel code overwrites nothing live
   below %rsp.

   The tables (all in .bss, zero until wolf writes them):
     pax_gdt        7 descriptors (56 bytes): null, kernel code, kernel
                    data, user data, user code, the 16-byte TSS descriptor
     pax_tss        the 104-byte 64-bit TSS
     pax_idt        256 16-byte gates (4096 bytes, page-aligned)
     pax_gdtr       LGDT's 10-byte operand (limit, base)
     pax_idtr       LIDT's 10-byte operand
     pax_ist1_stack 16 KiB; pax_ist1_top is its first byte past the end,
                    the TSS's IST1: #DF runs there whatever %rsp was

   Routines:
     pax_load_gdt(gdtr)   LGDT, then CS = 0x08 (a far return), DS, ES, SS,
                          FS and GS = 0x10
     pax_ltr(sel)         LTR: the task register = the TSS's selector
     pax_lidt(idtr)       LIDT
     pax_wait()           STI; HLT; CLI: sleep until one interrupt has been
                          handled, with interrupts enabled only for the HLT
                          (STI's one-instruction shadow keeps an interrupt
                          from landing between it and the HLT)
     pax_int3()           INT3, then return (the breakpoint kernel)
     pax_ud2()            UD2 (the invalid-opcode kernel; never returns
                          unless a handler moves RIP past it)
     pax_bad_stack()      %rsp = 0x1000 — PAX maps nothing in the lower
                          half — then a push: #PF, and the CPU's attempt to
                          push #PF's frame on that stack faults again, so a
                          double fault (the #DF kernel)

   Written from: the Intel SDM vol. 3A §3.4.5 (segment descriptors),
   §3.5.1 (segment descriptor tables), §6.10 (the IDTR), §6.13 (error
   code), §6.14.1 (64-bit IDT gate descriptors), §6.14.2 (the 64-bit
   stack frame), §6.14.3 (IRET in IA-32e mode), §6.14.5 (the interrupt
   stack table), §6.15 (exception reference: interrupts 0-31), §7.2.3
   and §7.7 (the TSS descriptor and the 64-bit TSS), Table 6-1; vol. 2
   (LGDT, LIDT, LTR, IRETQ, STI's interrupt shadow, HLT); the AMD64 APM
   vol. 2 §4.8 (long-mode segment descriptors), §8.2 (vectors), §8.9
   (long-mode interrupt control transfers: gates, the stack frame, IST),
   §12.2.5 (the 64-bit TSS); the x86-64 psABI. No Linux source; no other
   kernel's source. */

        .macro ISR_NOERR v
        .type pax_isr\v, @function
pax_isr\v:
        pushq   $0
        pushq   $\v
        jmp     pax_isr_common
        .size pax_isr\v, . - pax_isr\v
        .endm

        .macro ISR_ERR v
        .type pax_isr\v, @function
pax_isr\v:
        pushq   $\v
        jmp     pax_isr_common
        .size pax_isr\v, . - pax_isr\v
        .endm

        .text
        ISR_NOERR 0
        ISR_NOERR 1
        ISR_NOERR 2
        ISR_NOERR 3
        ISR_NOERR 4
        ISR_NOERR 5
        ISR_NOERR 6
        ISR_NOERR 7
        ISR_ERR   8
        ISR_NOERR 9
        ISR_ERR   10
        ISR_ERR   11
        ISR_ERR   12
        ISR_ERR   13
        ISR_ERR   14
        ISR_NOERR 15
        ISR_NOERR 16
        ISR_ERR   17
        ISR_NOERR 18
        ISR_NOERR 19
        ISR_NOERR 20
        ISR_ERR   21
        ISR_NOERR 22
        ISR_NOERR 23
        ISR_NOERR 24
        ISR_NOERR 25
        ISR_NOERR 26
        ISR_NOERR 27
        ISR_NOERR 28
        ISR_ERR   29
        ISR_ERR   30
        ISR_NOERR 31
        ISR_NOERR 32
        ISR_NOERR 33
        ISR_NOERR 34
        ISR_NOERR 35
        ISR_NOERR 36
        ISR_NOERR 37
        ISR_NOERR 38
        ISR_NOERR 39
        ISR_NOERR 40
        ISR_NOERR 41
        ISR_NOERR 42
        ISR_NOERR 43
        ISR_NOERR 44
        ISR_NOERR 45
        ISR_NOERR 46
        ISR_NOERR 47

        .globl pax_isr_common
        .type pax_isr_common, @function
pax_isr_common:
        pushq   %rax
        pushq   %rbx
        pushq   %rcx
        pushq   %rdx
        pushq   %rsi
        pushq   %rdi
        pushq   %rbp
        pushq   %r8
        pushq   %r9
        pushq   %r10
        pushq   %r11
        pushq   %r12
        pushq   %r13
        pushq   %r14
        pushq   %r15
        movq    %rsp, %rdi              /* the frame */
        movq    %rsp, %rbx              /* callee-saved: survives the call */
        andq    $-16, %rsp
        cld
        call    pax_interrupt
        movq    %rbx, %rsp
        popq    %r15
        popq    %r14
        popq    %r13
        popq    %r12
        popq    %r11
        popq    %r10
        popq    %r9
        popq    %r8
        popq    %rbp
        popq    %rdi
        popq    %rsi
        popq    %rdx
        popq    %rcx
        popq    %rbx
        popq    %rax
        addq    $16, %rsp               /* the vector and the error code */
        iretq
        .size pax_isr_common, . - pax_isr_common

        .globl pax_load_gdt
        .type pax_load_gdt, @function
pax_load_gdt:
        lgdt    (%rdi)
        movw    $0x10, %ax
        movw    %ax, %ds
        movw    %ax, %es
        movw    %ax, %ss
        movw    %ax, %fs
        movw    %ax, %gs
        popq    %rax                    /* our return address */
        pushq   $0x08
        pushq   %rax
        lretq                           /* CS = 0x08, back to the caller */
        .size pax_load_gdt, . - pax_load_gdt

        .globl pax_ltr
        .type pax_ltr, @function
pax_ltr:
        ltr     %di
        ret
        .size pax_ltr, . - pax_ltr

        .globl pax_lidt
        .type pax_lidt, @function
pax_lidt:
        lidt    (%rdi)
        ret
        .size pax_lidt, . - pax_lidt

        .globl pax_wait
        .type pax_wait, @function
pax_wait:
        sti
        hlt
        cli
        ret
        .size pax_wait, . - pax_wait

        .globl pax_int3
        .type pax_int3, @function
pax_int3:
        int3
        ret
        .size pax_int3, . - pax_int3

        .globl pax_ud2
        .type pax_ud2, @function
pax_ud2:
        ud2
        ret
        .size pax_ud2, . - pax_ud2

        .globl pax_bad_stack
        .type pax_bad_stack, @function
pax_bad_stack:
        movq    $0x1000, %rsp
        pushq   %rax
        ret
        .size pax_bad_stack, . - pax_bad_stack

/* The trampolines' addresses by vector, 0-47, for kernel/idt. */
        .section .rodata
        .p2align 3
        .globl pax_isr_table
pax_isr_table:
        .irp v, 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47
        .quad pax_isr\v
        .endr

        .section .bss
        .p2align 12
        .globl pax_idt
pax_idt:
        .zero 4096
        .p2align 4
        .globl pax_gdt
pax_gdt:
        .zero 64
        .globl pax_tss
pax_tss:
        .zero 112
        .globl pax_gdtr
pax_gdtr:
        .zero 16
        .globl pax_idtr
pax_idtr:
        .zero 16
        .p2align 4
        .globl pax_ist1_stack
pax_ist1_stack:
        .zero 16384
        .globl pax_ist1_top
pax_ist1_top:

        .section .note.GNU-stack, "", @progbits
