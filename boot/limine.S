/* limine.S — where Limine's requests are, for wolf (px01; px02).

   Listed under `asm` in kernel/wolf.pkg, so these routines are on
   wolf's roster ([abi.asm.roster]) and the kernel reaches them through
   bodyless `extern "c" fn` declarations (x86-64 SysV: the argument in
   %rdi, the result in %rax).

   px01 read every response here, because wolf had neither volatile
   access nor integer-to-pointer lowering. Since wolf-lang eb955c3b (kw06
   `N as *T`, kw07 `read_volatile`) kernel/boot_info reads the responses
   itself. What stays in assembly is what wolf still cannot spell: the
   ADDRESS of a symbol the assembler or the linker defines (wolf-lang
   #529: no way to name a linker-defined symbol, no module-level state).
   So these two routines return addresses and nothing else; they read no
   memory.

     pax_limine_request(which) -> u64   the address of request `which`
                                        in boot/start.S: 0 the base
                                        revision tag, 1 bootloader info,
                                        2 firmware type, 3 memory map,
                                        4 HHDM, 5 executable address; 0
                                        for any other `which`
     pax_image_bounds(which) -> u64     the kernel image's first (0) and
                                        one-past-last (1) virtual
                                        address, boot/kernel.ld's
                                        __pax_image_start and
                                        __pax_image_end; 0 otherwise

   Written from: the Limine protocol (PROTOCOL.md, limine-protocol
   3a0526b7: the request layout) and the x86-64 psABI. No Linux source. */

        .text

        .globl pax_limine_request
        .type pax_limine_request, @function
pax_limine_request:
        cmpq    $0, %rdi
        je      0f
        cmpq    $1, %rdi
        je      1f
        cmpq    $2, %rdi
        je      2f
        cmpq    $3, %rdi
        je      3f
        cmpq    $4, %rdi
        je      4f
        cmpq    $5, %rdi
        je      5f
        xorl    %eax, %eax
        ret
0:      leaq    limine_base_revision(%rip), %rax
        ret
1:      leaq    limine_bootloader_info_request(%rip), %rax
        ret
2:      leaq    limine_firmware_type_request(%rip), %rax
        ret
3:      leaq    limine_memmap_request(%rip), %rax
        ret
4:      leaq    limine_hhdm_request(%rip), %rax
        ret
5:      leaq    limine_executable_address_request(%rip), %rax
        ret
        .size pax_limine_request, . - pax_limine_request

        .globl pax_image_bounds
        .type pax_image_bounds, @function
pax_image_bounds:
        cmpq    $0, %rdi
        je      0f
        cmpq    $1, %rdi
        je      1f
        xorl    %eax, %eax
        ret
0:      leaq    __pax_image_start(%rip), %rax
        ret
1:      leaq    __pax_image_end(%rip), %rax
        ret
        .size pax_image_bounds, . - pax_image_bounds

        .section .note.GNU-stack, "", @progbits
