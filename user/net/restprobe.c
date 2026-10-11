/* restprobe — the rest of what wolf's hosted runtime and lobo ask of a
   kernel beside poll and epoll (px24; `notes/px24/linux/`), call by
   call: writev to a pipe, to /dev/null and to a stream socket (a
   response's head and body), its bounds and a short write; getrandom's
   flags; sched_getaffinity; sigaltstack and a handler that runs on the
   alternate stack; getsockopt's SO_ACCEPTCONN, SO_TYPE and lengths,
   TCP_NODELAY; accept4's flags; prctl's name; the clocks; and two
   things that must be a thread's own: the count of bytes a waiting
   stream send has queued, and a waiting call's deadline (two threads of
   one process waiting at once). Everything stays on this machine. Its
   output on PAX must be its output on Linux, but for the lines that
   start with `~` (a clock's step, which is the machine's). */
#define _GNU_SOURCE
#include "say.h"
#pragma GCC diagnostic ignored "-Wunused-result"
#pragma GCC diagnostic ignored "-Wstringop-overflow"
#pragma GCC diagnostic ignored "-Wstringop-overread"
#include <fcntl.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <pthread.h>
#include <sched.h>
#include <signal.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/prctl.h>
#include <sys/random.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <sys/uio.h>
#include <sys/wait.h>
#include <time.h>
#include <ucontext.h>

static char rb[64];
#define N(label, call) do { long r_ = (call); say("%s: %s\n", label, res(r_, rb, sizeof rb, 1)); } while (0)

static long ms_now(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000L + t.tv_nsec / 1000000L;
}

static void nap(long ms)
{
    struct timespec t = { ms / 1000, (ms % 1000) * 1000000L };
    nanosleep(&t, 0);
}

static void pair(int port, int *l, int *c, int *s)
{
    int one = 1;
    struct sockaddr_in a = sin_of("127.0.0.1", port);
    *l = socket(AF_INET, SOCK_STREAM, 0);
    setsockopt(*l, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    if (bind(*l, (struct sockaddr *)&a, sizeof a) < 0 || listen(*l, 4) < 0)
        say("pair %d: bind or listen: %s\n", port, ename(errno));
    *c = socket(AF_INET, SOCK_STREAM, 0);
    if (connect(*c, (struct sockaddr *)&a, sizeof a) < 0)
        say("pair %d: connect: %s\n", port, ename(errno));
    *s = accept(*l, 0, 0);
    if (*s < 0)
        say("pair %d: accept: %s\n", port, ename(errno));
}

/* --- sigaltstack ---------------------------------------------------- */

static char *alt;
static size_t alt_size;
static volatile int h_on_alt, h_flags, h_change, h_uc_sp, h_uc_size, h_uc_flags;

static void on_usr(int sig, siginfo_t *si, void *ctx)
{
    char here;
    stack_t now, try = { alt, 0, alt_size };
    ucontext_t *uc = ctx;
    (void)sig;
    (void)si;
    h_on_alt = &here >= alt && &here < alt + alt_size;
    sigaltstack(0, &now);
    h_flags = now.ss_flags;
    h_change = sigaltstack(&try, 0) < 0 ? errno : 0;
    h_uc_sp = uc->uc_stack.ss_sp == alt;
    h_uc_size = uc->uc_stack.ss_size == alt_size;
    h_uc_flags = uc->uc_stack.ss_flags;
}

static const char *ssf(int f, char *b, size_t cap)
{
    snprintf(b, cap, "%s", f == 0 ? "0" : f == SS_DISABLE ? "SS_DISABLE" : f == SS_ONSTACK ? "SS_ONSTACK" : "other");
    return b;
}

static void *thread_stack(void *arg)
{
    stack_t now;
    (void)arg;
    sigaltstack(0, &now);
    return (void *)(long)now.ss_flags;
}

static void altstack(void)
{
    char b[32], b2[32];
    stack_t now, st;
    struct sigaction sa;
    alt_size = 32768;
    alt = malloc(alt_size);
    N("sigaltstack, asking only", sigaltstack(0, &now));
    say("a process starts with: %s, size %ld\n", ssf(now.ss_flags, b, sizeof b), (long)now.ss_size);
    st.ss_sp = alt; st.ss_flags = 0; st.ss_size = 1024;
    N("a stack of 1024 bytes", sigaltstack(&st, 0));
    st.ss_size = alt_size; st.ss_flags = 4;
    N("a flag that is none (4)", sigaltstack(&st, 0));
    st.ss_flags = 0;
    N("a stack of 32768 bytes", sigaltstack(&st, 0));
    sigaltstack(0, &now);
    say("then: %s, the stack given %s, size %ld\n", ssf(now.ss_flags, b, sizeof b), now.ss_sp == alt ? "yes" : "no", (long)now.ss_size);
    memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = on_usr;
    sa.sa_flags = SA_SIGINFO | SA_ONSTACK;
    sigaction(SIGUSR1, &sa, 0);
    raise(SIGUSR1);
    say("a handler with SA_ONSTACK: on the alternate stack %s; sigaltstack inside says %s; a change inside: %s; the context's stack: given %s, size %s, flags %s\n",
        h_on_alt ? "yes" : "no", ssf(h_flags, b, sizeof b), ename(h_change), h_uc_sp ? "yes" : "no", h_uc_size ? "yes" : "no", ssf(h_uc_flags, b2, sizeof b2));
    sigaltstack(0, &now);
    say("after it returned: %s\n", ssf(now.ss_flags, b, sizeof b));
    sa.sa_flags = SA_SIGINFO;
    sigaction(SIGUSR1, &sa, 0);
    raise(SIGUSR1);
    say("a handler without SA_ONSTACK: on the alternate stack %s; sigaltstack inside says %s; the context's stack: given %s, flags %s\n",
        h_on_alt ? "yes" : "no", ssf(h_flags, b, sizeof b), h_uc_sp ? "yes" : "no", ssf(h_uc_flags, b2, sizeof b2));
    pthread_t t;
    void *tr = 0;
    pthread_create(&t, 0, thread_stack, 0);
    pthread_join(t, &tr);
    say("a new thread starts with: %s\n", ssf((int)(long)tr, b, sizeof b));
    pid_t k = fork();
    if (k == 0) {
        sigaltstack(0, &now);
        _exit(now.ss_flags == 0 && now.ss_sp == alt ? 0 : 1);
    }
    int ws = 0;
    waitpid(k, &ws, 0);
    say("a fork's child keeps it: %s\n", WEXITSTATUS(ws) == 0 ? "yes" : "no");
    st.ss_flags = SS_DISABLE;
    N("SS_DISABLE", sigaltstack(&st, 0));
    sigaltstack(0, &now);
    say("then: %s\n", ssf(now.ss_flags, b, sizeof b));
    sa.sa_flags = SA_SIGINFO | SA_ONSTACK;
    sigaction(SIGUSR1, &sa, 0);
    raise(SIGUSR1);
    say("a handler with SA_ONSTACK and no alternate stack: on it %s\n", h_on_alt ? "yes" : "no");
    signal(SIGUSR1, SIG_DFL);
}

/* --- two threads of one process, each waiting ------------------------ */

struct job {
    int fd;
    size_t n;
    unsigned seed;
    long sent;
    unsigned long crc;
};

static void *sender(void *arg)
{
    struct job *j = arg;
    static __thread unsigned char buf[65536];
    size_t off = 0;
    while (off < j->n) {
        size_t k = j->n - off < sizeof buf ? j->n - off : sizeof buf;
        pattern_fill(buf, off + j->seed * 1000003ULL, k);
        j->crc = crc32_of(j->crc, buf, k);
        /* One send of the whole piece: it waits, part-way, for room. */
        ssize_t w = send(j->fd, buf, k, MSG_NOSIGNAL);
        if (w != (ssize_t)k) {
            j->sent = -1;
            return 0;
        }
        off += k;
    }
    j->sent = off;
    return 0;
}

static unsigned long drain(int fd, size_t n, long *got)
{
    static unsigned char buf[65536];
    unsigned long crc = 0;
    size_t off = 0;
    while (off < n) {
        ssize_t r = recv(fd, buf, sizeof buf, 0);
        if (r <= 0)
            break;
        crc = crc32_of(crc, buf, r);
        off += r;
    }
    *got = off;
    return crc;
}

struct timed {
    int fd;
    int ms;
    long took;
    int result;
};

static void *poller(void *arg)
{
    struct timed *t = arg;
    struct pollfd p = { t->fd, POLLIN, 0 };
    long t0 = ms_now();
    t->result = poll(&p, 1, t->ms);
    t->took = ms_now() - t0;
    return 0;
}

static void *receiver(void *arg)
{
    struct timed *t = arg;
    char b[16];
    long t0 = ms_now();
    t->result = recv(t->fd, b, sizeof b, 0) < 0 ? errno : 0;
    t->took = ms_now() - t0;
    return 0;
}

static void two_threads(void)
{
    int l1, c1, s1, l2, c2, s2;
    pair(4601, &l1, &c1, &s1);
    pair(4602, &l2, &c2, &s2);
    struct job a = { c1, 400000, 1, 0, 0 }, b = { c2, 300000, 2, 0, 0 };
    pthread_t ta, tb;
    pthread_create(&ta, 0, sender, &a);
    pthread_create(&tb, 0, sender, &b);
    nap(150); /* both are waiting in a send by now: each buffer pair is full */
    long ga = 0, gb = 0;
    unsigned long cb = drain(s2, b.n, &gb), ca = drain(s1, a.n, &ga);
    pthread_join(ta, 0);
    pthread_join(tb, 0);
    say("two threads, each waiting in a send on a socket of its own: the first sent %ld of 400000, the second %ld of 300000; received %ld and %ld; the bytes %s and %s\n",
        a.sent, b.sent, ga, gb, ca == a.crc ? "exact" : "wrong", cb == b.crc ? "exact" : "wrong");
    close(l1); close(c1); close(s1); close(l2); close(c2); close(s2);

    int p[2];
    pipe(p);
    int u = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in ua = sin_of("127.0.0.1", 4603);
    struct timeval tv = { 0, 150000 };
    bind(u, (struct sockaddr *)&ua, sizeof ua);
    setsockopt(u, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv);
    struct timed tp = { p[0], 400, 0, 0 }, tr = { u, 0, 0, 0 };
    pthread_create(&ta, 0, poller, &tp);
    pthread_create(&tb, 0, receiver, &tr);
    pthread_join(ta, 0);
    pthread_join(tb, 0);
    say("two threads, each waiting with a deadline of its own: poll for 400 ms answered %d after at least 400 ms: %s, under 700: %s; a receive with a 150 ms timeout answered %s after at least 150 ms: %s, under 350: %s\n",
        tp.result, tp.took >= 400 ? "yes" : "no", tp.took < 700 ? "yes" : "no", ename(tr.result), tr.took >= 150 ? "yes" : "no", tr.took < 350 ? "yes" : "no");
    close(p[0]); close(p[1]); close(u);
}

int main(void)
{
    int p[2], l, c, s, one = 1, v;
    socklen_t vl;
    char buf[8192], in[64];
    signal(SIGPIPE, SIG_IGN);
    memset(buf, 'w', sizeof buf);

    /* --- writev ------------------------------------------------------- */
    pipe(p);
    struct iovec two[2] = { { "head: 1\r\n\r\n", 11 }, { "the body\n", 9 } };
    N("writev of 11 and 9 bytes to a pipe", writev(p[1], two, 2));
    int r = read(p[0], in, sizeof in);
    say("read back: %d bytes, %s\n", r, r == 20 && memcmp(in, "head: 1\r\n\r\nthe body\n", 20) == 0 ? "in order" : "wrong");
    struct iovec holes[3] = { { "", 0 }, { "x", 1 }, { 0, 0 } };
    N("writev with empty parts", writev(p[1], holes, 3));
    read(p[0], in, 1);
    N("writev of no parts", writev(p[1], two, 0));
    {
        static struct iovec many[1025];
        for (int i = 0; i < 1025; i++) {
            many[i].iov_base = "";
            many[i].iov_len = 0;
        }
        N("writev of 1024 empty parts", writev(p[1], many, 1024));
        N("writev of 1025 parts", writev(p[1], many, 1025));
    }
    N("writev with a bad array", writev(p[1], (struct iovec *)8, 2));
    struct iovec badpart[2] = { { "ok", 2 }, { (void *)8, 4 } };
    r = writev(p[1], badpart, 2);
    say("writev whose second part is a bad pointer: %s\n", r == 2 ? "the first part's 2" : r < 0 ? ename(errno) : "other");
    if (r == 2)
        read(p[0], in, 2);
    N("writev to the read end", writev(p[0], two, 2));
    N("writev to a closed descriptor", writev(77, two, 2));
    int nul = open("/dev/null", O_WRONLY);
    N("writev to /dev/null", writev(nul, two, 2));
    close(nul);
    fcntl(p[1], F_SETFL, O_NONBLOCK);
    while (write(p[1], buf, 4096) > 0)
        ;
    read(p[0], buf, 4096);
    struct iovec big[2] = { { buf, 3000 }, { buf, 3000 } };
    N("writev of 3000 and 3000 to a pipe with room for 4096 (not blocking)", writev(p[1], big, 2));
    N("writev to the full pipe", writev(p[1], two, 2));
    close(p[0]);
    N("writev to a pipe with no reader", writev(p[1], two, 2));
    close(p[1]);
    pair(4600, &l, &c, &s);
    N("writev of 11 and 9 bytes to a stream socket", writev(s, two, 2));
    r = recv_all(c, in, 20);
    say("received: %d bytes, %s\n", r, r == 20 && memcmp(in, "head: 1\r\n\r\nthe body\n", 20) == 0 ? "in order" : "wrong");

    /* --- socket options -------------------------------------------------- */
    v = -1; vl = sizeof v;
    r = getsockopt(l, SOL_SOCKET, SO_ACCEPTCONN, &v, &vl);
    say("SO_ACCEPTCONN on a listener: %s, %d, length %d\n", r < 0 ? ename(errno) : "ok", v, (int)vl);
    v = -1; vl = sizeof v;
    getsockopt(s, SOL_SOCKET, SO_ACCEPTCONN, &v, &vl);
    say("on a connected socket: %d\n", v);
    int u = socket(AF_INET, SOCK_DGRAM, 0);
    v = -1; vl = sizeof v;
    r = getsockopt(u, SOL_SOCKET, SO_ACCEPTCONN, &v, &vl);
    say("on a datagram socket: %s, %d\n", r < 0 ? ename(errno) : "ok", v);
    close(u);
    {
        long long wide = -1;
        char one_byte = 9;
        vl = sizeof wide;
        r = getsockopt(l, SOL_SOCKET, SO_TYPE, &wide, &vl);
        say("SO_TYPE into 8 bytes: %s, length %d, value %d\n", r < 0 ? ename(errno) : "ok", (int)vl, (int)wide);
        vl = 1;
        r = getsockopt(l, SOL_SOCKET, SO_TYPE, &one_byte, &vl);
        say("SO_TYPE into 1 byte: %s, length %d, value %d\n", r < 0 ? ename(errno) : "ok", (int)vl, one_byte);
    }
    N("TCP_NODELAY set", setsockopt(s, IPPROTO_TCP, TCP_NODELAY, &one, sizeof one));
    v = -1; vl = sizeof v;
    getsockopt(s, IPPROTO_TCP, TCP_NODELAY, &v, &vl);
    say("TCP_NODELAY read: %d\n", v);
    close(c); close(s);
    c = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = sin_of("127.0.0.1", 4600);
    connect(c, (struct sockaddr *)&a, sizeof a);
    N("accept4 with a flag that is none (1)", accept4(l, 0, 0, 1));
    s = accept4(l, 0, 0, SOCK_CLOEXEC | SOCK_NONBLOCK);
    say("accept4 SOCK_CLOEXEC|SOCK_NONBLOCK: F_GETFD %d, O_NONBLOCK %s\n", fcntl(s, F_GETFD), fcntl(s, F_GETFL) & O_NONBLOCK ? "set" : "clear");
    struct sockaddr_storage big_name;
    vl = sizeof big_name;
    r = getpeername(l, (struct sockaddr *)&big_name, &vl);
    say("getpeername on a listener, a 128-byte buffer: %s\n", r < 0 ? ename(errno) : "ok");
    vl = sizeof big_name;
    r = getsockname(s, (struct sockaddr *)&big_name, &vl);
    say("getsockname, a 128-byte buffer: %s, length %d\n", r < 0 ? ename(errno) : "ok", (int)vl);
    close(c); close(s); close(l);

    /* --- getrandom --------------------------------------------------------- */
    unsigned char rnd[32];
    N("getrandom 16, GRND_INSECURE", getrandom(rnd, 16, GRND_INSECURE));
    N("getrandom 8, GRND_NONBLOCK", getrandom(rnd, 8, GRND_NONBLOCK));
    N("getrandom 8, no flag", getrandom(rnd, 8, 0));
    N("getrandom 8, GRND_RANDOM", getrandom(rnd, 8, GRND_RANDOM));
    N("getrandom 8, GRND_RANDOM|GRND_INSECURE", getrandom(rnd, 8, GRND_RANDOM | GRND_INSECURE));
    N("getrandom 8, a flag that is none (8)", getrandom(rnd, 8, 8));
    N("getrandom 0 bytes", getrandom(rnd, 0, 0));
    N("getrandom into a bad pointer", getrandom((void *)8, 8, 0));

    /* --- sched_getaffinity, prctl -------------------------------------------- */
    unsigned long mask[16];
    memset(mask, 0, sizeof mask);
    long ar = syscall(SYS_sched_getaffinity, 0, sizeof mask, mask);
    int cpus = 0;
    for (unsigned i = 0; i < sizeof mask * 8; i++)
        cpus += (mask[i / 64] >> (i % 64)) & 1;
    say("sched_getaffinity(0, 128): %ld; at least one CPU: %s\n", ar, cpus >= 1 ? "yes" : "no");
    say("~cpus: %d\n", cpus);
    N("sched_getaffinity into 4 bytes", syscall(SYS_sched_getaffinity, 0, 4, mask));
    N("sched_getaffinity of a thread that is none", syscall(SYS_sched_getaffinity, 999999, sizeof mask, mask));
    N("sched_getaffinity of this thread by its id", syscall(SYS_sched_getaffinity, (long)syscall(SYS_gettid), sizeof mask, mask));
    char name[32] = "";
    N("prctl PR_SET_NAME", prctl(PR_SET_NAME, "wolf-reactor"));
    prctl(PR_GET_NAME, name);
    say("PR_GET_NAME: %s\n", name);

    /* --- the clocks ------------------------------------------------------------ */
    {
        static const int ids[] = { CLOCK_REALTIME, CLOCK_MONOTONIC, CLOCK_MONOTONIC_RAW, CLOCK_REALTIME_COARSE, CLOCK_MONOTONIC_COARSE, CLOCK_BOOTTIME };
        struct timespec t, prev = { 0, 0 };
        int ok = 0, back = 0;
        for (unsigned i = 0; i < sizeof ids / sizeof ids[0]; i++)
            ok += clock_gettime(ids[i], &t) == 0;
        say("clock_gettime: %d of 6 clocks answer\n", ok);
        N("clock_gettime of a clock that is none (64)", clock_gettime(64, &t));
        long distinct = 0;
        for (int i = 0; i < 2000; i++) {
            clock_gettime(CLOCK_MONOTONIC, &t);
            if (t.tv_sec < prev.tv_sec || (t.tv_sec == prev.tv_sec && t.tv_nsec < prev.tv_nsec))
                back++;
            if (t.tv_sec != prev.tv_sec || t.tv_nsec != prev.tv_nsec)
                distinct++;
            prev = t;
        }
        say("CLOCK_MONOTONIC read 2000 times: went backwards %d times\n", back);
        say("~clock: %ld distinct readings of 2000\n", distinct);
        long t0 = ms_now();
        nap(50);
        long dt = ms_now() - t0;
        say("a 50 ms sleep by CLOCK_MONOTONIC: at least 50 ms: %s, under 200: %s\n", dt >= 50 ? "yes" : "no", dt < 200 ? "yes" : "no");
        struct timeval now;
        gettimeofday(&now, 0);
        clock_gettime(CLOCK_REALTIME, &t);
        say("CLOCK_REALTIME and gettimeofday agree to a second: %s; after 2020: %s\n",
            t.tv_sec - now.tv_sec <= 1 && now.tv_sec - t.tv_sec <= 1 ? "yes" : "no", t.tv_sec > 1577836800 ? "yes" : "no");
    }

    altstack();
    two_threads();
    say("restprobe: done\n");
    return 0;
}
