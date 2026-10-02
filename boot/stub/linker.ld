/* linker.ld — the proof's layout. Limine maps PT_LOAD segments at or
   above 0xffffffff80000000 (PROTOCOL.md, "Memory Layout at Entry"), so
   the image is linked there; one segment per permission so the NX and
   write bits Limine applies from p_flags are honest. */
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
    .rodata : { *(.rodata .rodata.*) } :rodata

    . = ALIGN(0x1000);
    .data : {
        *(.data.limine)
        *(.data .data.*)
    } :data

    /DISCARD/ : { *(.note .note.*) *(.comment) *(.eh_frame) }
}
