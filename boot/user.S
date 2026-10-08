/* user.S — the way into ring 3 and back (px09, user mode).

   Listed under `asm` in kernel/wolf.pkg, so every routine whose `.globl`
   is written out is on wolf's roster ([abi.asm.roster]) and reached
   through a bodyless `extern "c" fn` (x86-64 SysV: arguments in %rdi,
   %rsi; the result in %rax). wolf has no inline assembly (wolf-lang#526),
   and SYSCALL's entry, IRETQ to ring 3, STAC and CLAC have no other
   spelling.

   pax_syscall_entry     LSTAR's target (kernel/user writes it). SYSCALL
                         in ring 3 arrives here at CPL 0 with %rcx = the
                         caller's RIP after the instruction, %r11 = its
                         RFLAGS, RFLAGS masked by FMASK (IF, TF, DF, NT,
                         AC clear), CS 0x08 and SS 0x10 from STAR[47:32]
                         — and %rsp still the USER's: SYSCALL switches no
                         stack (Intel SDM vol. 3A §5.8.8; vol. 2 SYSCALL;
                         AMD64 APM vol. 2 §6.1.1). It parks the user %rsp
                         in pax_syscall_state word 1, loads word 0 (the
                         running thread's kernel stack top, which
                         kernel/sched writes beside the TSS's RSP0 at
                         every switch), and builds there the frame an
                         interrupt from ring 3 would have built — SS
                         0x1b, the user RSP, RFLAGS (from %r11), CS 0x23,
                         RIP (from %rcx), error 0, vector 0x100
                         (PAX_SYSCALL: a number no gate has, the CPU
                         never raises it) — and joins boot/isr.S's
                         pax_isr_common, which saves the fifteen
                         registers and calls pax_interrupt. Wolf
                         dispatches (kernel/user: the number in %rax,
                         the arguments in %rdi, %rsi, %rdx, %r10, %r8,
                         %r9, the result written back to the frame's
                         %rax: the psABI's A.2.1 kernel convention, which
                         is Linux's), and the frame leaves by SYSRETQ
                         (boot/isr.S's pax_sysret). One CPU and IF clear
                         from SYSCALL to here make word 1 safe; SMP needs
                         SWAPGS and a per-CPU area.
   pax_enter_user(rip, rsp)
                         a kernel thread's way into ring 3, never
                         returning: CLI, then on the current stack the
                         frame IRETQ pops for a change to CPL 3 — SS 0x1b,
                         RSP, RFLAGS 0x202 (IF and the always-one bit;
                         IOPL 0, so CLI, HLT, IN and OUT fault in ring
                         3), CS 0x23, RIP — every general register
                         zeroed (nothing of the kernel's leaks), and
                         IRETQ (SDM vol. 3A §6.14.3 and vol. 2 IRET: a
                         return to an outer privilege level pops SS and
                         RSP). The thread's kernel stack is abandoned
                         here: interrupts and system calls from ring 3
                         start again at its top (RSP0, word 0).
   pax_peek_user(va, smap) -> u64
                         the byte at user address va. kernel/user's
                         `write` reads the caller's buffer through this
                         and nothing else, after checking every page of
                         it is present and user-accessible in the
                         current tables. With SMAP on (smap = 1) the read
                         is bracketed by STAC and CLAC (EFLAGS.AC lets a
                         supervisor access a user page, SDM vol. 3A
                         §4.6.1); without it STAC would be #UD, so smap =
                         0 reads plainly.
   pax_jump(va)          JMP to va (kmain_user_smep only: the SMEP
                         witness jumps to a user page in ring 0).

   Storage (.bss, kernel/sched and kernel/user write it, read volatile):
     pax_syscall_state   eight 8-byte words: 0 the running thread's
                         kernel stack top (SYSCALL's stack), 1 the user
                         RSP while the entry builds the frame, 2 the
                         timer ticks that landed in ring 3, 3 SMAP on,
                         4 SMEP on.
     pax_kbuf            8192 bytes of scratch for a system call (px12):
                         [0, 4096) a path copied in from the caller,
                         [4096, 8192) the path made canonical. One CPU and
                         IF clear from SYSCALL to SYSRETQ, so one buffer
                         serves every call (kernel/files).
     pax_execbuf         4096 bytes where kernel/user's `exec` lays out
                         a path, argv and envp given as strings before
                         `exec_span` reads them (px12); kernel thread
                         context, IF clear.

   Written from: the Intel SDM vol. 3A §5.8.8 (SYSCALL and SYSRET in
   64-bit mode), §6.14.2 and §6.14.3 (the 64-bit stack frame, IRET),
   §4.6.1 (SMEP, SMAP, EFLAGS.AC); vol. 2 (SYSCALL, SYSRET, IRET, STAC,
   CLAC, CLI); the AMD64 APM vol. 2 §6.1.1 (SYSCALL and SYSRET) and
   §8.9.3; the x86-64 psABI A.2.1 (the Linux kernel calling convention:
   number in %rax, arguments in %rdi, %rsi, %rdx, %r10, %r8, %r9, %rcx and
   %r11 destroyed, the result in %rax, -4095..-1 an error). No Linux
   source; no other kernel's source. */

        .text
        .globl pax_syscall_entry
        .type pax_syscall_entry, @function
pax_syscall_entry:
        movq    %rsp, pax_syscall_state+8(%rip)  /* the user's rsp */
        movq    pax_syscall_state(%rip), %rsp    /* this thread's kernel stack */
        pushq   $0x1b                   /* SS */
        pushq   pax_syscall_state+8(%rip)        /* RSP */
        pushq   %r11                    /* RFLAGS */
        pushq   $0x23                   /* CS */
        pushq   %rcx                    /* RIP */
        pushq   $0                      /* error */
        pushq   $0x100                  /* vector: PAX_SYSCALL */
        jmp     pax_isr_common
        .size pax_syscall_entry, . - pax_syscall_entry

        .globl pax_enter_user
        .type pax_enter_user, @function
pax_enter_user:
        cli
        pushq   $0x1b                   /* SS: user data, RPL 3 */
        pushq   %rsi                    /* RSP */
        pushq   $0x202                  /* RFLAGS: IF */
        pushq   $0x23                   /* CS: user code, RPL 3 */
        pushq   %rdi                    /* RIP */
        xorl    %eax, %eax
        xorl    %ebx, %ebx
        xorl    %ecx, %ecx
        xorl    %edx, %edx
        xorl    %esi, %esi
        xorl    %edi, %edi
        xorl    %ebp, %ebp
        xorl    %r8d, %r8d
        xorl    %r9d, %r9d
        xorl    %r10d, %r10d
        xorl    %r11d, %r11d
        xorl    %r12d, %r12d
        xorl    %r13d, %r13d
        xorl    %r14d, %r14d
        xorl    %r15d, %r15d
        iretq
        .size pax_enter_user, . - pax_enter_user

        .globl pax_peek_user
        .type pax_peek_user, @function
pax_peek_user:
        testq   %rsi, %rsi
        jz      1f
        stac
        movzbl  (%rdi), %eax
        clac
        ret
1:      movzbl  (%rdi), %eax
        ret
        .size pax_peek_user, . - pax_peek_user

        .globl pax_jump
        .type pax_jump, @function
pax_jump:
        jmp     *%rdi
        .size pax_jump, . - pax_jump

        .section .bss
        .p2align 6
        .globl pax_syscall_state
pax_syscall_state:
        .zero 64
        .p2align 12
        .globl pax_kbuf
pax_kbuf:
        .zero 8192
        .globl pax_execbuf
pax_execbuf:
        .zero 4096

        .section .note.GNU-stack, "", @progbits
