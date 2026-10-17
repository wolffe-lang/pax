/* nbprobe — descriptors that do not block (px24): what fcntl's status
   and descriptor flags answer on each kind of descriptor a process can
   make here (a pipe's two ends, a stream socket, a datagram socket, a
   socketpair's end, a regular file, a directory), and what each call
   that would wait answers once O_NONBLOCK is set: -EAGAIN from read,
   write, accept, recv and send, -EINPROGRESS from connect with the
   result read from SO_ERROR afterwards. Everything here stays on this
   machine. Its output on PAX must be its output on Linux. */
#define _GNU_SOURCE
#include "say.h"
#pragma GCC diagnostic ignored "-Wunused-result"
#pragma GCC diagnostic ignored "-Wstringop-overflow"
#pragma GCC diagnostic ignored "-Wstringop-overread"
#include <fcntl.h>
#include <poll.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <time.h>

static char rb[64];
#define R(label, call) do { long r_ = (call); say("%s: %s\n", label, res(r_, rb, sizeof rb, 0)); } while (0)
#define N(label, call) do { long r_ = (call); say("%s: %s\n", label, res(r_, rb, sizeof rb, 1)); } while (0)

/* F_GETFL as its access mode and the two status flags this lane reads. */
static void fl_line(const char *label, int fd)
{
    int f = fcntl(fd, F_GETFL);
    if (f < 0) {
        say("%s: F_GETFL -%s\n", label, ename(errno));
        return;
    }
    int acc = f & O_ACCMODE;
    say("%s: F_GETFL %s%s%s, F_GETFD %d\n", label, acc == O_RDONLY ? "O_RDONLY" : acc == O_WRONLY ? "O_WRONLY" : "O_RDWR",
        f & O_NONBLOCK ? "|O_NONBLOCK" : "", f & O_APPEND ? "|O_APPEND" : "", fcntl(fd, F_GETFD));
}

static int nb_on(int fd)
{
    return fcntl(fd, F_SETFL, fcntl(fd, F_GETFL) | O_NONBLOCK);
}

static int nb_off(int fd)
{
    return fcntl(fd, F_SETFL, fcntl(fd, F_GETFL) & ~O_NONBLOCK);
}

static int so_error(int fd)
{
    int e = -1;
    socklen_t l = sizeof e;
    if (getsockopt(fd, SOL_SOCKET, SO_ERROR, &e, &l) < 0)
        return -errno;
    return e;
}

/* Wait until `fd` can be written or has failed (the end of a connect
   that answered -EINPROGRESS): poll's revents, or -1. */
static int settle(int fd)
{
    struct pollfd p = { fd, POLLOUT, 0 };
    if (poll(&p, 1, 5000) != 1)
        return -1;
    return p.revents;
}

int main(void)
{
    int p[2], sv[2], one = 1, zero = 0;
    char buf[4096];
    struct sockaddr_in a = sin_of("127.0.0.1", 4301), closed = sin_of("127.0.0.1", 4399);

    /* --- the flags, kind by kind -------------------------------------- */
    R("pipe", pipe(p));
    fl_line("pipe read end", p[0]);
    fl_line("pipe write end", p[1]);
    R("pipe read end F_SETFL O_NONBLOCK", nb_on(p[0]));
    fl_line("pipe read end", p[0]);
    fl_line("pipe write end (its own open file)", p[1]);
    N("read of the empty pipe", read(p[0], buf, 16));
    N("write 5", write(p[1], "hello", 5));
    N("read of 5", read(p[0], buf, 16));
    N("read again", read(p[0], buf, 16));
    R("write end F_SETFL O_NONBLOCK", nb_on(p[1]));
    memset(buf, 'x', sizeof buf);
    long put = 0, w;
    while ((w = write(p[1], buf, sizeof buf)) > 0)
        put += w;
    say("writes until the pipe is full: %ld bytes, then -%s\n", put, ename(errno));
    N("a write of 1 to the full pipe", write(p[1], "y", 1));
    N("read 4096", read(p[0], buf, sizeof buf));
    N("a write of 4097 then (room for 4096)", write(p[1], buf, 4097));
    N("a write of 100", write(p[1], buf, 100));
    R("F_SETFL 0 on the read end", nb_off(p[0]));
    fl_line("pipe read end", p[0]);
    R("F_SETFL O_APPEND|O_NONBLOCK|O_RDWR on the read end (the access mode stays)", fcntl(p[0], F_SETFL, O_APPEND | O_NONBLOCK | O_RDWR));
    fl_line("pipe read end", p[0]);
    close(p[0]);
    close(p[1]);

    int p2[2];
    R("pipe2 O_NONBLOCK|O_CLOEXEC", pipe2(p2, O_NONBLOCK | O_CLOEXEC));
    fl_line("its read end", p2[0]);
    fl_line("its write end", p2[1]);
    N("F_SETFD 0", fcntl(p2[0], F_SETFD, 0));
    N("F_GETFD", fcntl(p2[0], F_GETFD));
    N("F_SETFD FD_CLOEXEC", fcntl(p2[0], F_SETFD, FD_CLOEXEC));
    N("F_GETFD", fcntl(p2[0], F_GETFD));
    int d = fcntl(p2[0], F_DUPFD_CLOEXEC, 40);
    say("F_DUPFD_CLOEXEC from 40: %d\n", d);
    fl_line("the copy (one open file, a flag of its own)", d);
    int d2 = fcntl(p2[0], F_DUPFD, 41);
    say("F_DUPFD from 41: %d\n", d2);
    fl_line("that copy", d2);
    R("F_SETFL 0 through the copy", nb_off(d2));
    fl_line("the first, after", p2[0]);
    N("F_DUPFD from 2147483647", fcntl(p2[0], F_DUPFD, 2147483647));
    N("F_GETFL on a closed descriptor", fcntl(77, F_GETFL));
    N("F_GETFD on a closed descriptor", fcntl(77, F_GETFD));
    N("F_SETFL on a closed descriptor", fcntl(77, F_SETFL, O_NONBLOCK));
    close(d);
    close(d2);
    close(p2[0]);
    close(p2[1]);

    int f = open("/bin/nbprobe", O_RDONLY);
    fl_line("a regular file", f);
    R("F_SETFL O_NONBLOCK on it", nb_on(f));
    fl_line("a regular file", f);
    N("read 4 of it (a file never waits)", read(f, buf, 4));
    close(f);
    int dir = open("/bin", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    fl_line("a directory", dir);
    close(dir);

    R("socketpair", socketpair(AF_UNIX, SOCK_STREAM, 0, sv));
    fl_line("a socketpair's end", sv[0]);
    R("F_SETFL O_NONBLOCK", nb_on(sv[0]));
    N("recv of nothing", recv(sv[0], buf, 16, 0));
    N("send 3", send(sv[0], "abc", 3, 0));
    N("the other end, blocking, reads", read(sv[1], buf, 16));
    N("MSG_DONTWAIT on the blocking end", recv(sv[1], buf, 16, MSG_DONTWAIT));
    close(sv[0]);
    close(sv[1]);
    R("socketpair SOCK_NONBLOCK|SOCK_CLOEXEC", socketpair(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0, sv));
    fl_line("its end", sv[0]);
    close(sv[0]);
    close(sv[1]);

    int u = socket(AF_INET, SOCK_DGRAM, 0);
    fl_line("a datagram socket", u);
    R("F_SETFL O_NONBLOCK", nb_on(u));
    fl_line("a datagram socket", u);
    R("bind", bind(u, (struct sockaddr *)&a, sizeof a));
    N("recv of nothing", recv(u, buf, 16, 0));
    R("ioctl FIONBIO 0", ioctl(u, FIONBIO, &zero));
    fl_line("a datagram socket", u);
    N("recv of nothing, MSG_DONTWAIT", recv(u, buf, 16, MSG_DONTWAIT));
    close(u);
    u = socket(AF_INET, SOCK_DGRAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
    fl_line("socket SOCK_DGRAM|SOCK_NONBLOCK|SOCK_CLOEXEC", u);
    close(u);

    /* --- a stream socket: accept, connect, recv, send ----------------- */
    int l = socket(AF_INET, SOCK_STREAM, 0);
    fl_line("a stream socket", l);
    setsockopt(l, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    R("bind", bind(l, (struct sockaddr *)&a, sizeof a));
    R("listen", listen(l, 8));
    R("ioctl FIONBIO 1 on the listener", ioctl(l, FIONBIO, &one));
    fl_line("the listener", l);
    N("accept with nobody waiting", accept(l, 0, 0));
    N("accept4 with nobody waiting", accept4(l, 0, 0, SOCK_CLOEXEC | SOCK_NONBLOCK));

    int c = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK, 0);
    fl_line("socket SOCK_STREAM|SOCK_NONBLOCK", c);
    say("SO_ERROR before the connect: %d\n", so_error(c));
    N("connect", connect(c, (struct sockaddr *)&a, sizeof a));
    int rv = settle(c);
    say("then writable: %s%s%s, SO_ERROR %d\n", rv & POLLOUT ? "POLLOUT" : "", rv & POLLERR ? "|POLLERR" : "", rv & POLLHUP ? "|POLLHUP" : "", so_error(c));
    N("connect again", connect(c, (struct sockaddr *)&a, sizeof a));
    N("recv of nothing", recv(c, buf, 16, 0));
    int s = accept4(l, 0, 0, SOCK_NONBLOCK | SOCK_CLOEXEC);
    fl_line("accept4 SOCK_NONBLOCK|SOCK_CLOEXEC", s);
    close(s);
    close(c);
    c = socket(AF_INET, SOCK_STREAM, 0);
    R("a blocking connect", connect(c, (struct sockaddr *)&a, sizeof a));
    s = accept(l, 0, 0);
    fl_line("accept on a non-blocking listener (the flag is not handed down)", s);
    N("recv of nothing, MSG_DONTWAIT", recv(s, buf, 16, MSG_DONTWAIT));
    R("F_SETFL O_NONBLOCK on the accepted end", nb_on(s));
    N("recv of nothing", recv(s, buf, 16, 0));
    N("read of nothing", read(s, buf, 16));
    put = 0;
    while ((w = send(s, buf, sizeof buf, MSG_NOSIGNAL)) > 0)
        put += w;
    say("sends until both buffers are full: %s, then -%s\n", put >= 65536 ? "65536 bytes or more" : "under 65536 bytes", ename(errno));
    /* px50 PLANT B (never merged): the row as before px50, its write
     * made 60 ms late, as a loaded runner can be (notes/px50/nbrace.c). */
    {
        struct timespec ts = { 0, 60000000L };
        nanosleep(&ts, 0);
    }
    N("a write of 1 then", write(s, "z", 1));
    N("a blocking socket's send with MSG_DONTWAIT, its buffer not full", send(c, "q", 1, MSG_DONTWAIT | MSG_NOSIGNAL));
    close(s);
    close(c);

    c = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK, 0);
    N("connect to a port nobody listens on", connect(c, (struct sockaddr *)&closed, sizeof closed));
    rv = settle(c);
    say("then: %s%s%s%s\n", rv & POLLIN ? "POLLIN|" : "", rv & POLLOUT ? "POLLOUT" : "", rv & POLLERR ? "|POLLERR" : "", rv & POLLHUP ? "|POLLHUP" : "");
    int e = so_error(c);
    say("SO_ERROR: %s, and again: %d\n", ename(e), so_error(c));
    close(c);
    close(l);
    say("nbprobe: done\n");
    return 0;
}
