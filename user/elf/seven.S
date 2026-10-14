/* seven.S — px43: the smallest program PAX and Linux both run, as an
   archive file: it exits with status 7 and does nothing else. tests/
   mpx5-users puts copies of it in the image at every mode px38's `perm`
   asks about, owned 1000:2000, so `chk` can show `execve`'s class rule
   on PAX, whose loader runs only the archive's own bytes (px27): a copy
   written since boot is refused whatever its mode.

   Built by tools/mkcred: cc -nostdlib -static -no-pie, ET_EXEC with no
   PT_INTERP. */
        .globl  _start
        .text
_start:
        movl    $231, %eax              /* exit_group */
        movl    $7, %edi
        syscall
        hlt

        .section .note.GNU-stack, "", @progbits
