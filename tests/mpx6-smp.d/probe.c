/* tests/mpx6-smp.d/probe.c: SMP stage 2's probe. No libc: the system calls by number, the
   threads by clone(2), the handlers with their own restorer. Built by tests/mpx6-smp with
   gcc -nostdlib -static -ffreestanding -fno-stack-protector -fno-pie -no-pie -O2 -mgeneral-regs-only.

     /bin/smpprobe rows            SMP-ACTIVE, SMP-RUN, SMP-TLB, SMP-SIGNAL, SMP-EXIT, SMP-WAIT
     /bin/smpprobe stress SECS     SMP-LOCK: ten processes at once for SECS seconds
     /bin/smpprobe end halt|poweroff|restart
                                   a spinner a processor, then root's reboot(2) (SMP-END)
     /bin/smpprobe cap             SMP-ACTIVE and one SMP-RUN round (SMP-CAP, `pax.cpus=N`)
     /bin/smpprobe one             SMP-ACTIVE alone (one processor: `nosmp`, `-smp 1`, `pax.cpus=1`)
     /bin/smpprobe exec-child      SMP-EXIT's execve target: one line, exit status 9

   Every line starts with its row's name; tests/mpx6-smp.d/rows.py reads them with /proc/pax-cpus as
   the probe copied it (`SMP-PROC <tag> begin` … `SMP-PROC <tag> end`). Times are the TSC's, read in
   ring 3 and calibrated against CLOCK_MONOTONIC over 300 ms (PAX's CLOCK_MONOTONIC is the tick
   count, 10 ms a step: too coarse for the 1 ms and 2 ms bounds); the rate is printed. Workers whose
   CPU time is checked do fixed work (a loop count calibrated to the time asked), never a timed
   spin, so a processor shared at stage 1 does not shorten what they are owed. Each line is one
   write(2), so lines of several processes never interleave inside a line. */
typedef unsigned long U;
typedef long L;

/* --- system calls ------------------------------------------------------------------------- */
static L sc6(L n, L a, L b, L c, L d, L e, L f) {
    L r;
    register L r10 __asm__("r10") = d;
    register L r8 __asm__("r8") = e;
    register L r9 __asm__("r9") = f;
    __asm__ volatile("syscall" : "=a"(r) : "a"(n), "D"(a), "S"(b), "d"(c), "r"(r10), "r"(r8), "r"(r9)
                     : "rcx", "r11", "memory");
    return r;
}
#define sc(n, a, b, c) sc6((n), (L)(a), (L)(b), (L)(c), 0, 0, 0)
enum {
    NR_READ = 0, NR_WRITE = 1, NR_OPEN = 2, NR_CLOSE = 3, NR_MMAP = 9, NR_MPROTECT = 10, NR_MUNMAP = 11,
    NR_SIGACTION = 13, NR_SIGPROCMASK = 14, NR_YIELD = 24, NR_MADVISE = 28, NR_NANOSLEEP = 35, NR_GETPID = 39, NR_CLONE = 56,
    NR_FORK = 57, NR_EXECVE = 59, NR_EXIT = 60, NR_WAIT4 = 61, NR_KILL = 62, NR_GETRUSAGE = 98,
    NR_REBOOT = 169, NR_GETTID = 186, NR_FUTEX = 202, NR_SETAFFINITY = 203, NR_GETAFFINITY = 204,
    NR_CLOCK_GETTIME = 228, NR_EXIT_GROUP = 231, NR_TGKILL = 234, NR_PIPE2 = 293
};
enum { SIGKILL = 9, SIGUSR1 = 10, SIGSEGV = 11, SIGUSR2 = 12, SIGCONT = 18, SIGSTOP = 19 };
enum { WNOHANG = 1, WUNTRACED = 2, WCONTINUED = 8 };
#define PROT_RW 3
#define PROT_R 1
#define MAP_SHARED_ANON 0x21
#define MAP_PRIVATE_ANON 0x22
#define MAP_FIXED 0x10

static void exit_thread(int st) { for (;;) sc(NR_EXIT, st, 0, 0); }
static void exit_group(int st) { for (;;) sc(NR_EXIT_GROUP, st, 0, 0); }
static L gettid(void) { return sc(NR_GETTID, 0, 0, 0); }
static L getpid(void) { return sc(NR_GETPID, 0, 0, 0); }
static L fork(void) { return sc(NR_FORK, 0, 0, 0); }
static void yield(void) { sc(NR_YIELD, 0, 0, 0); }
static L wait4(L pid, int *st, L opt, void *ru) { return sc6(NR_WAIT4, pid, (L)st, opt, (L)ru, 0, 0); }
static void *map(U len, L prot, L flags) { return (void *)sc6(NR_MMAP, 0, (L)len, prot, flags, -1, 0); }
static void *shared_page(void) { return map(4096, PROT_RW, MAP_SHARED_ANON); }
static int futex(volatile int *w, L op, L val) { return (int)sc6(NR_FUTEX, (L)w, op, val, 0, 0, 0); }
#define FUTEX_WAIT 0
#define FUTEX_WAIT_PRIVATE 128
#define FUTEX_WAKE_PRIVATE 129

/* gcc may call these even when freestanding. */
void *memset(void *d, int c, U n) { void *r = d; __asm__ volatile("rep stosb" : "+D"(d), "+c"(n) : "a"(c) : "memory"); return r; }
void *memcpy(void *d, const void *s, U n) { void *r = d; __asm__ volatile("rep movsb" : "+D"(d), "+S"(s), "+c"(n) :: "memory"); return r; }

/* --- lines ------------------------------------------------------------------------------- */
struct ln { U n; char b[1500]; };
static void lc(struct ln *l, char c) { if (l->n < sizeof l->b - 2) l->b[l->n++] = c; }
static void ls(struct ln *l, const char *s) { while (*s) lc(l, *s++); }
static void ld(struct ln *l, U v) {
    char t[24]; int i = 24;
    do { t[--i] = (char)('0' + v % 10); v /= 10; } while (v);
    while (i < 24) lc(l, t[i++]);
}
static void lsd(struct ln *l, L v) { if (v < 0) { lc(l, '-'); ld(l, (U)-v); } else ld(l, (U)v); }
static void lx(struct ln *l, U v) {
    char t[20]; int i = 20;
    do { t[--i] = "0123456789abcdef"[v & 15]; v >>= 4; } while (v);
    ls(l, "0x");
    while (i < 20) lc(l, t[i++]);
}
static void lcpu(struct ln *l, L c) { if (c < 0) lc(l, '-'); else ld(l, (U)c); }
static void le(struct ln *l) { l->b[l->n++] = '\n'; sc(NR_WRITE, 1, l->b, l->n); l->n = 0; }
static void say(const char *s) { struct ln l; l.n = 0; ls(&l, s); le(&l); }
static int same(const char *a, const char *b) { while (*a && *a == *b) { a++; b++; } return *a == *b; }

/* --- time -------------------------------------------------------------------------------- */
static U rdtsc(void) { U lo, hi; __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi)); return lo | hi << 32; }
static U mono_ns(void) { U ts[2]; sc(NR_CLOCK_GETTIME, 1, ts, 0); return ts[0] * 1000000000ul + ts[1]; }
static void nap(U ns) { U ts[2] = { ns / 1000000000ul, ns % 1000000000ul }; sc(NR_NANOSLEEP, ts, 0, 0); }
static U tsc_hz = 1;
static U us_of(U cycles) { U mhz = tsc_hz / 1000000; return cycles / (mhz ? mhz : 1); }
static U cycles_of_ms(U ms) { return tsc_hz / 1000 * ms; }
static void calibrate_tsc(void) {
    U a = mono_ns(), b, c;
    do { b = mono_ns(); } while (b == a);
    U t0 = rdtsc();
    do { c = mono_ns(); } while (c < b + 300000000ul);
    U t1 = rdtsc();
    tsc_hz = (t1 - t0) * 1000000000ul / (c - b);
}
/* Wait for *w != 0 up to ms milliseconds of TSC time, yielding the processor between looks (at
   stage 1 the thread waited for shares the one processor). Returns whether it came. */
static int await(volatile U *w, U ms) {
    U end = rdtsc() + cycles_of_ms(ms);
    while (!*w) { if (rdtsc() > end) return 0; yield(); }
    return 1;
}

/* --- work -------------------------------------------------------------------------------- */
static U work(U n) {
    U x = 88172645463325252ul;
    for (U i = 0; i < n; i++) { x ^= x << 13; x ^= x >> 7; x ^= x << 17; __asm__ volatile("" : "+r"(x)); }
    return x;
}
static U loops_per_ms = 1;
static void calibrate_work(void) {
    for (U n = 1ul << 18;; n <<= 1) {
        U t0 = rdtsc();
        work(n);
        U us = us_of(rdtsc() - t0);
        if (us >= 50000 || n >= 1ul << 36) { loops_per_ms = n * 1000 / (us ? us : 1); if (!loops_per_ms) loops_per_ms = 1; return; }
    }
}

/* --- /proc/pax-cpus ----------------------------------------------------------------------- */
static char pbuf[32768];
static L readfile(const char *path, char *buf, U cap) {
    L fd = sc(NR_OPEN, path, 0, 0);
    if (fd < 0) return -1;
    U n = 0;
    for (;;) {
        L k = sc(NR_READ, fd, buf + n, cap - 1 - n > 4096 ? 4096 : cap - 1 - n);
        if (k < 0) { sc(NR_CLOSE, fd, 0, 0); return -1; }
        if (!k || n + (U)k >= cap - 1) { n += (U)k; break; }
        n += (U)k;
    }
    buf[n] = 0;
    sc(NR_CLOSE, fd, 0, 0);
    return (L)n;
}
static void census(const char *tag) {
    struct ln l;
    L n = readfile("/proc/pax-cpus", pbuf, sizeof pbuf);
    l.n = 0; ls(&l, "SMP-PROC "); ls(&l, tag); ls(&l, n < 0 ? " missing" : " begin"); le(&l);
    if (n < 0) return;
    sc(NR_WRITE, 1, pbuf, n);
    l.n = 0; ls(&l, "SMP-PROC "); ls(&l, tag); ls(&l, " end"); le(&l);
}
#define MAXC 64
enum { ST_NONE, ST_BOOT, ST_RUNS, ST_IDLE, ST_STOPPED, ST_NEVER, ST_PARKED, ST_OTHER };
#define CUR_IDLE (-1)
#define CUR_KERNEL (-2)
#define CUR_NONE (-3)
struct snap { L active, started, sset, smerged, staken, sslept; int n; int st[MAXC]; L cur[MAXC], user[MAXC], tlb[MAXC], resched[MAXC]; };
static const char *find(const char *s, const char *e, const char *pat) {
    for (; s < e; s++) {
        const char *a = s, *p = pat;
        while (*p && a < e && *a == *p) { a++; p++; }
        if (!*p) return s;
    }
    return 0;
}
static L num(const char *s, const char *e) {
    if (!s || s >= e || *s < '0' || *s > '9') return -1;
    L v = 0;
    while (s < e && *s >= '0' && *s <= '9') v = v * 10 + (*s++ - '0');
    return v;
}
static L after(const char *s, const char *e, const char *key) {
    const char *k = find(s, e, key);
    if (!k) return -1;
    while (*key) { k++; key++; }
    return num(k, e);
}
static int starts(const char *s, const char *e, const char *w) { while (*w) { if (s >= e || *s != *w) return 0; s++; w++; } return 1; }
static int take(struct snap *z) {
    L n = readfile("/proc/pax-cpus", pbuf, sizeof pbuf);
    z->n = 0; z->active = z->started = z->sset = z->smerged = z->staken = z->sslept = -1;
    if (n < 0) return 0;
    const char *e = pbuf + n;
    z->active = after(pbuf, e, "\nactive ");
    z->started = after(pbuf, e, "\nstarted ");
    /* the kernel's signal counts (kernel/sched's `signal_counts`): the sleeper's instrument */
    z->sset = after(pbuf, e, "\nsignals set ");
    z->smerged = after(pbuf, e, " merged ");
    z->staken = after(pbuf, e, " taken ");
    z->sslept = after(pbuf, e, " slept-with-one-pending ");
    for (const char *s = pbuf; s < e;) {
        const char *t = s;
        while (t < e && *t != '\n') t++;
        if (starts(s, t, "cpu ")) {
            L i = num(s + 4, t);
            const char *a = find(s, t, " apic ");
            if (i >= 0 && i < MAXC && a) {
                a += 6;
                while (a < t && *a != ' ') a++;
                a++;
                z->st[i] = starts(a, t, "boot") ? ST_BOOT : starts(a, t, "runs") ? ST_RUNS : starts(a, t, "idle") ? ST_IDLE
                         : starts(a, t, "stopped") ? ST_STOPPED : starts(a, t, "never") ? ST_NEVER
                         : starts(a, t, "parked") ? ST_PARKED : ST_OTHER;
                L p = after(s, t, " current pid ");
                z->cur[i] = p >= 0 ? p : find(s, t, " current idle") ? CUR_IDLE : find(s, t, " current kernel") ? CUR_KERNEL : CUR_NONE;
                z->user[i] = after(s, t, " user ");
                z->tlb[i] = after(s, t, " tlb ");
                z->resched[i] = after(s, t, " resched ");
                if (i + 1 > z->n) z->n = (int)i + 1;
            }
        }
        s = t + 1;
    }
    return 1;
}
static L cpu_of(const struct snap *z, L tid) {
    for (int i = 0; i < z->n; i++) if (z->cur[i] == tid) return i;
    return -1;
}
static L tlb_sum(const struct snap *z) {
    L s = 0;
    for (int i = 0; i < z->n; i++) { if (z->tlb[i] < 0) return -1; s += z->tlb[i]; }
    return s;
}
static void ldelta(struct ln *l, L a, L b) { if (a < 0 || b < 0) lc(l, '-'); else { lc(l, '+'); lsd(l, b - a); } }
/* The kB a /proc file gives `key` (`MemFree:`, `VmRSS:`): the key, tabs or spaces, the value; 0 when absent. */
static U kb_of(const char *path, const char *key) {
    static char m[8192];
    L n = readfile(path, m, sizeof m);
    if (n < 0) return 0;
    const char *k = find(m, m + n, key);
    if (!k) return 0;
    while (*key) { k++; key++; }
    while (k < m + n && (*k == ' ' || *k == '\t')) k++; /* `MemFree:\t` then the value padded to eight */
    L v = num(k, m + n);
    return v < 0 ? 0 : (U)v;
}
static U memfree_kb(void) { return kb_of("/proc/meminfo", "MemFree:"); }

/* --- threads ------------------------------------------------------------------------------ */
#define THREAD_FLAGS (0x100 | 0x200 | 0x400 | 0x800 | 0x10000 | 0x40000 | 0x100000 | 0x200000)
struct thr { volatile int tid; void *stack; };
#define STACK (64 * 1024)
/* clone(2) with a stack of its own: the child pops its function and argument, calls it with the
   stack 16-aligned, and leaves through exit(2) (this thread alone). CLONE_PARENT_SETTID and
   CLONE_CHILD_CLEARTID name t->tid: the tid now, 0 and a futex wake at the thread's end. */
static L spawn(struct thr *t, void (*fn)(void *), void *arg) {
    t->stack = map(STACK, PROT_RW, MAP_PRIVATE_ANON);
    void **sp = (void **)((char *)t->stack + STACK);
    *--sp = arg;
    *--sp = (void *)fn;
    L r;
    register L r10 __asm__("r10") = (L)&t->tid;
    register L r8 __asm__("r8") = 0;
    __asm__ volatile("syscall\n\t"
                     "test %%rax, %%rax\n\t"
                     "jnz 1f\n\t"
                     "xor %%ebp, %%ebp\n\t"
                     "pop %%rax\n\t"
                     "pop %%rdi\n\t"
                     "and $-16, %%rsp\n\t"
                     "call *%%rax\n\t"
                     "mov $60, %%eax\n\t"
                     "xor %%edi, %%edi\n\t"
                     "syscall\n\t"
                     "ud2\n"
                     "1:"
                     : "=a"(r)
                     : "a"(NR_CLONE), "D"(THREAD_FLAGS), "S"(sp), "d"(&t->tid), "r"(r10), "r"(r8)
                     : "rcx", "r11", "memory");
    return r;
}
/* The kernel's clear-child-tid wake at a thread's end is a wake WITHOUT the private flag (as on Linux, and as
   a threading library's join waits), so this wait is not private either: a private wait is never reached by it,
   and a join that began before the thread ended would wait for ever (the first development take's stress). */
static void join(struct thr *t) {
    for (;;) { int v = t->tid; if (!v) break; futex(&t->tid, FUTEX_WAIT, v); }
    sc(NR_MUNMAP, t->stack, STACK, 0);
}

/* --- signals ------------------------------------------------------------------------------ */
struct ksa { void (*h)(int); U flags; void (*restorer)(void); U mask; };
extern void smp_restorer(void);
__asm__(".text\n.globl smp_restorer\n.type smp_restorer, @function\nsmp_restorer:\n\tmov $15, %eax\n\tsyscall\n\tud2\n");
static void on(int sig, void (*h)(int)) {
    struct ksa a = { h, h ? 0x04000000ul : 0, h ? smp_restorer : 0, 0 }; /* SA_RESTORER */
    sc6(NR_SIGACTION, sig, (L)&a, 0, 8, 0, 0);
}

/* One page every scenario's processes share (MAP_SHARED, so across fork too). */
struct sh {
    volatile U ready, stop, go, done, phase, hit, count, spins, got, wpid;
    volatile U fault_tsc, btid, reads, stale, started, running, cpumask;
    volatile U ttid, thit, t2, tready;
    volatile U ht[16]; /* the sleeper's rounds: when the handler took each SIGUSR1, in order */
    volatile U pids[16];
    volatile L gtids[4]; /* SMP-DEAD: the group's four thread ids, written by its main thread */
    volatile U wsamples, wsampon, widle[MAXC]; /* SMP-WAIT's sampler: its reads, the processors it sat on, each one's idle reads */
    volatile U rss; /* SMP-EXIT: the group's VmRSS in kB, read by its main thread before the exec */
};
static struct sh *G;
__attribute__((force_align_arg_pointer)) static void h_usr1(int s) { (void)s; G->hit = rdtsc(); __atomic_add_fetch(&G->count, 1, __ATOMIC_SEQ_CST); }
__attribute__((force_align_arg_pointer)) static void h_usr2(int s) { (void)s; G->ttid = (U)gettid(); G->thit = rdtsc(); }
__attribute__((force_align_arg_pointer)) static void h_count(int s) { (void)s; __atomic_add_fetch(&G->got, 1, __ATOMIC_SEQ_CST); }
__attribute__((force_align_arg_pointer)) static void h_round(int s) {
    (void)s;
    U t = rdtsc(), n = __atomic_add_fetch(&G->count, 1, __ATOMIC_SEQ_CST);
    if (n <= 16) G->ht[n - 1] = t;
    G->hit = t;
}
__attribute__((force_align_arg_pointer)) static void h_segv(int s) { (void)s; G->fault_tsc = rdtsc(); exit_thread(0); }

static char **envp;
static L started_cpus = 1;

/* --- SMP-ACTIVE --------------------------------------------------------------------------- */
static void row_active(void) {
    static char on_buf[256];
    U mask[16];
    memset(mask, 0, sizeof mask);
    struct ln l; l.n = 0;
    ls(&l, "SMP-ACTIVE online ");
    L n = readfile("/sys/devices/system/cpu/online", on_buf, sizeof on_buf);
    if (n <= 0) ls(&l, "-");
    else { for (L i = 0; i < n && on_buf[i] != '\n'; i++) lc(&l, on_buf[i]); }
    L r = sc(NR_GETAFFINITY, 0, sizeof mask, mask);
    ls(&l, " affinity-ret "); lsd(&l, r); ls(&l, " mask "); lx(&l, mask[0]);
    U all = started_cpus >= 64 ? ~0ul : (1ul << started_cpus) - 1;
    L r2 = sc(NR_SETAFFINITY, 0, 8, &all);
    ls(&l, " setaffinity-ret "); lsd(&l, r2);
    /* proc_pid_status(5)'s two processor lines, as written (tabs and all, to the line's end). */
    static char st_buf[8192];
    L k = readfile("/proc/self/status", st_buf, sizeof st_buf);
    const char *keys[] = { "\nCpus_allowed:\t", "\nCpus_allowed_list:\t" };
    const char *names[] = { " cpus-allowed ", " cpus-allowed-list " };
    for (int i = 0; i < 2; i++) {
        ls(&l, names[i]);
        const char *p = k > 0 ? find(st_buf, st_buf + k, keys[i]) : 0;
        if (!p) { lc(&l, '-'); continue; }
        for (p += i ? 20 : 15; p < st_buf + k && *p != '\n'; p++) lc(&l, *p);
    }
    le(&l);
}

/* --- SMP-RUN ------------------------------------------------------------------------------ */
struct rus { U us, uus, ss, sus; L rest[14]; };
static U cpu_us(const struct rus *r) { return r->us * 1000000 + r->uus + r->ss * 1000000 + r->sus; }
/* The sampler reads /proc/pax-cpus from ring 3, so the processor it runs on shows the sampler itself, never a
   worker: each line names the sampler's pid (rows.py says where it sat) and the time since the phase began. Its naps
   are 50, 60 and 70 ms in turn, whole ticks that are not all multiples of the scheduler's two-tick quantum, so its
   reads do not lock to one point of the workers' rotation (sched2b-smoke's 25 reads, 8 ticks apart, all caught the
   same worker on CPU 1). */
static void sampler(int round) {
    struct snap z;
    struct ln l;
    L me = getpid();
    U t0 = rdtsc();
    for (int k = 0; !G->done && k < 2000; k++) {
        nap((U)(5 + k % 3) * 10000000ul);
        if (G->done || !take(&z)) break;
        l.n = 0; ls(&l, "SMP-RUN round "); ld(&l, (U)round); ls(&l, " sample "); ld(&l, (U)k);
        ls(&l, " at-us "); ld(&l, us_of(rdtsc() - t0)); ls(&l, " sampler "); lsd(&l, me);
        for (int i = 0; i < z.n; i++) {
            lc(&l, ' '); ld(&l, (U)i); lc(&l, ':');
            if (z.cur[i] >= 0) ld(&l, (U)z.cur[i]); else lc(&l, z.cur[i] == CUR_IDLE ? 'i' : z.cur[i] == CUR_KERNEL ? 'k' : '-');
        }
        le(&l);
    }
    exit_group(0);
}
static void run_round(int round, int jobs, U loops) {
    struct ln l;
    int st;
    struct rus ru;
    /* The lone worker. */
    U t0 = rdtsc();
    L p = fork();
    if (!p) { work(loops); exit_group(0); }
    memset(&ru, 0, sizeof ru);
    L w = wait4(p, &st, 0, &ru);
    U t1 = rdtsc();
    l.n = 0; ls(&l, "SMP-RUN round "); ld(&l, (U)round); ls(&l, " lone wall-us "); ld(&l, us_of(t1 - t0));
    ls(&l, " cpu-us "); ld(&l, cpu_us(&ru)); ls(&l, " status "); lx(&l, w == p ? (U)st : 0xdead); le(&l);
    /* jobs workers at once, a sampler beside them. */
    struct snap z0, z1;
    take(&z0);
    U m0 = mono_ns();
    G->done = 0;
    L sp = fork();
    if (!sp) sampler(round);
    L pids[MAXC];
    t0 = rdtsc();
    for (int i = 0; i < jobs; i++) { pids[i] = fork(); if (!pids[i]) { work(loops); exit_group(0); } }
    U cu[MAXC], bad = 0;
    for (int i = 0; i < jobs; i++) {
        memset(&ru, 0, sizeof ru);
        w = wait4(pids[i], &st, 0, &ru);
        cu[i] = cpu_us(&ru);
        if (w != pids[i] || st != 0) bad++;
    }
    t1 = rdtsc();
    U m1 = mono_ns();
    G->done = 1;
    wait4(sp, &st, 0, 0);
    take(&z1);
    l.n = 0; ls(&l, "SMP-RUN round "); ld(&l, (U)round); ls(&l, " workers");
    for (int i = 0; i < jobs; i++) { lc(&l, ' '); lsd(&l, pids[i]); }
    le(&l);
    l.n = 0; ls(&l, "SMP-RUN round "); ld(&l, (U)round); ls(&l, " jobs "); ld(&l, (U)jobs); ls(&l, " wall-us "); ld(&l, us_of(t1 - t0));
    ls(&l, " cpu-us");
    for (int i = 0; i < jobs; i++) { lc(&l, i ? ',' : ' '); ld(&l, cu[i]); }
    ls(&l, " bad-status "); ld(&l, bad); le(&l);
    l.n = 0; ls(&l, "SMP-RUN round "); ld(&l, (U)round); ls(&l, " phase-ticks "); ld(&l, (m1 - m0) / 10000000ul); ls(&l, " user-ticks");
    for (int i = 0; i < z1.n; i++) { lc(&l, ' '); ld(&l, (U)i); lc(&l, ':'); ldelta(&l, i < z0.n ? z0.user[i] : -1, z1.user[i]); }
    le(&l);
}
static void row_run(int jobs, int rounds) {
    U loops = loops_per_ms * 1000; /* one second of work alone */
    struct ln l; l.n = 0;
    ls(&l, "SMP-RUN jobs "); ld(&l, (U)jobs); ls(&l, " loops "); ld(&l, loops); le(&l);
    for (int r = 0; r < rounds; r++) run_round(r, jobs, loops);
    say("SMP-RUN done");
}

/* --- SMP-TLB ------------------------------------------------------------------------------ */
#define PAT_X 0x1111111111111111ul
#define PAT_Y 0x2222222222222222ul
static void b_protect(void *arg) {
    volatile U *p = arg;
    G->btid = (U)gettid();
    for (;;) {
        U v = *p;
        __asm__ volatile("" :: "r"(v));
        G->reads++;
        G->ready = 1;
        if (G->stop) return;
    }
}
static void b_replace(void *arg) {
    volatile U *p = arg;
    G->btid = (U)gettid();
    for (;;) {
        if (p[0] == PAT_X) G->ready = 1;
        if (__atomic_load_n(&G->phase, __ATOMIC_ACQUIRE)) break;
        if (G->stop) return;
    }
    U stale = 0;
    for (U i = 0; i < 200000; i++) if (p[0] != PAT_Y || p[1] != 0) stale++;
    G->stale = stale;
    G->reads = 200000;
    G->done = 1;
}
static void tlb_head(struct ln *l, const char *what, int r) { l->n = 0; ls(l, "SMP-TLB "); ls(l, what); lc(l, ' '); ld(l, (U)r); }
static void tlb_cpus(struct ln *l, struct snap *z) {
    ls(l, " a-cpu "); lcpu(l, cpu_of(z, gettid()));
    ls(l, " b-cpu "); lcpu(l, cpu_of(z, (L)G->btid));
}
static void tlb_protect(int r) {
    struct thr t;
    struct snap z0, z1;
    struct ln l;
    volatile U *p = map(4096, PROT_RW, MAP_PRIVATE_ANON);
    p[0] = PAT_X;
    G->ready = G->stop = G->fault_tsc = G->btid = G->reads = 0;
    spawn(&t, b_protect, (void *)p);
    int up = await(&G->ready, 2000);
    take(&z0);
    U t0 = rdtsc();
    L m = sc(NR_MPROTECT, p, 4096, 0);
    U t1 = rdtsc();
    int faulted = await(&G->fault_tsc, 2000);
    if (!faulted) G->stop = 1;
    join(&t);
    take(&z1);
    tlb_head(&l, "protect", r);
    ls(&l, faulted ? " faulted yes latency-us " : " faulted no latency-us ");
    if (faulted) ld(&l, us_of(G->fault_tsc - t0)); else lc(&l, '-');
    ls(&l, " call-us "); ld(&l, us_of(t1 - t0)); ls(&l, " mprotect "); lsd(&l, m);
    tlb_cpus(&l, &z0);
    ls(&l, " tlb "); ldelta(&l, tlb_sum(&z0), tlb_sum(&z1));
    ls(&l, " reads "); ld(&l, G->reads); ls(&l, up ? "" : " b-never-ready");
    le(&l);
    sc(NR_MUNMAP, p, 4096, 0);
}
static void tlb_replace(int r) {
    struct thr t;
    struct snap z0, z1;
    struct ln l;
    volatile U *p = map(4096, PROT_RW, MAP_PRIVATE_ANON);
    p[0] = PAT_X; p[1] = PAT_X;
    G->ready = G->stop = G->phase = G->done = G->stale = G->reads = G->btid = G->fault_tsc = 0;
    spawn(&t, b_replace, (void *)p);
    int up = await(&G->ready, 2000);
    take(&z0);
    L m = sc6(NR_MMAP, (L)p, 4096, PROT_RW, MAP_PRIVATE_ANON | MAP_FIXED, -1, 0);
    p[0] = PAT_Y;
    __atomic_store_n(&G->phase, 1, __ATOMIC_RELEASE);
    int done = await(&G->done, 2000);
    if (!done) G->stop = 1;
    join(&t);
    take(&z1);
    tlb_head(&l, "replace", r);
    ls(&l, " stale ");
    if (done) ld(&l, G->stale); else lc(&l, '-');
    ls(&l, " reads "); ld(&l, G->reads); ls(&l, m == (L)p ? " fixed yes" : " fixed no");
    /* B's SIGSEGV (h_segv: the time, then its thread ends): a fault on the page while A replaced it, refused when
       it was routed although the new page was present by then */
    ls(&l, G->fault_tsc ? " b-fault yes" : " b-fault no");
    tlb_cpus(&l, &z0);
    ls(&l, " tlb "); ldelta(&l, tlb_sum(&z0), tlb_sum(&z1));
    ls(&l, up ? "" : " b-never-ready");
    le(&l);
    sc(NR_MUNMAP, p, 4096, 0);
}
static void row_tlb(int rounds) {
    on(SIGSEGV, h_segv);
    for (int r = 0; r < rounds; r++) tlb_protect(r);
    for (int r = 0; r < rounds; r++) tlb_replace(r);
    on(SIGSEGV, 0);
    say("SMP-TLB done");
}

/* --- SMP-SIGNAL --------------------------------------------------------------------------- */
static void spin_forever(void) { for (;;) G->spins++; }
static L spinner(void) {
    G->ready = 0;
    L p = fork();
    if (!p) { G->wpid = (U)getpid(); G->ready = 1; spin_forever(); }
    await(&G->ready, 2000);
    return p;
}
static void sig_cpus(struct ln *l, const char *who, L tid) {
    struct snap z;
    take(&z);
    lc(l, ' '); ls(l, who); ls(l, "-cpu "); lcpu(l, cpu_of(&z, tid));
    ls(l, " p-cpu "); lcpu(l, cpu_of(&z, gettid()));
}
static void t2_spin(void *arg) { (void)arg; G->t2 = (U)gettid(); G->tready = 1; for (;;) G->spins++; }
/* the sleeper: the second thread of a process whose main thread blocks SIGUSR1; it unblocks SIGUSR1 for itself and
   sleeps 10 ms at a time, so a SIGUSR1 sent to the process must wake it (tests/mpx3-threads' takers, which a record
   saw take 8 of 10 at four processors where Linux took 10) */
static void t2_sleep(void *arg) {
    (void)arg;
    U set = 1ul << (SIGUSR1 - 1);
    sc6(NR_SIGPROCMASK, 1, (L)&set, 0, 8, 0, 0); /* SIG_UNBLOCK */
    G->t2 = (U)gettid(); G->tready = 1;
    for (;;) nap(10000000);
}
static void row_signal(int samples) {
    struct ln l, c;
    int st = 0, st2 = 0;
    /* step 5's witness: each processor's RESCHEDs taken across the row (one snapshot before, one after) */
    static struct snap r0, r1;
    take(&r0);
    on(SIGUSR1, h_usr1);
    L w = spinner();
    for (int k = 0; k < samples; k++) {
        G->hit = 0;
        c.n = 0; sig_cpus(&c, "w", w);
        U t0 = rdtsc();
        sc(NR_KILL, w, SIGUSR1, 0);
        int got = await(&G->hit, 1000);
        l.n = 0; ls(&l, "SMP-SIGNAL usr1 "); ld(&l, (U)k); ls(&l, " latency-us ");
        if (got) ld(&l, us_of(G->hit - t0)); else lc(&l, '-');
        c.b[c.n] = 0; ls(&l, c.b); le(&l);
    }
    sc(NR_KILL, w, SIGSTOP, 0);
    L a = wait4(w, &st, WUNTRACED, 0);
    U s0 = G->spins; nap(30000000); U s1 = G->spins;
    sc(NR_KILL, w, SIGCONT, 0);
    L b = wait4(w, &st2, WCONTINUED, 0);
    nap(30000000); U s2 = G->spins;
    l.n = 0; ls(&l, "SMP-SIGNAL stop status "); lx(&l, a == w ? (U)st : 0xdead); ls(&l, " cont status "); lx(&l, b == w ? (U)st2 : 0xdead);
    ls(&l, s1 == s0 ? " held yes" : " held no"); ls(&l, s2 > s1 ? " resumed yes" : " resumed no"); le(&l);
    sc(NR_KILL, w, SIGKILL, 0);
    wait4(w, &st, 0, 0);
    on(SIGUSR1, 0);
    for (int k = 0; k < 5; k++) {
        w = spinner();
        c.n = 0; sig_cpus(&c, "w", w);
        U t0 = rdtsc();
        sc(NR_KILL, w, SIGKILL, 0);
        L r = wait4(w, &st, 0, 0);
        U t1 = rdtsc();
        l.n = 0; ls(&l, "SMP-SIGNAL kill "); ld(&l, (U)k); ls(&l, " latency-us "); ld(&l, us_of(t1 - t0));
        ls(&l, " status "); lx(&l, r == w ? (U)st : 0xdead); c.b[c.n] = 0; ls(&l, c.b); le(&l);
    }
    /* tgkill: a process of two threads; the second spins, the first sends it SIGUSR2. */
    G->tready = 0;
    L cp = fork();
    if (!cp) {
        struct thr t;
        on(SIGUSR2, h_usr2);
        spawn(&t, t2_spin, 0);
        await(&G->tready, 2000);
        for (int k = 0; k < samples; k++) {
            G->thit = 0; G->ttid = 0;
            c.n = 0; sig_cpus(&c, "t", (L)G->t2);
            U t0 = rdtsc();
            sc(NR_TGKILL, getpid(), G->t2, SIGUSR2);
            int got = await(&G->thit, 1000);
            l.n = 0; ls(&l, "SMP-SIGNAL tgkill "); ld(&l, (U)k); ls(&l, " latency-us ");
            if (got) ld(&l, us_of(G->thit - t0)); else lc(&l, '-');
            ls(&l, got && G->ttid == G->t2 ? " tid-ok yes" : " tid-ok no");
            c.b[c.n] = 0; ls(&l, c.b); le(&l);
        }
        exit_group(0);
    }
    L r = wait4(cp, &st, 0, 0);
    l.n = 0; ls(&l, "SMP-SIGNAL tgkill-status "); lx(&l, r == cp ? (U)st : 0xdead); le(&l);
    /* the sleeper: a SIGUSR1 to the process, which only its sleeping second thread may take, thirty times. The main
       thread spins while it waits (no yield), so its own processor does not take the sleeper: the kernel must wake
       it where it can run. Then twenty rounds of ten sent 5 ms apart with the main thread asleep between them, as
       the takers probe sends them: how many the sleeper took in each (SIGUSR1 is not queued, so one still pending
       when the next is sent is taken once) */
    G->tready = 0;
    L sp = fork();
    if (!sp) {
        struct thr t;
        U set = 1ul << (SIGUSR1 - 1);
        on(SIGUSR1, h_round);
        sc6(NR_SIGPROCMASK, 0, (L)&set, 0, 8, 0, 0); /* SIG_BLOCK: the main thread never takes it */
        spawn(&t, t2_sleep, 0);
        await(&G->tready, 2000);
        nap(20000000);
        for (int k = 0; k < 30; k++) {
            G->hit = 0;
            c.n = 0; sig_cpus(&c, "s", (L)G->t2);
            U t0 = rdtsc(), end = t0 + cycles_of_ms(1000);
            sc(NR_KILL, getpid(), SIGUSR1, 0);
            while (!G->hit && rdtsc() < end) ;
            l.n = 0; ls(&l, "SMP-SIGNAL sleeper "); ld(&l, (U)k); ls(&l, " latency-us ");
            if (G->hit) ld(&l, us_of(G->hit - t0)); else lc(&l, '-');
            c.b[c.n] = 0; ls(&l, c.b); le(&l);
            nap(20000000);
        }
        /* each round with its instrument: the worst time from a send to the handler's entry that took it (in order),
           and the kernel's signal counts across the round (raises that set the bit, raises merged into one pending,
           signals taken, sleeps entered with one pending) */
        static struct snap a0, a1;
        for (int round = 0; round < 20; round++) {
            U sent[10];
            G->count = 0;
            take(&a0);
            for (int k = 0; k < 10; k++) { sent[k] = rdtsc(); sc(NR_KILL, getpid(), SIGUSR1, 0); nap(5000000); }
            nap(50000000);
            take(&a1);
            /* each send's latency: to the first handler entry at or after it (entries are in time order; a send merged
               into one still pending is answered by that one's late entry, so the worst is the oldest pending signal's
               wait, not a pairing of the k-th entry with the k-th send, which a merge shifts by a send interval) */
            U n = G->count, worst = 0;
            for (int k = 0; k < 10; k++) {
                U d = cycles_of_ms(1000);
                for (U i = 0; i < n && i < 16; i++) if (G->ht[i] >= sent[k]) { d = G->ht[i] - sent[k]; break; }
                if (d > worst) worst = d;
            }
            l.n = 0; ls(&l, "SMP-SIGNAL sleeper-ten round "); ld(&l, (U)round); ls(&l, " taken "); ld(&l, n);
            ls(&l, " worst-us "); ld(&l, us_of(worst));
            ls(&l, " set "); lsd(&l, a0.sset < 0 || a1.sset < 0 ? -1 : a1.sset - a0.sset);
            ls(&l, " merged "); lsd(&l, a0.smerged < 0 || a1.smerged < 0 ? -1 : a1.smerged - a0.smerged);
            ls(&l, " took "); lsd(&l, a0.staken < 0 || a1.staken < 0 ? -1 : a1.staken - a0.staken);
            ls(&l, " slept-pending "); lsd(&l, a0.sslept < 0 || a1.sslept < 0 ? -1 : a1.sslept - a0.sslept);
            le(&l);
        }
        exit_group(0);
    }
    r = wait4(sp, &st, 0, 0);
    l.n = 0; ls(&l, "SMP-SIGNAL sleeper-status "); lx(&l, r == sp ? (U)st : 0xdead); le(&l);
    take(&r1);
    l.n = 0; ls(&l, "SMP-SIGNAL resched");
    for (int i = 0; i < r1.n; i++) {
        lc(&l, ' '); ld(&l, (U)i); lc(&l, ':');
        if (r0.resched[i] >= 0 && r1.resched[i] >= r0.resched[i]) ld(&l, (U)(r1.resched[i] - r0.resched[i])); else lc(&l, '-');
    }
    le(&l);
    say("SMP-SIGNAL done");
}

/* --- SMP-EXIT ----------------------------------------------------------------------------- */
static struct thr grp[3];
static void g_spin(void *arg) {
    U me = (U)arg;
    __atomic_add_fetch(&G->started, 1, __ATOMIC_SEQ_CST);
    for (;;) {
        if (G->go == 1 && me == 2) exit_group(8);
        if (G->go == 2 && me == 1) {
            char *argv[] = { "/bin/smpprobe", "exec-child", 0 };
            sc(NR_EXECVE, argv[0], argv, envp);
            exit_group(66);
        }
        G->spins++;
    }
}
/* In the group's own main thread: up to five looks 10 ms apart, the most of its four threads seen
   running on distinct processors in one look (the looker is one of them, running as it looks). */
static U group_running(void) {
    struct snap z;
    L tids[4] = { gettid(), grp[0].tid, grp[1].tid, grp[2].tid };
    U best = 0;
    for (int k = 0; k < 5; k++) {
        if (k) nap(10000000);
        if (!take(&z)) continue;
        U seen = 0;
        for (int i = 0; i < 4; i++) if (cpu_of(&z, tids[i]) >= 0) seen++;
        if (seen > best) best = seen;
    }
    return best;
}
static L group(int how) { /* how: 0 the main thread exits, 1 a sibling does, 2 a sibling execs */
    G->started = 0; G->go = 0; G->running = 0;
    L p = fork();
    if (!p) {
        for (U i = 0; i < 3; i++) spawn(&grp[i], g_spin, (void *)i);
        U end = rdtsc() + cycles_of_ms(2000);
        while (G->started < 3 && rdtsc() < end) yield();
        G->gtids[0] = gettid();
        for (U i = 0; i < 3; i++) G->gtids[i + 1] = grp[i].tid;
        G->running = group_running();
        if (how == 2) G->rss = kb_of("/proc/self/status", "VmRSS:");
        if (how == 0) exit_group(7);
        G->go = how == 1 ? 1 : 2;
        for (;;) G->spins++;
    }
    return p;
}
/* --- SMP-DEAD (the cap kind) --------------------------------------------------------------------
   The group's main thread calls exit_group while its siblings spin, one on the other processor that
   runs threads: that sibling is ended in place (DEAD) and must be switched off at its next tick or
   RESCHED, never queued again. Three rounds: the status within 2 s (WNOHANG, every 5 ms), then ten
   looks 10 ms apart for any of the group's thread ids still current on a processor. */
static void row_dead(void) {
    struct ln l;
    struct snap z;
    for (int r = 0; r < 3; r++) {
        for (int i = 0; i < 4; i++) G->gtids[i] = 0;
        int st = 0;
        L p = group(0), w = 0;
        U end = rdtsc() + cycles_of_ms(2000);
        while (w == 0 && rdtsc() < end) { w = wait4(p, &st, WNOHANG, 0); if (w == 0) nap(5000000); }
        U revived = 0;
        for (int k = 0; k < 10; k++) {
            nap(10000000);
            if (take(&z)) for (int i = 0; i < 4; i++) if (G->gtids[i] > 0 && cpu_of(&z, G->gtids[i]) >= 0) revived++;
        }
        l.n = 0; ls(&l, "SMP-DEAD round "); ld(&l, (U)r); ls(&l, " status "); lx(&l, w == p ? (U)st : 0xdead);
        ls(&l, " running "); ld(&l, G->running); ls(&l, " revived "); ld(&l, revived); le(&l);
        if (w != p) break;
    }
    say("SMP-DEAD done");
}
/* SMP-EXIT's settle after exec round child `p` was waited: every 5 ms, at most 2 s, until none of the round's four
   threads is current on any processor (/proc/pax-cpus), then a wait4 for `p` again, which finds no such child but runs
   the kernel's reap first (kernel/sched's wait_find); then MemFree. That reap frees the space the exec parked while an
   ended sibling's processor still held it in CR3 (kernel/sched's leave_space) and the siblings' stacks the departure
   rule put off. The round's own wait4 runs it too, but may run it before the last of those processors has switched,
   and nothing else reaps until the next fork. `ms` the wait, `left` the threads still current when it ended. */
static U settled_kb(L p, U *ms, U *left) {
    struct snap z;
    U t0 = rdtsc(), end = t0 + cycles_of_ms(2000);
    for (;;) {
        U k = 4;
        if (take(&z)) { k = 0; for (int i = 0; i < 4; i++) if (G->gtids[i] > 0 && cpu_of(&z, G->gtids[i]) >= 0) k++; }
        *left = k;
        if (!k || rdtsc() >= end) break;
        nap(5000000);
    }
    *ms = us_of(rdtsc() - t0) / 1000;
    int st;
    wait4(p, &st, WNOHANG, 0);
    return memfree_kb();
}
static void row_exit(void) {
    struct ln l;
    int st;
    for (int r = 0; r < 4; r++) {
        L p = group(r < 2 ? 0 : 1);
        L w = wait4(p, &st, 0, 0);
        l.n = 0; ls(&l, "SMP-EXIT group "); ld(&l, (U)r); ls(&l, r < 2 ? " exiter main" : " exiter sibling");
        ls(&l, " status "); lx(&l, w == p ? (U)st : 0xdead); ls(&l, " running "); ld(&l, G->running); ls(&l, " of 4"); le(&l);
    }
    /* Each exec round read twice: when its wait4 returns, and settled (`settled_kb`). The warm round's settled
       reading is `before`, the last round's `after`. */
    U before = 0, after = 0;
    for (int r = 0; r < 5; r++) {
        for (int i = 0; i < 4; i++) G->gtids[i] = 0;
        G->rss = 0;
        L p = group(2);
        L w = wait4(p, &st, 0, 0);
        U waited = memfree_kb(), ms = 0, left = 0;
        U settled = settled_kb(p, &ms, &left);
        if (r == 0) before = settled;
        after = settled;
        l.n = 0; ls(&l, "SMP-EXIT exec "); ld(&l, (U)r); ls(&l, r ? " measured" : " warm");
        ls(&l, " status "); lx(&l, w == p ? (U)st : 0xdead); ls(&l, " running "); ld(&l, G->running); ls(&l, " of 4");
        ls(&l, " rss-kb "); ld(&l, G->rss); ls(&l, " waited-kb "); ld(&l, waited); ls(&l, " settled-kb "); ld(&l, settled);
        ls(&l, " settle-ms "); ld(&l, ms); ls(&l, " left "); ld(&l, left); le(&l);
    }
    l.n = 0; ls(&l, "SMP-EXIT frames-kb before "); ld(&l, before); ls(&l, " after "); ld(&l, after); le(&l);
    struct snap z;
    take(&z);
    l.n = 0; ls(&l, "SMP-EXIT stopped");
    int any = 0;
    for (int i = 0; i < z.n; i++) if (z.st[i] == ST_STOPPED || z.st[i] == ST_NEVER) { lc(&l, ' '); ld(&l, (U)i); any = 1; }
    if (!any) ls(&l, " none");
    le(&l);
    say("SMP-EXIT done");
}

/* --- SMP-WAIT ----------------------------------------------------------------------------- */
static void wait_sampler(void) {
    struct snap z;
    L me = getpid();
    for (int k = 0; !G->done && k < 5000; k++) {
        nap(10000000);
        if (!take(&z)) continue;
        G->wsamples++;
        for (int i = 0; i < z.n && i < MAXC; i++) {
            for (int j = 0; j < 16; j++)
                if (G->pids[j] && z.cur[i] == (L)G->pids[j]) G->cpumask |= 1ul << i;
            if (z.cur[i] == me) G->wsampon |= 1ul << i;    /* where it sat: blind there this read */
            if (z.cur[i] == CUR_IDLE) G->widle[i]++;        /* a processor with no thread this read */
        }
    }
    exit_group(0);
}
static void row_wait(void) {
    struct ln l;
    struct rus r0, r1;
    struct snap z0, z1;
    int st;
    memset(&r0, 0, sizeof r0); memset(&r1, 0, sizeof r1);
    sc(NR_GETRUSAGE, -1, &r0, 0);
    /* the kernel's own per-processor ring-3 ticks, before the children and after them: the row counts the processors
       the children ran on from these, which no processor hides from (the sampler, below, never sees a child on the
       processor it runs on itself) */
    if (!take(&z0)) z0.n = 0;
    G->done = 0; G->cpumask = 0; G->wsamples = 0; G->wsampon = 0;
    for (int i = 0; i < MAXC; i++) G->widle[i] = 0;
    for (int j = 0; j < 16; j++) G->pids[j] = 0;
    L sp = fork();
    if (!sp) wait_sampler();
    L pids[16];
    U expect_us = 0;
    for (int i = 0; i < 16; i++) {
        expect_us += 20000ul * (U)(i + 1);
        pids[i] = fork();
        if (!pids[i]) { work(loops_per_ms * 20 * (U)(i + 1)); exit_group(i + 1); }
        G->pids[i] = (U)pids[i];
    }
    int right = 0;
    for (int k = 0; k < 16; k++) {
        L w = wait4(-1, &st, 0, 0);
        if (w == sp) { k--; continue; }
        for (int i = 0; i < 16; i++) if (pids[i] == w && (st & 0x7f) == 0 && ((st >> 8) & 0xff) == i + 1) right++;
    }
    G->done = 1;
    wait4(sp, &st, 0, 0);
    sc(NR_GETRUSAGE, -1, &r1, 0);
    if (!take(&z1)) z1.n = 0;
    l.n = 0; ls(&l, "SMP-WAIT statuses right "); ld(&l, (U)right); ls(&l, " of 16 cpu-us "); ld(&l, cpu_us(&r1) - cpu_us(&r0));
    ls(&l, " expected-us "); ld(&l, expect_us); ls(&l, " cpus");
    int any = 0;
    for (int i = 0; i < MAXC; i++) if (G->cpumask >> i & 1) { lc(&l, any ? ',' : ' '); ld(&l, (U)i); any = 1; }
    if (!any) ls(&l, " -");
    le(&l);
    l.n = 0; ls(&l, "SMP-WAIT user-ticks");
    for (int i = 0; i < z1.n; i++) { lc(&l, ' '); ld(&l, (U)i); lc(&l, ':'); ldelta(&l, i < z0.n ? z0.user[i] : -1, z1.user[i]); }
    le(&l);
    /* the RESCHEDs each processor took while the children ran (kernel/sched's share() sends one to the lowest-numbered
       idle processor with none in flight): a processor the ticks find starved either took some and found nothing, or
       took none */
    l.n = 0; ls(&l, "SMP-WAIT resched");
    for (int i = 0; i < z1.n; i++) { lc(&l, ' '); ld(&l, (U)i); lc(&l, ':'); ldelta(&l, i < z0.n ? z0.resched[i] : -1, z1.resched[i]); }
    le(&l);
    l.n = 0; ls(&l, "SMP-WAIT samples "); ld(&l, G->wsamples); ls(&l, " sampler-on ");
    any = 0;
    for (int i = 0; i < MAXC; i++) if (G->wsampon >> i & 1) { if (any) lc(&l, ','); ld(&l, (U)i); any = 1; }
    if (!any) lc(&l, '-');
    ls(&l, " idle");
    for (int i = 0; i < z1.n && i < MAXC; i++) { lc(&l, ' '); ld(&l, (U)i); lc(&l, ':'); ld(&l, G->widle[i]); }
    le(&l);
    say("SMP-WAIT done");
}

/* --- SMP-LOCK: the stress ------------------------------------------------------------------ */
static U deadline;
static int before_deadline(void) { return mono_ns() < deadline; }
static void c_forkwait(int i) {
    U k = 0, wrong = 0;
    int st;
    while (before_deadline()) {
        L p = fork();
        if (!p) exit_group((int)(k & 0x7f));
        if (wait4(p, &st, 0, 0) != p || (st & 0x7f) || ((st >> 8) & 0xff) != (int)(k & 0x7f)) wrong++;
        k++;
    }
    struct ln l; l.n = 0;
    ls(&l, "SMP-LOCK forkwait "); ld(&l, (U)i); ls(&l, " rounds "); ld(&l, k); ls(&l, " wrong "); ld(&l, wrong); le(&l);
    exit_group(wrong || !k);
}
static void c_pipe(int i) {
    int a[2], b[2], st;
    U k = 0, wrong = 0;
    if (sc(NR_PIPE2, a, 0, 0) || sc(NR_PIPE2, b, 0, 0)) { say("SMP-LOCK pipe pipe2 failed"); exit_group(2); }
    L p = fork();
    if (!p) {
        U v;
        sc(NR_CLOSE, a[1], 0, 0); sc(NR_CLOSE, b[0], 0, 0);
        for (;;) {
            L n = sc(NR_READ, a[0], &v, 8);
            if (n == 0) exit_group(0);
            if (n != 8) exit_group(3);
            v++;
            if (sc(NR_WRITE, b[1], &v, 8) != 8) exit_group(4);
        }
    }
    sc(NR_CLOSE, a[0], 0, 0); sc(NR_CLOSE, b[1], 0, 0);
    while (before_deadline()) {
        U v = k, r = 0;
        if (sc(NR_WRITE, a[1], &v, 8) != 8 || sc(NR_READ, b[0], &r, 8) != 8) { wrong++; break; }
        if (r != k + 1) wrong++;
        k++;
    }
    sc(NR_CLOSE, a[1], 0, 0);
    if (wait4(p, &st, 0, 0) != p || st) wrong++;
    struct ln l; l.n = 0;
    ls(&l, "SMP-LOCK pipe "); ld(&l, (U)i); ls(&l, " rounds "); ld(&l, k); ls(&l, " wrong "); ld(&l, wrong); le(&l);
    exit_group(wrong || !k);
}
static volatile int fw;
static volatile U f_rounds;
static void f_thread(void *arg) {
    (void)arg;
    for (;;) {
        int v;
        while ((v = __atomic_load_n(&fw, __ATOMIC_ACQUIRE)) != 1 && v != 3) futex(&fw, FUTEX_WAIT_PRIVATE, v);
        if (v == 3) return;
        f_rounds++;
        __atomic_store_n(&fw, 2, __ATOMIC_RELEASE);
        futex(&fw, FUTEX_WAKE_PRIVATE, 1);
    }
}
static void c_futex(int i) {
    struct thr t;
    U k = 0;
    fw = 0; f_rounds = 0;
    spawn(&t, f_thread, 0);
    while (before_deadline()) {
        __atomic_store_n(&fw, 1, __ATOMIC_RELEASE);
        futex(&fw, FUTEX_WAKE_PRIVATE, 1);
        int v;
        while ((v = __atomic_load_n(&fw, __ATOMIC_ACQUIRE)) != 2) futex(&fw, FUTEX_WAIT_PRIVATE, v);
        k++;
    }
    __atomic_store_n(&fw, 3, __ATOMIC_RELEASE);
    futex(&fw, FUTEX_WAKE_PRIVATE, 1);
    join(&t);
    U wrong = f_rounds != k;
    struct ln l; l.n = 0;
    ls(&l, "SMP-LOCK futex "); ld(&l, (U)i); ls(&l, " rounds "); ld(&l, k); ls(&l, " thread-rounds "); ld(&l, f_rounds);
    ls(&l, " wrong "); ld(&l, wrong); le(&l);
    exit_group(wrong || !k);
}
static volatile U *stable;
static volatile U c_stop, c_reads, c_bad;
static void c_reader(void *arg) {
    (void)arg;
    while (!c_stop) {
        for (int j = 0; j < 8; j++) if (stable[j * 64] != 0xc0ffee00ul + (U)j) c_bad++;
        c_reads++;
    }
}
static void c_churn(void) {
    struct thr t;
    U k = 0, wrong = 0;
    stable = map(4096, PROT_RW, MAP_PRIVATE_ANON);
    for (int j = 0; j < 8; j++) stable[j * 64] = 0xc0ffee00ul + (U)j;
    spawn(&t, c_reader, 0);
    while (before_deadline()) {
        volatile U *m = map(8 * 4096, PROT_RW, MAP_PRIVATE_ANON);
        if ((L)m < 0) { wrong++; break; }
        for (int j = 0; j < 8; j++) m[j * 512] = k + (U)j;
        if (sc(NR_MPROTECT, m, 8 * 4096, 1)) wrong++;
        for (int j = 0; j < 8; j++) if (m[j * 512] != k + (U)j) wrong++;
        if (sc(NR_MPROTECT, m, 8 * 4096, PROT_RW)) wrong++;
        if (sc(NR_MADVISE, m, 4096, 4) || m[0] != 0) wrong++; /* MADV_DONTNEED: a fresh zero page */
        if (sc(NR_MUNMAP, m, 8 * 4096, 0)) wrong++;
        k++;
    }
    c_stop = 1;
    join(&t);
    wrong += c_bad;
    struct ln l; l.n = 0;
    ls(&l, "SMP-LOCK churn ops "); ld(&l, k); ls(&l, " reader-reads "); ld(&l, c_reads); ls(&l, " wrong "); ld(&l, wrong); le(&l);
    exit_group(wrong || !k || !c_reads);
}
static void c_kill(void) {
    int st;
    U sent = 0, lost = 0;
    G = shared_page();
    on(SIGUSR1, h_count);
    L w = spinner();
    while (before_deadline()) {
        U c = G->got;
        sc(NR_KILL, w, SIGUSR1, 0);
        sent++;
        U end = rdtsc() + cycles_of_ms(1000);
        while (G->got == c && rdtsc() < end) yield();
        if (G->got == c) lost++;
    }
    sc(NR_KILL, w, SIGKILL, 0);
    wait4(w, &st, 0, 0);
    struct ln l; l.n = 0;
    ls(&l, "SMP-LOCK kill sent "); ld(&l, sent); ls(&l, " got "); ld(&l, G->got); ls(&l, " lost "); ld(&l, lost); le(&l);
    exit_group(lost || G->got != sent || !sent);
}
static void stress(U secs) {
    static const char *names[] = { "forkwait", "forkwait", "forkwait", "forkwait", "pipe", "pipe", "futex", "futex", "churn", "kill" };
    struct snap z0, z1;
    struct ln l;
    L pids[10];
    int st;
    take(&z0);
    deadline = mono_ns() + secs * 1000000000ul;
    for (int i = 0; i < 10; i++) {
        pids[i] = fork();
        if (pids[i]) continue;
        if (i < 4) c_forkwait(i);
        else if (i < 6) c_pipe(i - 4);
        else if (i < 8) c_futex(i - 6);
        else if (i == 8) c_churn();
        else c_kill();
    }
    /* Every component ends by itself soon after the deadline; one still there 30 s later is named as hung and
       ended with SIGKILL (its status then 0x9), so a hang is a red row by name and the boot still reaches its end. */
    int stv[10], left = 10;
    L gone[10];
    for (int i = 0; i < 10; i++) gone[i] = 0;
    while (left && mono_ns() < deadline + 30000000000ul) {
        L w = wait4(-1, &st, WNOHANG, 0);
        if (w <= 0) { nap(100000000); continue; }
        for (int i = 0; i < 10; i++) if (pids[i] == w && !gone[i]) { gone[i] = 1; stv[i] = st; left--; }
    }
    for (int i = 0; i < 10; i++) {
        if (gone[i]) continue;
        l.n = 0; ls(&l, "SMP-LOCK component "); ls(&l, names[i]); ls(&l, " pid "); lsd(&l, pids[i]);
        ls(&l, " hung 30 s past the deadline: SIGKILL"); le(&l);
        sc(NR_KILL, pids[i], SIGKILL, 0);
        if (wait4(pids[i], &st, 0, 0) == pids[i]) { gone[i] = 1; stv[i] = st; }
    }
    for (int i = 0; i < 10; i++) {
        l.n = 0; ls(&l, "SMP-LOCK component "); ls(&l, names[i]); ls(&l, " pid "); lsd(&l, pids[i]);
        ls(&l, " status "); lx(&l, gone[i] ? (U)stv[i] : 0xdead); le(&l);
    }
    take(&z1);
    l.n = 0; ls(&l, "SMP-LOCK user-ticks");
    for (int i = 0; i < z1.n; i++) { lc(&l, ' '); ld(&l, (U)i); lc(&l, ':'); ldelta(&l, i < z0.n ? z0.user[i] : -1, z1.user[i]); }
    le(&l);
    census("stress");
    say("SMP-LOCK done");
}

/* --- SMP-END ------------------------------------------------------------------------------- */
static void end(const char *how) {
    U cmd = same(how, "halt") ? 0xcdef0123ul : same(how, "poweroff") ? 0x4321fedcul : 0x01234567ul;
    struct snap z;
    struct ln l;
    L pids[MAXC];
    int n = (int)(started_cpus < MAXC ? started_cpus : MAXC);
    for (int i = 0; i < n; i++) { pids[i] = fork(); if (!pids[i]) for (;;) work(1ul << 20); }
    nap(200000000);
    take(&z);
    l.n = 0; ls(&l, "SMP-END spinners "); ld(&l, (U)n); ls(&l, " on cpus");
    int any = 0;
    for (int i = 0; i < z.n; i++) for (int j = 0; j < n; j++) if (z.cur[i] == pids[j]) { lc(&l, any ? ',' : ' '); ld(&l, (U)i); any = 1; }
    if (!any) ls(&l, " -");
    le(&l);
    l.n = 0; ls(&l, "SMP-END asking reboot(2) "); ls(&l, how); le(&l);
    L r = sc6(NR_REBOOT, 0xfee1deadl, 672274793l, (L)cmd, 0, 0, 0);
    l.n = 0; ls(&l, "SMP-END reboot(2) returned "); lsd(&l, r); le(&l);
    exit_group(1);
}

/* --- the panic kinds: a spinner on every processor until a test build's test panic stops them --- */
static void spin(void) {
    struct ln l;
    int n = (int)(started_cpus < MAXC ? started_cpus : MAXC);
    for (int i = 0; i < n; i++) { L p = fork(); if (!p) for (;;) work(1ul << 20); }
    l.n = 0; ls(&l, "SMP-PANIC spinners "); ld(&l, (U)n); le(&l);
    for (;;) nap(1000000000);
}

/* --- SMP-REFUSE (one processor runs threads: the one, nosmp and cap1 boots) ----------------------
   Faults the page tables refuse are still refused (kernel/vm retries a fault only when the page is present at its
   routing and allows the access): a write to a read-only page, a fetch from a page without PROT_EXEC, a read of the
   kernel's half. Each in a child whose SIGSEGV handler exits 11: `refused yes` is that status (0xb00), a child the
   access let through exits 0. */
__attribute__((force_align_arg_pointer)) static void h_refused(int s) { (void)s; exit_group(11); }
static void refuse_one(const char *what, int how) {
    struct ln l;
    int st = 0;
    L p = fork();
    if (!p) {
        on(SIGSEGV, h_refused);
        if (how == 0) {
            volatile U *q = map(4096, PROT_R, MAP_PRIVATE_ANON);
            q[0] = 1;
        } else if (how == 1) {
            volatile unsigned char *q = map(4096, PROT_RW, MAP_PRIVATE_ANON);
            q[0] = 0xc3; /* ret */
            ((void (*)(void))(U)q)();
        } else {
            volatile U *q = (volatile U *)0xffffffff80000000ul;
            U v = *q;
            __asm__ volatile("" :: "r"(v));
        }
        exit_group(0);
    }
    L w = wait4(p, &st, 0, 0);
    l.n = 0; ls(&l, "SMP-REFUSE "); ls(&l, what); ls(&l, w == p && st == 0xb00 ? " refused yes" : " refused no");
    ls(&l, " status "); lx(&l, w == p ? (U)st : 0xdead); le(&l);
}
static void row_refuse(void) {
    refuse_one("write-ro", 0);
    refuse_one("fetch-nx", 1);
    refuse_one("kernel-read", 2);
    say("SMP-REFUSE done");
}

/* --- the entry ------------------------------------------------------------------------------ */
__attribute__((used)) static void smp_main(U *sp) {
    int argc = (int)sp[0];
    char **argv = (char **)(sp + 1);
    envp = argv + argc + 1;
    const char *mode = argc > 1 ? argv[1] : "rows";
    struct ln l;
    if (same(mode, "exec-child")) {
        l.n = 0; ls(&l, "SMP-EXIT exec-child pid "); lsd(&l, getpid()); le(&l);
        exit_group(9);
    }
    G = shared_page();
    l.n = 0; ls(&l, "SMP-PROBE start mode "); ls(&l, mode); ls(&l, " pid "); lsd(&l, getpid()); le(&l);
    calibrate_tsc();
    calibrate_work();
    l.n = 0; ls(&l, "SMP-PROBE tsc-hz "); ld(&l, tsc_hz); ls(&l, " loops-per-ms "); ld(&l, loops_per_ms); le(&l);
    census("start");
    struct snap z;
    take(&z);
    started_cpus = z.started > 0 ? z.started : 1;
    if (same(mode, "stress")) {
        U secs = 0;
        for (const char *s = argc > 2 ? argv[2] : "20"; *s >= '0' && *s <= '9'; s++) secs = secs * 10 + (U)(*s - '0');
        stress(secs ? secs : 20);
    } else if (same(mode, "spin")) {
        spin();
    } else if (same(mode, "end")) {
        end(argc > 2 ? argv[2] : "halt");
    } else {
        row_active();
        if (same(mode, "cap")) {
            row_run((int)started_cpus, 1);
            G = shared_page();
            row_dead();
        } else if (same(mode, "one")) {
            row_refuse();
        } else if (same(mode, "rows")) {
            row_run((int)started_cpus, 3);
            G = shared_page();
            row_tlb(5);
            G = shared_page();
            row_signal(9);
            G = shared_page();
            row_exit();
            G = shared_page();
            row_wait();
        }
        census("end");
    }
    say("SMP-PROBE done");
    exit_group(0);
}
__asm__(".text\n.globl _start\n.type _start, @function\n_start:\n\txor %ebp, %ebp\n\tmov %rsp, %rdi\n\tand $-16, %rsp\n\tcall smp_main\n\tud2\n");
