/* hello.S — px10's test program: a static x86-64 Linux ELF with no libc,
   run unmodified on Linux and on PAX, whose output must be identical.

   Built three ways from this one source (tools/mkuser):
     hello      cc -nostdlib -static -no-pie        ET_EXEC, no PT_INTERP
     hello-pie  cc -nostdlib -static-pie            ET_DYN (PAX refuses: later)
     hello-dyn  cc -nostdlib -no-pie -Wl,-dynamic-linker,…  a PT_INTERP
   Every line it prints is built in a buffer and written with ONE
   write(2), so two processes printing at once never split a line.

   With no arguments past argv[0], or any that are not `spin K`, it
   checks what Linux's execve(2) hands a static program, per the x86-64
   psABI §3.4.1 (the initial process stack) and getauxval(3):
     argc 3 / argv[i] … / envp[j] …       the strings, in order
     AT_PAGESZ 4096, AT_PHENT 56          their values
     AT_PHNUM <n> ok                      = e_phnum of its own ELF header
                                            (__ehdr_start, which ld
                                            defines when the header is
                                            in a loaded segment)
     AT_PHDR ok                           = __ehdr_start + e_phoff
     AT_ENTRY ok                          = _start
     AT_RANDOM ok                         16 readable bytes
     rsp 16-aligned                       %rsp at _start
     rdx 0                                %rdx at _start (no exit fn)
     fcw 0x037f mxcsr 0x1f80              the x87 control word and
                                            MXCSR at _start (Linux's
                                            initial FPU state)
     data ok / bss ok / rodata ok         an initialised word; 64 KiB
                                            of zeroes past the file's
                                            bytes, then written; a
                                            read-only string
     xmm ok                               all sixteen xmm registers
                                            hold what was put in them
   and exits with exit_group(failures).

   `spin K` (K one digit): loads every xmm register with a pattern of
   its own (K in the top byte), spins 2^29 iterations with no system
   call (long enough to be preempted many times on a timer of ~100 Hz),
   checks all sixteen, prints `spin K: xmm ok` and exits 0, or `spin K:
   xmm BAD <reg>` and exits 1: two at once on one CPU prove that each
   process's FPU state is saved and restored with it (px10's
   FXSAVE/XSAVE per thread).

   Written from: the x86-64 psABI (§3.4.1, A.2.1: the system call
   convention, %rcx and %r11 clobbered), syscall_64.tbl (write 1,
   exit_group 231), include/uapi/linux/auxvec.h (the AT_* numbers),
   elf(5) and the gABI (the ELF header: e_phoff at 32, e_phnum at 56),
   the Intel SDM vol. 1 §8.1.5 and §10.2.3 (FNSTCW, STMXCSR, their
   initial values) and vol. 2 (MOVQ, PINSRQ-free SSE2 moves). No libc;
   no Linux source. */

        .set SYS_WRITE, 1
        .set SYS_EXIT_GROUP, 231
        .set AT_NULL, 0
        .set AT_PHDR, 3
        .set AT_PHENT, 4
        .set AT_PHNUM, 5
        .set AT_PAGESZ, 6
        .set AT_ENTRY, 9
        .set AT_RANDOM, 25
        .set BSS_BYTES, 65536
        .set SPINS, 0x20000000
        .set LINE_MAX, 256

        .text
        .globl _start
        .type _start, @function
_start:
        movq    %rsp, %r15              /* the initial stack: argc */
        movq    %rdx, %r14              /* %rdx at entry */
        fnstcw  fcw_at_entry(%rip)
        stmxcsr mxcsr_at_entry(%rip)
        andq    $-16, %rsp
        xorl    %r13d, %r13d            /* failures */

        /* argv[1] == "spin" and argv[2] one digit: the FPU test. */
        cmpq    $3, (%r15)
        jne     .Lchecks
        movq    16(%r15), %rsi
        leaq    s_spin(%rip), %rdi
        call    streq
        testl   %eax, %eax
        jz      .Lchecks
        movq    24(%r15), %rsi
        movzbl  (%rsi), %eax
        cmpb    $0, 1(%rsi)
        jne     .Lchecks
        subl    $0x30, %eax
        cmpl    $9, %eax
        ja      .Lchecks
        jmp     spin

.Lchecks:
        /* argc and argv */
        leaq    s_argc(%rip), %rsi
        call    put_str
        movq    (%r15), %rax
        call    put_dec
        call    flush
        movq    (%r15), %rbx            /* argc */
        xorl    %r12d, %r12d
1:      cmpq    %rbx, %r12
        jae     2f
        leaq    s_argv(%rip), %rsi
        call    put_str
        movq    %r12, %rax
        call    put_dec
        leaq    s_close(%rip), %rsi
        call    put_str
        movq    8(%r15,%r12,8), %rsi
        call    put_str
        call    flush
        incq    %r12
        jmp     1b
2:      leaq    16(%r15,%rbx,8), %rbx   /* envp: past argv and its NULL */
        cmpq    $0, -8(%rbx)
        je      3f
        leaq    s_argv_null(%rip), %rsi /* argv's NULL is missing */
        call    put_str
        call    flush
        incl    %r13d
3:      xorl    %r12d, %r12d
4:      movq    (%rbx,%r12,8), %rsi
        testq   %rsi, %rsi
        jz      5f
        pushq   %rsi
        pushq   %rsi
        leaq    s_envp(%rip), %rsi
        call    put_str
        movq    %r12, %rax
        call    put_dec
        leaq    s_close(%rip), %rsi
        call    put_str
        popq    %rsi
        popq    %rsi
        call    put_str
        call    flush
        incq    %r12
        jmp     4b
5:      leaq    8(%rbx,%r12,8), %rbx    /* auxv: past envp's NULL */

        /* the auxiliary vector: remember the entries checked */
        xorl    %eax, %eax
        movq    %rax, av_phdr(%rip)
        movq    %rax, av_phent(%rip)
        movq    %rax, av_phnum(%rip)
        movq    %rax, av_pagesz(%rip)
        movq    %rax, av_entry(%rip)
        movq    %rax, av_random(%rip)
6:      movq    (%rbx), %rax
        movq    8(%rbx), %rdx
        addq    $16, %rbx
        cmpq    $AT_NULL, %rax
        je      7f
        cmpq    $AT_PHDR, %rax
        jne     61f
        movq    %rdx, av_phdr(%rip)
61:     cmpq    $AT_PHENT, %rax
        jne     62f
        movq    %rdx, av_phent(%rip)
62:     cmpq    $AT_PHNUM, %rax
        jne     63f
        movq    %rdx, av_phnum(%rip)
63:     cmpq    $AT_PAGESZ, %rax
        jne     64f
        movq    %rdx, av_pagesz(%rip)
64:     cmpq    $AT_ENTRY, %rax
        jne     65f
        movq    %rdx, av_entry(%rip)
65:     cmpq    $AT_RANDOM, %rax
        jne     6b
        movq    %rdx, av_random(%rip)
        jmp     6b

7:      /* AT_PAGESZ, AT_PHENT: their values */
        leaq    s_pagesz(%rip), %rsi
        call    put_str
        movq    av_pagesz(%rip), %rax
        call    put_dec
        call    flush
        cmpq    $4096, av_pagesz(%rip)
        je      71f
        incl    %r13d
71:     leaq    s_phent(%rip), %rsi
        call    put_str
        movq    av_phent(%rip), %rax
        call    put_dec
        call    flush
        cmpq    $56, av_phent(%rip)
        je      72f
        incl    %r13d
72:     /* AT_PHNUM against e_phnum (each expected value in %rbx: the
           put_* helpers clobber %rdx) */
        leaq    __ehdr_start(%rip), %rcx
        movzwl  56(%rcx), %ebx
        leaq    s_phnum(%rip), %rsi
        call    put_str
        movq    av_phnum(%rip), %rax
        call    put_dec
        cmpq    %rbx, av_phnum(%rip)
        call    ok_or_bad
        call    flush
        /* AT_PHDR = __ehdr_start + e_phoff */
        leaq    __ehdr_start(%rip), %rcx
        movq    32(%rcx), %rbx
        addq    %rcx, %rbx
        leaq    s_phdr(%rip), %rsi
        call    put_str
        cmpq    %rbx, av_phdr(%rip)
        call    ok_or_bad
        call    flush
        /* AT_ENTRY = _start */
        leaq    _start(%rip), %rbx
        leaq    s_entry(%rip), %rsi
        call    put_str
        cmpq    %rbx, av_entry(%rip)
        call    ok_or_bad
        call    flush
        /* AT_RANDOM: 16 readable bytes */
        leaq    s_random(%rip), %rsi
        call    put_str
        movq    av_random(%rip), %rcx
        testq   %rcx, %rcx
        jnz     73f
        cmpq    $1, %rcx                /* absent: ZF clear, BAD */
        jmp     74f
73:     movq    (%rcx), %rax            /* both halves read: a fault */
        orq     8(%rcx), %rax           /* here is a missing page */
        cmpq    %rcx, %rcx              /* ZF: ok */
74:     call    ok_or_bad
        call    flush

        /* %rsp and %rdx at entry */
        testq   $15, %r15
        jnz     81f
        leaq    s_rsp_ok(%rip), %rsi
        jmp     82f
81:     leaq    s_rsp_bad(%rip), %rsi
        incl    %r13d
82:     call    put_str
        call    flush
        testq   %r14, %r14
        jnz     83f
        leaq    s_rdx_ok(%rip), %rsi
        jmp     84f
83:     leaq    s_rdx_bad(%rip), %rsi
        incl    %r13d
84:     call    put_str
        call    flush

        /* the FPU's state at entry */
        leaq    s_fcw(%rip), %rsi
        call    put_str
        movzwl  fcw_at_entry(%rip), %eax
        call    put_hex4
        leaq    s_mxcsr(%rip), %rsi
        call    put_str
        movl    mxcsr_at_entry(%rip), %eax
        call    put_hex4
        call    flush
        cmpw    $0x037f, fcw_at_entry(%rip)
        je      85f
        incl    %r13d
85:     cmpl    $0x1f80, mxcsr_at_entry(%rip)
        je      86f
        incl    %r13d
86:
        /* data: the initialised word, then written */
        leaq    s_data(%rip), %rsi
        call    put_str
        movabsq $0x44414f4c5f584150, %rax       /* "PAX_LOAD" */
        cmpq    %rax, magic(%rip)
        jne     91f
        incq    magic(%rip)
        incq    %rax
        cmpq    %rax, magic(%rip)
91:     call    ok_or_bad
        call    flush
        /* bss: 64 KiB of zeroes, then written */
        leaq    s_bss(%rip), %rsi
        call    put_str
        leaq    big(%rip), %rcx
        xorl    %eax, %eax
        movl    $(BSS_BYTES / 8), %edx
92:     orq     (%rcx), %rax
        movq    %rdx, (%rcx)
        addq    $8, %rcx
        decl    %edx
        jnz     92b
        testq   %rax, %rax
        call    ok_or_bad
        call    flush
        /* rodata: a known string */
        leaq    s_rodata(%rip), %rsi
        call    put_str
        movabsq $0x0074696c6976616d, %rax       /* "mavilit\0" */
        cmpq    %rax, s_known(%rip)
        call    ok_or_bad
        call    flush
        /* xmm: all sixteen hold what was put in them */
        movl    $0x58, %edi
        call    fill_xmm
        movl    $0x58, %edi
        call    check_xmm
        movl    %eax, %ebx
        leaq    s_xmm(%rip), %rsi
        call    put_str
        testl   %ebx, %ebx
        call    ok_or_bad
        call    flush

        movl    %r13d, %edi
        movl    $SYS_EXIT_GROUP, %eax
        syscall
        ud2
        .size _start, . - _start

/* spin: %eax = K (0-9). */
        .type spin, @function
spin:
        movl    %eax, %r12d
        movl    %r12d, %edi
        call    fill_xmm
        movl    $SPINS, %ecx
1:      decq    %rcx
        jnz     1b
        movl    %r12d, %edi
        call    check_xmm
        movl    %eax, %ebx              /* 0 ok, else 1 + the register */
        leaq    s_spin_line(%rip), %rsi
        call    put_str
        leal    0x30(%r12), %eax
        call    put_byte
        leaq    s_spin_xmm(%rip), %rsi
        call    put_str
        testl   %ebx, %ebx
        jnz     2f
        leaq    s_ok(%rip), %rsi
        call    put_str
        call    flush
        xorl    %edi, %edi
        jmp     3f
2:      leaq    s_bad_reg(%rip), %rsi
        call    put_str
        leal    -1(%rbx), %eax
        call    put_dec
        call    flush
        movl    $1, %edi
3:      movl    $SYS_EXIT_GROUP, %eax
        syscall
        ud2
        .size spin, . - spin

/* fill_xmm(%edi = tag): xmmN = (tag << 56 | N << 8 | 0xa5) in both
   halves, through the stack (SSE2 moves only). */
        .type fill_xmm, @function
fill_xmm:
        subq    $24, %rsp
        movq    %rdi, %rax
        shlq    $56, %rax
        orq     $0xa5, %rax
        .irp n, 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
        movq    %rax, %rdx
        orq     $(\n << 8), %rdx
        movq    %rdx, (%rsp)
        movq    %rdx, 8(%rsp)
        movdqu  (%rsp), %xmm\n
        .endr
        addq    $24, %rsp
        ret
        .size fill_xmm, . - fill_xmm

/* check_xmm(%edi = tag) -> %eax: 0 when every xmmN holds fill_xmm's
   value in both halves, else 1 + the first N that does not. */
        .type check_xmm, @function
check_xmm:
        subq    $24, %rsp
        movq    %rdi, %rax
        shlq    $56, %rax
        orq     $0xa5, %rax
        .irp n, 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
        movdqu  %xmm\n, (%rsp)
        movq    %rax, %rdx
        orq     $(\n << 8), %rdx
        cmpq    %rdx, (%rsp)
        jne     .Lxmm_bad\n
        cmpq    %rdx, 8(%rsp)
        jne     .Lxmm_bad\n
        .endr
        xorl    %eax, %eax
        addq    $24, %rsp
        ret
        .irp n, 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
.Lxmm_bad\n:
        movl    $(\n + 1), %eax
        addq    $24, %rsp
        ret
        .endr
        .size check_xmm, . - check_xmm

/* ok_or_bad: appends " ok" when ZF is set, else " BAD" (and counts a
   failure in %r13d). Preserves nothing but %r12-%r15, %rbx. */
        .type ok_or_bad, @function
ok_or_bad:
        jne     1f
        leaq    s_sp_ok(%rip), %rsi
        jmp     put_str
1:      incl    %r13d
        leaq    s_sp_bad(%rip), %rsi
        jmp     put_str
        .size ok_or_bad, . - ok_or_bad

/* streq(%rdi, %rsi) -> %eax 1 when the NUL-terminated strings match. */
        .type streq, @function
streq:
1:      movzbl  (%rdi), %eax
        cmpb    (%rsi), %al
        jne     2f
        testb   %al, %al
        jz      3f
        incq    %rdi
        incq    %rsi
        jmp     1b
2:      xorl    %eax, %eax
        ret
3:      movl    $1, %eax
        ret
        .size streq, . - streq

/* The line buffer: put_* append, flush writes it with one write(2) and
   a '\n', then empties it. Each clobbers %rax, %rcx, %rdx, %rsi, %rdi,
   %r8-%r11. */
        .type put_byte, @function
put_byte:                               /* %al */
        movq    line_len(%rip), %rcx
        cmpq    $(LINE_MAX - 2), %rcx
        jae     1f
        leaq    line(%rip), %rdi
        movb    %al, (%rdi,%rcx)
        incq    line_len(%rip)
1:      ret
        .size put_byte, . - put_byte

        .type put_str, @function
put_str:                                /* %rsi: NUL-terminated */
1:      movzbl  (%rsi), %eax
        testb   %al, %al
        jz      2f
        pushq   %rsi
        call    put_byte
        popq    %rsi
        incq    %rsi
        jmp     1b
2:      ret
        .size put_str, . - put_str

        .type put_dec, @function
put_dec:                                /* %rax, unsigned */
        subq    $40, %rsp
        leaq    32(%rsp), %rsi
        movb    $0, (%rsi)
        movl    $10, %ecx
1:      xorl    %edx, %edx
        divq    %rcx
        addb    $0x30, %dl
        decq    %rsi
        movb    %dl, (%rsi)
        testq   %rax, %rax
        jnz     1b
        call    put_str
        addq    $40, %rsp
        ret
        .size put_dec, . - put_dec

        .type put_hex4, @function
put_hex4:                               /* %ax as 0x and four hex digits */
        pushq   %rbx
        movl    %eax, %ebx
        movb    $0x30, %al
        call    put_byte
        movb    $0x78, %al
        call    put_byte
        movl    $12, %r8d
1:      movl    %ebx, %eax
        movl    %r8d, %ecx
        shrl    %cl, %eax
        andl    $15, %eax
        leaq    hexdigits(%rip), %rdx
        movzbl  (%rdx,%rax), %eax
        pushq   %r8
        call    put_byte
        popq    %r8
        subl    $4, %r8d
        jns     1b
        popq    %rbx
        ret
        .size put_hex4, . - put_hex4

        .type flush, @function
flush:
        movq    line_len(%rip), %rdx
        leaq    line(%rip), %rsi
        movb    $10, (%rsi,%rdx)
        incq    %rdx
        movl    $1, %edi
        movl    $SYS_WRITE, %eax
        syscall
        movq    $0, line_len(%rip)
        ret
        .size flush, . - flush

        .section .rodata
s_known:        .asciz "mavilit"
s_spin:         .asciz "spin"
s_argc:         .asciz "argc "
s_argv:         .asciz "argv["
s_envp:         .asciz "envp["
s_close:        .asciz "] "
s_argv_null:    .asciz "argv has no NULL"
s_pagesz:       .asciz "AT_PAGESZ "
s_phent:        .asciz "AT_PHENT "
s_phnum:        .asciz "AT_PHNUM "
s_phdr:         .asciz "AT_PHDR"
s_entry:        .asciz "AT_ENTRY"
s_random:       .asciz "AT_RANDOM"
s_rsp_ok:       .asciz "rsp 16-aligned"
s_rsp_bad:      .asciz "rsp misaligned"
s_rdx_ok:       .asciz "rdx 0"
s_rdx_bad:      .asciz "rdx not 0"
s_fcw:          .asciz "fcw "
s_mxcsr:        .asciz " mxcsr "
s_data:         .asciz "data"
s_bss:          .asciz "bss"
s_rodata:       .asciz "rodata"
s_xmm:          .asciz "xmm"
s_sp_ok:        .asciz " ok"
s_sp_bad:       .asciz " BAD"
s_spin_line:    .asciz "spin "
s_spin_xmm:     .asciz ": xmm"
s_ok:           .asciz " ok"
s_bad_reg:      .asciz " BAD xmm"
hexdigits:      .ascii "0123456789abcdef"

        .data
        .p2align 3
magic:          .quad 0x44414f4c5f584150        /* "PAX_LOAD" */

        .bss
        .p2align 12
big:            .zero BSS_BYTES
        .p2align 3
line_len:       .zero 8
av_phdr:        .zero 8
av_phent:       .zero 8
av_phnum:       .zero 8
av_pagesz:      .zero 8
av_entry:       .zero 8
av_random:      .zero 8
mxcsr_at_entry: .zero 4
fcw_at_entry:   .zero 2
        .p2align 3
line:           .zero LINE_MAX

        .section .note.GNU-stack, "", @progbits
