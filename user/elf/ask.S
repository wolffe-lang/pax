/* ask.S — px13's test program for the console: a static x86-64 Linux
   ELF with no libc, run unmodified on Linux (on a pseudo-terminal) and
   on PAX (on its console), whose transcripts must be identical.

   `ask` prompts `ask> ` on standard output, makes ONE read(0, buf, 256)
   and says what it got:

       ask: read <n> bytes: <the bytes>          (a newline added when
                                                  the bytes end without one)
       ask: end of input                         (read answered 0: exit 0)
       ask: read failed <-errno>                 (exit 1)

   so each prompt shows one read: in canonical mode one line (or what
   Ctrl-D handed over), with the line discipline's editing already done.

   `ask tty` first asks the terminal, then goes on as `ask`:
       ask: tcgets <rc> iflag 0x… oflag 0x… cflag 0x… lflag 0x… line <l> cc <19 bytes>
       ask: winsize <rc> rows <r> cols <c>
       ask: ioctl 0x5499 <rc>                    (a request no terminal
                                                  answers: -25, ENOTTY)
     then clears ECHO (TCSETS), prompts `secret> `, reads one line and
       ask: read <n> bytes without echo: <the bytes>
     then clears ICANON and ECHO with VMIN 1 (TCSETS), prompts `raw> `,
     reads ONE byte a call until a `q` (at most 32), and
       ask: raw bytes <hex> <hex> …
     then restores the settings it read (TCSETS) and says
       ask: restored <rc>

   Every line is built in a buffer and written with one write(2).

   Written from: the x86-64 psABI (§3.4.1, A.2.1), syscall_64.tbl
   (read 0, write 1, ioctl 16, exit_group 231), and the termios layout
   and request numbers measured black-box on Linux (notes/px13/: what
   TCGETS writes, strace's names for each bit). No libc; no Linux
   source. */

        .set SYS_READ, 0
        .set SYS_WRITE, 1
        .set SYS_IOCTL, 16
        .set SYS_EXIT_GROUP, 231
        .set TCGETS, 0x5401
        .set TCSETS, 0x5402
        .set TIOCGWINSZ, 0x5413
        .set BOGUS, 0x5499
        .set ICANON, 0x2
        .set ECHO, 0x8
        .set VMIN, 6

        .text
        .globl _start
        .type _start, @function
_start:
        movq    %rsp, %r15
        andq    $-16, %rsp
        cmpq    $2, (%r15)
        jne     .Lask
        movq    16(%r15), %rsi          /* argv[1] == "tty"? */
        cmpb    $'t', 0(%rsi)
        jne     .Lask
        cmpb    $'t', 1(%rsi)
        jne     .Lask
        cmpb    $'y', 2(%rsi)
        jne     .Lask
        cmpb    $0, 3(%rsi)
        jne     .Lask
        call    tty
.Lask:
        leaq    s_prompt(%rip), %rdi
        movl    $s_prompt_len, %esi
        call    say
        xorl    %edi, %edi
        leaq    inbuf(%rip), %rsi
        movl    $256, %edx
        movl    $SYS_READ, %eax
        syscall
        testq   %rax, %rax
        jz      .Leof
        js      .Lfail
        movq    %rax, %r12
        call    reset
        leaq    s_read(%rip), %rdi
        movl    $s_read_len, %esi
        call    cat
        movq    %r12, %rdi
        call    dec
        leaq    s_bytes(%rip), %rdi
        movl    $s_bytes_len, %esi
        call    cat
        leaq    inbuf(%rip), %rdi
        movq    %r12, %rsi
        call    cat
        leaq    inbuf(%rip), %rax
        cmpb    $10, -1(%rax,%r12)
        je      1f
        call    nl
1:      call    flush
        jmp     .Lask
.Leof:
        leaq    s_eof(%rip), %rdi
        movl    $s_eof_len, %esi
        call    say
        xorl    %edi, %edi
        jmp     quit
.Lfail:
        movq    %rax, %r12
        call    reset
        leaq    s_failed(%rip), %rdi
        movl    $s_failed_len, %esi
        call    cat
        movq    %r12, %rdi
        call    sdec
        call    nl
        call    flush
        movl    $1, %edi
        jmp     quit
        .size _start, . - _start

/* tty: the terminal's answers, no echo, raw bytes, restored. */
        .type tty, @function
tty:
        pushq   %rbx
        /* TCGETS into saved */
        xorl    %edi, %edi
        movl    $TCGETS, %esi
        leaq    saved(%rip), %rdx
        movl    $SYS_IOCTL, %eax
        syscall
        movq    %rax, %rbx
        call    reset
        leaq    s_tcgets(%rip), %rdi
        movl    $s_tcgets_len, %esi
        call    cat
        movq    %rbx, %rdi
        call    sdec
        leaq    s_iflag(%rip), %rdi
        movl    $s_iflag_len, %esi
        call    cat
        movl    saved+0(%rip), %edi
        call    hex
        leaq    s_oflag(%rip), %rdi
        movl    $s_oflag_len, %esi
        call    cat
        movl    saved+4(%rip), %edi
        call    hex
        leaq    s_cflag(%rip), %rdi
        movl    $s_cflag_len, %esi
        call    cat
        movl    saved+8(%rip), %edi
        call    hex
        leaq    s_lflag(%rip), %rdi
        movl    $s_lflag_len, %esi
        call    cat
        movl    saved+12(%rip), %edi
        call    hex
        leaq    s_line(%rip), %rdi
        movl    $s_line_len, %esi
        call    cat
        movzbl  saved+16(%rip), %edi
        call    dec
        leaq    s_cc(%rip), %rdi
        movl    $s_cc_len, %esi
        call    cat
        xorl    %ebx, %ebx
2:      movl    $' ', %edi
        call    ch
        leaq    saved+17(%rip), %rax
        movzbl  (%rax,%rbx), %edi
        call    hex2
        incl    %ebx
        cmpl    $19, %ebx
        jb      2b
        call    nl
        call    flush

        /* TIOCGWINSZ */
        xorl    %edi, %edi
        movl    $TIOCGWINSZ, %esi
        leaq    winsz(%rip), %rdx
        movl    $SYS_IOCTL, %eax
        syscall
        movq    %rax, %rbx
        call    reset
        leaq    s_winsz(%rip), %rdi
        movl    $s_winsz_len, %esi
        call    cat
        movq    %rbx, %rdi
        call    sdec
        leaq    s_rows(%rip), %rdi
        movl    $s_rows_len, %esi
        call    cat
        movzwl  winsz+0(%rip), %edi
        call    dec
        leaq    s_cols(%rip), %rdi
        movl    $s_cols_len, %esi
        call    cat
        movzwl  winsz+2(%rip), %edi
        call    dec
        call    nl
        call    flush

        /* a request no terminal answers */
        xorl    %edi, %edi
        movl    $BOGUS, %esi
        leaq    winsz(%rip), %rdx
        movl    $SYS_IOCTL, %eax
        syscall
        movq    %rax, %rbx
        call    reset
        leaq    s_bogus(%rip), %rdi
        movl    $s_bogus_len, %esi
        call    cat
        movq    %rbx, %rdi
        call    sdec
        call    nl
        call    flush

        /* no echo: a copy of saved with ECHO clear */
        call    copy
        andl    $~ECHO, work+12(%rip)
        call    set_work
        leaq    s_secret(%rip), %rdi
        movl    $s_secret_len, %esi
        call    say
        xorl    %edi, %edi
        leaq    inbuf(%rip), %rsi
        movl    $256, %edx
        movl    $SYS_READ, %eax
        syscall
        movq    %rax, %rbx
        call    reset
        leaq    s_read(%rip), %rdi
        movl    $s_read_len, %esi
        call    cat
        movq    %rbx, %rdi
        call    sdec
        leaq    s_noecho(%rip), %rdi
        movl    $s_noecho_len, %esi
        call    cat
        testq   %rbx, %rbx
        jle     3f
        leaq    inbuf(%rip), %rdi
        movq    %rbx, %rsi
        call    cat
        leaq    inbuf(%rip), %rax
        cmpb    $10, -1(%rax,%rbx)
        je      4f
3:      call    nl
4:      call    flush

        /* raw: ICANON and ECHO clear, VMIN 1, one byte a read */
        call    copy
        andl    $~(ICANON | ECHO), work+12(%rip)
        movb    $1, work+17+VMIN(%rip)
        call    set_work
        leaq    s_raw(%rip), %rdi
        movl    $s_raw_len, %esi
        call    say
        call    reset
        leaq    s_rawb(%rip), %rdi
        movl    $s_rawb_len, %esi
        call    cat
        xorl    %ebx, %ebx
5:      xorl    %edi, %edi
        leaq    inbuf(%rip), %rsi
        movl    $1, %edx
        movl    $SYS_READ, %eax
        syscall
        cmpq    $1, %rax
        jne     6f
        movl    $' ', %edi
        call    ch
        movzbl  inbuf(%rip), %edi
        call    hex2
        cmpb    $'q', inbuf(%rip)
        je      6f
        incl    %ebx
        cmpl    $32, %ebx
        jb      5b
6:      call    nl
        call    flush

        /* restore */
        xorl    %edi, %edi
        movl    $TCSETS, %esi
        leaq    saved(%rip), %rdx
        movl    $SYS_IOCTL, %eax
        syscall
        movq    %rax, %rbx
        call    reset
        leaq    s_restored(%rip), %rdi
        movl    $s_restored_len, %esi
        call    cat
        movq    %rbx, %rdi
        call    sdec
        call    nl
        call    flush
        popq    %rbx
        ret
        .size tty, . - tty

/* copy: work = saved (36 bytes) */
copy:
        leaq    saved(%rip), %rsi
        leaq    work(%rip), %rdi
        movl    $36, %ecx
        rep movsb
        ret

/* set_work: TCSETS(0, work) */
set_work:
        xorl    %edi, %edi
        movl    $TCSETS, %esi
        leaq    work(%rip), %rdx
        movl    $SYS_IOCTL, %eax
        syscall
        ret

/* --- the output line ---------------------------------------------- */

/* reset: empty the line */
reset:
        movq    $0, outlen(%rip)
        ret

/* cat(rdi = bytes, rsi = n): append */
cat:
        movq    outlen(%rip), %rax
        leaq    outbuf(%rip), %rdx
1:      testq   %rsi, %rsi
        jz      2f
        cmpq    $1000, %rax
        jae     2f
        movb    (%rdi), %cl
        movb    %cl, (%rdx,%rax)
        incq    %rax
        incq    %rdi
        decq    %rsi
        jmp     1b
2:      movq    %rax, outlen(%rip)
        ret

/* ch(edi = byte): append one */
ch:
        movq    outlen(%rip), %rax
        cmpq    $1000, %rax
        jae     1f
        leaq    outbuf(%rip), %rdx
        movb    %dil, (%rdx,%rax)
        incq    %rax
        movq    %rax, outlen(%rip)
1:      ret

nl:
        movl    $10, %edi
        jmp     ch

/* dec(rdi = unsigned): append in decimal */
dec:
        movq    %rdi, %rax
        leaq    digits+24(%rip), %r8
        xorl    %r9d, %r9d
        movl    $10, %ecx
1:      xorl    %edx, %edx
        divq    %rcx
        addb    $'0', %dl
        decq    %r8
        movb    %dl, (%r8)
        incq    %r9
        testq   %rax, %rax
        jnz     1b
        movq    %r8, %rdi
        movq    %r9, %rsi
        jmp     cat

/* sdec(rdi = signed): append in decimal, `-` first when negative */
sdec:
        testq   %rdi, %rdi
        jns     dec
        pushq   %rdi
        movl    $'-', %edi
        call    ch
        popq    %rdi
        negq    %rdi
        jmp     dec

/* hex(edi = 32 bits): `0x` and the digits, no leading zeros */
hex:
        pushq   %rbx
        movl    %edi, %ebx
        movl    $'0', %edi
        call    ch
        movl    $'x', %edi
        call    ch
        movl    $28, %ecx
        xorl    %r10d, %r10d            /* a digit written yet */
1:      movl    %ebx, %eax
        shrl    %cl, %eax
        andl    $15, %eax
        testl   %r10d, %r10d
        jnz     2f
        testl   %eax, %eax
        jnz     2f
        testl   %ecx, %ecx
        jnz     3f
2:      movl    $1, %r10d
        pushq   %rcx
        movl    %eax, %edi
        call    nib
        popq    %rcx
3:      subl    $4, %ecx
        jns     1b
        popq    %rbx
        ret

/* hex2(edi = byte): two hex digits */
hex2:
        pushq   %rdi
        shrl    $4, %edi
        andl    $15, %edi
        call    nib
        popq    %rdi
        andl    $15, %edi
        jmp     nib

/* nib(edi = 0..15): one hex digit */
nib:
        cmpl    $10, %edi
        jb      1f
        addl    $('a' - 10 - '0'), %edi
1:      addl    $'0', %edi
        jmp     ch

/* flush: write the line, one write(2) */
flush:
        movl    $1, %edi
        leaq    outbuf(%rip), %rsi
        movq    outlen(%rip), %rdx
        movl    $SYS_WRITE, %eax
        syscall
        ret

/* say(rdi = bytes, esi = n): write them as they are */
say:
        movq    %rsi, %rdx
        movq    %rdi, %rsi
        movl    $1, %edi
        movl    $SYS_WRITE, %eax
        syscall
        ret

/* quit(edi = status) */
quit:
        movl    $SYS_EXIT_GROUP, %eax
        syscall
        hlt

        .section .rodata
s_prompt:   .ascii "ask> "
        .set s_prompt_len, . - s_prompt
s_read:     .ascii "ask: read "
        .set s_read_len, . - s_read
s_bytes:    .ascii " bytes: "
        .set s_bytes_len, . - s_bytes
s_eof:      .ascii "ask: end of input\n"
        .set s_eof_len, . - s_eof
s_failed:   .ascii "ask: read failed "
        .set s_failed_len, . - s_failed
s_tcgets:   .ascii "ask: tcgets "
        .set s_tcgets_len, . - s_tcgets
s_iflag:    .ascii " iflag "
        .set s_iflag_len, . - s_iflag
s_oflag:    .ascii " oflag "
        .set s_oflag_len, . - s_oflag
s_cflag:    .ascii " cflag "
        .set s_cflag_len, . - s_cflag
s_lflag:    .ascii " lflag "
        .set s_lflag_len, . - s_lflag
s_line:     .ascii " line "
        .set s_line_len, . - s_line
s_cc:       .ascii " cc"
        .set s_cc_len, . - s_cc
s_winsz:    .ascii "ask: winsize "
        .set s_winsz_len, . - s_winsz
s_rows:     .ascii " rows "
        .set s_rows_len, . - s_rows
s_cols:     .ascii " cols "
        .set s_cols_len, . - s_cols
s_bogus:    .ascii "ask: ioctl 0x5499 "
        .set s_bogus_len, . - s_bogus
s_secret:   .ascii "secret> "
        .set s_secret_len, . - s_secret
s_noecho:   .ascii " bytes without echo: "
        .set s_noecho_len, . - s_noecho
s_raw:      .ascii "raw> "
        .set s_raw_len, . - s_raw
s_rawb:     .ascii "ask: raw bytes"
        .set s_rawb_len, . - s_rawb
s_restored: .ascii "ask: restored "
        .set s_restored_len, . - s_restored

        .bss
        .p2align 4
inbuf:      .zero 256
saved:      .zero 64
work:       .zero 64
winsz:      .zero 16
digits:     .zero 32
outlen:     .zero 8
outbuf:     .zero 1024

        .section .note.GNU-stack, "", @progbits
