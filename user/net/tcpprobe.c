/* tcpprobe — one TCP connection to IP:PORT and what came back (px89, the
   metal leg): connect(2) with a 10 s limit, then, for port 80, an HTTP
   HEAD request (RFC 9110 9.3.2, HTTP/1.0 so the server closes), and the
   first line the server sent; for any other port, the first bytes it
   sends within 5 s, if any. Prints the local address the kernel chose
   (getsockname) and the time the handshake took.

     tcpprobe IP PORT */
#include "say.h"
#include <fcntl.h>
#include <poll.h>
#include <stdlib.h>
#include <time.h>

static long ms_since(const struct timespec *a)
{
    struct timespec b;
    clock_gettime(CLOCK_MONOTONIC, &b);
    return (b.tv_sec - a->tv_sec) * 1000 + (b.tv_nsec - a->tv_nsec) / 1000000;
}

int main(int argc, char **argv)
{
    if (argc != 3) {
        say("usage: tcpprobe IP PORT\n");
        return 2;
    }
    int port = atoi(argv[2]);
    struct sockaddr_in to = sin_of(argv[1], port), me;
    int s = socket(AF_INET, SOCK_STREAM, 0);
    if (s < 0) {
        say("tcpprobe: socket: %s\n", ename(errno));
        return 1;
    }
    int fl = fcntl(s, F_GETFL);
    fcntl(s, F_SETFL, fl | O_NONBLOCK);
    struct timespec t0;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    int r = connect(s, (struct sockaddr *)&to, sizeof to);
    if (r < 0 && errno != EINPROGRESS) {
        say("tcpprobe: connect %s:%d: %s\n", argv[1], port, ename(errno));
        return 1;
    }
    if (r < 0) {
        struct pollfd p = {s, POLLOUT, 0};
        int n = poll(&p, 1, 10000);
        int e = 0;
        socklen_t el = sizeof e;
        if (n <= 0) {
            say("tcpprobe: connect %s:%d: no answer in 10 s\n", argv[1], port);
            return 1;
        }
        getsockopt(s, SOL_SOCKET, SO_ERROR, &e, &el);
        if (e != 0) {
            say("tcpprobe: connect %s:%d: %s after %ld ms\n", argv[1], port, ename(e), ms_since(&t0));
            return 1;
        }
    }
    long took = ms_since(&t0);
    socklen_t ml = sizeof me;
    getsockname(s, (struct sockaddr *)&me, &ml);
    say("tcpprobe: connected %s:%d -> %s:%d in %ld ms\n", inet_ntoa(me.sin_addr), ntohs(me.sin_port), argv[1], port, took);
    fcntl(s, F_SETFL, fl);
    if (port == 80) {
        char req[256];
        int n = snprintf(req, sizeof req, "HEAD / HTTP/1.0\r\nHost: %s\r\n\r\n", argv[1]);
        if (write(s, req, n) != n) {
            say("tcpprobe: write: %s\n", ename(errno));
            return 1;
        }
    }
    struct pollfd p = {s, POLLIN, 0};
    char got[512];
    ssize_t m = 0;
    if (poll(&p, 1, 5000) > 0)
        m = read(s, got, sizeof got - 1);
    if (m > 0) {
        got[m] = 0;
        char *e = strpbrk(got, "\r\n");
        if (e)
            *e = 0;
        say("tcpprobe: the server's first line: %s\n", got);
    } else {
        say("tcpprobe: the server sent nothing in 5 s (%s)\n", m < 0 ? ename(errno) : "end or silence");
    }
    close(s);
    return 0;
}
