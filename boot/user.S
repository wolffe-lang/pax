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
                         in its CPU's record (px161), loads the record's
                         kernel stack top (the running thread's, which
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
                         (boot/isr.S's pax_sysret). px161: SWAPGS first,
                         and the two words are this CPU's record's
                         (kernel/percpu, %gs:24 and %gs:16), words 1 and 0
                         of pax_syscall_state before.
   pax_enter_user(rip, rsp)
                         a kernel thread's way into ring 3, never
                         returning: CLI (px131: and kernel/latency's
                         interval closed, when it is on), then on the
                         current stack the
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
     pax_syscall_state   eight 8-byte words: 0 and 1 unused since px161
                         (the running thread's kernel stack top and the
                         user RSP: each CPU's record's now), 2 the
                         timer ticks that landed in ring 3, 3 SMAP on,
                         4 SMEP on, 5 the last exit's status + 1 (px13),
                         6 the wall clock at tick 0 (px26), 7 a page fault
                         past a mapped file's end, for SIGBUS (px62).
     pax_kbuf            8192 bytes of scratch for a system call (px12):
                         [0, 4096) a path copied in from the caller,
                         [4096, 8192) the path made canonical. One CPU and
                         IF clear from SYSCALL to SYSRETQ, so one buffer
                         serves every call (kernel/files).
     pax_execbuf         4096 bytes where kernel/user's `exec` lays out
                         a path, argv and envp given as strings before
                         `exec_span` reads them (px12); kernel thread
                         context, IF clear.
     pax_argbuf          69632 bytes where kernel/process stages a new
                         program's strings (px14): [0, 65536) argv's and
                         envp's, NUL-terminated one after another (the
                         kernel's words, or an execve caller's vectors
                         copied out of its memory), [65536, 69632) the
                         path; IF clear for the whole call.
     pax_ofiles          2048 open files (px34; 512 since px24, 64 before), 64 bytes each (px17): what a
                         descriptor names and every descriptor duplicated
                         from it shares (kernel/files): a reference count,
                         the kind, the node, the offset, the open flags.
     pax_pipes           512 pipe buffers' records (px34; 64 since px24, 16 before), 256 bytes each (px17):
                         the frames holding the bytes (kernel/files), the
                         readers and writers open, the bytes read and
                         written so far. A socketpair is two of them.

   Written from: the Intel SDM vol. 3A §5.8.8 (SYSCALL and SYSRET in
   64-bit mode), §6.14.2 and §6.14.3 (the 64-bit stack frame, IRET),
   §4.6.1 (SMEP, SMAP, EFLAGS.AC); vol. 2 (SYSCALL, SYSRET, IRET, STAC,
   CLAC, CLI); the AMD64 APM vol. 2 §6.1.1 (SYSCALL and SYSRET) and
   §8.9.3; the x86-64 psABI A.2.1 (the Linux kernel calling convention:
   number in %rax, arguments in %rdi, %rsi, %rdx, %r10, %r8, %r9, %rcx and
   %r11 destroyed, the result in %rax, -4095..-1 an error). No Linux
   source; no other kernel's source. */

/* px161: SWAPGS and the GS-relative accesses are written as their bytes:
   clef, the assembler in wolf (tests/kernel-as's K5, which holds every
   object to GNU as's), has neither the mnemonic nor a %gs: memory operand
   yet. The bytes are what GNU as and clang emit for the instruction in
   each comment (Intel SDM vol. 2: SWAPGS 0F 01 F8; MOV, CMP and PUSH with
   the GS prefix 65 and an absolute disp32, ModRM rm 100 and SIB 25). */
        .macro SWAPGS
        .byte   0x0f, 0x01, 0xf8        /* swapgs */
        .endm

        .text
        .globl pax_syscall_entry
        .type pax_syscall_entry, @function
pax_syscall_entry:
        SWAPGS                          /* px161: this CPU's record at %gs */
        .byte   0x65, 0x48, 0x89, 0x24, 0x25, 0x18, 0x00, 0x00, 0x00 /* movq    %rsp, %gs:24: the user's rsp, in the record */
        .byte   0x65, 0x48, 0x8b, 0x24, 0x25, 0x10, 0x00, 0x00, 0x00 /* movq    %gs:16, %rsp: the running thread's kernel stack */
        pushq   $0x1b                   /* SS */
        .byte   0x65, 0xff, 0x34, 0x25, 0x18, 0x00, 0x00, 0x00 /* pushq   %gs:24: RSP */
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
        testq   $1, pax_lat(%rip)       /* px131: ring 3 runs with IF set: */
        jz      1f                      /* kernel/latency's interval closes */
        pushq   %rdi
        pushq   %rsi
        pushq   %rbx                    /* %rsp 16-aligned for the call */
        movq    pax_lat+248(%rip), %rax /* kernel/latency's close (word 31) */
        callq   *%rax
        popq    %rbx
        popq    %rsi
        popq    %rdi
1:
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
        SWAPGS                          /* px161: ring 3's GS, last */
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
        .p2align 12
        .globl pax_argbuf
pax_argbuf:
        .zero 69632
        .p2align 6
        .globl pax_ofiles
pax_ofiles:
        .zero 2048 * 64
        .globl pax_pipes
pax_pipes:
        .zero 512 * 256

        .section .note.GNU-stack, "", @progbits
