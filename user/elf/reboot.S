/* reboot.S — px63: PAX's `reboot`. sync(2), then reboot(2) with
   LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2 and LINUX_REBOOT_CMD_RESTART
   (uapi linux/reboot.h; reboot(2)): the kernel writes every mounted
   volume, marks it clean and resets the machine. Root's alone: a user
   is told -EPERM and the program exits 1 (it says nothing: PAX's own
   kernel line names the reboot). With an argument it halts instead
   (LINUX_REBOOT_CMD_HALT), `reboot -h` or any word.

   Built by tools/mkdiskprobe: cc -nostdlib -static -no-pie, ET_EXEC
   with no PT_INTERP. */
        .globl  _start
        .text
_start:
        movl    $162, %eax              /* sync */
        syscall
        movl    $0x01234567, %edx       /* LINUX_REBOOT_CMD_RESTART */
        cmpq    $1, (%rsp)              /* argc */
        je      1f
        movl    $0xcdef0123, %edx       /* LINUX_REBOOT_CMD_HALT */
1:      movl    $169, %eax              /* reboot */
        movl    $0xfee1dead, %edi
        movl    $672274793, %esi
        xorl    %r10d, %r10d
        syscall
        movl    $231, %eax              /* exit_group: the reboot was refused */
        movl    $1, %edi
        syscall
        hlt

        .section .note.GNU-stack, "", @progbits
