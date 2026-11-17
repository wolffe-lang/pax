/* tests/mpx12-security.d/probe.c — the ring-3 side of tests/mpx12-security.

   With no argument it prints /proc/pax-security twice (read seven bytes at a time, so the file's
   offsets are exercised), what CPUID tells ring 3 about the CPU's protections, and one witness line
   for each protection a program can observe from ring 3. Each witness that might fault runs in a
   forked child, and the parent reports how the child ended:
     nx-exec    a `ret` written into a read-write anonymous page, then called
     stack-nx   a `ret` written into the stack, then called
     umip       SGDT (its result is never printed)
     user-wx    mmap of PROT_READ|PROT_WRITE|PROT_EXEC, and mprotect of a read-write page to the same
     null-page  mmap MAP_FIXED of the page at address 0
   With the argument `addr` it prints where its stack, a fresh anonymous mapping, its break and its
   code are, so two runs show whether those addresses move.

   No libc: system calls by `syscall` (the psABI's A.2.1; the numbers from the syscall table, the
   PROT_*, MAP_* and errno values from the uapi headers). Nothing here reads kernel memory. */
typedef long i64;
typedef unsigned long u64;

static i64 sys6(i64 n, i64 a, i64 b, i64 c, i64 d, i64 e, i64 f) {
    i64 r;
    register i64 r10 __asm__("r10") = d;
    register i64 r8 __asm__("r8") = e;
    register i64 r9 __asm__("r9") = f;
    __asm__ volatile("syscall" : "=a"(r) : "a"(n), "D"(a), "S"(b), "d"(c), "r"(r10), "r"(r8), "r"(r9)
                     : "rcx", "r11", "memory");
    return r;
}
#define sys(n, a, b, c) sys6(n, a, b, c, 0, 0, 0)

enum { SYS_READ = 0, SYS_WRITE = 1, SYS_OPEN = 2, SYS_CLOSE = 3, SYS_MMAP = 9, SYS_MPROTECT = 10,
       SYS_MUNMAP = 11, SYS_BRK = 12, SYS_CLONE = 56, SYS_WAIT4 = 61, SYS_EXIT_GROUP = 231 };
enum { PROT_READ = 1, PROT_WRITE = 2, PROT_EXEC = 4, MAP_PRIVATE = 2, MAP_FIXED = 0x10, MAP_ANONYMOUS = 0x20,
       SIGCHLD = 17 };

static void outn(const char *s, i64 n) {
    while (n > 0) {
        i64 w = sys(SYS_WRITE, 1, (i64)s, n);
        if (w <= 0) return;
        s += w;
        n -= w;
    }
}

/* A line is written whole, with one write, at its newline: a child that dies or exits while the
   parent waits makes the kernel write its own line, which must not land inside one of ours. */
static char line[512];
static i64 used;

static void out(const char *s) {
    for (i64 i = 0; s[i]; i++) {
        if (used < (i64)sizeof line) line[used++] = s[i];
        if (s[i] == '\n') {
            outn(line, used);
            used = 0;
        }
    }
}

static void hex(u64 v) {
    char b[19];
    b[0] = '0';
    b[1] = 'x';
    for (int i = 0; i < 16; i++) b[2 + i] = "0123456789abcdef"[(v >> (60 - 4 * i)) & 15];
    b[18] = 0;
    out(b);
}

static void dec(i64 v) {
    char b[24];
    int i = 23;
    int neg = v < 0;
    u64 u = neg ? (u64)(-v) : (u64)v;
    b[i] = 0;
    do {
        b[--i] = (char)('0' + u % 10);
        u /= 10;
    } while (u);
    if (neg) b[--i] = '-';
    out(b + i);
}

static void cpuid(unsigned leaf, unsigned sub, unsigned r[4]) {
    __asm__ volatile("cpuid" : "=a"(r[0]), "=b"(r[1]), "=c"(r[2]), "=d"(r[3]) : "a"(leaf), "c"(sub));
}

static char text[8192];

/* /proc/pax-security, seven bytes a read, between marker lines. */
static void show(int round) {
    out("px146: BEGIN pax-security ");
    dec(round);
    out("\n");
    i64 fd = sys(SYS_OPEN, (i64)"/proc/pax-security", 0, 0);
    if (fd < 0) {
        out("px146: open /proc/pax-security: ");
        dec(fd);
        out("\n");
    } else {
        i64 n = 0;
        for (;;) {
            if (n + 7 > (i64)sizeof text) break;
            i64 r = sys(SYS_READ, fd, (i64)(text + n), 7);
            if (r <= 0) {
                if (r < 0) {
                    out("px146: read /proc/pax-security: ");
                    dec(r);
                    out("\n");
                }
                break;
            }
            n += r;
        }
        sys(SYS_CLOSE, fd, 0, 0);
        outn(text, n);
    }
    out("px146: END pax-security ");
    dec(round);
    out("\n");
}

static void call(void *p) { ((void (*)(void))p)(); }

/* Run WHAT in a child; "ran" when it exited 0, "segv" when SIGSEGV ended it, else the status. */
static void witness(const char *name, int what) {
    i64 pid = sys6(SYS_CLONE, SIGCHLD, 0, 0, 0, 0, 0);
    if (pid == 0) {
        if (what == 0) { /* nx-exec */
            i64 p = sys6(SYS_MMAP, 0, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
            if (p < 0 && p > -4096) sys(SYS_EXIT_GROUP, 3, 0, 0);
            *(volatile unsigned char *)p = 0xc3;
            call((void *)p);
        } else if (what == 1) { /* stack-nx */
            volatile unsigned char code[64];
            code[0] = 0xc3;
            call((void *)code);
        } else { /* umip */
            unsigned char gdtr[16];
            __asm__ volatile("sgdt %0" : "=m"(gdtr) : : "memory");
        }
        sys(SYS_EXIT_GROUP, 0, 0, 0);
    }
    if (pid < 0) {
        out("px146: witness ");
        out(name);
        out(" fork ");
        dec(pid);
        out("\n");
        return;
    }
    int status = 0;
    i64 w = sys6(SYS_WAIT4, pid, (i64)&status, 0, 0, 0, 0);
    out("px146: witness ");
    out(name);
    if (w != pid) {
        out(" wait ");
        dec(w);
    } else if ((status & 0x7f) == 0 && ((status >> 8) & 0xff) == 0) {
        out(" ran");
    } else if ((status & 0x7f) == 11) {
        out(" segv");
    } else {
        out(" status ");
        hex((u64)status);
    }
    out("\n");
}

static void result(i64 r) {
    if (r < 0 && r > -4096) {
        out("err ");
        dec(r);
    } else {
        out("ok");
    }
}

static void addresses(void) {
    volatile int here = 0;
    i64 m = sys6(SYS_MMAP, 0, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    i64 b = sys(SYS_BRK, 0, 0, 0);
    out("px146: addr stack ");
    hex((u64)&here & ~0xfffUL);
    out(" mmap ");
    hex((u64)m);
    out(" brk ");
    hex((u64)b);
    out(" text ");
    hex((u64)&addresses);
    out("\n");
}

void _start_c(i64 *sp) {
    i64 argc = sp[0];
    char **argv = (char **)(sp + 1);
    if (argc > 1 && argv[1][0] == 'a') {
        addresses();
        sys(SYS_EXIT_GROUP, 0, 0, 0);
    }
    out("px146: probe ran\n");
    show(1);
    show(2);

    unsigned r[4];
    cpuid(0, 0, r);
    unsigned max = r[0];
    unsigned b7 = 0, c7 = 0, d7 = 0;
    if (max >= 7) {
        cpuid(7, 0, r);
        b7 = r[1];
        c7 = r[2];
        d7 = r[3];
    }
    cpuid(0x80000000u, 0, r);
    unsigned nx = 0;
    if (r[0] >= 0x80000001u) {
        cpuid(0x80000001u, 0, r);
        nx = (r[3] >> 20) & 1;
    }
    out("px146: cpuid nx ");
    dec(nx);
    out(" smep ");
    dec((b7 >> 7) & 1);
    out(" smap ");
    dec((b7 >> 20) & 1);
    out(" umip ");
    dec((c7 >> 2) & 1);
    out(" ibrs ");
    dec((d7 >> 26) & 1);
    out(" arch-capabilities ");
    dec((d7 >> 29) & 1);
    out("\n");

    witness("nx-exec", 0);
    witness("stack-nx", 1);
    witness("umip", 2);

    out("px146: witness user-wx mmap ");
    i64 x = sys6(SYS_MMAP, 0, 4096, PROT_READ | PROT_WRITE | PROT_EXEC, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    result(x);
    if (!(x < 0 && x > -4096)) sys(SYS_MUNMAP, x, 4096, 0);
    out(" mprotect ");
    i64 p = sys6(SYS_MMAP, 0, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p < 0 && p > -4096) {
        out("mmap ");
        dec(p);
    } else {
        result(sys(SYS_MPROTECT, p, 4096, PROT_READ | PROT_WRITE | PROT_EXEC));
        sys(SYS_MUNMAP, p, 4096, 0);
    }
    out("\n");

    out("px146: witness null-page ");
    i64 z = sys6(SYS_MMAP, 0, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0);
    result(z);
    if (z == 0) sys(SYS_MUNMAP, 0, 4096, 0);
    out("\n");

    out("px146: probe done\n");
    sys(SYS_EXIT_GROUP, 0, 0, 0);
}

__asm__(".globl _start\n_start:\n  mov %rsp, %rdi\n  and $-16, %rsp\n  call _start_c\n  hlt\n");
