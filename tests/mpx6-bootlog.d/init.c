/* tests/mpx6-bootlog.d/init.c — px118: the first program of the rows' archives. The kernel runs an
   ELF file alone as its first program, so each archive's is this: it writes `px118: init ran` and
   exits 0, and the kernel's end follows (`halt`). No libc: write and exit_group by `syscall` (the
   psABI's A.2.1, the numbers from arch/x86/entry/syscalls/syscall_64.tbl). */
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
    out("px118: init ran\n");
    sys(231, 0, 0, 0);
}

__asm__(".globl _start\n"
        "_start:\n"
        "  andq $-16, %rsp\n"
        "  call start_c\n"
        "  hlt\n");
