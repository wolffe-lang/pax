/* lspc.c — px99's Language Server Protocol client: it starts a server
   as a child on three pipes, types a recorded session at it, and writes
   every frame both ways to its own standard output, one line a frame.
   tests/mpx5-lsp runs it against /usr/bin/wolf's `lsp` on PAX and against
   the same binaries on Linux, and holds the two outputs byte for byte.

     lspc SESSION        run SESSION (below); exit 0 when it ran to its
                         end, 3 when a wait's deadline passed or the
                         server's output ended first, 4 when a `quiet`
                         wait saw its text, 2 on a usage or tool error

   The server is started the way an editor's client starts one (sagitta,
   the C editor yew ports, src/edit/job.c): three pipes for its standard
   input, output and error and a fourth, close-on-exec, on which the child
   reports a failed execve; `fork`; in the child `setpgid(0, 0)`, `chdir`,
   the three `dup2`s and `execve`; in the parent the pipes' read ends made
   non-blocking. SIGCHLD reaches a handler that writes a byte to a
   non-blocking self-pipe, and every wait is one `poll` over the terminal
   (descriptor 0), the server's output, its error and the self-pipe, with
   a deadline from CLOCK_MONOTONIC. A killed server is killed by its
   process group.

   SESSION is a file of lines, `#` lines and empty lines skipped:
     name NAME             the session's name, printed at its start and end
     cwd DIR               the server's working directory
     env NAME=VALUE        added to (or replacing in) the server's environment,
                           which is otherwise this program's
     argv PROG ARG...      the server: PROG is the path execve is given
     deadline MS           the deadline of each later wait (default 600000)
     send BODY             one frame: `Content-Length: N` CR LF CR LF BODY,
                           in one write to the server's input
     wait LABEL TEXT       read frames until one whose body holds TEXT
     quiet LABEL MS TEXT   read frames for MS milliseconds; TEXT should not come
     close                 close the server's input
     kill                  kill the server's process group with SIGKILL
     reap                  wait for the server's output and error to end and
                           its SIGCHLD, then reap it; its input stays open
     end                   close the server's input, then `reap`
   `close`, `kill`, `reap` and `end` start the server first if no `send` has.
   SIGPIPE is ignored, as an editor ignores it: a write to a server that has
   gone answers EPIPE, which the `send` prints.

   What it prints, each line in one write:
     lspc: begin NAME
     spawn: PROG ARG... (cwd DIR)
     exec: ok | exec: failed errno N
     c2s N BODY            a frame it sent (N the body's bytes)
     s2c N BODY            a frame it read
     s2c-header TEXT       a header that is not exactly `Content-Length: N`
     stderr: LINE          a line of the server's standard error
     deadline: LABEL not seen within MS ms
     came: LABEL           (a `quiet` wait's text came)
     eof: the server's output ended before LABEL
     kill: the server's process group, SIGKILL: R
     lspc: write to the server failed R
     exit: status N | exit: signal N
     sigchld: N            the bytes the SIGCHLD handler wrote
     tty: N bytes          what was read from descriptor 0 meanwhile
     time: LABEL N us      from the last send to the wait's frame, or for
                           `exit` from close or kill to the reap: the only
                           lines that are not the same on two machines
     lspc: end NAME status S

   No libc: the calls are made with `syscall` (the psABI's A.2.1, the
   numbers from arch/x86/entry/syscalls/syscall_64.tbl, the layouts from
   the uapi headers: asm/signal.h, linux/time.h, asm-generic/poll.h,
   asm-generic/fcntl.h). Written from the LSP 3.17 specification's base
   protocol and the man pages (pipe(2), fork(2), execve(2), poll(2),
   wait4(2), setpgid(2), kill(2), sigaction(2)). No libc's, kernel's,
   editor's or LSP library's source was read. Built by tools/mklspc with
   -nostdlib -ffreestanding, static, no PIE. */

typedef unsigned long u64;
typedef long i64;
typedef unsigned int u32;
typedef unsigned char u8;

#define SYS_read 0
#define SYS_write 1
#define SYS_close 3
#define SYS_poll 7
#define SYS_rt_sigaction 13
#define SYS_dup2 33
#define SYS_fork 57
#define SYS_execve 59
#define SYS_wait4 61
#define SYS_kill 62
#define SYS_fcntl 72
#define SYS_chdir 80
#define SYS_setpgid 109
#define SYS_clock_gettime 228
#define SYS_exit_group 231
#define SYS_openat 257
#define SYS_pipe2 293

#define AT_FDCWD (-100)
#define O_RDONLY 0
#define O_NONBLOCK 0x800
#define O_CLOEXEC 0x80000
#define F_GETFL 3
#define F_SETFL 4
#define POLLIN 0x1
#define POLLERR 0x8
#define POLLHUP 0x10
#define POLLNVAL 0x20
#define SIGKILL 9
#define SIGPIPE 13
#define SIGCHLD 17
#define SA_NOCLDSTOP 0x1
#define SA_RESTORER 0x04000000
#define CLOCK_MONOTONIC 1
#define EINTR 4
#define EAGAIN 11

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
    u8 *p = d;
    while (n--) *p++ = (u8)c;
    return d;
}

void *memcpy(void *d, const void *s, u64 n) {
    u8 *p = d;
    const u8 *q = s;
    while (n--) *p++ = *q++;
    return d;
}

static u64 slen(const char *s) {
    u64 n = 0;
    while (s[n]) n++;
    return n;
}

static int sprefix(const char *s, const char *p) {
    while (*p)
        if (*s++ != *p++) return 0;
    return 1;
}

/* Whether the n bytes at h hold the string t. */
static int holds(const u8 *h, u64 n, const char *t) {
    u64 m = slen(t);
    if (m == 0) return 1;
    for (u64 i = 0; i + m <= n; i++) {
        u64 k = 0;
        while (k < m && h[i + k] == (u8)t[k]) k++;
        if (k == m) return 1;
    }
    return 0;
}

static void quit(int code) {
    sys(SYS_exit_group, code, 0, 0);
    for (;;) {}
}

/* ---- output: one line, one write ------------------------------------------ */

static char ob[1 << 18];
static u64 on;
static int ocut;

static void o_n(const void *p, u64 n) {
    const u8 *q = p;
    for (u64 i = 0; i < n; i++) {
        if (on >= sizeof ob - 16) { ocut = 1; return; }
        ob[on++] = (char)q[i];
    }
}
static void o_s(const char *s) { o_n(s, slen(s)); }
static void o_u(u64 v) {
    char b[24];
    int k = 0;
    do { b[k++] = (char)('0' + v % 10); v /= 10; } while (v);
    while (k) { char c = b[--k]; o_n(&c, 1); }
}
static void o_i(i64 v) {
    if (v < 0) { o_s("-"); o_u((u64)-v); } else o_u((u64)v);
}
static void o_end(void) {
    if (ocut) {
        const char *c = " (cut)";
        while (*c) ob[on++] = *c++;
        ocut = 0;
    }
    ob[on++] = '\n';
    u64 at = 0;
    while (at < on) {
        i64 r = sys(SYS_write, 1, ob + at, on - at);
        if (r == -EINTR) continue;
        if (r <= 0) break;
        at += (u64)r;
    }
    on = 0;
}

static u64 now_us(void) {
    i64 ts[2] = { 0, 0 };
    sys(SYS_clock_gettime, CLOCK_MONOTONIC, ts, 0);
    return (u64)ts[0] * 1000000 + (u64)ts[1] / 1000;
}

/* ---- SIGCHLD through a self-pipe ------------------------------------------ */

static volatile int sig_w = -1;
static int sig_r = -1;

static void on_chld(int sig) {
    (void)sig;
    u8 b = 'c';
    sys(SYS_write, sig_w, &b, 1);
}

void lspc_restorer(void);
__asm__(".globl lspc_restorer\n"
        "lspc_restorer:\n"
        "  movq $15, %rax\n"
        "  syscall\n"
        "  hlt\n");

/* ---- the session file ------------------------------------------------------- */

static char sess[1 << 16];
static char *lines[512];
static int nlines;

static int load(const char *path) {
    i64 fd = sys6(SYS_openat, AT_FDCWD, (i64)path, O_RDONLY | O_CLOEXEC, 0, 0);
    if (fd < 0) return 0;
    u64 n = 0;
    for (;;) {
        i64 r = sys(SYS_read, fd, sess + n, sizeof sess - 1 - n);
        if (r == -EINTR) continue;
        if (r < 0) return 0;
        if (r == 0) break;
        n += (u64)r;
        if (n >= sizeof sess - 1) return 0;
    }
    sys(SYS_close, fd, 0, 0);
    sess[n] = 0;
    char *p = sess;
    while (*p && nlines < (int)(sizeof lines / sizeof lines[0])) {
        char *e = p;
        while (*e && *e != '\n') e++;
        int more = *e == '\n';
        *e = 0;
        if (*p && *p != '#') lines[nlines++] = p;
        if (!more) break;
        p = e + 1;
    }
    return 1;
}

/* The word after a directive: s past `word `. */
static char *arg(char *s) {
    while (*s && *s != ' ') s++;
    while (*s == ' ') s++;
    return s;
}

static u64 num(const char *s) {
    u64 v = 0;
    while (*s >= '0' && *s <= '9') v = v * 10 + (u64)(*s++ - '0');
    return v;
}

/* ---- the server ------------------------------------------------------------- */

static char *senv[96];
static int nsenv;
static char *sargv[17];
static char *cwd;
static i64 child = -1;
static int fd_in = -1, fd_out = -1, fd_err = -1;
static u64 nsig, ntty, t_last;
static int started, reaped, rc;

static void setenv_(char *kv) {
    u64 k = 0;
    while (kv[k] && kv[k] != '=') k++;
    for (int i = 0; i < nsenv; i++) {
        u64 j = 0;
        while (j < k && senv[i][j] == kv[j]) j++;
        if (j == k && senv[i][k] == '=') { senv[i] = kv; return; }
    }
    if (nsenv < (int)(sizeof senv / sizeof senv[0]) - 1) senv[nsenv++] = kv;
}

static void spawn(void) {
    int pin[2], pout[2], perr[2], pex[2];
    started = 1;
    o_s("spawn:");
    for (int i = 0; sargv[i]; i++) { o_s(" "); o_s(sargv[i]); }
    o_s(" (cwd "); o_s(cwd ? cwd : "."); o_s(")");
    o_end();
    if (sys(SYS_pipe2, pin, O_CLOEXEC, 0) < 0 || sys(SYS_pipe2, pout, O_CLOEXEC, 0) < 0 ||
        sys(SYS_pipe2, perr, O_CLOEXEC, 0) < 0 || sys(SYS_pipe2, pex, O_CLOEXEC, 0) < 0) {
        o_s("lspc: pipe2 failed"); o_end(); quit(2);
    }
    child = sys(SYS_fork, 0, 0, 0);
    if (child < 0) { o_s("lspc: fork failed "); o_i(child); o_end(); quit(2); }
    if (child == 0) {
        i64 r = sys(SYS_setpgid, 0, 0, 0);
        if (r == 0 && cwd) r = sys(SYS_chdir, cwd, 0, 0);
        if (r == 0) r = sys(SYS_dup2, pin[0], 0, 0);
        if (r == 0) r = sys(SYS_dup2, pout[1], 1, 0) == 1 ? 0 : -1;
        if (r == 0) r = sys(SYS_dup2, perr[1], 2, 0) == 2 ? 0 : -1;
        if (r == 0) r = sys(SYS_execve, sargv[0], sargv, senv);
        u32 e = (u32)-r;
        sys(SYS_write, pex[1], &e, 4);
        quit(127);
    }
    sys(SYS_close, pin[0], 0, 0);
    sys(SYS_close, pout[1], 0, 0);
    sys(SYS_close, perr[1], 0, 0);
    sys(SYS_close, pex[1], 0, 0);
    u32 e = 0;
    i64 r;
    do r = sys(SYS_read, pex[0], &e, 4); while (r == -EINTR);
    sys(SYS_close, pex[0], 0, 0);
    if (r != 0) { o_s("exec: failed errno "); o_u(e); o_end(); }
    else { o_s("exec: ok"); o_end(); }
    fd_in = pin[1];
    fd_out = pout[0];
    fd_err = perr[0];
    sys(SYS_fcntl, fd_out, F_SETFL, sys(SYS_fcntl, fd_out, F_GETFL, 0) | O_NONBLOCK);
    sys(SYS_fcntl, fd_err, F_SETFL, sys(SYS_fcntl, fd_err, F_GETFL, 0) | O_NONBLOCK);
}

/* The server's output, its frames one at a time. */
static u8 rb[1 << 20];
static u64 rn;
static u8 eb[1 << 14];
static u64 en;

/* The next whole frame in rb, printed and taken out; whether it holds t
   (t 0: none is asked). 0 when no whole frame is there yet. */
static int frame(const char *t, int *matched) {
    u64 h = 0;
    while (h + 4 <= rn && !(rb[h] == '\r' && rb[h + 1] == '\n' && rb[h + 2] == '\r' && rb[h + 3] == '\n')) h++;
    if (h + 4 > rn) return 0;
    u64 len = 0, ok = 0;
    if (h > 16 && sprefix((const char *)rb, "Content-Length: ")) {
        ok = 1;
        for (u64 i = 16; i < h; i++) {
            if (rb[i] < '0' || rb[i] > '9') { ok = 0; break; }
            len = len * 10 + (rb[i] - '0');
        }
    }
    if (!ok) {
        o_s("s2c-header ");
        for (u64 i = 0; i < h; i++) {
            if (rb[i] == '\r') o_s("\\r");
            else if (rb[i] == '\n') o_s("\\n");
            else o_n(rb + i, 1);
        }
        o_end();
        /* A header with no length the client reads: what follows it is
           taken to the next header as a body would be. */
        u64 j = h + 4;
        while (j < rn && rb[j] != 'C') j++;
        len = j - (h + 4);
    }
    if (h + 4 + len > rn) {
        if (rn == sizeof rb) { o_s("lspc: a frame larger than the buffer"); o_end(); quit(2); }
        return 0;
    }
    const u8 *b = rb + h + 4;
    o_s("s2c "); o_u(len); o_s(" "); o_n(b, len); o_end();
    *matched = t && holds(b, len, t);
    u64 used = h + 4 + len;
    for (u64 i = used; i < rn; i++) rb[i - used] = rb[i];
    rn -= used;
    return 1;
}

static void err_lines(int all) {
    u64 s = 0;
    for (u64 i = 0; i < en; i++)
        if (eb[i] == '\n') {
            o_s("stderr: "); o_n(eb + s, i - s); o_end();
            s = i + 1;
        }
    if (all && s < en) { o_s("stderr: "); o_n(eb + s, en - s); o_s(" (no newline)"); o_end(); s = en; }
    for (u64 i = s; i < en; i++) eb[i - s] = eb[i];
    en -= s;
    if (en == sizeof eb) { o_s("stderr: "); o_n(eb, en); o_s(" (cut)"); o_end(); en = 0; }
}

static int tty_on = 1;

/* Read what is ready. Each descriptor that ends is closed (the terminal
   is only left out of the poll). */
static void drain(int fd, int which) {
    for (;;) {
        u8 tmp[4096];
        u8 *dst = tmp;
        u64 cap = sizeof tmp;
        if (which == 1) { dst = rb + rn; cap = sizeof rb - rn; }
        if (which == 2) { dst = eb + en; cap = sizeof eb - en; }
        if (cap == 0) return;
        i64 r = sys(SYS_read, fd, dst, cap);
        if (r == -EINTR) continue;
        if (r == -EAGAIN) return;
        if (r <= 0 && which == 0) {
            tty_on = 0; /* the terminal is never closed, only left out of the poll */
            return;
        }
        if (r <= 0) {
            sys(SYS_close, fd, 0, 0);
            if (which == 1) fd_out = -1;
            if (which == 2) { fd_err = -1; err_lines(1); }
            return;
        }
        if (which == 1) rn += (u64)r;
        else if (which == 2) { en += (u64)r; err_lines(0); }
        else if (which == 3) nsig += (u64)r;
        else ntty += (u64)r;
        if (which == 0) return; /* a terminal: what one read gives */
    }
}

/* One poll over the terminal, the server's output and error and the
   self-pipe, at most until `until` (microseconds). */
static void pump_once(u64 until) {
    struct { int fd; short ev, rev; } p[4];
    p[0].fd = tty_on ? 0 : -1;
    p[1].fd = fd_out;
    p[2].fd = fd_err;
    p[3].fd = sig_r;
    for (int i = 0; i < 4; i++) { p[i].ev = POLLIN; p[i].rev = 0; }
    u64 t = now_us();
    i64 ms = until > t ? (i64)((until - t + 999) / 1000) : 0;
    i64 r = sys(SYS_poll, p, 4, ms);
    if (r == -EINTR || r == 0) return;
    if (r < 0) { o_s("lspc: poll failed "); o_i(r); o_end(); quit(2); }
    if (p[0].rev & (POLLERR | POLLNVAL)) {
        o_s("tty: dropped from the poll, revents 0x"); o_u((u64)p[0].rev); o_end();
        tty_on = 0;
    } else if (p[0].rev & (POLLIN | POLLHUP)) drain(0, 0);
    if (p[1].rev) drain(fd_out, 1);
    if (p[2].rev) drain(fd_err, 2);
    if (p[3].rev) drain(sig_r, 3);
}

/* Read frames until one holds t; 1 when one did, 0 at the deadline, -1
   when the server's output ended first. */
static int wait_for(const char *t, u64 until) {
    for (;;) {
        int m = 0;
        while (frame(t, &m))
            if (m) return 1;
        if (fd_out < 0) return -1;
        if (now_us() >= until) return 0;
        pump_once(until);
    }
}

static void reap(void) {
    i64 st = 0;
    i64 r;
    do r = sys6(SYS_wait4, child, (i64)&st, 0, 0, 0); while (r == -EINTR);
    reaped = 1;
    if (r != child) { o_s("exit: wait4 "); o_i(r); }
    else if ((st & 0x7f) == 0) { o_s("exit: status "); o_u((u64)((st >> 8) & 0xff)); }
    else { o_s("exit: signal "); o_u((u64)(st & 0x7f)); }
    o_end();
}

/* The server's end: its output and error ended and its SIGCHLD come, or
   the deadline (it is killed then), and it is reaped. */
static void finish(u64 until, const char *label) {
    int late = 0;
    if (reaped) return;
    while (fd_out >= 0 || fd_err >= 0 || nsig == 0) {
        int m = 0;
        while (frame(0, &m)) {}
        if (now_us() >= until) {
            if (late) {
                /* A minute after the kill: what has not ended is said, and
                   wait4 decides. */
                o_s("deadline: after the kill, output ");
                o_s(fd_out >= 0 ? "open" : "ended"); o_s(", error "); o_s(fd_err >= 0 ? "open" : "ended");
                o_s(", SIGCHLD "); o_u(nsig); o_end();
                break;
            }
            o_s("deadline: the server's end not seen within the deadline"); o_end();
            o_s("kill: the server's process group, SIGKILL: "); o_i(sys(SYS_kill, -child, SIGKILL, 0)); o_end();
            rc = 3;
            until = now_us() + 60000000;
            label = 0;
            late = 1;
        }
        pump_once(until);
    }
    int m = 0;
    while (frame(0, &m)) {}
    reap();
    if (label) { o_s("time: "); o_s(label); o_s(" "); o_u(now_us() - t_last); o_s(" us"); o_end(); }
}

static void send(const char *body) {
    u64 n = slen(body);
    static char fb[1 << 16];
    u64 k = 0;
    const char *h = "Content-Length: ";
    while (*h) fb[k++] = *h++;
    char d[24];
    int dn = 0;
    u64 v = n;
    do { d[dn++] = (char)('0' + v % 10); v /= 10; } while (v);
    while (dn) fb[k++] = d[--dn];
    fb[k++] = '\r'; fb[k++] = '\n'; fb[k++] = '\r'; fb[k++] = '\n';
    if (k + n > sizeof fb) { o_s("lspc: a frame larger than the buffer"); o_end(); quit(2); }
    memcpy(fb + k, body, n);
    k += n;
    o_s("c2s "); o_u(n); o_s(" "); o_n(body, n); o_end();
    t_last = now_us();
    u64 at = 0;
    while (at < k) {
        i64 r = sys(SYS_write, fd_in, fb + at, k - at);
        if (r == -EINTR) continue;
        if (r <= 0) { o_s("lspc: write to the server failed "); o_i(r); o_end(); break; }
        at += (u64)r;
    }
}

int cmain(u64 *sp) {
    i64 argc = (i64)sp[0];
    char **argv = (char **)(sp + 1);
    char **envp = argv + argc + 1;
    if (argc != 2 || !load(argv[1])) {
        o_s("usage: lspc SESSION (a readable session file)"); o_end();
        quit(2);
    }
    for (char **e = envp; *e && nsenv < 64; e++) senv[nsenv++] = *e;
    /* The self-pipe and the handler. */
    int sp2[2];
    if (sys(SYS_pipe2, sp2, O_NONBLOCK | O_CLOEXEC, 0) < 0) { o_s("lspc: pipe2 failed"); o_end(); quit(2); }
    sig_r = sp2[0];
    sig_w = sp2[1];
    u64 act[4] = { (u64)on_chld, SA_NOCLDSTOP | SA_RESTORER, (u64)lspc_restorer, 0 };
    u64 ign[4] = { 1, SA_RESTORER, (u64)lspc_restorer, 0 }; /* SIG_IGN */
    if (sys6(SYS_rt_sigaction, SIGCHLD, (i64)act, 0, 8, 0) != 0 || sys6(SYS_rt_sigaction, SIGPIPE, (i64)ign, 0, 8, 0) != 0) {
        o_s("lspc: rt_sigaction failed"); o_end(); quit(2);
    }

    const char *name = "(unnamed)";
    u64 deadline = 600000;
    for (int i = 0; i < nlines; i++) {
        char *l = lines[i];
        if (sprefix(l, "name ")) {
            name = arg(l);
            o_s("lspc: begin "); o_s(name); o_end();
        } else if (sprefix(l, "cwd ")) {
            cwd = arg(l);
        } else if (sprefix(l, "env ")) {
            setenv_(arg(l));
        } else if (sprefix(l, "argv ")) {
            char *p = arg(l);
            int n = 0;
            while (*p && n < 16) {
                sargv[n++] = p;
                while (*p && *p != ' ') p++;
                if (*p) *p++ = 0;
                while (*p == ' ') p++;
            }
            sargv[n] = 0;
        } else if (sprefix(l, "deadline ")) {
            deadline = num(arg(l));
        } else if (sprefix(l, "send ")) {
            if (!started) spawn();
            if (fd_in >= 0) send(arg(l));
        } else if (sprefix(l, "wait ") || sprefix(l, "quiet ")) {
            int quiet = sprefix(l, "quiet ");
            char *label = arg(l);
            char *t = arg(label);
            u64 ms = deadline;
            if (quiet) { ms = num(t); t = arg(t); }
            for (char *q = label; *q; q++) if (*q == ' ') { *q = 0; break; }
            if (!started) spawn();
            int r = wait_for(t, now_us() + ms * 1000);
            if (r == 1 && !quiet) {
                o_s("time: "); o_s(label); o_s(" "); o_u(now_us() - t_last); o_s(" us"); o_end();
            } else if (r == 1) {
                o_s("came: "); o_s(label); o_end();
                rc = 4;
            } else if (r == 0) {
                o_s("deadline: "); o_s(label); o_s(" not seen within "); o_u(ms); o_s(" ms"); o_end();
                if (!quiet) {
                    o_s("kill: the server's process group, SIGKILL: "); o_i(sys(SYS_kill, -child, SIGKILL, 0)); o_end();
                    t_last = now_us();
                    finish(now_us() + deadline * 1000, "exit");
                    rc = 3;
                    break;
                }
            } else {
                o_s("eof: the server's output ended before "); o_s(label); o_end();
                t_last = now_us();
                finish(now_us() + deadline * 1000, "exit");
                rc = 3;
                break;
            }
        } else if (sprefix(l, "close")) {
            if (!started) spawn();
            if (fd_in >= 0) { sys(SYS_close, fd_in, 0, 0); fd_in = -1; }
            t_last = now_us();
        } else if (sprefix(l, "kill")) {
            if (!started) spawn();
            o_s("kill: the server's process group, SIGKILL: "); o_i(sys(SYS_kill, -child, SIGKILL, 0)); o_end();
            t_last = now_us();
        } else if (sprefix(l, "reap")) {
            if (!started) spawn();
            finish(now_us() + deadline * 1000, "exit");
        } else if (sprefix(l, "end")) {
            if (!started) spawn();
            if (fd_in >= 0) { sys(SYS_close, fd_in, 0, 0); fd_in = -1; }
            finish(now_us() + deadline * 1000, "exit");
        } else {
            o_s("lspc: unknown directive: "); o_s(l); o_end();
            quit(2);
        }
    }
    if (started && !reaped) finish(now_us() + deadline * 1000, "exit");
    o_s("sigchld: "); o_u(nsig); o_end();
    o_s("tty: "); o_u(ntty); o_s(" bytes"); o_end();
    o_s("lspc: end "); o_s(name); o_s(" status "); o_u((u64)rc); o_end();
    quit(rc);
    return rc;
}

__asm__(".globl _start\n"
        "_start:\n"
        "  xorl %ebp, %ebp\n"
        "  movq %rsp, %rdi\n"
        "  andq $-16, %rsp\n"
        "  call cmain\n"
        "  hlt\n");
