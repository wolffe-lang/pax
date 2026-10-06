/* sched.S — the scheduler's assembly (px07): the voluntary switch, a
   new thread's first instruction, the idle loop, the interrupt-flag
   routines the spinlock needs, and the thread table's storage.

   Listed under `asm` in kernel/wolf.pkg, so every routine whose `.globl`
   is written out is on wolf's roster ([abi.asm.roster]) and reached
   through a bodyless `extern "c" fn` (x86-64 SysV: arguments in %rdi,
   %rsi; the result in %rax). kernel/sched and kernel/sync name the
   storage with `extern "c" let`: module state holds scalars only
   ([mem.static.3]).

   A context switch is boot/isr.S's common path returning a different
   frame: `pax_interrupt` returns the address of the frame to resume, the
   common path moves it into %rsp, pops the fifteen registers, drops the
   vector and the error code and `iretq`s. A frame is saved where the
   CPU built it, on the interrupted thread's own stack: a kernel thread
   runs at CPL 0, an interrupt there changes no privilege, so the CPU
   neither switches stacks nor consults the TSS's RSP0, and in 64-bit
   mode it aligns %rsp to 16 and pushes SS, RSP, RFLAGS, CS and RIP
   unconditionally (Intel SDM vol. 3A §6.14.2; AMD64 APM vol. 2
   §8.9.3). `iretq` in 64-bit mode pops all five again whatever the
   privilege (SDM vol. 3A §6.14.3; vol. 2 IRET), so resuming any saved
   frame restores that thread's RSP with its RIP.

   pax_switch()          the VOLUNTARY switch (yield, sleep, exit,
                         wait_all): builds, in the caller's context, the
                         frame the CPU would have built for an interrupt
                         at the caller's return address — SS 0x10, the
                         RSP the caller has after the return, RFLAGS as
                         it was (then CLI), CS 0x08, RIP = the return
                         address, error 0, vector 0x81 (PAX_SWITCH: no
                         gate routes it, the CPU never raises it) — and
                         jumps into pax_isr_common, which saves the
                         registers and calls pax_interrupt like any
                         vector. Resumed, the caller returns from this
                         call with its RSP, its callee-saved registers
                         and its IF as they were; the C convention lets
                         the call clobber the rest. On entry %rsp is 8
                         mod 16 (the call pushed the return address);
                         after the pop it is 0 mod 16, and 7 + 15 pushed
                         words (176 bytes) leave the frame 16-aligned, as
                         the CPU's is.
   pax_thread_entry      a new thread's first instruction (kernel/sched
                         writes it as the first frame's RIP, with %r12 =
                         the body's address and %r13 its argument):
                         calls the body with the argument in %rdi, then
                         pax_thread_exit (kernel/sched; it never
                         returns). %rsp is the stack's 16-aligned top, so
                         the body is entered with %rsp 8 mod 16, as after
                         any call.
   pax_idle              the idle thread: HLT forever. Its frame's
                         RFLAGS has IF set, so each HLT ends at the next
                         interrupt (SDM vol. 2 HLT).
   pax_pause()           PAUSE (SDM vol. 2): a spin-wait hint; also an
                         opaque call, so a polling loop rereads memory.
   pax_irq_save()        RFLAGS (the caller's IF in bit 9), then CLI.
   pax_irq_restore(fl)   STI if bit 9 of fl is set; otherwise nothing.

   Storage (.bss, zero until kernel/sched writes it):
     pax_threads       16 thread records, 72 bytes each (kernel/sched's
                       #[repr(c)] Thread)
     pax_sched_locks   eight 8-byte lock words (kernel/sync; word 0 is
                       the console's)
     pax_sched_state   sixteen 8-byte words: the scheduler's scalars
                       (the current slot, the run queue's ends, …),
                       kept here and read volatile rather than in module
                       `var`s, which wolf 0.2.24 forwards across a call
                       that writes them (wolf-lang#598)

   Written from: the Intel SDM vol. 3A §6.8.1 (masking maskable
   interrupts: IF, CLI, STI), §6.12.1 (exception and interrupt handler
   procedures, the stack on a call through an interrupt gate), §6.14.2
   (the 64-bit mode stack frame), §6.14.3 (IRET in IA-32e mode); vol. 2
   (PUSHF, POPF, CLI, STI and its one-instruction shadow, HLT, PAUSE,
   IRET); the AMD64 APM vol. 2 §8.9.3 (interrupt stack frame in long
   mode) and §8.9.5 (IRET in long mode); the x86-64 psABI (alignment,
   the callee-saved registers). No Linux source; no other kernel's
   source. */

        .text
        .globl pax_switch
        .type pax_switch, @function
pax_switch:
        popq    %rcx                    /* the return address: RIP */
        movq    %rsp, %rax              /* the caller's RSP after the return */
        pushq   $0x10                   /* SS */
        pushq   %rax                    /* RSP */
        pushfq                          /* RFLAGS, the caller's IF */
        cli
        pushq   $0x08                   /* CS */
        pushq   %rcx                    /* RIP */
        pushq   $0                      /* error */
        pushq   $0x81                   /* vector: PAX_SWITCH */
        jmp     pax_isr_common
        .size pax_switch, . - pax_switch

        .globl pax_thread_entry
        .type pax_thread_entry, @function
pax_thread_entry:
        movq    %r13, %rdi              /* the argument */
        callq   *%r12                   /* the body */
        callq   pax_thread_exit         /* never returns */
        ud2
        .size pax_thread_entry, . - pax_thread_entry

        .globl pax_idle
        .type pax_idle, @function
pax_idle:
        hlt
        jmp     pax_idle
        .size pax_idle, . - pax_idle

        .globl pax_pause
        .type pax_pause, @function
pax_pause:
        pause
        ret
        .size pax_pause, . - pax_pause

        .globl pax_irq_save
        .type pax_irq_save, @function
pax_irq_save:
        pushfq
        popq    %rax
        cli
        ret
        .size pax_irq_save, . - pax_irq_save

        .globl pax_irq_restore
        .type pax_irq_restore, @function
pax_irq_restore:
        testl   $0x200, %edi
        jz      1f
        sti
1:      ret
        .size pax_irq_restore, . - pax_irq_restore

        .section .bss
        .p2align 6
        .globl pax_threads
pax_threads:
        .zero 16 * 72
        .p2align 6
        .globl pax_sched_locks
pax_sched_locks:
        .zero 64
        .p2align 6
        .globl pax_sched_state
pax_sched_state:
        .zero 128

        .section .note.GNU-stack, "", @progbits
