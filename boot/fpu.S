/* fpu.S — the x87/SSE/AVX state's control and its save and restore
   (px10), for kernel/fpu.

   Listed under `asm` in kernel/wolf.pkg, so these routines are on
   wolf's roster ([abi.asm.roster]) and reached through bodyless `extern
   "c" fn` declarations (x86-64 SysV: arguments in %rdi, %rsi, %rdx; the
   result in %rax). wolf has no inline assembly (wolf-lang#526), and
   none of these instructions has another spelling. The kernel itself
   is built with no SSE ([abi.target.none.codegen]; tools/build-kernel
   asserts no xmm/ymm register is named), and nothing here names one:
   the registers are only ever moved whole, by XSAVE/XRSTOR or
   FXSAVE/FXRSTOR, so at a switch they still hold the outgoing thread's
   state.

     pax_set_cr0(v)               MOV to CR0 (EM clear, MP set, TS clear)
     pax_cpuid(leaf, sub, reg) -> u64
                                  CPUID with EAX = leaf, ECX = sub;
                                  returns EAX, EBX, ECX or EDX for reg 0,
                                  1, 2 or 3
     pax_xgetbv0() -> u64         XGETBV with ECX = 0: XCR0
     pax_xsetbv0(v)               XSETBV with ECX = 0 (EDX:EAX = v)
     pax_fpu_save(area, mode)     mode 1: XSAVE64 of every component XCR0
                                  enables (EDX:EAX all ones), area
                                  64-byte aligned; mode 2: FXSAVE64,
                                  area 16-byte aligned; mode 0: nothing
     pax_fpu_restore(area, mode)  XRSTOR64 or FXRSTOR64 likewise
     pax_rdtsc() -> u64           RDTSC: EDX:EAX
     pax_rdrand() -> u64          RDRAND into %rax, retried while CF says
                                  no value was ready (at most 16 tries;
                                  the caller asks only when CPUID.1:ECX
                                  bit 30 says the instruction exists),
                                  0 when none came

   Written from: the Intel SDM vol. 1 §10.5 (FXSAVE's area), ch. 13
   (XSAVE: §13.2 enumeration by CPUID leaf 0DH, §13.3 enabling with
   CR4.OSXSAVE and XCR0, §13.4 the area and its header, §13.7–13.8
   XSAVE and XRSTOR's standard form, the init state), §7.3.17 (RDRAND);
   vol. 2 (CPUID, XGETBV, XSETBV, XSAVE, XRSTOR, FXSAVE, FXRSTOR, RDTSC,
   RDRAND, MOV to CR0); vol. 3A §2.5 (CR0.MP, EM, TS; CR4.OSFXSR,
   OSXMMEXCPT, OSXSAVE), §2.6 (XCR0); the AMD64 APM vol. 2 §11.5 (saving
   media and x87 state). No Linux source; no other kernel's source. */

        .text
        .globl pax_set_cr0
        .type pax_set_cr0, @function
pax_set_cr0:
        movq    %rdi, %cr0
        ret
        .size pax_set_cr0, . - pax_set_cr0

        .globl pax_cpuid
        .type pax_cpuid, @function
pax_cpuid:
        pushq   %rbx                    /* callee-saved; CPUID writes it */
        movq    %rdx, %r8               /* reg */
        movl    %edi, %eax
        movl    %esi, %ecx
        cpuid
        cmpq    $1, %r8
        je      1f
        cmpq    $2, %r8
        je      2f
        cmpq    $3, %r8
        je      3f
        movl    %eax, %eax              /* reg 0: EAX, zero-extended */
        popq    %rbx
        ret
1:      movl    %ebx, %eax
        popq    %rbx
        ret
2:      movl    %ecx, %eax
        popq    %rbx
        ret
3:      movl    %edx, %eax
        popq    %rbx
        ret
        .size pax_cpuid, . - pax_cpuid

        .globl pax_xgetbv0
        .type pax_xgetbv0, @function
pax_xgetbv0:
        xorl    %ecx, %ecx
        xgetbv
        shlq    $32, %rdx
        movl    %eax, %eax
        orq     %rdx, %rax
        ret
        .size pax_xgetbv0, . - pax_xgetbv0

        .globl pax_xsetbv0
        .type pax_xsetbv0, @function
pax_xsetbv0:
        movl    %edi, %eax
        movq    %rdi, %rdx
        shrq    $32, %rdx
        xorl    %ecx, %ecx
        xsetbv
        ret
        .size pax_xsetbv0, . - pax_xsetbv0

        .globl pax_fpu_save
        .type pax_fpu_save, @function
pax_fpu_save:
        cmpq    $1, %rsi
        je      1f
        cmpq    $2, %rsi
        je      2f
        ret
1:      movl    $-1, %eax
        movl    $-1, %edx
        xsave64 (%rdi)
        ret
2:      fxsave64 (%rdi)
        ret
        .size pax_fpu_save, . - pax_fpu_save

        .globl pax_fpu_restore
        .type pax_fpu_restore, @function
pax_fpu_restore:
        cmpq    $1, %rsi
        je      1f
        cmpq    $2, %rsi
        je      2f
        ret
1:      movl    $-1, %eax
        movl    $-1, %edx
        xrstor64 (%rdi)
        ret
2:      fxrstor64 (%rdi)
        ret
        .size pax_fpu_restore, . - pax_fpu_restore

        .globl pax_rdtsc
        .type pax_rdtsc, @function
pax_rdtsc:
        rdtsc
        shlq    $32, %rdx
        movl    %eax, %eax
        orq     %rdx, %rax
        ret
        .size pax_rdtsc, . - pax_rdtsc

        .globl pax_rdrand
        .type pax_rdrand, @function
pax_rdrand:
        movl    $16, %ecx
1:      rdrand  %rax
        jc      2f
        decl    %ecx
        jnz     1b
        xorl    %eax, %eax
2:      ret
        .size pax_rdrand, . - pax_rdrand

/* kernel/fpu's words, read and written volatile (#598's rule: state a
   switch reads lives in storage words): 0 the mode (0 off, 1 XSAVE, 2
   FXSAVE), 1 the area's size, 2 XCR0, 3 the template's address, 4–19
   each thread slot's area (an HHDM address of a frame of its own). */
        .section .bss
        .p2align 6
        .globl pax_fpu_state
pax_fpu_state:
        .zero 20 * 8

        .section .note.GNU-stack, "", @progbits
