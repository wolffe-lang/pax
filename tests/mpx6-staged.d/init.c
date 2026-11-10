/* tests/mpx6-staged.d/init.c — px115: the first program of the staged rows' archives. The kernel runs
   ELF files alone as its first program (a `#!` script is refused: `not an ELF file`), so each archive's
   is this, built twice by tests/mpx6-staged.d/rows.py with WHO set: it writes `WHO: init ran`, then
   /etc/px115-staged's bytes when the file is there (the staged archive's marker; the installed root
   has none), and exits 0. No libc: write, open, read and exit_group by `syscall` (the psABI's A.2.1,
   the numbers from arch/x86/entry/syscalls/syscall_64.tbl). */
typedef long i64;

static i64 sys(i64 n, i64 a, i64 b, i64 c) {
    i64 r;
    __asm__ volatile("syscall" : "=a"(r) : "a"(n), "D"(a), "S"(b), "d"(c) : "rcx", "r11", "memory");
    return r;
}

static void out(const char *s) {
    i64 n = 0;
    while (s[n]) n++;
    sys(1, 1, (i64)s, n);
}

void start_c(void) {
    char b[256];
    out(WHO ": init ran\n");
    i64 fd = sys(2, (i64)"/etc/px115-staged", 0, 0);
    if (fd >= 0) {
        i64 n = sys(0, fd, (i64)b, sizeof b);
        if (n > 0) sys(1, 1, (i64)b, n);
    }
    sys(231, 0, 0, 0);
}

__asm__(".globl _start\n"
        "_start:\n"
        "  andq $-16, %rsp\n"
        "  call start_c\n"
        "  hlt\n");
