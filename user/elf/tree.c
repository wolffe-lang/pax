/* tree.c — px27's probe of a writable file tree: one static glibc
   program that prints what it sees, run unmodified as the first program
   on Linux (its root a tmpfs, inside a throwaway container) and on PAX
   (tests/mpx3-tree), the two outputs compared byte for byte. Every line
   is something a kernel decides: what `open` makes and refuses, where
   `O_APPEND` puts a write, what a hole reads as and what it costs, what
   `ftruncate` gives back, what is left of a file whose name is gone
   while it is open, what `rename` replaces and refuses, a directory's
   size and link count, what a reading of a directory returns while the
   directory changes, a working directory that has been removed, which
   times move and when, and the errnos.

     tree             every probe, in order (it works in /t, which it
                      makes and removes)
     tree soak        10,000 rounds of create, write, rename, unlink
                      (and mkdir, rmdir), then a fill to ENOSPC and
                      back, twice: the second time with 120 MiB of the
                      program's own memory held
     tree noop        (a role the probe starts: exit 7)
     tree speed       16 MiB written and read back, then eight more
                      passes over it, timed

   Built with the host's cc: `cc -static -O1` (tools/mkprobes). Lines
   that depend on the host and not on the ABI (how many megabytes fit, a
   time in milliseconds, what PAX refuses by name and Linux does) start
   with `~` and are not compared. Nothing here reads a kernel's or a
   libc's source: the calls are the man pages', the structures the
   public headers'. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <sched.h>
#include <limits.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/sendfile.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/time.h>
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

/* -1 with errno E as "-E", else the value */
static long r(long v) { return v == -1 ? -errno : v; }
static void ms(int n) {
    struct timespec t = { n / 1000, (n % 1000) * 1000000L };
    while (nanosleep(&t, &t) != 0 && errno == EINTR) {}
}
static long long ns_of(struct timespec t) { return t.tv_sec * 1000000000LL + t.tv_nsec; }
static long long wall(void) {
    struct timespec t;
    clock_gettime(CLOCK_REALTIME, &t);
    return ns_of(t);
}
static long mono_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

/* "mode 100644 links 1 size 5 blocks 8", or "-2" */
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
static long put(const char *path, const char *text) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (fd < 0) return -errno;
    long w = r(write(fd, text, strlen(text)));
    close(fd);
    return w;
}
/* a file's whole text (at most 255 bytes), or "-E" */
static const char *get(const char *path) {
    static char b[4][256];
    static int k;
    char *o = b[k++ & 3];
    int fd = open(path, O_RDONLY);
    if (fd < 0) { snprintf(o, 256, "%d", -errno); return o; }
    ssize_t n = read(fd, o, 255);
    if (n < 0) snprintf(o, 256, "%d", -errno); else o[n] = 0;
    close(fd);
    return o;
}

static ino_t ino_of(const char *p) {
    struct stat s;
    return stat(p, &s) == 0 ? s.st_ino : 0;
}

/* Every answer is taken in a statement of its own, in the order the
   line names it: C leaves the order of a call's arguments open. */

/* ---- making: mkdir, open with O_CREAT, the mode and umask ----------------- */
static void making(void) {
    mode_t um = umask(022);
    umask(um);
    long a = r(mkdir("/t", 0777)), b = r(mkdir("/t", 0777));
    say("make: umask %03o; mkdir /t %ld, again %ld, /t: %s\n", um, a, b, st("/t"));
    put("/t/f", "x");
    a = r(mkdir("/t/no/such", 0777));
    b = r(mkdir("/t/f/d", 0777));
    long c = r(mkdir("/t/slash/", 0777));
    const char *s1 = st("/t/slash");
    long d = r(mkdir("/t/.", 0777)), e = r(mkdir("/", 0777)), f = r(mkdir("/dev", 0777));
    say("make: mkdir /t/no/such %ld, under a file %ld, with a trailing slash %ld (%s), of . %ld, of / %ld, of /dev %ld\n", a, b, c,
        s1, d, e, f);
    int fd = open("/t/a", O_WRONLY | O_CREAT | O_EXCL, 0666);
    s1 = fst(fd);
    a = r(open("/t/a", O_WRONLY | O_CREAT | O_EXCL, 0666));
    int fd2 = open("/t/a", O_WRONLY | O_CREAT, 0666);
    say("create: O_CREAT|O_EXCL makes it %d, %s; again %ld; O_CREAT alone opens it %d\n", fd >= 0, s1, a, fd2 >= 0);
    close(fd2);
    a = r(write(fd, "hello", 5));
    s1 = fst(fd);
    b = r(lseek(fd, 0, SEEK_CUR));
    char ch = 0;
    c = r(read(fd, &ch, 1));
    say("create: write 5 bytes %ld, %s, the offset %ld; a read on it %ld\n", a, s1, b, c);
    close(fd);
    fd = open("/t/a", O_RDONLY);
    s1 = get("/t/a");
    a = r(write(fd, &ch, 1));
    say("create: read back '%s'; a write on a descriptor opened to read %ld\n", s1, a);
    close(fd);
    fd = open("/t/a", O_WRONLY | O_TRUNC);
    say("create: O_TRUNC leaves %s\n", fst(fd));
    close(fd);
    put("/t/a", "hello");
    fd = open("/t/a", O_RDONLY | O_TRUNC);
    say("create: O_RDONLY|O_TRUNC opens %d and leaves %s\n", fd >= 0, st("/t/a"));
    close(fd);
    a = r(open("/t", O_WRONLY));
    b = r(open("/t", O_RDWR));
    c = r(open("/t", O_RDONLY | O_CREAT, 0666));
    d = r(open("/t/a/", O_RDONLY));
    e = r(open("/t/a", O_RDONLY | O_DIRECTORY));
    say("create: a directory opened to write %ld, to read and write %ld, with O_CREAT %ld; a file with a trailing slash %ld; O_DIRECTORY on a file %ld\n",
        a, b, c, d, e);
    a = r(open("/t/no/x", O_WRONLY | O_CREAT, 0666));
    b = r(open("/t/a/x", O_WRONLY | O_CREAT, 0666));
    c = r(open("/t/new/", O_WRONLY | O_CREAT, 0666));
    d = r(open("/t/none", O_WRONLY));
    say("create: in a missing directory %ld, under a file %ld, a new name with a trailing slash %ld, a missing name without O_CREAT %ld\n",
        a, b, c, d);
    mode_t old = umask(027);
    close(open("/t/m1", O_WRONLY | O_CREAT, 0666));
    mkdir("/t/md", 0777);
    s1 = st("/t/m1");
    say("mode: under umask 027 (the old one %03o): %s; %s\n", old, s1, st("/t/md"));
    umask(0);
    close(open("/t/m2", O_WRONLY | O_CREAT, 0666));
    close(open("/t/m3", O_WRONLY | O_CREAT, 0));
    fd = open("/t/m3", O_RDWR);
    s1 = st("/t/m2");
    say("mode: under umask 0: %s; made with mode 0: %s, and root opens it to write %d\n", s1, st("/t/m3"), fd >= 0);
    close(fd);
    say("mode: umask answers the old mask %03o\n", umask(022));
    a = r(unlink("/t/f")); b = r(unlink("/t/a")); c = r(unlink("/t/m1")); d = r(unlink("/t/m2")); e = r(unlink("/t/m3"));
    f = r(rmdir("/t/md"));
    long g = r(rmdir("/t/slash"));
    say("make: unlink the five %ld %ld %ld %ld %ld, rmdir the two %ld %ld\n", a, b, c, d, e, f, g);
}

/* ---- O_APPEND -------------------------------------------------------------- */
static void appending(void) {
    int a = open("/t/log", O_WRONLY | O_CREAT | O_APPEND, 0666);
    int b = open("/t/log", O_WRONLY | O_APPEND);
    int p = open("/t/log", O_WRONLY);
    write(a, "one\n", 4);
    write(b, "two\n", 4);
    write(a, "three\n", 6);
    const char *g = get("/t/log");
    say("append: two descriptors, three writes: '%s' (%s)\n", g, st("/t/log"));
    write(p, "ONE", 3);
    say("append: a third without O_APPEND writes at its own offset: '%s'\n", get("/t/log"));
    long at = r(lseek(a, 0, SEEK_SET));
    write(a, "four\n", 5);
    const char *s1 = st("/t/log") + 20;
    long off = r(lseek(a, 0, SEEK_CUR));
    say("append: after lseek to %ld the appending one still appends: %s, its offset %ld\n", at, s1, off);
    long pw = r(pwrite(a, "five\n", 5, 0));
    g = get("/t/log");
    say("append: pwrite at 0 on it %ld: the file starts '%.3s' and is %s\n", pw, g, st("/t/log") + 20);
    close(a); close(b); close(p);
    /* two processes, 200 lines each of 32 bytes: every line whole */
    unlink("/t/log");
    pid_t k = fork();
    int fd = open("/t/log", O_WRONLY | O_CREAT | O_APPEND, 0666);
    char line[33];
    memset(line, k == 0 ? 'c' : 'p', 31);
    line[31] = '\n';
    for (int i = 0; i < 200; i++) {
        if (write(fd, line, 32) != 32) _exit(9);
        if (i % 16 == 0) sched_yield();
    }
    close(fd);
    if (k == 0) _exit(0);
    int ws = 0;
    waitpid(k, &ws, 0);
    fd = open("/t/log", O_RDONLY);
    int whole = 1, nc = 0, np = 0;
    char got[32];
    while (read(fd, got, 32) == 32) {
        for (int i = 1; i < 31; i++) if (got[i] != got[0]) whole = 0;
        if (got[31] != '\n') whole = 0;
        if (got[0] == 'c') nc++; else if (got[0] == 'p') np++; else whole = 0;
    }
    close(fd);
    say("append: two processes, 200 lines each: the child's status %d, %s, the child's lines %d, the parent's %d, every line whole %d\n",
        ws, st("/t/log") + 20, nc, np, whole);
    unlink("/t/log");
}

/* ---- holes, pwrite, truncation ----------------------------------------------- */
static void holes(void) {
    int fd = open("/t/h", O_RDWR | O_CREAT, 0666);
    long at = r(lseek(fd, 1048576, SEEK_SET));
    const char *s1 = fst(fd) + 20;
    write(fd, "x", 1);
    say("hole: lseek past the end %ld leaves %s; one byte written there: %s\n", at, s1, fst(fd) + 20);
    char z[16] = "................";
    long n = r(pread(fd, z, 16, 4000));
    int zero = 1;
    for (int i = 0; i < 16; i++) if (z[i] != 0) zero = 0;
    long a = r(pread(fd, z, 16, 1048576)), b = r(pread(fd, z, 16, 2000000));
    say("hole: 16 bytes read from the hole %ld, all zero %d; read at the end %ld, past it %ld\n", n, zero, a, b);
    a = r(pwrite(fd, "abc", 3, 12288));
    say("hole: pwrite of 3 bytes at 12288: %ld, %s\n", a, fst(fd) + 20);
    a = r(ftruncate(fd, 5000));
    s1 = fst(fd) + 20;
    b = r(ftruncate(fd, 10000));
    say("hole: ftruncate to 5000: %ld, %s; to 10000: %ld, %s\n", a, s1, b, fst(fd) + 20);
    char w[20];
    memset(w, 'q', 20);
    a = r(pwrite(fd, w, 20, 4086));
    say("hole: 20 bytes across the page boundary at 4086: %ld, %s\n", a, fst(fd) + 20);
    ftruncate(fd, 4090);
    ftruncate(fd, 10000);
    char back[20];
    pread(fd, back, 20, 4086);
    int tail = 1;
    for (int i = 4; i < 20; i++) if (back[i] != 0) tail = 0;
    say("hole: cut to 4090 and grown again: the four bytes kept '%.4s', what was cut reads zero %d, %s\n", back, tail, fst(fd) + 20);
    a = r(ftruncate(fd, 0));
    s1 = fst(fd) + 20;
    b = r(ftruncate(fd, -1));
    say("hole: ftruncate to 0: %ld, %s; to -1: %ld\n", a, s1, b);
    int rd = open("/t/h", O_RDONLY);
    write(fd, "0123456789", 10);
    a = r(ftruncate(rd, 0));
    b = r(truncate("/t/h", 7));
    s1 = st("/t/h") + 20;
    long c = r(truncate("/t", 0)), d = r(truncate("/t/none", 0));
    say("hole: ftruncate on a descriptor opened to read %ld; truncate by path to 7: %ld (%s), of a directory %ld, of a missing name %ld\n",
        a, b, s1, c, d);
    a = r(pwrite(rd, "x", 1, 0));
    close(rd);
    rd = open("/t/h", O_WRONLY);
    b = r(pread(rd, z, 1, 0));
    c = r(pwrite(fd, "x", 1, -1));
    say("hole: pwrite on a descriptor opened to read %ld, pread on one opened to write %ld, pwrite at a negative offset %ld\n", a, b, c);
    close(rd);
    a = r(fsync(fd));
    b = r(fdatasync(fd));
    rd = open("/t", O_RDONLY);
    c = r(fsync(rd));
    close(rd);
    d = r(fsync(rd));
    say("sync: fsync %ld, fdatasync %ld, of a directory %ld, of a closed descriptor %ld\n", a, b, c, d);
    close(fd);
    unlink("/t/h");
}

/* ---- a file whose name is gone while it is open -------------------------------- */
static void unlinked(void) {
    int fd = open("/t/u", O_RDWR | O_CREAT, 0666);
    char page[4096];
    memset(page, 'u', sizeof page);
    for (int i = 0; i < 3; i++) write(fd, page, sizeof page);
    int d = dup(fd);
    const char *s1 = fst(fd);
    long a = r(unlink("/t/u"));
    const char *s2 = st("/t/u");
    say("unlinked: %s; unlink %ld; by name %s; by descriptor %s\n", s1, a, s2, fst(fd));
    char b[8];
    long n = r(pread(fd, b, 8, 8000));
    a = r(write(d, page, sizeof page));
    s1 = fst(d) + 20;
    put("/t/u", "new");
    say("unlinked: still read %ld '%.8s', written %ld, %s; the name made again is another file: %s\n", n, b, a, s1, st("/t/u"));
    close(fd);
    say("unlinked: after one close the other descriptor still reads %ld; then closed\n", r(pread(d, b, 8, 12288)));
    close(d);
    unlink("/t/u");
    mkdir("/t/d", 0777);
    put("/t/d/x", "x");
    a = r(unlink("/t/d"));
    long c = r(unlink("/t/none")), e = r(unlink("/t/d/x/")), f = r(unlink("/t/d/."));
    say("remove: unlink of a directory %ld, of a missing name %ld, of a file with a trailing slash %ld, of . %ld\n", a, c, e, f);
    a = r(rmdir("/t/d/x")); c = r(rmdir("/t/d")); e = r(rmdir("/t/none")); f = r(rmdir("/t/d/."));
    long g = r(rmdir("/t/d/..")), h = r(rmdir("/")), i = r(rmdir("/dev"));
    say("remove: rmdir of a file %ld, of a directory with an entry %ld, of a missing name %ld, of d/. %ld, of d/.. %ld, of / %ld, of /dev %ld\n",
        a, c, e, f, g, h, i);
    a = r(unlinkat(AT_FDCWD, "/t/d/x", AT_REMOVEDIR));
    c = r(unlinkat(AT_FDCWD, "/t/d", 0));
    e = r(unlinkat(AT_FDCWD, "/t/d/x", 0));
    f = r(unlinkat(AT_FDCWD, "/t/d", AT_REMOVEDIR));
    say("remove: unlinkat with AT_REMOVEDIR on a file %ld, without it on a directory %ld; then the file %ld and the directory %ld\n", a,
        c, e, f);
}

/* ---- a working directory that is removed ------------------------------------- */
static void workdir(void) {
    char p[256];
    mkdir("/t/w", 0777);
    int dfd = open("/t/w", O_RDONLY | O_DIRECTORY);
    long a = r(chdir("/t/w"));
    char *g = getcwd(p, sizeof p);
    say("cwd: chdir %ld, getcwd '%s'; ", a, g ? p : "?");
    say("rmdir of it from inside %ld; ", r(rmdir("../w")));
    g = getcwd(p, sizeof p);
    long ge = g ? 0 : -errno;
    char buf[256];
    long gd = syscall(SYS_getdents64, dfd, buf, sizeof buf);
    gd = gd == -1 ? -errno : gd;
    const char *s1 = st(".");
    say("then getcwd %ld, . is %s, by descriptor %s, a reading of it %ld\n", ge, s1, fst(dfd), gd);
    a = r(open("f", O_WRONLY | O_CREAT, 0666));
    long b = r(mkdir("d", 0777));
    int o = open(".", O_RDONLY);
    int up = ino_of("..") == ino_of("/t");
    say("cwd: a file made in it %ld, a directory %ld, . opened %d, .. is /t %d, the name is gone %s\n", a, b, o >= 0, up, st("/t/w"));
    close(o);
    a = r(chdir(".."));
    g = getcwd(p, sizeof p);
    say("cwd: chdir .. %ld, getcwd '%s'; /t: %s\n", a, g ? p : "?", st("/t"));
    close(dfd);
    chdir("/");
}

/* ---- rename ---------------------------------------------------------------------- */
static void renaming(void) {
    char p[256];
    put("/t/a", "aaa");
    put("/t/b", "bbbbb");
    ino_t ia = ino_of("/t/a");
    int fb = open("/t/b", O_RDONLY);
    int fa = open("/t/a", O_RDWR);
    long a = r(rename("/t/a", "/t/c"));
    const char *s1 = st("/t/a");
    const char *g = get("/t/c");
    say("rename: a to c %ld: a %s, c '%s', the same inode %d\n", a, s1, g, ino_of("/t/c") == ia);
    a = r(rename("/t/c", "/t/b"));
    g = get("/t/b");
    s1 = st("/t/c");
    say("rename: c over b %ld: b '%s', c %s; the replaced file by its descriptor: %s", a, g, s1, fst(fb));
    char old[8] = "";
    read(fb, old, 5);
    a = r(pwrite(fa, "Z", 1, 0));
    say(", read '%.5s'; the moved file's descriptor writes on: %ld, b '%s'\n", old, a, get("/t/b"));
    close(fa); close(fb);
    a = r(rename("/t/b", "/t/b"));
    long b = r(rename("/t/b", "/t/./b"));
    s1 = st("/t/b");
    long c = r(rename("/t/none", "/t/x")), d = r(rename("/t/b", "/t/no/x")), e = r(rename("/t/b", "/t/nodir/"));
    say("rename: b to b %ld, to ./b %ld (%s); a missing name %ld; into a missing directory %ld; a file to a missing name with a slash %ld\n",
        a, b, s1, c, d, e);
    mkdir("/t/d1", 0777);
    mkdir("/t/d1/in", 0777);
    put("/t/d1/in/f", "f");
    mkdir("/t/d2", 0777);
    mkdir("/t/e", 0777);
    s1 = st("/t") + 11;
    say("rename: /t %s, d1 %s; ", s1, st("/t/d1") + 11);
    a = r(rename("/t/b", "/t/e"));
    b = r(rename("/t/e", "/t/b"));
    c = r(rename("/t/e", "/t/d1"));
    d = r(rename("/t/d1", "/t/d1/sub"));
    e = r(rename("/t/d1", "/t/d1/in/deep"));
    say("a file onto a directory %ld, a directory onto a file %ld, a directory onto one with an entry %ld, into itself %ld, below itself %ld\n",
        a, b, c, d, e);
    ia = ino_of("/t/e");
    a = r(rename("/t/e", "/t/d2"));
    int same = ino_of("/t/d2") == ia;
    s1 = st("/t/e");
    b = r(rename("/t/d2", "/t/d3/"));
    say("rename: a directory onto an empty one %ld (d2's inode is now e's %d, e %s); to a new name with a slash %ld\n", a, same, s1, b);
    chdir("/t/d1/in");
    a = r(rename("/t/d1/in", "/t/d3/moved"));
    s1 = st("/t") + 11;
    const char *s2 = st("/t/d3") + 11;
    say("rename: a directory moved under another %ld: /t %s, d3 %s, d1 %s; ", a, s1, s2, st("/t/d1") + 11);
    char *cw = getcwd(p, sizeof p);
    int up = ino_of("..") == ino_of("/t/d3");
    say("a process working in it is now in '%s', its .. is d3 %d, its file '%s'\n", cw ? p : "?", up, get("f"));
    chdir("/");
    a = r(rename("/t/d1/.", "/t/x"));
    b = r(rename("/t/d1/..", "/t/x"));
    c = r(rename("/t/d1", "/t/."));
    d = r(rename("/", "/t/x"));
    e = r(rename("/dev", "/t/x"));
    long f = r(rename("/t/d1", "/dev"));
    long h = r(rename("/t/b", "/dev/px27-probe"));
    long i = r(rename("/dev/null", "/t/null"));
    say("rename: of . %ld, of .. %ld, onto . %ld, of / %ld, of /dev %ld, onto /dev %ld, into /dev %ld, out of /dev %ld\n", a, b, c, d, e,
        f, h, i);
    fa = open("/t", O_RDONLY | O_DIRECTORY);
    a = r(renameat(fa, "b", fa, "y"));
    b = r(syscall(SYS_renameat2, fa, "y", AT_FDCWD, "/t/z", 0));
    s1 = st("/t/b");
    say("rename: renameat by descriptors %ld, renameat2 with no flag %ld; b %s, z '%s'\n", a, b, s1, get("/t/z"));
    close(fa);
    unlink("/t/d3/moved/f");
    a = r(rmdir("/t/d3/moved")); b = r(rmdir("/t/d3")); c = r(rmdir("/t/d1")); d = r(unlink("/t/z"));
    say("rename: removed: %ld %ld %ld %ld\n", a, b, c, d);
}

/* ---- directories: sizes, link counts, a reading while it changes --------------- */
struct ent { uint64_t ino; int64_t off; unsigned short len; unsigned char type; char name[]; };
static int cmp(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }
static int names(const char *dir, char out[][64], int max, size_t bufsize) {
    int fd = open(dir, O_RDONLY | O_DIRECTORY);
    char buf[4096];
    int n = 0;
    for (;;) {
        long got = syscall(SYS_getdents64, fd, buf, bufsize);
        if (got <= 0) break;
        for (long o = 0; o < got;) {
            struct ent *e = (struct ent *)(buf + o);
            if (n < max) snprintf(out[n++], 64, "%s%c", e->name, e->type == DT_DIR ? '/' : e->type == DT_REG ? ' ' : '?');
            o += e->len;
        }
    }
    close(fd);
    char *p[512];
    static char tmp[512][64];
    for (int i = 0; i < n; i++) { memcpy(tmp[i], out[i], 64); p[i] = tmp[i]; }
    qsort(p, n, sizeof p[0], cmp);
    for (int i = 0; i < n; i++) memcpy(out[i], p[i], 64);
    return n;
}
static void directories(void) {
    static char nm[512][64];
    char list[512] = "";
    mkdir("/t/d", 0777);
    say("dir: empty %s; ", st("/t/d"));
    put("/t/d/one", "1");
    put("/t/d/two", "22");
    put("/t/d/three", "333");
    mkdir("/t/d/s1", 0777);
    mkdir("/t/d/s2", 0777);
    say("with three files and two directories %s; ", st("/t/d"));
    int n = names("/t/d", nm, 512, 4096);
    for (int i = 0; i < n; i++) { strcat(list, nm[i]); strcat(list, i + 1 < n ? "," : ""); }
    say("its names, sorted: %s\n", list);
    int fd = open("/t/d", O_RDONLY | O_DIRECTORY);
    char buf[512];
    long got = syscall(SYS_getdents64, fd, buf, sizeof buf);
    ino_t dot = 0, dotdot = 0;
    for (long o = 0; o < got;) {
        struct ent *e = (struct ent *)(buf + o);
        if (!strcmp(e->name, ".")) dot = e->ino;
        if (!strcmp(e->name, "..")) dotdot = e->ino;
        o += e->len;
    }
    lseek(fd, 0, SEEK_SET);
    long small = r(syscall(SYS_getdents64, fd, buf, 8));
    lseek(fd, 0, SEEK_SET);
    int again = syscall(SYS_getdents64, fd, buf, sizeof buf) == got;
    long rd = r(read(fd, buf, 8));
    say("dir: . is the directory's inode %d, .. its parent's %d; a buffer too small for one entry %ld; after lseek to 0 it reads again %d; read() on it %ld\n",
        dot == ino_of("/t/d"), dotdot == ino_of("/t"), small, again, rd);
    close(fd);
    unlink("/t/d/two");
    const char *s1 = st("/t/d");
    rmdir("/t/d/s2");
    say("dir: one file removed %s, one directory removed %s\n", s1, st("/t/d"));
    unlink("/t/d/one"); unlink("/t/d/three"); rmdir("/t/d/s1");
    /* a reading while the directory changes: 40 names, read a few at a
       time; between two readings some names are removed (ones already
       returned and ones not yet) and new ones made */
    char p[64];
    for (int i = 0; i < 40; i++) { snprintf(p, sizeof p, "/t/d/k%02d", i); put(p, "k"); }
    fd = open("/t/d", O_RDONLY | O_DIRECTORY);
    int seen[40] = { 0 }, gone[40] = { 0 }, seen_then[40] = { 0 }, rounds = 0;
    for (;;) {
        got = syscall(SYS_getdents64, fd, buf, 120);
        if (got <= 0) break;
        for (long o = 0; o < got;) {
            struct ent *e = (struct ent *)(buf + o);
            if (e->name[0] == 'k') {
                int i = atoi(e->name + 1);
                if (i >= 0 && i < 40) seen[i]++;
            }
            o += e->len;
        }
        if (++rounds == 3) {
            for (int i = 0; i < 40; i += 3) {
                snprintf(p, sizeof p, "/t/d/k%02d", i);
                seen_then[i] = seen[i];
                unlink(p);
                gone[i] = 1;
            }
            for (int i = 0; i < 10; i++) { snprintf(p, sizeof p, "/t/d/new%02d", i); put(p, "n"); }
        }
    }
    close(fd);
    int once = 1, twice = 0, late = 0;
    for (int i = 0; i < 40; i++) {
        if (!gone[i] && seen[i] != 1) once = 0;
        if (seen[i] > 1) twice++;
        if (gone[i] && seen[i] > seen_then[i]) late++;
    }
    say("dir: read while it changes: every name that stayed was returned exactly once %d, a name returned twice %d, a removed name returned after its removal %d\n",
        once, twice, late);
    n = names("/t/d", nm, 512, 256);
    int left = 0;
    for (int i = 0; i < n; i++) if (nm[i][0] == 'k' || nm[i][0] == 'n') left++;
    say("dir: then %d names, %s\n", left, st("/t/d"));
    for (int i = 0; i < 40; i++) { snprintf(p, sizeof p, "/t/d/k%02d", i); unlink(p); }
    for (int i = 0; i < 10; i++) { snprintf(p, sizeof p, "/t/d/new%02d", i); unlink(p); }
    s1 = st("/t/d");
    say("dir: emptied %s, removed %ld\n", s1, r(rmdir("/t/d")));
}

/* ---- names and the errnos -------------------------------------------------------- */
static void errnos(void) {
    static char big[5000];
    strcpy(big, "/t/");
    memset(big + 3, 'n', 255);
    big[258] = 0;
    int fd = open(big, O_WRONLY | O_CREAT, 0666);
    long ok255 = fd >= 0;
    close(fd);
    long un = r(unlink(big));
    memset(big + 3, 'n', 256);
    big[259] = 0;
    put("/t/a", "a");
    long a = r(open(big, O_WRONLY | O_CREAT, 0666)), b = r(mkdir(big, 0777));
    const char *s1 = st(big);
    long c = r(rename("/t/a", big));
    say("names: 255 bytes made %ld and removed %ld; 256 bytes: open %ld, mkdir %ld, stat %s, rename onto it %ld\n", ok255, un, a, b, s1, c);
    /* "/t" and "/." until the path is 4095 bytes (the longest: PATH_MAX
       counts the NUL), then one byte more */
    int o = sprintf(big, "/t/");
    while (o < 4095) o += sprintf(big + o, o + 2 <= 4095 ? "./" : ".");
    long l1 = strlen(big);
    a = r(access(big, F_OK));
    strcat(big, "/");
    long l2 = strlen(big);
    b = r(access(big, F_OK));
    say("names: a path of %ld bytes %ld, of %ld bytes %ld\n", l1, a, l2, b);
    mkdir("/t/d", 0777);
    put("/t/d/x", "x");
    a = r(open("/proc/self/exe", O_RDONLY | O_NOFOLLOW));
    b = r(rename("/t/a", "/dev/px27-probe"));
    c = r(rmdir("/t/d"));
    long d = r(mkdir("/t/d", 0777)), e = r(open("/t/d", O_WRONLY)), f = r(open("/t/a/b", O_RDONLY));
    long g = r(rename("/t/d", "/t/d/e")), h = r(rmdir("/"));
    say("errno: ELOOP: /proc/self/exe opened with O_NOFOLLOW %ld; EXDEV: a file renamed into /dev %ld; ENOTEMPTY %ld; EEXIST %ld; EISDIR %ld; ENOTDIR %ld; EINVAL %ld; EBUSY %ld\n",
        a, b, c, d, e, f, g, h);
    a = r(access("/t/a", R_OK | W_OK));
    b = r(access("/t/a", X_OK));
    c = r(access("/t/d", X_OK));
    d = r(access("/t/none", F_OK));
    e = r(access("/t/a", 8));
    f = r(faccessat(AT_FDCWD, "/t/a", R_OK, 0));
    g = r(syscall(SYS_faccessat, AT_FDCWD, "/t/a", X_OK));
    say("access: a 0644 file to read and write %ld, to execute %ld (root); a directory to execute %ld; a missing name %ld; a bad mode %ld; faccessat (glibc's, and the call itself) %ld %ld\n",
        a, b, c, d, e, f, g);
    pid_t k = fork();
    if (k == 0) {
        char *argv[] = { "/t/a", 0 };
        execve("/t/a", argv, argv + 1);
        _exit(errno);
    }
    int ws = 0;
    waitpid(k, &ws, 0);
    say("errno: EACCES: execve of a file with no execute bit %d; EBADF: write to a closed descriptor %ld\n", -WEXITSTATUS(ws),
        r(write(99, "x", 1)));
    unlink("/t/d/x"); rmdir("/t/d"); unlink("/t/a");
}

/* ---- paths: .., descriptors as directories, devices ------------------------------- */
static void paths(void) {
    struct stat a, b, c;
    mkdir("/t/p", 0777);
    put("/t/p/f", "pf");
    stat("/", &a);
    stat("/..", &b);
    stat("/t/p/../..", &c);
    long m = r(access("/t/none/../p/f", F_OK));
    long n = r(access("/t/p/f/..", F_OK));
    say("paths: /.. is / %d, /t/p/../.. is / %d; through a missing directory and back %ld; .. of a file %ld; a directory with a trailing slash %ld, with /. %ld\n",
        a.st_ino == b.st_ino && a.st_dev == b.st_dev, a.st_ino == c.st_ino, m, n, r(access("/t/p/", F_OK)), r(access("/t/p/.", F_OK)));
    stat("/t", &b);
    stat("/dev", &c);
    struct stat d;
    stat("/dev/null", &d);
    say("paths: / and /t are one file system %d and two files %d; /dev is another %d, /dev/null is on it %d\n", a.st_dev == b.st_dev,
        a.st_ino != b.st_ino, c.st_dev != a.st_dev, d.st_dev == c.st_dev);
    int dfd = open("/t/p", O_RDONLY | O_DIRECTORY);
    int fd = openat(dfd, "g", O_WRONLY | O_CREAT | O_EXCL, 0666);
    long w = r(write(fd, "pg", 2));
    close(fd);
    long mk = r(mkdirat(dfd, "sub", 0777));
    long ac = r(faccessat(dfd, "sub", F_OK, 0));
    long nd = r(openat(dfd, "f/x", O_RDONLY));
    fd = open("/t/p/f", O_RDONLY);
    long bad = r(openat(fd, "x", O_RDONLY));
    close(fd);
    const char *g = get("/t/p/g");
    say("paths: openat in a directory descriptor writes %ld ('%s'), mkdirat %ld, faccessat %ld; under a file %ld; with a file as the directory %ld\n",
        w, g, mk, ac, nd, bad);
    long fc = r(fchdir(dfd));
    char p[64];
    char *cw = getcwd(p, sizeof p);
    long un = r(unlinkat(dfd, "g", 0)), rm = r(unlinkat(dfd, "sub", AT_REMOVEDIR));
    say("paths: fchdir %ld, getcwd '%s'; unlinkat there %ld, with AT_REMOVEDIR %ld; an empty path %ld\n", fc, cw ? p : "?", un, rm,
        r(access("", F_OK)));
    chdir("/");
    close(dfd);
    /* one file, two descriptors: a truncation under a reader */
    put("/t/p/f", "0123456789");
    int rd = open("/t/p/f", O_RDONLY);
    char two[2];
    read(rd, two, 2);
    truncate("/t/p/f", 1);
    long after = r(read(rd, two, 2));
    long back = r(lseek(rd, -1, SEEK_END));
    say("paths: a reader at offset 2 of a file cut to 1 byte reads %ld; SEEK_END - 1 is %ld; lseek before the start %ld, whence 9 %ld\n",
        after, back, r(lseek(rd, -5, SEEK_SET)), r(lseek(rd, 0, 9)));
    close(rd);
    unlink("/t/p/f");
    rmdir("/t/p");
}

/* ---- a file of the initramfs: written, cut, renamed, removed; a program run ------ */
static void initram(const char *self) {
    char keep[64] = "";
    int fd = open("/etc/pax-run", O_RDWR);
    long n = r(read(fd, keep, sizeof keep - 1));
    const char *s0 = fst(fd);
    long w = r(pwrite(fd, "X", 1, 1));
    char now[64] = "";
    pread(fd, now, sizeof now - 1, 0);
    int same = n > 2 && now[0] == keep[0] && now[1] == 'X' && !strcmp(now + 2, keep + 2);
    say("initramfs: /etc/pax-run read %d, %s; one byte written in it %ld: the rest unchanged %d\n", n > 0, s0 + 12, w, same);
    long t = r(ftruncate(fd, 3));
    long g = r(ftruncate(fd, 9));
    memset(now, '?', sizeof now);
    long m = r(pread(fd, now, sizeof now, 0));
    int cutok = m == 9 && now[0] == keep[0] && now[1] == 'X' && now[2] == keep[2] && now[3] == 0 && now[8] == 0;
    say("initramfs: cut to 3 %ld and grown to 9 %ld: three bytes kept and six zeros %d\n", t, g, cutok);
    close(fd);
    long mv = r(rename("/etc/pax-run", "/etc/run2"));
    long un = r(unlink("/etc/run2"));
    fd = open("/etc/pax-run", O_WRONLY | O_CREAT | O_EXCL, 0644);
    write(fd, keep, strlen(keep));
    close(fd);
    say("initramfs: renamed %ld, removed %ld, made again with what it held '%.9s'\n", mv, un, get("/etc/pax-run"));
    /* the running program, renamed, still starts (its bytes are where
       they were); a copy of it is a new file */
    long r1 = r(rename(self, "/bin/renamed"));
    pid_t k = fork();
    if (k == 0) {
        char *argv[] = { "/bin/renamed", "noop", 0 };
        execve("/bin/renamed", argv, argv + 2);
        _exit(100 + errno);
    }
    int ws = 0;
    waitpid(k, &ws, 0);
    long r2 = r(rename("/bin/renamed", self));
    say("initramfs: the program renamed %ld, run by its new name: status %d; renamed back %ld\n", r1, WEXITSTATUS(ws), r2);
    int in = open(self, O_RDONLY);
    int out = open("/t/copy", O_WRONLY | O_CREAT, 0755);
    long total = 0, c;
    while ((c = copy_file_range(in, 0, out, 0, 1 << 30, 0)) > 0) total += c;
    struct stat a, b;
    fstat(in, &a);
    fstat(out, &b);
    close(in); close(out);
    say("initramfs: the program copied: every byte %d, %s\n", total == a.st_size && b.st_size == a.st_size, st("/t/copy") + 12 - 12);
    k = fork();
    if (k == 0) {
        char *argv[] = { "/t/copy", "noop", 0 };
        execve("/t/copy", argv, argv + 2);
        _exit(100 + errno);
    }
    ws = 0;
    waitpid(k, &ws, 0);
    say("~exec: a program copied since boot, run: status %d (7: it ran; 113: -EACCES)\n", WEXITSTATUS(ws));
    unlink("/t/copy");
}

/* ---- rename replaces at once: a reader never finds the name missing ------------- */
static void atomic(void) {
    put("/t/x", "0");
    int pp[2];
    pipe(pp);
    pid_t k = fork();
    if (k == 0) {
        struct stat s;
        int missing = 0, n = 0;
        char c;
        close(pp[1]);
        fcntl(pp[0], F_SETFL, O_NONBLOCK);
        while (read(pp[0], &c, 1) != 0) {
            if (stat("/t/x", &s) != 0) missing++;
            int fd = open("/t/x", O_RDONLY);
            if (fd < 0) missing++; else { if (read(fd, &c, 1) != 1) missing++; close(fd); }
            n++;
            if (n % 8 == 0) sched_yield();
        }
        _exit(missing ? 1 : n > 0 ? 0 : 2);
    }
    close(pp[0]);
    int bad = 0;
    for (int i = 0; i < 500; i++) {
        if (put("/t/x.new", "1") != 1) bad++;
        if (rename("/t/x.new", "/t/x") != 0) bad++;
        sched_yield();
    }
    close(pp[1]);
    int ws = 0;
    waitpid(k, &ws, 0);
    say("atomic: 500 renames over a name while another process opens it: the renames failed %d times, the reader's status %d (0: it never found the name missing or empty)\n",
        bad, WEXITSTATUS(ws));
    unlink("/t/x");
}

/* ---- times -------------------------------------------------------------------------- */
static void times(void) {
    struct stat a, b, d0, d1;
    long long t0 = wall();
    ms(30);
    put("/t/tm", "x");
    ms(30);
    long long t1 = wall();
    stat("/t/tm", &a);
    say("times: a new file's times lie between the clock before and after: mtime %d, ctime %d, atime %d; mtime is ctime %d\n",
        ns_of(a.st_mtim) >= t0 - 20000000 && ns_of(a.st_mtim) <= t1, ns_of(a.st_ctim) >= t0 - 20000000 && ns_of(a.st_ctim) <= t1,
        ns_of(a.st_atim) >= t0 - 20000000 && ns_of(a.st_atim) <= t1, ns_of(a.st_mtim) == ns_of(a.st_ctim));
    stat("/t", &d0);
    ms(30);
    int fd = open("/t/tm", O_WRONLY | O_APPEND);
    write(fd, "y", 1);
    close(fd);
    stat("/t/tm", &b);
    stat("/t", &d1);
    say("times: a write moves mtime %d and ctime %d, and leaves the directory's alone %d\n", ns_of(b.st_mtim) > ns_of(a.st_mtim),
        ns_of(b.st_ctim) > ns_of(a.st_ctim), ns_of(d1.st_mtim) == ns_of(d0.st_mtim));
    ms(30);
    get("/t/tm");
    stat("/t/tm", &a);
    ms(30);
    get("/t/tm");
    struct stat a2;
    stat("/t/tm", &a2);
    say("times: a read leaves mtime %d and ctime %d; it moves an atime that was not after them %d, and a second read does not move it again %d\n",
        ns_of(a.st_mtim) == ns_of(b.st_mtim), ns_of(a.st_ctim) == ns_of(b.st_ctim), ns_of(a.st_atim) > ns_of(b.st_atim),
        ns_of(a2.st_atim) == ns_of(a.st_atim));
    ms(30);
    rename("/t/tm", "/t/tn");
    stat("/t/tn", &b);
    stat("/t", &d0);
    say("times: a rename leaves the file's mtime %d, moves its ctime %d and the directory's mtime %d\n",
        ns_of(b.st_mtim) == ns_of(a.st_mtim), ns_of(b.st_ctim) > ns_of(a.st_ctim), ns_of(d0.st_mtim) > ns_of(d1.st_mtim));
    ms(30);
    truncate("/t/tn", 0);
    stat("/t/tn", &a);
    ms(30);
    unlink("/t/tn");
    stat("/t", &d1);
    say("times: a truncation moves mtime %d; an unlink moves the directory's mtime %d and ctime %d\n",
        ns_of(a.st_mtim) > ns_of(b.st_mtim), ns_of(d1.st_mtim) > ns_of(d0.st_mtim), ns_of(d1.st_ctim) > ns_of(d0.st_ctim));
}

/* ---- copies in the kernel --------------------------------------------------------- */
static void copies(void) {
    static char src[10000], back[10000];
    for (int i = 0; i < 10000; i++) src[i] = 'a' + i % 23;
    int in = open("/t/src", O_RDWR | O_CREAT, 0666);
    write(in, src, sizeof src);
    lseek(in, 0, SEEK_SET);
    int out = open("/t/dst", O_RDWR | O_CREAT, 0666);
    long n1 = r(copy_file_range(in, 0, out, 0, 1 << 30, 0));
    long n2 = r(copy_file_range(in, 0, out, 0, 1 << 30, 0));
    pread(out, back, sizeof back, 0);
    long a = r(lseek(in, 0, SEEK_CUR)), b = r(lseek(out, 0, SEEK_CUR));
    say("copy: copy_file_range of 10000 bytes %ld, then %ld; the same bytes %d; offsets %ld and %ld\n", n1, n2,
        memcmp(src, back, sizeof src) == 0, a, b);
    loff_t oi = 100, oo = 20000;
    long n3 = r(copy_file_range(in, &oi, out, &oo, 50, 0));
    pread(out, back, 50, 20000);
    int kept = lseek(in, 0, SEEK_CUR) == 10000 && lseek(out, 0, SEEK_CUR) == 10000;
    say("copy: with offsets %ld: they moved to %lld and %lld, the descriptors' did not %d, the bytes are the source's %d, %s\n", n3,
        (long long)oi, (long long)oo, kept, memcmp(back, src + 100, 50) == 0, fst(out) + 20);
    int ap = open("/t/dst", O_WRONLY | O_APPEND);
    int pp[2];
    pipe(pp);
    loff_t z = 0;
    a = r(copy_file_range(in, &z, ap, 0, 10, 0));
    b = r(copy_file_range(pp[0], 0, out, 0, 10, 0));
    oi = 0; oo = 5;
    long c = r(copy_file_range(in, &oi, in, &oo, 10, 0));
    oi = 0; oo = 9000;
    long d = r(copy_file_range(in, &oi, in, &oo, 10, 0));
    z = 0;
    long e = r(copy_file_range(in, &z, out, 0, 10, 1));
    int dfd = open("/t", O_RDONLY);
    long f = r(copy_file_range(dfd, 0, out, 0, 10, 0));
    close(dfd);
    say("copy: onto an O_APPEND descriptor %ld; from a pipe %ld; a file onto itself, overlapping %ld, apart %ld; with a flag %ld; from a directory %ld\n",
        a, b, c, d, e, f);
    off_t so = 0;
    lseek(out, 0, SEEK_SET);
    ftruncate(out, 0);
    long s1 = r(sendfile(out, in, &so, 1 << 20));
    const char *s2 = fst(out) + 20;
    so = 0;
    a = r(sendfile(ap, in, &so, 10));
    lseek(in, 0, SEEK_SET);
    b = r(splice(in, 0, out, 0, 10, 0));
    say("copy: sendfile file to file %ld, %s; onto an O_APPEND descriptor %ld; splice file to file %ld\n", s1, s2, a, b);
    close(in); close(out); close(ap); close(pp[0]); close(pp[1]);
    unlink("/t/src"); unlink("/t/dst");
}

/* ---- what PAX refuses by name and Linux does (not compared) ------------------------ */
static void refused(void) {
    put("/t/a", "a");
    long a = r(link("/t/a", "/t/l")), b = r(symlink("a", "/t/s")), c = r(chmod("/t/a", 0600)), d = r(chown("/t/a", 0, 0));
    long e = r(utimensat(AT_FDCWD, "/t/a", 0, 0));
    int f1 = open("/t/a", O_RDONLY | O_SYNC);
    long f = f1 < 0 ? -errno : 0;
    if (f1 >= 0) close(f1);
    int g1 = open("/t", O_TMPFILE | O_RDWR, 0600);
    long g = g1 < 0 ? -errno : 0;
    if (g1 >= 0) close(g1);
    long h = r(syscall(SYS_renameat2, AT_FDCWD, "/t/a", AT_FDCWD, "/t/b", 1));
    say("~refused: link %ld, symlink %ld, chmod %ld, chown %ld, utimensat %ld, O_SYNC %ld, O_TMPFILE %ld, RENAME_NOREPLACE %ld\n", a, b,
        c, d, e, f, g, h);
    unlink("/t/l"); unlink("/t/s"); unlink("/t/b");
    /* PAX's /dev is fixed; its largest file is 1 GiB */
    int dv = open("/dev/px27-probe", O_WRONLY | O_CREAT | O_EXCL, 0600);
    long mk = dv < 0 ? -errno : 0;
    if (dv >= 0) { close(dv); unlink("/dev/px27-probe"); }
    long md = r(mkdir("/dev/px27-probe.d", 0700));
    if (md == 0) rmdir("/dev/px27-probe.d");
    put("/t/a", "a");
    int big = open("/t/a", O_WRONLY);
    long far = r(pwrite(big, "x", 1, (off_t)1 << 30));
    long grow = r(ftruncate(big, (off_t)1 << 31));
    close(big);
    say("~limits: a file made in /dev %ld, a directory %ld; a byte written at 1 GiB %ld, a file grown to 2 GiB %ld\n", mk, md, far, grow);
    unlink("/t/a");
    mkdir("/t/d", 0777);
    a = r(link("/t/d", "/t/dl"));
    rmdir("/t/d");
    say("errno: EPERM: a hard link to a directory %ld\n", a);
}

/* ---- the soak and the fill --------------------------------------------------------- */
static char mb[1 << 20];
/* 1 MiB files /t/s/fillN until one cannot be written whole: how many
   were made, how many bytes the last one took, and the errno that
   stopped it */
static long fill(int *files, long *last) {
    char a[64];
    long err = 0;
    int n = 0;
    memset(mb, 'm', sizeof mb);
    for (; n < 4096 && err == 0; n++) {
        snprintf(a, sizeof a, "/t/s/fill%d", n);
        int fd = open(a, O_WRONLY | O_CREAT, 0666);
        if (fd < 0) { err = -errno; break; }
        long w = write(fd, mb, sizeof mb);
        if (w < 0) err = -errno;
        else if (w < (long)sizeof mb) { *last = w; err = r(write(fd, mb, sizeof mb)); }
        close(fd);
    }
    *files = n;
    return err;
}
static void empty(int files) {
    char a[64];
    for (int i = 0; i < files; i++) { snprintf(a, sizeof a, "/t/s/fill%d", i); unlink(a); }
}
static int soak(void) {
    static char block[8192], back[8192];
    char a[64], b[64];
    int bad = 0;
    for (int i = 0; i < 8192; i++) block[i] = 'A' + i % 26;
    mkdir("/t", 0777);
    mkdir("/t/s", 0777);
    char *brk0 = sbrk(0);
    for (int i = 0; i < 10000; i++) {
        snprintf(a, sizeof a, "/t/s/f%d", i % 7);
        snprintf(b, sizeof b, "/t/s/g%d", i % 5);
        int fd = open(a, O_WRONLY | O_CREAT | O_EXCL, 0666);
        if (fd < 0) { bad++; continue; }
        if (write(fd, block, sizeof block) != (ssize_t)sizeof block) bad++;
        close(fd);
        if (rename(a, b) != 0) bad++;
        if (i % 100 == 0) {
            fd = open(b, O_RDONLY);
            if (read(fd, back, sizeof back) != (ssize_t)sizeof back || memcmp(block, back, sizeof block)) bad++;
            close(fd);
        }
        if (mkdir("/t/s/d", 0777) != 0 || rmdir("/t/s/d") != 0) bad++;
        if (unlink(b) != 0) bad++;
    }
    say("soak: 10000 rounds of create, write 8192 bytes, rename, mkdir, rmdir, unlink: %d errors; /t/s: %s; the program's break moved %ld bytes\n",
        bad, st("/t/s"), (long)((char *)sbrk(0) - brk0));
    /* the fill: 1 MiB files until ENOSPC, then back */
    int files = 0;
    long last = 0;
    long err = fill(&files, &last);
    say("~fill: %d files of 1 MiB, the last one took %ld bytes\n", files, last);
    int fd = open("/t/s/after", O_WRONLY | O_CREAT, 0666);
    long full = fd >= 0 ? r(write(fd, mb, 8192)) : -errno;
    if (fd >= 0) close(fd);
    unlink("/t/s/fill0");
    fd = open("/t/s/after", O_WRONLY | O_CREAT, 0666);
    long room = r(write(fd, mb, 8192));
    close(fd);
    say("fill: stopped by %ld; 8192 more bytes then %ld; after one file is removed %ld\n", err, full, room);
    empty(files);
    unlink("/t/s/after");
    fd = open("/t/s/again", O_WRONLY | O_CREAT, 0666);
    long again = r(write(fd, mb, sizeof mb));
    close(fd);
    long u = r(unlink("/t/s/again"));
    say("fill: everything removed; a megabyte written again %ld, removed %ld\n", again, u);
    /* again with 120 MiB of the program's own memory held: on PAX the
       machine reaches the frames the tree never takes before the tree
       reaches its cap */
    size_t big = (size_t)120 << 20;
    char *held = mmap(0, big, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    int got = held != MAP_FAILED;
    for (size_t o = 0; got && o < big; o += 4096) held[o] = 1;
    files = 0;
    last = 0;
    err = fill(&files, &last);
    say("~fill: with 120 MiB held: %d files of 1 MiB, the last one took %ld bytes\n", files, last);
    char *one = mmap(0, 65536, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    int own = one != MAP_FAILED;
    for (size_t o = 0; own && o < 65536; o += 4096) one[o] = 1;
    say("fill: with 120 MiB of the program's own memory held %d: stopped by %ld; 64 KiB more of its own memory after that %d\n", got, err,
        own);
    if (own) munmap(one, 65536);
    if (got) munmap(held, big);
    empty(files);
    long d1 = r(rmdir("/t/s")), d2 = r(rmdir("/t"));
    say("fill: everything removed again: %ld %ld\n", d1, d2);
    return bad != 0;
}

static int speed(void) {
    memset(mb, 's', sizeof mb);
    mkdir("/t", 0777);
    int fd = open("/t/big", O_RDWR | O_CREAT, 0666);
    long t0 = mono_ms();
    long w = 0, g = 0, w8 = 0, g8 = 0;
    for (int i = 0; i < 16; i++) w += write(fd, mb, sizeof mb);
    long t1 = mono_ms();
    lseek(fd, 0, SEEK_SET);
    for (int i = 0; i < 16; i++) g += read(fd, mb, sizeof mb);
    long t2 = mono_ms();
    /* eight more passes over the same 16 MiB (its frames are there now) */
    for (int p = 0; p < 8; p++) {
        lseek(fd, 0, SEEK_SET);
        for (int i = 0; i < 16; i++) w8 += write(fd, mb, sizeof mb);
    }
    long t3 = mono_ms();
    for (int p = 0; p < 8; p++) {
        lseek(fd, 0, SEEK_SET);
        for (int i = 0; i < 16; i++) g8 += read(fd, mb, sizeof mb);
    }
    long t4 = mono_ms();
    say("speed: 16 MiB written %ld, read back %ld, %s; eight more passes: written %ld, read %ld\n", w, g, fst(fd) + 20, w8, g8);
    say("~speed: 16 MiB first written in %ld ms, read in %ld ms; 128 MiB rewritten in %ld ms, read in %ld ms\n", t1 - t0, t2 - t1,
        t3 - t2, t4 - t3);
    close(fd);
    long u = r(unlink("/t/big")), d = r(rmdir("/t"));
    say("speed: removed %ld %ld\n", u, d);
    return 0;
}

int main(int argc, char **argv) {
    if (argc > 1 && !strcmp(argv[1], "soak")) return soak();
    if (argc > 1 && !strcmp(argv[1], "speed")) return speed();
    if (argc > 1 && !strcmp(argv[1], "noop")) return 7;
    making();
    appending();
    holes();
    unlinked();
    workdir();
    renaming();
    directories();
    errnos();
    paths();
    initram("/bin/tree");
    atomic();
    times();
    copies();
    refused();
    say("end: rmdir /t %ld; / still has it %s\n", r(rmdir("/t")), st("/t"));
    return 0;
}
