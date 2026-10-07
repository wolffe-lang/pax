/* cpu.S — the control registers, the EFER MSR and INVLPG, for wolf
   (px03, paging).

   Listed under `asm` in kernel/wolf.pkg, so these routines are on
   wolf's roster ([abi.asm.roster]) and the kernel reaches them through
   bodyless `extern "c" fn` declarations (x86-64 SysV: arguments in
   %rdi, %rsi; the result in %rax). wolf has no inline assembly (KWC
   kw13), and a move to or from a control register, RDMSR/WRMSR and
   INVLPG have no other spelling.

     pax_cr0() -> u64          MOV from CR0
     pax_cr2() -> u64          MOV from CR2: the linear address of the
                               last page fault (kw10, kernel/interrupts)
     pax_cr3() -> u64          MOV from CR3
     pax_cr4() -> u64          MOV from CR4
     pax_set_cr3(v: u64)       MOV to CR3: the switch to the paging
                               structures whose PML4 is at physical v
                               (bits 51:12; PCD and PWT clear), and a
                               flush of every non-global TLB entry
     pax_efer() -> u64         RDMSR of IA32_EFER (0xC0000080)
     pax_apic_base() -> u64    RDMSR of IA32_APIC_BASE (0x1B): the local
                               APIC's physical base in bits 51:12, its
                               global enable in bit 11 (kw10, kernel/apic)
     pax_set_efer(v: u64)      WRMSR of IA32_EFER (edx:eax = v)
     pax_invlpg(va: u64)       INVLPG va: drop the TLB entries for the
                               page holding va
     pax_cpuid_nx() -> u64     1 if CPUID 0x80000001 EDX bit 20 (the
                               execute-disable bit is supported), else 0
     pax_rsp() -> u64          the caller's stack pointer (the stack
                               must stay mapped across the switch)
     pax_rdmsr(msr) -> u64     RDMSR of any MSR (px09: STAR, LSTAR,
                               FMASK read back for the report)
     pax_wrmsr(msr, v)         WRMSR of any MSR (px09: EFER.SCE, STAR,
                               LSTAR, FMASK)
     pax_set_cr4(v: u64)       MOV to CR4 (px09: SMEP bit 20, SMAP bit 21)
     pax_cpuid7_ebx() -> u64   CPUID leaf 7 subleaf 0's EBX (SMEP is bit
                               7, SMAP bit 20), or 0 when the CPU's
                               highest basic leaf is below 7

   Each routine reads or writes exactly what it names. They run at CPL
   0 with interrupts off (Limine's entry state, docs/BOOT.md).

   Written from: the Intel 64 and IA-32 SDM vol. 2 (MOV to/from control
   registers, RDMSR, WRMSR, INVLPG, CPUID leaf 0x80000001), vol. 3A §2.5
   (control registers; kw10: CR2, the page-fault linear address), §2.2.1
   (IA32_EFER: SCE bit 0, LME 8, LMA 10, NXE 11), §4.10.4.1 (what MOV to
   CR3 and INVLPG invalidate), §11.4.4 (kw10: IA32_APIC_BASE); px09: §2.5
   (CR4.SMEP, CR4.SMAP), §4.6.1 (SMEP and SMAP), vol. 2 CPUID leaf 07H
   (EBX bits 7 and 20) and vol. 4 (the MSRs' addresses: STAR C0000081H,
   LSTAR C0000082H, FMASK C0000084H); the AMD64 APM vol. 2 §3.1.7 (EFER),
   §5.5 (TLB invalidation) and §6.1.1 (SYSCALL and SYSRET's MSRs); the
   x86-64 psABI. No Linux source; no other kernel's source. */

        .text

        .globl pax_cr0
        .type pax_cr0, @function
pax_cr0:
        movq    %cr0, %rax
        ret
        .size pax_cr0, . - pax_cr0

        .globl pax_cr2
        .type pax_cr2, @function
pax_cr2:
        movq    %cr2, %rax
        ret
        .size pax_cr2, . - pax_cr2

        .globl pax_cr3
        .type pax_cr3, @function
pax_cr3:
        movq    %cr3, %rax
        ret
        .size pax_cr3, . - pax_cr3

        .globl pax_cr4
        .type pax_cr4, @function
pax_cr4:
        movq    %cr4, %rax
        ret
        .size pax_cr4, . - pax_cr4

        .globl pax_set_cr3
        .type pax_set_cr3, @function
pax_set_cr3:
        movq    %rdi, %cr3
        ret
        .size pax_set_cr3, . - pax_set_cr3

        .globl pax_efer
        .type pax_efer, @function
pax_efer:
        movl    $0xc0000080, %ecx
        rdmsr
        shlq    $32, %rdx
        movl    %eax, %eax
        orq     %rdx, %rax
        ret
        .size pax_efer, . - pax_efer

        .globl pax_apic_base
        .type pax_apic_base, @function
pax_apic_base:
        movl    $0x1b, %ecx
        rdmsr
        shlq    $32, %rdx
        movl    %eax, %eax
        orq     %rdx, %rax
        ret
        .size pax_apic_base, . - pax_apic_base

        .globl pax_set_efer
        .type pax_set_efer, @function
pax_set_efer:
        movl    $0xc0000080, %ecx
        movq    %rdi, %rax
        movq    %rdi, %rdx
        shrq    $32, %rdx
        wrmsr
        ret
        .size pax_set_efer, . - pax_set_efer

        .globl pax_invlpg
        .type pax_invlpg, @function
pax_invlpg:
        invlpg  (%rdi)
        ret
        .size pax_invlpg, . - pax_invlpg

        .globl pax_cpuid_nx
        .type pax_cpuid_nx, @function
pax_cpuid_nx:
        pushq   %rbx                    /* CPUID writes %rbx, callee-saved */
        movl    $0x80000000, %eax
        cpuid
        xorl    %r8d, %r8d
        cmpl    $0x80000001, %eax
        jb      1f
        movl    $0x80000001, %eax
        cpuid
        btl     $20, %edx
        setc    %r8b
1:      movl    %r8d, %eax
        popq    %rbx
        ret
        .size pax_cpuid_nx, . - pax_cpuid_nx

        .globl pax_rsp
        .type pax_rsp, @function
pax_rsp:
        leaq    8(%rsp), %rax           /* the caller's %rsp, before the call pushed */
        ret
        .size pax_rsp, . - pax_rsp

        .globl pax_rdmsr
        .type pax_rdmsr, @function
pax_rdmsr:
        movl    %edi, %ecx
        rdmsr
        shlq    $32, %rdx
        movl    %eax, %eax
        orq     %rdx, %rax
        ret
        .size pax_rdmsr, . - pax_rdmsr

        .globl pax_wrmsr
        .type pax_wrmsr, @function
pax_wrmsr:
        movl    %edi, %ecx
        movq    %rsi, %rax
        movq    %rsi, %rdx
        shrq    $32, %rdx
        wrmsr
        ret
        .size pax_wrmsr, . - pax_wrmsr

        .globl pax_set_cr4
        .type pax_set_cr4, @function
pax_set_cr4:
        movq    %rdi, %cr4
        ret
        .size pax_set_cr4, . - pax_set_cr4

        .globl pax_cpuid7_ebx
        .type pax_cpuid7_ebx, @function
pax_cpuid7_ebx:
        pushq   %rbx                    /* CPUID writes %rbx, callee-saved */
        xorl    %eax, %eax
        cpuid                           /* EAX: the highest basic leaf */
        xorl    %r8d, %r8d
        cmpl    $7, %eax
        jb      1f
        movl    $7, %eax
        xorl    %ecx, %ecx              /* subleaf 0 */
        cpuid
        movl    %ebx, %r8d
1:      movl    %r8d, %eax
        popq    %rbx
        ret
        .size pax_cpuid7_ebx, . - pax_cpuid7_ebx

        .section .note.GNU-stack, "", @progbits
