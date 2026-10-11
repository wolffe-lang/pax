/* epollprobe — epoll(7), call by call (px24): epoll_create1 and its
   flags; epoll_ctl's add, modify and delete with the errno for a
   duplicate, a missing entry, an epoll in itself, a regular file, a
   closed descriptor and a descriptor that is no epoll; epoll_wait's
   three timeouts and its bounds; level triggering (reported for as long
   as it holds), edge triggering (reported once for each arrival),
   one-shot (reported once, then silent until re-armed), EPOLLRDHUP,
   and the hang-up and error reports nobody has to ask for; a
   registration that goes with the last close of what it names and
   stays while a copy is open; an epoll descriptor shared across fork;
   a registration added, or modified, while another process is already
   waiting.
   Everything stays on this machine. Its output on PAX must be its
   output on Linux, but for the lines that start with `~`: what PAX
   refuses by name and Linux takes. */
#define _GNU_SOURCE
#include "say.h"
#pragma GCC diagnostic ignored "-Wunused-result"
#pragma GCC diagnostic ignored "-Wstringop-overflow"
#pragma GCC diagnostic ignored "-Wstringop-overread"
#include <fcntl.h>
#include <signal.h>
#include <sys/epoll.h>
#include <sys/wait.h>
#include <time.h>

static char rb[64];
#define R(label, call) do { long r_ = (call); say("%s: %s\n", label, res(r_, rb, sizeof rb, 0)); } while (0)
#define N(label, call) do { long r_ = (call); say("%s: %s\n", label, res(r_, rb, sizeof rb, 1)); } while (0)

static const char *bits(unsigned r, char *b, size_t cap)
{
    snprintf(b, cap, "%s%s%s%s%s%s%s", r & EPOLLIN ? " EPOLLIN" : "", r & EPOLLPRI ? " EPOLLPRI" : "", r & EPOLLOUT ? " EPOLLOUT" : "",
             r & EPOLLRDHUP ? " EPOLLRDHUP" : "", r & EPOLLERR ? " EPOLLERR" : "", r & EPOLLHUP ? " EPOLLHUP" : "",
             r & ~(unsigned)(EPOLLIN | EPOLLPRI | EPOLLOUT | EPOLLRDHUP | EPOLLERR | EPOLLHUP) ? " other" : "");
    return r ? b + 1 : "nothing";
}

static int ctl(int ep, int op, int fd, unsigned events, unsigned long long data)
{
    struct epoll_event e;
    memset(&e, 0, sizeof e);
    e.events = events;
    e.data.u64 = data;
    return epoll_ctl(ep, op, fd, &e);
}

/* epoll_wait for at most `ms`, room for 8: how many, and each one's
   data and events, in the order of their data (the kernel's order of
   reporting is its own). */
static void wait_line(const char *label, int ep, int ms)
{
    struct epoll_event ev[8];
    char b[96];
    int n = epoll_wait(ep, ev, 8, ms);
    if (n < 0) {
        say("%s: -%s\n", label, ename(errno));
        return;
    }
    for (int i = 0; i < n; i++)
        for (int j = i + 1; j < n; j++)
            if (ev[j].data.u64 < ev[i].data.u64) {
                struct epoll_event t = ev[i];
                ev[i] = ev[j];
                ev[j] = t;
            }
    say("%s: %d", label, n);
    for (int i = 0; i < n; i++)
        say("%s [%llu] %s", i ? "," : ";", (unsigned long long)ev[i].data.u64, bits(ev[i].events, b, sizeof b));
    say("\n");
}

static long ms_now(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000L + t.tv_nsec / 1000000L;
}

static void pair(int port, int *l, int *c, int *s)
{
    int one = 1;
    struct sockaddr_in a = sin_of("127.0.0.1", port);
    *l = socket(AF_INET, SOCK_STREAM, 0);
    setsockopt(*l, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    if (bind(*l, (struct sockaddr *)&a, sizeof a) < 0 || listen(*l, 4) < 0)
        say("pair %d: bind or listen: %s\n", port, ename(errno));
    *c = socket(AF_INET, SOCK_STREAM, 0);
    if (connect(*c, (struct sockaddr *)&a, sizeof a) < 0)
        say("pair %d: connect: %s\n", port, ename(errno));
    *s = accept(*l, 0, 0);
    if (*s < 0)
        say("pair %d: accept: %s\n", port, ename(errno));
}

int main(void)
{
    int p[2], q[2], l, c, s;
    char buf[4096];
    struct epoll_event ev[4];
    signal(SIGPIPE, SIG_IGN);

    /* --- making one ---------------------------------------------------- */
    int ep = epoll_create1(0);
    say("epoll_create1(0): %s, F_GETFD %d\n", ep >= 0 ? "a descriptor" : ename(errno), fcntl(ep, F_GETFD));
    int ep2 = epoll_create1(EPOLL_CLOEXEC);
    say("epoll_create1(EPOLL_CLOEXEC): %s, F_GETFD %d\n", ep2 >= 0 ? "a descriptor" : ename(errno), fcntl(ep2, F_GETFD));
    N("epoll_create1(O_NONBLOCK)", epoll_create1(O_NONBLOCK));
    N("epoll_create1(1)", epoll_create1(1));
    N("read of an epoll descriptor", read(ep, buf, 8));
    N("write to one", write(ep, buf, 8));
    N("lseek on one", lseek(ep, 0, SEEK_CUR));

    /* --- epoll_ctl's errnos ---------------------------------------------- */
    R("pipe", pipe(p));
    R("add the read end, EPOLLIN", ctl(ep, EPOLL_CTL_ADD, p[0], EPOLLIN, 1));
    N("add it again", ctl(ep, EPOLL_CTL_ADD, p[0], EPOLLIN, 1));
    N("modify the write end, never added", ctl(ep, EPOLL_CTL_MOD, p[1], EPOLLOUT, 2));
    N("delete the write end, never added", ctl(ep, EPOLL_CTL_DEL, p[1], 0, 0));
    N("add the epoll to itself", ctl(ep, EPOLL_CTL_ADD, ep, EPOLLIN, 3));
    int f = open("/bin/epollprobe", O_RDONLY);
    N("add a regular file", ctl(ep, EPOLL_CTL_ADD, f, EPOLLIN, 4));
    close(f);
    f = open("/bin", O_RDONLY | O_DIRECTORY);
    N("add a directory", ctl(ep, EPOLL_CTL_ADD, f, EPOLLIN, 4));
    close(f);
    N("add a closed descriptor", ctl(ep, EPOLL_CTL_ADD, 77, EPOLLIN, 5));
    N("add to a closed descriptor", ctl(77, EPOLL_CTL_ADD, p[1], EPOLLIN, 5));
    N("add to a pipe", ctl(p[1], EPOLL_CTL_ADD, p[0], EPOLLIN, 5));
    N("an operation that is none", ctl(ep, 9, p[1], EPOLLIN, 5));
    N("add with a null event", epoll_ctl(ep, EPOLL_CTL_ADD, p[1], 0));
    N("delete with a null event", epoll_ctl(ep, EPOLL_CTL_DEL, p[0], 0));
    R("add the read end back", ctl(ep, EPOLL_CTL_ADD, p[0], EPOLLIN, 1));

    /* --- epoll_wait's bounds and timeouts --------------------------------- */
    N("epoll_wait, room for 0", epoll_wait(ep, ev, 0, 0));
    N("epoll_wait, room for -1", epoll_wait(ep, ev, -1, 0));
    N("epoll_wait on a pipe", epoll_wait(p[0], ev, 4, 0));
    N("epoll_wait on a closed descriptor", epoll_wait(77, ev, 4, 0));
    write(p[1], "a", 1);
    N("epoll_wait into a bad array, one ready", epoll_wait(ep, (struct epoll_event *)8, 4, 0));
    read(p[0], buf, 1);
    wait_line("nothing ready, timeout 0", ep, 0);
    long t0 = ms_now();
    wait_line("nothing ready, 250 ms", ep, 250);
    long dt = ms_now() - t0;
    say("that took at least 250 ms: %s; under 550: %s\n", dt >= 250 ? "yes" : "no", dt < 550 ? "yes" : "no");
    pid_t k = fork();
    if (k == 0) {
        struct timespec nap = { 0, 200 * 1000000L };
        nanosleep(&nap, 0);
        write(p[1], "w", 1);
        _exit(0);
    }
    t0 = ms_now();
    wait_line("no timeout, a child writing in 200 ms", ep, -1);
    say("that took at least 150 ms: %s\n", ms_now() - t0 >= 150 ? "yes" : "no");
    int st;
    waitpid(k, &st, 0);

    /* --- level triggering -------------------------------------------------- */
    wait_line("level: the byte still unread", ep, 0);
    wait_line("level: and again", ep, 0);
    read(p[0], buf, 1);
    wait_line("level: read", ep, 0);
    R("pipe", pipe(q));
    R("add its write end, EPOLLOUT, and its read end", ctl(ep, EPOLL_CTL_ADD, q[1], EPOLLOUT, 2) | ctl(ep, EPOLL_CTL_ADD, q[0], EPOLLIN, 3));
    wait_line("level: an empty pipe's write end", ep, 0);
    write(q[1], "b", 1);
    write(p[1], "a", 1);
    wait_line("level: three registrations, all ready", ep, 0);
    {
        int n = epoll_wait(ep, ev, 2, 0), m = epoll_wait(ep, ev, 1, 0);
        say("room for 2 of the three: %d; room for 1: %d\n", n, m);
    }
    R("modify the write end to ask nothing", ctl(ep, EPOLL_CTL_MOD, q[1], 0, 2));
    wait_line("level: after that", ep, 0);
    R("delete the write end, and the second pipe's read end", ctl(ep, EPOLL_CTL_DEL, q[1], 0, 0) | ctl(ep, EPOLL_CTL_DEL, q[0], 0, 0));
    read(p[0], buf, 1);
    read(q[0], buf, 1);
    wait_line("level: one registration, nothing ready", ep, 0);

    /* --- edge triggering ------------------------------------------------------ */
    R("modify the read end to EPOLLIN|EPOLLET", ctl(ep, EPOLL_CTL_MOD, p[0], EPOLLIN | EPOLLET, 1));
    wait_line("edge: nothing yet", ep, 0);
    write(p[1], "ab", 2);
    wait_line("edge: two bytes arrived", ep, 0);
    wait_line("edge: asked again, nothing new", ep, 0);
    read(p[0], buf, 1);
    wait_line("edge: one of them read, nothing new", ep, 0);
    write(p[1], "c", 1);
    wait_line("edge: a third arrived", ep, 0);
    wait_line("edge: asked again", ep, 0);
    R("modify it to the same events (a modification re-arms)", ctl(ep, EPOLL_CTL_MOD, p[0], EPOLLIN | EPOLLET, 1));
    wait_line("edge: after the modification, bytes still unread", ep, 0);
    wait_line("edge: asked again", ep, 0);
    read(p[0], buf, 16);
    write(p[1], "d", 1);
    write(p[1], "e", 1);
    wait_line("edge: two writes, one report", ep, 0);
    wait_line("edge: asked again", ep, 0);
    read(p[0], buf, 16);

    /* --- one-shot ---------------------------------------------------------------- */
    R("modify it to EPOLLIN|EPOLLONESHOT", ctl(ep, EPOLL_CTL_MOD, p[0], EPOLLIN | EPOLLONESHOT, 7));
    write(p[1], "f", 1);
    wait_line("one-shot: a byte arrived", ep, 0);
    wait_line("one-shot: asked again, the byte unread", ep, 0);
    write(p[1], "g", 1);
    wait_line("one-shot: another arrived, not re-armed", ep, 0);
    N("one-shot: add it again while it is disarmed", ctl(ep, EPOLL_CTL_ADD, p[0], EPOLLIN, 7));
    R("one-shot: re-arm with a modification", ctl(ep, EPOLL_CTL_MOD, p[0], EPOLLIN | EPOLLONESHOT, 8));
    wait_line("one-shot: re-armed, bytes unread", ep, 0);
    wait_line("one-shot: asked again", ep, 0);
    read(p[0], buf, 16);
    R("delete it", ctl(ep, EPOLL_CTL_DEL, p[0], 0, 0));

    /* --- hang-up and error, unasked ------------------------------------------------- */
    R("add the read end asking nothing", ctl(ep, EPOLL_CTL_ADD, p[0], 0, 9));
    write(p[1], "h", 1);
    wait_line("asked nothing, a byte in the pipe", ep, 0);
    close(p[1]);
    wait_line("asked nothing, the writer closed", ep, 0);
    close(p[0]);
    wait_line("the read end closed too (its registration went with it)", ep, 0);
    R("pipe", pipe(p));
    R("add the write end, EPOLLOUT", ctl(ep, EPOLL_CTL_ADD, p[1], EPOLLOUT, 10));
    close(p[0]);
    wait_line("a pipe's write end, the reader closed", ep, 0);
    close(p[1]);

    /* --- a stream socket ----------------------------------------------------------- */
    pair(4501, &l, &c, &s);
    R("add the listener, EPOLLIN", ctl(ep, EPOLL_CTL_ADD, l, EPOLLIN, 20));
    R("add the accepted end, EPOLLIN|EPOLLRDHUP|EPOLLONESHOT", ctl(ep, EPOLL_CTL_ADD, s, EPOLLIN | EPOLLRDHUP | EPOLLONESHOT, 21));
    wait_line("socket: idle", ep, 0);
    write(c, "ping", 4);
    wait_line("socket: 4 bytes", ep, 1000);
    wait_line("socket: asked again (one-shot)", ep, 0);
    read(s, buf, 4);
    R("delete it, add it with EPOLLIN|EPOLLRDHUP|EPOLLONESHOT again", ctl(ep, EPOLL_CTL_DEL, s, 0, 0) | ctl(ep, EPOLL_CTL_ADD, s, EPOLLIN | EPOLLRDHUP | EPOLLONESHOT, 22));
    wait_line("socket: idle again", ep, 0);
    shutdown(c, SHUT_WR);
    wait_line("socket: the peer shut its writing side", ep, 1000);
    R("re-arm with EPOLLIN alone, level", ctl(ep, EPOLL_CTL_MOD, s, EPOLLIN, 23));
    wait_line("socket: level, the end of the stream stays readable", ep, 0);
    R("modify to EPOLLOUT|EPOLLET", ctl(ep, EPOLL_CTL_MOD, s, EPOLLOUT | EPOLLET, 24));
    wait_line("socket: writable, edge", ep, 0);
    wait_line("socket: asked again", ep, 0);
    int c2 = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = sin_of("127.0.0.1", 4501);
    connect(c2, (struct sockaddr *)&a, sizeof a);
    wait_line("socket: a connection for the listener", ep, 1000);
    wait_line("socket: level, still waiting to be accepted", ep, 0);
    int s2 = accept(l, 0, 0);
    wait_line("socket: accepted", ep, 0);
    close(c);
    wait_line("socket: the peer closed too (asked EPOLLOUT|EPOLLET)", ep, 1000);
    close(s);
    close(s2);
    close(c2);
    close(l);
    wait_line("every socket closed", ep, 0);

    /* --- a registration and the last close -------------------------------------------- */
    R("pipe", pipe(p));
    R("add the read end", ctl(ep, EPOLL_CTL_ADD, p[0], EPOLLIN, 30));
    int d = dup(p[0]);
    write(p[1], "i", 1);
    close(p[0]);
    wait_line("the descriptor closed, a copy of it open", ep, 0);
    N("delete by the closed number", ctl(ep, EPOLL_CTL_DEL, p[0], 0, 0));
    N("delete by the copy's number", ctl(ep, EPOLL_CTL_DEL, d, 0, 0));
    close(d);
    wait_line("the copy closed too", ep, 0);
    close(p[1]);

    /* --- across fork ---------------------------------------------------------------------- */
    R("pipe", pipe(p));
    R("pipe", pipe(q));
    R("add the first's read end", ctl(ep, EPOLL_CTL_ADD, p[0], EPOLLIN, 40));
    k = fork();
    if (k == 0) {
        /* The child shares the epoll: what it adds, the parent sees. */
        int r1 = ctl(ep, EPOLL_CTL_ADD, q[0], EPOLLIN, 41);
        int r2 = ctl(ep, EPOLL_CTL_DEL, p[0], 0, 0);
        write(q[1], "j", 1);
        _exit(r1 == 0 && r2 == 0 ? 0 : 1);
    }
    waitpid(k, &st, 0);
    say("the child added one and deleted one: status %d\n", WEXITSTATUS(st));
    write(p[1], "k", 1);
    wait_line("the parent's view after the child", ep, 0);
    N("the parent deletes what the child deleted", ctl(ep, EPOLL_CTL_DEL, p[0], 0, 0));
    R("the parent deletes what the child added", ctl(ep, EPOLL_CTL_DEL, q[0], 0, 0));
    close(p[0]); close(p[1]); close(q[0]); close(q[1]);

    /* --- a registration added while another process waits ---------------------------------- */
    /* What a runtime does: one thread sits in epoll_wait while another,
       whose read has just answered -EAGAIN, adds its descriptor. If the
       bytes came between that read and the add, nothing more will
       arrive to stir the waiter: the add itself must. */
    R("pipe", pipe(p));
    write(p[1], "l", 1);
    k = fork();
    if (k == 0) {
        struct timespec nap = { 0, 200 * 1000000L };
        nanosleep(&nap, 0);
        _exit(ctl(ep, EPOLL_CTL_ADD, p[0], EPOLLIN | EPOLLRDHUP | EPOLLONESHOT, 60) == 0 ? 0 : 1);
    }
    t0 = ms_now();
    wait_line("waiting with nothing registered; a child adds a readable pipe in 200 ms", ep, 5000);
    say("that took at least 150 ms: %s; under 2000: %s\n", ms_now() - t0 >= 150 ? "yes" : "no", ms_now() - t0 < 2000 ? "yes" : "no");
    waitpid(k, &st, 0);
    R("delete it", ctl(ep, EPOLL_CTL_DEL, p[0], 0, 0));
    R("add it back asking nothing", ctl(ep, EPOLL_CTL_ADD, p[0], 0, 61));
    k = fork();
    if (k == 0) {
        struct timespec nap = { 0, 200 * 1000000L };
        nanosleep(&nap, 0);
        _exit(ctl(ep, EPOLL_CTL_MOD, p[0], EPOLLIN, 62) == 0 ? 0 : 1);
    }
    wait_line("waiting; a child modifies the registration to EPOLLIN in 200 ms", ep, 5000);
    waitpid(k, &st, 0);
    close(p[0]); close(p[1]);

    /* --- many, and the end ------------------------------------------------------------------- */
    {
        int pp[12][2], ok = 0;
        for (int i = 0; i < 12; i++) {
            pipe(pp[i]);
            ok += ctl(ep, EPOLL_CTL_ADD, pp[i][0], EPOLLIN | EPOLLET, 100 + i) == 0;
        }
        for (int i = 0; i < 12; i++)
            write(pp[i][1], "s", 1);
        struct epoll_event big[16];
        int n = epoll_wait(ep, big, 16, 0), sum = 0;
        for (int i = 0; i < n; i++)
            sum += (int)big[i].data.u64;
        int again = epoll_wait(ep, big, 16, 0);
        say("twelve pipes added (%d), all written: %d reported, data sum %d; asked again: %d\n", ok, n, sum, again);
        for (int i = 0; i < 12; i++) {
            close(pp[i][0]);
            close(pp[i][1]);
        }
    }
    /* What PAX refuses by name and Linux takes: lines tests/mpx4-ready
       holds to PAX's answer and does not compare. */
    {
        int inner = epoll_create1(0), r1, r2;
        pipe(p);
        r1 = ctl(ep, EPOLL_CTL_ADD, inner, EPOLLIN, 50);
        say("~nested: an epoll object added to another: %s\n", r1 < 0 ? ename(errno) : "0");
        r2 = ctl(ep, EPOLL_CTL_ADD, p[0], EPOLLIN | EPOLLEXCLUSIVE, 51);
        say("~exclusive: a registration with EPOLLEXCLUSIVE: %s\n", r2 < 0 ? ename(errno) : "0");
        close(inner); close(p[0]); close(p[1]);
    }
    R("close the epoll", close(ep));
    N("epoll_wait on it then", epoll_wait(ep, ev, 4, 0));
    close(ep2);
    say("epollprobe: done\n");
    return 0;
}
