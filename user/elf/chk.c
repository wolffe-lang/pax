/* chk.c — px43: the file checks. What a process may open, truncate,
 * ask `access` about, run and walk through, by the class rule (owner,
 * group, other, chosen by the file-system ids; the access family by
 * the real ids, or with AT_EACCESS by the file-system ones), and what
 * a descriptor already open keeps. Static; every call under test is a
 * raw `syscall(2)` (px38.h's `rc`) or a plain wrapper whose answer is
 * the kernel's.
 *
 *   chk          as root: the image's cases (/k, built with owners and
 *                modes into the archive, the same archive on PAX and as
 *                Linux's root), each row by px38's five actors (a child
 *                that has become that user for good) or by a state of
 *                ids root sets up first
 *   chk user     the rows a user can make alone, as whoever runs it
 *                (tests/mpx5-users: `as 1000 1000 /bin/chk user`)
 *   chk soak N   N rounds of opens, refusals, walks, access, truncation,
 *                a file made and removed; every 1,000th round two execs
 *
 * Written from the man pages named in notes/px43-the-file-checks.md;
 * no kernel's or libc's source. */
#include "px38.h"
#include <dirent.h>
#include <sys/socket.h>
#include <sys/un.h>

struct actor { const char *name; unsigned uid, gid; int ng; unsigned gs[2]; };
static const struct actor A[] = {
    { "own ", 1000, 2999, 0, { 0, 0 } },
    { "grp ", 1001, 2000, 0, { 0, 0 } },
    { "sup ", 1001, 2999, 1, { 2000, 0 } },
    { "oth ", 1002, 2999, 0, { 0, 0 } },
    { "root", 0, 0, 0, { 0, 0 } },
};
#define NA 5
enum { OWN, GRP, SUP, OTH, ROOT };
static const char *cur = "self";
static int alone; /* `chk user`: every row as whoever runs it */
static char LONGNAME[257];

/* Run fn(arg) as actor a in a child (alone: in this process, as itself). */
static void as(int a, void (*fn)(long), long arg)
{
    if (alone) { cur = "self"; fn(arg); return; }
    cur = A[a].name;
    pid_t p = fork();
    if (p == 0) {
        if (A[a].uid != 0) become(A[a].uid, A[a].gid, A[a].ng, A[a].gs);
        else rc(SYS_setgroups, 0, 0, 0, 0, 0);
        fn(arg);
        _exit(0);
    }
    int st = reap(p);
    if (st != 0) say("! actor %s failed (%d)\n", A[a].name, st);
}
static void each(void (*fn)(long), long arg)
{
    if (alone) { as(0, fn, arg); return; }
    for (int a = 0; a < NA; a++) as(a, fn, arg);
}

static long st(const char *p)
{
    struct stat s;
    return rc(SYS_newfstatat, AT_FDCWD, (long)p, (long)&s, 0, 0);
}
static long op(const char *p, int flags)
{
    long fd = rc(SYS_openat, AT_FDCWD, (long)p, flags, 0640, 0);
    if (fd < 0) return fd;
    close((int)fd);
    return 0;
}
static long cd(const char *p)
{
    long r = rc(SYS_chdir, (long)p, 0, 0, 0, 0);
    if (r == 0 && chdir("/") != 0) _exit(97);
    return r;
}
/* execve(p) in a child: 0 when the program ran (seven exits 7), else -errno. */
static long run7(const char *p)
{
    pid_t q = fork();
    if (q == 0) {
        char *av[] = { (char *)p, NULL };
        char *ev[] = { NULL };
        rc(SYS_execve, (long)p, (long)av, (long)ev, 0, 0);
        _exit(100 + errno);
    }
    int s = reap(q);
    return s == 7 ? 0 : s >= 100 && s < 240 ? -(long)(s - 100) : 9000 + s;
}
static long size_of(const char *p)
{
    struct stat s;
    if (stat(p, &s) != 0) return -errno;
    return (long)s.st_size;
}
static const char *path(const char *a, const char *b)
{
    static char o[8][700];
    static int i;
    char *r = o[i++ & 7];
    snprintf(r, 700, "%s/%s", a, b);
    return r;
}

/* --- the image, as the process finds it ------------------------------------ */
static void census(void)
{
    static const char *P[] = { "/k", "/k/w/o", "/k/w/g", "/k/w/t", "/k/w/n", "/k/w/r", "/k/w/o/f", "/k/w/o/s", "/k/w/o/seven",
                               "/k/w/deep/mid", "/k/o/ro", "/k/o/rw", "/k/o/g", "/k/o/e0", "/k/c/a", "/k/c/rx", "/k/c/wx", "/k/c/gw",
                               "/k/c/nx", "/k/a/u1001", "/k/a/root", "/k/a/g2000", "/k/a/d1001", "/k/a/x644", "/k/a/x100", "/k/a/dir0",
                               "/k/x/m0000", "/k/x/m0754", "/k/x/dir", "/k/h/own", "/k/h/ownd", "/k/h/mine", "/k/h/mined", NULL };
    say("image:");
    for (int i = 0; P[i]; i++) say(" %s %04o %s", P[i], mode_of(P[i]), own_of(P[i]));
    say("\n");
}

/* --- W: the search of every directory a path passes ------------------------ */
static const char *const WD[] = { "/k/w/o", "/k/w/g", "/k/w/t", "/k/w/n", "/k/w/r" };
static const char *const WM[] = { "0100", "0010", "0001", "0000", "0444" };
static void walk_row(long i)
{
    const char *D = WD[i];
    char slash[64];
    snprintf(slash, sizeof slash, "%s/", D);
    say("walk %s %s of 1000:2000 %s: stat it %ld, it/ %ld; f %ld, s/f %ld, a missing name %ld, . %ld, .. %ld, f/x %ld, a 256-byte name %ld; open f %ld; "
        "access(F_OK) f %ld; chdir %ld; execve seven %ld\n",
        D, WM[i], cur, st(D), st(slash), st(path(D, "f")), st(path(D, "s/f")), st(path(D, "nothere")), st(path(D, ".")), st(path(D, "..")),
        st(path(D, "f/x")), st(path(D, LONGNAME)), op(path(D, "f"), O_RDONLY), rc(SYS_access, (long)path(D, "f"), 0, 0, 0, 0),
        cd(D), run7(path(D, "seven")));
}
static void deep_row(long unused)
{
    (void)unused;
    say("walk /k/w/deep/mid 0700 of 1001:2000 %s: stat mid %ld, mid/end %ld, mid/end/f %ld; open mid/end/f %ld; chdir mid/end %ld; a missing directory "
        "on the way %ld\n",
        cur, st("/k/w/deep/mid"), st("/k/w/deep/mid/end"), st("/k/w/deep/mid/end/f"), op("/k/w/deep/mid/end/f", O_RDONLY),
        cd("/k/w/deep/mid/end"), st("/k/w/deep/none/f"));
}

/* A working directory the process may not search: root goes in, then the
 * child becomes the actor. */
static void cwd_row(long i)
{
    char b[512];
    long g = rc(SYS_getcwd, (long)b, sizeof b, 0, 0, 0);
    long f = st("f"), dot = st("."), dd = st(".."), sf = st("s/f"), o = op(".", O_RDONLY | O_DIRECTORY);
    long c1 = rc(SYS_chdir, (long)"s", 0, 0, 0, 0), c2 = rc(SYS_chdir, (long)"..", 0, 0, 0, 0);
    say("cwd %s %s: stat f %ld, . %ld, .. %ld, s/f %ld; open . %ld; getcwd %s (%ld); chdir s %ld, then .. %ld\n", WD[i], cur, f, dot, dd, sf, o,
        g > 0 ? b : "-", g > 0 ? 0 : g, c1, c2);
}
static void dirfd_row(long i)
{
    /* descriptor 9: the directory, opened by root before the drop */
    struct stat s;
    char b[1024];
    long g = rc(SYS_getdents64, 9, (long)b, sizeof b, 0, 0);
    long f = rc(SYS_newfstatat, 9, (long)"f", (long)&s, 0, 0), e = rc(SYS_newfstatat, 9, (long)"", (long)&s, AT_EMPTY_PATH, 0);
    long u = rc(SYS_newfstatat, 9, (long)"..", (long)&s, 0, 0), o = rc(SYS_openat, 9, (long)"f", O_RDONLY, 0, 0);
    long x = rc(SYS_faccessat, 9, (long)"f", 0, 0, 0), c = rc(SYS_fchdir, 9, 0, 0, 0, 0);
    say("dirfd %s %s: fstatat f %ld, \"\" AT_EMPTY_PATH %ld, .. %ld; openat f %ld; faccessat(F_OK) f %ld; getdents64 %ld; fchdir %ld\n", WD[i], cur, f, e,
        u, o >= 0 ? 0 : o, x, g > 0 ? 0 : g, c);
}
static void root_then(int a, const char *dir, int asfd, void (*fn)(long), long arg)
{
    cur = A[a].name;
    pid_t p = fork();
    if (p == 0) {
        if (asfd) {
            int fd = open(dir, O_RDONLY | O_DIRECTORY);
            if (fd < 0 || dup2(fd, 9) != 9) { say("! %s: %d\n", dir, -errno); _exit(93); }
        } else if (chdir(dir) != 0) { say("! chdir %s: %d\n", dir, -errno); _exit(93); }
        if (A[a].uid != 0) become(A[a].uid, A[a].gid, A[a].ng, A[a].gs);
        else rc(SYS_setgroups, 0, 0, 0, 0, 0);
        fn(arg);
        _exit(0);
    }
    int s = reap(p);
    if (s != 0) say("! actor %s failed (%d)\n", A[a].name, s);
}

/* Symbolic links, made where the actor may search: what they lead through. */
static const char *LK;
static void link_row(long unused)
{
    (void)unused;
    struct stat s;
    char b[64];
    long rl = rc(SYS_readlink, (long)path(LK, "ln"), (long)b, sizeof b, 0, 0);
    say("links %s: stat ln (to /k/w/n/f) %ld, lstat ln %ld, readlink ln %ld; stat lo (to /k/w/o/f) %ld; lt (to ../../k/w/t/f) %ld; ldn (to /k/w/n) "
        "%ld, ldn/f %ld; chdir ldn %ld\n",
        cur, st(path(LK, "ln")), rc(SYS_newfstatat, AT_FDCWD, (long)path(LK, "ln"), (long)&s, AT_SYMLINK_NOFOLLOW, 0), rl,
        st(path(LK, "lo")), st(path(LK, "lt")), st(path(LK, "ldn")), st(path(LK, "ldn/f")), cd(path(LK, "ldn")));
}

/* --- O: open and truncate ---------------------------------------------------- */
static void open_row(long unused)
{
    (void)unused;
    long o1 = op("/k/o/ro", O_RDONLY | O_TRUNC), s1 = size_of("/k/o/ro");
    long o2 = op("/k/o/ro", O_WRONLY | O_TRUNC), s2 = size_of("/k/o/ro");
    long o3 = op("/k/o/e0", O_RDONLY | O_TRUNC);
    long o4 = op("/k/o/ro", O_RDONLY | O_CREAT), o5 = op("/k/o/ro", O_WRONLY | O_CREAT);
    long o6 = op("/k/o/g", O_RDWR), o7 = op("/k/o/g", O_RDONLY);
    long t1 = rc(SYS_truncate, (long)"/k/o/ro", 7, 0, 0, 0), t2 = rc(SYS_truncate, (long)"/k/o/rw", 7, 0, 0, 0);
    long t3 = rc(SYS_truncate, (long)"/k/o", 0, 0, 0, 0);
    long o8 = op("/k/o", O_WRONLY), o9 = op("/k/o", O_RDONLY);
    long f1, f2;
    int fd = open("/k/o/rw", O_RDONLY);
    f1 = fd < 0 ? 7000 + errno : rc(SYS_ftruncate, fd, 7, 0, 0, 0);
    if (fd >= 0) close(fd);
    fd = open("/k/o/rw", O_WRONLY);
    f2 = fd < 0 ? 7000 + errno : rc(SYS_ftruncate, fd, 7, 0, 0, 0);
    if (fd >= 0) close(fd);
    say("open %s: ro (0444) O_RDONLY|O_TRUNC %ld, size %ld; O_WRONLY|O_TRUNC %ld, size %ld; an empty 0444 file O_RDONLY|O_TRUNC %ld; ro O_RDONLY|O_CREAT "
        "%ld, O_WRONLY|O_CREAT %ld; the 0060 file O_RDWR %ld, O_RDONLY %ld; truncate ro %ld, rw (0666) %ld, the directory %ld; the directory (0755 root's) "
        "O_WRONLY %ld, O_RDONLY %ld; ftruncate rw on a read-only descriptor %ld, a write-only one %ld; sizes after: ro %ld, rw %ld\n",
        cur, o1, s1, o2, s2, o3, o4, o5, o6, o7, t1, t2, t3, o8, o9, f1, f2, size_of("/k/o/ro"), size_of("/k/o/rw"));
}

/* --- C: a name made in a directory ------------------------------------------- */
static long make_in(const char *d)
{
    char n[96];
    snprintf(n, sizeof n, "%s/n%u", d, (unsigned)getuid());
    long fd = rc(SYS_openat, AT_FDCWD, (long)n, O_WRONLY | O_CREAT | O_EXCL, 0640, 0);
    if (fd < 0) return fd;
    close((int)fd);
    if (unlink(n) != 0) return 8000 + errno;
    return 0;
}
static void create_row(long unused)
{
    (void)unused;
    say("create %s: in a 0777 directory of root %ld, 0555 of root %ld, 0300 of 1000:2000 %ld, 0030 of 1000:2000 %ld, 0666 of root %ld; in the 0555 one, "
        "O_CREAT|O_EXCL of a name that exists %ld, O_CREAT alone %ld\n",
        cur, make_in("/k/c/a"), make_in("/k/c/rx"), make_in("/k/c/wx"), make_in("/k/c/gw"), make_in("/k/c/nx"),
        op("/k/c/rx/e", O_RDONLY | O_CREAT | O_EXCL), op("/k/c/rx/e", O_RDONLY | O_CREAT));
}

/* --- A: the access family: whose ids ----------------------------------------- */
static void access_lines(const char *who)
{
    static const char *F[] = { "/k/a/u1001", "/k/a/root", "/k/a/g2000" };
    static const char *FN[] = { "1001's 0600", "root's 0600", "1002:2000's 0040" };
    for (int k = 0; k < 3; k++)
        say("access %s, %s file: access(R_OK) %ld, faccessat(R_OK) %ld, faccessat2(R_OK, 0) %ld, faccessat2(R_OK, AT_EACCESS) %ld, open %ld\n", who, FN[k],
            rc(SYS_access, (long)F[k], 4, 0, 0, 0), rc(SYS_faccessat, AT_FDCWD, (long)F[k], 4, 0, 0),
            rc(SYS_faccessat2, AT_FDCWD, (long)F[k], 4, 0, 0), rc(SYS_faccessat2, AT_FDCWD, (long)F[k], 4, AT_EACCESS, 0), op(F[k], O_RDONLY));
    say("access %s, through 1001's 0700 directory: access(F_OK) %ld, faccessat2(F_OK, AT_EACCESS) %ld, open %ld; X_OK of root's 0644 file %ld, 0100 file "
        "%ld, 0000 directory %ld, AT_EACCESS %ld %ld %ld; R_OK|W_OK of the 0000 directory %ld\n",
        who, rc(SYS_access, (long)"/k/a/d1001/f", 0, 0, 0, 0), rc(SYS_faccessat2, AT_FDCWD, (long)"/k/a/d1001/f", 0, AT_EACCESS, 0),
        op("/k/a/d1001/f", O_RDONLY), rc(SYS_access, (long)"/k/a/x644", 1, 0, 0, 0), rc(SYS_access, (long)"/k/a/x100", 1, 0, 0, 0),
        rc(SYS_access, (long)"/k/a/dir0", 1, 0, 0, 0), rc(SYS_faccessat2, AT_FDCWD, (long)"/k/a/x644", 1, AT_EACCESS, 0),
        rc(SYS_faccessat2, AT_FDCWD, (long)"/k/a/x100", 1, AT_EACCESS, 0), rc(SYS_faccessat2, AT_FDCWD, (long)"/k/a/dir0", 1, AT_EACCESS, 0),
        rc(SYS_access, (long)"/k/a/dir0", 6, 0, 0, 0));
}
struct state { long r, e, s, fsu, gr, ge, gs, fsg; int ng; unsigned gl[2]; };
static void access_state(const struct state *S)
{
    pid_t p = fork();
    if (p == 0) {
        if (rc(SYS_setgroups, S->ng, (long)S->gl, 0, 0, 0) != 0) _exit(91);
        if (rc(SYS_setresgid, S->gr, S->ge, S->gs, 0, 0) != 0) _exit(91);
        if (S->fsg >= 0) rc(SYS_setfsgid, S->fsg, 0, 0, 0, 0);
        if (rc(SYS_setresuid, S->r, S->e, S->s, 0, 0) != 0) _exit(91);
        if (S->fsu >= 0) rc(SYS_setfsuid, S->fsu, 0, 0, 0, 0);
        char who[160];
        snprintf(who, sizeof who, "uid %s gid %s groups '%s'", uids(), gids(), groups());
        access_lines(who);
        _exit(0);
    }
    int s = reap(p);
    if (s != 0) say("! access state failed (%d)\n", s);
}

/* --- X: execve of an archive file, by mode and by who asks ------------------- */
static const unsigned XM[] = { 0000, 0400, 0200, 0100, 0040, 0020, 0010, 0004, 0002, 0001, 0700, 0070, 0007,
                               0077, 0707, 0770, 0777, 0644, 0755, 0750, 0754 };
#define NXM (sizeof XM / sizeof *XM)
static void exec_row(long i)
{
    char p[32];
    snprintf(p, sizeof p, "/k/x/m%04o", XM[i]);
    say("exec %04o %s: execve %ld; access(X_OK) %ld, AT_EACCESS %ld\n", XM[i], cur, run7(p), rc(SYS_access, (long)p, 1, 0, 0, 0),
        rc(SYS_faccessat2, AT_FDCWD, (long)p, 1, AT_EACCESS, 0));
}
static void exec_more(long unused)
{
    (void)unused;
    say("exec %s: a directory %ld; /k/w/n/seven (0755, in a 0000 directory) %ld; /k/w/o/seven (in a 0100 one of 1000) %ld\n", cur, run7("/k/x/dir"),
        run7("/k/w/n/seven"), run7("/k/w/o/seven"));
}

/* --- H: a descriptor that outlives a change of mode -------------------------- */
static void held_after(const char *f, const char *d, int rw, int ro, int dd)
{
    char b[1024];
    struct stat s;
    long r = lseek(ro, 0, SEEK_SET) == 0 && read(ro, b, 1) == 1 ? 0L : -(long)errno;
    long w = write(rw, "h", 1) == 1 ? 0L : -(long)errno;
    long t = rc(SYS_ftruncate, rw, 2, 0, 0, 0);
    long wo = rc(SYS_write, ro, (long)"h", 1, 0, 0);
    long fs = rc(SYS_fstat, rw, (long)&s, 0, 0, 0);
    unsigned fm = fs == 0 ? (unsigned)(s.st_mode & 07777) : 0u;
    long g = rc(SYS_getdents64, dd, (long)b, sizeof b, 0, 0);
    long cw = rc(SYS_getcwd, (long)b, sizeof b, 0, 0, 0);
    say("held %s: a file and a directory opened at 0666 and 0755, then made 0000: read on the old read descriptor %ld, write on the old O_RDWR one %ld, "
        "ftruncate %ld, write on the read one %ld, fstat %ld mode %04o; a new open O_RDONLY %ld, O_WRONLY %ld; the directory: getdents64 %ld, fstatat "
        "f %ld, fchdir %ld; in it as the working directory: stat f %ld, getcwd %ld\n",
        cur, r, w, t, wo, fs, fm, op(f, O_RDONLY), op(f, O_WRONLY), g > 0 ? 0 : g,
        rc(SYS_newfstatat, dd, (long)"f", (long)&s, 0, 0), rc(SYS_fchdir, dd, 0, 0, 0, 0), st("f"), cw > 0 ? 0 : cw);
    (void)d;
}
static void held_by(int a)
{
    char f[64], d[72];
    snprintf(f, sizeof f, "/k/h/%.4s", A[a].name);
    for (char *q = f; *q; q++) if (*q == ' ') *q = 0;
    snprintf(d, sizeof d, "%sd", f);
    int p1[2], p2[2];
    if (pipe(p1) || pipe(p2)) { say("! pipe\n"); return; }
    cur = A[a].name;
    pid_t p = fork();
    if (p == 0) {
        close(p1[0]); close(p2[1]);
        if (A[a].uid != 0) become(A[a].uid, A[a].gid, A[a].ng, A[a].gs);
        else rc(SYS_setgroups, 0, 0, 0, 0, 0);
        int rw = open(f, O_RDWR), ro = open(f, O_RDONLY), dd = open(d, O_RDONLY | O_DIRECTORY);
        if (rw < 0 || ro < 0 || dd < 0 || chdir(d) != 0) { say("! held %s: %d\n", cur, -errno); _exit(93); }
        char c = 'r';
        if (write(p1[1], &c, 1) != 1 || read(p2[0], &c, 1) != 1) _exit(94);
        held_after(f, d, rw, ro, dd);
        _exit(0);
    }
    close(p1[1]); close(p2[0]);
    char c;
    if (read(p1[0], &c, 1) == 1) {
        long a1 = rc(SYS_chmod, (long)f, 0, 0, 0, 0), a2 = rc(SYS_chmod, (long)d, 0, 0, 0, 0);
        if (a1 || a2) say("! chmod by root %ld %ld\n", a1, a2);
    } else say("! the holder did not open\n");
    c = 'g';
    if (write(p2[1], &c, 1) != 1) say("! pipe\n");
    close(p1[0]); close(p2[1]);
    int s = reap(p);
    if (s != 0) say("! actor %s failed (%d)\n", A[a].name, s);
}
static void held_alone(void)
{
    /* the user's own file and directory: it opens them, then makes them 0000 itself */
    const char *f = "/k/h/mine", *d = "/k/h/mined";
    int rw = open(f, O_RDWR), ro = open(f, O_RDONLY), dd = open(d, O_RDONLY | O_DIRECTORY);
    if (rw < 0 || ro < 0 || dd < 0 || chdir(d) != 0) { say("! held: %d\n", -errno); return; }
    long a1 = rc(SYS_chmod, (long)f, 0, 0, 0, 0), a2 = rc(SYS_chmod, (long)d, 0, 0, 0, 0);
    say("held self: its own file and directory made 0000 by itself: chmod %ld, %ld\n", a1, a2);
    held_after(f, d, rw, ro, dd);
    if (chdir("/") != 0) _exit(97);
    close(rw); close(ro); close(dd);
}

/* --- S: a socket's name -------------------------------------------------------- */
static void sock_row(long unused)
{
    (void)unused;
    say("socket's name 0000 of root %s: open O_RDONLY %ld, O_WRONLY %ld; stat %ld\n", cur, op("/t/chk/sock", O_RDONLY), op("/t/chk/sock", O_WRONLY),
        st("/t/chk/sock"));
}

/* --- the soak ------------------------------------------------------------------ */
static long memfree(void)
{
    return atol(status_line("/proc/meminfo", "MemFree"));
}
static int soak(long n)
{
    unsigned me = getuid();
    int root = me == 0;
    long wrong = 0, calls = 0, execs = 0, mem[5] = { 0, 0, 0, 0, 0 };
    long no = root ? 0 : -13; /* what a user is told where root is let through */
    char mk[64];
    snprintf(mk, sizeof mk, "/k/c/a/s%u", me);
    mem[0] = memfree();
    for (long i = 0; i < n; i++) {
        wrong += op("/k/o/g", O_RDONLY) != no;
        wrong += op("/k/o/rw", O_RDWR) != 0;
        wrong += st("/k/w/n/f") != no;
        wrong += st("/k/w/o/f") != 0;
        wrong += rc(SYS_access, (long)"/k/a/root", 4, 0, 0, 0) != no;
        wrong += rc(SYS_faccessat2, AT_FDCWD, (long)"/k/a/root", 4, AT_EACCESS, 0) != no;
        long fd = rc(SYS_openat, AT_FDCWD, (long)mk, O_WRONLY | O_CREAT | O_EXCL, 0600, 0);
        wrong += fd < 0;
        if (fd >= 0) close((int)fd);
        wrong += unlink(mk) != 0;
        wrong += rc(SYS_truncate, (long)"/k/o/ro", 7, 0, 0, 0) != no;
        wrong += cd("/k/w/n") != no;
        calls += 10;
        if (i % 1000 == 0) {
            wrong += run7("/k/x/m0700") != 0;
            wrong += run7("/k/x/m0070") != no;
            execs += 2;
        }
        if (n >= 4 && (i + 1) % (n / 4) == 0 && (i + 1) / (n / 4) <= 4) mem[(i + 1) / (n / 4)] = memfree();
    }
    say("soak: %ld rounds, %ld calls that open, walk, ask access, truncate, make and remove, %ld execs, %ld wrong answers, as uid %u\n", n, calls, execs,
        wrong, me);
    say("~soak: MemFree before %ld kB, at each quarter %ld %ld %ld %ld kB\n", mem[0], mem[1], mem[2], mem[3], mem[4]);
    return wrong ? 1 : 0;
}

int main(int argc, char **argv)
{
    memset(LONGNAME, 'a', 256);
    if (argc > 2 && strcmp(argv[1], "soak") == 0) return soak(atol(argv[2]));
    alone = argc > 1 && strcmp(argv[1], "user") == 0;
    if (!alone && getuid() != 0) { say("usage: chk (as root) | chk user | chk soak N\n"); return 2; }
    umask(022);
    say("chk: uid %s gid %s groups '%s'\n", uids(), gids(), groups());
    census();

    say("== W: the search of every directory a path passes\n");
    for (long i = 0; i < 5; i++) each(walk_row, i);
    each(deep_row, 0);
    if (!alone) {
        for (long i = 0; i < 5; i++)
            for (int a = 0; a < NA; a++) root_then(a, WD[i], 0, cwd_row, i);
        for (long i = 3; i < 5; i++)
            for (int a = 0; a < NA; a++) root_then(a, WD[i], 1, dirfd_row, i);
    }
    LK = alone ? "/t/chku" : "/t/chk";
    if (mkdir(LK, 0755) != 0) say("! mkdir %s: %d\n", LK, -errno);
    {
        long a = symlink("/k/w/n/f", path(LK, "ln")), b = symlink("/k/w/o/f", path(LK, "lo")), c = symlink("../../k/w/t/f", path(LK, "lt")),
             d = symlink("/k/w/n", path(LK, "ldn"));
        if (a || b || c || d) say("! symlink: %d\n", -errno);
    }
    each(link_row, 0);

    say("== O: open and truncate\n");
    each(open_row, 0);
    say("== C: a name made in a directory\n");
    each(create_row, 0);

    say("== A: the access family\n");
    if (alone) access_lines("self");
    else {
        static const struct state S[] = {
            { 1000, 1001, 1001, -1, 2999, 2999, 2999, -1, 0, { 0, 0 } },
            { 1001, 1000, 1000, -1, 2999, 2999, 2999, -1, 0, { 0, 0 } },
            { 0, 1000, 0, -1, 2999, 2999, 2999, -1, 0, { 0, 0 } },
            { 1000, 0, 0, -1, 2999, 2999, 2999, -1, 0, { 0, 0 } },
            { 0, 0, 0, 1002, 2999, 2999, 2999, -1, 0, { 0, 0 } },
            { 0, 1000, 0, 0, 2999, 2999, 2999, -1, 0, { 0, 0 } },
            { 1000, 0, 0, 1000, 2999, 2999, 2999, -1, 0, { 0, 0 } },
            { 1003, 1003, 1003, -1, 2000, 2999, 2999, -1, 0, { 0, 0 } },
            { 1003, 1003, 1003, -1, 2999, 2000, 2000, -1, 0, { 0, 0 } },
            { 1003, 1003, 1003, -1, 2000, 2000, 2000, 2999, 0, { 0, 0 } },
            { 1003, 1003, 1003, -1, 2999, 2999, 2999, -1, 1, { 2000, 0 } },
            { 1002, 1002, 1002, -1, 2000, 2000, 2000, -1, 0, { 0, 0 } },
            { 0, 0, 0, -1, 0, 0, 0, -1, 0, { 0, 0 } },
        };
        for (unsigned i = 0; i < sizeof S / sizeof *S; i++) access_state(&S[i]);
    }

    say("== X: execve of an archive file 1000:2000, by mode and by who asks\n");
    for (long i = 0; i < (long)NXM; i++) each(exec_row, i);
    each(exec_more, 0);
    if (!alone) {
        pid_t p = fork();
        if (p == 0) {
            rc(SYS_setgroups, 0, 0, 0, 0, 0);
            long f = rc(SYS_setfsuid, 1002, 0, 0, 0, 0);
            say("exec root after setfsuid(1002) = %ld: m0700 %ld, m0070 %ld, m0007 %ld, m0001 %ld, m0000 %ld\n", f, run7("/k/x/m0700"), run7("/k/x/m0070"),
                run7("/k/x/m0007"), run7("/k/x/m0001"), run7("/k/x/m0000"));
            _exit(0);
        }
        reap(p);
    }

    say("== H: a descriptor that outlives a change of mode\n");
    if (alone) held_alone();
    else for (int a = 0; a < NA; a++) held_by(a);

    if (!alone) {
        say("== S: a socket's name\n");
        struct sockaddr_un a;
        memset(&a, 0, sizeof a);
        a.sun_family = AF_UNIX;
        snprintf(a.sun_path, sizeof a.sun_path, "/t/chk/sock");
        int s = socket(AF_UNIX, SOCK_STREAM, 0);
        umask(0777);
        long b = s < 0 ? -errno : bind(s, (struct sockaddr *)&a, sizeof a) == 0 ? 0L : -(long)errno;
        umask(022);
        say("bound by root with umask 0777: %ld, %04o %s\n", b, mode_of("/t/chk/sock"), own_of("/t/chk/sock"));
        each(sock_row, 0);
        if (s >= 0) close(s);
        unlink("/t/chk/sock");
    }
    say("chk: done\n");
    return 0;
}
