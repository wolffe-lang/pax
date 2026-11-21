/* clock.c — px168: root sets the clock. What root's clock_settime(2) and
 * settimeofday(2) do and what a user is told; the time zone settimeofday
 * keeps; adjtimex(2) and clock_adjtime(2); and what a set does to the other
 * clocks, to relative and absolute sleeps, to a futex wait on the wall clock
 * and to the times of a file made after it.
 *
 *   clock DIR          as root, DIR a directory it may write: every row
 *   clock user DIR     as a user (after `as 1000 1000`): what a user is told
 *
 * Every line starts with its row's name. Times are said against a margin
 * (yes, or which of the expected outcomes happened), never as dates, so a
 * line is the same on every boot of either kernel. Every call is a raw
 * system call: glibc answers the time calls in user space through Linux's
 * vDSO, and PAX has none, so only the call itself is the same on both.
 * Root's session ends by putting the clock back where it would have been. */
#include "px38.h"
#include <linux/futex.h>
#include <poll.h>
#include <pthread.h>
#include <sys/mman.h>
#include <sys/time.h>
#include <sys/timex.h>
#include <time.h>

#define NS 1000000000LL
#define T2030 1906502400LL /* 2030-06-01T00:00:00Z */
#define T2001 978307200LL  /* 2001-01-01T00:00:00Z */
#define T2100 4102444800LL /* 2100-01-01T00:00:00Z */

static const char *D;
static void *unmapped;


static long rc6(long nr, long a, long b, long c, long d, long e, long f)
{
    long r = syscall(nr, a, b, c, d, e, f);
    return r == -1 ? -(long)errno : r;
}

static long long now(int clk)
{
    struct timespec t = { 0, 0 };
    if (rc(SYS_clock_gettime, clk, (long)&t, 0, 0, 0) != 0) return -1;
    return (long long)t.tv_sec * NS + t.tv_nsec;
}

static long long mono(void) { return now(CLOCK_MONOTONIC); }

static long set_rt(long long sec, long nsec)
{
    struct timespec t = { (time_t)sec, nsec };
    return rc(SYS_clock_settime, CLOCK_REALTIME, (long)&t, 0, 0, 0);
}

static long set_tv(long long sec, long usec)
{
    struct timeval t = { (time_t)sec, usec };
    return rc(SYS_settimeofday, (long)&t, 0, 0, 0, 0);
}

static void nap_ms(long ms)
{
    struct timespec t = { ms / 1000, (ms % 1000) * 1000000 };
    while (rc(SYS_nanosleep, (long)&t, (long)&t, 0, 0, 0) == -EINTR) {}
}

/* "yes" when time v (ns) lies within [want - 0.5 s, want + 2 s], else
 * "no" with how far off it is (a red row says by how much). */
static const char *near(long long v, long long want)
{
    static char b[8][48];
    static int k;
    char *o = b[k++ % 8];
    if (v >= want - NS / 2 && v <= want + 2 * NS) return "yes";
    snprintf(o, 48, "no (%+lld ms)", (v - want) / 1000000);
    return o;
}

static long long st_ns(const struct timespec *t) { return (long long)t->tv_sec * NS + t->tv_nsec; }

/* A file made now, and a file whose times utimensat(UTIME_NOW) sets now:
 * how each of their times lies against `want`. */
static void file_times(const char *tag, long long want, char *out, size_t n)
{
    char p[512], q[512];
    snprintf(p, sizeof p, "%s/made-%s", D, tag);
    snprintf(q, sizeof q, "%s/touched-%s", D, tag);
    unlink(p);
    int fd = open(p, O_CREAT | O_WRONLY | O_TRUNC, 0644);
    struct stat st;
    memset(&st, 0, sizeof st);
    if (fd >= 0) { fstat(fd, &st); close(fd); }
    int g = open(q, O_CREAT | O_WRONLY, 0644);
    if (g >= 0) close(g);
    struct timespec tt[2] = { { 0, UTIME_NOW }, { 0, UTIME_NOW } };
    long u = rc(SYS_utimensat, AT_FDCWD, (long)q, (long)tt, 0, 0);
    struct stat su;
    memset(&su, 0, sizeof su);
    stat(q, &su);
    snprintf(out, n, "a new file's mtime %s, ctime %s, atime %s; utimensat(UTIME_NOW) %ld, its mtime %s",
             near(st_ns(&st.st_mtim), want), near(st_ns(&st.st_ctim), want), near(st_ns(&st.st_atim), want), u,
             near(st_ns(&su.st_mtim), want));
}

static void remove_files(void)
{
    static const char *tags[] = { "set", "back" };
    for (unsigned i = 0; i < 2; i++) {
        char p[512];
        snprintf(p, sizeof p, "%s/made-%s", D, tags[i]);
        unlink(p);
        snprintf(p, sizeof p, "%s/touched-%s", D, tags[i]);
        unlink(p);
    }
}

/* --- the time zone (first: the first call that names a zone is special) ---- */

static long tz_set(int west, int dst)
{
    struct timezone z = { west, dst };
    return rc(SYS_settimeofday, 0, (long)&z, 0, 0, 0);
}

static void tz_read(struct timezone *z)
{
    struct timeval tv;
    z->tz_minuteswest = -7777;
    z->tz_dsttime = -7777;
    rc(SYS_gettimeofday, (long)&tv, (long)z, 0, 0, 0);
}

/* The minutes the wall clock moved, beyond the time that passed, across `r = call()`. */
#define MOVED(call, r, minutes)                                                                                         \
    do {                                                                                                                \
        long long a_ = now(CLOCK_REALTIME), ma_ = mono();                                                               \
        r = call;                                                                                                       \
        long long b_ = now(CLOCK_REALTIME), mb_ = mono();                                                               \
        long long j_ = (b_ - a_) - (mb_ - ma_);                                                                         \
        minutes = (j_ >= 0 ? j_ + 30 * NS : j_ - 30 * NS) / (60 * NS);                                                  \
    } while (0)

static void timezone_rows(void)
{
    struct timezone z0, z1, z2, z3;
    long r1, r2;
    long long m1, m2;
    tz_read(&z0);
    MOVED(tz_set(60, 0), r1, m1);
    tz_read(&z1);
    MOVED(tz_set(120, 0), r2, m2);
    tz_read(&z2);
    say("clock-timezone: gettimeofday's zone %d %d; settimeofday(NULL, {60, 0}) %ld, the clock moved %lld minutes, "
        "the zone %d %d; settimeofday(NULL, {120, 0}) %ld, moved %lld minutes, the zone %d %d\n",
        z0.tz_minuteswest, z0.tz_dsttime, r1, m1, z1.tz_minuteswest, z1.tz_dsttime, r2, m2, z2.tz_minuteswest,
        z2.tz_dsttime);
    long a = tz_set(900, 0), b = tz_set(901, 0), c = tz_set(-900, 0), d = tz_set(-901, 0), e = tz_set(0, 1);
    long f = rc(SYS_settimeofday, 0, (long)unmapped, 0, 0, 0);
    long g = tz_set(0, 0);
    tz_read(&z3);
    say("clock-timezone: settimeofday(NULL, {900, 0}) %ld, {901, 0} %ld, {-900, 0} %ld, {-901, 0} %ld, {0, 1} %ld, "
        "an unmapped zone %ld; settimeofday(NULL, {0, 0}) %ld, the zone %d %d\n",
        a, b, c, d, e, f, g, z3.tz_minuteswest, z3.tz_dsttime);
}

/* --- what a set refuses ------------------------------------------------------ */

static void invalid_rows(const char *who)
{
    struct timespec ts;
    long long w = now(CLOCK_REALTIME);
#define CS(clk, s, n) (ts.tv_sec = (s), ts.tv_nsec = (n), rc(SYS_clock_settime, (clk), (long)&ts, 0, 0, 0))
    long a = CS(CLOCK_REALTIME, w / NS, w % NS);
    long b = CS(CLOCK_REALTIME, w / NS, 1000000000L), c = CS(CLOCK_REALTIME, w / NS, -1L);
    long d = CS(CLOCK_REALTIME, -1L, 0), e = CS(CLOCK_REALTIME, 0, 1);
    long f = CS(CLOCK_REALTIME, T2100, 0), g = CS(CLOCK_REALTIME, 1LL << 33, 0), h = CS(CLOCK_REALTIME, 1LL << 40, 0);
    long i = CS(CLOCK_REALTIME, 1LL << 62, 0), j = CS(CLOCK_REALTIME, 0x7fffffffffffffffLL, 0);
    long k = rc(SYS_clock_settime, CLOCK_REALTIME, 0, 0, 0, 0), l = rc(SYS_clock_settime, CLOCK_REALTIME, (long)unmapped, 0, 0, 0);
    w = now(CLOCK_REALTIME);
    long m = CS(CLOCK_MONOTONIC, w / NS, 0), n = CS(CLOCK_REALTIME_COARSE, w / NS, 0), o = CS(CLOCK_REALTIME_ALARM, w / NS, 0);
    long p = CS(CLOCK_TAI, w / NS, 0), q = CS(CLOCK_BOOTTIME, w / NS, 0), r = CS(99, w / NS, 0);
#undef CS
    say("%s: clock_settime(CLOCK_REALTIME) to now %ld; tv_nsec 1000000000 %ld, -1 %ld; tv_sec -1 %ld; {0, 1} (below "
        "CLOCK_MONOTONIC) %ld; 2100-01-01 %ld, 2^33 s %ld, 2^40 s %ld, 2^62 s %ld, 2^63 - 1 s %ld; NULL %ld, an unmapped "
        "timespec %ld; to now on CLOCK_MONOTONIC %ld, CLOCK_REALTIME_COARSE %ld, CLOCK_REALTIME_ALARM %ld, CLOCK_TAI %ld, "
        "CLOCK_BOOTTIME %ld, clock 99 %ld\n",
        who, a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r);
    w = now(CLOCK_REALTIME);
    struct timezone z = { 0, 0 };
    long A = set_tv(w / NS, (w % NS) / 1000);
    long B = set_tv(w / NS, 1000000L), C = set_tv(w / NS, -1L), Dd = set_tv(-1, 0), E = set_tv(0, 1);
    long F = set_tv(1LL << 40, 0);
    long G = rc(SYS_settimeofday, (long)unmapped, 0, 0, 0, 0);
    long H = rc(SYS_settimeofday, 0, 0, 0, 0, 0);
    long I = rc(SYS_settimeofday, 0, (long)&z, 0, 0, 0);
    say("%s: settimeofday to now %ld; tv_usec 1000000 %ld, -1 %ld; tv_sec -1 %ld; {0, 1} (below CLOCK_MONOTONIC) %ld; "
        "2^40 s %ld; an unmapped timeval %ld; (NULL, NULL) %ld; (NULL, {0, 0}) %ld\n",
        who, A, B, C, Dd, E, F, G, H, I);
}

/* --- root's sets ------------------------------------------------------------- */

static void reads(long long want, char *out, size_t n)
{
    struct timeval tv = { 0, 0 };
    long long rt = now(CLOCK_REALTIME), co = now(CLOCK_REALTIME_COARSE), tai = now(CLOCK_TAI);
    long t = rc(SYS_time, 0, 0, 0, 0, 0);
    rc(SYS_gettimeofday, (long)&tv, 0, 0, 0, 0);
    snprintf(out, n, "CLOCK_REALTIME %s, CLOCK_REALTIME_COARSE %s, CLOCK_TAI %s, time %s, gettimeofday %s", near(rt, want),
             near(co, want), near(tai, want), near((long long)t * NS, want - NS / 2 + 1),
             near((long long)tv.tv_sec * NS + tv.tv_usec * 1000LL, want));
}

static long long m_set_before, m_set_after, b_set_before, b_set_after, m_back_before, m_back_after, b_back_before, b_back_after;
static long r_set, r_back;

static void set_rows(void)
{
    char rd[400], ft[400];
    m_set_before = mono(); b_set_before = now(CLOCK_BOOTTIME);
    r_set = set_rt(T2030, 0);
    m_set_after = mono(); b_set_after = now(CLOCK_BOOTTIME);
    reads(T2030 * NS, rd, sizeof rd);
    file_times("set", T2030 * NS, ft, sizeof ft);
    say("clock-root-set: clock_settime(CLOCK_REALTIME, 2030-06-01T00:00:00Z) %ld; within 2 s of it: %s; %s\n", r_set, rd, ft);

    m_back_before = mono(); b_back_before = now(CLOCK_BOOTTIME);
    r_back = set_rt(T2001, 0);
    m_back_after = mono(); b_back_after = now(CLOCK_BOOTTIME);
    reads(T2001 * NS, rd, sizeof rd);
    file_times("back", T2001 * NS, ft, sizeof ft);
    long f = set_tv(T2030 + 100, 500000);
    char rf[400];
    reads((T2030 + 100) * NS + 500000000LL, rf, sizeof rf);
    say("clock-root-back: clock_settime(CLOCK_REALTIME, 2001-01-01T00:00:00Z) %ld; within 2 s of it: %s; %s; "
        "settimeofday forward to 2030-06-01T00:01:40.5Z %ld; within 2 s of it: %s\n", r_back, rd, ft, f, rf);
}

static const char *steady(long long before, long long after)
{
    return after >= before && after - before < 2 * NS ? "yes" : "no";
}

static void monotonic_row(void)
{
    say("clock-monotonic-steady: across clock_settime to 2030 (%ld) CLOCK_MONOTONIC moved under 2 s %s, CLOCK_BOOTTIME "
        "%s; across clock_settime to 2001 (%ld) CLOCK_MONOTONIC %s, CLOCK_BOOTTIME %s\n",
        r_set, steady(m_set_before, m_set_after), steady(b_set_before, b_set_after), r_back,
        steady(m_back_before, m_back_after), steady(b_back_before, b_back_after));
}

/* --- sleeps across a set ----------------------------------------------------- */

struct woke { long r; long long m; };

/* A child that runs `kind`'s sleep and writes what it returned and when
 * (CLOCK_MONOTONIC) it woke into a pipe. */
static pid_t sleeper(int kind, long long arg, int *fd)
{
    int p[2];
    if (pipe(p) != 0) return -1;
    pid_t c = fork();
    if (c == 0) {
        close(p[0]);
        struct timespec t = { (time_t)(arg / NS), (long)(arg % NS) };
        struct woke w;
        if (kind == 0) w.r = rc(SYS_clock_nanosleep, CLOCK_REALTIME, 0, (long)&t, 0, 0);
        else if (kind == 1) w.r = rc(SYS_nanosleep, (long)&t, 0, 0, 0, 0);
        else w.r = rc(SYS_clock_nanosleep, CLOCK_REALTIME, TIMER_ABSTIME, (long)&t, 0, 0);
        w.m = mono();
        if (write(p[1], &w, sizeof w) != sizeof w) _exit(3);
        _exit(0);
    }
    close(p[1]);
    *fd = p[0];
    return c;
}

/* What a sleeper wrote, waiting at most `ms`; 0 when it wrote, -1 when not. */
static int heard(int fd, long ms, struct woke *w)
{
    struct pollfd q = { fd, POLLIN, 0 };
    if (poll(&q, 1, (int)ms) != 1) return -1;
    return read(fd, w, sizeof *w) == sizeof *w ? 0 : -1;
}

static void done_with(pid_t c, int fd, int heard_it)
{
    if (!heard_it) kill(c, SIGKILL);
    reap(c);
    close(fd);
}

static void rel_sleep_row(void)
{
    int fa, fb;
    long long t0 = mono();
    pid_t a = sleeper(0, 3 * NS, &fa), b = sleeper(1, 3 * NS, &fb);
    nap_ms(1000);
    long long w = now(CLOCK_REALTIME);
    long s = set_rt(w / NS + 3600, w % NS);
    struct woke wa = { 0, 0 }, wb = { 0, 0 };
    int ha = heard(fa, 20000, &wa) == 0, hb = heard(fb, 20000, &wb) == 0;
    done_with(a, fa, ha);
    done_with(b, fb, hb);
    const char *ya = ha && wa.m - t0 >= 3 * NS && wa.m - t0 < 10 * NS ? "yes" : "no";
    const char *yb = hb && wb.m - t0 >= 3 * NS && wb.m - t0 < 10 * NS ? "yes" : "no";
    say("clock-rel-sleep-steady: across clock_settime an hour forward (%ld) a relative 3 s clock_nanosleep(CLOCK_REALTIME) "
        "%ld ended after 3 s and before 10 s %s; nanosleep %ld, %s\n",
        s, wa.r, ya, wb.r, yb);
}

/* How long after a set, d (ns), a waiter came back, said as one of the outcomes. */
static const char *after_set(long long d)
{
    static char b[48];
    if (d >= 0 && d < 5 * NS) return "within 5 s of the set";
    if (d >= 9 * NS && d < 25 * NS) return "at the deadline the call computed";
    snprintf(b, sizeof b, "%lld ms after the set", d / 1000000);
    return b;
}

static void abs_sleep_rows(void)
{
    int fd;
    long long w = now(CLOCK_REALTIME), dl = w + 12 * NS;
    pid_t c = sleeper(2, dl, &fd);
    nap_ms(1000);
    long long ms = mono();
    long s = set_rt(dl / NS + 60, 0);
    struct woke k = { 0, 0 };
    int h = heard(fd, 30000, &k) == 0;
    done_with(c, fd, h);
    say("clock-abs-sleep-follows: forward: a TIMER_ABSTIME clock_nanosleep to CLOCK_REALTIME + 12 s, the clock set past "
        "it at 1 s (%ld): the sleep %ld came back %s\n",
        s, k.r, h ? after_set(k.m - ms) : "never (30 s)");

    long long t0 = mono();
    w = now(CLOCK_REALTIME);
    dl = w + 3 * NS;
    c = sleeper(2, dl, &fd);
    nap_ms(1000);
    long long w1 = now(CLOCK_REALTIME);
    long s1 = set_rt(w1 / NS - 3600, w1 % NS);
    long long rest = 6 * NS - (mono() - t0);
    struct woke k2 = { 0, 0 };
    int early = heard(fd, rest > 0 ? (long)(rest / 1000000) : 0, &k2) == 0;
    int h2 = early;
    if (early) {
        done_with(c, fd, 1);
        say("clock-abs-sleep-follows: back: a TIMER_ABSTIME clock_nanosleep to CLOCK_REALTIME + 3 s, the clock set an hour "
            "back at 1 s (%ld): the sleep %ld came back before the clock reached its deadline\n", s1, k2.r);
        return;
    }
    long long m2 = mono();
    long s2 = set_rt(dl / NS + 60, 0);
    h2 = heard(fd, 30000, &k2) == 0;
    const char *then = h2 ? (k2.m - m2 >= 0 && k2.m - m2 < 5 * NS ? "came back within 5 s of it" : "came back later")
                          : "never came back (30 s)";
    done_with(c, fd, h2);
    say("clock-abs-sleep-follows: back: a TIMER_ABSTIME clock_nanosleep to CLOCK_REALTIME + 3 s, the clock set an hour "
        "back at 1 s (%ld): still asleep at 6 s; the clock set past the deadline then (%ld): the sleep %ld %s\n",
        s1, s2, k2.r, then);
}

/* --- a futex wait on the wall clock across a set ------------------------------ */

static int fword;
static volatile long f_r;
static volatile long long f_m;
static volatile int f_done;
static struct timespec f_t;
static int f_op;

static void *fwaiter(void *x)
{
    (void)x;
    f_r = rc6(SYS_futex, (long)&fword, f_op, 0, (long)&f_t, 0, FUTEX_BITSET_MATCH_ANY);
    f_m = mono();
    __atomic_store_n(&f_done, 1, __ATOMIC_SEQ_CST);
    return NULL;
}

static pthread_t fstart(int op, long long arg)
{
    pthread_t t;
    f_op = op;
    f_t.tv_sec = (time_t)(arg / NS);
    f_t.tv_nsec = (long)(arg % NS);
    f_done = 0;
    pthread_create(&t, NULL, fwaiter, NULL);
    return t;
}

/* Whether the waiter came back within `ms`. */
static int fback(long ms)
{
    for (long i = 0; i * 20 < ms; i++) {
        if (__atomic_load_n(&f_done, __ATOMIC_SEQ_CST)) return 1;
        nap_ms(20);
    }
    return __atomic_load_n(&f_done, __ATOMIC_SEQ_CST);
}

static void futex_rows(void)
{
    const int abs = FUTEX_WAIT_BITSET | FUTEX_PRIVATE_FLAG | FUTEX_CLOCK_REALTIME;
    long long w = now(CLOCK_REALTIME), dl = w + 12 * NS;
    pthread_t t = fstart(abs, dl);
    nap_ms(1000);
    long long ms = mono();
    long s = set_rt(dl / NS + 60, 0);
    int h = fback(30000);
    say("clock-futex-realtime: forward: FUTEX_WAIT_BITSET|FUTEX_CLOCK_REALTIME to CLOCK_REALTIME + 12 s, the clock set "
        "past it at 1 s (%ld): the wait %ld came back %s\n",
        s, h ? f_r : 0L, h ? after_set(f_m - ms) : "never (30 s)");
    if (h) pthread_join(t, NULL);
    else return;

    long long t0 = mono();
    w = now(CLOCK_REALTIME);
    dl = w + 3 * NS;
    t = fstart(abs, dl);
    nap_ms(1000);
    long long w1 = now(CLOCK_REALTIME);
    long s1 = set_rt(w1 / NS - 3600, w1 % NS);
    long long rest = 6 * NS - (mono() - t0);
    int early = fback(rest > 0 ? (long)(rest / 1000000) : 0);
    if (early) {
        pthread_join(t, NULL);
        say("clock-futex-realtime: back: FUTEX_WAIT_BITSET|FUTEX_CLOCK_REALTIME to CLOCK_REALTIME + 3 s, the clock set an "
            "hour back at 1 s (%ld): the wait %ld came back before the clock reached its deadline\n", s1, f_r);
    } else {
        long long m2 = mono();
        long s2 = set_rt(dl / NS + 60, 0);
        int h2 = fback(30000);
        const char *then = h2 ? (f_m - m2 >= 0 && f_m - m2 < 5 * NS ? "came back within 5 s of it" : "came back later")
                              : "never came back (30 s)";
        say("clock-futex-realtime: back: FUTEX_WAIT_BITSET|FUTEX_CLOCK_REALTIME to CLOCK_REALTIME + 3 s, the clock set an "
            "hour back at 1 s (%ld): still waiting at 6 s; the clock set past the deadline then (%ld): the wait %ld %s\n",
            s1, s2, h2 ? f_r : 0L, then);
        if (!h2) return;
        pthread_join(t, NULL);
    }

    t0 = mono();
    t = fstart(FUTEX_WAIT | FUTEX_PRIVATE_FLAG | FUTEX_CLOCK_REALTIME, 3 * NS);
    nap_ms(1000);
    w = now(CLOCK_REALTIME);
    long s3 = set_rt(w / NS + 3600, w % NS);
    long long m3 = mono();
    int h3 = fback(30000);
    const char *how = !h3 ? "never (30 s)"
                    : f_m - m3 < 1 * NS ? "within 1 s of the set"
                    : f_m - t0 >= 3 * NS && f_m - t0 < 10 * NS ? "after 3 s, as if no set" : "at another time";
    say("clock-futex-realtime: relative: FUTEX_WAIT|FUTEX_CLOCK_REALTIME for 3 s, the clock set an hour forward at 1 s "
        "(%ld): the wait %ld came back %s\n",
        s3, h3 ? f_r : 0L, how);
    if (h3) pthread_join(t, NULL);
}

/* --- adjtimex and clock_adjtime ---------------------------------------------- */

static long adj(int modes)
{
    struct timex t;
    memset(&t, 0, sizeof t);
    t.modes = modes;
    return rc(SYS_adjtimex, (long)&t, 0, 0, 0, 0);
}

static long cadj(long clk, int modes)
{
    struct timex t;
    memset(&t, 0, sizeof t);
    t.modes = modes;
    return rc(SYS_clock_adjtime, clk, (long)&t, 0, 0, 0);
}

static void adjtime_rows(const char *who)
{
    long r0 = adj(0), r1 = adj(ADJ_OFFSET_SS_READ), r2 = cadj(CLOCK_REALTIME, 0);
    say("%s: reads: adjtimex modes 0 %ld, ADJ_OFFSET_SS_READ %ld; clock_adjtime(CLOCK_REALTIME, modes 0) %ld\n", who, r0, r1, r2);
    long s0 = adj(ADJ_OFFSET), s1 = adj(ADJ_FREQUENCY), s2 = adj(ADJ_SETOFFSET), s3 = cadj(CLOCK_REALTIME, ADJ_OFFSET);
    say("%s: sets: adjtimex ADJ_OFFSET %ld, ADJ_FREQUENCY %ld, ADJ_SETOFFSET %ld; clock_adjtime(CLOCK_REALTIME, "
        "ADJ_OFFSET) %ld\n",
        who, s0, s1, s2, s3);
    long e0 = rc(SYS_adjtimex, 0, 0, 0, 0, 0), e1 = rc(SYS_adjtimex, (long)unmapped, 0, 0, 0, 0);
    long e2 = cadj(CLOCK_MONOTONIC, 0), e3 = cadj(99, 0), e4 = rc(SYS_clock_adjtime, CLOCK_REALTIME, 0, 0, 0, 0);
    say("%s: errors: adjtimex(NULL) %ld, an unmapped buffer %ld; clock_adjtime(CLOCK_MONOTONIC, modes 0) %ld, (99, "
        "modes 0) %ld, (CLOCK_REALTIME, NULL) %ld\n",
        who, e0, e1, e2, e3, e4);
}

int main(int argc, char **argv)
{
    int user = argc >= 2 && !strcmp(argv[1], "user");
    if (argc < 2 + user) { say("usage: clock [user] DIR\n"); return 2; }
    D = argv[1 + user];
    unmapped = (void *)0x1000; /* below every mapping either kernel makes for a static program */
    if (user) {
        invalid_rows("clock-user-refused");
        adjtime_rows("clock-user-adjtime");
        return 0;
    }
    long long r0 = now(CLOCK_REALTIME), m0 = mono();
    timezone_rows();
    invalid_rows("clock-invalid");
    set_rows();
    monotonic_row();
    rel_sleep_row();
    abs_sleep_rows();
    futex_rows();
    adjtime_rows("clock-adjtime");
    long long back = r0 + (mono() - m0);
    long r = set_rt(back / NS, back % NS);
    long long chk = now(CLOCK_REALTIME);
    remove_files();
    say("clock-restore: clock_settime(CLOCK_REALTIME) back to the time it would have been %ld; within 2 s of it %s\n", r,
        near(chk, back));
    return 0;
}
