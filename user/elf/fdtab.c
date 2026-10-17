/* px50: the descriptor table as /proc shows it (pax#78) — readlink of
 * each /proc/self/fd entry (a file, a directory, a device, the terminal,
 * a pipe's ends, a socketpair's end, a UDP, a TCP and an AF_UNIX path
 * socket, an eventfd, an epoll object, a file renamed, moved and
 * unlinked while open), lstat of the entries and stat and statx through
 * them, opening through them, the two directories' listings, the
 * fdinfo files' lines, who may read another process's (ptrace(2)'s
 * read mode: root, a user's own, another user's, root's, a
 * non-dumpable one's, a zombie's); and (pax#80) rmdir and rename of
 * /proc and /sys. Run as the first program on a terminal (PAX's
 * console; a Linux pseudo-terminal as its session leader, notes/px50's
 * guest and tools/linux-tree), as root and as a user (through `as`),
 * with /g a 1777 directory and /g/r644 root's 0644 file in the archive.
 *
 * Every line is `case: answer`. Nothing that differs between two
 * correct kernels is printed by value: an inode number is printed as
 * whether it is the one fstat answers, a mount id as which file's it
 * is the same as, the terminal's name as whether it is a path in /dev
 * that stat finds to be the descriptor's. No pid, time or address.
 *
 *   fdtab           every section, L S O D I P X
 *
 * Written from the man pages (proc(5), proc_pid_fd(5),
 * proc_pid_fdinfo(5), readlink(2), open(2), stat(2), statx(2),
 * getdents64(2), ptrace(2), prctl(2), pipe(7), socket(7), unix(7),
 * eventfd(2), epoll_create(2), rmdir(2), rename(2)) and the uapi
 * headers' numbers. No C library's or kernel's source was read.
 * Written for this lane. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/eventfd.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static int root;

static const char *ename(int e) {
    switch (e) {
    case 0: return "0";
    case EPERM: return "EPERM"; case ENOENT: return "ENOENT"; case ESRCH: return "ESRCH"; case EINTR: return "EINTR";
    case EIO: return "EIO"; case ENXIO: return "ENXIO"; case EBADF: return "EBADF"; case EAGAIN: return "EAGAIN";
    case EACCES: return "EACCES"; case EEXIST: return "EEXIST"; case EXDEV: return "EXDEV"; case EISDIR: return "EISDIR";
    case EINVAL: return "EINVAL"; case ENOTTY: return "ENOTTY"; case ESPIPE: return "ESPIPE"; case ENOTEMPTY: return "ENOTEMPTY";
    case EOPNOTSUPP: return "EOPNOTSUPP"; case ENODEV: return "ENODEV"; case EBUSY: return "EBUSY"; case EROFS: return "EROFS";
    case ENOSYS: return "ENOSYS"; case ENOTDIR: return "ENOTDIR"; case EFAULT: return "EFAULT"; case ELOOP: return "ELOOP";
    case ENAMETOOLONG: return "ENAMETOOLONG";
    default: { static char b[32]; snprintf(b, sizeof b, "errno%d", e); return b; }
    }
}

/* One line, written whole (children write too: no stdio buffer). */
static void out(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void out(const char *fmt, ...) {
    char b[1024];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b - 1, fmt, ap);
    va_end(ap);
    if (n < 0) return;
    if (n > (int)sizeof b - 2) n = (int)sizeof b - 2;
    b[n++] = '\n';
    (void)!write(1, b, (size_t)n);
}

static void nap(int ms) {
    struct timespec ts = {ms / 1000, (long)(ms % 1000) * 1000000L};
    while (nanosleep(&ts, &ts) < 0 && errno == EINTR) {}
}

static const char *yesno(int c) { return c ? "yes" : "no"; }

/* An answer: 0, or the errno's name. */
static const char *rv(long r, int e) { return r < 0 ? ename(e) : "0"; }

static char *ent(int fd) {
    static char p[4][64];
    static int k;
    k = (k + 1) & 3;
    snprintf(p[k], sizeof p[k], "/proc/self/fd/%d", fd);
    return p[k];
}

static char *info(int fd) {
    static char p[2][64];
    static int k;
    k = (k + 1) & 1;
    snprintf(p[k], sizeof p[k], "/proc/self/fdinfo/%d", fd);
    return p[k];
}

/* readlink of `path`, its numbers said by rule: `pipe:[N]` and
 * `socket:[N]` as `pipe:[fstat's]` when N is descriptor `fd`'s st_ino. */
static const char *lnk(const char *path, int fd) {
    static char o[2][320];
    static int k;
    k = (k + 1) & 1;
    char b[256];
    errno = 0;
    ssize_t n = readlink(path, b, sizeof b - 1);
    if (n < 0) { snprintf(o[k], sizeof o[k], "%s", ename(errno)); return o[k]; }
    b[n] = 0;
    struct stat s;
    unsigned long v;
    char kind[32];
    if (sscanf(b, "%31[a-z]:[%lu]", kind, &v) == 2 && strchr(b, ']') && strchr(b, ']')[1] == 0) {
        int same = fd >= 0 && fstat(fd, &s) == 0 && (unsigned long)s.st_ino == v;
        snprintf(o[k], sizeof o[k], "\"%s:[%s]\"", kind, same ? "fstat's st_ino" : "another number");
        return o[k];
    }
    snprintf(o[k], sizeof o[k], "\"%s\"", b);
    return o[k];
}

static const char *perm(mode_t m) {
    static char b[2][16];
    static int k;
    k = (k + 1) & 1;
    const char *t = S_ISLNK(m) ? "link" : S_ISDIR(m) ? "dir" : S_ISREG(m) ? "file" : S_ISFIFO(m) ? "fifo" : S_ISSOCK(m) ? "sock" : S_ISCHR(m) ? "chr" : (m & S_IFMT) == 0 ? "untyped" : "other";
    snprintf(b[k], sizeof b[k], "%s %04o", t, (unsigned)(m & 07777));
    return b[k];
}

/* stat and statx of `path` (following) against fstat of `fd`. */
static const char *through(const char *path, int fd) {
    static char b[200];
    struct stat a, f;
    struct statx x;
    errno = 0;
    if (stat(path, &a) < 0) { snprintf(b, sizeof b, "stat %s", ename(errno)); return b; }
    if (fstat(fd, &f) < 0) { snprintf(b, sizeof b, "fstat %s", ename(errno)); return b; }
    int sx = statx(AT_FDCWD, path, 0, STATX_BASIC_STATS, &x);
    int same = a.st_dev == f.st_dev && a.st_ino == f.st_ino && a.st_mode == f.st_mode && a.st_rdev == f.st_rdev && a.st_size == f.st_size && a.st_uid == f.st_uid && a.st_gid == f.st_gid && a.st_nlink == f.st_nlink;
    int xsame = sx == 0 && x.stx_ino == f.st_ino && x.stx_mode == f.st_mode && makedev(x.stx_dev_major, x.stx_dev_minor) == f.st_dev;
    snprintf(b, sizeof b, "stat %s, fstat's: %s; statx fstat's: %s", perm(a.st_mode), yesno(same), yesno(xsame));
    return b;
}

static const char *lst(const char *path) {
    static char b[2][120];
    static int k;
    k = (k + 1) & 1;
    struct stat s;
    errno = 0;
    if (lstat(path, &s) < 0) { snprintf(b[k], sizeof b[k], "lstat %s", ename(errno)); return b[k]; }
    snprintf(b[k], sizeof b[k], "lstat %s size %lld nlink %lu owner %u:%u", perm(s.st_mode), (long long)s.st_size, (unsigned long)s.st_nlink, (unsigned)s.st_uid, (unsigned)s.st_gid);
    return b[k];
}

static void put(const char *path, const char *text) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) { out("! put %s: %s", path, ename(errno)); return; }
    (void)!write(fd, text, strlen(text));
    close(fd);
}

/* ---- L and S: what an entry names ------------------------------------- */

static void row(const char *what, int fd) {
    out("L: %s: %s", what, lnk(ent(fd), fd));
    out("S: %s: %s; %s", what, lst(ent(fd)), through(ent(fd), fd));
}

static void link_rows(void) {
    put("/g/f1", "abcdef\n");
    put("/g/f2", "second\n");
    int f1 = open("/g/f1", O_RDONLY);
    row("a file opened O_RDONLY", f1);
    if (chdir("/g") != 0) out("! chdir /g: %s", ename(errno));
    int f2 = open("f2", O_WRONLY);
    row("a file opened O_WRONLY by a relative name", f2);
    int f3 = open("/g/f2", O_RDWR);
    row("a file opened O_RDWR", f3);
    if (chdir("/") != 0) out("! chdir /: %s", ename(errno));
    int d = open("/g", O_RDONLY | O_DIRECTORY);
    row("the directory /g", d);
    int r = open("/", O_RDONLY | O_DIRECTORY);
    row("the directory /", r);
    int n = open("/dev/null", O_RDWR);
    row("/dev/null", n);
    int z = open("/dev/zero", O_RDONLY);
    row("/dev/zero", z);
    int t = open("/dev/tty", O_RDWR);
    row("/dev/tty", t);
    /* The terminal the program was given: its name is the host's. */
    char b[256];
    ssize_t k = readlink(ent(0), b, sizeof b - 1);
    if (k > 0) b[k] = 0;
    struct stat a, f;
    int via = k > 0 && stat(b, &a) == 0 && fstat(0, &f) == 0 && a.st_rdev == f.st_rdev && S_ISCHR(a.st_mode);
    out("L: descriptor 0: a path in /dev: %s; stat of that path is the descriptor's terminal: %s", yesno(k > 5 && strncmp(b, "/dev/", 5) == 0), yesno(via));
    out("S: descriptor 0: %s; %s", lst(ent(0)), through(ent(0), 0));
    int p[2];
    (void)!pipe(p);
    row("a pipe's read end", p[0]);
    row("a pipe's write end", p[1]);
    struct stat s0, s1;
    fstat(p[0], &s0); fstat(p[1], &s1);
    out("L: the pipe's two ends: one inode: %s", yesno(s0.st_ino == s1.st_ino));
    int sv[2];
    (void)!socketpair(AF_UNIX, SOCK_STREAM, 0, sv);
    row("a socketpair's end", sv[0]);
    fstat(sv[0], &s0); fstat(sv[1], &s1);
    out("L: the socketpair's two ends: one inode: %s", yesno(s0.st_ino == s1.st_ino));
    int u = socket(AF_INET, SOCK_DGRAM, 0);
    row("a UDP socket", u);
    int tc = socket(AF_INET, SOCK_STREAM, 0);
    row("a TCP socket", tc);
    int us = socket(AF_UNIX, SOCK_STREAM, 0);
    struct sockaddr_un ua;
    memset(&ua, 0, sizeof ua);
    ua.sun_family = AF_UNIX;
    strcpy(ua.sun_path, root ? "/g/sock-r" : "/g/sock-u");
    unlink(ua.sun_path);
    errno = 0;
    long bd = bind(us, (struct sockaddr *)&ua, sizeof ua);
    out("L: an AF_UNIX socket bound to a name: bind %s", rv(bd, errno));
    row("an AF_UNIX path socket", us);
    int e = eventfd(0, 0);
    row("an eventfd", e);
    int ep = epoll_create1(0);
    row("an epoll object", ep);
    int pf = open("/proc/self/status", O_RDONLY);
    char want[64];
    snprintf(want, sizeof want, "/proc/%d/status", (int)getpid());
    k = readlink(ent(pf), b, sizeof b - 1);
    if (k > 0) b[k] = 0;
    out("L: /proc/self/status opened: %s", k < 0 ? ename(errno) : strcmp(b, want) == 0 ? "\"/proc/<its pid>/status\"" : b);
    int pd = open("/proc/self/fd", O_RDONLY | O_DIRECTORY);
    snprintf(want, sizeof want, "/proc/%d/fd", (int)getpid());
    k = readlink(ent(pd), b, sizeof b - 1);
    if (k > 0) b[k] = 0;
    out("L: /proc/self/fd opened: %s", k < 0 ? ename(errno) : strcmp(b, want) == 0 ? "\"/proc/<its pid>/fd\"" : b);
    close(pf); close(pd);

    /* A file renamed, moved and unlinked while it is open. */
    put("/g/f3", "three\n");
    mkdir("/g/sub", 0755);
    int f4 = open("/g/f3", O_RDONLY);
    rename("/g/f3", "/g/f3b");
    out("L: a file renamed in its directory while open: %s", lnk(ent(f4), f4));
    rename("/g/f3b", "/g/sub/f3c");
    out("L: then moved to another directory: %s", lnk(ent(f4), f4));
    put("/g/f5", "five\n");
    int f5 = open("/g/f5", O_RDONLY);
    unlink("/g/f5");
    out("L: a file unlinked while open: %s", lnk(ent(f5), f5));
    out("S: a file unlinked while open: %s; %s", lst(ent(f5)), through(ent(f5), f5));
    mkdir("/g/gone", 0755);
    int gd = open("/g/gone", O_RDONLY | O_DIRECTORY);
    rmdir("/g/gone");
    out("L: a directory removed while open: %s", lnk(ent(gd), gd));
    int dp = dup(f1);
    out("L: a dup of the O_RDONLY file: %s", lnk(ent(dp), dp));
    errno = 0;
    k = readlink(ent(f1), b, 3);
    out("L: readlink with room for 3 bytes: %ld \"%.*s\"", (long)k, k > 0 ? (int)k : 0, b);
    errno = 0;
    k = syscall(SYS_readlinkat, AT_FDCWD, ent(f1), b, 0);
    out("L: readlink with room for 0 bytes: %s", rv(k, errno));
    errno = 0;
    k = readlink("/proc/self/fd", b, sizeof b);
    out("L: readlink of /proc/self/fd itself: %s", rv(k, errno));
    out("L: a closed descriptor's entry (900): %s", lnk("/proc/self/fd/900", -1));
    char p01[64];
    snprintf(p01, sizeof p01, "/proc/self/fd/0%d", f1);
    out("L: the entry with a leading zero: %s", lnk(p01, f1));
    out("L: /proc/self/fd/x: %s", lnk("/proc/self/fd/x", -1));
    out("L: an entry with a trailing slash (a file): %s", lnk("/proc/self/fd/0/", -1));
    char pid[64];
    snprintf(pid, sizeof pid, "/proc/%d/fd/%d", (int)getpid(), f1);
    out("L: /proc/<its pid>/fd/N: %s", lnk(pid, f1));
    out("S: /proc/self/fd: %s", lst("/proc/self/fd"));
    out("S: /proc/self/fdinfo: %s", lst("/proc/self/fdinfo"));
    out("S: an fdinfo entry: %s", lst(info(f1)));
    close(f1); close(f2); close(f3); close(d); close(r); close(n); close(z); close(t);
    close(p[0]); close(p[1]); close(sv[0]); close(sv[1]); close(u); close(tc); close(us); close(e); close(ep);
    close(f4); close(f5); close(gd); close(dp);
    unlink(ua.sun_path);
    unlink("/g/sub/f3c");
    rmdir("/g/sub");
}

/* ---- O: opening through an entry --------------------------------------- */

static void open_rows(void) {
    put("/g/o1", root ? "rootfile\n" : "userfile\n");
    int f = open("/g/o1", O_RDONLY);
    char c[16] = {0};
    errno = 0;
    int g = open(ent(f), O_RDONLY);
    int eg = errno;
    ssize_t k = g < 0 ? -1 : read(g, c, 4);
    out("O: a file's entry, O_RDONLY: %s; read 4: \"%.*s\"; the first descriptor's offset then: %ld", rv(g, eg), k > 0 ? (int)k : 0, c, (long)lseek(f, 0, SEEK_CUR));
    errno = 0;
    int w = open(ent(f), O_RDWR);
    out("O: the O_RDONLY descriptor's entry opened O_RDWR (its own file, 0644): %s", rv(w, errno));
    if (w >= 0) {
        (void)!write(w, "X", 1);
        char d[16] = {0};
        (void)!pread(f, d, 3, 0);
        out("O: written through it, read by the first: \"%s\"", d);
        close(w);
    }
    int r = open("/g/r644", O_RDONLY);
    errno = 0;
    w = open(ent(r), O_WRONLY);
    out("O: root's 0644 file's O_RDONLY entry opened O_WRONLY: %s", rv(w, errno));
    if (w >= 0) close(w);
    close(r);
    errno = 0;
    w = open(ent(f), O_RDONLY | O_NOFOLLOW);
    out("O: O_NOFOLLOW: %s", rv(w, errno));
    if (w >= 0) close(w);
    errno = 0;
    w = open(ent(f), O_RDONLY | O_DIRECTORY);
    out("O: O_DIRECTORY on a file's entry: %s", rv(w, errno));
    if (w >= 0) close(w);
    errno = 0;
    w = open(ent(f), O_WRONLY | O_CREAT, 0600);
    out("O: O_CREAT on a file's entry: %s", rv(w, errno));
    if (w >= 0) close(w);
    errno = 0;
    w = open(ent(f), O_WRONLY | O_CREAT | O_EXCL, 0600);
    out("O: O_CREAT|O_EXCL on a file's entry: %s", rv(w, errno));
    if (w >= 0) close(w);
    errno = 0;
    w = open(ent(f), O_WRONLY | O_TRUNC);
    struct stat s;
    fstat(f, &s);
    out("O: O_TRUNC through the entry: %s; the size then %lld", rv(w, errno), (long long)s.st_size);
    if (w >= 0) close(w);
    char p[96];
    snprintf(p, sizeof p, "%s/", ent(f));
    errno = 0;
    w = open(p, O_RDONLY);
    out("O: a file's entry with a trailing slash: %s", rv(w, errno));
    if (w >= 0) close(w);
    int d = open("/g", O_RDONLY | O_DIRECTORY);
    snprintf(p, sizeof p, "%s/o1", ent(d));
    errno = 0;
    w = open(p, O_RDONLY);
    struct stat a, b;
    int same = w >= 0 && fstat(w, &a) == 0 && stat("/g/o1", &b) == 0 && a.st_ino == b.st_ino && a.st_dev == b.st_dev;
    out("O: the directory's entry, then o1: %s, /g/o1: %s", rv(w, errno), yesno(same));
    if (w >= 0) close(w);
    snprintf(p, sizeof p, "%s/..", ent(d));
    same = stat(p, &a) == 0 && stat("/", &b) == 0 && a.st_ino == b.st_ino && a.st_dev == b.st_dev;
    out("O: the directory's entry, then ..: /: %s", yesno(same));
    errno = 0;
    w = open(ent(d), O_RDONLY | O_DIRECTORY);
    out("O: the directory's entry, O_DIRECTORY: %s", rv(w, errno));
    if (w >= 0) close(w);
    errno = 0;
    w = open(ent(d), O_WRONLY);
    out("O: the directory's entry, O_WRONLY: %s", rv(w, errno));
    if (w >= 0) close(w);
    errno = 0;
    w = chdir(ent(d));
    char cwd[128] = "";
    if (w == 0 && !getcwd(cwd, sizeof cwd)) snprintf(cwd, sizeof cwd, "getcwd %s", ename(errno));
    out("O: chdir to the directory's entry: %s, getcwd \"%s\"", rv(w, errno), cwd);
    if (chdir("/") != 0) out("! chdir /");
    close(d);

    int pp[2];
    (void)!pipe(pp);
    errno = 0;
    int pr = open(ent(pp[1]), O_RDONLY);
    out("O: a pipe's write end's entry opened O_RDONLY: %s", rv(pr, errno));
    (void)!write(pp[1], "pq", 2);
    char q[8] = {0};
    if (pr >= 0) { fcntl(pr, F_SETFL, O_NONBLOCK); k = read(pr, q, 2); out("O: read through it after a write: %ld \"%s\"", (long)k, q); close(pr); }
    errno = 0;
    int pw = open(ent(pp[0]), O_WRONLY);
    out("O: a pipe's read end's entry opened O_WRONLY: %s", rv(pw, errno));
    if (pw >= 0) {
        (void)!write(pw, "z", 1);
        memset(q, 0, sizeof q);
        fcntl(pp[0], F_SETFL, O_NONBLOCK);
        k = read(pp[0], q, 4);
        out("O: written through it, read from the read end: %ld \"%s\"", (long)k, q);
        close(pw);
    }
    close(pp[0]); close(pp[1]);
    int sv[2];
    (void)!socketpair(AF_UNIX, SOCK_STREAM, 0, sv);
    errno = 0;
    w = open(ent(sv[0]), O_RDWR);
    out("O: a socketpair's entry: %s", rv(w, errno));
    if (w >= 0) close(w);
    close(sv[0]); close(sv[1]);
    int u = socket(AF_INET, SOCK_DGRAM, 0);
    errno = 0;
    w = open(ent(u), O_RDWR);
    out("O: a UDP socket's entry: %s", rv(w, errno));
    if (w >= 0) close(w);
    close(u);
    int e = eventfd(0, 0);
    errno = 0;
    w = open(ent(e), O_RDWR);
    out("O: an eventfd's entry: %s", rv(w, errno));
    if (w >= 0) close(w);
    close(e);
    int ep = epoll_create1(0);
    errno = 0;
    w = open(ent(ep), O_RDWR);
    out("O: an epoll object's entry: %s", rv(w, errno));
    if (w >= 0) close(w);
    close(ep);
    int n = open("/dev/null", O_WRONLY);
    errno = 0;
    w = open(ent(n), O_RDONLY);
    k = w < 0 ? -2 : read(w, q, 4);
    out("O: /dev/null's entry, O_RDONLY: %s, read %ld", rv(w, errno), (long)k);
    if (w >= 0) close(w);
    close(n);
    errno = 0;
    w = open(ent(0), O_RDWR | O_NOCTTY);
    out("O: descriptor 0's entry (the terminal), O_RDWR: %s; a terminal: %s", rv(w, errno), yesno(w >= 0 && isatty(w)));
    if (w >= 0) close(w);
    put("/g/o2", "unlinked\n");
    int un = open("/g/o2", O_RDONLY);
    unlink("/g/o2");
    errno = 0;
    w = open(ent(un), O_RDONLY);
    memset(c, 0, sizeof c);
    k = w < 0 ? -2 : read(w, c, 8);
    out("O: an unlinked file's entry: %s, read %ld \"%s\"", rv(w, errno), (long)k, c);
    if (w >= 0) close(w);
    close(un);
    errno = 0;
    w = open("/proc/self/fd/900", O_RDONLY);
    out("O: a closed descriptor's entry: %s", rv(w, errno));
    close(f);
    unlink("/g/o1");
}

/* ---- D: the listings ---------------------------------------------------- */

static void names(const char *what, const char *path) {
    char b[400] = "";
    size_t l = 0;
    errno = 0;
    DIR *d = opendir(path);
    if (!d) { out("D: %s: %s", what, ename(errno)); return; }
    struct dirent *e;
    while ((e = readdir(d))) {
        const char *t = e->d_type == DT_LNK ? "l" : e->d_type == DT_REG ? "r" : e->d_type == DT_DIR ? "d" : e->d_type == DT_UNKNOWN ? "?" : "o";
        l += (size_t)snprintf(b + l, sizeof b > l ? sizeof b - l : 0, "%s%s(%s)", l ? " " : "", e->d_name, t);
    }
    closedir(d);
    out("D: %s: %s", what, b);
}

static int has_name(const char *dir, const char *name) {
    DIR *d = opendir(dir);
    if (!d) return 0;
    struct dirent *e;
    int y = 0;
    while ((e = readdir(d))) if (strcmp(e->d_name, name) == 0) y = 1;
    closedir(d);
    return y;
}

static void list_rows(void) {
    pid_t c = fork();
    if (c == 0) {
        for (int i = 3; i < 1024; i++) close(i);
        int a = open("/dev/null", O_RDONLY);
        int b = open("/dev/null", O_RDONLY);
        (void)!dup2(a, 9);
        close(b);
        (void)a;
        names("/proc/self/fd, with 0 1 2 3 9 open", "/proc/self/fd");
        names("/proc/self/fdinfo, the same", "/proc/self/fdinfo");
        char p[64];
        snprintf(p, sizeof p, "/proc/%d/fd", (int)getpid());
        names("/proc/<its pid>/fd", p);
        out("D: /proc/self lists fd: %s, fdinfo: %s", yesno(has_name("/proc/self", "fd")), yesno(has_name("/proc/self", "fdinfo")));
        snprintf(p, sizeof p, "/proc/%d", (int)getpid());
        out("D: /proc/<its pid> lists fd: %s, fdinfo: %s", yesno(has_name(p, "fd")), yesno(has_name(p, "fdinfo")));
        _exit(0);
    }
    waitpid(c, 0, 0);
}

/* ---- I: the fdinfo files ------------------------------------------------- */

static unsigned long mnt_tree, mnt_proc;

static long field(const char *text, const char *key) {
    size_t kl = strlen(key);
    for (const char *s = text; s && *s; s = strchr(s, '\n') ? strchr(s, '\n') + 1 : 0)
        if (strncmp(s, key, kl) == 0 && s[kl] == ':') return strtol(s + kl + 1, 0, 10);
    return -1;
}

static int rdinfo(int fd, char *b, size_t n) {
    int i = open(info(fd), O_RDONLY);
    if (i < 0) return -errno;
    ssize_t k = read(i, b, n - 1);
    int e = errno;
    close(i);
    if (k < 0) return -e;
    b[k] = 0;
    return (int)k;
}

/* An fdinfo text as one line: tabs as \t, lines joined by |, the mount
 * id and the inode by rule, any other line's digits as N but for the
 * keys whose values are the descriptor's own (pos, flags, eventfd-count,
 * eventfd-semaphore, scm_fds). */
static const char *shown(int fd) {
    static char o[600];
    char b[1024];
    int r = rdinfo(fd, b, sizeof b);
    if (r < 0) { snprintf(o, sizeof o, "%s", ename(-r)); return o; }
    struct stat s;
    fstat(fd, &s);
    size_t l = 0;
    for (char *line = strtok(b, "\n"); line; line = strtok(NULL, "\n")) {
        char key[64] = "";
        sscanf(line, "%63[^:]", key);
        char *v = strchr(line, ':');
        char val[256] = "";
        if (v) {
            v++;
            char ws[96] = "";
            size_t wn = strspn(v, " \t");
            for (size_t i = 0; i < wn && i < 40; i++) strcat(ws, v[i] == '\t' ? "\\t" : " ");
            char *num = v + wn;
            if (strcmp(key, "mnt_id") == 0) {
                unsigned long m = strtoul(num, 0, 10);
                snprintf(val, sizeof val, "%s%s", ws, m == mnt_tree ? "<the tree's>" : m == mnt_proc ? "<proc's>" : "<another>");
            } else if (strcmp(key, "ino") == 0) {
                snprintf(val, sizeof val, "%s%s", ws, strtoul(num, 0, 10) == (unsigned long)s.st_ino ? "<fstat's>" : "<another>");
            } else if (strcmp(key, "pos") == 0 || strcmp(key, "flags") == 0 || strcmp(key, "eventfd-count") == 0 || strcmp(key, "eventfd-semaphore") == 0 || strcmp(key, "scm_fds") == 0) {
                snprintf(val, sizeof val, "%s%s", ws, num);
            } else {
                size_t j = 0;
                for (const char *q = v; *q && j < sizeof val - 2; q++) {
                    if (*q >= '0' && *q <= '9') { if (j == 0 || val[j - 1] != 'N') val[j++] = 'N'; }
                    else if (*q == '\t') { val[j++] = '\\'; val[j++] = 't'; }
                    else val[j++] = *q;
                }
                val[j] = 0;
            }
        }
        l += (size_t)snprintf(o + l, sizeof o > l ? sizeof o - l : 0, "%s%s:%s", l ? "|" : "", key, val);
    }
    return o;
}

static void info_rows(void) {
    char b[1024];
    put("/g/i1", "0123456789\n");
    int ref = open("/g/i1", O_RDONLY);
    int pr = open("/proc/self/status", O_RDONLY);
    mnt_tree = rdinfo(ref, b, sizeof b) > 0 ? (unsigned long)field(b, "mnt_id") : 0;
    mnt_proc = rdinfo(pr, b, sizeof b) > 0 ? (unsigned long)field(b, "mnt_id") : 1;
    out("I: the tree's mount id and /proc's differ: %s", yesno(mnt_tree != mnt_proc));
    out("I: a file, O_RDONLY: %s", shown(ref));
    char c[8];
    (void)!read(ref, c, 3);
    out("I: after a read of 3: %s", shown(ref));
    lseek(ref, 7, SEEK_SET);
    int dp = dup(ref);
    out("I: a dup after lseek to 7: %s", shown(dp));
    close(dp);
    int a = open("/g/i1", O_WRONLY | O_APPEND | O_CREAT | O_TRUNC, 0644);
    out("I: O_WRONLY|O_APPEND|O_CREAT|O_TRUNC (as >>, truncated): %s", shown(a));
    (void)!write(a, "hello", 5);
    out("I: after a write of 5: %s", shown(a));
    close(a);
    a = open("/g/i1", O_WRONLY | O_APPEND);
    out("I: O_WRONLY|O_APPEND (>>): %s", shown(a));
    close(a);
    a = open("/g/i1", O_RDWR | O_NONBLOCK | O_CLOEXEC);
    out("I: O_RDWR|O_NONBLOCK|O_CLOEXEC: %s", shown(a));
    fcntl(a, F_SETFD, 0);
    out("I: then F_SETFD 0: %s", shown(a));
    fcntl(a, F_SETFL, O_APPEND);
    out("I: then F_SETFL O_APPEND: %s", shown(a));
    close(a);
    a = open("/g/i1", O_RDONLY | O_NOFOLLOW | O_NOCTTY);
    out("I: O_RDONLY|O_NOFOLLOW|O_NOCTTY: %s", shown(a));
    close(a);
    a = open("/g", O_RDONLY | O_DIRECTORY);
    out("I: a directory, O_DIRECTORY: %s", shown(a));
    close(a);
    a = open("/g", O_RDONLY);
    out("I: a directory, O_RDONLY: %s", shown(a));
    close(a);
    a = open("/dev/null", O_RDWR);
    out("I: /dev/null, O_RDWR: %s", shown(a));
    close(a);
    a = open("/dev/tty", O_RDWR);
    out("I: /dev/tty, O_RDWR: %s", shown(a));
    close(a);
    out("I: /proc/self/status: %s", shown(pr));
    int p[2];
    (void)!pipe(p);
    out("I: a pipe's read end: %s", shown(p[0]));
    out("I: a pipe's write end: %s", shown(p[1]));
    close(p[0]); close(p[1]);
    (void)!pipe2(p, O_NONBLOCK | O_CLOEXEC);
    out("I: pipe2 O_NONBLOCK|O_CLOEXEC, its read end: %s", shown(p[0]));
    close(p[0]); close(p[1]);
    int sv[2];
    (void)!socketpair(AF_UNIX, SOCK_STREAM, 0, sv);
    out("I: a socketpair's end: %s", shown(sv[0]));
    close(sv[0]); close(sv[1]);
    int u = socket(AF_INET, SOCK_DGRAM, 0);
    out("I: a UDP socket: %s", shown(u));
    close(u);
    int e = eventfd(5, 0);
    out("I: an eventfd made with 5: %s", shown(e));
    uint64_t v = 7;
    (void)!write(e, &v, 8);
    out("I: then a write of 7: %s", shown(e));
    close(e);
    e = eventfd(0, EFD_NONBLOCK | EFD_SEMAPHORE);
    out("I: an eventfd EFD_NONBLOCK|EFD_SEMAPHORE: %s", shown(e));
    close(e);
    int ep = epoll_create1(0);
    out("I: an epoll object with nothing registered: %s", shown(ep));
    close(ep);
    out("I: a closed descriptor's: %s", shown(900));
    close(ref); close(pr);
    unlink("/g/i1");
}

/* ---- P: who may read another process's ---------------------------------- */

static int tell[2];
static int fds_of_target;

/* A process that holds /dev/null as descriptor 7 and waits. */
static pid_t target(uid_t u, int dumpable) {
    int ready[2];
    (void)!pipe(ready);
    pid_t p = fork();
    if (p == 0) {
        close(ready[0]);
        int n = open("/dev/null", O_RDONLY);
        (void)!dup2(n, 7);
        if (u != 0) {
            if (setgroups(0, 0) != 0 && root) _exit(91);
            if (setresgid(u, u, u) != 0 || setresuid(u, u, u) != 0) _exit(92);
        }
        /* A change of ids makes a process not dumpable (proc(5)): the
         * dumpable target says so again itself. */
        prctl(PR_SET_DUMPABLE, dumpable ? 1 : 0, 0, 0, 0);
        (void)!write(ready[1], "r", 1);
        close(ready[1]);
        for (;;) pause();
    }
    close(ready[1]);
    char c;
    (void)!read(ready[0], &c, 1);
    close(ready[0]);
    return p;
}

static void ask(const char *who, const char *of, pid_t t) {
    char d[64], e[64], i[64], fi[64];
    snprintf(d, sizeof d, "/proc/%d/fd", (int)t);
    snprintf(e, sizeof e, "/proc/%d/fd/7", (int)t);
    snprintf(i, sizeof i, "/proc/%d/fdinfo", (int)t);
    snprintf(fi, sizeof fi, "/proc/%d/fdinfo/7", (int)t);
    struct stat s;
    char ow[48];
    if (lstat(d, &s) == 0) snprintf(ow, sizeof ow, "%u:%u %04o", (unsigned)s.st_uid, (unsigned)s.st_gid, (unsigned)(s.st_mode & 07777));
    else snprintf(ow, sizeof ow, "%s", ename(errno));
    char io[48];
    if (lstat(i, &s) == 0) snprintf(io, sizeof io, "%u:%u %04o", (unsigned)s.st_uid, (unsigned)s.st_gid, (unsigned)(s.st_mode & 07777));
    else snprintf(io, sizeof io, "%s", ename(errno));
    errno = 0;
    int od = open(d, O_RDONLY | O_DIRECTORY);
    int eod = errno;
    if (od >= 0) close(od);
    char b[128];
    errno = 0;
    ssize_t k = readlink(e, b, sizeof b - 1);
    int ek = errno;
    if (k > 0) b[k] = 0;
    errno = 0;
    long st = stat(e, &s);
    int es = errno;
    errno = 0;
    long ls = lstat(e, &s);
    int el = errno;
    char lo[48];
    if (ls == 0) snprintf(lo, sizeof lo, " %u:%u %04o", (unsigned)s.st_uid, (unsigned)s.st_gid, (unsigned)(s.st_mode & 07777));
    else lo[0] = 0;
    char fo[48];
    if (lstat(fi, &s) == 0) snprintf(fo, sizeof fo, "%u:%u %04o", (unsigned)s.st_uid, (unsigned)s.st_gid, (unsigned)(s.st_mode & 07777));
    else snprintf(fo, sizeof fo, "%s", ename(errno));
    errno = 0;
    int oi = open(i, O_RDONLY | O_DIRECTORY);
    int eoi = errno;
    if (oi >= 0) close(oi);
    errno = 0;
    int of_ = open(fi, O_RDONLY);
    int eof_ = errno;
    if (of_ >= 0) close(of_);
    errno = 0;
    int oe = open(e, O_RDONLY);
    int eoe = errno;
    if (oe >= 0) close(oe);
    out("P: %s, of %s: fd/ %s, open %s; readlink fd/7 %s; stat %s, lstat %s%s, open %s; fdinfo/ %s, open %s; fdinfo/7 %s, open %s",
        who, of, ow, rv(od, eod), k < 0 ? ename(ek) : strcmp(b, "/dev/null") == 0 ? "\"/dev/null\"" : b, rv(st, es), rv(ls, el), lo, rv(oe, eoe), io, rv(oi, eoi), fo, rv(of_, eof_));
}

/* Run ask() as user u (from root: setresuid), against target t. */
static void ask_as(uid_t u, const char *who, const char *of, pid_t t) {
    pid_t p = fork();
    if (p == 0) {
        if (u != getuid()) {
            setgroups(0, 0);
            if (setresgid(u, u, u) != 0 || setresuid(u, u, u) != 0) { out("! ids"); _exit(1); }
        }
        ask(who, of, t);
        _exit(0);
    }
    waitpid(p, 0, 0);
}

static void perm_rows(void) {
    (void)tell; (void)fds_of_target;
    if (root) {
        pid_t r0 = target(0, 1), a = target(1001, 1), b = target(1002, 1), nd = target(1001, 0);
        ask_as(0, "root", "1001's", a);
        ask_as(0, "root", "1001's not dumpable", nd);
        ask_as(1001, "1001", "its own sibling's (1001)", a);
        ask_as(1001, "1001", "root's", r0);
        ask_as(1001, "1001", "1002's", b);
        ask_as(1001, "1001", "a 1001 not dumpable", nd);
        pid_t ts[] = { r0, a, b, nd };
        for (int i = 0; i < 4; i++) { kill(ts[i], SIGKILL); waitpid(ts[i], 0, 0); }
        /* A pipe root made, reopened through its entry by 1001. */
        int p[2];
        (void)!pipe(p);
        pid_t c = fork();
        if (c == 0) {
            setgroups(0, 0);
            if (setresgid(1001, 1001, 1001) != 0 || setresuid(1001, 1001, 1001) != 0) _exit(1);
            errno = 0;
            int w = open(ent(p[1]), O_WRONLY);
            out("P: 1001 opens, through its own entry, a pipe root made: %s; writes through the end it holds: %ld", rv(w, errno), (long)write(p[1], "x", 1));
            _exit(0);
        }
        waitpid(c, 0, 0);
        close(p[0]); close(p[1]);
    } else {
        pid_t a = target(getuid(), 1), nd = target(getuid(), 0);
        ask_as(getuid(), "the user", "its own child's", a);
        ask_as(getuid(), "the user", "its own child's, not dumpable", nd);
        kill(a, SIGKILL); waitpid(a, 0, 0);
        kill(nd, SIGKILL); waitpid(nd, 0, 0);
    }
    /* Its own entries once it is not dumpable. */
    pid_t c = fork();
    if (c == 0) {
        prctl(PR_SET_DUMPABLE, 0, 0, 0, 0);
        int n = open("/dev/null", O_RDONLY);
        (void)!dup2(n, 7);
        ask("itself not dumpable", "its own (/proc/<its pid>)", getpid());
        struct stat s;
        errno = 0;
        long r = stat("/proc/self/fd/7", &s);
        out("P: itself not dumpable: stat /proc/self/fd/7 %s; fdinfo/7 %s", rv(r, errno), shown(7) );
        _exit(0);
    }
    waitpid(c, 0, 0);
    /* A zombie's. */
    c = fork();
    if (c == 0) _exit(0);
    nap(300);
    char d[64];
    snprintf(d, sizeof d, "/proc/%d/fd", (int)c);
    struct stat s;
    errno = 0;
    long l = lstat(d, &s);
    char ow[48] = "";
    if (l == 0) snprintf(ow, sizeof ow, " %u:%u %04o", (unsigned)s.st_uid, (unsigned)s.st_gid, (unsigned)(s.st_mode & 07777));
    errno = 0;
    DIR *dd = opendir(d);
    int eo = errno;
    int nent = 0;
    if (dd) { struct dirent *e; while ((e = readdir(dd))) if (e->d_name[0] != '.') nent++; closedir(dd); }
    char e0[64];
    snprintf(e0, sizeof e0, "/proc/%d/fd/0", (int)c);
    out("P: its zombie child's fd/: lstat %s%s; open %s, %d entries; fd/0 %s", rv(l, errno), ow, dd ? "0" : ename(eo), nent, lnk(e0, -1));
    waitpid(c, 0, 0);
}

/* ---- X: rmdir and rename of /proc and /sys (pax#80) ----------------------- */

static void mount_rows(void) {
    errno = 0; long a = rmdir("/proc"); int ea = errno;
    errno = 0; long b = rmdir("/sys"); int eb = errno;
    out("X: rmdir of /proc %s, /sys %s", rv(a, ea), rv(b, eb));
    errno = 0; a = rename("/proc", "/pq"); ea = errno;
    errno = 0; b = rename("/sys", "/sq"); eb = errno;
    out("X: rename of /proc to /pq %s, /sys to /sq %s", rv(a, ea), rv(b, eb));
    mkdir("/g/e", 0755);
    errno = 0; a = rename("/g/e", "/proc"); ea = errno;
    errno = 0; b = rename("/g/e", "/sys"); eb = errno;
    out("X: a directory renamed onto /proc %s, onto /sys %s", rv(a, ea), rv(b, eb));
    errno = 0; a = rename("/proc", "/proc"); ea = errno;
    out("X: rename of /proc to itself %s", rv(a, ea));
    errno = 0; a = rename("/proc/self", "/g/ps"); ea = errno;
    errno = 0; b = rmdir("/proc/self/fd"); eb = errno;
    out("X: rename of /proc/self out %s; rmdir of /proc/self/fd %s", rv(a, ea), rv(b, eb));
    struct stat s;
    /* `/`'s owner is not printed: the container's root is its user
     * namespace's, not 0 (its mode is the guest's and PAX's). */
    out("X: / is %04o; /proc and /sys still there: %s", stat("/", &s) == 0 ? (unsigned)(s.st_mode & 07777) : 0u, yesno(stat("/proc/self", &s) == 0 && stat("/sys", &s) == 0));
    rmdir("/g/e");
}

int main(void) {
    root = geteuid() == 0;
    out("fdtab: px50's probe, as %s", root ? "root" : "a user");
    link_rows();
    open_rows();
    list_rows();
    info_rows();
    perm_rows();
    mount_rows();
    out("fdtab: done");
    return 0;
}
