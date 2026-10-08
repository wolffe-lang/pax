/* procs.c — px14's process witness: the system calls that make, replace
   and wait for processes, run as the first program (pid 1) on PAX and,
   for the reference, as pid 1 of a fresh pid namespace on Linux. Every
   line it writes is the same on both; tests/mpx3-shell compares them
   byte for byte.

   No libc: the calls are made with `syscall` (the psABI's A.2.1, the
   numbers from arch/x86/entry/syscalls/syscall_64.tbl, flags and
   layouts from the uapi headers: linux/sched.h, linux/wait.h,
   asm-generic/siginfo.h, asm/signal.h), so the binary is a few KiB and
   every call is the one named here. Built by tools/mkuser with
   -nostdlib -ffreestanding, static, no PIE.

   A child is started the way pelt's spawn starts one (measured,
   notes/px14/): a vfork-style clone (CLONE_VM | CLONE_VFORK, a stack of
   its own) whose child does nothing but execve this program again with
   a role in argv[1]; the parent resumes once the child has exec'd. Run
   with no argument it is the parent and walks the cases in order:

     ids       getpid, getppid, gettid (1, 0, 1)
     cloexec   /etc/motd opened with O_CLOEXEC (3) and without (4); a
               child exiting 3 finds 3 closed and 4 open (pread at 0:
               the offset is not shared state anyone reads); wait4
               answers its pid and 0x300
     signal    a child that writes address 0: wait4's status 0xb (the
               core-dump bit masked: the host's choice, not the ABI's)
     zombie    a child that exits 5 while the parent sleeps 300 ms;
               wait4(-1, WNOHANG) then reaps it: kept until waited for
     orphan    a child that starts a grandchild and exits 0 at once;
               the grandchild, 300 ms later, has ppid 1; pid 1's
               wait4(-1) reaps it (0x700)
     waitid    P_PID, WEXITED: si_signo 17, si_code 1, si_pid, si_status 9
     echild    wait4(-1) with no child: -10
     execve    errors in place: a missing file -2, a text file -13, a
               directory -13, an executable that is not ELF -8
     sigs      SIGUSR1 blocked and handled, SIGINT ignored; a child sees
               the mask kept and SIGUSR1 back to SIG_DFL, SIGINT still
               ignored (execve's rule); SIGKILL's action -22
     dup       dup2 to 7, dup3 with O_CLOEXEC to 8, dup3 onto itself
               -22; a child finds 7 open and 8 closed
   and `kill(getpid(), 0)`, whose answer it does not print (PAX refuses
   it by name; Linux answers 0: the test reads PAX's log line).

   The pids are deterministic on both sides: a fresh pid namespace
   numbers from 1 as PAX does, one process at a time. */

typedef unsigned long u64;
typedef long i64;

#define SYS_read 0
#define SYS_write 1
#define SYS_open 2
#define SYS_rt_sigaction 13
#define SYS_rt_sigprocmask 14
#define SYS_pread64 17
#define SYS_dup2 33
#define SYS_nanosleep 35
#define SYS_getpid 39
#define SYS_clone 56
#define SYS_execve 59
#define SYS_wait4 61
#define SYS_kill 62
#define SYS_getppid 110
#define SYS_gettid 186
#define SYS_exit_group 231
#define SYS_waitid 247
#define SYS_dup3 292
#define SYS_prlimit64 302

#define CLONE_VM 0x100
#define CLONE_VFORK 0x4000
#define SIGCHLD 17
#define O_CLOEXEC 0x80000
#define WNOHANG 1
#define WEXITED 4
#define P_PID 1
#define SIGINT 2
#define SIGKILL 9
#define SIGUSR1 10
#define SIG_BLOCK 0
#define RLIMIT_CORE 4

static i64 sys6(i64 n, i64 a, i64 b, i64 c, i64 d, i64 e) {
    register i64 r10 __asm__("r10") = d;
    register i64 r8 __asm__("r8") = e;
    i64 r;
    __asm__ volatile("syscall"
                     : "=a"(r)
                     : "a"(n), "D"(a), "S"(b), "d"(c), "r"(r10), "r"(r8)
                     : "rcx", "r11", "memory");
    return r;
}
#define sys(n, a, b, c) sys6((n), (i64)(a), (i64)(b), (i64)(c), 0, 0)

void *memset(void *d, int c, u64 n) {
    unsigned char *p = d;
    while (n--) *p++ = (unsigned char)c;
    return d;
}

void *memcpy(void *d, const void *s, u64 n) {
    unsigned char *p = d;
    const unsigned char *q = s;
    while (n--) *p++ = *q++;
    return d;
}

/* One line at a time, written whole. */
static char line[256];
static u64 used;

static void put(const char *s) {
    while (*s && used < sizeof line) line[used++] = *s++;
}

static void dec(i64 v) {
    char b[24];
    int k = 0;
    u64 u = v < 0 ? (u64)-v : (u64)v;
    if (v < 0) put("-");
    do { b[k++] = (char)('0' + u % 10); u /= 10; } while (u);
    while (k) { char c[2] = { b[--k], 0 }; put(c); }
}

static void hex(u64 v) {
    char b[20];
    int k = 0;
    put("0x");
    do { b[k++] = "0123456789abcdef"[v & 15]; v >>= 4; } while (v);
    while (k) { char c[2] = { b[--k], 0 }; put(c); }
}

static void end(void) {
    if (used < sizeof line) line[used++] = '\n';
    sys(SYS_write, 1, line, used);
    used = 0;
}

static int same(const char *a, const char *b) {
    while (*a && *a == *b) { a++; b++; }
    return *a == *b;
}

/* The spawn: these globals are what the child's execve reads. */
char *g_path;
char **g_argv;
char **g_envp;
static char cstack[16384] __attribute__((aligned(16)));

static i64 spawn(char **argv) {
    i64 r;
    g_path = "/bin/procs";
    g_argv = argv;
    __asm__ volatile(
        "xorl %%r10d, %%r10d\n\t"
        "xorl %%r8d, %%r8d\n\t"
        "syscall\n\t"
        "testq %%rax, %%rax\n\t"
        "jnz 1f\n\t"
        /* the child, on cstack, sharing the parent's memory: execve only */
        "movq g_path(%%rip), %%rdi\n\t"
        "movq g_argv(%%rip), %%rsi\n\t"
        "movq g_envp(%%rip), %%rdx\n\t"
        "movl $59, %%eax\n\t"
        "syscall\n\t"
        "movl $127, %%edi\n\t"
        "movl $231, %%eax\n\t"
        "syscall\n\t"
        "1:"
        : "=a"(r)
        : "a"(SYS_clone), "D"(CLONE_VM | CLONE_VFORK | SIGCHLD), "S"(cstack + sizeof cstack), "d"(0)
        : "rcx", "r8", "r10", "r11", "memory");
    return r;
}

static void wait_line(const char *what, i64 pid, int options) {
    int st = 0;
    i64 r = sys6(SYS_wait4, pid, (i64)&st, options, 0, 0);
    put(what);
    put(": ");
    dec(r);
    /* The core-dump bit (0x80) is the Linux host's core_pattern's
       business (measured: set under a piped pattern whatever
       RLIMIT_CORE says), so it is left out; PAX never sets it. */
    if (r > 0) { put(" status "); hex((u64)(unsigned)st & 0xff7f); }
    end();
}

static void nap(void) {
    i64 ts[2] = { 0, 300000000 };
    sys(SYS_nanosleep, ts, 0, 0);
}

static void ids(const char *who) {
    put(who);
    put(": pid ");
    dec(sys(SYS_getpid, 0, 0, 0));
    put(" ppid ");
    dec(sys(SYS_getppid, 0, 0, 0));
    put(" tid ");
    dec(sys(SYS_gettid, 0, 0, 0));
}

static void peek(const char *what, int fd) {
    char b[5] = { 0, 0, 0, 0, 0 };
    i64 r = sys6(SYS_pread64, fd, (i64)b, 4, 0, 0);
    put(" ");
    put(what);
    put(" ");
    if (r < 0) dec(r); else put(b);
}

static int child(char **argv) {
    const char *role = argv[1];
    if (same(role, "exit")) {
        int code = argv[2][0] - '0';
        ids("child");
        put(" exit ");
        dec(code);
        end();
        return code;
    }
    if (same(role, "fds")) {
        ids("fds");
        peek("fd3", 3);
        peek("fd4", 4);
        end();
        return 3;
    }
    if (same(role, "segv")) {
        __asm__ volatile("movl $1, 0" ::: "memory");
        return 1;
    }
    if (same(role, "orphan")) {
        ids("orphan");
        end();
        char *gv[] = { "procs", "grandchild", 0 };
        i64 g = spawn(gv);
        put("orphan: started ");
        dec(g);
        put(", exits without waiting");
        end();
        return 0;
    }
    if (same(role, "grandchild")) {
        nap();
        ids("grandchild");
        end();
        return 7;
    }
    if (same(role, "sigs")) {
        u64 m = 1;
        i64 r = sys6(SYS_rt_sigprocmask, SIG_BLOCK, 0, (i64)&m, 8, 0);
        u64 usr1[4] = { 9, 9, 9, 9 }, in[4] = { 9, 9, 9, 9 };
        sys6(SYS_rt_sigaction, SIGUSR1, 0, (i64)usr1, 8, 0);
        sys6(SYS_rt_sigaction, SIGINT, 0, (i64)in, 8, 0);
        put("sigs: mask ");
        dec(r);
        put(" ");
        hex(m);
        put(", usr1 handler ");
        hex(usr1[0]);
        put(", int handler ");
        hex(in[0]);
        end();
        return 0;
    }
    if (same(role, "dup")) {
        ids("dup");
        peek("fd7", 7);
        peek("fd8", 8);
        end();
        return 0;
    }
    return 99;
}

static int parent(void) {
    ids("procs");
    end();
    { u64 zero[2] = { 0, 0 }; sys6(SYS_prlimit64, 0, RLIMIT_CORE, (i64)zero, 0, 0); }

    /* cloexec */
    i64 a = sys(SYS_open, "/etc/motd", O_CLOEXEC, 0);
    i64 b = sys(SYS_open, "/etc/motd", 0, 0);
    put("cloexec: opened ");
    dec(a);
    put(" with O_CLOEXEC, ");
    dec(b);
    put(" without");
    end();
    char *fv[] = { "procs", "fds", 0 };
    i64 c = spawn(fv);
    wait_line("wait4 fds", c, 0);

    /* signal */
    char *sv[] = { "procs", "segv", 0 };
    c = spawn(sv);
    wait_line("wait4 segv", c, 0);

    /* zombie */
    char *zv[] = { "procs", "exit", "5", 0 };
    c = spawn(zv);
    nap();
    wait_line("wait4 zombie, WNOHANG", -1, WNOHANG);

    /* orphan */
    char *ov[] = { "procs", "orphan", 0 };
    c = spawn(ov);
    wait_line("wait4 orphan", c, 0);
    wait_line("wait4 any (the reparented grandchild)", -1, 0);

    /* waitid */
    char *wv[] = { "procs", "exit", "9", 0 };
    c = spawn(wv);
    {
        int si[32];
        for (int k = 0; k < 32; k++) si[k] = -1;
        i64 r = sys6(SYS_waitid, P_PID, c, (i64)si, WEXITED, 0);
        put("waitid: ");
        dec(r);
        put(" signo ");
        dec(si[0]);
        put(" code ");
        dec(si[2]);
        put(" pid ");
        dec(si[4]);
        put(" status ");
        dec(si[6]);
        end();
    }

    /* echild */
    wait_line("wait4 with no child", -1, 0);

    /* execve errors, in place */
    {
        char *xv[] = { "x", 0 };
        put("execve:");
        const char *paths[] = { "/nonexistent", "/etc/motd", "/bin", "/etc/script" };
        for (int k = 0; k < 4; k++) {
            put(" ");
            put(paths[k]);
            put(" ");
            dec(sys(SYS_execve, paths[k], xv, g_envp));
        }
        end();
    }

    /* sigs */
    {
        u64 set = 1UL << (SIGUSR1 - 1), old = 7;
        i64 r = sys6(SYS_rt_sigprocmask, SIG_BLOCK, (i64)&set, (i64)&old, 8, 0);
        u64 act[4] = { 0x401000, 0, 0, 0 }, ign[4] = { 1, 0, 0, 0 }, back[4] = { 9, 9, 9, 9 };
        i64 r1 = sys6(SYS_rt_sigaction, SIGUSR1, (i64)act, 0, 8, 0);
        i64 r2 = sys6(SYS_rt_sigaction, SIGINT, (i64)ign, 0, 8, 0);
        i64 r3 = sys6(SYS_rt_sigaction, SIGUSR1, 0, (i64)back, 8, 0);
        i64 r4 = sys6(SYS_rt_sigaction, SIGKILL, (i64)ign, 0, 8, 0);
        i64 r5 = sys6(SYS_rt_sigprocmask, SIG_BLOCK, 0, 0, 4, 0);
        put("sigs: block ");
        dec(r);
        put(" old ");
        hex(old);
        put(", usr1 ");
        dec(r1);
        put(" int ");
        dec(r2);
        put(" back ");
        dec(r3);
        put(" ");
        hex(back[0]);
        put(", kill's action ");
        dec(r4);
        put(", sigsetsize 4 ");
        dec(r5);
        end();
        char *gv[] = { "procs", "sigs", 0 };
        c = spawn(gv);
        wait_line("wait4 sigs", c, 0);
    }

    /* dup */
    {
        i64 d1 = sys(SYS_dup2, b, 7, 0);
        i64 d2 = sys(SYS_dup3, b, 8, O_CLOEXEC);
        i64 d3 = sys(SYS_dup3, b, b, 0);
        put("dup: dup2 ");
        dec(d1);
        put(" dup3 ");
        dec(d2);
        put(" onto itself ");
        dec(d3);
        end();
        char *dv[] = { "procs", "dup", 0 };
        c = spawn(dv);
        wait_line("wait4 dup", c, 0);
    }

    sys(SYS_kill, sys(SYS_getpid, 0, 0, 0), 0, 0);
    put("procs: done");
    end();
    return 0;
}

int cmain(u64 *sp) {
    int argc = (int)sp[0];
    char **argv = (char **)(sp + 1);
    g_envp = argv + argc + 1;
    int code = argc > 1 ? child(argv) : parent();
    sys(SYS_exit_group, code, 0, 0);
    return 0;
}

__asm__(".globl _start\n"
        "_start:\n"
        "  xorl %ebp, %ebp\n"
        "  movq %rsp, %rdi\n"
        "  andq $-16, %rsp\n"
        "  call cmain\n"
        "  hlt\n");
