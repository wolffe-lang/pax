/* The census probe (px138), and px161's: ring 3's GS, the probe's pid, and
   /proc/pax-cpus read twice, 300 ms apart, in small pieces. No libc.

   CPU-USER-GS: a page mapped at 0x200000 holds a word; a read of
   %gs:0x200000 must find it, so ring 3's GS base is 0 (PAX gives ring 3
   none of its own). Read three times: as the kernel left GS, after
   `mov $0x1b, %gs` (the user data selector, which sets the base to the
   descriptor's 0), and after a sleep and a system call. A kernel that
   left its own GS base live in ring 3 makes the read fault on a
   supervisor page, and the probe dies before its census lines. */
typedef unsigned long U;
static long call(U n, U a, U b, U c) {
    long r;
    __asm__ volatile("syscall" : "=a"(r) : "a"(n), "D"(a), "S"(b), "d"(c) : "rcx", "r11", "memory");
    return r;
}
static long call6(U n, U a, U b, U c, U d, U e, U f) {
    long r;
    register U r10 __asm__("r10") = d;
    register U r8 __asm__("r8") = e;
    register U r9 __asm__("r9") = f;
    __asm__ volatile("syscall" : "=a"(r) : "a"(n), "D"(a), "S"(b), "d"(c), "r"(r10), "r"(r8), "r"(r9) : "rcx", "r11", "memory");
    return r;
}
static void out(const char *s, U n) { call(1, 1, (U)s, n); }
static U len(const char *s) { U n = 0; while (s[n]) n++; return n; }
static void put(const char *s) { out(s, len(s)); }
static void dec(U v) {
    char b[24]; int i = 24;
    do { b[--i] = (char)('0' + v % 10); v /= 10; } while (v);
    out(b + i, (U)(24 - i));
}
static void hex(U v) {
    char b[20]; int i = 20;
    do { b[--i] = "0123456789abcdef"[v & 15]; v >>= 4; } while (v);
    b[--i] = 'x'; b[--i] = '0';
    out(b + i, (U)(20 - i));
}
static U gsword(void) {
    U v;
    __asm__ volatile("movq %%gs:0x200000, %0" : "=r"(v) :: "memory");
    return v;
}
static void nap(U ns) {
    U ts[2] = { ns / 1000000000ul, ns % 1000000000ul };
    call(35, (U)ts, 0, 0); /* nanosleep */
}
static char buf[16384];
static void census(const char *tag) {
    U n = 0;
    long fd = call(2, (U)"/proc/pax-cpus", 0, 0);
    if (fd < 0) { put(tag); put(" missing\n"); call(60, 1, 0, 0); }
    for (;;) {
        long k = call(0, fd, (U)(buf + n), 7);
        if (k < 0 || n + (U)k >= sizeof buf) { put(tag); put(" read failed\n"); call(60, 2, 0, 0); }
        if (!k) break;
        n += (U)k;
    }
    put(tag); put(" begin\n"); out(buf, n); put(tag); put(" end\n");
    call(3, fd, 0, 0);
}
void _start(void) {
    const U magic = 0x50415847535f3136ul;
    long m = call6(9, 0x200000, 4096, 3, 0x32, (U)-1, 0); /* PROT_READ|WRITE, PRIVATE|ANONYMOUS|FIXED */
    if (m != 0x200000) { put("CPU-USER-GS mmap failed "); hex((U)m); put("\n"); }
    else {
        *(volatile U *)0x200000 = magic;
        U a = gsword();
        __asm__ volatile("movw %0, %%gs" :: "r"((unsigned short)0x1b));
        U b = gsword();
        nap(20000000);
        call(39, 0, 0, 0);
        U c = gsword();
        if (a == magic && b == magic && c == magic) put("CPU-USER-GS ok 3 reads\n");
        else { put("CPU-USER-GS differs "); hex(a); put(" "); hex(b); put(" "); hex(c); put("\n"); }
    }
    put("CPU-PID "); dec((U)call(39, 0, 0, 0)); put("\n");
    census("CPU-PROC");
    nap(300000000);
    census("CPU-PROC2");
    call(60, 0, 0, 0);
    for (;;) {}
}
