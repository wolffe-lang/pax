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
   *Frame) -> *Frame` (kernel/interrupts) with %rsp 16-aligned and DF
   clear, moves the frame it RETURNS into %rsp (px07), restores the
   registers from it, drops the vector and the error code and returns
   with `iretq` (or, for a system call's frame, px09, `sysretq`:
   pax_sysret below). px161: between the pushes and the call, and again
   before the pops, the GS step: SWAPGS on every change of ring, so ring 0
   always finds its CPU's record at %gs:0 (the comment at the step says
   how an exception that lands in a window is told apart). A handler that returns its argument resumes the
   interrupted code; one that returns another thread's saved frame
   switches to that thread (kernel/sched, boot/sched.S: the frame lives
   on that thread's stack, where the CPU or pax_switch built it, and
   `iretq` restores its RSP with its RIP). The frame, lowest address
   first:

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
     pax_tick_count kernel/timer's tick count (px07): written by the
                    handler, polled by threads, so it is a word read
                    volatile, not a module `var` (wolf-lang#598)
     pax_tick_delivered
                    kernel/timer's count of tick interrupts taken (px131):
                    the same kind of word; pax_tick_count follows the
                    clock, so a host reads this one for the ticks lost
     pax_cpu0       px161: CPU 0's record (kernel/percpu), GS's base in
                    ring 0 on the boot processor
     pax_ap_boot    px161: sixteen words kernel/smp publishes for the
                    application processors and the processors share
     pax_ap_holds   px161: two words for each application processor
                    held at the entry (pax_ap_hold): 0 HELD, which it
                    sets, 1 its record, which kernel/smp sets

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
   (long-mode interrupt control transfers: gates, the stack frame, IST;
   §8.9.3 and §8.9.5 for px07's resumed frame),
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
        /* px76: four independently routed PCI MSI vectors. */
        ISR_NOERR 80
        ISR_NOERR 81
        ISR_NOERR 82
        ISR_NOERR 83

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
        /* px161: GS. In ring 0 IA32_GS_BASE is this CPU's record (kernel/
           percpu); in ring 3 it is the program's (0: PAX gives ring 3 no GS
           base of its own), the record waiting in IA32_KERNEL_GS_BASE. Every
           register is in the frame now, so any may be used. %r12 (callee-
           saved, so it survives pax_interrupt and every call below, and
           restored from the frame on the way out) says whether the way out
           must swap back: 1 only for an exception that landed in a window
           where ring 0 ran on ring 3's GS (between SWAPGS and SYSRETQ or
           IRETQ, or before pax_syscall_entry's own SWAPGS).
           - vector 0x100, a system call's frame: pax_syscall_entry swapped;
           - an exception (0-31: an NMI, #MC, #DB or #DF may land anywhere, and
             IRETQ's own faults land in a window): IA32_GS_BASE read; a kernel
             (negative) address is the record, anything else ring 3's, swapped;
           - an interrupt (32 and up, and pax_switch's 0x81: IF is clear in
             every window): swapped when it came from ring 3 (CS's RPL). */
        xorl    %r12d, %r12d
        cmpq    $0x100, 120(%rsp)
        je      .Lpax_gs_ready
        cmpq    $32, 120(%rsp)
        jb      .Lpax_gs_exception
        testb   $3, 144(%rsp)
        jz      .Lpax_gs_ready
        SWAPGS
        jmp     .Lpax_gs_ready
.Lpax_gs_exception:
        movl    $0xc0000101, %ecx       /* IA32_GS_BASE */
        rdmsr
        testl   %edx, %edx
        js      .Lpax_gs_ready          /* the record already */
        SWAPGS
        testb   $3, 144(%rsp)
        jnz     .Lpax_gs_ready          /* from ring 3: the way out decides by CS */
        movl    $1, %r12d               /* a window: swap back on the way out */
.Lpax_gs_ready:
        /* px131: kernel/latency's instrument, on with `latency` on the
           command line: an entry from a context with IF set opens an
           interrupts-off interval, begun at the interrupted RIP, for the
           vector, with %rax (a system call's number). px161: on CPU 0 only
           (%gs:8, the record's index): one CPU's instrument. */
        testq   $1, pax_lat(%rip)
        jz      1f
        .byte   0x65, 0x48, 0x83, 0x3c, 0x25, 0x08, 0x00, 0x00, 0x00, 0x00 /* cmpq    $0, %gs:8 */
        jne     1f
        testq   $0x200, 152(%rsp)
        jz      1f
        movq    136(%rsp), %rdi
        movq    120(%rsp), %rsi
        movq    112(%rsp), %rdx
        cld
        call    pax_lat_open
1:
        movq    %rsp, %rdi              /* the frame */
        andq    $-16, %rsp
        cld
        call    pax_interrupt
.Lpax_resume_frame:
        movq    %rax, %rsp              /* the frame to resume (px07) */
        /* px131: a frame resumed with IF set closes the interval (its
           registers are all restored from the frame below, so the call
           may clobber any; %rbx keeps %rsp across it). */
        testq   $1, pax_lat(%rip)
        jz      2f
        .byte   0x65, 0x48, 0x83, 0x3c, 0x25, 0x08, 0x00, 0x00, 0x00, 0x00 /* cmpq    $0, %gs:8: px161: CPU 0's instrument */
        jne     2f
        testq   $0x200, 152(%rsp)
        jz      2f
        movq    %rsp, %rbx
        andq    $-16, %rsp
        cld
        movq    pax_lat+248(%rip), %rax /* kernel/latency's close, through its word 31 */
        callq   *%rax
        movq    %rbx, %rsp
2:
        cmpq    $0x102, 120(%rsp)       /* px102: stopped syscall's kernel continuation */
        je      .Lpax_trace_syscall
        cmpq    $0x103, 120(%rsp)       /* px102: finish a completed clone/vfork/exec call */
        je      .Lpax_trace_finished
        cmpq    $0x100, 120(%rsp)       /* PAX_SYSCALL's frame (px09) */
        je      pax_sysret
        jmp     .Lpax_iret
.Lpax_trace_syscall:
        movq    %rsp, %rdi
        andq    $-16, %rsp
        call    pax_trace_resume_syscall
        jmp     .Lpax_resume_frame
.Lpax_trace_finished:
        movq    %rsp, %rdi
        andq    $-16, %rsp
        call    pax_trace_finish_syscall
        jmp     .Lpax_resume_frame
.Lpax_iret:
        /* px161: back to ring 3, or into a window an exception interrupted
           (%r12, set on the way in): ring 3's GS. */
        testb   $3, 144(%rsp)
        jnz     3f
        testl   %r12d, %r12d
        jz      4f
3:      SWAPGS
4:
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

/* pax_sysret (px09): the return from a system call. A frame
   boot/user.S's pax_syscall_entry built (vector 0x100) is resumed by
   SYSRETQ: RIP from %rcx, RFLAGS from %r11, CS 0x23 and SS 0x1b from
   STAR[63:48] (Intel SDM vol. 2 SYSRET; AMD64 APM vol. 2 §6.1.1), so a
   caller sees %rcx = its return address and %r11 = its RFLAGS, as the
   psABI's A.2.1 says the kernel leaves them. Two checks first, either
   of which sends the frame to the IRETQ path instead: CS must be 0x23
   (only a ring-3 syscall builds this vector), and RIP must lie below
   0x7ffffffff000. SYSRETQ with a non-canonical %rcx raises #GP in ring
   0 on the user's stack on Intel CPUs (SDM vol. 2 SYSRET, "If RCX is not
   canonical"), and the only way a syscall can return there is a
   `syscall` in the last bytes below 0x800000000000, a page PAX never
   maps; the check costs one compare. Interrupts are off from here to
   SYSRETQ (every path into pax_isr_common clears IF), which loads IF
   from %r11 with the rest of RFLAGS. An NMI between the stack load
   and SYSRETQ would run on the user's stack in ring 0: px77d puts the
   NMI's gate on IST2 (kernel/idt), so it lands on its own stack. */
        .globl pax_sysret
        .type pax_sysret, @function
pax_sysret:
        testq   $0x100, 152(%rsp)       /* TF: IRETQ restores the step flag */
        jnz     .Lpax_iret
        cmpq    $0x23, 144(%rsp)        /* the frame's CS */
        jne     .Lpax_iret
        movabsq $0x00007ffffffff000, %rcx
        cmpq    %rcx, 136(%rsp)         /* the frame's RIP */
        jae     .Lpax_iret
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
        movq    16(%rsp), %rcx          /* rip (the vector is at 0, error 8) */
        movq    32(%rsp), %r11          /* rflags */
        movq    40(%rsp), %rsp          /* the user's rsp */
        SWAPGS                          /* px161: ring 3's GS, last */
        sysretq
        .size pax_sysret, . - pax_sysret

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
        testq   $1, pax_lat(%rip)       /* px131: IF set for the HLT closes */
        jz      1f
        pushq   %rbx                    /* %rsp 16-aligned for the call */
        movq    pax_lat+248(%rip), %rax /* kernel/latency's close (word 31) */
        callq   *%rax
        popq    %rbx
1:      sti
        hlt
        cli
        testq   $1, pax_lat(%rip)       /* and the CLI opens again */
        jz      2f
        movq    (%rsp), %rdi            /* our caller */
        movq    $0x201, %rsi
        xorl    %edx, %edx
        call    pax_lat_open
2:      ret
        .size pax_wait, . - pax_wait

/* px131: pax_lat_open(rip, tag, nr): the TSC now, as the start of an
   interrupts-off interval, with where it began (%rdi), its vector or tag
   (%rsi: a vector, 0x200 an irq_save, 0x201 pax_wait) and %rdx (a system
   call's number, or the running thread's slot); kernel/latency reads
   them. Clobbers %rax, %rcx and %rdx only, so the paths that call it
   keep their registers. IF is clear. */
        .globl pax_lat_open
        .type pax_lat_open, @function
pax_lat_open:
        movq    %rdx, %rcx
        rdtsc
        shlq    $32, %rdx
        orq     %rdx, %rax
        movq    %rax, pax_lat+8(%rip)
        movq    %rdi, pax_lat+16(%rip)
        movq    %rsi, pax_lat+24(%rip)
        movq    %rcx, pax_lat+32(%rip)
        ret
        .size pax_lat_open, . - pax_lat_open

/* px161: the processors (SMP stage 1). kernel/percpu names a CPU's record
   by these offsets, and the code below and in boot/user.S and boot/sched.S
   reads them as %gs:N: 0 the record's own address, 8 its index (0 the boot
   processor), 16 the running thread's kernel stack top (SYSCALL's stack),
   24 the user RSP while pax_syscall_entry builds the frame, 32 the running
   thread's slot, 96 an application processor's idle stack top, 320 its
   GDTR (LGDT's operand), then its GDT at 256 and its TSS at 384.

   pax_cpu_self() -> u64   %gs:0, this CPU's record.
   pax_ap_hold             where Limine sends an application processor
                           at the kernel's entry (its MP feature:
                           `goto_address`, with %rdi its `struct
                           limine_mp_info`, on Limine's tables and stack,
                           interrupts off): CLI, its hold words from
                           `extra_argument` (+24) in %rbx, an IDT of its
                           own on its stack with one gate, the NMI's (IST
                           0, the code segment it runs on), then HELD set
                           and HLT, for good. The NMI's handler
                           (pax_ap_hold_nmi) returns to the look at its
                           record (word 1), never into the loop: the
                           record is looked at only after an NMI, and
                           kernel/smp sends its one NMI only after it
                           stored the record and read HELD, so that NMI
                           is always taken here, on this gate, and none
                           is left to arrive once the processor has gone
                           on. No record yet: HLT again. With the record:
                           `extra_argument` = the record, and on to
                           pax_ap_entry, as if Limine had sent it there.
   pax_ap_park             CLI; HLT for good: an application processor PAX
                           will not run (`nosmp`, past kernel/smp's MAX),
                           until kernel/smp sends it INIT.
   pax_ap_entry            an application processor's way into PAX, with
                           %rdi its `struct limine_mp_info` (Limine's
                           tables and stack, interrupts off). The record
                           kernel/smp wrote into `extra_argument` (+24) is kept in
                           %rbx; PAX's tables load first (pax_ap_boot word
                           0: the kernel's PML4) and at once the record's
                           stack (Limine's stack need not be mapped in
                           PAX's tables), then the record's GDT (CS 0x08 by
                           a far return, the data selectors 0x10), its TSS
                           (LTR 0x28), the one IDT (pax_idtr), GS_BASE the
                           record and KERNEL_GS_BASE 0, and then the wolf
                           routine whose address pax_ap_boot word 1 holds
                           (kernel/smp's pax_ap_main, given the record),
                           which never returns. No wolf symbol is named
                           here, so a kernel without kernel/smp links as
                           before.
   pax_ap_halt()           STI; HLT; CLI; RET: an application processor's
                           idle, until its next interrupt (its tick).

   Written from: the Limine protocol (PROTOCOL.md at 3a0526b7, the MP
   feature: goto_address, extra_argument, %rdi, the machine state as at
   the entry); the Intel SDM vol. 2 (SWAPGS, RDMSR, WRMSR, LGDT, LTR,
   LIDT, MOV to CR3, HLT, STI's shadow, IRETQ), vol. 3A §6.7.1 and §6.14.1
   (the NMI's blocking, a 64-bit interrupt gate), §2.5 and §4.10.4.1
   (CR3), §3.4.4 and §5.8.8 (FS and GS bases in 64-bit mode, the SYSCALL
   window), vol. 4 (IA32_GS_BASE 0xC0000101, IA32_KERNEL_GS_BASE
   0xC0000102). No Linux source; no other kernel's source. */
        .globl pax_cpu_self
        .type pax_cpu_self, @function
pax_cpu_self:
        .byte   0x65, 0x48, 0x8b, 0x04, 0x25, 0x00, 0x00, 0x00, 0x00 /* movq    %gs:0, %rax */
        ret
        .size pax_cpu_self, . - pax_cpu_self

        .globl pax_ap_entry
        .type pax_ap_entry, @function
pax_ap_entry:
        cli
        movq    24(%rdi), %rbx          /* extra_argument: this CPU's record */
        movq    pax_ap_boot(%rip), %rax /* the kernel's PML4 */
        movq    %rax, %cr3
        movq    96(%rbx), %rsp          /* the record's idle stack */
        lgdt    320(%rbx)
        movw    $0x10, %ax
        movw    %ax, %ds
        movw    %ax, %es
        movw    %ax, %ss
        movw    %ax, %fs
        movw    %ax, %gs
        leaq    1f(%rip), %rax
        pushq   $0x08
        pushq   %rax
        lretq                           /* CS = 0x08 */
1:      movw    $0x28, %ax
        ltr     %ax
        lidt    pax_idtr(%rip)
        movl    $0xc0000101, %ecx       /* IA32_GS_BASE: the record */
        movl    %ebx, %eax
        movq    %rbx, %rdx
        shrq    $32, %rdx
        wrmsr
        movl    $0xc0000102, %ecx       /* IA32_KERNEL_GS_BASE: 0 */
        xorl    %eax, %eax
        xorl    %edx, %edx
        wrmsr
        movq    %rbx, %rdi
        xorl    %ebp, %ebp
        pushq   $0                      /* no return address: the chain ends */
        movq    pax_ap_boot+8(%rip), %rax
        jmp     *%rax                   /* pax_ap_main(record), never back */
        .size pax_ap_entry, . - pax_ap_entry

        .globl pax_ap_hold
        .type pax_ap_hold, @function
pax_ap_hold:
        cli
        movq    24(%rdi), %rbx          /* extra_argument: its hold words */
        andq    $-16, %rsp
        subq    $64, %rsp               /* the IDT at 0 (3 gates), its IDTR at 48 */
        xorl    %eax, %eax
        movq    %rax, 0(%rsp)
        movq    %rax, 8(%rsp)
        movq    %rax, 16(%rsp)
        movq    %rax, 24(%rsp)
        movq    %rax, 32(%rsp)
        movq    %rax, 40(%rsp)
        leaq    pax_ap_hold_nmi(%rip), %rax
        movw    %ax, 32(%rsp)           /* gate 2: offset 15:0 */
        movw    %cs, %cx
        movw    %cx, 34(%rsp)           /* the code segment it runs on */
        movw    $0x8e00, 36(%rsp)       /* IST 0; present, DPL 0, interrupt gate */
        shrq    $16, %rax
        movw    %ax, 38(%rsp)           /* offset 31:16 */
        shrq    $16, %rax
        movl    %eax, 40(%rsp)          /* offset 63:32 */
        movw    $47, 48(%rsp)
        movq    %rsp, 50(%rsp)
        lidt    48(%rsp)
        movq    $1, (%rbx)              /* HELD: an NMI finds its gate now */
1:      hlt                             /* until an NMI: its handler returns below */
        jmp     1b
pax_ap_hold_look:                       /* reached from pax_ap_hold_nmi alone */
        movq    8(%rbx), %rax           /* its record, once kernel/smp wrote it */
        testq   %rax, %rax
        jz      1b
        movq    %rax, 24(%rdi)
        jmp     pax_ap_entry
        .size pax_ap_hold, . - pax_ap_hold

        .type pax_ap_hold_nmi, @function
pax_ap_hold_nmi:
        pushq   %rax
        leaq    pax_ap_hold_look(%rip), %rax
        movq    %rax, 8(%rsp)           /* the frame's RIP: back to the look */
        popq    %rax
        iretq
        .size pax_ap_hold_nmi, . - pax_ap_hold_nmi

        .globl pax_ap_park
        .type pax_ap_park, @function
pax_ap_park:
        cli
1:      hlt
        jmp     1b
        .size pax_ap_park, . - pax_ap_park

        .globl pax_ap_halt
        .type pax_ap_halt, @function
pax_ap_halt:
        sti
        hlt
        cli
        ret
        .size pax_ap_halt, . - pax_ap_halt


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

        .globl pax_msi_isr_table
pax_msi_isr_table:
        .quad pax_isr80, pax_isr81, pax_isr82, pax_isr83

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
        .globl pax_tick_count
pax_tick_count:
        .zero 8
        .globl pax_tick_delivered
pax_tick_delivered:
        .zero 8
        /* px161: CPU 0's record (kernel/percpu: 512 bytes, the offsets
           above; its GDT and TSS stay pax_gdt and pax_tss), and the words
           kernel/smp publishes before it releases an application processor
           and the words the processors share after (kernel/smp's header
           lists them), then the hold words of up to 64 processors. */
        .p2align 6
        .globl pax_cpu0
pax_cpu0:
        .zero 512
        .globl pax_ap_boot
pax_ap_boot:
        .zero 128
        .globl pax_ap_holds
pax_ap_holds:
        .zero 1024
        /* px131: kernel/latency's words (32): 0 on, 1 the open interval's
           TSC (0 none), 2 its RIP, 3 its vector or tag, 4 its number or
           slot, then kernel/latency's own, and 31 the address of its
           pax_lat_close, written before word 0 turns on: the paths here
           call it through that word, so the assembly names no wolf
           function and a kernel without kernel/latency links as before.
           Then its histogram (64 words, by the interval's TSC cycles'
           highest bit); the longest since the last read for each system
           call number (512), each vector (256) and each thread slot's
           irq_save sections (64). */
        .p2align 6
        .globl pax_lat
pax_lat:
        .zero 32 * 8
        .globl pax_lat_hist
pax_lat_hist:
        .zero 64 * 8
        .globl pax_lat_sys
pax_lat_sys:
        .zero 512 * 8
        .globl pax_lat_vec
pax_lat_vec:
        .zero 256 * 8
        .globl pax_lat_slot
pax_lat_slot:
        .zero 64 * 8
        .p2align 4
        .globl pax_ist1_stack
pax_ist1_stack:
        .zero 16384
        .globl pax_ist1_top
pax_ist1_top:
        /* px77d: IST2 for the NMI and IST3 for the machine check (kernel/idt),
           so either lands on a known stack whatever the interrupted code's
           (a bad stack, the window before a thread's, SYSRETQ's user stack). */
        .globl pax_ist2_stack
pax_ist2_stack:
        .zero 16384
        .globl pax_ist2_top
pax_ist2_top:
        .globl pax_ist3_stack
pax_ist3_stack:
        .zero 16384
        .globl pax_ist3_top
pax_ist3_top:
        /* px102: #DB can arrive after SYSCALL, before RSP has switched. */
        .globl pax_ist4_stack
pax_ist4_stack:
        .zero 16384
        .globl pax_ist4_top
pax_ist4_top:

        .section .note.GNU-stack, "", @progbits
