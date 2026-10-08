/* programs.S — the first user programs (px09): flat, position-
   independent x86-64 blobs the kernel carries in its .rodata and copies,
   one per process, into fresh frames mapped at 0x400000 in that
   process's user half (kernel/user). Each starts executing at its first
   byte, in ring 3, with %rsp the top of a 16 KiB stack at 0x7ffffffff000
   and every other general register zero (boot/user.S's pax_enter_user).
   They reach their own bytes only RIP-relative, so the copy runs at any
   address; and since .rodata is mapped no-execute in the kernel's
   tables, none of this can run in ring 0 where it is linked.

   Why assembly and not wolf (argued in notes/px09-user-mode.md): wolf
   has no inline assembly (wolf-lang#526), so a wolf program still needs
   an assembly `syscall` shim; the fault cases need the exact faulting
   instruction (a `hlt`, a read of address 0); and the general ELF loader
   that a wolf-built program wants is px10's. These blobs test the
   kernel's ring-3 path and nothing else.

   System calls follow Linux's x86-64 ABI (the psABI's A.2.1, numbers
   from arch/x86/entry/syscalls/syscall_64.tbl): %rax the number, %rdi,
   %rsi, %rdx the first three arguments, `syscall`, the result in %rax,
   -4095..-1 an errno (EFAULT 14, ENOSYS 38 from the uapi errno headers).
   write is 1, _sysctl 156, exit 60; 156 must come back -38 (ENOSYS:
   the table names it sys_ni_syscall, so Linux answers ENOSYS too, and
   PAX never implements it), as must 500 (no such number). px09 used
   getpid (39) here; px14 implements getpid, so the witness moved.

     hello      write(1, "hello from ring 3: cpl ", 23); then the CPL,
                computed here as CS & 3 and written as a digit and a
                newline into two bytes of its own stack, write(1, sp, 2);
                _sysctl and 500, each expected -38; exit(0), or 1-4 naming
                the first expectation that failed
     segv       reads address 0 (nothing is mapped there): #PF, a user
                read of a page not present (error 0x4)
     kread      reads the kernel image at 0xffffffff80000000: present
                but supervisor (error 0x5)
     textwrite  writes its own first instruction: present, user, read-
                only (error 0x7)
     guard      writes 16 bytes below the stack's lowest page, into the
                guard page the kernel leaves unmapped (error 0x6)
     priv       `hlt` at CPL 3: #GP(0) (SDM vol. 2 HLT)
     badptr     write(1, p, 16) with p a kernel-half address, an unmapped
                user address (0x10), and the stack's top less 8 (8 bytes
                mapped, then the unmapped page above); exit(14) when all
                three returned -14 (EFAULT), exit(1) otherwise
     spin1, spin2
                write(1, "spinN: begin\n", 13); a mark of its own
                ("SPIN11" or "SPIN22") in %r12 and pushed on its own
                stack; 2^29 decrements of a register (no system call);
                then both marks checked: write(1, "spinN: end\n", 11)
                and exit(0) when both hold, exit(3) and no end line when
                either was lost — run at once, each preempted in ring 3
                and resumed many times, so a frame resumed in the wrong
                process (another's registers under its own CR3: the
                blobs share a layout) or a stack swapped under it shows

   pax_uprogs: the blobs' bounds, a [start, end) pair of addresses per
   blob, in the order kernel/user numbers them (0 hello … 7 spin1, 8
   spin2).

   Written from the Intel SDM vol. 2 (SYSCALL, HLT, MOV from a segment
   register), vol. 3A §4.7 (page-fault error codes), §6.15 (interrupt
   13, 14); the x86-64 psABI A.2.1; syscall_64.tbl and the uapi errno
   headers. No Linux source; no other kernel's source. */

        .section .rodata.pax_user, "a"
        .p2align 4

        .globl pax_uprog_hello
pax_uprog_hello:
        movl    $1, %eax                /* write */
        movl    $1, %edi                /* stdout */
        leaq    .Lhello_msg(%rip), %rsi
        movl    $(.Lhello_msg_end - .Lhello_msg), %edx
        syscall
        cmpq    $(.Lhello_msg_end - .Lhello_msg), %rax
        movl    $1, %edi
        jne     .Lhello_exit
        movw    %cs, %ax                /* CPL = CS's RPL */
        andl    $3, %eax
        addl    $0x30, %eax             /* '0' + CPL */
        subq    $16, %rsp
        movb    %al, (%rsp)
        movb    $10, 1(%rsp)            /* '\n' */
        movl    $1, %eax
        movl    $1, %edi
        movq    %rsp, %rsi
        movl    $2, %edx
        syscall
        cmpq    $2, %rax
        movl    $2, %edi
        jne     .Lhello_exit
        movl    $156, %eax              /* _sysctl: never implemented */
        syscall
        cmpq    $-38, %rax
        movl    $3, %edi
        jne     .Lhello_exit
        movl    $500, %eax              /* no such number */
        syscall
        cmpq    $-38, %rax
        movl    $4, %edi
        jne     .Lhello_exit
        xorl    %edi, %edi
.Lhello_exit:
        movl    $60, %eax               /* exit */
        syscall
        ud2
.Lhello_msg:
        .ascii  "hello from ring 3: cpl "
.Lhello_msg_end:
pax_uprog_hello_end:

        .p2align 4
pax_uprog_segv:
        movq    0x0, %rax               /* a read of address 0 */
        movl    $99, %edi
        movl    $60, %eax
        syscall
        ud2
pax_uprog_segv_end:

        .p2align 4
pax_uprog_kread:
        movabsq $0xffffffff80000000, %rbx
        movq    (%rbx), %rax            /* the kernel image */
        movl    $99, %edi
        movl    $60, %eax
        syscall
        ud2
pax_uprog_kread_end:

        .p2align 4
pax_uprog_textwrite:
        leaq    pax_uprog_textwrite(%rip), %rbx
        movq    $1, (%rbx)              /* its own code */
        movl    $99, %edi
        movl    $60, %eax
        syscall
        ud2
pax_uprog_textwrite_end:

        .p2align 4
pax_uprog_guard:
        movq    %rax, -16400(%rsp)      /* 16 bytes below the stack's 16 KiB */
        movl    $99, %edi
        movl    $60, %eax
        syscall
        ud2
pax_uprog_guard_end:

        .p2align 4
pax_uprog_priv:
        hlt
        movl    $99, %edi
        movl    $60, %eax
        syscall
        ud2
pax_uprog_priv_end:

        .p2align 4
pax_uprog_badptr:
        xorl    %r12d, %r12d            /* how many came back -EFAULT */
        movl    $1, %eax
        movl    $1, %edi
        movabsq $0xffffffff80000000, %rsi
        movl    $16, %edx
        syscall
        cmpq    $-14, %rax
        jne     1f
        incl    %r12d
1:      movl    $1, %eax
        movl    $1, %edi
        movl    $0x10, %esi
        movl    $16, %edx
        syscall
        cmpq    $-14, %rax
        jne     2f
        incl    %r12d
2:      movl    $1, %eax
        movl    $1, %edi
        leaq    -8(%rsp), %rsi          /* 8 bytes of stack, then unmapped */
        movl    $16, %edx
        syscall
        cmpq    $-14, %rax
        jne     3f
        incl    %r12d
3:      movl    $1, %edi
        cmpl    $3, %r12d
        jne     4f
        movl    $14, %edi
4:      movl    $60, %eax
        syscall
        ud2
pax_uprog_badptr_end:

        .p2align 4
pax_uprog_spin1:
        movl    $1, %eax
        movl    $1, %edi
        leaq    .Lspin1_begin(%rip), %rsi
        movl    $(.Lspin1_begin_end - .Lspin1_begin), %edx
        syscall
        movabsq $0x31314e495053, %r12   /* "SPIN11": this process's mark */
        pushq   %r12                    /* and on its own stack */
        movl    $0x20000000, %ebx       /* 2^29 */
1:      decq    %rbx
        jnz     1b
        movabsq $0x31314e495053, %rax
        movl    $3, %edi                /* a mark lost: exit 3, no end line */
        cmpq    %rax, %r12
        jne     2f
        cmpq    %rax, (%rsp)
        jne     2f
        movl    $1, %eax
        movl    $1, %edi
        leaq    .Lspin1_end(%rip), %rsi
        movl    $(.Lspin1_end_end - .Lspin1_end), %edx
        syscall
        xorl    %edi, %edi
2:      movl    $60, %eax
        syscall
        ud2
.Lspin1_begin:
        .ascii  "spin1: begin\n"
.Lspin1_begin_end:
.Lspin1_end:
        .ascii  "spin1: end\n"
.Lspin1_end_end:
pax_uprog_spin1_end:

        .p2align 4
pax_uprog_spin2:
        movl    $1, %eax
        movl    $1, %edi
        leaq    .Lspin2_begin(%rip), %rsi
        movl    $(.Lspin2_begin_end - .Lspin2_begin), %edx
        syscall
        movabsq $0x32324e495053, %r12   /* "SPIN22" */
        pushq   %r12
        movl    $0x20000000, %ebx
1:      decq    %rbx
        jnz     1b
        movabsq $0x32324e495053, %rax
        movl    $3, %edi
        cmpq    %rax, %r12
        jne     2f
        cmpq    %rax, (%rsp)
        jne     2f
        movl    $1, %eax
        movl    $1, %edi
        leaq    .Lspin2_end(%rip), %rsi
        movl    $(.Lspin2_end_end - .Lspin2_end), %edx
        syscall
        xorl    %edi, %edi
2:      movl    $60, %eax
        syscall
        ud2
.Lspin2_begin:
        .ascii  "spin2: begin\n"
.Lspin2_begin_end:
.Lspin2_end:
        .ascii  "spin2: end\n"
.Lspin2_end_end:
pax_uprog_spin2_end:

        .section .rodata
        .p2align 3
        .globl pax_uprogs
pax_uprogs:
        .quad   pax_uprog_hello, pax_uprog_hello_end
        .quad   pax_uprog_segv, pax_uprog_segv_end
        .quad   pax_uprog_kread, pax_uprog_kread_end
        .quad   pax_uprog_textwrite, pax_uprog_textwrite_end
        .quad   pax_uprog_guard, pax_uprog_guard_end
        .quad   pax_uprog_priv, pax_uprog_priv_end
        .quad   pax_uprog_badptr, pax_uprog_badptr_end
        .quad   pax_uprog_spin1, pax_uprog_spin1_end
        .quad   pax_uprog_spin2, pax_uprog_spin2_end

        .section .note.GNU-stack, "", @progbits
