/* evprobe — eventfd(2), call by call (px24): the flags eventfd2 takes,
   what a read and a write of the counter answer (eight bytes or
   -EINVAL, -EAGAIN at zero and at the top), what poll says at zero, in
   between and at the top, a blocking read ended by another process's
   write, the counter shared by a duplicate and across fork, and the
   counter in an epoll object: level-triggered, as wolf's runtime keeps
   one to stir its waiting thread, and edge-triggered. Everything stays
   on this machine. Its output on PAX must be its output on Linux, but
   for the lines that start with `~`: what PAX refuses by name and Linux
   takes (EFD_SEMAPHORE), which tests/mpx4-ready holds to PAX's answer. */
#define _GNU_SOURCE
#include "say.h"
#pragma GCC diagnostic ignored "-Wunused-result"
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <sys/epoll.h>
#include <sys/eventfd.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>

static char rb[64];
#define N(label, call) do { long r_ = (call); say("%s: %s\n", label, res(r_, rb, sizeof rb, 1)); } while (0)

static void polled(const char *label, int fd)
{
    struct pollfd p = { fd, POLLIN | POLLOUT | POLLRDHUP | POLLPRI, 0 };
    int n = poll(&p, 1, 0);
    say("%s: %d,%s%s%s%s%s\n", label, n, p.revents & POLLIN ? " POLLIN" : "", p.revents & POLLOUT ? " POLLOUT" : "",
        p.revents & POLLERR ? " POLLERR" : "", p.revents & POLLHUP ? " POLLHUP" : "", p.revents ? "" : " nothing");
}

static long put(int fd, uint64_t v)
{
    return write(fd, &v, 8);
}

/* A read of the counter: its value, or -1 with errno. */
static void got(const char *label, int fd)
{
    uint64_t v = 0;
    long r = read(fd, &v, 8);
    if (r < 0)
        say("%s: -%s\n", label, ename(errno));
    else
        say("%s: %ld bytes, the value %llu\n", label, r, (unsigned long long)v);
}

static int waited(int ep)
{
    struct epoll_event ev[4];
    return epoll_wait(ep, ev, 4, 0);
}

/* Two waits, one after the other (C leaves the order in which a call's
   arguments are evaluated open). */
static void twice(const char *label, int ep)
{
    int first = waited(ep);
    int again = waited(ep);
    say("%s: %d; asked again: %d\n", label, first, again);
}

int main(void)
{
    struct stat st;
    uint64_t v = 0;
    char small[8];

    int e = eventfd(0, 0);
    int fl = fcntl(e, F_GETFL);
    say("eventfd(0, 0): %s; F_GETFL %s%s, F_GETFD %d\n", e >= 0 ? "a descriptor" : ename(errno),
        (fl & O_ACCMODE) == O_RDWR ? "O_RDWR" : "other", fl & O_NONBLOCK ? "|O_NONBLOCK" : "", fcntl(e, F_GETFD));
    fstat(e, &st);
    say("fstat: mode %o, size %ld\n", (unsigned)st.st_mode, (long)st.st_size);
    N("lseek", lseek(e, 0, SEEK_CUR));
    polled("at zero", e);
    N("write 5", put(e, 5));
    N("write 7", put(e, 7));
    polled("at 12", e);
    got("read", e);
    polled("read", e);
    N("a write of 4 bytes", write(e, &v, 4));
    N("a read into 4 bytes", read(e, small, 4));
    N("write 0xffffffffffffffff", put(e, 0xffffffffffffffffULL));
    N("write 0", put(e, 0));
    polled("after a write of 0", e);
    close(e);

    e = eventfd(3, EFD_NONBLOCK | EFD_CLOEXEC);
    fl = fcntl(e, F_GETFL);
    say("eventfd(3, EFD_NONBLOCK|EFD_CLOEXEC): F_GETFL %s%s, F_GETFD %d\n", (fl & O_ACCMODE) == O_RDWR ? "O_RDWR" : "other",
        fl & O_NONBLOCK ? "|O_NONBLOCK" : "", fcntl(e, F_GETFD));
    got("read", e);
    got("read again, at zero", e);
    N("write 0xfffffffffffffffe", put(e, 0xfffffffffffffffeULL));
    polled("at the top", e);
    N("write 1 at the top", put(e, 1));
    got("read", e);
    N("eventfd with a flag that is none (8)", eventfd(0, 8));
    {
        int s = eventfd(2, EFD_SEMAPHORE | EFD_NONBLOCK);
        uint64_t a = 0;
        long r = s >= 0 ? read(s, &a, 8) : -1;
        if (s < 0)
            say("~semaphore: eventfd(2, EFD_SEMAPHORE|EFD_NONBLOCK) -%s\n", ename(errno));
        else
            say("~semaphore: eventfd(2, EFD_SEMAPHORE|EFD_NONBLOCK) a descriptor; a read takes %llu of %ld bytes\n", (unsigned long long)a, r);
        if (s >= 0)
            close(s);
    }

    /* A duplicate and a child share the counter. */
    int d = dup(e);
    N("write 4 through a duplicate", put(d, 4));
    close(d);
    pid_t k = fork();
    if (k == 0) {
        put(e, 6);
        _exit(0);
    }
    int ws;
    waitpid(k, &ws, 0);
    got("read after the duplicate's 4 and a child's 6", e);
    close(e);

    /* A blocking read, ended by a child's write 200 ms later. */
    e = eventfd(0, 0);
    k = fork();
    if (k == 0) {
        struct timespec nap = { 0, 200 * 1000000L };
        nanosleep(&nap, 0);
        put(e, 9);
        _exit(0);
    }
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    got("a blocking read at zero, a child writing 9 in 200 ms", e);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    long ms = (t1.tv_sec - t0.tv_sec) * 1000L + (t1.tv_nsec - t0.tv_nsec) / 1000000L;
    say("that took at least 150 ms: %s\n", ms >= 150 ? "yes" : "no");
    waitpid(k, &ws, 0);

    /* In an epoll object: level, the way a runtime stirs its waiter. */
    int ep = epoll_create1(EPOLL_CLOEXEC);
    struct epoll_event ev = { EPOLLIN, { .u64 = 0xffffffffffffffffULL } };
    N("epoll: add it, EPOLLIN, level", epoll_ctl(ep, EPOLL_CTL_ADD, e, &ev));
    say("epoll: at zero: %d\n", waited(ep));
    put(e, 1);
    twice("epoll: written", ep);
    put(e, 1);
    say("epoll: written again, unread: %d\n", waited(ep));
    got("read", e);
    say("epoll: read: %d\n", waited(ep));
    ev.events = EPOLLIN | EPOLLET;
    N("epoll: modify to EPOLLIN|EPOLLET", epoll_ctl(ep, EPOLL_CTL_MOD, e, &ev));
    say("epoll: edge, at zero: %d\n", waited(ep));
    put(e, 1);
    put(e, 1);
    twice("epoll: edge, two writes", ep);
    put(e, 1);
    twice("epoll: edge, a third write, the counter still unread", ep);
    got("read", e);
    say("epoll: edge, read: %d\n", waited(ep));
    ev.events = EPOLLOUT | EPOLLET;
    N("epoll: modify to EPOLLOUT|EPOLLET", epoll_ctl(ep, EPOLL_CTL_MOD, e, &ev));
    twice("epoll: edge, writable", ep);
    close(e);
    say("epoll: closed: %d\n", waited(ep));
    close(ep);
    say("evprobe: done\n");
    return 0;
}
