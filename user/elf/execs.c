/* px56: what `execve` loads and how it refuses (pax#95), and `#!`
 * interpreter lines (pax#96). A program written since boot (a copy, an
 * archive file with one page rewritten in place, an archive text file
 * overwritten with a program, a copy unlinked while open and run by its
 * descriptor, a symbolic link to one); the mode rule and every refusal
 * a path can earn (ENOENT, ENOTDIR, EACCES, ENAMETOOLONG, ELOOP,
 * ENOEXEC, ETXTBSY); `#!` lines (the interpreter, its one argument, the
 * script's path appended, argv[0] dropped, blanks and tabs, a carriage
 * return, an empty line, a line past what is read, an interpreter that
 * is missing, a directory, unrunnable, text, out of reach, relative, a
 * script, a chain of them, a script that may not be read, a set-ID
 * script); `execveat` (a directory descriptor, AT_EMPTY_PATH, a
 * close-on-exec descriptor and a script, its refusals). Run as the
 * first program on a terminal (PAX's console; a Linux pseudo-terminal
 * as its session leader: notes/px52's guest and tools/linux-tree), as
 * root and as a user (through `as`), with the archive's /g/m cases
 * (tests/mpx5-jobs' execs image: their modes and owners) and /g (1777).
 *
 * Every line is `case: answer`. A program it runs is this one again (a
 * copy, or as the interpreter of a script), which prints one `run:`
 * line: its argv, AT_EXECFN, what /proc/self/exe reads, its name
 * (PR_GET_NAME), its real and effective user ids; or user/elf/seven
 * (the files of /g/m), which exits 7. No pid, inode, time or address is printed.
 *
 *   execs                 the probe, every section (F E S T X)
 *   execs time N PATH     N rounds of fork, execve(PATH, {PATH, quit}),
 *                         wait: the time they took (the lane's speed
 *                         measurement; not a suite's row)
 *   execs quit            exit 0 at once
 *   execs mark            print the marker this file was built with
 *   execs hold            print `ready`, read standard input to its end
 *   execs ANYTHING…       print the `run:` line
 *
 * Written from the man pages (execve(2) and its "Interpreter scripts"
 * paragraph and NOTES, execveat(2), fexecve(3), proc(5)'s
 * /proc/pid/exe and comm, prctl(2), getauxval(3), path_resolution(7),
 * open(2), truncate(2)) and the uapi headers' numbers. No C library's or
 * kernel's source was read. Written for this lane. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

extern char **environ;

/* The marker `mark` prints: one place in this file holds these bytes,
 * so the probe can find them in a copy of itself and rewrite them. */
static const char marker[] = "px56 marker A";

static const char *ename(int e) {
    switch (e) {
    case 0: return "0";
    case EPERM: return "EPERM"; case ENOENT: return "ENOENT"; case ESRCH: return "ESRCH"; case EINTR: return "EINTR";
    case EIO: return "EIO"; case ENXIO: return "ENXIO"; case E2BIG: return "E2BIG"; case ENOEXEC: return "ENOEXEC";
    case EBADF: return "EBADF"; case EAGAIN: return "EAGAIN"; case ENOMEM: return "ENOMEM"; case EACCES: return "EACCES";
    case EFAULT: return "EFAULT"; case EBUSY: return "EBUSY"; case EEXIST: return "EEXIST"; case ENOTDIR: return "ENOTDIR";
    case EISDIR: return "EISDIR"; case EINVAL: return "EINVAL"; case ETXTBSY: return "ETXTBSY"; case EROFS: return "EROFS";
    case ENAMETOOLONG: return "ENAMETOOLONG"; case ENOSYS: return "ENOSYS"; case ELOOP: return "ELOOP";
    case ENOTEMPTY: return "ENOTEMPTY"; case EOPNOTSUPP: return "EOPNOTSUPP";
    default: { static char b[32]; snprintf(b, sizeof b, "errno%d", e); return b; }
    }
}

/* One line, written whole. */
static void out(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void out(const char *fmt, ...) {
    char b[2048];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b - 1, fmt, ap);
    va_end(ap);
    if (n < 0) return;
    if (n > (int)sizeof b - 2) n = (int)sizeof b - 2;
    b[n++] = '\n';
    (void)!write(1, b, (size_t)n);
}

static const char *rv(long r) { return r < 0 ? ename(errno) : "0"; }

/* A string as a row shows it: quoted, a byte below 0x20 or from 0x7f
 * as \xNN, one past 40 bytes as its length. */
static void quote(char *o, size_t cap, const char *s) {
    size_t n = strlen(s), k = 0;
    if (n > 40) { snprintf(o, cap, "(%zu bytes)", n); return; }
    o[k++] = '"';
    for (size_t i = 0; i < n && k + 6 < cap; i++) {
        unsigned char c = (unsigned char)s[i];
        if (c < 0x20 || c >= 0x7f) k += (size_t)snprintf(o + k, cap - k, "\\x%02x", c);
        else o[k++] = (char)c;
    }
    o[k++] = '"';
    o[k] = 0;
}

/* ---- the program it runs ------------------------------------------------------ */

static int view(int argc, char **argv) {
    char line[4096], q[256];
    size_t k = (size_t)snprintf(line, sizeof line, "run: argc %d:", argc);
    for (int i = 0; i < argc && k < sizeof line - 300; i++) {
        quote(q, sizeof q, argv[i]);
        k += (size_t)snprintf(line + k, sizeof line - k, " %s", q);
    }
    const char *fn = (const char *)getauxval(AT_EXECFN);
    quote(q, sizeof q, fn ? fn : "(none)");
    k += (size_t)snprintf(line + k, sizeof line - k, "; execfn %s", q);
    char exe[512];
    ssize_t n = readlink("/proc/self/exe", exe, sizeof exe - 1);
    if (n < 0) snprintf(exe, sizeof exe, "%s", ename(errno));
    else exe[n] = 0;
    quote(q, sizeof q, exe);
    k += (size_t)snprintf(line + k, sizeof line - k, "; exe %s", q);
    char nm[17] = {0};
    if (prctl(PR_GET_NAME, nm, 0, 0, 0) != 0) snprintf(nm, sizeof nm, "%s", ename(errno));
    quote(q, sizeof q, nm);
    snprintf(line + k, sizeof line - k, "; name %s; ids %u/%u", q, (unsigned)getuid(), (unsigned)geteuid());
    out("%s", line);
    return 0;
}

static int hold(void) {
    out("ready");
    char b[64];
    while (read(0, b, sizeof b) > 0) {}
    return 0;
}

static long long now_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static int timing(int argc, char **argv) {
    if (argc < 4) { out("usage: execs time N PATH"); return 2; }
    int n = atoi(argv[2]);
    char *av[] = { argv[3], "quit", NULL };
    long long t0 = now_ms();
    int bad = 0;
    for (int i = 0; i < n; i++) {
        pid_t p = fork();
        if (p == 0) {
            execve(argv[3], av, environ);
            _exit(100);
        }
        int ws = 0;
        waitpid(p, &ws, 0);
        if (!WIFEXITED(ws) || WEXITSTATUS(ws) != 0) bad++;
    }
    long long t = now_ms() - t0;
    out("time: %d runs of %s: %lld ms, %lld.%03lld ms a run, %d not exit 0", n, argv[3], t, n ? t / n : 0,
        n ? (t * 1000 / n) % 1000 : 0, bad);
    return 0;
}

/* ---- the files it makes --------------------------------------------------------- */

static char W[64]; /* its work directory: /g/w<uid> */

static const char *in(const char *name) {
    static char p[8][160];
    static int k;
    k = (k + 1) & 7;
    snprintf(p[k], sizeof p[k], "%s/%s", W, name);
    return p[k];
}

static void wfile(const char *path, const void *b, size_t n, mode_t m) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (fd < 0) { out("! write %s: %s", path, ename(errno)); return; }
    if (n && write(fd, b, n) != (ssize_t)n) out("! write %s: short", path);
    if (fchmod(fd, m) != 0) out("! fchmod %s: %s", path, ename(errno));
    close(fd);
}

static void script(const char *name, const char *text) { wfile(in(name), text, strlen(text), 0755); }

static void copyf(const char *src, const char *dst, mode_t m) {
    int a = open(src, O_RDONLY | O_CLOEXEC);
    int b = open(dst, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (a < 0 || b < 0) { out("! copy %s %s: %s", src, dst, ename(errno)); if (a >= 0) close(a); if (b >= 0) close(b); return; }
    char buf[65536];
    ssize_t r;
    while ((r = read(a, buf, sizeof buf)) > 0) {
        if (write(b, buf, (size_t)r) != r) { out("! copy %s: short write", dst); break; }
    }
    if (fchmod(b, m) != 0) out("! fchmod %s: %s", dst, ename(errno));
    close(a);
    close(b);
}

/* ---- running a program and saying what came of it ----------------------------- */

struct job {
    const char *path;   /* execve's path, or execveat's */
    char **argv;
    int at;             /* 1: execveat(dirfd, path, …, flags) */
    int dirfd;
    int flags;
    const char *cwd;    /* the child's working directory first, when set */
};

static char *A0[] = { "zero", "a1", "a2", NULL };

/* Run `j` in a child whose standard output is a pipe; the row is what
 * came back: the program's lines (joined with ` / `), and its end when
 * that is not exit 0 (`exit N`, `signal N`), or the errno the call was
 * refused with. */
static void go(const char *label, struct job j) {
    int p[2];
    if (pipe2(p, O_CLOEXEC) != 0) { out("%s: ! pipe %s", label, ename(errno)); return; }
    pid_t k = fork();
    if (k == 0) {
        dup2(p[1], 1);
        if (j.cwd && chdir(j.cwd) != 0) { out("errno chdir %s", ename(errno)); _exit(101); }
        if (j.at) syscall(SYS_execveat, j.dirfd, j.path, j.argv, environ, j.flags);
        else execve(j.path, j.argv, environ);
        out("errno %s", ename(errno));
        _exit(100);
    }
    close(p[1]);
    char buf[8192];
    size_t n = 0;
    ssize_t r;
    while (n < sizeof buf - 1 && (r = read(p[0], buf + n, sizeof buf - 1 - n)) > 0) n += (size_t)r;
    close(p[0]);
    buf[n] = 0;
    while (n > 0 && buf[n - 1] == '\n') buf[--n] = 0;
    for (size_t i = 0; i < n; i++) if (buf[i] == '\n') buf[i] = '/';
    int ws = 0;
    waitpid(k, &ws, 0);
    char end[32] = "";
    if (WIFEXITED(ws) && WEXITSTATUS(ws) != 0 && WEXITSTATUS(ws) != 100) snprintf(end, sizeof end, "exit %d", WEXITSTATUS(ws));
    if (WIFSIGNALED(ws)) snprintf(end, sizeof end, "signal %d", WTERMSIG(ws));
    if (n && *end) out("%s: %s (%s)", label, buf, end);
    else if (n) out("%s: %s", label, buf);
    else out("%s: %s", label, *end ? end : "exit 0, nothing printed");
}

static void ex(const char *label, const char *path, char **argv) {
    go(label, (struct job){ path, argv, 0, 0, 0, NULL });
}

/* ---- F: what loads ---------------------------------------------------------------- */

static void find_marker(const char *path, off_t *at) {
    *at = -1;
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) return;
    static char buf[1 << 20];
    off_t base = 0;
    size_t keep = 0, ml = sizeof marker - 1;
    char m[sizeof marker];
    const volatile char *mv = marker;
    for (size_t i = 0; i < sizeof marker; i++) m[i] = mv[i];
    ssize_t r;
    while ((r = read(fd, buf + keep, sizeof buf - keep)) > 0) {
        size_t n = keep + (size_t)r;
        for (size_t i = 0; i + ml <= n; i++) {
            if (memcmp(buf + i, m, ml) == 0) { *at = base + (off_t)i; close(fd); return; }
        }
        keep = ml - 1 < n ? ml - 1 : n;
        memmove(buf, buf + n - keep, keep);
        base += (off_t)(n - keep);
    }
    close(fd);
}

static void loads(void) {
    char *say[] = { "execs", "say", NULL };
    ex("F: the archive's /bin/execs", "/bin/execs", say);
    copyf("/bin/execs", in("copy"), 0755);
    char *c1[] = { "copy", "one", "two", NULL };
    ex("F: a copy written since boot (read, write, 0755)", in("copy"), c1);
    char *c2[] = { "./copy", "rel", NULL };
    go("F: the copy by a relative path from its directory", (struct job){ "./copy", c2, 0, 0, 0, W });
    copyf("/bin/execs", in("a-name-longer-than-fifteen"), 0755);
    char *c3[] = { "long", "x", NULL };
    ex("F: a copy whose name is longer than 15 bytes", in("a-name-longer-than-fifteen"), c3);
    /* an archive ELF, one page rewritten in place */
    char rw[64];
    snprintf(rw, sizeof rw, "/g/m/rw%u", (unsigned)getuid());
    char *mk[] = { "rw", "mark", NULL };
    ex("F: an archive copy of the probe, as it is", rw, mk);
    off_t at;
    find_marker(rw, &at);
    char b[sizeof marker];
    const volatile char *mv = marker;
    for (size_t i = 0; i < sizeof marker; i++) b[i] = mv[i];
    b[sizeof marker - 2] = 'B';
    int fd = open(rw, O_WRONLY | O_CLOEXEC);
    long w = fd < 0 ? -1 : (long)pwrite(fd, b, sizeof marker - 1, at);
    int e = errno;
    if (fd >= 0) close(fd);
    errno = e;
    out("F: its marker found: %s; rewritten in place by pwrite: %s", at >= 0 ? "yes" : "no", w == (long)(sizeof marker - 1) ? "0" : rv(w));
    ex("F: the archive copy with that page rewritten", rw, mk);
    /* an archive text file overwritten with the probe */
    char tx[64];
    snprintf(tx, sizeof tx, "/g/m/tx%u", (unsigned)getuid());
    char *t1[] = { "tx", "t", NULL };
    ex("F: an archive text file (0755), as it is", tx, t1);
    copyf("/bin/execs", tx, 0755);
    ex("F: that file overwritten (O_TRUNC) with the probe", tx, t1);
    /* unlinked while open */
    copyf("/bin/execs", in("gone"), 0755);
    int g = open(in("gone"), O_RDONLY);
    if (g >= 0 && g != 9) { dup2(g, 9); close(g); g = 9; }
    out("F: a copy opened (descriptor 9) and unlinked: %s", rv(unlink(in("gone"))));
    char *u1[] = { "fd", "u", NULL };
    ex("F: run by /proc/self/fd/9", "/proc/self/fd/9", u1);
    go("F: run by execveat(9, \"\", AT_EMPTY_PATH)", (struct job){ "", u1, 1, 9, AT_EMPTY_PATH, NULL });
    close(9);
    /* a symbolic link */
    out("F: a link to the copy: %s", rv(symlink(in("copy"), in("link"))));
    char *l1[] = { "link", "l", NULL };
    ex("F: run by the link", in("link"), l1);
}

/* ---- E: the refusals ---------------------------------------------------------------- */

static void refusals(void) {
    char *s[] = { "x", NULL };
    ex("E: a missing file", in("nosuch"), s);
    ex("E: a missing directory on the way", "/g/nosuchdir/x", s);
    ex("E: a file on the way", "/g/m/r0744/x", s);
    ex("E: an empty path", "", s);
    char longp[300];
    memset(longp, 'n', 256);
    longp[256] = 0;
    char lp[320];
    snprintf(lp, sizeof lp, "/g/%s", longp);
    ex("E: a component of 256 bytes", lp, s);
    symlink(in("loop2"), in("loop1"));
    symlink(in("loop1"), in("loop2"));
    ex("E: a loop of links", in("loop1"), s);
    ex("E: a directory", "/g/m/d0755", s);
    ex("E: /dev/null", "/dev/null", s);
    ex("E: a 0644 file", "/g/m/n0644", s);
    ex("E: root's 0744 file", "/g/m/r0744", s);
    ex("E: root's 0701 file (execute, no read)", "/g/m/r0701", s);
    ex("E: 0:1000's 0710 file", "/g/m/g0710", s);
    ex("E: a 0755 file in root's 0700 directory", "/g/m/ns/prog", s);
    ex("E: a 0755 text file with no #!", "/g/m/text", s);
    ex("E: an empty 0755 file", "/g/m/empty", s);
    ex("E: a 0755 file of \\x7fELF alone", "/g/m/elf4", s);
}

/* ---- S: #! lines -------------------------------------------------------------------- */

static void shebangs(void) {
    script("s1", "#!/bin/execs say\nbody\n");
    ex("S: #!/bin/execs say, run with argv zero a1 a2", in("s1"), A0);
    script("s2", "#!/bin/execs\n");
    ex("S: #!/bin/execs (no argument)", in("s2"), A0);
    script("s3", "#!  /bin/execs   one two  \t \n");
    ex("S: blanks after #!, around and inside the argument", in("s3"), A0);
    script("s4", "#!\t/bin/execs\tx\ty\n");
    ex("S: tabs", in("s4"), A0);
    script("s5", "#!/bin/execs a");
    ex("S: no newline at the end", in("s5"), A0);
    script("s6", "#!/bin/execs\r\n");
    ex("S: a carriage return after the interpreter", in("s6"), A0);
    script("s7", "#!/bin/execs x\r\n");
    ex("S: a carriage return after the argument", in("s7"), A0);
    script("s8", "#!\n");
    ex("S: #! and a newline", in("s8"), A0);
    script("s9", "#!   \t \n");
    ex("S: #! and blanks", in("s9"), A0);
    script("s10", "#!");
    ex("S: #! alone", in("s10"), A0);
    script("s17", "#!   ");
    ex("S: #! and blanks, no newline", in("s17"), A0);
    {
        char t1[300];
        memcpy(t1, "#!", 2);
        memset(t1 + 2, ' ', 298);
        wfile(in("s18"), t1, 300, 0755);
        ex("S: #! and 298 blanks, no newline", in("s18"), A0);
        memcpy(t1, "#!/bin/execs", 12);
        wfile(in("s19"), t1, 300, 0755);
        ex("S: #!/bin/execs and 288 blanks, no newline", in("s19"), A0);
    }
    wfile(in("s20"), "#!/bin/execs a\0b\n", sizeof "#!/bin/execs a\0b\n" - 1, 0755);
    ex("S: a NUL inside the argument", in("s20"), A0);
    wfile(in("s21"), "#!/bin/ex\0ecs say\n", sizeof "#!/bin/ex\0ecs say\n" - 1, 0755);
    ex("S: a NUL inside the interpreter", in("s21"), A0);
    wfile(in("s22"), "#!/bin/execs \0b\n", sizeof "#!/bin/execs \0b\n" - 1, 0755);
    ex("S: a NUL where the argument starts", in("s22"), A0);
    script("s11", "#!/g/nosuch\n");
    ex("S: an interpreter that is missing", in("s11"), A0);
    script("s12", "#!/g/m/d0755\n");
    ex("S: an interpreter that is a directory", in("s12"), A0);
    script("s13", "#!/g/m/n0644\n");
    ex("S: an interpreter with no execute bit", in("s13"), A0);
    script("s14", "#!/g/m/text\n");
    ex("S: an interpreter that is text with no #!", in("s14"), A0);
    script("s15", "#!/g/m/ni/execs say\n");
    ex("S: an interpreter in root's 0700 directory", in("s15"), A0);
    script("s16", "#!execs rel\n");
    go("S: a relative interpreter, from /bin", (struct job){ in("s16"), A0, 0, 0, 0, "/bin" });
    go("S: a relative interpreter, from /", (struct job){ in("s16"), A0, 0, 0, 0, "/" });
    ex("S: root's 0711 script", "/g/m/s0711", A0);
    ex("S: a 0644 script", "/g/m/s0644", A0);
    ex("S: root's 04755 script", "/g/m/suid", A0);
    /* lines past what is read: an argument cut, an interpreter cut, and
       the interpreter's end at bytes 252 to 257 of the line */
    char t[600];
    int k = snprintf(t, sizeof t, "#!/bin/execs ");
    while (k < 400) t[k++] = 'a';
    t[k++] = '\n';
    wfile(in("l1"), t, (size_t)k, 0755);
    ex("S: an argument that runs past byte 400", in("l1"), A0);
    for (int end = 252; end <= 258; end++) {
        /* `#!/bin` then slashes, then `/execs` ending at byte `end`, then a newline */
        k = snprintf(t, sizeof t, "#!/bin");
        while (k < end - 6) t[k++] = '/';
        memcpy(t + k, "/execs", 6);
        k += 6;
        t[k++] = '\n';
        wfile(in("l2"), t, (size_t)k, 0755);
        char lab[96];
        snprintf(lab, sizeof lab, "S: an interpreter whose name ends at byte %d, then a newline", end);
        ex(lab, in("l2"), A0);
    }
    for (int end = 252; end <= 258; end++) {
        /* `#!/bin/execs ` then an argument of `b`s ending at byte `end`, then a newline */
        k = snprintf(t, sizeof t, "#!/bin/execs ");
        while (k < end) t[k++] = 'b';
        t[k++] = '\n';
        wfile(in("l3"), t, (size_t)k, 0755);
        char lab[96];
        snprintf(lab, sizeof lab, "S: an argument that ends at byte %d, then a newline", end);
        ex(lab, in("l3"), A0);
    }
    /* a chain: c1's interpreter is the probe, ck's is c(k-1) */
    script("c1", "#!/bin/execs say\n");
    for (int c = 2; c <= 7; c++) {
        char nm[8], txt[200];
        snprintf(nm, sizeof nm, "c%d", c);
        snprintf(txt, sizeof txt, "#!%s/c%d arg%d\n", W, c - 1, c);
        script(nm, txt);
    }
    for (int c = 1; c <= 7; c++) {
        char nm[8], lab[64];
        snprintf(nm, sizeof nm, "c%d", c);
        snprintf(lab, sizeof lab, "S: a chain of %d script%s", c, c == 1 ? "" : "s");
        char *av[] = { "zero", "z", NULL };
        ex(lab, in(nm), av);
    }
    /* execveat and scripts */
    int d = open(W, O_RDONLY | O_DIRECTORY);
    if (d >= 0 && d != 8) { dup2(d, 8); close(d); }
    go("S: execveat(dirfd 8, \"s1\")", (struct job){ "s1", A0, 1, 8, 0, NULL });
    int f = open(in("s1"), O_RDONLY);
    if (f >= 0 && f != 9) { dup2(f, 9); close(f); }
    go("S: execveat(9, \"\", AT_EMPTY_PATH) of s1", (struct job){ "", A0, 1, 9, AT_EMPTY_PATH, NULL });
    fcntl(9, F_SETFD, FD_CLOEXEC);
    go("S: the same, descriptor 9 close-on-exec", (struct job){ "", A0, 1, 9, AT_EMPTY_PATH, NULL });
    fcntl(8, F_SETFD, FD_CLOEXEC);
    go("S: execveat(dirfd 8, \"s1\"), dirfd close-on-exec", (struct job){ "s1", A0, 1, 8, 0, NULL });
    char *e1[] = { "seven", NULL };
    go("S: execveat(dirfd 8, \"../m/r0744\"), an ELF, dirfd close-on-exec", (struct job){ "../m/r0744", e1, 1, 8, 0, NULL });
    close(8);
    close(9);
}

/* ---- T: a file being written, a program running ---------------------------------- */

/* A child running `path hold` (or a script whose interpreter holds):
 * its pid, its stdin's write end (*w), its stdout's read end (*r), once
 * it has said `ready`. */
static pid_t holder(const char *path, int *w, int *r) {
    int i[2], o[2];
    if (pipe2(i, O_CLOEXEC) != 0 || pipe2(o, O_CLOEXEC) != 0) return -1;
    pid_t k = fork();
    if (k == 0) {
        dup2(i[0], 0);
        dup2(o[1], 1);
        char *av[] = { "held", "hold", NULL };
        execve(path, av, environ);
        out("errno %s", ename(errno));
        _exit(100);
    }
    close(i[0]);
    close(o[1]);
    char b[64];
    ssize_t n = read(o[0], b, sizeof b - 1);
    b[n > 0 ? n : 0] = 0;
    if (strncmp(b, "ready", 5) != 0) out("T: ! the holder said '%s'", b);
    *w = i[1];
    *r = o[0];
    return k;
}

static void finish(pid_t k, int w, int r) {
    close(w);
    char b[64];
    while (read(r, b, sizeof b) > 0) {}
    close(r);
    int ws = 0;
    waitpid(k, &ws, 0);
    if (!WIFEXITED(ws) || WEXITSTATUS(ws) != 0) out("T: ! the holder ended %#x", ws);
}

static void busy(void) {
    copyf("/bin/execs", in("busy"), 0755);
    int fd = open(in("busy"), O_WRONLY);
    char *s[] = { "busy", "b", NULL };
    ex("T: a copy the probe holds open for writing", in("busy"), s);
    close(fd);
    ex("T: the same once closed", in("busy"), s);
    int w, r;
    pid_t k = holder(in("busy"), &w, &r);
    int o1 = open(in("busy"), O_WRONLY);
    out("T: while a process runs it: open O_WRONLY %s", o1 < 0 ? ename(errno) : "0");
    if (o1 >= 0) close(o1);
    int o2 = open(in("busy"), O_RDWR);
    out("T: open O_RDWR %s", o2 < 0 ? ename(errno) : "0");
    if (o2 >= 0) close(o2);
    int o3 = open(in("busy"), O_RDONLY);
    out("T: open O_RDONLY %s", o3 < 0 ? ename(errno) : "0");
    if (o3 >= 0) close(o3);
    out("T: truncate to 0 %s", rv(truncate(in("busy"), 0)));
    out("T: unlink %s", rv(unlink(in("busy"))));
    finish(k, w, r);
    /* scripts */
    copyf("/bin/execs", in("interp"), 0755);
    char txt[200];
    snprintf(txt, sizeof txt, "#!%s\n", in("interp"));
    script("sbusy", txt);
    fd = open(in("sbusy"), O_WRONLY);
    ex("T: a script the probe holds open for writing", in("sbusy"), A0);
    close(fd);
    fd = open(in("interp"), O_WRONLY);
    ex("T: a script whose interpreter the probe holds open for writing", in("sbusy"), A0);
    close(fd);
    snprintf(txt, sizeof txt, "#!%s hold\n", in("interp"));
    script("shold", txt);
    k = holder(in("shold"), &w, &r);
    o1 = open(in("shold"), O_WRONLY);
    out("T: while a script runs: the script open O_WRONLY %s", o1 < 0 ? ename(errno) : "0");
    if (o1 >= 0) close(o1);
    o2 = open(in("interp"), O_WRONLY);
    out("T: its interpreter open O_WRONLY %s", o2 < 0 ? ename(errno) : "0");
    if (o2 >= 0) close(o2);
    finish(k, w, r);
}

/* ---- X: execveat's own answers ---------------------------------------------------- */

static void ats(void) {
    char *s[] = { "x", "y", NULL };
    go("X: execveat(AT_FDCWD, the copy's absolute path, 0)", (struct job){ in("copy"), s, 1, AT_FDCWD, 0, NULL });
    int d = open("/g/m", O_RDONLY | O_DIRECTORY);
    if (d >= 0 && d != 8) { dup2(d, 8); close(d); }
    go("X: execveat(dirfd /g/m, \"r0744\", 0)", (struct job){ "r0744", s, 1, 8, 0, NULL });
    go("X: execveat(dirfd /g/m, an absolute path, 0)", (struct job){ in("copy"), s, 1, 8, 0, NULL });
    go("X: execveat with flag 0x1", (struct job){ in("copy"), s, 1, AT_FDCWD, 0x1, NULL });
    go("X: execveat(AT_SYMLINK_NOFOLLOW) of a link", (struct job){ in("link"), s, 1, AT_FDCWD, AT_SYMLINK_NOFOLLOW, NULL });
    go("X: execveat(AT_SYMLINK_NOFOLLOW) of the copy", (struct job){ in("copy"), s, 1, AT_FDCWD, AT_SYMLINK_NOFOLLOW, NULL });
    int f = open(in("copy"), O_RDONLY);
    if (f >= 0 && f != 9) { dup2(f, 9); close(f); }
    go("X: execveat(a file's descriptor, \"x\", 0)", (struct job){ "x", s, 1, 9, 0, NULL });
    go("X: execveat(a file's descriptor, \"\", 0)", (struct job){ "", s, 1, 9, 0, NULL });
    close(9);
    go("X: execveat(a closed descriptor, \"x\", 0)", (struct job){ "x", s, 1, 9, 0, NULL });
    go("X: execveat(a closed descriptor, \"\", AT_EMPTY_PATH)", (struct job){ "", s, 1, 9, AT_EMPTY_PATH, NULL });
    close(8);
}

static void clean(void) {
    const char *names[] = { "copy", "a-name-longer-than-fifteen", "link", "loop1", "loop2", "s1", "s2", "s3", "s4", "s5",
        "s6", "s7", "s8", "s9", "s10", "s11", "s12", "s13", "s14", "s15", "s16", "s17", "s18", "s19", "s20", "s21", "s22", "l1", "l2", "l3", "c1", "c2", "c3", "c4",
        "c5", "c6", "c7", "interp", "sbusy", "shold", NULL };
    for (int i = 0; names[i]; i++) unlink(in(names[i]));
    out("end: the work directory removed: %s", rv(rmdir(W)));
}

int main(int argc, char **argv) {
    if (argc >= 2) {
        if (strcmp(argv[1], "quit") == 0) return 0;
        if (strcmp(argv[1], "hold") == 0) return hold();
        if (strcmp(argv[1], "time") == 0) return timing(argc, argv);
        if (strcmp(argv[1], "mark") == 0) { out("run: marker \"%s\"", marker); return 0; }
        return view(argc, argv);
    }
    umask(022);
    out("execs: px56's probe, as %s", getuid() == 0 ? "root" : "a user");
    snprintf(W, sizeof W, "/g/w%u", (unsigned)getuid());
    out("start: its work directory %s made: %s", getuid() == 0 ? "/g/w0" : "/g/w<uid>", rv(mkdir(W, 0755)));
    loads();
    refusals();
    shebangs();
    busy();
    ats();
    clean();
    return 0;
}
