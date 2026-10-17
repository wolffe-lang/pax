/* threads.c — px26's probe of threads, futexes and signals: one static
   glibc program that prints what it sees, run unmodified as the first
   program on Linux and on PAX (tests/mpx3-threads), its two outputs
   compared byte for byte. Every line is something a kernel decides:
   which ids a thread has, what `futex` answers, which handler runs
   first and with what siginfo, how the signal frame is laid out, that
   a handler's return puts back every register and the x87/SSE/AVX
   state, which system calls a handler interrupts and which run again,
   what a fatal signal leaves in a wait status.

     threads            every probe, in order
     threads soak       10,000 threads made and joined and 10,000
                        signals delivered to a handler, with the
                        program's own counters before and after
     threads exec       (a role the `exec` probe starts)

   Built with the host's cc: `cc -static -O1 -pthread` (tools/mkprobes).
   Lines that depend on the host's kernel and not on the ABI (whether
   MADV_GUARD_INSTALL exists) start with `~` and are not compared.
   Nothing here reads a kernel's or a libc's source: the calls are the
   man pages', the structures the public headers'. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <linux/futex.h>
#include <pthread.h>
#include <setjmp.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <time.h>
#include <ucontext.h>
#include <unistd.h>

static void say(const char *fmt, ...) {
    char b[512];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    if (n > (int)sizeof b - 1) n = sizeof b - 1;
    int o = 0;
    while (o < n) {
        ssize_t w = write(1, b + o, n - o);
        if (w <= 0) break;
        o += w;
    }
}

static long fut(void *a, int op, uint32_t v, void *t, void *a2, uint32_t v3) {
    return syscall(SYS_futex, a, op, v, t, a2, v3);
}
static pid_t tid(void) { return syscall(SYS_gettid); }
static void ms(int n) {
    struct timespec t = { n / 1000, (n % 1000) * 1000000L };
    while (nanosleep(&t, &t) != 0 && errno == EINTR) {}
}
static long now_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000 + t.tv_nsec / 1000000;
}
/* -1 with errno E as "-E", else the value */
static long r(long v) { return v == -1 ? -errno : v; }

static void act(int sig, void *fn, int flags) {
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    if (flags & SA_SIGINFO) sa.sa_sigaction = fn; else sa.sa_handler = fn;
    sa.sa_flags = flags;
    sigemptyset(&sa.sa_mask);
    sigaction(sig, &sa, 0);
}

/* ---- ids ---------------------------------------------------------------- */
static __thread int tl;
struct idw { pid_t pid, tid; int tlsaw; int n; };
static void *id_body(void *p) {
    struct idw *w = p;
    tl = 100 + w->n;
    w->pid = getpid();
    w->tid = tid();
    ms(20);
    w->tlsaw = tl;
    return (void *)(long)(w->n + 1);
}
static void ids(void) {
    pthread_t t[4];
    struct idw w[4];
    long sum = 0;
    int distinct = 1, same = 1, tls = 1;
    tl = 7;
    for (int i = 0; i < 4; i++) { w[i].n = i; pthread_create(&t[i], 0, id_body, &w[i]); }
    for (int i = 0; i < 4; i++) { void *v; pthread_join(t[i], &v); sum += (long)v; }
    for (int i = 0; i < 4; i++) {
        if (w[i].pid != getpid()) same = 0;
        if (w[i].tid == getpid() || w[i].tid <= 0) distinct = 0;
        for (int j = 0; j < i; j++) if (w[i].tid == w[j].tid) distinct = 0;
        if (w[i].tlsaw != 100 + i) tls = 0;
    }
    say("ids: main tid is pid %d; 4 threads joined, results sum %ld; each saw the process's pid %d, a tid of its own %d, its own thread-local %d; main's thread-local kept %d\n",
        tid() == getpid(), sum, same, distinct, tls, tl == 7);
    /* a tid that has ended: tgkill answers ESRCH */
    say("ids: tgkill of an ended thread's tid %ld, of another process's group %ld, signal 0 to self %ld\n",
        r(syscall(SYS_tgkill, getpid(), w[0].tid, 0)), r(syscall(SYS_tgkill, getpid() + 1000, tid(), 0)),
        r(syscall(SYS_tgkill, getpid(), tid(), 0)));
}

/* ---- futex --------------------------------------------------------------- */
static uint32_t fw;
static volatile int forder[3], fnext;
struct fq { int n; uint32_t bits; long ret; };
static void *f_wait(void *p) {
    struct fq *q = p;
    q->ret = r(q->bits ? fut(&fw, FUTEX_WAIT_BITSET | FUTEX_PRIVATE_FLAG, 0, 0, 0, q->bits)
                       : fut(&fw, FUTEX_WAIT | FUTEX_PRIVATE_FLAG, 0, 0, 0, 0));
    forder[__sync_fetch_and_add(&fnext, 1) % 3] = q->n;
    return 0;
}
static void futexes(void) {
    struct timespec rel = { 0, 30000000 }, past = { 0, 1 };
    pthread_t t[3];
    struct fq q[3];
    fw = 0;
    say("futex: wait on a changed word %ld", r(fut(&fw, FUTEX_WAIT, 1, 0, 0, 0)));
    long t0 = now_ms();
    long a = r(fut(&fw, FUTEX_WAIT, 0, &rel, 0, 0));
    say(", a 30 ms timeout %ld after at least 30 ms %d", a, now_ms() - t0 >= 29);
    say(", an absolute deadline in the past %ld", r(fut(&fw, FUTEX_WAIT_BITSET, 0, &past, 0, FUTEX_BITSET_MATCH_ANY)));
    say(", a zero bitset %ld, a wake with nobody waiting %ld\n", r(fut(&fw, FUTEX_WAIT_BITSET, 0, &rel, 0, 0)), r(fut(&fw, FUTEX_WAKE, 1, 0, 0, 0)));
    say("futex: a word off a 4-byte boundary %ld, an unreadable word %ld, a bad timespec %ld, an operation that does not exist %ld\n",
        r(fut((char *)&fw + 1, FUTEX_WAIT, 0, &rel, 0, 0)), r(fut((void *)4096, FUTEX_WAIT, 0, &rel, 0, 0)),
        r(fut(&fw, FUTEX_WAIT, 0, &(struct timespec){ 0, 2000000000 }, 0, 0)), r(fut(&fw, 77, 0, 0, 0, 0)));
    /* one waiter, one wake */
    q[0] = (struct fq){ 0, 0, 99 };
    pthread_create(&t[0], 0, f_wait, &q[0]);
    ms(80);
    long w1 = r(fut(&fw, FUTEX_WAKE | FUTEX_PRIVATE_FLAG, 1, 0, 0, 0));
    pthread_join(t[0], 0);
    say("futex: one waiter: wake answered %ld, the wait %ld", w1, q[0].ret);
    /* the same word without the private flag meets the private waiter */
    q[0] = (struct fq){ 0, 0, 99 };
    pthread_create(&t[0], 0, f_wait, &q[0]);
    ms(80);
    w1 = r(fut(&fw, FUTEX_WAKE, 1, 0, 0, 0));
    if (w1 == 0) fut(&fw, FUTEX_WAKE | FUTEX_PRIVATE_FLAG, 1, 0, 0, 0);
    pthread_join(t[0], 0);
    say("; a wake without the private flag reaches a private waiter %ld\n", w1);
    /* bitsets */
    q[0] = (struct fq){ 0, 2, 99 };
    pthread_create(&t[0], 0, f_wait, &q[0]);
    ms(80);
    long b1 = r(fut(&fw, FUTEX_WAKE_BITSET | FUTEX_PRIVATE_FLAG, 1, 0, 0, 1));
    long b2 = r(fut(&fw, FUTEX_WAKE_BITSET | FUTEX_PRIVATE_FLAG, 1, 0, 0, 6));
    pthread_join(t[0], 0);
    say("futex: a waiter with bitset 2: a wake with bitset 1 woke %ld, with bitset 6 woke %ld, the wait %ld\n", b1, b2, q[0].ret);
    /* three waiters, in order; wake 1, then 1, then all */
    fnext = 0;
    for (int i = 0; i < 3; i++) {
        q[i] = (struct fq){ i, 0, 99 };
        pthread_create(&t[i], 0, f_wait, &q[i]);
        ms(60);
    }
    long k1 = r(fut(&fw, FUTEX_WAKE | FUTEX_PRIVATE_FLAG, 1, 0, 0, 0));
    ms(60);
    long k2 = r(fut(&fw, FUTEX_WAKE | FUTEX_PRIVATE_FLAG, 1, 0, 0, 0));
    ms(60);
    long k3 = r(fut(&fw, FUTEX_WAKE | FUTEX_PRIVATE_FLAG, INT_MAX, 0, 0, 0));
    for (int i = 0; i < 3; i++) pthread_join(t[i], 0);
    say("futex: three waiters: wakes answered %ld %ld %ld, woken in the order %d %d %d\n", k1, k2, k3, forder[0], forder[1], forder[2]);
    /* an operation Linux has and PAX refuses by name: not compared */
    say("~futex: FUTEX_REQUEUE with nobody waiting answers %ld here\n", r(fut(&fw, FUTEX_REQUEUE | FUTEX_PRIVATE_FLAG, 1, 0, &fw, 0)));
}

/* ---- signals: the basics ------------------------------------------------- */
static volatile int hits, last_sig, last_code, last_pid_ok, last_tid, order[8], norder;
static volatile unsigned long in_mask;
static void h_info(int sig, siginfo_t *si, void *uc) {
    (void)uc;
    sigset_t cur;
    hits++;
    last_sig = sig;
    last_code = si->si_code;
    last_pid_ok = si->si_pid == getpid();
    last_tid = tid();
    if (norder < 8) order[norder++] = sig;
    sigprocmask(SIG_BLOCK, 0, &cur);
    in_mask = *(unsigned long *)&cur;
}
static volatile int depth, maxdepth, raises;
static void h_nest(int sig) {
    depth++;
    if (depth > maxdepth) maxdepth = depth;
    if (raises < 2) { raises++; syscall(SYS_tgkill, getpid(), tid(), sig); }
    depth--;
}
static void signals(void) {
    sigset_t set, old, pend;
    struct sigaction sa, back;
    act(SIGUSR1, h_info, SA_SIGINFO);
    act(SIGUSR2, h_info, SA_SIGINFO);
    hits = 0;
    long k = r(kill(getpid(), SIGUSR1));
    int before = hits; /* delivered before kill returned */
    say("signal: kill to self %ld, the handler had run when it returned %d, signal %d si_code %d si_pid is ours %d, on the main thread %d\n",
        k, before, last_sig, last_code, last_pid_ok, last_tid == getpid());
    k = r(syscall(SYS_tgkill, getpid(), tid(), SIGUSR2));
    say("signal: tgkill to self %ld, handler runs %d, signal %d si_code %d; the mask inside the handler 0x%lx\n", k, hits, last_sig, last_code, in_mask);
    sigprocmask(SIG_BLOCK, 0, &old);
    say("signal: the mask after the handlers 0x%lx\n", *(unsigned long *)&old);
    /* blocked, pending, then delivered at the unblock: the order */
    act(SIGTERM, h_info, SA_SIGINFO);
    sigemptyset(&set);
    sigaddset(&set, SIGUSR1); sigaddset(&set, SIGUSR2); sigaddset(&set, SIGTERM);
    sigprocmask(SIG_BLOCK, &set, &old);
    hits = 0; norder = 0;
    kill(getpid(), SIGUSR2); kill(getpid(), SIGTERM); kill(getpid(), SIGUSR1); kill(getpid(), SIGUSR1);
    sigpending(&pend);
    int held = hits;
    sigprocmask(SIG_SETMASK, &old, 0);
    say("signal: three blocked and raised (one twice): handler runs while blocked %d, pending 0x%lx, runs after the unblock %d in the order %d %d %d\n",
        held, *(unsigned long *)&pend, hits, order[0], order[1], order[2]);
    sigpending(&pend);
    say("signal: pending afterwards 0x%lx\n", *(unsigned long *)&pend);
    /* SIG_IGN, SA_RESETHAND, SA_NODEFER, sa_mask, what sigaction answers */
    signal(SIGUSR1, SIG_IGN);
    hits = 0;
    kill(getpid(), SIGUSR1);
    sigprocmask(SIG_BLOCK, &set, &old);
    kill(getpid(), SIGUSR1); /* ignored and blocked: still discarded? */
    sigpending(&pend);
    sigprocmask(SIG_SETMASK, &old, 0);
    say("signal: ignored: handler runs %d, pending while blocked 0x%lx\n", hits, *(unsigned long *)&pend);
    act(SIGUSR1, h_info, SA_SIGINFO | SA_RESETHAND);
    kill(getpid(), SIGUSR1);
    sigaction(SIGUSR1, 0, &back);
    say("signal: SA_RESETHAND: handler runs %d, the action afterwards is the default %d, its flags 0x%x\n", hits, back.sa_handler == SIG_DFL, (unsigned)back.sa_flags & ~0x04000000u);
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = h_nest;
    sa.sa_flags = SA_NODEFER;
    sigaction(SIGUSR1, &sa, 0);
    depth = maxdepth = raises = 0;
    syscall(SYS_tgkill, getpid(), tid(), SIGUSR1);
    int nd = maxdepth;
    sa.sa_flags = 0;
    sigaction(SIGUSR1, &sa, 0);
    depth = maxdepth = raises = 0;
    syscall(SYS_tgkill, getpid(), tid(), SIGUSR1);
    say("signal: a handler raising its own signal nests to depth %d with SA_NODEFER, %d without\n", nd, maxdepth);
    memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = h_info;
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);
    sigaddset(&sa.sa_mask, SIGTERM); sigaddset(&sa.sa_mask, SIGKILL); sigaddset(&sa.sa_mask, SIGSTOP);
    sigaction(SIGUSR1, &sa, 0);
    kill(getpid(), SIGUSR1);
    sigaction(SIGUSR1, 0, &back);
    say("signal: sa_mask TERM KILL STOP: the mask inside the handler 0x%lx, sigaction answers the mask 0x%lx\n", in_mask, *(unsigned long *)&back.sa_mask);
    say("signal: sigaction on SIGKILL %ld, on SIGSTOP %ld, on signal 65 %ld, reading SIGKILL's %ld; kill of a pid nobody has %ld, of signal 65 %ld, of signal 0 to self %ld\n",
        r(sigaction(SIGKILL, &sa, 0)), r(sigaction(SIGSTOP, &sa, 0)), r(syscall(SYS_rt_sigaction, 65, &sa, 0, 8)), r(sigaction(SIGKILL, 0, &back)),
        r(kill(0x3ffffe, SIGUSR1)), r(kill(getpid(), 65)), r(kill(getpid(), 0)));
    signal(SIGUSR1, SIG_DFL); signal(SIGUSR2, SIG_DFL); signal(SIGTERM, SIG_DFL);
}

/* ---- which thread takes a signal for the process -------------------------- */
static volatile int taker_main, taker_other, t_ready, t_quit;
static void h_who(int sig) {
    (void)sig;
    if (tid() == getpid()) taker_main++; else taker_other++;
}
static void *t_idle(void *p) {
    sigset_t s;
    sigemptyset(&s);
    if (p) { sigaddset(&s, SIGUSR1); pthread_sigmask(SIG_BLOCK, &s, 0); }
    else { sigaddset(&s, SIGUSR1); pthread_sigmask(SIG_UNBLOCK, &s, 0); }
    t_ready = 1;
    while (!t_quit) ms(10);
    return 0;
}
static void takers(void) {
    pthread_t t;
    sigset_t s, old;
    act(SIGUSR1, h_who, 0);
    sigemptyset(&s); sigaddset(&s, SIGUSR1);
    /* both unblocked: who takes ten of them */
    taker_main = taker_other = t_ready = t_quit = 0;
    pthread_create(&t, 0, t_idle, 0);
    while (!t_ready) ms(5);
    for (int i = 0; i < 10; i++) { kill(getpid(), SIGUSR1); ms(5); }
    int m1 = taker_main, o1 = taker_other;
    /* main blocks it: the other thread takes them */
    pthread_sigmask(SIG_BLOCK, &s, &old);
    taker_main = taker_other = 0;
    for (int i = 0; i < 10; i++) { kill(getpid(), SIGUSR1); ms(5); }
    ms(50);
    int m2 = taker_main, o2 = taker_other;
    t_quit = 1;
    pthread_join(t, 0);
    /* every thread blocks it: it waits for the process, and main takes it at its unblock */
    taker_main = taker_other = t_ready = t_quit = 0;
    pthread_create(&t, 0, t_idle, (void *)1);
    while (!t_ready) ms(5);
    kill(getpid(), SIGUSR1);
    ms(50);
    int held = taker_main + taker_other;
    pthread_sigmask(SIG_SETMASK, &old, 0);
    int m3 = taker_main, o3 = taker_other;
    t_quit = 1;
    pthread_join(t, 0);
    say("takers: ten for the process, both threads open: main took %d, the other %d; main blocking: main %d, the other %d; both blocking: delivered while blocked %d, then main %d, the other %d\n",
        m1, o1, m2, o2, held, m3, o3);
    signal(SIGUSR1, SIG_DFL);
}

/* ---- the frame ------------------------------------------------------------- */
static volatile unsigned long fr_sp;
static unsigned int fr_mx;
static unsigned short fr_cw;
static volatile long fr_uc_off, fr_si_off, fr_fp_align, fr_fp_above, fr_flags, fr_ssflags, fr_sssize, fr_cs, fr_ss, fr_magic1, fr_magic2ok, fr_xsz_ok, fr_link, fr_retok, fr_err, fr_trap, fr_oldmask, fr_cr2, fr_rsp_ok, fr_rip_ok, fr_ucmask, fr_sisigno, fr_sierrno, fr_rdx_rsi_ok;
void fr_c(unsigned long sp, int sig, siginfo_t *si, ucontext_t *uc) {
    unsigned long *ret = (unsigned long *)sp;
    mcontext_t *m = &uc->uc_mcontext;
    unsigned char *fp = (unsigned char *)m->fpregs;
    struct sigaction sa;
    fr_sp = sp;
    fr_uc_off = (long)uc - (long)sp;
    fr_si_off = (long)si - (long)uc;
    fr_fp_align = fp ? (long)fp % 64 : -1;
    fr_fp_above = fp ? ((unsigned long)fp > (unsigned long)si) : -1;
    fr_flags = uc->uc_flags;
    fr_link = (long)uc->uc_link;
    fr_ssflags = uc->uc_stack.ss_flags;
    fr_sssize = (long)uc->uc_stack.ss_size + (long)uc->uc_stack.ss_sp;
    fr_cs = m->gregs[REG_CSGSFS] & 3; /* the selectors' numbers are a kernel's own; their ring is not */
    fr_ss = (m->gregs[REG_CSGSFS] >> 48) & 3;
    __asm__ volatile("stmxcsr %0" : "=m"(fr_mx));
    __asm__ volatile("fnstcw %0" : "=m"(fr_cw));
    fr_err = m->gregs[REG_ERR];
    fr_trap = m->gregs[REG_TRAPNO];
    fr_oldmask = m->gregs[REG_OLDMASK];
    fr_cr2 = m->gregs[REG_CR2];
    fr_ucmask = *(unsigned long *)&uc->uc_sigmask;
    fr_sisigno = si->si_signo == sig;
    fr_sierrno = si->si_errno;
    sigaction(sig, 0, &sa);
    fr_retok = *ret == (unsigned long)sa.sa_restorer;
    /* the interrupted stack pointer lies above the frame, past the red zone */
    fr_rsp_ok = (unsigned long)m->gregs[REG_RSP] >= (unsigned long)(si + 1) + 128;
    fr_rip_ok = m->gregs[REG_RIP] != 0;
    if (fp) {
        uint32_t magic1 = *(uint32_t *)(fp + 464), ext = *(uint32_t *)(fp + 468), xsz = *(uint32_t *)(fp + 480);
        fr_magic1 = magic1;
        fr_xsz_ok = magic1 == 0x46505853 ? (ext == xsz + 4 && xsz >= 576) : -1;
        fr_magic2ok = magic1 == 0x46505853 ? (*(uint32_t *)(fp + xsz) == 0x46505845) : -1;
    }
}
/* the handler proper is assembly, so it sees the stack pointer the kernel left */
void fr_handler(int, siginfo_t *, void *);
__asm__(".text\n.globl fr_handler\n.type fr_handler,@function\nfr_handler:\n"
        "  movq %rdx, %rcx\n  movq %rsi, %rdx\n  movq %rdi, %rsi\n  movq %rsp, %rdi\n"
        "  subq $8, %rsp\n  call fr_c\n  addq $8, %rsp\n  ret\n.size fr_handler, .-fr_handler\n");
static volatile unsigned long mark_mask;
static void frame(void) {
    sigset_t s, old;
    act(SIGUSR1, fr_handler, SA_SIGINFO);
    sigemptyset(&s); sigaddset(&s, SIGUSR2);
    sigprocmask(SIG_BLOCK, &s, &old);
    unsigned int mx = 0x3fa0, mx0 = 0x1f80, mxb = 0;
    unsigned short cw = 0x027f, cw0 = 0x037f, cwb = 0;
    __asm__ volatile("ldmxcsr %0\n fldcw %1" : : "m"(mx), "m"(cw));
    syscall(SYS_tgkill, getpid(), tid(), SIGUSR1);
    __asm__ volatile("stmxcsr %0\n fnstcw %1" : "=m"(mxb), "=m"(cwb));
    __asm__ volatile("ldmxcsr %0\n fldcw %1" : : "m"(mx0), "m"(cw0));
    sigprocmask(SIG_SETMASK, &old, 0);
    say("frame: with MXCSR 0x3fa0 and the x87 control word 0x027f when the signal came, the handler starts with 0x%x and 0x%x, and they are 0x%x and 0x%x again after it\n", fr_mx, (unsigned)fr_cw, mxb, (unsigned)cwb);
    say("frame: at the handler's first instruction (rsp + 8) %% 16 is %lu, the word at rsp is the restorer %ld; the ucontext is %ld bytes above rsp and the siginfo %ld above it; the extended state lies above both %ld, on a 64-byte boundary %ld\n",
        (fr_sp + 8) % 16, fr_retok, fr_uc_off, fr_si_off, fr_fp_above, fr_fp_align == 0);
    say("frame: uc_flags 0x%lx uc_link %ld, the stack's flags %ld size and base %ld; cs's ring %ld ss's ring %ld err %ld trapno %ld oldmask 0x%lx cr2 %ld; uc_sigmask 0x%lx; si_signo is the signal %ld si_errno %ld\n",
        fr_flags, fr_link, fr_ssflags, fr_sssize, fr_cs, fr_ss, fr_err, fr_trap, fr_oldmask, fr_cr2, fr_ucmask, fr_sisigno, fr_sierrno);
    say("frame: the extended state's software bytes: magic 0x%lx, its sizes agree %ld, the closing magic is there %ld; the saved rsp is past the red zone %ld\n",
        fr_magic1, fr_xsz_ok, fr_magic2ok, fr_rsp_ok);
    signal(SIGUSR1, SIG_DFL);
}

/* ---- the round trip: every register, the x87/SSE/AVX state ---------------- */
/* rt_spin loads a pattern into every general register but rsp, into
   xmm0-15 (ymm0-15 with AVX), st(0), the x87 control word and MXCSR,
   then waits for rt_stop with nothing but a compare of memory, and
   stores them all. rt_handler, the signal's handler, is assembly too:
   it counts, overwrites every one of them and returns. Whatever the
   kernel fails to put back stays wrong and is seen at the end. */
unsigned long rt_g[15] = { 0x1111111111111111, 0x2222222222222222, 0x3333333333333333, 0x4444444444444444,
    0x5555555555555555, 0x6666666666666666, 0x7777777777777777, 0x8888888888888888, 0x9999999999999999,
    0xaaaaaaaaaaaaaaaa, 0xbbbbbbbbbbbbbbbb, 0xcccccccccccccccc, 0xdddddddddddddddd, 0xeeeeeeeeeeeeeeee, 0xf0f0f0f0f0f0f0f0 };
unsigned long rt_gout[15];
unsigned char rt_y[16][32] __attribute__((aligned(32)));
unsigned char rt_yout[16][32] __attribute__((aligned(32)));
double rt_f = 1.5, rt_fout;
unsigned short rt_cw = 0x027f, rt_cwout;
unsigned int rt_mx = 0x3fa0, rt_mxout, rt_mxdef = 0x1f80;
volatile int rt_stop, rt_count;
unsigned long rt_self[3]; /* rt_raise: pid, tid, signal */
long rt_spin_sse(void), rt_spin_avx(void), rt_raise_sse(void), rt_raise_avx(void);
void rt_handler_sse(int), rt_handler_avx(int);
#define RT_LOADG \
    "  movq rt_g+0(%rip), %rax\n  movq rt_g+8(%rip), %rbx\n  movq rt_g+16(%rip), %rcx\n  movq rt_g+24(%rip), %rdx\n" \
    "  movq rt_g+32(%rip), %rsi\n  movq rt_g+40(%rip), %rdi\n  movq rt_g+48(%rip), %rbp\n  movq rt_g+56(%rip), %r8\n" \
    "  movq rt_g+64(%rip), %r9\n  movq rt_g+72(%rip), %r10\n  movq rt_g+80(%rip), %r11\n  movq rt_g+88(%rip), %r12\n" \
    "  movq rt_g+96(%rip), %r13\n  movq rt_g+104(%rip), %r14\n  movq rt_g+112(%rip), %r15\n"
#define RT_STOREG \
    "  movq %rax, rt_gout+0(%rip)\n  movq %rbx, rt_gout+8(%rip)\n  movq %rcx, rt_gout+16(%rip)\n  movq %rdx, rt_gout+24(%rip)\n" \
    "  movq %rsi, rt_gout+32(%rip)\n  movq %rdi, rt_gout+40(%rip)\n  movq %rbp, rt_gout+48(%rip)\n  movq %r8, rt_gout+56(%rip)\n" \
    "  movq %r9, rt_gout+64(%rip)\n  movq %r10, rt_gout+72(%rip)\n  movq %r11, rt_gout+80(%rip)\n  movq %r12, rt_gout+88(%rip)\n" \
    "  movq %r13, rt_gout+96(%rip)\n  movq %r14, rt_gout+104(%rip)\n  movq %r15, rt_gout+112(%rip)\n"
#define X16(op, reg, mem) \
    op " " mem "+0(%rip), %" reg "0\n" op " " mem "+32(%rip), %" reg "1\n" op " " mem "+64(%rip), %" reg "2\n" op " " mem "+96(%rip), %" reg "3\n" \
    op " " mem "+128(%rip), %" reg "4\n" op " " mem "+160(%rip), %" reg "5\n" op " " mem "+192(%rip), %" reg "6\n" op " " mem "+224(%rip), %" reg "7\n" \
    op " " mem "+256(%rip), %" reg "8\n" op " " mem "+288(%rip), %" reg "9\n" op " " mem "+320(%rip), %" reg "10\n" op " " mem "+352(%rip), %" reg "11\n" \
    op " " mem "+384(%rip), %" reg "12\n" op " " mem "+416(%rip), %" reg "13\n" op " " mem "+448(%rip), %" reg "14\n" op " " mem "+480(%rip), %" reg "15\n"
#define X16S(op, reg, mem) \
    op " %" reg "0, " mem "+0(%rip)\n" op " %" reg "1, " mem "+32(%rip)\n" op " %" reg "2, " mem "+64(%rip)\n" op " %" reg "3, " mem "+96(%rip)\n" \
    op " %" reg "4, " mem "+128(%rip)\n" op " %" reg "5, " mem "+160(%rip)\n" op " %" reg "6, " mem "+192(%rip)\n" op " %" reg "7, " mem "+224(%rip)\n" \
    op " %" reg "8, " mem "+256(%rip)\n" op " %" reg "9, " mem "+288(%rip)\n" op " %" reg "10, " mem "+320(%rip)\n" op " %" reg "11, " mem "+352(%rip)\n" \
    op " %" reg "12, " mem "+384(%rip)\n" op " %" reg "13, " mem "+416(%rip)\n" op " %" reg "14, " mem "+448(%rip)\n" op " %" reg "15, " mem "+480(%rip)\n"
#define RT_PROLOG "  pushq %rbx\n  pushq %rbp\n  pushq %r12\n  pushq %r13\n  pushq %r14\n  pushq %r15\n"
#define RT_EPILOG "  popq %r15\n  popq %r14\n  popq %r13\n  popq %r12\n  popq %rbp\n  popq %rbx\n  xorl %eax, %eax\n  ret\n"
#define RT_FP_IN "  fldl rt_f(%rip)\n  fldcw rt_cw(%rip)\n  ldmxcsr rt_mx(%rip)\n"
#define RT_FP_OUT "  fnstcw rt_cwout(%rip)\n  stmxcsr rt_mxout(%rip)\n  fstpl rt_fout(%rip)\n  fninit\n  ldmxcsr rt_mxdef(%rip)\n"
#define RT_SPIN(name, load, store) \
    ".text\n.globl " name "\n.type " name ",@function\n" name ":\n" RT_PROLOG RT_FP_IN load RT_LOADG \
    "1:\n  cmpl $0, rt_stop(%rip)\n  jne 2f\n  pause\n  jmp 1b\n2:\n" RT_STOREG store RT_FP_OUT RT_EPILOG ".size " name ", .-" name "\n"
/* rt_raise: the same, but the signal comes from the thread's own tgkill:
   the path out of a system call (rax, rcx and r11 are the call's). */
#define RT_RAISE(name, load, store) \
    ".text\n.globl " name "\n.type " name ",@function\n" name ":\n" RT_PROLOG RT_FP_IN load RT_LOADG \
    "  movq rt_self+0(%rip), %rdi\n  movq rt_self+8(%rip), %rsi\n  movq rt_self+16(%rip), %rdx\n  movl $234, %eax\n  syscall\n" \
    RT_STOREG store RT_FP_OUT RT_EPILOG ".size " name ", .-" name "\n"
#define RT_HANDLER(name, wipe) \
    ".text\n.globl " name "\n.type " name ",@function\n" name ":\n  lock incl rt_count(%rip)\n" \
    "  movq $-1, %rax\n  movq %rax, %rbx\n  movq %rax, %rcx\n  movq %rax, %rdx\n  movq %rax, %rsi\n  movq %rax, %rdi\n  movq %rax, %rbp\n" \
    "  movq %rax, %r8\n  movq %rax, %r9\n  movq %rax, %r10\n  movq %rax, %r11\n  movq %rax, %r12\n  movq %rax, %r13\n  movq %rax, %r14\n  movq %rax, %r15\n" \
    wipe "  fninit\n  fldz\n  ldmxcsr rt_mxdef(%rip)\n  ret\n.size " name ", .-" name "\n"
#define WIPE_SSE "  pcmpeqd %xmm0, %xmm0\n  movdqa %xmm0, %xmm1\n  movdqa %xmm0, %xmm2\n  movdqa %xmm0, %xmm3\n  movdqa %xmm0, %xmm4\n  movdqa %xmm0, %xmm5\n  movdqa %xmm0, %xmm6\n  movdqa %xmm0, %xmm7\n" \
    "  movdqa %xmm0, %xmm8\n  movdqa %xmm0, %xmm9\n  movdqa %xmm0, %xmm10\n  movdqa %xmm0, %xmm11\n  movdqa %xmm0, %xmm12\n  movdqa %xmm0, %xmm13\n  movdqa %xmm0, %xmm14\n  movdqa %xmm0, %xmm15\n"
__asm__(RT_SPIN("rt_spin_sse", X16("  movdqu", "xmm", "rt_y"), X16S("  movdqu", "xmm", "rt_yout")));
__asm__(RT_SPIN("rt_spin_avx", X16("  vmovdqu", "ymm", "rt_y"), X16S("  vmovdqu", "ymm", "rt_yout") "  vzeroupper\n"));
__asm__(RT_RAISE("rt_raise_sse", X16("  movdqu", "xmm", "rt_y"), X16S("  movdqu", "xmm", "rt_yout")));
__asm__(RT_RAISE("rt_raise_avx", X16("  vmovdqu", "ymm", "rt_y"), X16S("  vmovdqu", "ymm", "rt_yout") "  vzeroupper\n"));
__asm__(RT_HANDLER("rt_handler_sse", WIPE_SSE));
__asm__(RT_HANDLER("rt_handler_avx", "  vzeroall\n" WIPE_SSE));
static int rt_avx;
static void *rt_body(void *p) {
    *(pid_t *)p = tid();
    if (rt_avx) rt_spin_avx(); else rt_spin_sse();
    return 0;
}
static int rt_check(int syscall_path, char *why, int cap) {
    int bad = 0, w = rt_avx ? 32 : 16;
    static const char *gn[15] = { "rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15" };
    why[0] = 0;
    for (int i = 0; i < 15; i++) {
        if (syscall_path && (i == 0 || i == 2 || i == 10)) continue; /* the call's own: rax, rcx, r11 */
        unsigned long want = rt_g[i];
        if (syscall_path && i == 5) want = rt_self[0];
        if (syscall_path && i == 4) want = rt_self[1];
        if (syscall_path && i == 3) want = rt_self[2];
        if (rt_gout[i] != want) { bad++; snprintf(why + strlen(why), cap - strlen(why), " %s", gn[i]); }
    }
    for (int i = 0; i < 16; i++)
        if (memcmp(rt_y[i], rt_yout[i], w)) { bad++; snprintf(why + strlen(why), cap - strlen(why), " %s%d", rt_avx ? "ymm" : "xmm", i); }
    if (rt_fout != rt_f) { bad++; snprintf(why + strlen(why), cap - strlen(why), " st0"); }
    if (rt_cwout != rt_cw) { bad++; snprintf(why + strlen(why), cap - strlen(why), " fcw"); }
    if (rt_mxout != rt_mx) { bad++; snprintf(why + strlen(why), cap - strlen(why), " mxcsr"); }
    return bad;
}
static int roundtrip_n(int n, char *why, int cap) {
    pthread_t t;
    volatile pid_t other = 0;
    rt_avx = __builtin_cpu_supports("avx");
    for (int i = 0; i < 16; i++) for (int j = 0; j < 32; j++) rt_y[i][j] = (unsigned char)(0x10 * i + j + 1);
    memset(rt_gout, 0, sizeof rt_gout); memset(rt_yout, 0, sizeof rt_yout);
    act(SIGUSR1, rt_avx ? (void *)rt_handler_avx : (void *)rt_handler_sse, 0);
    rt_stop = rt_count = 0;
    pthread_create(&t, 0, rt_body, (void *)&other);
    while (!other) ms(1);
    ms(20);
    for (int i = 1; i <= n; i++) {
        syscall(SYS_tgkill, getpid(), other, SIGUSR1);
        while (rt_count < i) sched_yield();
    }
    rt_stop = 1;
    pthread_join(t, 0);
    return rt_check(0, why, cap);
}
static void roundtrip(void) {
    char why[256], why2[256];
    int bad = roundtrip_n(200, why, sizeof why);
    say("roundtrip: 200 signals into a spinning thread whose handler overwrites every register: handler runs %d, registers not put back %d%s\n", rt_count, bad, why);
    /* out of a system call */
    memset(rt_gout, 0, sizeof rt_gout); memset(rt_yout, 0, sizeof rt_yout);
    rt_self[0] = getpid(); rt_self[1] = tid(); rt_self[2] = SIGUSR1;
    rt_count = 0;
    if (rt_avx) rt_raise_avx(); else rt_raise_sse();
    bad = rt_check(1, why2, sizeof why2);
    say("roundtrip: a signal a thread sends itself, taken on the way out of the call: handler runs %d, registers not put back %d%s\n", rt_count, bad, why2);
    signal(SIGUSR1, SIG_DFL);
}

/* ---- what a handler interrupts, and what runs again ------------------------- */
static volatile int eh;
static void h_count(int sig) { (void)sig; eh++; }
struct ew { int kind; pid_t tid; long ret; int hits_at_return; long ms; int pfd; };
static uint32_t ew_word;
static void *e_body(void *p) {
    struct ew *w = p;
    char c;
    struct timespec t2 = { 2, 0 }, rem = { 0, 0 };
    long t0 = now_ms();
    w->tid = tid();
    switch (w->kind) {
    case 0: w->ret = r(read(w->pfd, &c, 1)); break;
    case 1: w->ret = r(nanosleep(&t2, &rem)); if (w->ret == -EINTR) w->ret = (rem.tv_sec >= 1 && rem.tv_sec < 2) ? -EINTR : -9999; break;
    case 2: w->ret = r(fut(&ew_word, FUTEX_WAIT | FUTEX_PRIVATE_FLAG, 0, 0, 0, 0)); break;
    case 3: w->ret = r(fut(&ew_word, FUTEX_WAIT | FUTEX_PRIVATE_FLAG, 0, &(struct timespec){ 1, 0 }, 0, 0)); break;
    case 4: w->ret = r(clock_nanosleep(CLOCK_MONOTONIC, 0, &t2, &rem)); if (w->ret > 0) w->ret = -w->ret; break;
    }
    w->hits_at_return = eh;
    w->ms = now_ms() - t0;
    return 0;
}
/* one case: a thread blocks in call `kind`; 100 ms later it gets SIGUSR1; 100 ms
   after that the thing it waits for happens (a byte, a wake). */
static void e_case(const char *name, int kind, int restart) {
    pthread_t t;
    struct ew w = { kind, 0, 99, 0, 0, 0 };
    int pf[2] = { -1, -1 };
    eh = 0;
    ew_word = 0;
    act(SIGUSR1, h_count, restart ? SA_RESTART : 0);
    if (kind == 0) { if (pipe(pf)) {} w.pfd = pf[0]; }
    pthread_create(&t, 0, e_body, &w);
    while (!w.tid) ms(1);
    ms(100);
    syscall(SYS_tgkill, getpid(), w.tid, SIGUSR1);
    ms(100);
    if (kind == 0) { if (write(pf[1], "x", 1)) {} }
    if (kind == 2 || kind == 3) { ew_word = 1; fut(&ew_word, FUTEX_WAKE | FUTEX_PRIVATE_FLAG, 1, 0, 0, 0); }
    pthread_join(t, 0);
    if (kind == 0) { close(pf[0]); close(pf[1]); }
    say(" %s %s: %ld (handler runs %d, %s)", name, restart ? "with SA_RESTART" : "without", w.ret, w.hits_at_return,
        w.ms < 150 ? "at the signal" : w.ms < 600 ? "at the event" : "at its own end");
}
static volatile pid_t wmain;
static void *w_poker(void *p) {
    (void)p;
    ms(100);
    syscall(SYS_tgkill, getpid(), wmain, SIGUSR1);
    return 0;
}
static void interrupts(void) {
    say("eintr: a read of an empty pipe");
    e_case("", 0, 0); e_case("", 0, 1);
    say("\neintr: nanosleep of 2 s");
    e_case("", 1, 0); e_case("", 1, 1);
    say("\neintr: clock_nanosleep of 2 s");
    e_case("", 4, 0); e_case("", 4, 1);
    say("\neintr: a futex wait with no timeout");
    e_case("", 2, 0); e_case("", 2, 1);
    say("\neintr: a futex wait with a 1 s timeout");
    e_case("", 3, 0); e_case("", 3, 1);
    say("\n");
    /* wait4, on the main thread */
    for (int restart = 0; restart < 2; restart++) {
        pthread_t t;
        int st = -1;
        eh = 0;
        act(SIGUSR1, h_count, restart ? SA_RESTART : 0);
        pid_t c = fork();
        if (c == 0) { ms(300); _exit(3); }
        wmain = tid();
        pthread_create(&t, 0, w_poker, 0);
        long t0 = now_ms();
        long w = r(waitpid(c, &st, 0));
        long took = now_ms() - t0;
        int first = w == c;
        if (!first) waitpid(c, &st, 0);
        pthread_join(t, 0);
        say("eintr: wait4 %s: %s (handler runs %d, %s), the child's status 0x%x\n", restart ? "with SA_RESTART" : "without",
            first ? "the child" : w == -EINTR ? "-4" : "?", eh, took < 200 ? "at the signal" : "at the child's end", st);
    }
    signal(SIGUSR1, SIG_DFL);
}

/* ---- what a signal does to a process ---------------------------------------- */
static volatile int chld_code, chld_status, chld_hits;
static volatile pid_t chld_pid;
static void h_chld(int sig, siginfo_t *si, void *uc) {
    (void)sig; (void)uc;
    chld_hits++;
    chld_code = si->si_code;
    chld_status = si->si_status;
    chld_pid = si->si_pid; /* compared by the caller: the child may end before fork returns here */
}
static int child_killed_by(int prep, int sig) {
    int st = -1;
    pid_t c = fork();
    if (c == 0) {
        if (prep == 1) signal(SIGINT, SIG_IGN);
        if (prep == 2) { sigset_t s; sigemptyset(&s); sigaddset(&s, SIGTERM); sigprocmask(SIG_BLOCK, &s, 0); }
        for (;;) ms(1000);
    }
    ms(50);
    if (prep == 1) { kill(c, SIGINT); ms(50); }
    if (prep == 2) { kill(c, SIGTERM); ms(50); }
    kill(c, sig);
    waitpid(c, &st, 0);
    return st;
}
static volatile int pipe_hits, pipe_code, pipe_pid_ok;
static void h_pipe(int sig, siginfo_t *si, void *uc) {
    (void)sig; (void)uc;
    pipe_hits++;
    pipe_code = si->si_code;
    pipe_pid_ok = si->si_pid == getpid();
}
static void deaths(void) {
    int st, pf[2];
    say("death: a child killed by SIGTERM leaves 0x%x, by SIGKILL 0x%x, by SIGUSR1 0x%x", child_killed_by(0, SIGTERM), child_killed_by(0, SIGKILL), child_killed_by(0, SIGUSR1));
    say("; ignoring SIGINT it outlives one and SIGTERM leaves 0x%x; blocking SIGTERM it outlives one and SIGKILL leaves 0x%x\n", child_killed_by(1, SIGTERM), child_killed_by(2, SIGKILL));
    /* SIGCHLD */
    act(SIGCHLD, h_chld, SA_SIGINFO);
    chld_hits = 0;
    pid_t c = fork();
    if (c == 0) _exit(5);
    while (!chld_hits) ms(5);
    waitpid(c, &st, 0);
    say("death: SIGCHLD for a child that exits 5: si_code %d si_status %d si_pid is the child %d", chld_code, chld_status, chld_pid == c);
    chld_hits = 0;
    c = fork();
    if (c == 0) for (;;) ms(1000);
    ms(30);
    kill(c, SIGKILL);
    while (!chld_hits) ms(5);
    waitpid(c, &st, 0);
    say("; for one killed by SIGKILL: si_code %d si_status %d\n", chld_code, chld_status);
    signal(SIGCHLD, SIG_DFL);
    /* SIGPIPE */
    act(SIGPIPE, h_pipe, SA_SIGINFO);
    if (pipe(pf)) {}
    close(pf[0]);
    long w = r(write(pf[1], "x", 1));
    close(pf[1]);
    say("death: a write to a pipe with no reader, SIGPIPE handled: the write %ld, handler runs %d, si_code %d si_pid is ours %d", w, pipe_hits, pipe_code, pipe_pid_ok);
    signal(SIGPIPE, SIG_IGN);
    if (pipe(pf)) {}
    close(pf[0]);
    w = r(write(pf[1], "x", 1));
    close(pf[1]);
    say("; ignored: the write %ld", w);
    c = fork();
    if (c == 0) {
        signal(SIGPIPE, SIG_DFL);
        if (pipe(pf)) {}
        close(pf[0]);
        if (write(pf[1], "x", 1)) {}
        _exit(0);
    }
    waitpid(c, &st, 0);
    say("; default, in a child: its status 0x%x\n", st);
    signal(SIGPIPE, SIG_DFL);
    /* a stop: in an orphaned group (this program is pid 1, alone in its group) SIGTSTP is discarded, on Linux and since px48 on PAX; not compared */
    c = fork();
    if (c == 0) { kill(getpid(), SIGTSTP); _exit(3); }
    waitpid(c, &st, WUNTRACED);
    if (WIFSTOPPED(st)) { kill(c, SIGKILL); waitpid(c, 0, 0); }
    say("~stop: a child that sends itself SIGTSTP with the default action: its parent's wait sees 0x%x here\n", st);
}

/* ---- a thread's exit against the process's --------------------------------- */
static void *x_exit3(void *p) { (void)p; syscall(SYS_exit, 3); return 0; }
static void *x_group5(void *p) { (void)p; ms(30); syscall(SYS_exit_group, 5); return 0; }
static void *x_late6(void *p) { (void)p; ms(80); syscall(SYS_exit, 6); return 0; }
static void *x_sleep(void *p) { (void)p; for (;;) ms(1000); return 0; }
static void *x_segv(void *p) { (void)p; ms(30); *(volatile int *)8 = 1; return 0; }
static void *x_fork(void *p) {
    int st = -1;
    pid_t c = fork();
    if (c == 0) _exit(7);
    waitpid(c, &st, 0);
    *(int *)p = st;
    return 0;
}
static void *x_exec(void *p) {
    char *self = p;
    char *argv[] = { self, "exec", 0 };
    static char pidbuf[32];
    snprintf(pidbuf, sizeof pidbuf, "PROBE_PID=%d", getpid());
    char *envp[] = { pidbuf, 0 };
    ms(30);
    execve(self, argv, envp);
    _exit(99);
}
static void exits(const char *self) {
    int st;
    pthread_t t;
    pid_t c = fork();
    if (c == 0) {
        pthread_create(&t, 0, x_exit3, 0);
        ms(60);
        say("exit: after a thread's exit(3) the process runs on\n");
        pthread_create(&t, 0, x_group5, 0);
        for (;;) ms(1000);
    }
    waitpid(c, &st, 0);
    say("exit: then another thread's exit_group(5) while main sleeps: status 0x%x\n", st);
    c = fork();
    if (c == 0) {
        pthread_create(&t, 0, x_late6, 0);
        syscall(SYS_exit, 4); /* the main thread alone ends; the other runs on, then ends with 6 */
    }
    long t0 = now_ms();
    waitpid(c, &st, 0);
    say("exit: main's exit(4) with a thread still running, which exits 6 later: status 0x%x, known only after the thread ended %d\n", st, now_ms() - t0 >= 60);
    c = fork();
    if (c == 0) {
        pthread_create(&t, 0, x_segv, 0);
        for (;;) ms(1000);
    }
    waitpid(c, &st, 0);
    say("exit: a thread's fault ends the whole process: status 0x%x\n", st & 0xff7f);
    c = fork();
    if (c == 0) {
        pthread_create(&t, 0, x_sleep, 0);
        ms(30);
        _exit(8);
    }
    waitpid(c, &st, 0);
    say("exit: exit_group(8) from main with a thread asleep: status 0x%x\n", st);
    st = -1;
    pthread_create(&t, 0, x_fork, &st);
    pthread_join(t, 0);
    say("exit: a fork from a second thread; its child exits 7 and that thread waits for it: status 0x%x\n", st);
    c = fork();
    if (c == 0) {
        pthread_create(&t, 0, x_exec, (void *)self);
        for (;;) ms(1000);
    }
    waitpid(c, &st, 0);
    say("exit: an execve from a second thread: the new program's status 0x%x\n", st);
}

/* ---- memory a thread's library asks for ----------------------------------- */
static sigjmp_buf jb;
static volatile int f_code, f_sig;
static volatile unsigned long f_addr, f_trap, f_err_p, f_cr2;
static void h_fault(int sig, siginfo_t *si, void *ucv) {
    ucontext_t *uc = ucv;
    f_sig = sig;
    f_code = si->si_code;
    f_addr = (unsigned long)si->si_addr;
    f_trap = uc->uc_mcontext.gregs[REG_TRAPNO];
    f_err_p = uc->uc_mcontext.gregs[REG_ERR];
    f_cr2 = uc->uc_mcontext.gregs[REG_CR2];
    siglongjmp(jb, 1);
}
static int zero;
static void memory(void) {
    size_t big = 256UL << 20;
    unsigned char *p = mmap(0, big, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    long m1 = r(mprotect(p + 4096, 8192, PROT_READ | PROT_WRITE));
    p[4096] = 9; p[4096 + 8191] = 7;
    long d = r(madvise(p + 4096, 8192, MADV_DONTNEED));
    int z = p[4096] == 0 && p[4096 + 8191] == 0;
    long u1 = r(munmap(p, 4096)), u2 = r(munmap(p + (128UL << 20), 128UL << 20));
    act(SIGSEGV, h_fault, SA_SIGINFO);
    act(SIGFPE, h_fault, SA_SIGINFO);
    act(SIGILL, h_fault, SA_SIGINFO);
    say("memory: 256 MiB reserved with PROT_NONE %d, two pages of it made writable %ld and written, MADV_DONTNEED %ld and they read zero %d, the ends unmapped %ld %ld\n",
        p != MAP_FAILED, m1, d, z, u1, u2);
    f_sig = 0;
    if (!sigsetjmp(jb, 1)) p[3 * 4096] = 1; /* reserved, never made accessible */
    say("fault: a write to a reserved page: signal %d si_code %d si_addr is the address %d trapno %lu the error's low bits 0x%lx cr2 is the address %d", f_sig, f_code,
        f_addr == (unsigned long)(p + 3 * 4096), f_trap, f_err_p & 7, f_cr2 == (unsigned long)(p + 3 * 4096));
    f_sig = 0;
    if (!sigsetjmp(jb, 1)) *(volatile int *)16 = 1; /* nothing mapped */
    say("; to an address nothing maps: signal %d si_code %d si_addr %lu error 0x%lx\n", f_sig, f_code, f_addr, f_err_p & 7);
    f_sig = 0;
    if (!sigsetjmp(jb, 1)) __asm__ volatile("xorl %%edx, %%edx\n movl $1, %%eax\n idivl %0" : : "m"(zero) : "eax", "edx", "cc");
    say("fault: a division by zero: signal %d si_code %d trapno %lu si_addr is in the program %d", f_sig, f_code, f_trap, f_addr >= 0x400000 && f_addr < 0x800000);
    f_sig = 0;
    if (!sigsetjmp(jb, 1)) __asm__("ud2");
    say("; an undefined instruction: signal %d si_code %d trapno %lu; each handler left by siglongjmp, and the program runs on\n", f_sig, f_code, f_trap);
    /* a fault with the signal blocked or ignored is still fatal */
    int st;
    pid_t c = fork();
    if (c == 0) { signal(SIGSEGV, SIG_IGN); *(volatile int *)16 = 1; _exit(0); }
    waitpid(c, &st, 0);
    say("fault: with SIGSEGV ignored a fault still ends the process: status 0x%x", st & 0xff7f);
    c = fork();
    if (c == 0) { sigset_t s; sigemptyset(&s); sigaddset(&s, SIGSEGV); sigprocmask(SIG_BLOCK, &s, 0); *(volatile int *)16 = 1; _exit(0); }
    waitpid(c, &st, 0);
    say("; with it blocked and handled: status 0x%x\n", st & 0xff7f);
    signal(SIGSEGV, SIG_DFL); signal(SIGFPE, SIG_DFL); signal(SIGILL, SIG_DFL);
    /* the guard a newer libc installs below a thread's stack */
    unsigned char *g = mmap(0, 3 * 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    g[0] = 1;
    long gi = r(madvise(g, 4096, 102)); /* MADV_GUARD_INSTALL */
    if (gi != 0) {
        say("~guard: MADV_GUARD_INSTALL answers %ld here\n", gi);
    } else {
        act(SIGSEGV, h_fault, SA_SIGINFO);
        f_sig = 0;
        if (!sigsetjmp(jb, 1)) g[0] = 2;
        int faulted = f_sig;
        long gr = r(madvise(g, 4096, 103)); /* MADV_GUARD_REMOVE */
        f_sig = 0;
        if (!sigsetjmp(jb, 1)) g[0] = 3;
        say("~guard: MADV_GUARD_INSTALL 0: a touch of the page raises signal %d; MADV_GUARD_REMOVE %ld and a write then raises %d\n", faulted, gr, f_sig);
        signal(SIGSEGV, SIG_DFL);
    }
    char nm[16] = { 0 }, nm2[16] = { 0 };
    long ps = r(prctl(PR_SET_NAME, "px26-a-name-longer-than-15"));
    prctl(PR_GET_NAME, nm);
    say("name: PR_SET_NAME %ld, PR_GET_NAME \"%s\"\n", ps, nm);
    (void)nm2;
}

/* ---- the soak --------------------------------------------------------------- */
static void *s_body(void *p) { return p; }
static volatile unsigned long s_sp_first, s_sp_moved;
static volatile int s_hits;
static void h_soak(int sig) {
    int here;
    (void)sig;
    s_hits++;
    if (!s_sp_first) s_sp_first = (unsigned long)&here;
    else if (s_sp_first != (unsigned long)&here) s_sp_moved++;
}
static void __attribute__((noinline)) soak_signals(int n) {
    for (int i = 0; i < n; i++) syscall(SYS_tgkill, getpid(), tid(), SIGUSR1);
}
static int soak(void) {
    const int N = 10000;
    void *brk0 = sbrk(0);
    pthread_t t;
    long sum = 0;
    char why[256];
    long t0 = now_ms();
    for (long i = 0; i < N; i++) {
        void *v;
        if (pthread_create(&t, 0, s_body, (void *)i)) { say("soak: pthread_create failed at %ld: errno %d\n", i, errno); return 1; }
        pthread_join(t, &v);
        sum += (long)v;
    }
    void *brk1 = sbrk(0);
    say("soak: %d threads made and joined, their results sum %ld; the break moved %ld bytes\n", N, sum, (long)((char *)brk1 - (char *)brk0));
    act(SIGUSR1, h_soak, 0);
    soak_signals(N);
    say("soak: %d signals sent to self, handler runs %d, the handler's stack moved %lu times\n", N, s_hits, s_sp_moved);
    int bad = roundtrip_n(2000, why, sizeof why);
    say("soak: 2000 more into a spinning thread: handler runs %d, registers not put back %d%s\n", rt_count, bad, why);
    for (long i = 0; i < 100; i++) { pthread_create(&t, 0, s_body, 0); pthread_join(t, 0); }
    say("soak: the break after it all moved %ld bytes from the start\n", (long)((char *)sbrk(0) - (char *)brk0));
    (void)t0;
    return 0;
}

int main(int argc, char **argv) {
    if (argc > 1 && !strcmp(argv[1], "exec")) {
        const char *want = getenv("PROBE_PID");
        say("exec: the new program's pid is the old process's %d, its tid is its pid %d\n", want && atoi(want) == getpid(), tid() == getpid());
        return 0;
    }
    if (argc > 1 && !strcmp(argv[1], "soak")) return soak();
    ids();
    futexes();
    signals();
    takers();
    frame();
    roundtrip();
    interrupts();
    deaths();
    exits(argv[0]);
    memory();
    say("done\n");
    return 0;
}
