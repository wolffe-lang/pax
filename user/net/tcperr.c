/* tcperr — what AF_INET/SOCK_STREAM sockets answer when nothing is on
   the wire (px23): the refusals by errno, the port table and
   SO_REUSEADDR, listen and accept, a refused connection, names, a
   stream's reads, half-close, what a peer's close and a reset leave,
   SIGPIPE, the options, time-wait and bind. Every segment here travels
   over loopback. Its output on PAX must be its output on Linux. */
#include "say.h"
#include <fcntl.h>
#include <netinet/tcp.h>
#include <signal.h>
#include <sys/stat.h>
#include <sys/wait.h>

static char rb[64], ab[64];
#define R(label, call) do { long r_ = (call); say("%s: %s\n", label, res(r_, rb, sizeof rb, 0)); } while (0)
#define N(label, call) do { long r_ = (call); say("%s: %s\n", label, res(r_, rb, sizeof rb, 1)); } while (0)

static void name_line(const char *label, int fd, int peer)
{
    struct sockaddr_in a;
    socklen_t l = sizeof a;
    memset(&a, 0, sizeof a);
    int r = peer ? getpeername(fd, (struct sockaddr *)&a, &l) : getsockname(fd, (struct sockaddr *)&a, &l);
    if (r < 0)
        say("%s: -%s\n", label, ename(errno));
    else
        say("%s: %s len %d family %d\n", label, aname(&a, ab, sizeof ab), (int)l, a.sin_family);
}

static void recv_line(const char *label, int fd, size_t cap, int flags)
{
    char buf[256];
    ssize_t n = recv(fd, buf, cap, flags);
    if (n < 0)
        say("%s: -%s\n", label, ename(errno));
    else
        say("%s: %ld bytes \"%.*s\"\n", label, (long)n, (int)n, buf);
}

static void opt_line(const char *label, int fd, int level, int opt)
{
    int v = -1;
    socklen_t l = sizeof v;
    if (getsockopt(fd, level, opt, &v, &l) < 0)
        say("%s: -%s\n", label, ename(errno));
    else
        say("%s: %d len %d\n", label, v, (int)l);
}

static int stream(void)
{
    return socket(AF_INET, SOCK_STREAM, 0);
}

/* A listener on 127.0.0.1:port (SO_REUSEADDR), a client connected to
   it and the accepted end. */
static void pair(int port, int *l, int *c, int *s)
{
    int one = 1;
    struct sockaddr_in a = sin_of("127.0.0.1", port);
    *l = stream();
    setsockopt(*l, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    if (bind(*l, (struct sockaddr *)&a, sizeof a) < 0 || listen(*l, 4) < 0)
        say("pair %d: bind or listen: %s\n", port, ename(errno));
    *c = stream();
    if (connect(*c, (struct sockaddr *)&a, sizeof a) < 0)
        say("pair %d: connect: %s\n", port, ename(errno));
    *s = accept(*l, 0, 0);
    if (*s < 0)
        say("pair %d: accept: %s\n", port, ename(errno));
}

int main(void)
{
    int one = 1, zero = 0, v;
    struct sockaddr_in a1 = sin_of("127.0.0.1", 4101), closed = sin_of("127.0.0.1", 4199);
    struct sockaddr_in far = sin_of("10.9.9.9", 4103), p0 = sin_of("127.0.0.1", 0), from;
    struct stat st;
    socklen_t l;

    /* types and protocols */
    R("socket(AF_INET, SOCK_STREAM, IPPROTO_UDP)", socket(AF_INET, SOCK_STREAM, IPPROTO_UDP));
    R("socket(AF_INET, SOCK_STREAM, 9999)", socket(AF_INET, SOCK_STREAM, 9999));
    int a = stream();
    int b = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    say("socket(AF_INET, SOCK_STREAM, 0) and (…, IPPROTO_TCP): %s %s\n", a >= 0 ? "ok" : ename(errno), b >= 0 ? "ok" : ename(errno));
    opt_line("a, SO_TYPE", a, SOL_SOCKET, SO_TYPE);
    opt_line("a, SO_ERROR", a, SOL_SOCKET, SO_ERROR);
    R("fstat(a)", fstat(a, &st));
    say("a is a socket: %s, mode %o\n", S_ISSOCK(st.st_mode) ? "yes" : "no", (unsigned)st.st_mode);
    R("lseek(a)", lseek(a, 0, SEEK_CUR));

    /* a stream socket that is not connected */
    name_line("a, getsockname before bind", a, 0);
    name_line("a, getpeername", a, 1);
    recv_line("a, recv", a, 16, 0);
    N("a, send MSG_NOSIGNAL", send(a, "x", 1, MSG_NOSIGNAL));
    R("a, accept", accept(a, 0, 0));
    /* On its own socket: Linux answers -ENOTCONN and marks the socket
       shut all the same, and a connection later accepted from it would
       inherit the mark (measured). */
    int x = stream();
    R("shutdown(SHUT_WR), not connected", shutdown(x, SHUT_WR));
    R("shutdown(7)", shutdown(x, 7));
    close(x);

    /* bind */
    R("bind(a, 127.0.0.1:4101)", bind(a, (struct sockaddr *)&a1, sizeof a1));
    R("bind(a) again", bind(a, (struct sockaddr *)&a1, sizeof a1));
    R("bind(b, 127.0.0.1:4101), held", bind(b, (struct sockaddr *)&a1, sizeof a1));
    R("setsockopt(b, SO_REUSEADDR, 1)", setsockopt(b, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one));
    opt_line("b, SO_REUSEADDR", b, SOL_SOCKET, SO_REUSEADDR);
    R("bind(b, 127.0.0.1:4101), held by one without SO_REUSEADDR", bind(b, (struct sockaddr *)&a1, sizeof a1));
    R("bind(b, 10.9.9.9:4103), not ours", bind(b, (struct sockaddr *)&far, sizeof far));
    int u = socket(AF_INET, SOCK_DGRAM, 0);
    R("bind(a datagram socket, 127.0.0.1:4101)", bind(u, (struct sockaddr *)&a1, sizeof a1));
    close(u);
    R("bind(b, 127.0.0.1:0)", bind(b, (struct sockaddr *)&p0, sizeof p0));
    name_line("b, getsockname", b, 0);

    /* listen and accept */
    R("listen(a, 4)", listen(a, 4));
    R("listen(a, 8) again", listen(a, 8));
    R("connect(a listening socket)", connect(a, (struct sockaddr *)&closed, sizeof closed));
    recv_line("a listening socket, recv", a, 16, 0);
    N("a listening socket, send MSG_NOSIGNAL", send(a, "x", 1, MSG_NOSIGNAL));
    int e = stream();
    R("listen(a socket with no port, 1)", listen(e, 1));
    name_line("its getsockname", e, 0);
    close(e);

    /* connect */
    int c = stream();
    R("connect(c, 127.0.0.1:4199), nobody listening", connect(c, (struct sockaddr *)&closed, sizeof closed));
    opt_line("c, SO_ERROR", c, SOL_SOCKET, SO_ERROR);
    name_line("c, getpeername", c, 1);
    R("connect(c, 127.0.0.1:4101), after the refusal", connect(c, (struct sockaddr *)&a1, sizeof a1));
    R("connect(c) again", connect(c, (struct sockaddr *)&a1, sizeof a1));
    R("listen(c, 1), connected", listen(c, 1));
    R("bind(c), connected", bind(c, (struct sockaddr *)&p0, sizeof p0));
    l = sizeof from;
    memset(&from, 0, sizeof from);
    int s = accept(a, (struct sockaddr *)&from, &l);
    say("accept(a): %s from %s len %d\n", s >= 0 ? "ok" : ename(errno), aname(&from, ab, sizeof ab), (int)l);
    name_line("s, getsockname", s, 0);
    name_line("s, getpeername", s, 1);
    name_line("c, getsockname", c, 0);
    name_line("c, getpeername", c, 1);
    opt_line("s, SO_TYPE", s, SOL_SOCKET, SO_TYPE);
    R("accept(s), connected", accept(s, 0, 0));

    /* a stream: bytes, not messages */
    N("send(c, 5)", send(c, "hello", 5, 0));
    N("send(c, 7)", send(c, ", world", 7, 0));
    recv_line("s, MSG_PEEK", s, 64, MSG_PEEK);
    recv_line("s, 3 bytes", s, 3, 0);
    recv_line("s, the rest", s, 64, 0);
    recv_line("s, MSG_DONTWAIT", s, 64, MSG_DONTWAIT);
    N("send(c, 0 bytes)", send(c, "", 0, 0));
    N("write(s, 4)", write(s, "back", 4));
    char rd[16];
    v = read(c, rd, sizeof rd);
    say("read(c): %d bytes \"%.*s\"\n", v, v > 0 ? v : 0, rd);
    int d = dup(c);
    N("send(a duplicate of c, 3)", send(d, "dup", 3, 0));
    recv_line("s", s, 64, 0);
    close(d);

    /* half-close */
    R("shutdown(c, SHUT_WR)", shutdown(c, SHUT_WR));
    N("send(c) after it", send(c, "x", 1, MSG_NOSIGNAL));
    recv_line("s, the end of the stream", s, 64, 0);
    recv_line("s, again", s, 64, 0);
    N("send(s, 4), the other way still open", send(s, "late", 4, 0));
    recv_line("c", c, 64, 0);
    R("shutdown(c, SHUT_WR) again", shutdown(c, SHUT_WR));
    R("shutdown(c, SHUT_RD)", shutdown(c, SHUT_RD));
    recv_line("c, after SHUT_RD", c, 64, 0);
    R("shutdown(s, SHUT_RDWR)", shutdown(s, SHUT_RDWR));
    recv_line("s, after SHUT_RDWR", s, 64, 0);
    N("send(s) after it", send(s, "x", 1, MSG_NOSIGNAL));
    close(c);
    close(s);

    /* the peer closes; then a write draws a reset */
    int l2, c2, s2;
    pair(4102, &l2, &c2, &s2);
    close(s2);
    recv_line("c2, the peer closed", c2, 64, 0);
    N("send(c2), to a closed peer", send(c2, "x", 1, MSG_NOSIGNAL));
    N("send(c2), after the reset", send(c2, "y", 1, MSG_NOSIGNAL));
    opt_line("c2, SO_ERROR", c2, SOL_SOCKET, SO_ERROR);
    recv_line("c2, recv", c2, 64, 0);
    close(c2);

    /* a close with unread data resets the peer */
    int c3 = stream();
    connect(c3, (struct sockaddr *)&(struct sockaddr_in){.sin_family = AF_INET, .sin_port = htons(4102), .sin_addr.s_addr = htonl(0x7f000001)}, sizeof a1);
    int s3 = accept(l2, 0, 0);
    N("send(c3, 6)", send(c3, "unread", 6, 0));
    close(s3);
    recv_line("c3, the peer closed with 6 bytes unread", c3, 64, 0);
    opt_line("c3, SO_ERROR", c3, SOL_SOCKET, SO_ERROR);
    recv_line("c3, again", c3, 64, 0);
    close(c3);

    /* SIGPIPE: a plain write after the reset ends the writer */
    int c4 = stream();
    connect(c4, (struct sockaddr *)&(struct sockaddr_in){.sin_family = AF_INET, .sin_port = htons(4102), .sin_addr.s_addr = htonl(0x7f000001)}, sizeof a1);
    int s4 = accept(l2, 0, 0);
    close(s4);
    N("send(c4), to a closed peer", send(c4, "x", 1, MSG_NOSIGNAL));
    pid_t pid = fork();
    if (pid == 0) {
        ssize_t w = write(c4, "y", 1);
        say("child: write returned %ld (%s): not killed\n", (long)w, ename(errno));
        _exit(3);
    }
    int ws = 0;
    waitpid(pid, &ws, 0);
    if (WIFSIGNALED(ws))
        say("a child's write(c4) after the reset: killed by signal %d\n", WTERMSIG(ws));
    else
        say("a child's write(c4) after the reset: exit %d\n", WEXITSTATUS(ws));
    signal(SIGPIPE, SIG_IGN);
    N("write(c4), SIGPIPE ignored", write(c4, "z", 1));
    signal(SIGPIPE, SIG_DFL);
    close(c4);

    /* options */
    int o = stream();
    opt_line("o, SO_REUSEADDR", o, SOL_SOCKET, SO_REUSEADDR);
    opt_line("o, TCP_NODELAY", o, IPPROTO_TCP, TCP_NODELAY);
    R("setsockopt(o, TCP_NODELAY, 1)", setsockopt(o, IPPROTO_TCP, TCP_NODELAY, &one, sizeof one));
    opt_line("o, TCP_NODELAY", o, IPPROTO_TCP, TCP_NODELAY);
    R("setsockopt(o, TCP_NODELAY, 0)", setsockopt(o, IPPROTO_TCP, TCP_NODELAY, &zero, sizeof zero));
    v = 3;
    R("setsockopt(o, TCP_SYNCNT, 3)", setsockopt(o, IPPROTO_TCP, TCP_SYNCNT, &v, sizeof v));
    opt_line("o, TCP_SYNCNT", o, IPPROTO_TCP, TCP_SYNCNT);
    v = 256;
    R("setsockopt(o, TCP_SYNCNT, 256)", setsockopt(o, IPPROTO_TCP, TCP_SYNCNT, &v, sizeof v));
    v = 5000;
    R("setsockopt(o, TCP_USER_TIMEOUT, 5000)", setsockopt(o, IPPROTO_TCP, TCP_USER_TIMEOUT, &v, sizeof v));
    opt_line("o, TCP_USER_TIMEOUT", o, IPPROTO_TCP, TCP_USER_TIMEOUT);
    R("setsockopt(o, SOL_SOCKET, 9999)", setsockopt(o, SOL_SOCKET, 9999, &one, sizeof one));
    R("setsockopt(o, IPPROTO_TCP, 9999)", setsockopt(o, IPPROTO_TCP, 9999, &one, sizeof one));
    R("getsockopt(o, IPPROTO_TCP, 9999)", getsockopt(o, IPPROTO_TCP, 9999, &v, &(socklen_t){sizeof v}));
    R("setsockopt(o, SO_REUSEADDR, 2 bytes)", setsockopt(o, SOL_SOCKET, SO_REUSEADDR, &one, 2));
    close(o);

    /* time-wait: the end that closes first keeps the port for a while */
    int l5, c5, s5;
    struct sockaddr_in a5 = sin_of("127.0.0.1", 4105);
    pair(4105, &l5, &c5, &s5);
    close(s5); /* the accepted end closes first: it is the one that waits */
    recv_line("c5, the peer closed", c5, 64, 0);
    close(c5);
    close(l5);
    int w1 = stream();
    R("bind(127.0.0.1:4105) while a closed connection waits", bind(w1, (struct sockaddr *)&a5, sizeof a5));
    int w2 = stream();
    setsockopt(w2, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    R("the same with SO_REUSEADDR", bind(w2, (struct sockaddr *)&a5, sizeof a5));
    R("listen", listen(w2, 1));
    int w3 = stream();
    setsockopt(w3, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    R("bind(127.0.0.1:4105) with SO_REUSEADDR while another listens", bind(w3, (struct sockaddr *)&a5, sizeof a5));
    close(w1);
    close(w2);
    close(w3);

    close(a);
    close(b);
    close(l2);
    say("tcperr: done\n");
    return 0;
}
