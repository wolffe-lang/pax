/* unixprobe — AF_UNIX path sockets and the rest lobo asks of a kernel
   beside them (px34; `notes/px34/linux/`): socket, bind, listen, accept4,
   connect and their errnos; a name that is unlinked while its socket
   listens, and a name left behind by a socket that closed; reads,
   writes, the end of a stream, EPIPE, shutdown; getsockname,
   getpeername, getsockopt; poll and epoll on each kind of Unix socket;
   socketpair(AF_UNIX, SOCK_SEQPACKET)'s message boundaries; the files
   of /proc and /sys lobo reads; and memory mapped with MAP_NORESERVE.
   Everything stays on this machine, in /u. Its output on PAX must be its
   output on Linux, but for the lines that start with `~` (what is the
   machine's: its CPUs, its controllers, how much memory a page costs,
   and what PAX refuses by name).

   `unixprobe soak` instead makes 10,000 connections through one
   listener in a second process, each a request and an answer; then it
   takes all the memory it can and makes a thread (with a raw clone, its
   stack its own): on PAX no frame is left for the thread's kernel stack,
   and the clone must answer EAGAIN, not take the kernel down. */
#define _GNU_SOURCE
#include "../net/say.h"
#pragma GCC diagnostic ignored "-Wunused-result"
#include <dirent.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stddef.h>
#include <stdlib.h>
#include <sys/epoll.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/uio.h>
#include <sys/un.h>
#include <sched.h>
#include <sys/wait.h>
#include <time.h>

static char rb[96];
#define N(label, call) do { long r_ = (call); say("%s: %s\n", label, res(r_, rb, sizeof rb, 1)); } while (0)

static void nap(long ms)
{
    struct timespec t = { ms / 1000, (ms % 1000) * 1000000L };
    nanosleep(&t, 0);
}

/* A sockaddr_un for `path` and its length with the NUL counted. */
static socklen_t un_of(struct sockaddr_un *a, const char *path)
{
    memset(a, 0, sizeof *a);
    a->sun_family = AF_UNIX;
    strncpy(a->sun_path, path, sizeof a->sun_path - 1);
    return (socklen_t)(offsetof(struct sockaddr_un, sun_path) + strlen(path) + 1);
}

static int usock(void)
{
    return socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
}

static int bound(const char *path)
{
    struct sockaddr_un a;
    socklen_t l = un_of(&a, path);
    int s = usock();
    if (bind(s, (struct sockaddr *)&a, l) < 0)
        say("bound %s: %s\n", path, ename(errno));
    return s;
}

static int listening(const char *path, int backlog)
{
    int s = bound(path);
    if (listen(s, backlog) < 0)
        say("listen %s: %s\n", path, ename(errno));
    return s;
}

static long dial(int s, const char *path)
{
    struct sockaddr_un a;
    socklen_t l = un_of(&a, path);
    return connect(s, (struct sockaddr *)&a, l);
}

/* A name as getsockname / getpeername / accept answer it: its length,
   and the path when there is one. */
static const char *named(const struct sockaddr_un *a, socklen_t l, char *buf, size_t cap)
{
    if (l <= offsetof(struct sockaddr_un, sun_path))
        snprintf(buf, cap, "length %u, family %d, unnamed", (unsigned)l, a->sun_family);
    else
        snprintf(buf, cap, "length %u, family %d, \"%s\"", (unsigned)l, a->sun_family, a->sun_path);
    return buf;
}

static void sockname(const char *label, int s, int peer)
{
    struct sockaddr_un a;
    socklen_t l = sizeof a;
    char b[200];
    memset(&a, 0, sizeof a);
    long r = peer ? getpeername(s, (struct sockaddr *)&a, &l) : getsockname(s, (struct sockaddr *)&a, &l);
    if (r < 0)
        say("%s: -%s\n", label, ename(errno));
    else
        say("%s: %s\n", label, named(&a, l, b, sizeof b));
}

static const char *pbits(int m, char *buf, size_t cap)
{
    buf[0] = 0;
    if (m & POLLIN) strncat(buf, "IN ", cap - strlen(buf) - 1);
    if (m & POLLPRI) strncat(buf, "PRI ", cap - strlen(buf) - 1);
    if (m & POLLOUT) strncat(buf, "OUT ", cap - strlen(buf) - 1);
    if (m & POLLERR) strncat(buf, "ERR ", cap - strlen(buf) - 1);
    if (m & POLLHUP) strncat(buf, "HUP ", cap - strlen(buf) - 1);
    if (m & POLLNVAL) strncat(buf, "NVAL ", cap - strlen(buf) - 1);
    if (m & POLLRDHUP) strncat(buf, "RDHUP ", cap - strlen(buf) - 1);
    if (!buf[0])
        snprintf(buf, cap, "none");
    else
        buf[strlen(buf) - 1] = 0;
    return buf;
}

static void polled(const char *label, int s)
{
    struct pollfd p = { s, POLLIN | POLLOUT | POLLRDHUP, 0 };
    char b[64];
    int r = poll(&p, 1, 0);
    say("poll %s: %d, %s\n", label, r, pbits(p.revents, b, sizeof b));
}

static const char *ebits(unsigned m, char *buf, size_t cap)
{
    buf[0] = 0;
    if (m & EPOLLIN) strncat(buf, "IN ", cap - strlen(buf) - 1);
    if (m & EPOLLOUT) strncat(buf, "OUT ", cap - strlen(buf) - 1);
    if (m & EPOLLERR) strncat(buf, "ERR ", cap - strlen(buf) - 1);
    if (m & EPOLLHUP) strncat(buf, "HUP ", cap - strlen(buf) - 1);
    if (m & EPOLLRDHUP) strncat(buf, "RDHUP ", cap - strlen(buf) - 1);
    if (!buf[0])
        snprintf(buf, cap, "none");
    else
        buf[strlen(buf) - 1] = 0;
    return buf;
}

/* recv into a buffer and say what came. */
static void got(const char *label, int s, size_t cap, int flags)
{
    char b[256];
    long r = recv(s, b, cap < sizeof b ? cap : sizeof b, flags);
    if (r < 0)
        say("%s: -%s\n", label, ename(errno));
    else
        say("%s: %ld \"%.*s\"\n", label, r, (int)(r < 64 ? r : 64), b);
}

static void sent(const char *label, int s, const char *what, int flags)
{
    long r = send(s, what, strlen(what), flags | MSG_NOSIGNAL);
    say("%s: %s\n", label, res(r, rb, sizeof rb, 1));
}

static const char *mode_of(mode_t m, char *buf, size_t cap)
{
    const char *t = S_ISSOCK(m) ? "socket" : S_ISREG(m) ? "file" : S_ISDIR(m) ? "dir" : "other";
    snprintf(buf, cap, "%s %04o", t, (unsigned)(m & 07777));
    return buf;
}

/* --- section A: socket ------------------------------------------------ */

static char refused[512];
static void refusal(const char *what, long r)
{
    char b[64];
    snprintf(b, sizeof b, "%s%s %s", refused[0] ? ", " : "", what, r < 0 ? ename(errno) : "ok");
    strncat(refused, b, sizeof refused - strlen(refused) - 1);
}

static void sockets(void)
{
    say("== socket\n");
    int s = socket(AF_UNIX, SOCK_STREAM, 0);
    say("socket(AF_UNIX, SOCK_STREAM, 0): %s\n", s < 0 ? ename(errno) : "ok");
    close(s);
    s = socket(AF_UNIX, SOCK_STREAM, 1);
    say("socket(AF_UNIX, SOCK_STREAM, 1): %s\n", s < 0 ? ename(errno) : "ok");
    if (s >= 0) close(s);
    N("socket(AF_UNIX, SOCK_STREAM, 2)", socket(AF_UNIX, SOCK_STREAM, 2));
    s = socket(AF_UNIX, SOCK_RAW, 0);
    refusal("socket SOCK_RAW", s);
    if (s >= 0) close(s);
    N("socket(AF_UNIX, 11, 0)", socket(AF_UNIX, 11, 0));
    s = socket(AF_UNIX, SOCK_SEQPACKET, 0);
    refusal("socket SOCK_SEQPACKET", s);
    if (s >= 0) close(s);
    s = socket(AF_UNIX, SOCK_DGRAM, 0);
    refusal("socket SOCK_DGRAM", s);
    if (s >= 0) close(s);
    s = usock();
    struct stat st;
    char b[64];
    fstat(s, &st);
    say("fstat of a fresh one: %s, size %ld\n", mode_of(st.st_mode, b, sizeof b), (long)st.st_size);
    sockname("getsockname of a fresh one", s, 0);
    sockname("getpeername of a fresh one", s, 1);
    polled("a fresh one", s);
    int v = -1;
    socklen_t vl = sizeof v;
    N("getsockopt SO_TYPE", getsockopt(s, SOL_SOCKET, SO_TYPE, &v, &vl));
    say("  SO_TYPE %d, length %u\n", v, (unsigned)vl);
    v = -1, vl = sizeof v;
    N("getsockopt SO_ACCEPTCONN", getsockopt(s, SOL_SOCKET, SO_ACCEPTCONN, &v, &vl));
    say("  SO_ACCEPTCONN %d\n", v);
    v = -1, vl = sizeof v;
    N("getsockopt SO_ERROR", getsockopt(s, SOL_SOCKET, SO_ERROR, &v, &vl));
    say("  SO_ERROR %d\n", v);
    v = -1, vl = sizeof v;
    N("getsockopt option 9999", getsockopt(s, SOL_SOCKET, 9999, &v, &vl));
    int one = 1;
    refusal("setsockopt SO_REUSEADDR", setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one));
    N("recv on a fresh one", recv(s, b, 8, MSG_DONTWAIT));
    N("send on a fresh one", send(s, "x", 1, MSG_NOSIGNAL));
    N("shutdown of a fresh one", shutdown(s, SHUT_WR));
    polled("a fresh one after its shutdown", s);
    struct sockaddr_un to;
    socklen_t tol = un_of(&to, "/u/none.sock");
    N("sendto with an address on a fresh one", sendto(s, "x", 1, MSG_NOSIGNAL, (struct sockaddr *)&to, tol));
    N("accept on a fresh one", accept4(s, 0, 0, SOCK_NONBLOCK));
    N("lseek on one", lseek(s, 0, SEEK_CUR));
    int on = 1;
    N("ioctl FIONBIO", ioctl(s, FIONBIO, &on));
    say("  O_NONBLOCK now %s\n", fcntl(s, F_GETFL) & O_NONBLOCK ? "set" : "clear");
    on = 0;
    N("ioctl FIONBIO 0", ioctl(s, FIONBIO, &on));
    say("  O_NONBLOCK now %s\n", fcntl(s, F_GETFL) & O_NONBLOCK ? "set" : "clear");
    close(s);
}

/* --- section B: bind ------------------------------------------------- */

static void binds(void)
{
    say("== bind\n");
    struct sockaddr_un a;
    struct stat st;
    char b[200];
    int s = usock();
    socklen_t l = un_of(&a, "/u/b.sock");
    N("bind /u/b.sock", bind(s, (struct sockaddr *)&a, l));
    sockname("getsockname", s, 0);
    N("stat /u/b.sock", stat("/u/b.sock", &st));
    say("  %s, size %ld, links %ld\n", mode_of(st.st_mode, b, sizeof b), (long)st.st_size, (long)st.st_nlink);
    N("bind it again", bind(s, (struct sockaddr *)&a, l));
    l = un_of(&a, "/u/b2.sock");
    N("bind the bound socket elsewhere", bind(s, (struct sockaddr *)&a, l));
    int t = usock();
    l = un_of(&a, "/u/b.sock");
    N("bind another to the same name", bind(t, (struct sockaddr *)&a, l));
    close(open("/u/file", O_WRONLY | O_CREAT | O_TRUNC, 0644));
    l = un_of(&a, "/u/file");
    N("bind to a file's name", bind(t, (struct sockaddr *)&a, l));
    l = un_of(&a, "/u");
    N("bind to a directory's name", bind(t, (struct sockaddr *)&a, l));
    l = un_of(&a, "/u/none/x.sock");
    N("bind under a missing directory", bind(t, (struct sockaddr *)&a, l));
    l = un_of(&a, "/u/file/x.sock");
    N("bind under a file", bind(t, (struct sockaddr *)&a, l));
    l = un_of(&a, "/u/b3.sock");
    a.sun_family = AF_INET;
    N("bind with family AF_INET", bind(t, (struct sockaddr *)&a, l));
    l = un_of(&a, "/u/b3.sock");
    N("bind with length 111", bind(t, (struct sockaddr *)&a, 111));
    N("bind with length 1", bind(t, (struct sockaddr *)&a, 1));
    N("bind with a bad pointer", bind(t, (struct sockaddr *)8, l));
    /* The NUL not counted: the name is the bytes up to addrlen. */
    l = un_of(&a, "/u/b4.sockXYZ");
    N("bind \"/u/b4.sockXYZ\" with length 2+10 (no NUL in it)", bind(t, (struct sockaddr *)&a, 2 + 10));
    sockname("  getsockname", t, 0);
    N("stat /u/b4.sock", stat("/u/b4.sock", &st));
    close(t);
    t = usock();
    memset(&a, 0, sizeof a);
    a.sun_family = AF_UNIX;
    memcpy(a.sun_path, "\0abstract", 9);
    refusal("bind abstract", bind(t, (struct sockaddr *)&a, 2 + 9));
    close(t);
    t = usock();
    refusal("bind autobind", bind(t, (struct sockaddr *)&a, 2));
    close(t);
    /* A relative name, as lobo binds logs/control.sock. */
    chdir("/u");
    mkdir("logs", 0755);
    t = usock();
    l = un_of(&a, "logs/control.sock");
    N("bind logs/control.sock (relative)", bind(t, (struct sockaddr *)&a, l));
    sockname("  getsockname", t, 0);
    N("stat /u/logs/control.sock", stat("/u/logs/control.sock", &st));
    chdir("/");
    close(t);
    unlink("/u/logs/control.sock");
    rmdir("/u/logs");
    /* umask applies to the socket's mode. */
    mode_t old = umask(077);
    t = bound("/u/b5.sock");
    stat("/u/b5.sock", &st);
    say("bound under umask 077: %s\n", mode_of(st.st_mode, b, sizeof b));
    umask(old);
    close(t);
    unlink("/u/b5.sock");
    N("open of the socket's name", open("/u/b.sock", O_RDONLY));
    N("open of it to write", open("/u/b.sock", O_WRONLY));
    DIR *d = opendir("/u");
    struct dirent *e;
    while ((e = readdir(d)))
        if (!strcmp(e->d_name, "b.sock"))
            say("readdir /u: b.sock, d_type %d\n", e->d_type);
    closedir(d);
    close(s);
    N("stat after its socket closed", stat("/u/b.sock", &st));
    N("bind a third to the name its closed socket left", bind(usock(), (struct sockaddr *)&a, un_of(&a, "/u/b.sock")));
    N("unlink /u/b.sock", unlink("/u/b.sock"));
    unlink("/u/b4.sock");
    unlink("/u/file");
}

/* --- section C: listen and the queue ----------------------------------- */

static void queue(void)
{
    say("== listen, the queue\n");
    int t = usock();
    N("listen on an unbound socket", listen(t, 1));
    close(t);
    int l = listening("/u/q.sock", 1);
    int v = -1;
    socklen_t vl = sizeof v;
    getsockopt(l, SOL_SOCKET, SO_ACCEPTCONN, &v, &vl);
    say("SO_ACCEPTCONN on the listener: %d\n", v);
    polled("the listener, empty", l);
    int c[8], n = 0;
    for (int i = 0; i < 8; i++) {
        c[i] = socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK, 0);
        long r = dial(c[i], "/u/q.sock");
        say("non-blocking connect %d to a listener of backlog 1: %s\n", i + 1, res(r, rb, sizeof rb, 0));
        if (r < 0)
            break;
        n++;
    }
    polled("the listener, two queued", l);
    sockname("getpeername of a queued client", c[0], 1);
    sockname("getsockname of a queued client", c[0], 0);
    sent("send from a queued client", c[0], "early", 0);
    /* A blocking connect waits for room. */
    pid_t k = fork();
    if (k == 0) {
        int s = usock();
        long r = dial(s, "/u/q.sock");
        _exit(r == 0 ? 0 : 10 + errno % 100);
    }
    nap(200);
    say("the child's blocking connect still waits: %s\n", waitpid(k, 0, WNOHANG) == 0 ? "yes" : "no");
    struct sockaddr_un a;
    socklen_t al = sizeof a;
    int s = accept4(l, (struct sockaddr *)&a, &al, SOCK_CLOEXEC);
    char b[200];
    say("accept4 with an address: %s\n", s < 0 ? ename(errno) : named(&a, al, b, sizeof b));
    got("the accepted end reads what its client sent before the accept", s, 64, 0);
    int st = -1;
    waitpid(k, &st, 0);
    say("the child's blocking connect: %s\n", WIFEXITED(st) && WEXITSTATUS(st) == 0 ? "ok" : "failed");
    sockname("getsockname of an accepted end", s, 0);
    sockname("getpeername of an accepted end (unnamed client)", s, 1);
    close(s);
    int nb = 1;
    ioctl(l, FIONBIO, &nb);
    while ((s = accept4(l, 0, 0, SOCK_NONBLOCK)) >= 0)
        close(s);
    say("the queue drained: %s\n", ename(errno));
    N("accept4 with flag 1", accept4(l, 0, 0, 1));
    N("listen again, backlog 4", listen(l, 4));
    N("connect on a listener", dial(l, "/u/q.sock"));
    for (int i = 0; i < n; i++)
        close(c[i]);
    close(l);
    unlink("/u/q.sock");
    /* backlog -1, as lobo listens: well past eight. */
    l = listening("/u/q2.sock", -1);
    for (int i = 0; i < 8; i++) {
        c[i] = socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK, 0);
        if (dial(c[i], "/u/q2.sock") < 0)
            say("backlog -1: connect %d: %s\n", i + 1, ename(errno));
    }
    say("backlog -1: eight connected\n");
    for (int i = 0; i < 8; i++)
        close(c[i]);
    close(l);
    unlink("/u/q2.sock");
    /* A client bound to a name of its own. */
    l = listening("/u/q3.sock", 4);
    int cb = bound("/u/q3c.sock");
    N("a bound client connects", dial(cb, "/u/q3.sock"));
    al = sizeof a;
    s = accept4(l, (struct sockaddr *)&a, &al, 0);
    say("accept4 of a bound client: %s\n", s < 0 ? ename(errno) : named(&a, al, b, sizeof b));
    sockname("getpeername of its accepted end", s, 1);
    sockname("getpeername of the client", cb, 1);
    al = 4;
    memset(&a, 0, sizeof a);
    N("getpeername with room for 4", getpeername(s, (struct sockaddr *)&a, &al));
    say("  length %u, family %d, first bytes \"%.2s\"\n", (unsigned)al, a.sun_family, a.sun_path);
    close(s);
    close(cb);
    close(l);
    unlink("/u/q3.sock");
    unlink("/u/q3c.sock");
}

/* --- section D: connect's errnos --------------------------------------- */

static void connects(void)
{
    say("== connect\n");
    int s = usock();
    N("connect to a missing name", dial(s, "/u/none.sock"));
    N("connect under a missing directory", dial(s, "/u/none/x.sock"));
    close(open("/u/file", O_WRONLY | O_CREAT | O_TRUNC, 0644));
    N("connect to a file", dial(s, "/u/file"));
    N("connect under a file", dial(s, "/u/file/x"));
    N("connect to a directory", dial(s, "/u"));
    unlink("/u/file");
    int b = bound("/u/nl.sock");
    N("connect to a socket bound and not listening", dial(s, "/u/nl.sock"));
    close(b);
    N("connect to the name a closed socket left", dial(s, "/u/nl.sock"));
    unlink("/u/nl.sock");
    int l = listening("/u/c.sock", 4);
    struct sockaddr_un a;
    socklen_t al = un_of(&a, "/u/c.sock");
    a.sun_family = AF_INET;
    N("connect with family AF_INET", connect(s, (struct sockaddr *)&a, al));
    a.sun_family = AF_UNIX;
    N("connect with length 1", connect(s, (struct sockaddr *)&a, 1));
    N("connect with length 111", connect(s, (struct sockaddr *)&a, 111));
    N("connect", dial(s, "/u/c.sock"));
    N("connect again", dial(s, "/u/c.sock"));
    int t = usock();
    N("connect to the same listener, a second socket", dial(t, "/u/c.sock"));
    N("sendto with an address on a connected socket", sendto(s, "x", 1, MSG_NOSIGNAL, (struct sockaddr *)&a, al));
    N("sendto with no address", sendto(s, "x", 1, MSG_NOSIGNAL, 0, 0));
    close(t);
    close(s);
    close(l);
    unlink("/u/c.sock");
}

/* --- section E: data --------------------------------------------------- */

static void data(void)
{
    say("== data\n");
    int l = listening("/u/d.sock", 4);
    int c = usock();
    dial(c, "/u/d.sock");
    int s = accept4(l, 0, 0, SOCK_CLOEXEC);
    polled("a connected client, idle", c);
    sent("send hello", c, "hello", 0);
    polled("the server end, with five bytes", s);
    got("recv MSG_PEEK", s, 3, MSG_PEEK);
    got("recv 3", s, 3, 0);
    got("read the rest", s, 64, 0);
    got("recv MSG_DONTWAIT on empty", s, 64, MSG_DONTWAIT);
    N("write 4 by write(2)", write(s, "abcd", 4));
    char b[64];
    N("read by read(2)", read(c, b, sizeof b));
    struct iovec v[2] = { { "head ", 5 }, { "body", 4 } };
    N("writev of two parts", writev(s, v, 2));
    got("recv them", c, 64, 0);
    int on = 1;
    ioctl(c, FIONBIO, &on);
    got("recv after FIONBIO, nothing there", c, 64, 0);
    on = 0;
    ioctl(c, FIONBIO, &on);
    /* Many writes and reads past the buffer: every byte arrives in order. */
    pid_t k = fork();
    if (k == 0) {
        unsigned char w[1000];
        for (int i = 0; i < 300; i++) {
            pattern_fill(w, (unsigned long long)i * sizeof w, sizeof w);
            if (send_all(s, w, sizeof w) < 0)
                _exit(1);
        }
        _exit(0);
    }
    unsigned char r[777];
    unsigned long crc = 0, total = 0;
    while (total < 300000) {
        long m = recv(c, r, total + sizeof r > 300000 ? 300000 - total : sizeof r, 0);
        if (m <= 0)
            break;
        crc = crc32_of(crc, r, m);
        total += m;
    }
    unsigned char want[1000];
    unsigned long wcrc = 0;
    for (int i = 0; i < 300; i++) {
        pattern_fill(want, (unsigned long long)i * sizeof want, sizeof want);
        wcrc = crc32_of(wcrc, want, sizeof want);
    }
    int st;
    waitpid(k, &st, 0);
    say("300000 bytes through, %lu read, crc %s, the writer ended %d\n", total, crc == wcrc ? "same" : "differs", WEXITSTATUS(st));
    close(s);
    polled("a client whose peer closed", c);
    got("recv after the peer closed", c, 64, 0);
    sent("send after the peer closed", c, "x", 0);
    signal(SIGPIPE, SIG_DFL);
    k = fork();
    if (k == 0) {
        send(c, "x", 1, 0);
        _exit(0);
    }
    waitpid(k, &st, 0);
    say("send without MSG_NOSIGNAL after the peer closed: %s\n", WIFSIGNALED(st) ? (WTERMSIG(st) == SIGPIPE ? "SIGPIPE" : "another signal") : "no signal");
    signal(SIGPIPE, SIG_IGN);
    close(c);
    close(l);
    unlink("/u/d.sock");
}

/* --- section F: ends --------------------------------------------------- */

static void ends(void)
{
    say("== ends\n");
    /* A listener closed with a connection queued. */
    int l = listening("/u/e.sock", 4);
    int c = usock();
    dial(c, "/u/e.sock");
    sent("send to the queued end", c, "lost", 0);
    close(l);
    polled("a client whose listener closed before accepting it", c);
    got("its recv", c, 64, 0);
    got("its recv again", c, 64, 0);
    sent("its send", c, "x", 0);
    close(c);
    N("connect to the name the closed listener left", dial(usock(), "/u/e.sock"));
    unlink("/u/e.sock");
    /* The same, the queued client having sent nothing. */
    l = listening("/u/e.sock", 4);
    c = usock();
    dial(c, "/u/e.sock");
    close(l);
    polled("a client that sent nothing, its listener closed", c);
    got("its recv", c, 64, 0);
    sent("its send", c, "x", 0);
    close(c);
    unlink("/u/e.sock");
    /* A connection whose peer closed with nothing unread, ours unread. */
    l = listening("/u/e.sock", 4);
    c = usock();
    dial(c, "/u/e.sock");
    int t = accept4(l, 0, 0, 0);
    sent("the server end sends two bytes", t, "zz", 0);
    close(t);
    polled("a client with two bytes to read, its peer gone", c);
    got("its recv", c, 64, 0);
    got("its recv again", c, 64, 0);
    close(c);
    close(l);
    unlink("/u/e.sock");
    /* A connection closed with bytes unread. */
    l = listening("/u/e.sock", 4);
    c = usock();
    dial(c, "/u/e.sock");
    int s = accept4(l, 0, 0, 0);
    sent("send three bytes nobody reads", c, "abc", 0);
    close(s);
    polled("a client whose peer closed with bytes unread", c);
    got("its recv", c, 64, 0);
    got("its recv again", c, 64, 0);
    sent("its send", c, "x", 0);
    close(c);
    /* shutdown. */
    c = usock();
    dial(c, "/u/e.sock");
    s = accept4(l, 0, 0, 0);
    sent("send before SHUT_WR", c, "last", 0);
    N("shutdown SHUT_WR", shutdown(c, SHUT_WR));
    polled("the client after its SHUT_WR", c);
    polled("its peer", s);
    got("the peer reads", s, 64, 0);
    got("the peer reads again", s, 64, 0);
    sent("send after SHUT_WR", c, "x", 0);
    sent("the peer still sends", s, "reply", 0);
    got("the client still reads", c, 64, 0);
    N("shutdown SHUT_RD", shutdown(s, SHUT_RD));
    polled("the peer after its SHUT_RD", s);
    got("the peer reads after SHUT_RD", s, 64, MSG_DONTWAIT);
    N("shutdown how 3", shutdown(s, 3));
    N("shutdown SHUT_RDWR", shutdown(s, SHUT_RDWR));
    polled("the client after its peer's SHUT_RDWR", c);
    got("the client reads", c, 64, MSG_DONTWAIT);
    close(s);
    close(c);
    close(l);
    unlink("/u/e.sock");
}

/* --- section G: unlink while listening --------------------------------- */

static void unlinked(void)
{
    say("== a name unlinked while its socket listens\n");
    int l = listening("/u/g.sock", 4);
    int c1 = usock();
    N("connect before the unlink", dial(c1, "/u/g.sock"));
    N("unlink /u/g.sock", unlink("/u/g.sock"));
    int c2 = usock();
    N("connect after the unlink", dial(c2, "/u/g.sock"));
    polled("the listener, one queued from before", l);
    int s = accept4(l, 0, 0, SOCK_NONBLOCK);
    say("accept of the connection made before: %s\n", s < 0 ? ename(errno) : "ok");
    sent("it still talks", s, "still", 0);
    got("its client reads", c1, 64, 0);
    sockname("the listener's getsockname, its name gone", l, 0);
    int l2 = listening("/u/g.sock", 4);
    N("a second listener bound to the same path", 0);
    N("connect now", dial(c2, "/u/g.sock"));
    int nb = 1;
    ioctl(l, FIONBIO, &nb);
    ioctl(l2, FIONBIO, &nb);
    int s2 = accept4(l2, 0, 0, SOCK_NONBLOCK);
    say("the second listener has it: %s; the first: %s\n", s2 < 0 ? ename(errno) : "yes",
        accept4(l, 0, 0, SOCK_NONBLOCK) < 0 ? ename(errno) : "it too");
    close(s);
    close(s2);
    close(c1);
    close(c2);
    close(l);
    close(l2);
    unlink("/u/g.sock");
}

/* --- section H: readiness and two processes ---------------------------- */

static char cl[1024];
static void cl_say(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    size_t n = strlen(cl);
    vsnprintf(cl + n, sizeof cl - n, fmt, ap);
    va_end(ap);
}

static void ready(void)
{
    say("== epoll, two processes\n");
    int l = listening("/u/h.sock", -1);
    int on = 1;
    ioctl(l, FIONBIO, &on);
    pid_t k = fork();
    if (k == 0) {
        /* lobo's client: connect, FIONBIO, the verb, wait, read to the end. */
        nap(50);
        int c = usock();
        long r = dial(c, "/u/h.sock");
        ioctl(c, FIONBIO, &on);
        send(c, "status\n", 7, MSG_NOSIGNAL);
        char b[128];
        long n = recv(c, b, sizeof b, 0);
        cl_say("  client: connect %s, first recv %s\n", res(r, rb, sizeof rb, 0), n < 0 ? ename(errno) : "data");
        int ep = epoll_create1(EPOLL_CLOEXEC);
        struct epoll_event ev = { EPOLLIN | EPOLLRDHUP | EPOLLONESHOT, { .u64 = 7 } };
        epoll_ctl(ep, EPOLL_CTL_ADD, c, &ev);
        struct epoll_event got_ev[4];
        int m = epoll_wait(ep, got_ev, 4, 5000);
        char e[64];
        cl_say("  client: epoll_wait %d, %s, data %llu\n", m, m > 0 ? ebits(got_ev[0].events, e, sizeof e) : "none",
            m > 0 ? (unsigned long long)got_ev[0].data.u64 : 0ULL);
        epoll_ctl(ep, EPOLL_CTL_DEL, c, 0);
        size_t t = 0;
        while ((n = recv(c, b + t, sizeof b - 1 - t, 0)) > 0)
            t += n;
        b[t] = 0;
        cl_say("  client: read %zu bytes \"%s\", then %s\n", t, strtok(b, "\n"), n == 0 ? "the end" : ename(errno));
        close(c);
        say("%s", cl);
        _exit(0);
    }
    struct pollfd p = { l, POLLIN, 0 };
    int r = poll(&p, 1, 5000);
    char b[64];
    say("server: poll %d, %s\n", r, pbits(p.revents, b, sizeof b));
    int s = accept4(l, 0, 0, SOCK_CLOEXEC | SOCK_NONBLOCK);
    char v[64];
    long n;
    while ((n = recv(s, v, sizeof v, 0)) < 0 && errno == EAGAIN) {
        struct pollfd q = { s, POLLIN, 0 };
        poll(&q, 1, 250);
    }
    say("server: verb %ld bytes \"%.*s\"\n", n, n > 0 ? (int)n - 1 : 0, v);
    nap(100);
    sent("server: answer", s, "lobo status\nquitting: false\n", 0);
    close(s);
    int st;
    waitpid(k, &st, 0);
    say("server: the client ended %d\n", WEXITSTATUS(st));
    /* epoll on a listener. */
    int ep = epoll_create1(0);
    struct epoll_event ev = { EPOLLIN, { .u64 = 1 } };
    N("epoll_ctl ADD a listener", epoll_ctl(ep, EPOLL_CTL_ADD, l, &ev));
    struct epoll_event out[2];
    N("epoll_wait, nobody queued", epoll_wait(ep, out, 2, 0));
    int c = usock();
    dial(c, "/u/h.sock");
    r = epoll_wait(ep, out, 2, 0);
    say("epoll_wait, one queued: %d, %s\n", r, r > 0 ? ebits(out[0].events, b, sizeof b) : "none");
    close(c);
    s = accept4(l, 0, 0, 0);
    polled("an accepted end whose client is gone", s);
    close(s);
    close(ep);
    close(l);
    unlink("/u/h.sock");
}

/* --- section I: socketpair SOCK_SEQPACKET -------------------------------- */

static void seqpacket(void)
{
    say("== socketpair SOCK_SEQPACKET\n");
    int sv[2];
    N("socketpair(AF_UNIX, SOCK_SEQPACKET|SOCK_CLOEXEC)", socketpair(AF_UNIX, SOCK_SEQPACKET | SOCK_CLOEXEC, 0, sv));
    N("send 5", send(sv[0], "fives", 5, 0));
    N("send 0", send(sv[0], "", 0, 0));
    N("send 7", send(sv[0], "sevenxx", 7, 0));
    N("send 11", send(sv[0], "eleven bytes", 11, 0));
    N("send 2", send(sv[0], "ab", 2, 0));
    polled("the reading end, four messages waiting", sv[1]);
    got("recv 100", sv[1], 100, 0);
    got("recv 100", sv[1], 100, 0);
    got("recv 100", sv[1], 100, 0);
    got("recv 3 of 11", sv[1], 3, 0);
    char b[64];
    long r = recv(sv[1], b, 1, MSG_TRUNC | MSG_PEEK);
    say("recv 1 MSG_TRUNC|MSG_PEEK: %ld\n", r);
    got("recv 100", sv[1], 100, 0);
    got("recv MSG_DONTWAIT on none", sv[1], 100, MSG_DONTWAIT);
    struct iovec v[2] = { { "one", 3 }, { "two", 3 } };
    N("writev of two parts is one message", writev(sv[0], v, 2));
    N("write 4", write(sv[0], "four", 4));
    got("recv 100", sv[1], 100, 0);
    N("read 64", read(sv[1], b, sizeof b));
    int st;
    pid_t k = fork();
    if (k == 0) {
        close(sv[1]);
        send(sv[0], "x", 1, 0);
        _exit(0);
    }
    close(sv[0]);
    waitpid(k, &st, 0);
    got("recv after the writer's end closed, one message left", sv[1], 100, 0);
    got("recv at the end", sv[1], 100, 0);
    close(sv[1]);
    /* A large message: Linux takes it whole; PAX's buffer is one frame. */
    socketpair(AF_UNIX, SOCK_SEQPACKET, 0, sv);
    char *big = calloc(1, 8000);
    r = send(sv[0], big, 8000, MSG_DONTWAIT);
    say("~seqpacket: a message of 8000 bytes: %s\n", res(r, rb, sizeof rb, 1));
    r = send(sv[0], big, 4000, MSG_DONTWAIT);
    say("a message of 4000 bytes: %s\n", res(r, rb, sizeof rb, 1));
    r = recv(sv[1], big, 8000, MSG_DONTWAIT);
    if (r == 8000)
        r = recv(sv[1], big, 8000, MSG_DONTWAIT);
    say("its read: %s\n", res(r, rb, sizeof rb, 1));
    free(big);
    close(sv[0]);
    close(sv[1]);
    /* The stream pair is unchanged: two writes read as one. */
    socketpair(AF_UNIX, SOCK_STREAM, 0, sv);
    send(sv[0], "ab", 2, 0);
    send(sv[0], "cd", 2, 0);
    got("a stream pair's two writes", sv[1], 100, 0);
    int on = 1;
    N("ioctl FIONBIO on a pair's end", ioctl(sv[1], FIONBIO, &on));
    got("recv on it, nothing there", sv[1], 100, 0);
    close(sv[0]);
    close(sv[1]);
}

/* --- section J: /proc and /sys ---------------------------------------- */

static void file(const char *path, int show)
{
    struct stat st;
    char b[64];
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        say("%s: open -%s\n", path, ename(errno));
        return;
    }
    fstat(fd, &st);
    say("%s: %s, size %ld, lseek SEEK_CUR %ld\n", path, mode_of(st.st_mode, b, sizeof b), (long)st.st_size, (long)lseek(fd, 0, SEEK_CUR));
    char t[4096];
    size_t n = 0;
    long r;
    size_t step = 32;
    while (n < sizeof t - 1 && (r = read(fd, t + n, step < sizeof t - 1 - n ? step : sizeof t - 1 - n)) > 0) {
        n += r;
        step *= 2;
    }
    t[n] = 0;
    if (show == 1)
        say("  \"%.*s\"\n", (int)(n && t[n - 1] == '\n' ? n - 1 : n), t);
    else if (show == 2)
        say("~  \"%.*s\"\n", (int)(n && t[n - 1] == '\n' ? n - 1 : n), t);
    else {
        /* /proc/self/status: the lines that are the same on any machine
           for this program, and how many lines in all. */
        int lines = 0;
        for (char *line = strtok(t, "\n"); line; line = strtok(0, "\n")) {
            lines++;
            if (!strncmp(line, "Name:", 5) || !strncmp(line, "Umask:", 6) || !strncmp(line, "State:", 6) ||
                !strncmp(line, "Uid:", 4) || !strncmp(line, "Gid:", 4) || !strncmp(line, "Threads:", 8) ||
                !strncmp(line, "TracerPid:", 10) || !strncmp(line, "SigPnd:", 7) || !strncmp(line, "ShdPnd:", 7) ||
                !strncmp(line, "SigBlk:", 7) || !strncmp(line, "SigCgt:", 7) || !strncmp(line, "NoNewPrivs:", 11) ||
                !strncmp(line, "Kthread:", 8) || !strncmp(line, "VmLck:", 6) || !strncmp(line, "VmSwap:", 7))
                say("  %s\n", line);
            else if (!strncmp(line, "VmRSS:", 6) || !strncmp(line, "Cpus_allowed_list:", 18) || !strncmp(line, "FDSize:", 7))
                say("~  %s\n", line);
        }
        say("~  %d lines\n", lines);
    }
    N("  a second read at the end", read(fd, t, 16));
    close(fd);
}

static void procsys(void)
{
    say("== /proc and /sys\n");
    file("/proc/self/status", 0);
    file("/proc/self/cgroup", 1);
    file("/sys/fs/cgroup/cpu.max", 1);
    file("/sys/fs/cgroup/cgroup.controllers", 2);
    file("/sys/devices/system/cpu/online", 2);
    file("/proc/sys/vm/overcommit_memory", 1);
    struct statx sx;
    char b[64];
    long r = statx(AT_FDCWD, "/sys/fs/cgroup/cgroup.controllers", AT_STATX_SYNC_AS_STAT, STATX_ALL, &sx);
    say("statx /sys/fs/cgroup/cgroup.controllers: %s, %s, size %llu\n", res(r, rb, sizeof rb, 0), mode_of(sx.stx_mode, b, sizeof b), (unsigned long long)sx.stx_size);
    int fd = open("/proc/self/status", O_RDONLY);
    struct stat st;
    N("fstatat by AT_EMPTY_PATH", fstatat(fd, "", &st, AT_EMPTY_PATH));
    close(fd);
    fd = open("/proc/self/cgroup", O_WRONLY);
    say("open /proc/self/cgroup to write: %s\n", fd < 0 ? ename(errno) : "ok");
    N("  write to it", write(fd, "0::/x\n", 6));
    close(fd);
    N("open /proc/self/nothing", open("/proc/self/nothing", O_RDONLY));
    N("open /sys/fs/cgroup/nothing", open("/sys/fs/cgroup/nothing", O_RDONLY));
    N("mkdir /proc/self/x", mkdir("/proc/self/x", 0755));
    char t[64];
    r = readlink("/proc/self/exe", t, sizeof t - 1);
    t[r > 0 ? r : 0] = 0;
    say("readlink /proc/self/exe: \"%s\"\n", t);
    struct rlimit rl;
    getrlimit(RLIMIT_NOFILE, &rl);
    say("~rlimit: RLIMIT_NOFILE %lu %lu\n", (unsigned long)rl.rlim_cur, (unsigned long)rl.rlim_max);
}

/* --- section K: MAP_NORESERVE ------------------------------------------ */

static long rss_kb(void)
{
    char t[4096];
    int fd = open("/proc/self/status", O_RDONLY);
    long n = read(fd, t, sizeof t - 1);
    close(fd);
    if (n <= 0)
        return -1;
    t[n] = 0;
    char *p = strstr(t, "VmRSS:");
    return p ? strtol(p + 6, 0, 10) : -1;
}

static void noreserve(void)
{
    say("== MAP_NORESERVE\n");
    size_t len = 8486912;
    long before = rss_kb();
    char *m = mmap(0, len, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
    say("mmap of 8486912 bytes, MAP_NORESERVE: %s\n", m == MAP_FAILED ? ename(errno) : "ok");
    long after_map = rss_kb();
    say("~noreserve: VmRSS %ld kB before, %ld kB more after the mmap\n", before, after_map - before);
    say("a page never touched reads %d\n", m[len - 1]);
    m[len - 4096] = 'a';
    m[len - 1] = 'z';
    m[4 * 65536] = 'b';
    say("three bytes written and read back: %c%c%c\n", m[len - 4096], m[4 * 65536], m[len - 1]);
    int p[2];
    pipe(p);
    write(p[1], "through a pipe", 14);
    N("read(2) into a page never touched", read(p[0], m + len / 2, 14));
    say("  it holds \"%.14s\"\n", m + len / 2);
    close(p[0]);
    close(p[1]);
    N("mprotect of the first 65536 bytes to PROT_NONE", mprotect(m, 65536, PROT_NONE));
    long after_touch = rss_kb();
    say("~noreserve: %ld kB more after three pages and a read\n", after_touch - after_map);
    N("madvise MADV_DONTNEED of a written page", madvise(m + len - 4096, 4096, MADV_DONTNEED));
    say("it reads %d after\n", m[len - 4096]);
    N("madvise MADV_FREE of the rest", madvise(m + 65536, len - 65536, MADV_FREE));
    long after_free = rss_kb();
    say("~noreserve: %ld kB after MADV_FREE than before it\n", after_free - after_touch);
    m[4 * 65536] = 'c';
    say("written again after MADV_FREE: %c\n", m[4 * 65536]);
    pid_t k = fork();
    if (k == 0) {
        say("  child: a page the parent wrote: %c; one it never touched: %d\n", m[4 * 65536], m[len / 4]);
        m[len / 4] = 'k';
        _exit(0);
    }
    int st;
    waitpid(k, &st, 0);
    say("the child ended %d; the parent's page is still %d\n", WEXITSTATUS(st), m[len / 4]);
    k = fork();
    if (k == 0) {
        m[100] = 1; /* in the PROT_NONE guard */
        _exit(0);
    }
    waitpid(k, &st, 0);
    say("a touch of the guard: %s\n", WIFSIGNALED(st) ? (WTERMSIG(st) == SIGSEGV ? "SIGSEGV" : "another signal") : "no signal");
    N("munmap", munmap(m, len));
}

/* --- a thread with no frame for its kernel stack ------------------------- */

/* A thread by the raw clone(2) call, on the stack whose top is `top`:
   it ends at once (exit(2), the thread alone). The new thread's id, or
   -errno. */
static long raw_thread(char *top)
{
    long r;
    register long r10 __asm__("r10") = 0;
    register long r8 __asm__("r8") = 0;
    unsigned long flags = CLONE_VM | CLONE_FS | CLONE_FILES | CLONE_SIGHAND | CLONE_THREAD | CLONE_SYSVSEM;
    __asm__ volatile(
        "syscall\n\t"
        "test %%rax, %%rax\n\t"
        "jnz 1f\n\t"
        "mov $60, %%eax\n\t"
        "xor %%edi, %%edi\n\t"
        "syscall\n\t"
        "1:"
        : "=a"(r)
        : "0"(56L), "D"(flags), "S"(top), "d"(0L), "r"(r10), "r"(r8)
        : "rcx", "r11", "memory");
    return r;
}

/* A thread like `raw_thread`'s that waits on the futex word `w` until
   it is no longer 0, and only then ends: while it waits it holds its
   kernel stack, so no dead thread's stack is left to reuse. */
static long parked_thread(char *top, volatile int *w)
{
    long r;
    register long r10 __asm__("r10") = 0;
    register long r8 __asm__("r8") = 0;
    register volatile int *r12 __asm__("r12") = w;
    unsigned long flags = CLONE_VM | CLONE_FS | CLONE_FILES | CLONE_SIGHAND | CLONE_THREAD | CLONE_SYSVSEM;
    __asm__ volatile(
        "syscall\n\t"
        "test %%rax, %%rax\n\t"
        "jnz 1f\n\t"
        "2:\n\t"
        "mov $202, %%eax\n\t"
        "mov %%r12, %%rdi\n\t"
        "xor %%esi, %%esi\n\t"
        "xor %%edx, %%edx\n\t"
        "xor %%r10d, %%r10d\n\t"
        "syscall\n\t"
        "cmpl $0, (%%r12)\n\t"
        "je 2b\n\t"
        "mov $60, %%eax\n\t"
        "xor %%edi, %%edi\n\t"
        "syscall\n\t"
        "1:"
        : "=a"(r)
        : "0"(56L), "D"(flags), "S"(top), "d"(0L), "r"(r10), "r"(r8), "r"(r12)
        : "rcx", "r11", "memory");
    return r;
}

static void *chunks[2048];
static void *pages[8192];
static volatile int parked;

static void stacks(void)
{
    say("== a thread with no frame for its kernel stack\n");
    size_t sz = 65536;
    char *st = mmap(0, 4 * sz, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    memset(st, 0, 4 * sz);
    long r = raw_thread(st + sz);
    say("a thread before: %s\n", r > 0 ? "ok" : ename((int)-r));
    nap(50);
    /* This clone takes back the stack of the one that ended; the thread
       then waits, keeping its own. */
    r = parked_thread(st + 2 * sz, &parked);
    say("a thread that waits: %s\n", r > 0 ? "ok" : ename((int)-r));
    nap(50);
    int nc = 0, np = 0;
    while (nc < 2048) {
        void *m = mmap(0, 1 << 20, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (m == MAP_FAILED)
            break;
        chunks[nc++] = m;
    }
    while (np < 8192) {
        void *m = mmap(0, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (m == MAP_FAILED)
            break;
        pages[np++] = m;
    }
    r = raw_thread(st + 3 * sz);
    say("~stack: %d MiB and %d pages taken%s; a thread then: %s\n", nc, np,
        nc < 2048 || np < 8192 ? " (no more to take)" : "", r > 0 ? "ok" : ename((int)-r));
    for (int i = 0; i < nc; i++)
        munmap(chunks[i], 1 << 20);
    for (int i = 0; i < np; i++)
        munmap(pages[i], 4096);
    parked = 1;
    syscall(SYS_futex, &parked, 1 /* FUTEX_WAKE */, 1, 0, 0, 0);
    nap(50);
    r = raw_thread(st + 4 * sz);
    say("a thread after the memory came back: %s\n", r > 0 ? "ok" : ename((int)-r));
    nap(50);
    munmap(st, 4 * sz);
}

/* --- the soak ------------------------------------------------------------ */

static int soak(void)
{
    int n = 10000;
    unlink("/u/soak.sock");
    int l = listening("/u/soak.sock", 16);
    pid_t k = fork();
    if (k == 0) {
        char b[64];
        long total = 0;
        for (;;) {
            int s = accept4(l, 0, 0, SOCK_CLOEXEC);
            if (s < 0)
                _exit(2);
            long r = recv(s, b, sizeof b, 0);
            if (r == 4 && !memcmp(b, "quit", 4)) {
                close(s);
                break;
            }
            total += r;
            send(s, b, r, MSG_NOSIGNAL);
            close(s);
        }
        close(l);
        say("soak server: %ld bytes echoed\n", total);
        _exit(0);
    }
    close(l);
    unsigned long crc = 0;
    int bad = 0;
    for (int i = 0; i < n; i++) {
        char q[32], a[32];
        int s = usock();
        if (dial(s, "/u/soak.sock") < 0) {
            say("soak: connect %d: %s\n", i, ename(errno));
            bad++;
            close(s);
            continue;
        }
        int m = snprintf(q, sizeof q, "ping %d", i);
        send(s, q, m, MSG_NOSIGNAL);
        long r = recv_all(s, a, m);
        if (r != m || memcmp(a, q, m))
            bad++;
        crc = crc32_of(crc, (unsigned char *)a, r > 0 ? r : 0);
        close(s);
    }
    int s = usock();
    dial(s, "/u/soak.sock");
    send(s, "quit", 4, MSG_NOSIGNAL);
    close(s);
    int st;
    waitpid(k, &st, 0);
    unlink("/u/soak.sock");
    say("soak: %d connections, %d wrong, crc %08lx, the server ended %d\n", n, bad, crc, WEXITSTATUS(st));
    stacks();
    rmdir("/u");
    return bad != 0;
}

int main(int argc, char **argv)
{
    signal(SIGPIPE, SIG_IGN);
    mkdir("/u", 0755);
    if (argc > 1 && !strcmp(argv[1], "soak"))
        return soak();
    say("unixprobe\n");
    sockets();
    binds();
    queue();
    connects();
    data();
    ends();
    unlinked();
    ready();
    seqpacket();
    procsys();
    noreserve();
    say("~refused: %s\n", refused);
    DIR *d = opendir("/u");
    struct dirent *e;
    int left = 0;
    while ((e = readdir(d)))
        if (strcmp(e->d_name, ".") && strcmp(e->d_name, ".."))
            say("left in /u: %s\n", e->d_name), left++;
    closedir(d);
    rmdir("/u");
    say("unixprobe: done, %d names left\n", left);
    return 0;
}
