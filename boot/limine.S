/* limine.S — Limine's responses, read for wolf (px01, M-PX1).

   Listed under `asm` in kernel/wolf.pkg, so these routines are on
   wolf's roster ([abi.asm.roster]) and the kernel reaches them through
   bodyless `extern "c" fn` declarations. The requests live in
   boot/start.S between the request markers; Limine writes each
   response pointer after the image is built (docs/BOOT.md clause 5), so
   wolf must not read them until it has volatile access (KWC kw07) and
   integer-to-pointer lowering (kw06). Here every routine loads the
   response pointer afresh from memory, follows it, and returns a plain
   integer in %rax (x86-64 SysV; arguments in %rdi, %rsi):

     pax_boot_revision_ok() -> int     1 if Limine zeroed the base
                                       revision tag's third word (it
                                       honoured revision 6), else 0
     pax_boot_str(which, i) -> int     byte i of the bootloader's name
                                       (which 0) or version (which 1),
                                       or -1 past its end, past 255, or
                                       with no response
     pax_boot_firmware() -> int        the firmware type (0 x86 BIOS,
                                       1 EFI32, 2 EFI64, 3 SBI), or -1
     pax_boot_hhdm() -> u64            the HHDM offset, or 0
     pax_boot_memmap_count() -> int    the memory map's entry count, or -1
     pax_boot_memmap(i, f) -> u64      entry i's base (f 0), length
                                       (f 1) or type (f 2); 0 when i or
                                       f is out of range or there is no
                                       response

   Written from: the Limine protocol (PROTOCOL.md, limine-protocol
   3a0526b7: the request/response layout, the Bootloader Info, Firmware
   Type, HHDM and Memory Map features, base revisions) and the x86-64
   psABI. No Linux source. */

        .set RESPONSE, 40               /* id[4], revision, then response */

        .text

        .globl pax_boot_revision_ok
        .type pax_boot_revision_ok, @function
pax_boot_revision_ok:
        xorl    %eax, %eax
        cmpq    $0, limine_base_revision+16(%rip)
        sete    %al
        ret
        .size pax_boot_revision_ok, . - pax_boot_revision_ok

        .globl pax_boot_str
        .type pax_boot_str, @function
pax_boot_str:
        movq    limine_bootloader_info_request+RESPONSE(%rip), %rax
        testq   %rax, %rax
        jz      9f
        movq    8(%rax), %rdx           /* name */
        testq   %rdi, %rdi
        jz      1f
        movq    16(%rax), %rdx          /* version */
1:      testq   %rdx, %rdx
        jz      9f
        cmpq    $255, %rsi
        ja      9f                      /* also every negative i */
        xorl    %ecx, %ecx
2:      movzbl  (%rdx,%rcx), %eax
        testl   %eax, %eax
        jz      9f                      /* the NUL comes before byte i */
        cmpq    %rsi, %rcx
        je      3f
        incq    %rcx
        jmp     2b
3:      ret
9:      movq    $-1, %rax
        ret
        .size pax_boot_str, . - pax_boot_str

        .globl pax_boot_firmware
        .type pax_boot_firmware, @function
pax_boot_firmware:
        movq    limine_firmware_type_request+RESPONSE(%rip), %rax
        testq   %rax, %rax
        jz      9f
        movq    8(%rax), %rax
        ret
9:      movq    $-1, %rax
        ret
        .size pax_boot_firmware, . - pax_boot_firmware

        .globl pax_boot_hhdm
        .type pax_boot_hhdm, @function
pax_boot_hhdm:
        movq    limine_hhdm_request+RESPONSE(%rip), %rax
        testq   %rax, %rax
        jz      9f
        movq    8(%rax), %rax
9:      ret
        .size pax_boot_hhdm, . - pax_boot_hhdm

        .globl pax_boot_memmap_count
        .type pax_boot_memmap_count, @function
pax_boot_memmap_count:
        movq    limine_memmap_request+RESPONSE(%rip), %rax
        testq   %rax, %rax
        jz      9f
        movq    8(%rax), %rax
        ret
9:      movq    $-1, %rax
        ret
        .size pax_boot_memmap_count, . - pax_boot_memmap_count

        .globl pax_boot_memmap
        .type pax_boot_memmap, @function
pax_boot_memmap:
        movq    limine_memmap_request+RESPONSE(%rip), %rdx
        testq   %rdx, %rdx
        jz      9f
        cmpq    8(%rdx), %rdi           /* unsigned: a negative i is huge */
        jae     9f
        cmpq    $2, %rsi
        ja      9f
        movq    16(%rdx), %rdx          /* entries: an array of pointers */
        movq    (%rdx,%rdi,8), %rdx     /* entries[i] */
        testq   %rdx, %rdx
        jz      9f
        movq    (%rdx,%rsi,8), %rax     /* base, length, type */
        ret
9:      xorl    %eax, %eax
        ret
        .size pax_boot_memmap, . - pax_boot_memmap

        .section .note.GNU-stack, "", @progbits
