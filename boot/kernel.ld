/* kernel.ld — the wolf kernel's layout (M-KW). The proof's layout
   (boot/stub/linker.ld) with the sections a compiled object brings:
   string literals in .rodata.*, relocated read-only data, a GOT for the
   small PIC code model ([abi.target.none.codegen]) and .bss. Limine maps
   PT_LOAD segments at or above 0xffffffff80000000, one per permission,
   so the NX and write bits it applies from p_flags are honest.

   px03: kernel/paging maps the image itself, one permission per
   section, from the bounds below (returned to wolf by limine.S's
   pax_image_bounds, wolf-lang#529): text [__pax_text_start,
   __pax_text_end) read-execute, rodata [__pax_rodata_start,
   __pax_rodata_end) read-only, data and bss [__pax_data_start,
   __pax_image_end) read-write no-execute. Each section starts on a page
   and each end is rounded up to one, so no page holds two permissions;
   tests/mpx2-paging G1 holds the ELF's three PT_LOADs to these bounds. */
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
    __pax_image_start = .;      /* px02: the image's extent, for the */
                                /* frame allocator's test (limine.S) */

    __pax_text_start = .;
    .text : { *(.text .text.*) } :text
    . = ALIGN(0x1000);
    __pax_text_end = .;

    __pax_rodata_start = .;
    .rodata : {
        *(.rodata .rodata.*)
        *(.data.rel.ro .data.rel.ro.*)
    } :rodata
    . = ALIGN(0x1000);
    __pax_rodata_end = .;

    __pax_data_start = .;
    .data : {
        *(.data.limine)
        *(.data .data.*)
        *(.got .got.plt)
    } :data

    .bss : {
        *(.bss .bss.*)
        *(COMMON)
    } :data
    . = ALIGN(0x1000);
    __pax_image_end = .;

    /DISCARD/ : { *(.note .note.*) *(.comment) *(.eh_frame) }
}
