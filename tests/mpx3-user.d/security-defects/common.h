/* Raw syscall helpers for the isolated security regression witnesses.
   Derived from px146's W1-W6 probes. No libc or reference implementation source. */
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
static void out(const char *s) { i64 n = 0; while (s[n]) n++; sys(1, 1, (i64)s, n); }
static void dec(i64 v) {
    char b[24]; int i = 23; int neg = v < 0; u64 u = neg ? 0UL - (u64)v : (u64)v;
    b[i] = 0;
    do { b[--i] = (char)('0' + u % 10); u /= 10; } while (u);
    if (neg) b[--i] = '-';
    out(b + i);
}
static int streq(const char *a, const char *b) { while (*a && *a == *b) { a++; b++; } return *a == *b; }
static void finish(int code) { sys(231, code, 0, 0); for (;;) {} }
static void require(int ok) { if (!ok) { out("security: setup failed\n"); finish(99); } }
enum { SIGUSR1 = 10, SIGCHLD = 17 };
__asm__(".globl _start\n_start:\n  mov %rsp, %rdi\n  and $-16, %rsp\n  call wit_main\n  hlt\n");
