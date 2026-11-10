/* tests/mpx6-bootlog.d/init.c — px118: the first program of the rows' archives. The kernel runs an
   ELF file alone as its first program, so each archive's is this: it writes `px118: init ran`, then
   /proc/pax-boot's text and /proc/pax-bootlog's bytes between marker lines (when the files are there),
   and, when /etc/px118-reboot exists and the previous boot is `none`, asks for a restart by reboot(2)
   (the kernel's own reset path, a warm reset); otherwise it exits 0 and the kernel's end follows
   (`halt`). No libc: read, write, open, close, reboot and exit_group by `syscall` (the psABI's A.2.1,
   the numbers from arch/x86/entry/syscalls/syscall_64.tbl; reboot(2)'s magic words and RESTART from
   the uapi linux/reboot.h). */
typedef long i64;

static i64 sys(i64 n, i64 a, i64 b, i64 c, i64 d) {
    i64 r;
    register i64 r10 __asm__("r10") = d;
    __asm__ volatile("syscall" : "=a"(r) : "a"(n), "D"(a), "S"(b), "d"(c), "r"(r10) : "rcx", "r11", "memory");
    return r;
}

static void outn(const char *s, i64 n) {
    while (n > 0) {
        i64 w = sys(1, 1, (i64)s, n, 0);
        if (w <= 0) return;
        s += w;
        n -= w;
    }
}

static void out(const char *s) {
    i64 n = 0;
    while (s[n]) n++;
    outn(s, n);
}

static char buf[4096];
static char boot[4096];

/* Copy the file at PATH to the console between `px118: BEGIN NAME` and `px118: END NAME`;
   its first 4095 bytes are also kept in KEEP when KEEP is given. */
static void show(const char *path, const char *name, char *keep) {
    i64 fd = sys(2, (i64)path, 0, 0, 0);
    if (fd < 0) {
        out("px118: no ");
        out(path);
        out("\n");
        return;
    }
    out("px118: BEGIN ");
    out(name);
    out("\n");
    i64 kept = 0;
    for (;;) {
        i64 n = sys(0, fd, (i64)buf, sizeof buf, 0);
        if (n <= 0) break;
        if (keep) {
            for (i64 i = 0; i < n && kept < 4095; i++) keep[kept++] = buf[i];
        }
        outn(buf, n);
    }
    if (keep) keep[kept] = 0;
    sys(3, fd, 0, 0, 0);
    out("\npx118: END ");
    out(name);
    out("\n");
}

static int has(const char *s, const char *w) {
    for (; *s; s++) {
        const char *a = s, *b = w;
        while (*b && *a == *b) a++, b++;
        if (!*b) return 1;
    }
    return 0;
}

void start_c(void) {
    out("px118: init ran\n");
    show("/proc/pax-boot", "pax-boot", boot);
    show("/proc/pax-bootlog", "pax-bootlog", 0);
    i64 fd = sys(2, (i64)"/etc/px118-reboot", 0, 0, 0);
    if (fd >= 0 && has(boot, "previous none")) {
        out("px118: reboot\n");
        sys(169, 0xfee1dead, 672274793, 0x01234567, 0);
    }
    sys(231, 0, 0, 0, 0);
}

__asm__(".globl _start\n"
        "_start:\n"
        "  andq $-16, %rsp\n"
        "  call start_c\n"
        "  hlt\n");
