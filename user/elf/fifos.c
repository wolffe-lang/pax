/* fifos.c — px62's probe of named pipes and advisory locks (pax#108):
   one static glibc program that prints what it sees, run unmodified as
   the first program on Linux (its root a tmpfs, inside a throwaway
   container) and on PAX (tests/mpx3-maps), the two outputs compared
   byte for byte.

     fifos         every row, in order (it works in /t/q, which it makes
                   and removes; /t is the image's)

   The rows:
     fifo:  mkfifo and mknodat (a FIFO, a regular file, the errnos), what
            stat, fstat and a directory's listing say of one, the open
            rules of fifo(7) (a reader waits for a writer and a writer for
            a reader, O_NONBLOCK's read end at once and write end ENXIO,
            O_RDWR at once), a signal ending a waiting open, 70,000 bytes
            through one (more than it holds), end of file, SIGPIPE's
            EPIPE, the bytes gone when every end has closed, a name
            removed while it is open, and s254's `[os.fs.mkfifo]` rows as
            the system calls they make;
     flock: s254's `[os.fs.lock]` rows as the system calls they make (an
            exclusive lock refused to a second open of the file, shared
            locks together, a close releasing), the errnos, dup and fork
            sharing one lock, a lock that waits for an unlock, a signal
            ending a wait, a conversion LOCK_NB refuses, and a lock on a
            FIFO, a directory and a pipe.

   Built with the host's cc: `cc -static -O1` (tools/mkprobes). Nothing
   here reads a kernel's or a libc's source: the calls are the man
   pages', the structures the public headers'. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static void say(const char *fmt, ...) {
    char b[1024];
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

static long r(long v) { return v == -1 ? -errno : v; }
static const char *yes(int b) { return b ? "yes" : "no"; }
static void ms(int n) {
    struct timespec t = { n / 1000, (n % 1000) * 1000000L };
    while (nanosleep(&t, &t) != 0 && errno == EINTR) {}
}
static uint32_t fnv(const unsigned char *p, long n, uint32_t h) {
    for (long i = 0; i < n; i++) h = (h ^ p[i]) * 16777619u;
    return h;
}
/* "mode 10640 links 1 size 0 blocks 0", or "-2" */
static const char *st(const char *path) {
    static char b[4][96];
    static int k;
    struct stat s;
    char *o = b[k++ & 3];
    if (stat(path, &s) != 0) snprintf(o, 96, "%d", -errno);
    else snprintf(o, 96, "mode %o links %lu size %lld blocks %lld", s.st_mode, (unsigned long)s.st_nlink,
                  (long long)s.st_size, (long long)s.st_blocks);
    return o;
}
static const char *fst(int fd) {
    static char b[4][96];
    static int k;
    struct stat s;
    char *o = b[k++ & 3];
    if (fstat(fd, &s) != 0) snprintf(o, 96, "%d", -errno);
    else snprintf(o, 96, "mode %o links %lu size %lld blocks %lld", s.st_mode, (unsigned long)s.st_nlink,
                  (long long)s.st_size, (long long)s.st_blocks);
    return o;
}
static int same_inode(const char *path, int fd) {
    struct stat a, b;
    return stat(path, &a) == 0 && fstat(fd, &b) == 0 && a.st_ino == b.st_ino && a.st_dev == b.st_dev;
}
/* the d_type a listing of `dir` gives `name`, or -1 */
static int dtype(const char *dir, const char *name) {
    DIR *d = opendir(dir);
    if (!d) return -errno;
    struct dirent *e;
    int t = -1;
    while ((e = readdir(d)) != NULL)
        if (strcmp(e->d_name, name) == 0) t = e->d_type;
    closedir(d);
    return t;
}

static volatile int usr1;
static void on_usr1(int s) { (void)s; usr1++; }

/* --- FIFOs ---------------------------------------------------------------- */

static void fifo_rows(void) {
    char b[80000];
    long x1 = r(mkfifo("/t/q/f", 0640));
    const char *s1 = st("/t/q/f");
    long x2 = r(mkfifo("/t/q/f", 0640));
    say("fifo: mkfifo 0640: %ld; stat %s; again %ld\n", x1, s1, x2);
    say("fifo: its listing's type %d\n", dtype("/t/q", "f"));
    x1 = r(mkfifo("/t/q/none/x", 0600));
    x2 = r(mkfifo("/t/q/sticky", 01777));
    say("fifo: mkfifo in a directory that is not there %ld, mode 01777 %ld (%s)\n", x1, x2, st("/t/q/sticky"));
    int dfd = open("/t/q", O_RDONLY | O_DIRECTORY);
    x1 = r(mknodat(dfd, "g", S_IFIFO | 0600, 0));
    say("fifo: mknodat S_IFIFO|0600 %ld (%s)\n", x1, st("/t/q/g"));
    x1 = r(mknodat(dfd, "reg", S_IFREG | 0644, 0));
    say("fifo: mknodat S_IFREG|0644 %ld (%s)\n", x1, st("/t/q/reg"));
    x1 = r(mknodat(dfd, "reg0", 0644, 0));
    say("fifo: mknodat of type 0 %ld (%s)\n", x1, st("/t/q/reg0"));
    x1 = r(mknod("/t/q/g", S_IFIFO | 0600, 0));
    x2 = r(mknod("/t/q/bad", S_IFMT | 0600, 0));
    say("fifo: mknod of a name that is there %ld, a type that is none %ld\n", x1, x2);
    x1 = r(unlinkat(dfd, "g", 0));
    x2 = r(unlink("/t/q/reg"));
    long x3 = r(unlink("/t/q/reg0")), x4 = r(unlink("/t/q/sticky"));
    say("fifo: removed g, reg, reg0, sticky: %ld %ld %ld %ld\n", x1, x2, x3, x4);
    close(dfd);

    /* O_NONBLOCK's two ends, and O_RDWR */
    int rd = open("/t/q/f", O_RDONLY | O_NONBLOCK);
    say("fifo: the read end with O_NONBLOCK and no writer: %s; fstat %s, the name's inode %s\n", rd >= 0 ? "opened" : "refused",
        fst(rd), yes(same_inode("/t/q/f", rd)));
    say("fifo: a read with no writer: %ld\n", r(read(rd, b, 16)));
    x1 = r(lseek(rd, 0, SEEK_SET));
    x2 = r(fcntl(rd, F_GETPIPE_SZ));
    say("fifo: lseek %ld, F_GETPIPE_SZ %ld\n", x1, x2);
    int wr = open("/t/q/f", O_WRONLY | O_NONBLOCK);
    x1 = r(write(wr, "x", 1));
    x2 = r(read(rd, b, 16));
    say("fifo: the write end with O_NONBLOCK and a reader: %s; written %ld; read %ld\n", wr >= 0 ? "opened" : "refused", x1, x2);
    say("fifo: a read with a writer and nothing written: %ld\n", r(read(rd, b, 16)));
    close(wr);
    say("fifo: a read after the writer closed: %ld\n", r(read(rd, b, 16)));
    close(rd);
    say("fifo: the write end with O_NONBLOCK and no reader: %ld\n", r(open("/t/q/f", O_WRONLY | O_NONBLOCK)));
    int both = open("/t/q/f", O_RDWR);
    say("fifo: O_RDWR with nobody else: %s; written %ld\n", both >= 0 ? "opened" : "refused", r(write(both, "abc", 3)));
    close(both);
    both = open("/t/q/f", O_RDWR | O_NONBLOCK);
    say("fifo: reopened after every end closed: what was written is gone: %ld\n", r(read(both, b, 16)));
    close(both);

    /* a reader waits for its writer */
    int *flag = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    flag[0] = 0;
    pid_t k = fork();
    if (k == 0) {
        ms(200);
        flag[0] = 1;
        int w = open("/t/q/f", O_WRONLY);
        if (w < 0) _exit(3);
        static char big[70000];
        for (int i = 0; i < 70000; i++) big[i] = (char)(i * 13 + 5);
        long n = write(w, big, sizeof big);
        close(w);
        _exit(n == 70000 ? 0 : 4);
    }
    int rfd = open("/t/q/f", O_RDONLY);
    int after = flag[0];
    long got = 0, n;
    uint32_t h = 2166136261u;
    while ((n = read(rfd, b, sizeof b)) > 0) {
        h = fnv((unsigned char *)b, n, h);
        got += n;
    }
    int status = 0;
    waitpid(k, &status, 0);
    say("fifo: a reader waited for its writer: opened %s, after the writer's open began %s; %ld bytes (%08x), then %ld; the writer's status %d\n",
        rfd >= 0 ? "yes" : "no", yes(after == 1), got, h, n, status);
    close(rfd);

    /* a writer waits for its reader */
    flag[0] = 0;
    k = fork();
    if (k == 0) {
        ms(200);
        flag[0] = 1;
        int rr = open("/t/q/f", O_RDONLY);
        char c[32];
        long m2 = read(rr, c, 16);
        long m3 = read(rr, c + 16, 16);
        say("fifo: the reader read %ld bytes (%.5s), then %ld\n", m2, c, m3);
        close(rr);
        _exit(0);
    }
    int wfd = open("/t/q/f", O_WRONLY);
    after = flag[0];
    long wn = r(write(wfd, "hello", 5));
    close(wfd);
    waitpid(k, &status, 0);
    say("fifo: a writer waited for its reader: opened %s, after the reader's open began %s; wrote %ld; the reader's status %d\n",
        wfd >= 0 ? "yes" : "no", yes(after == 1), wn, status);

    /* a signal ends a waiting open; nothing of it is left behind */
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = on_usr1;
    sigaction(SIGUSR1, &sa, NULL);
    pid_t me = getpid();
    k = fork();
    if (k == 0) {
        ms(200);
        kill(me, SIGUSR1);
        _exit(0);
    }
    long e = r(open("/t/q/f", O_RDONLY));
    waitpid(k, &status, 0);
    say("fifo: a waiting open of the read end, a handled SIGUSR1 without SA_RESTART: %ld (handled %d); then the write end with O_NONBLOCK: %ld\n",
        e, usr1, r(open("/t/q/f", O_WRONLY | O_NONBLOCK)));

    /* SIGPIPE's EPIPE, and a name removed while open */
    signal(SIGPIPE, SIG_IGN);
    rd = open("/t/q/f", O_RDONLY | O_NONBLOCK);
    wr = open("/t/q/f", O_WRONLY | O_NONBLOCK);
    close(rd);
    say("fifo: a write with the reader gone (SIGPIPE ignored): %ld\n", r(write(wr, "y", 1)));
    close(wr);
    rd = open("/t/q/f", O_RDONLY | O_NONBLOCK);
    wr = open("/t/q/f", O_WRONLY | O_NONBLOCK);
    x1 = r(unlink("/t/q/f"));
    x2 = r(write(wr, "zz", 2));
    x3 = r(read(rd, b, 16));
    say("fifo: its name removed while open: %ld; written %ld, read %ld; fstat %s\n", x1, x2, x3, fst(rd));
    close(rd);
    close(wr);
    signal(SIGPIPE, SIG_DFL);

    /* s254's [os.fs.mkfifo] rows, as their system calls */
    x1 = r(mkfifo("/t/q/ff", 0600));
    x2 = r(mkfifo("/t/q/ff", 0600));
    x3 = r(mkfifo("/t/q/ff-none/x", 0600));
    say("fifo: s254 made %ld, again %ld, a missing parent %ld\n", x1, x2, x3);
    rd = open("/t/q/ff", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
    struct stat s;
    fstat(rd, &s);
    say("fifo: s254 the read end at once %s, a FIFO %s, a read %ld\n", rd >= 0 ? "yes" : "no", yes(S_ISFIFO(s.st_mode)), r(read(rd, b, 16)));
    wr = open("/t/q/ff", O_WRONLY | O_CLOEXEC);
    x1 = r(write(wr, "x", 1));
    x2 = r(read(rd, b, 16));
    say("fifo: s254 a writer %s, wrote %ld, read back %ld\n", wr >= 0 ? "opened" : "refused", x1, x2);
    close(wr);
    close(rd);
    say("fifo: s254 removed %ld\n", r(unlink("/t/q/ff")));
    munmap(flag, 4096);
}

/* --- flock ---------------------------------------------------------------- */

static void flock_rows(void) {
    long x1, x2, x3, x4, x5;
    int fd = open("/t/q/lk", O_WRONLY | O_CREAT | O_TRUNC, 0644);
    say("flock: the file: %ld\n", r(write(fd, "journal\n", 8)));
    close(fd);
    int a = open("/t/q/lk", O_RDWR), b = open("/t/q/lk", O_RDWR), c = open("/t/q/lk", O_RDWR);
    /* s254's [os.fs.lock] rows, as their system calls */
    say("flock: a exclusive %ld\n", r(flock(a, LOCK_EX | LOCK_NB)));
    x1 = r(flock(b, LOCK_EX | LOCK_NB));
    x2 = r(flock(b, LOCK_SH | LOCK_NB));
    say("flock: b exclusive %ld, shared %ld\n", x1, x2);
    x1 = r(flock(a, LOCK_UN));
    x2 = r(flock(b, LOCK_SH | LOCK_NB));
    x3 = r(flock(a, LOCK_SH | LOCK_NB));
    x4 = r(flock(c, LOCK_EX | LOCK_NB));
    say("flock: a unlocked %ld; b shared %ld; a shared %ld; c exclusive %ld\n", x1, x2, x3, x4);
    x1 = r(flock(a, LOCK_UN));
    x2 = r(flock(b, LOCK_UN));
    x3 = r(flock(c, LOCK_EX | LOCK_NB));
    say("flock: a and b unlocked %ld %ld; c exclusive %ld\n", x1, x2, x3);
    close(c);
    x1 = r(flock(a, LOCK_EX | LOCK_NB));
    x2 = r(flock(a, LOCK_UN));
    x3 = r(flock(a, LOCK_UN));
    say("flock: c closed; a exclusive %ld; unlocked %ld, and again %ld\n", x1, x2, x3);
    x1 = r(flock(a, 0));
    x2 = r(flock(a, LOCK_SH | LOCK_EX));
    x3 = r(flock(a, LOCK_NB));
    x4 = r(flock(a, 64));
    say("flock: an operation of 0 %ld, LOCK_SH|LOCK_EX %ld, LOCK_NB alone %ld, 64 %ld\n", x1, x2, x3, x4);
    x1 = r(flock(c, LOCK_SH));
    x2 = r(flock(1000000, LOCK_EX));
    say("flock: a closed descriptor %ld, descriptor 1000000 %ld\n", x1, x2);
    say("flock: LOCK_UN|LOCK_NB %ld\n", r(flock(a, LOCK_UN | LOCK_NB)));

    /* dup and fork share the open file's lock */
    int d = dup(a);
    x1 = r(flock(a, LOCK_EX | LOCK_NB));
    close(a);
    x2 = r(flock(b, LOCK_EX | LOCK_NB));
    say("flock: a exclusive %ld; a closed, its dup open: b exclusive %ld\n", x1, x2);
    close(d);
    x1 = r(flock(b, LOCK_EX | LOCK_NB));
    x2 = r(flock(b, LOCK_UN));
    say("flock: the dup closed too: b exclusive %ld; unlocked %ld\n", x1, x2);
    a = open("/t/q/lk", O_RDWR);
    flock(a, LOCK_EX | LOCK_NB);
    pid_t k = fork();
    if (k == 0) {
        long u = r(flock(a, LOCK_UN));
        _exit(u == 0 ? 0 : 3);
    }
    int status = 0;
    waitpid(k, &status, 0);
    x1 = r(flock(b, LOCK_EX | LOCK_NB));
    x2 = r(flock(b, LOCK_UN));
    say("flock: the child unlocked the inherited descriptor (status %d): b exclusive %ld; unlocked %ld\n", status, x1, x2);
    flock(a, LOCK_EX | LOCK_NB);
    k = fork();
    if (k == 0) {
        int own = open("/t/q/lk", O_RDWR);
        long x = r(flock(own, LOCK_EX | LOCK_NB));
        _exit(x == -EWOULDBLOCK ? 0 : 3);
    }
    waitpid(k, &status, 0);
    say("flock: a child's own open refused while the parent holds it: status %d\n", status);

    /* a lock that waits */
    int pp[2];
    if (pipe(pp) != 0) say("flock: pipe failed\n");
    k = fork();
    if (k == 0) {
        close(pp[0]);
        int own = open("/t/q/lk", O_RDWR);
        long x = r(flock(own, LOCK_EX));
        char t = x == 0 ? 'L' : 'E';
        if (write(pp[1], &t, 1) != 1) _exit(4);
        ms(100);
        _exit(0);
    }
    close(pp[1]);
    ms(300);
    char t = '-';
    fcntl(pp[0], F_SETFL, O_NONBLOCK);
    long early = read(pp[0], &t, 1);
    int nothing = early == -1 && errno == EAGAIN;
    x1 = r(flock(a, LOCK_UN));
    say("flock: a child waiting for the lock: nothing yet %s; unlocked %ld\n", yes(nothing), x1);
    fcntl(pp[0], F_SETFL, 0);
    long got = read(pp[0], &t, 1);
    waitpid(k, &status, 0);
    say("flock: then the child had it: %ld %c, status %d; a exclusive once it ended %ld\n", got, t, status, r(flock(a, LOCK_EX | LOCK_NB)));
    close(pp[0]);

    /* a signal ends a waiting lock */
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = on_usr1;
    sigaction(SIGUSR1, &sa, NULL);
    usr1 = 0;
    pid_t me = getpid();
    k = fork();
    if (k == 0) {
        ms(200);
        kill(me, SIGUSR1);
        _exit(0);
    }
    x1 = r(flock(b, LOCK_EX));
    say("flock: b waiting for a's lock, a handled SIGUSR1: %ld (handled %d)\n", x1, usr1);
    waitpid(k, &status, 0);
    flock(a, LOCK_UN);

    /* a conversion LOCK_NB refuses */
    c = open("/t/q/lk", O_RDWR);
    x1 = r(flock(a, LOCK_SH | LOCK_NB));
    x2 = r(flock(b, LOCK_SH | LOCK_NB));
    x3 = r(flock(a, LOCK_EX | LOCK_NB));
    x4 = r(flock(b, LOCK_UN));
    x5 = r(flock(c, LOCK_EX | LOCK_NB));
    say("flock: a and b shared %ld %ld; a to exclusive with LOCK_NB %ld; b unlocked %ld; c exclusive %ld\n", x1, x2, x3, x4, x5);
    flock(c, LOCK_UN);
    x1 = r(flock(a, LOCK_SH | LOCK_NB));
    x2 = r(flock(a, LOCK_EX | LOCK_NB));
    x3 = r(flock(a, LOCK_SH | LOCK_NB));
    x4 = r(flock(b, LOCK_SH | LOCK_NB));
    say("flock: a shared %ld, to exclusive %ld, back to shared %ld; b shared %ld\n", x1, x2, x3, x4);
    close(a);
    close(b);
    close(c);

    /* other kinds of descriptor */
    mkfifo("/t/q/lf", 0600);
    int f1 = open("/t/q/lf", O_RDWR), f2 = open("/t/q/lf", O_RDWR);
    int dd = open("/t/q", O_RDONLY | O_DIRECTORY), dd2 = open("/t/q", O_RDONLY | O_DIRECTORY);
    int p2[2];
    if (pipe(p2) != 0) p2[0] = p2[1] = -1;
    x1 = r(flock(f1, LOCK_EX | LOCK_NB));
    x2 = r(flock(f2, LOCK_EX | LOCK_NB));
    x3 = r(flock(dd, LOCK_EX | LOCK_NB));
    x4 = r(flock(dd2, LOCK_EX | LOCK_NB));
    x5 = r(flock(p2[0], LOCK_EX | LOCK_NB));
    long x6 = r(flock(p2[1], LOCK_EX | LOCK_NB));
    say("flock: a FIFO %ld, its second open %ld; a directory %ld, its second open %ld; a pipe's ends %ld %ld\n", x1, x2, x3, x4, x5, x6);
    close(f1);
    close(f2);
    close(dd);
    close(dd2);
    close(p2[0]);
    close(p2[1]);
    x1 = r(unlink("/t/q/lf"));
    x2 = r(unlink("/t/q/lk"));
    say("flock: removed %ld %ld\n", x1, x2);
}

int main(void) {
    umask(022);
    say("fifos: /t/q made: %ld\n", r(mkdir("/t/q", 0755)));
    fifo_rows();
    flock_rows();
    say("fifos: /t/q removed: %ld\n", r(rmdir("/t/q")));
    say("fifos: done\n");
    return 0;
}
