/* pollprobe — poll(2), state by state (px24): what POLLIN, POLLOUT,
   POLLRDHUP, POLLHUP, POLLERR and POLLNVAL say for a pipe (empty, with
   bytes, full, with no writer, with no reader), a regular file, a
   datagram socket, a stream socket in each state it can be in (new,
   listening with and without a connection waiting, connecting,
   connected, with bytes, half-closed by the peer, half-closed by this
   end, closed by the peer, reset, refused), a socketpair's end, a
   closed descriptor and a negative one; and the three timeouts: zero,
   finite, and none (ended by a child's write). Everything stays on this
   machine. Its output on PAX must be its output on Linux. */
#define _GNU_SOURCE
#include "say.h"
#pragma GCC diagnostic ignored "-Wunused-result"
#pragma GCC diagnostic ignored "-Wstringop-overflow"
#pragma GCC diagnostic ignored "-Wstringop-overread"
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <sys/wait.h>
#include <time.h>

static char rb[64];
#define R(label, call) do { long r_ = (call); say("%s: %s\n", label, res(r_, rb, sizeof rb, 0)); } while (0)

static const char *bits(int r, char *b, size_t cap)
{
    snprintf(b, cap, "%s%s%s%s%s%s%s%s", r & POLLIN ? " POLLIN" : "", r & POLLPRI ? " POLLPRI" : "", r & POLLOUT ? " POLLOUT" : "",
             r & POLLRDHUP ? " POLLRDHUP" : "", r & POLLERR ? " POLLERR" : "", r & POLLHUP ? " POLLHUP" : "", r & POLLNVAL ? " POLLNVAL" : "",
             r & ~(POLLIN | POLLPRI | POLLOUT | POLLRDHUP | POLLERR | POLLHUP | POLLNVAL) ? " other" : "");
    return r ? b + 1 : "nothing";
}

#define ALL (POLLIN | POLLOUT | POLLRDHUP | POLLPRI)

/* One descriptor asked for `ev`, for at most `ms`: the count poll
   answered and what it reported. */
static void ask(const char *label, int fd, int ev, int ms)
{
    char b[96];
    struct pollfd p = { fd, ev, 0 };
    int n = poll(&p, 1, ms);
    if (n < 0)
        say("%s: -%s\n", label, ename(errno));
    else
        say("%s: %d, %s\n", label, n, bits(p.revents, b, sizeof b));
}

static long ms_now(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000L + t.tv_nsec / 1000000L;
}

static int stream(void)
{
    return socket(AF_INET, SOCK_STREAM, 0);
}

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
    int p[2], sv[2], l, c, s, one = 1;
    char buf[4096], b[96];
    struct sockaddr_in a = sin_of("127.0.0.1", 4401), closed = sin_of("127.0.0.1", 4499);
    signal(SIGPIPE, SIG_IGN);
    memset(buf, 'x', sizeof buf);

    /* --- pipes -------------------------------------------------------- */
    R("pipe", pipe(p));
    ask("empty pipe, read end", p[0], ALL, 0);
    ask("empty pipe, write end", p[1], ALL, 0);
    write(p[1], "abc", 3);
    ask("3 bytes in it, read end", p[0], ALL, 0);
    ask("3 bytes in it, read end asked only POLLOUT", p[0], POLLOUT, 0);
    ask("3 bytes in it, read end asked nothing", p[0], 0, 0);
    read(p[0], buf, 3);
    fcntl(p[1], F_SETFL, O_NONBLOCK);
    while (write(p[1], buf, sizeof buf) > 0)
        ;
    ask("full pipe, write end", p[1], ALL, 0);
    ask("full pipe, read end", p[0], ALL, 0);
    read(p[0], buf, 4095);
    ask("4095 bytes read from it, write end", p[1], ALL, 0);
    read(p[0], buf, 1);
    ask("4096 bytes read from it, write end", p[1], ALL, 0);
    close(p[1]);
    ask("the writer closed, bytes left, read end", p[0], ALL, 0);
    while (read(p[0], buf, sizeof buf) > 0)
        ;
    ask("the writer closed, empty, read end", p[0], ALL, 0);
    ask("the writer closed, empty, read end asked nothing", p[0], 0, 0);
    close(p[0]);
    R("pipe", pipe(p));
    close(p[0]);
    ask("the reader closed, write end", p[1], ALL, 0);
    ask("the reader closed, write end asked nothing", p[1], 0, 0);
    close(p[1]);

    /* --- what is not a pipe or a socket -------------------------------- */
    int f = open("/bin/pollprobe", O_RDONLY);
    ask("a regular file", f, ALL, 0);
    lseek(f, 0, SEEK_END);
    ask("a regular file at its end", f, ALL, 0);
    close(f);
    f = open("/bin", O_RDONLY | O_DIRECTORY);
    ask("a directory", f, ALL, 0);
    close(f);
    ask("a closed descriptor", 77, ALL, 0);
    ask("a closed descriptor asked nothing", 77, 0, 0);
    ask("descriptor -1", -1, ALL, 0);
    {
        struct pollfd v[3] = { { -1, POLLIN, 0x55 }, { 77, POLLIN, 0x55 }, { 78, 0, 0x55 } };
        int n = poll(v, 3, 0);
        say("three at once (-1, closed, closed): %d; revents %s", n, bits(v[0].revents, b, sizeof b));
        say(", %s", bits(v[1].revents, b, sizeof b));
        say(", %s\n", bits(v[2].revents, b, sizeof b));
        say("no descriptors, timeout 0: %d\n", poll(v, 0, 0));
        say("a null array of none: %d\n", poll(0, 0, 0));
        int n2 = poll((struct pollfd *)8, 1, 0);
        say("a bad array of one: %s\n", n2 < 0 ? ename(errno) : "taken");
    }

    /* --- a socketpair --------------------------------------------------- */
    R("socketpair", socketpair(AF_UNIX, SOCK_STREAM, 0, sv));
    ask("a socketpair's end", sv[0], ALL, 0);
    write(sv[1], "hi", 2);
    ask("2 bytes for it", sv[0], ALL, 0);
    read(sv[0], buf, 2);
    close(sv[1]);
    ask("its peer closed", sv[0], ALL, 0);
    close(sv[0]);

    /* --- a datagram socket ---------------------------------------------- */
    int u = socket(AF_INET, SOCK_DGRAM, 0);
    ask("a datagram socket, new", u, ALL, 0);
    bind(u, (struct sockaddr *)&a, sizeof a);
    ask("bound", u, ALL, 0);
    int u2 = socket(AF_INET, SOCK_DGRAM, 0);
    sendto(u2, "dg", 2, 0, (struct sockaddr *)&a, sizeof a);
    ask("a datagram waiting", u, ALL, 200);
    recv(u, buf, 16, 0);
    ask("taken", u, ALL, 0);
    close(u);
    close(u2);

    /* --- a stream socket ------------------------------------------------- */
    l = stream();
    ask("a stream socket, new", l, ALL, 0);
    setsockopt(l, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    bind(l, (struct sockaddr *)&a, sizeof a);
    ask("bound", l, ALL, 0);
    listen(l, 4);
    ask("listening, nobody waiting", l, ALL, 0);
    c = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK, 0);
    int r = connect(c, (struct sockaddr *)&a, sizeof a);
    say("a non-blocking connect: %s\n", r < 0 ? ename(errno) : "0");
    ask("the connecting socket, asked POLLOUT", c, POLLOUT, 1000);
    ask("listening, one waiting", l, ALL, 1000);
    s = accept(l, 0, 0);
    ask("listening, taken", l, ALL, 0);
    ask("connected, idle (the client)", c, ALL, 0);
    ask("connected, idle (the accepted end)", s, ALL, 0);
    ask("connected, idle, asked only POLLIN", s, POLLIN, 0);
    write(c, "ping", 4);
    ask("4 bytes for it", s, ALL, 1000);
    ask("4 bytes for it, asked POLLRDHUP alone", s, POLLRDHUP, 0);
    read(s, buf, 4);
    ask("read", s, ALL, 0);
    shutdown(c, SHUT_WR);
    ask("the peer shut its writing side", s, ALL, 1000);
    ask("the peer shut its writing side, asked nothing", s, 0, 0);
    ask("the end that shut its writing side", c, ALL, 0);
    write(s, "pong", 4);
    ask("bytes for the end that shut its writing side", c, ALL, 1000);
    read(c, buf, 4);
    shutdown(s, SHUT_WR);
    ask("both sides shut for writing (the accepted end)", s, ALL, 1000);
    ask("both sides shut for writing (the client)", c, ALL, 1000);
    ask("the same, asked nothing", c, 0, 0);
    close(s);
    close(c);

    pair(4402, &l, &c, &s);
    close(l);
    shutdown(s, SHUT_RD);
    ask("an end shut for reading", s, ALL, 0);
    shutdown(s, SHUT_RDWR);
    ask("an end shut both ways", s, ALL, 0);
    ask("its peer", c, ALL, 1000);
    close(s);
    close(c);

    pair(4403, &l, &c, &s);
    close(l);
    close(c);
    ask("the peer closed", s, ALL, 1000);
    close(s);

    pair(4404, &l, &c, &s);
    close(l);
    write(c, "unread", 6);
    ask("bytes waiting (the peer is about to close with them unread)", s, POLLIN, 1000);
    write(s, "x", 1);
    ask("a byte for the client", c, POLLIN, 1000);
    close(c); /* with a byte unread: a reset */
    ask("reset by the peer", s, ALL, 1000);
    ask("reset by the peer, asked nothing", s, 0, 0);
    r = read(s, buf, 16);
    say("its read: %s\n", r < 0 ? ename(errno) : r == 6 ? "the 6 bytes" : "other");
    r = read(s, buf, 16);
    say("its next read: %s\n", r < 0 ? ename(errno) : r == 0 ? "0" : "other");
    ask("after its error was taken", s, ALL, 0);
    close(s);

    c = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK, 0);
    r = connect(c, (struct sockaddr *)&closed, sizeof closed);
    say("a non-blocking connect to a port nobody listens on: %s\n", r < 0 ? ename(errno) : "0");
    ask("refused", c, ALL, 1000);
    ask("refused, asked nothing", c, 0, 0);
    {
        int e = -1;
        socklen_t el = sizeof e;
        getsockopt(c, SOL_SOCKET, SO_ERROR, &e, &el);
        say("SO_ERROR: %s\n", ename(e));
    }
    ask("refused, its error taken", c, ALL, 0);
    close(c);

    /* --- the timeouts ------------------------------------------------------ */
    R("pipe", pipe(p));
    long t0 = ms_now();
    ask("an empty pipe for 300 ms", p[0], POLLIN, 300);
    long dt = ms_now() - t0;
    say("that took at least 300 ms: %s; under 600: %s\n", dt >= 300 ? "yes" : "no", dt < 600 ? "yes" : "no");
    t0 = ms_now();
    say("no descriptors for 120 ms: %d", poll(0, 0, 120));
    dt = ms_now() - t0;
    say("; at least 120 ms: %s\n", dt >= 120 ? "yes" : "no");
    t0 = ms_now();
    ask("an empty pipe, timeout 0", p[0], POLLIN, 0);
    say("that took under 100 ms: %s\n", ms_now() - t0 < 100 ? "yes" : "no");
    pid_t k = fork();
    if (k == 0) {
        struct timespec nap = { 0, 200 * 1000000L };
        nanosleep(&nap, 0);
        write(p[1], "wake", 4);
        _exit(0);
    }
    t0 = ms_now();
    ask("an empty pipe with no timeout, a child writing in 200 ms", p[0], POLLIN, -1);
    dt = ms_now() - t0;
    say("that took at least 150 ms: %s\n", dt >= 150 ? "yes" : "no");
    int st = 0;
    waitpid(k, &st, 0);
    k = fork();
    if (k == 0) {
        struct timespec nap = { 0, 100 * 1000000L };
        nanosleep(&nap, 0);
        _exit(0); /* its copy of the write end closes */
    }
    close(p[1]);
    read(p[0], buf, 4);
    ask("the last writer about to exit, 2000 ms", p[0], POLLIN, 2000);
    waitpid(k, &st, 0);
    close(p[0]);

    /* Many at once: 12 pipes, two readable. */
    {
        int pp[12][2];
        struct pollfd v[12];
        for (int i = 0; i < 12; i++) {
            if (pipe(pp[i]) < 0)
                say("pipe %d: %s\n", i, ename(errno));
            v[i].fd = pp[i][0];
            v[i].events = POLLIN;
            v[i].revents = 0;
        }
        write(pp[11][1], "z", 1);
        write(pp[7][1], "z", 1);
        int n = poll(v, 12, 0), which = 0;
        for (int i = 0; i < 12; i++)
            if (v[i].revents)
                which += i;
        say("twelve pipes, two readable: %d ready, their indices sum to %d\n", n, which);
        for (int i = 0; i < 12; i++) {
            close(pp[i][0]);
            close(pp[i][1]);
        }
    }
    say("pollprobe: done\n");
    return 0;
}
