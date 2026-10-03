/* kernel.ld — the wolf kernel's layout (M-KW). The proof's layout
   (boot/stub/linker.ld) with the sections a compiled object brings:
   string literals in .rodata.*, relocated read-only data, a GOT for the
   small PIC code model ([abi.target.none.codegen]) and .bss. Limine maps
   PT_LOAD segments at or above 0xffffffff80000000, one per permission,
   so the NX and write bits it applies from p_flags are honest. */
OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)

PHDRS
{
    text   PT_LOAD FLAGS(5);   /* r-x */
    rodata PT_LOAD FLAGS(4);   /* r-- */
    data   PT_LOAD FLAGS(6);   /* rw- */
}

SECTIONS
{
    . = 0xffffffff80000000;

    .text : { *(.text .text.*) } :text

    . = ALIGN(0x1000);
    .rodata : {
        *(.rodata .rodata.*)
        *(.data.rel.ro .data.rel.ro.*)
    } :rodata

    . = ALIGN(0x1000);
    .data : {
        *(.data.limine)
        *(.data .data.*)
        *(.got .got.plt)
    } :data

    .bss : {
        *(.bss .bss.*)
        *(COMMON)
    } :data

    /DISCARD/ : { *(.note .note.*) *(.comment) *(.eh_frame) }
}
