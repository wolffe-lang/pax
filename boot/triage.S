/* triage.S — the metal triage (px77d): numbered stripes, a fault screen
   and a halt that never reboots, all behind the command-line word
   `triage`.

   kasumi rebooted the moment Limine handed it PAX (px77). PAX's panic
   path halts, so a reboot is a triple fault (an exception before PAX's
   IDT is live, or one inside a handler) or a machine check with
   CR4.MCE clear (the SDM's shutdown). With `triage` on Limine's
   command line, boot/start.S calls `pax_triage_entry` before kmain:

   - it keeps Limine's CR3 (Limine's page tables are bootloader-
     reclaimable memory, which PAX never hands out: R-px76-4) and the
     first framebuffer Limine describes; every drawing below switches
     to Limine's CR3 and to a stack of its own in this image's .bss
     (mapped by Limine's tables and PAX's alike), so it draws the same
     before PAX's paging, between PAX's switch and kernel/fb's mapping,
     and after;
   - it loads a GDT of PAX's layout (code 0x08, data 0x10, TSS 0x28)
     with a TSS whose IST1 is a stack of its own, and an IDT of the 32
     exception gates, each on IST1, so a fault on a bad stack is still
     drawn (any other vector meets the IDT's limit: a #GP whose error
     code names it, SDM vol. 3A §6.13); and it sets CR4.MCE, so a machine check is drawn (vector
     0x12, with the banks) instead of shutting the machine down;
   - it reads what the firmware handed over (IA32_APIC_BASE, CR0, CR4,
     EFER, IA32_PAT, the MTRR default type, CPUID's signature, the
     framebuffer's physical address and shape, the memory map's size,
     IA32_MCG_CAP and STATUS and every machine-check bank that holds a
     valid error: a previous boot's machine check survives a warm
     reset) and draws them in a band at the bottom of the screen,
     which kernel/screen's console leaves alone in triage mode
     (`pax_triage_console_h`);
   - `pax_triage_stripe(n)` (kernel/triage's `step`) draws box n of the
     band, coloured and numbered in hex, and redraws every box reached
     before it, so each early step's box stays on screen; with `slow`
     on the command line each box is held about a second;
   - every exception through the triage IDT, and in triage mode every
     fatal exception kernel/interrupts reports (`pax_triage_fatal`),
     draws the vector, error code, RIP, CR2, RSP, CR3, CR4, CS, RFLAGS
     and the last step in large hex over the console and halts with
     interrupts off, forever; `pax_triage_stop(n)` (the command line's
     `stop=N`) halts the same way at step N, by design.

   Without `triage` the entry returns at once and nothing here runs:
   the normal boot is unchanged. kernel/gdt and kernel/idt replace the
   triage tables at interrupts.start, as in every boot.

   Mnemonics are those the other boot .S files already use (clef's set, tests/kernel-as
   K5); no division and no shift by %cl.

   Written from: the Intel SDM vol. 3A §2.5 (CR4.MCE), §3.4.5 and §7.2
   (the code, data and TSS descriptors, the 64-bit TSS and its IST),
   §6.10-6.14 (the IDT, 64-bit interrupt gates, the IST, the frame an
   exception pushes, which exceptions push an error code), ch. 15 (the
   machine-check architecture: IA32_MCG_CAP 0x179, IA32_MCG_STATUS
   0x17A, IA32_MCi_STATUS 0x401 + 4i and IA32_MCi_ADDR 0x402 + 4i, the
   VAL and ADDRV bits, the shutdown with CR4.MCE clear), §11.11 and
   §11.12 (IA32_MTRR_DEF_TYPE 0x2FF, IA32_PAT 0x277); vol. 2 (CPUID
   leaves 0, 1 and 16H, RDMSR, RDTSC, LGDT, LIDT, LTR, MOV CR);
   Limine's PROTOCOL.md (the executable command line, framebuffer and
   HHDM responses' layouts). No Linux source; no other kernel's,
   firmware's or bootloader's source. */

        .set STEPS,     64

        .text

/* --- entry --------------------------------------------------------------- */

/* pax_triage_word(w: *u8) -> u64: 1 when the NUL-ended word w is a
   space-separated word of Limine's executable command line. */
        .globl pax_triage_word
        .type pax_triage_word, @function
pax_triage_word:
        movq    limine_executable_cmdline_request+40(%rip), %rax
        testq   %rax, %rax
        jz      9f
        movq    8(%rax), %rsi
        testq   %rsi, %rsi
        jz      9f
        xorl    %ecx, %ecx              /* i */
        movl    $1, %edx                /* a word starts at i */
1:      cmpq    $4096, %rcx
        jae     9f
        movzbl  (%rsi,%rcx), %eax
        testl   %eax, %eax
        jz      9f
        cmpl    $32, %eax
        je      5f
        testl   %edx, %edx
        jz      4f
        xorl    %r8d, %r8d              /* k */
2:      movzbl  (%rdi,%r8), %r9d
        testl   %r9d, %r9d
        jz      3f
        movq    %rcx, %r10
        addq    %r8, %r10
        movzbl  (%rsi,%r10), %r11d
        cmpl    %r9d, %r11d
        jne     4f
        addq    $1, %r8
        jmp     2b
3:      movq    %rcx, %r10              /* the word matched: its end? */
        addq    %r8, %r10
        movzbl  (%rsi,%r10), %r11d
        testl   %r11d, %r11d
        jz      8f
        cmpl    $32, %r11d
        je      8f
4:      xorl    %edx, %edx
        addq    $1, %rcx
        jmp     1b
5:      movl    $1, %edx
        addq    $1, %rcx
        jmp     1b
8:      movl    $1, %eax
        ret
9:      xorl    %eax, %eax
        ret
        .size pax_triage_word, . - pax_triage_word

/* pax_triage_entry(): boot/start.S, before kmain. Returns at once
   without `triage`. */
        .globl pax_triage_entry
        .type pax_triage_entry, @function
pax_triage_entry:
        pushq   %rbx
        pushq   %rbp
        pushq   %r12
        pushq   %r13
        pushq   %r14
        pushq   %r15
        leaq    word_triage(%rip), %rdi
        call    pax_triage_word
        testq   %rax, %rax
        jz      9f
        movl    $1, %eax
        movq    %rax, tg_on(%rip)
        leaq    word_slow(%rip), %rdi
        call    pax_triage_word
        movq    %rax, tg_slow(%rip)
        movq    %cr3, %rax
        movq    %rax, tg_cr3(%rip)
        call    t_tables                /* the IDT first: a fault below is drawn */
        call    t_fb_setup
        call    t_delay_setup
        call    t_facts
        call    t_panel
        movl    $1, %edi
        call    pax_triage_stripe
9:      popq    %r15
        popq    %r14
        popq    %r13
        popq    %r12
        popq    %rbp
        popq    %rbx
        ret
        .size pax_triage_entry, . - pax_triage_entry

/* pax_triage_enabled() -> u64: 1 in triage mode. */
        .globl pax_triage_enabled
        .type pax_triage_enabled, @function
pax_triage_enabled:
        movq    tg_on(%rip), %rax
        ret
        .size pax_triage_enabled, . - pax_triage_enabled

/* pax_triage_console_h(h) -> u64: the height kernel/screen's console may
   draw in: h, or in triage mode with a framebuffer the band's top. */
        .globl pax_triage_console_h
        .type pax_triage_console_h, @function
pax_triage_console_h:
        movq    %rdi, %rax
        cmpq    $0, tg_ok(%rip)
        je      1f
        movq    tg_band_y(%rip), %rcx
        cmpq    %rcx, %rax
        jb      1f
        movq    %rcx, %rax
1:      ret
        .size pax_triage_console_h, . - pax_triage_console_h

/* --- the tables ---------------------------------------------------------- */

t_tables:
        /* The TSS: IST1 at byte 36, the I/O map base past its 104 bytes. */
        leaq    tg_fstack_top(%rip), %rax
        movq    %rax, tg_tss+36(%rip)
        movl    $104, %eax
        movw    %ax, tg_tss+102(%rip)
        /* The GDT: PAX's layout (kernel/gdt), the TSS at 0x28. */
        xorl    %eax, %eax
        movq    %rax, tg_gdt(%rip)
        movabsq $0x00af9a000000ffff, %rax
        movq    %rax, tg_gdt+8(%rip)
        movabsq $0x00cf92000000ffff, %rax
        movq    %rax, tg_gdt+16(%rip)
        movabsq $0x00cff2000000ffff, %rax
        movq    %rax, tg_gdt+24(%rip)
        movabsq $0x00affa000000ffff, %rax
        movq    %rax, tg_gdt+32(%rip)
        leaq    tg_tss(%rip), %rdx      /* the TSS descriptor, limit 103, type 9 */
        movq    %rdx, %rax
        andq    $0xffffff, %rax
        shlq    $16, %rax
        orq     $103, %rax
        movabsq $0x0000890000000000, %rcx
        orq     %rcx, %rax
        movq    %rdx, %rcx
        shrq    $24, %rcx
        andq    $0xff, %rcx
        shlq    $56, %rcx
        orq     %rcx, %rax
        movq    %rax, tg_gdt+40(%rip)
        movq    %rdx, %rax
        shrq    $32, %rax
        movq    %rax, tg_gdt+48(%rip)
        movl    $55, %eax
        movw    %ax, tg_gdtr(%rip)
        leaq    tg_gdt(%rip), %rax
        movq    %rax, tg_gdtr+2(%rip)
        leaq    tg_gdtr(%rip), %rdi
        call    pax_load_gdt
        movl    $0x28, %edi
        call    pax_ltr
        /* The IDT: 32 interrupt gates, selector 0x08, IST1, DPL 0. */
        leaq    t_stub_table(%rip), %rsi
        leaq    tg_idt(%rip), %rdi
        xorl    %ecx, %ecx
1:      movq    (%rsi), %rdx            /* the stub's address */
        movq    %rdx, %rax
        andq    $0xffff, %rax
        movabsq $0x00008e0100080000, %r8
        orq     %r8, %rax
        movq    %rdx, %r8
        shrq    $16, %r8
        andq    $0xffff, %r8
        shlq    $48, %r8
        orq     %r8, %rax
        movq    %rax, (%rdi)
        movq    %rdx, %rax
        shrq    $32, %rax
        movq    %rax, 8(%rdi)
        addq    $8, %rsi
        addq    $16, %rdi
        addq    $1, %rcx
        cmpq    $32, %rcx
        jb      1b
        movl    $511, %eax
        movw    %ax, tg_idtr(%rip)
        leaq    tg_idt(%rip), %rax
        movq    %rax, tg_idtr+2(%rip)
        leaq    tg_idtr(%rip), %rdi
        call    pax_lidt
        movq    %cr4, %rax              /* CR4.MCE: a machine check is drawn */
        orq     $0x40, %rax
        movq    %rax, %cr4
        ret

/* --- the framebuffer ----------------------------------------------------- */

t_fb_setup:
        movq    limine_framebuffer_request+40(%rip), %rax
        testq   %rax, %rax
        jz      9f
        cmpq    $0, 8(%rax)             /* framebuffer_count */
        je      9f
        movq    16(%rax), %rax          /* framebuffers */
        testq   %rax, %rax
        jz      9f
        movq    (%rax), %rax            /* the first */
        testq   %rax, %rax
        jz      9f
        movq    (%rax), %rcx
        movq    %rcx, tg_fb(%rip)
        movq    8(%rax), %rcx
        movq    %rcx, tg_w(%rip)
        movq    16(%rax), %rcx
        movq    %rcx, tg_h(%rip)
        movq    24(%rax), %rcx
        movq    %rcx, tg_pitch(%rip)
        movzbl  32(%rax), %ecx          /* bpp, low byte */
        cmpl    $32, %ecx
        jne     9f
        movzbl  34(%rax), %ecx          /* memory model 1: RGB */
        cmpl    $1, %ecx
        jne     9f
        movzbl  36(%rax), %ecx          /* red shift: 16 xRGB, 0 xBGR */
        xorl    %edx, %edx
        cmpl    $0, %ecx
        jne     1f
        movl    $1, %edx
1:      movq    %rdx, tg_fmt(%rip)
        cmpq    $64, tg_w(%rip)
        jb      9f
        cmpq    $64, tg_h(%rip)
        jb      9f
        /* The physical address, for the panel: the HHDM's offset off. */
        movq    tg_fb(%rip), %rcx
        movq    limine_hhdm_request+40(%rip), %rax
        testq   %rax, %rax
        jz      2f
        subq    8(%rax), %rcx
2:      movq    %rcx, tg_fb_phys(%rip)
        /* ss: 2, or the largest s with s * 640 <= w. */
        movl    $2, %ecx
3:      movq    %rcx, %rax
        addq    $1, %rax
        movq    %rax, %rdx
        shlq    $9, %rdx                /* (s+1) * 512 */
        movq    %rax, %r8
        shlq    $7, %r8                 /* (s+1) * 128 */
        addq    %r8, %rdx               /* (s+1) * 640 */
        cmpq    tg_w(%rip), %rdx
        jae     4f
        movq    %rax, %rcx
        cmpq    $16, %rcx
        jb      3b
4:      movq    %rcx, tg_ss(%rip)
        /* The band: two rows of boxes (10 ss each) and nine panel lines
           (9 ss each), ss above, below and between: 103 ss. */
        movq    %rcx, %rax
        shlq    $6, %rax                /* 64 ss */
        movq    %rcx, %rdx
        shlq    $5, %rdx                /* 32 ss */
        addq    %rdx, %rax
        movq    %rcx, %rdx
        shlq    $3, %rdx                /* 8 ss */
        addq    %rdx, %rax              /* 104 ss */
        movq    tg_h(%rip), %rdx
        shrq    $1, %rdx
        cmpq    %rdx, %rax              /* at most half the screen */
        jb      5f
        movq    %rdx, %rax
5:      movq    tg_h(%rip), %rdx
        subq    %rax, %rdx
        movq    %rdx, tg_band_y(%rip)
        /* fs, the fault screen's scale: the largest f with f * 144 <= w
           and f * 117 <= band_y (24 columns of 6, 13 lines of 9). */
        movl    $1, %ecx
6:      movq    %rcx, %rax
        addq    $1, %rax
        movq    %rax, %rdx
        shlq    $7, %rdx
        movq    %rax, %r8
        shlq    $4, %r8
        addq    %r8, %rdx               /* (f+1) * 144 */
        cmpq    tg_w(%rip), %rdx
        jae     7f
        movq    %rax, %rdx
        shlq    $7, %rdx
        movq    %rax, %r8
        shlq    $3, %r8
        subq    %r8, %rdx
        subq    %rax, %rdx
        subq    %rax, %rdx
        subq    %rax, %rdx              /* (f+1) * 117 */
        cmpq    tg_band_y(%rip), %rdx
        jae     7f
        movq    %rax, %rcx
        cmpq    $64, %rcx
        jb      6b
7:      movq    %rcx, tg_fs(%rip)
        movl    $1, %eax
        movq    %rax, tg_ok(%rip)
9:      ret

/* --- timing -------------------------------------------------------------- */

t_delay_setup:
        pushq   %rbx
        xorl    %eax, %eax
        xorl    %ecx, %ecx
        cpuid
        movl    $3000, %r8d             /* MHz when CPUID does not say */
        cmpl    $0x16, %eax
        jb      1f
        movl    $0x16, %eax
        xorl    %ecx, %ecx
        cpuid
        andq    $0xffff, %rax
        testl   %eax, %eax
        jz      1f
        movl    %eax, %r8d
1:      movq    %r8, %rax
        shlq    $20, %rax               /* about a second of TSC */
        movq    %rax, tg_delay(%rip)
        popq    %rbx
        ret

t_delay:
        rdtsc
        shlq    $32, %rdx
        movl    %eax, %eax
        orq     %rdx, %rax
        movq    %rax, %rcx
        addq    tg_delay(%rip), %rcx
1:      pause
        rdtsc
        shlq    $32, %rdx
        movl    %eax, %eax
        orq     %rdx, %rax
        cmpq    %rcx, %rax
        jb      1b
        ret

/* --- what the firmware handed over --------------------------------------- */

t_facts:
        pushq   %rbx
        movl    $0x1b, %ecx
        rdmsr
        shlq    $32, %rdx
        movl    %eax, %eax
        orq     %rdx, %rax
        movq    %rax, tg_e_apic(%rip)
        movq    %cr0, %rax
        movq    %rax, tg_e_cr0(%rip)
        movq    %cr4, %rax
        movq    %rax, tg_e_cr4(%rip)
        movl    $0xc0000080, %ecx
        rdmsr
        movl    %eax, %eax
        movq    %rax, tg_e_efer(%rip)
        movl    $1, %eax
        xorl    %ecx, %ecx
        cpuid
        movl    %eax, %eax
        movq    %rax, tg_e_sig(%rip)
        movl    %edx, %ebx              /* CPUID.1:EDX */
        testl   $0x10000, %ebx          /* PAT */
        jz      1f
        movl    $0x277, %ecx
        rdmsr
        shlq    $32, %rdx
        movl    %eax, %eax
        orq     %rdx, %rax
        movq    %rax, tg_e_pat(%rip)
1:      testl   $0x1000, %ebx           /* MTRR */
        jz      2f
        movl    $0x2ff, %ecx
        rdmsr
        movl    %eax, %eax
        movq    %rax, tg_e_mtrr(%rip)
2:      testl   $0x4000, %ebx           /* MCA */
        jz      3f
        movl    $0x179, %ecx
        rdmsr
        movl    %eax, %eax
        movq    %rax, tg_e_mcgcap(%rip)
        movl    $0x17a, %ecx
        rdmsr
        movl    %eax, %eax
        movq    %rax, tg_e_mcgst(%rip)
3:      movq    limine_memmap_request+40(%rip), %rax
        testq   %rax, %rax
        jz      4f
        movq    8(%rax), %rax
        movq    %rax, tg_e_mmap(%rip)
4:      popq    %rbx
        ret

/* --- drawing ------------------------------------------------------------- */

/* t_pix(rgb: edi) -> eax: the pixel for 0xRRGGBB in the framebuffer's
   layout (xRGB, or xBGR with red at shift 0). */
t_pix:
        movl    %edi, %eax
        cmpq    $0, tg_fmt(%rip)
        je      1f
        movl    %edi, %ecx
        andq    $0xff, %rcx
        shlq    $16, %rcx
        movl    %edi, %edx
        shrq    $16, %rdx
        andq    $0xff, %rdx
        andq    $0x00ff00, %rax
        orq     %rcx, %rax
        orq     %rdx, %rax
1:      ret

/* t_fill(x, y, w, h, pixel): a rectangle, clipped to the framebuffer. */
t_fill:
        movq    tg_w(%rip), %rax
        cmpq    %rax, %rdi
        jae     9f
        movq    %rdi, %r9
        addq    %rdx, %r9
        cmpq    %r9, %rax
        jae     1f
        movq    %rax, %rdx
        subq    %rdi, %rdx
1:      movq    tg_h(%rip), %rax
        cmpq    %rax, %rsi
        jae     9f
        movq    %rsi, %r9
        addq    %rcx, %r9
        cmpq    %r9, %rax
        jae     2f
        movq    %rax, %rcx
        subq    %rsi, %rcx
2:      testq   %rdx, %rdx
        jz      9f
        testq   %rcx, %rcx
        jz      9f
        movq    tg_fb(%rip), %r10
        movq    tg_pitch(%rip), %rax
        movq    %rsi, %r11
3:      testq   %r11, %r11
        jz      4f
        addq    %rax, %r10
        subq    $1, %r11
        jmp     3b
4:      movq    %rdi, %r11
        shlq    $2, %r11
        addq    %r11, %r10
5:      movq    %r10, %r11
        movq    %rdx, %r9
6:      movl    %r8d, (%r11)
        addq    $4, %r11
        subq    $1, %r9
        jnz     6b
        addq    %rax, %r10
        subq    $1, %rcx
        jnz     5b
9:      ret

/* t_char(c: edi): one glyph at the pen (tg_px, tg_py), scale tg_ps,
   foreground tg_pfg, background tg_pbg; the pen moves 6 * ps right. */
t_char:
        cmpq    $0, tg_ok(%rip)
        jne     0f
        ret
0:      pushq   %rbx
        pushq   %rbp
        pushq   %r12
        pushq   %r13
        pushq   %r14
        pushq   %r15
        cmpl    $0x61, %edi             /* a-z drawn as A-Z */
        jb      1f
        cmpl    $0x7b, %edi
        jae     1f
        subq    $0x20, %rdi
1:      cmpl    $0x20, %edi
        jb      2f
        cmpl    $0x60, %edi
        jb      3f
2:      movl    $0x3f, %edi             /* '?' */
3:      movl    %edi, %eax
        subq    $0x20, %rax
        movq    %rax, %rcx
        shlq    $3, %rax
        subq    %rcx, %rax              /* index * 7 */
        leaq    pax_triage_font(%rip), %r12
        addq    %rax, %r12
        /* The cell's background: 6 ps by 9 ps. */
        movq    tg_ps(%rip), %rcx
        movq    %rcx, %rdx
        shlq    $2, %rdx
        addq    %rcx, %rdx
        addq    %rcx, %rdx              /* 6 ps */
        movq    %rcx, %rax
        shlq    $3, %rax
        addq    %rax, %rcx              /* 9 ps */
        movq    tg_px(%rip), %rdi
        movq    tg_py(%rip), %rsi
        movq    tg_pbg(%rip), %r8
        call    t_fill
        movq    tg_py(%rip), %r14       /* y */
        movl    $7, %r13d               /* rows */
4:      movzbl  (%r12), %ebp            /* the row's bits */
        movq    tg_px(%rip), %r15       /* x */
        movl    $0x10, %ebx             /* the column's bit */
5:      testl   %ebx, %ebp
        jz      6f
        movq    %r15, %rdi
        movq    %r14, %rsi
        movq    tg_ps(%rip), %rdx
        movq    %rdx, %rcx
        movq    tg_pfg(%rip), %r8
        call    t_fill
6:      addq    tg_ps(%rip), %r15
        shrq    $1, %rbx
        testl   %ebx, %ebx
        jnz     5b
        addq    tg_ps(%rip), %r14
        addq    $1, %r12
        subq    $1, %r13
        jnz     4b
        movq    tg_ps(%rip), %rax
        movq    %rax, %rcx
        shlq    $2, %rax
        addq    %rcx, %rax
        addq    %rcx, %rax
        addq    %rax, tg_px(%rip)
        popq    %r15
        popq    %r14
        popq    %r13
        popq    %r12
        popq    %rbp
        popq    %rbx
        ret

/* t_str(s: *u8): a NUL-ended string at the pen. */
t_str:
        pushq   %r12
        movq    %rdi, %r12
1:      movzbl  (%r12), %edi
        testl   %edi, %edi
        jz      2f
        call    t_char
        addq    $1, %r12
        jmp     1b
2:      popq    %r12
        ret

/* t_hex(v, n): v's low n hex digits (n is 2, 4, 8 or 16) at the pen. */
t_hex:
        pushq   %r12
        pushq   %r13
        movq    %rdi, %r12
        movq    %rsi, %r13
        cmpq    $2, %rsi
        jne     1f
        shlq    $56, %r12
1:      cmpq    $4, %rsi
        jne     2f
        shlq    $48, %r12
2:      cmpq    $8, %rsi
        jne     3f
        shlq    $32, %r12
3:      movq    %r12, %rdi
        shrq    $60, %rdi
        cmpq    $10, %rdi
        jb      4f
        addq    $7, %rdi                /* 'A' - '0' - 10 */
4:      addq    $0x30, %rdi
        call    t_char
        shlq    $4, %r12
        subq    $1, %r13
        jnz     3b
        popq    %r13
        popq    %r12
        ret

/* t_nl(): the pen to the margin of the next line (9 ps down). */
t_nl:
        movq    tg_pmargin(%rip), %rax
        movq    %rax, tg_px(%rip)
        movq    tg_ps(%rip), %rax
        movq    %rax, %rcx
        shlq    $3, %rax
        addq    %rcx, %rax
        addq    %rax, tg_py(%rip)
        ret

/* t_pen(x, y, scale, fg rgb, bg rgb): set the pen; x is the margin. */
t_pen:
        movq    %rdi, tg_px(%rip)
        movq    %rdi, tg_pmargin(%rip)
        movq    %rsi, tg_py(%rip)
        movq    %rdx, tg_ps(%rip)
        movq    %r8, %r9
        movl    %ecx, %edi
        call    t_pix
        movq    %rax, tg_pfg(%rip)
        movl    %r9d, %edi
        call    t_pix
        movq    %rax, tg_pbg(%rip)
        ret

/* --- the band: boxes and the panel --------------------------------------- */

/* t_steps(): every box reached, from box 1 (a row of boxes 14 ss wide
   and 10 ss high, wrapping once). */
t_steps:
        cmpq    $0, tg_ok(%rip)
        jne     0f
        ret
0:      pushq   %rbx
        pushq   %r12
        pushq   %r13
        pushq   %r14
        pushq   %r15
        movq    tg_ss(%rip), %rax
        movq    %rax, %r14              /* box width: 14 ss */
        shlq    $4, %r14
        subq    %rax, %r14
        subq    %rax, %r14
        movq    %rax, %r15              /* box height: 10 ss */
        shlq    $3, %r15
        addq    %rax, %r15
        addq    %rax, %r15
        xorl    %r12d, %r12d            /* x */
        movq    tg_band_y(%rip), %r13   /* y */
        addq    %rax, %r13
        movl    $1, %ebx                /* k */
1:      leaq    tg_reached(%rip), %rax
        addq    %rbx, %rax
        movzbl  (%rax), %eax
        testl   %eax, %eax
        jz      2f
        leaq    box_colours(%rip), %rax
        movq    %rbx, %rcx
        andq    $7, %rcx
        shlq    $2, %rcx
        addq    %rcx, %rax
        movl    (%rax), %edi
        call    t_pix
        movq    %rax, %r8
        movq    %r12, %rdi
        movq    %r13, %rsi
        movq    %r14, %rdx
        subq    tg_ss(%rip), %rdx
        movq    %r15, %rcx
        subq    tg_ss(%rip), %rcx
        call    t_fill
        movq    %r12, %rdi              /* the number, black on the colour */
        addq    tg_ss(%rip), %rdi
        movq    %r13, %rsi
        addq    tg_ss(%rip), %rsi
        movq    tg_ss(%rip), %rdx
        leaq    box_colours(%rip), %rax
        movq    %rbx, %rcx
        andq    $7, %rcx
        shlq    $2, %rcx
        addq    %rcx, %rax
        movl    (%rax), %r8d
        xorl    %ecx, %ecx
        call    t_pen
        movq    %rbx, %rdi
        movl    $2, %esi
        call    t_hex
2:      addq    %r14, %r12
        movq    %r12, %rax
        addq    %r14, %rax
        cmpq    tg_w(%rip), %rax
        jb      3f
        xorl    %r12d, %r12d
        addq    %r15, %r13
3:      addq    $1, %rbx
        cmpq    $STEPS, %rbx
        jb      1b
        popq    %r15
        popq    %r14
        popq    %r13
        popq    %r12
        popq    %rbx
        ret

/* t_panel(): the handover's facts, nine lines under the boxes. */
t_panel:
        cmpq    $0, tg_ok(%rip)
        jne     0f
        ret
0:      pushq   %rbx
        pushq   %r12
        pushq   %r13
        /* The panel's area, black. */
        movq    tg_ss(%rip), %rax
        movq    %rax, %rsi
        shlq    $4, %rsi
        addq    %rax, %rsi
        addq    %rax, %rsi
        addq    %rax, %rsi              /* 21 ss: below the boxes */
        addq    tg_band_y(%rip), %rsi
        movq    %rsi, %r12              /* the panel's top */
        xorl    %edi, %edi
        call    t_pix
        movq    %rax, %r8
        xorl    %edi, %edi
        movq    %r12, %rsi
        movq    tg_w(%rip), %rdx
        movq    tg_h(%rip), %rcx
        subq    %r12, %rcx
        call    t_fill
        movq    tg_ss(%rip), %rdi
        movq    %r12, %rsi
        movq    tg_ss(%rip), %rdx
        movl    $0xd0d0d0, %ecx
        movl    $0x000000, %r8d
        call    t_pen
        leaq    s_apic(%rip), %rdi
        call    t_str
        movq    tg_e_apic(%rip), %rdi
        movl    $16, %esi
        call    t_hex
        leaq    s_cr0(%rip), %rdi
        call    t_str
        movq    tg_e_cr0(%rip), %rdi
        movl    $8, %esi
        call    t_hex
        leaq    s_cr4p(%rip), %rdi
        call    t_str
        movq    tg_e_cr4(%rip), %rdi
        movl    $8, %esi
        call    t_hex
        call    t_nl
        leaq    s_efer(%rip), %rdi
        call    t_str
        movq    tg_e_efer(%rip), %rdi
        movl    $8, %esi
        call    t_hex
        leaq    s_pat(%rip), %rdi
        call    t_str
        movq    tg_e_pat(%rip), %rdi
        movl    $16, %esi
        call    t_hex
        call    t_nl
        leaq    s_sig(%rip), %rdi
        call    t_str
        movq    tg_e_sig(%rip), %rdi
        movl    $8, %esi
        call    t_hex
        leaq    s_mtrr(%rip), %rdi
        call    t_str
        movq    tg_e_mtrr(%rip), %rdi
        movl    $4, %esi
        call    t_hex
        leaq    s_mm(%rip), %rdi
        call    t_str
        movq    tg_e_mmap(%rip), %rdi
        movl    $4, %esi
        call    t_hex
        call    t_nl
        leaq    s_fb(%rip), %rdi
        call    t_str
        movq    tg_fb_phys(%rip), %rdi
        movl    $16, %esi
        call    t_hex
        leaq    s_space(%rip), %rdi
        call    t_str
        movq    tg_w(%rip), %rdi
        movl    $4, %esi
        call    t_hex
        leaq    s_x(%rip), %rdi
        call    t_str
        movq    tg_h(%rip), %rdi
        movl    $4, %esi
        call    t_hex
        leaq    s_p(%rip), %rdi
        call    t_str
        movq    tg_pitch(%rip), %rdi
        movl    $4, %esi
        call    t_hex
        call    t_nl
        leaq    s_mcg(%rip), %rdi
        call    t_str
        movq    tg_e_mcgcap(%rip), %rdi
        movl    $8, %esi
        call    t_hex
        leaq    s_st(%rip), %rdi
        call    t_str
        movq    tg_e_mcgst(%rip), %rdi
        movl    $4, %esi
        call    t_hex
        call    t_nl
        movl    $4, %edi                /* at most four valid banks */
        call    t_banks
        popq    %r13
        popq    %r12
        popq    %rbx
        ret

/* t_banks(max: edi): one line per machine-check bank whose status is
   valid (bit 63), at most `max`: `MC nn status addr`; or `MC CLEAN`. */
t_banks:
        pushq   %rbx
        pushq   %r12
        pushq   %r13
        pushq   %r14
        movq    %rdi, %r14              /* lines left */
        xorl    %r13d, %r13d            /* lines drawn */
        movq    tg_e_mcgcap(%rip), %r12
        andq    $0xff, %r12             /* banks */
        cmpq    $32, %r12
        jb      0f
        movl    $32, %r12d
0:      xorl    %ebx, %ebx              /* bank */
1:      cmpq    %r12, %rbx
        jae     8f
        testq   %r14, %r14
        jz      8f
        movq    %rbx, %rcx
        shlq    $2, %rcx
        addq    $0x401, %rcx
        rdmsr
        shlq    $32, %rdx
        movl    %eax, %eax
        orq     %rdx, %rax
        movq    %rax, tg_mc_status(%rip)
        shrq    $63, %rax               /* VAL, bit 63 */
        testq   %rax, %rax
        jz      7f
        xorl    %eax, %eax
        movq    %rax, tg_mc_addr(%rip)
        movq    tg_mc_status(%rip), %rax
        shrq    $58, %rax               /* ADDRV, bit 58 */
        andq    $1, %rax
        testq   %rax, %rax
        jz      2f
        movq    %rbx, %rcx
        shlq    $2, %rcx
        addq    $0x402, %rcx
        rdmsr
        shlq    $32, %rdx
        movl    %eax, %eax
        orq     %rdx, %rax
        movq    %rax, tg_mc_addr(%rip)
2:      leaq    s_mc(%rip), %rdi
        call    t_str
        movq    %rbx, %rdi
        movl    $2, %esi
        call    t_hex
        leaq    s_space(%rip), %rdi
        call    t_str
        movq    tg_mc_status(%rip), %rdi
        movl    $16, %esi
        call    t_hex
        leaq    s_space(%rip), %rdi
        call    t_str
        movq    tg_mc_addr(%rip), %rdi
        movl    $16, %esi
        call    t_hex
        call    t_nl
        addq    $1, %r13
        subq    $1, %r14
7:      addq    $1, %rbx
        jmp     1b
8:      testq   %r13, %r13
        jnz     9f
        leaq    s_mc_clean(%rip), %rdi
        call    t_str
        call    t_nl
9:      popq    %r14
        popq    %r13
        popq    %r12
        popq    %rbx
        ret

/* --- stripes, stops and faults ------------------------------------------- */

/* pax_triage_stripe(n): box n (1-63) reached, the band redrawn; held a
   second with `slow`. Interrupts are off while it draws, on Limine's
   CR3 and the stripe stack; both are restored. */
        .globl pax_triage_stripe
        .type pax_triage_stripe, @function
pax_triage_stripe:
        cmpq    $0, tg_on(%rip)
        jne     0f
        ret
0:      pushfq
        popq    %rax
        movq    %rax, tg_saved_flags(%rip)
        cli
        cmpq    $STEPS, %rdi
        jae     1f
        movq    %rdi, tg_step(%rip)
        leaq    tg_reached(%rip), %rax
        addq    %rdi, %rax
        movl    $1, %ecx
        movb    %cl, (%rax)
1:      pushq   %rbx
        pushq   %rbp
        pushq   %r12
        pushq   %r13
        pushq   %r14
        pushq   %r15
        movq    %rsp, tg_saved_rsp(%rip)
        movq    %cr3, %rax
        movq    %rax, tg_saved_cr3(%rip)
        leaq    tg_stack_top(%rip), %rsp
        movq    tg_cr3(%rip), %rax
        movq    %rax, %cr3
        call    t_steps
        movq    tg_saved_cr3(%rip), %rax
        movq    %rax, %cr3
        movq    tg_saved_rsp(%rip), %rsp
        popq    %r15
        popq    %r14
        popq    %r13
        popq    %r12
        popq    %rbp
        popq    %rbx
        cmpq    $0, tg_slow(%rip)
        je      2f
        call    t_delay
2:      movq    tg_saved_flags(%rip), %rax
        testl   $0x200, %eax
        jz      3f
        sti
3:      ret
        .size pax_triage_stripe, . - pax_triage_stripe

/* pax_triage_stop(n): `stop=N` reached at step n: a green banner, then
   halt with interrupts off, forever. */
        .globl pax_triage_stop
        .type pax_triage_stop, @function
pax_triage_stop:
        cli
        movq    %rdi, tg_f_vec(%rip)
        leaq    tg_fstack_top(%rip), %rsp
        movq    tg_cr3(%rip), %rax
        movq    %rax, %cr3
        call    t_steps
        cmpq    $0, tg_ok(%rip)
        je      t_halt
        movl    $0x004000, %edi
        call    t_pix
        movq    %rax, %r8
        xorl    %edi, %edi
        xorl    %esi, %esi
        movq    tg_w(%rip), %rdx
        movq    tg_fs(%rip), %rcx
        shlq    $5, %rcx                /* 32 fs */
        call    t_fill
        movq    tg_fs(%rip), %rdi
        shlq    $1, %rdi
        movq    %rdi, %rsi
        movq    tg_fs(%rip), %rdx
        movl    $0xffffff, %ecx
        movl    $0x004000, %r8d
        call    t_pen
        leaq    s_stopped(%rip), %rdi
        call    t_str
        movq    tg_f_vec(%rip), %rdi
        movl    $2, %esi
        call    t_hex
        call    t_nl
        leaq    s_stop2(%rip), %rdi
        call    t_str
        jmp     t_halt
        .size pax_triage_stop, . - pax_triage_stop

/* pax_triage_halted(): kernel/panic's halt in triage mode: one line in
   the panel, `HALT AT STEP nn`, the console's text left as it is. */
        .globl pax_triage_halted
        .type pax_triage_halted, @function
pax_triage_halted:
        cmpq    $0, tg_on(%rip)
        jne     0f
        ret
0:      cli
        leaq    tg_fstack_top(%rip), %rsp
        movq    tg_cr3(%rip), %rax
        movq    %rax, %cr3
        call    t_steps
        cmpq    $0, tg_ok(%rip)
        je      t_halt
        movq    tg_ss(%rip), %rax       /* the panel's last line */
        movq    tg_h(%rip), %rsi
        movq    %rax, %rcx
        shlq    $3, %rcx
        addq    %rax, %rcx
        addq    %rax, %rcx              /* 10 ss */
        subq    %rcx, %rsi
        movq    tg_ss(%rip), %rdi
        movq    tg_ss(%rip), %rdx
        movl    $0x000000, %ecx
        movl    $0xffff55, %r8d
        call    t_pen
        leaq    s_halted(%rip), %rdi
        call    t_str
        movq    tg_step(%rip), %rdi
        movl    $2, %esi
        call    t_hex
        jmp     t_halt
        .size pax_triage_halted, . - pax_triage_halted

/* pax_triage_fatal(vector, error, rip, rsp, cr2, cs): kernel/interrupts'
   fatal exception in triage mode, drawn as the triage IDT's are. */
        .globl pax_triage_fatal
        .type pax_triage_fatal, @function
pax_triage_fatal:
        cli
        movq    %rdi, tg_f_vec(%rip)
        movq    %rsi, tg_f_err(%rip)
        movq    %rdx, tg_f_rip(%rip)
        movq    %rcx, tg_f_rsp(%rip)
        movq    %r8, tg_f_cr2(%rip)
        movq    %r9, tg_f_cs(%rip)
        pushfq
        popq    %rax
        movq    %rax, tg_f_rfl(%rip)
        movl    $1, %eax
        movq    %rax, tg_f_src(%rip)
        jmp     t_fault
        .size pax_triage_fatal, . - pax_triage_fatal

/* The triage IDT's common path, on IST1: vector at 0, error code at 8,
   then the frame the CPU pushed (RIP, CS, RFLAGS, RSP, SS). */
t_common:
        cli
        movq    0(%rsp), %rax
        movq    %rax, tg_f_vec(%rip)
        movq    8(%rsp), %rax
        movq    %rax, tg_f_err(%rip)
        movq    16(%rsp), %rax
        movq    %rax, tg_f_rip(%rip)
        movq    24(%rsp), %rax
        movq    %rax, tg_f_cs(%rip)
        movq    32(%rsp), %rax
        movq    %rax, tg_f_rfl(%rip)
        movq    40(%rsp), %rax
        movq    %rax, tg_f_rsp(%rip)
        movq    %cr2, %rax
        movq    %rax, tg_f_cr2(%rip)
        xorl    %eax, %eax
        movq    %rax, tg_f_src(%rip)
t_fault:
        cmpq    $0, tg_in_fault(%rip)   /* a fault while drawing one: halt */
        jne     t_halt
        movl    $1, %eax
        movq    %rax, tg_in_fault(%rip)
        movq    %cr3, %rax
        movq    %rax, tg_f_cr3(%rip)
        movq    %cr4, %rax
        movq    %rax, tg_f_cr4(%rip)
        leaq    tg_fstack_top(%rip), %rsp
        movq    tg_cr3(%rip), %rax
        movq    %rax, %cr3
        call    t_fault_screen
t_halt:
        cli
        hlt
        jmp     t_halt

/* t_fault_screen(): the fault in large hex over the console's area. */
t_fault_screen:
        cmpq    $0, tg_ok(%rip)
        jne     0f
        ret
0:      call    t_steps
        movl    $0x600000, %edi
        call    t_pix
        movq    %rax, %r8
        xorl    %edi, %edi
        xorl    %esi, %esi
        movq    tg_w(%rip), %rdx
        movq    tg_band_y(%rip), %rcx
        call    t_fill
        movq    tg_fs(%rip), %rdi
        shlq    $1, %rdi
        movq    %rdi, %rsi
        movq    tg_fs(%rip), %rdx
        movl    $0xffffff, %ecx
        movl    $0x600000, %r8d
        call    t_pen
        leaq    s_fault(%rip), %rdi
        call    t_str
        movq    tg_f_src(%rip), %rdi
        movl    $2, %esi
        call    t_hex
        call    t_nl
        leaq    s_step(%rip), %rdi
        call    t_str
        movq    tg_step(%rip), %rdi
        movl    $2, %esi
        call    t_hex
        leaq    s_vec(%rip), %rdi
        call    t_str
        movq    tg_f_vec(%rip), %rdi
        movl    $2, %esi
        call    t_hex
        call    t_nl
        leaq    s_err(%rip), %rdi
        call    t_str
        movq    tg_f_err(%rip), %rdi
        movl    $16, %esi
        call    t_hex
        call    t_nl
        leaq    s_rip(%rip), %rdi
        call    t_str
        movq    tg_f_rip(%rip), %rdi
        movl    $16, %esi
        call    t_hex
        call    t_nl
        leaq    s_cr2(%rip), %rdi
        call    t_str
        movq    tg_f_cr2(%rip), %rdi
        movl    $16, %esi
        call    t_hex
        call    t_nl
        leaq    s_rsp(%rip), %rdi
        call    t_str
        movq    tg_f_rsp(%rip), %rdi
        movl    $16, %esi
        call    t_hex
        call    t_nl
        leaq    s_cr3(%rip), %rdi
        call    t_str
        movq    tg_f_cr3(%rip), %rdi
        movl    $16, %esi
        call    t_hex
        call    t_nl
        leaq    s_cr4(%rip), %rdi
        call    t_str
        movq    tg_f_cr4(%rip), %rdi
        movl    $8, %esi
        call    t_hex
        leaq    s_cs(%rip), %rdi
        call    t_str
        movq    tg_f_cs(%rip), %rdi
        movl    $4, %esi
        call    t_hex
        call    t_nl
        leaq    s_flags(%rip), %rdi
        call    t_str
        movq    tg_f_rfl(%rip), %rdi
        movl    $8, %esi
        call    t_hex
        call    t_nl
        cmpq    $18, tg_f_vec(%rip)     /* a machine check: its banks */
        jne     9f
        movl    $3, %edi
        call    t_banks
9:      ret

/* --- the stubs ----------------------------------------------------------- */

/* One stub a vector: those the CPU gives no error code push a zero
   (SDM vol. 3A Table 6-1: 8, 10-14, 17, 21, 29 and 30 push one). */
        .p2align 4
t_stubs:
        .irp v, 0,1,2,3,4,5,6,7,9,15,16,18,19,20,22,23,24,25,26,27,28,31
t_stub\v:
        pushq   $0
        pushq   $\v
        jmp     t_common
        .endr
        .irp v, 8,10,11,12,13,14,17,21,29,30
t_stub\v:
        pushq   $\v
        jmp     t_common
        .endr

        .section .rodata
        .p2align 3
t_stub_table:
        .irp v, 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31
        .quad t_stub\v
        .endr

box_colours:                            /* 0xRRGGBB, by step & 7 */
        .long 0xffffff, 0xff5555, 0x55ff55, 0xffff55, 0x55ffff, 0xff55ff, 0xffaa00, 0x8888ff

word_triage:    .asciz "triage"
word_slow:      .asciz "slow"
s_apic:         .asciz "APIC "
s_cr0:          .asciz " CR0 "
s_cr4:          .asciz "CR4 "
s_cr4p:         .asciz " CR4 "
s_efer:         .asciz "EFER "
s_pat:          .asciz " PAT "
s_sig:          .asciz "CPUID "
s_mtrr:         .asciz " MTRR "
s_mm:           .asciz " MMAP "
s_fb:           .asciz "FB "
s_x:            .asciz "X"
s_p:            .asciz " PITCH "
s_mcg:          .asciz "MCG "
s_st:           .asciz " STATUS "
s_mc:           .asciz "MC "
s_mc_clean:     .asciz "MC BANKS CLEAN"
s_space:        .asciz " "
s_fault:        .asciz "PAX TRIAGE FAULT "
s_step:         .asciz "STEP "
s_vec:          .asciz "  VEC "
s_err:          .asciz "ERR "
s_rip:          .asciz "RIP "
s_cr2:          .asciz "CR2 "
s_rsp:          .asciz "RSP "
s_cr3:          .asciz "CR3 "
s_cs:           .asciz " CS "
s_flags:        .asciz "RFLAGS "
s_stopped:      .asciz "PAX TRIAGE STOP AT STEP "
s_stop2:        .asciz "STOP=N REACHED. HALTED."
s_halted:       .asciz "HALT AT STEP "

/* The triage font: 5x7 glyphs for ASCII 0x20-0x5f, a byte a row (bit 4
   the left column), seven rows a glyph (generated: notes/px77d/font.py). */
        .globl pax_triage_font
pax_triage_font:
        .byte 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00    /* ' ' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '!' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '"' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '#' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '$' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '%' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '&' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* "'" */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '(' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* ')' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '*' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '+' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* ',' */
        .byte 0x00, 0x00, 0x00, 0x1f, 0x00, 0x00, 0x00    /* '-' */
        .byte 0x00, 0x00, 0x00, 0x00, 0x00, 0x0c, 0x0c    /* '.' */
        .byte 0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10    /* '/' */
        .byte 0x0e, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0e    /* '0' */
        .byte 0x04, 0x0c, 0x04, 0x04, 0x04, 0x04, 0x0e    /* '1' */
        .byte 0x0e, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1f    /* '2' */
        .byte 0x1f, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0e    /* '3' */
        .byte 0x02, 0x06, 0x0a, 0x12, 0x1f, 0x02, 0x02    /* '4' */
        .byte 0x1f, 0x10, 0x1e, 0x01, 0x01, 0x11, 0x0e    /* '5' */
        .byte 0x06, 0x08, 0x10, 0x1e, 0x11, 0x11, 0x0e    /* '6' */
        .byte 0x1f, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08    /* '7' */
        .byte 0x0e, 0x11, 0x11, 0x0e, 0x11, 0x11, 0x0e    /* '8' */
        .byte 0x0e, 0x11, 0x11, 0x0f, 0x01, 0x02, 0x0c    /* '9' */
        .byte 0x00, 0x04, 0x04, 0x00, 0x04, 0x04, 0x00    /* ':' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* ';' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '<' */
        .byte 0x00, 0x00, 0x1f, 0x00, 0x1f, 0x00, 0x00    /* '=' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '>' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '?' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '@' */
        .byte 0x0e, 0x11, 0x11, 0x1f, 0x11, 0x11, 0x11    /* 'A' */
        .byte 0x1e, 0x11, 0x11, 0x1e, 0x11, 0x11, 0x1e    /* 'B' */
        .byte 0x0e, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0e    /* 'C' */
        .byte 0x1e, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1e    /* 'D' */
        .byte 0x1f, 0x10, 0x10, 0x1e, 0x10, 0x10, 0x1f    /* 'E' */
        .byte 0x1f, 0x10, 0x10, 0x1e, 0x10, 0x10, 0x10    /* 'F' */
        .byte 0x0e, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0f    /* 'G' */
        .byte 0x11, 0x11, 0x11, 0x1f, 0x11, 0x11, 0x11    /* 'H' */
        .byte 0x0e, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0e    /* 'I' */
        .byte 0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0c    /* 'J' */
        .byte 0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11    /* 'K' */
        .byte 0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1f    /* 'L' */
        .byte 0x11, 0x1b, 0x15, 0x15, 0x11, 0x11, 0x11    /* 'M' */
        .byte 0x11, 0x11, 0x19, 0x15, 0x13, 0x11, 0x11    /* 'N' */
        .byte 0x0e, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0e    /* 'O' */
        .byte 0x1e, 0x11, 0x11, 0x1e, 0x10, 0x10, 0x10    /* 'P' */
        .byte 0x0e, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0d    /* 'Q' */
        .byte 0x1e, 0x11, 0x11, 0x1e, 0x14, 0x12, 0x11    /* 'R' */
        .byte 0x0f, 0x10, 0x10, 0x0e, 0x01, 0x01, 0x1e    /* 'S' */
        .byte 0x1f, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04    /* 'T' */
        .byte 0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0e    /* 'U' */
        .byte 0x11, 0x11, 0x11, 0x11, 0x11, 0x0a, 0x04    /* 'V' */
        .byte 0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0a    /* 'W' */
        .byte 0x11, 0x11, 0x0a, 0x04, 0x0a, 0x11, 0x11    /* 'X' */
        .byte 0x11, 0x11, 0x0a, 0x04, 0x04, 0x04, 0x04    /* 'Y' */
        .byte 0x1f, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1f    /* 'Z' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '[' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '\\' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* ']' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '^' */
        .byte 0x1f, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1f    /* '_' */

/* --- state --------------------------------------------------------------- */

        .section .bss
        .p2align 3
        .globl pax_triage_on
pax_triage_on:
tg_on:          .zero 8
tg_slow:        .zero 8
tg_ok:          .zero 8
tg_cr3:         .zero 8
tg_fb:          .zero 8
tg_fb_phys:     .zero 8
tg_w:           .zero 8
tg_h:           .zero 8
tg_pitch:       .zero 8
tg_fmt:         .zero 8
tg_ss:          .zero 8
tg_fs:          .zero 8
tg_band_y:      .zero 8
tg_delay:       .zero 8
tg_step:        .zero 8
tg_px:          .zero 8
tg_py:          .zero 8
tg_ps:          .zero 8
tg_pfg:         .zero 8
tg_pbg:         .zero 8
tg_pmargin:     .zero 8
tg_saved_rsp:   .zero 8
tg_saved_cr3:   .zero 8
tg_saved_flags: .zero 8
tg_in_fault:    .zero 8
tg_f_vec:       .zero 8
tg_f_err:       .zero 8
tg_f_rip:       .zero 8
tg_f_cs:        .zero 8
tg_f_rfl:       .zero 8
tg_f_rsp:       .zero 8
tg_f_cr2:       .zero 8
tg_f_cr3:       .zero 8
tg_f_cr4:       .zero 8
tg_f_src:       .zero 8
tg_e_apic:      .zero 8
tg_e_cr0:       .zero 8
tg_e_cr4:       .zero 8
tg_e_efer:      .zero 8
tg_e_pat:       .zero 8
tg_e_mtrr:      .zero 8
tg_e_sig:       .zero 8
tg_e_mcgcap:    .zero 8
tg_e_mcgst:     .zero 8
tg_e_mmap:      .zero 8
tg_mc_status:   .zero 8
tg_mc_addr:     .zero 8
tg_reached:     .zero STEPS
        .p2align 4
tg_gdt:         .zero 56
tg_gdtr:        .zero 16
tg_tss:         .zero 112
tg_idtr:        .zero 16
        .p2align 12
tg_idt:         .zero 4096
        .p2align 4
tg_stack:       .zero 16384
tg_stack_top:
tg_fstack:      .zero 16384
tg_fstack_top:

        .section .note.GNU-stack, "", @progbits
