/* dgramopts — px104: what a C library's DNS resolver asks of a datagram
   socket, over loopback only (nothing on the wire), each answer printed
   so the same binary's output on Linux and on PAX can be compared byte
   for byte (tests/mpx4-console-push's N1):
     - IP_RECVERR (ip(7)): set, cleared and read back as an int;
     - sendmmsg(2): a vector of datagrams on a connected socket and on an
       unconnected one (each message's own address), msg_len per message,
       an empty datagram, iovecs gathered into one datagram, vlen 0, the
       first message's errno when none went, the count when a later one
       fails, a bad descriptor and a descriptor that is no socket;
     - FIONREAD on a datagram socket (udp(7)): the next datagram's length,
       0 with none queued;
     - a receive with MSG_ERRQUEUE: the error queue, empty.
   Every datagram is read back with its source address and bytes. */
#define _GNU_SOURCE
#include "say.h"
#include <fcntl.h>
#include <netinet/ip.h>
#include <sys/ioctl.h>

static char rb[64];

static void opt(int fd, const char *what)
{
    int v = -1;
    socklen_t l = sizeof v;
    long r = getsockopt(fd, SOL_IP, IP_RECVERR, &v, &l);
    say("%s: getsockopt(SOL_IP, IP_RECVERR) %s value %d len %d\n", what, res(r, rb, sizeof rb, 0), v, (int)l);
}

static void set(int fd, int v, const char *what)
{
    long r = setsockopt(fd, SOL_IP, IP_RECVERR, &v, sizeof v);
    say("%s: setsockopt(SOL_IP, IP_RECVERR, %d) %s\n", what, v, res(r, rb, sizeof rb, 0));
}

static void pending(int fd, const char *what)
{
    int n = -1;
    long r = ioctl(fd, FIONREAD, &n);
    say("%s: ioctl(FIONREAD) %s value %d\n", what, res(r, rb, sizeof rb, 0), n);
}

static void take(int fd, const char *what)
{
    char b[2048], an[64];
    struct sockaddr_in from;
    socklen_t fl = sizeof from;
    memset(&from, 0, sizeof from);
    long r = recvfrom(fd, b, sizeof b, MSG_DONTWAIT, (struct sockaddr *)&from, &fl);
    if (r < 0) {
        say("%s: recvfrom %s\n", what, res(r, rb, sizeof rb, 0));
        return;
    }
    say("%s: recvfrom %ld bytes '%.*s' from %s\n", what, r, (int)r, b, aname(&from, an, sizeof an));
}

int main(void)
{
    char an[64];
    /* IP_RECVERR on a fresh socket: off; then set, read back, cleared. */
    int a = socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
    say("socket(AF_INET, SOCK_DGRAM|SOCK_CLOEXEC|SOCK_NONBLOCK) %s\n", a < 0 ? res(a, rb, sizeof rb, 0) : "ok");
    opt(a, "fresh");
    set(a, 1, "a");
    opt(a, "a");
    set(a, 0, "a");
    opt(a, "a");
    set(a, 5, "a");
    opt(a, "a");

    /* The receiver, on an ephemeral port of 127.0.0.1. */
    int b = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in lo = sin_of("127.0.0.1", 0), bn;
    socklen_t bl = sizeof bn;
    say("bind(b, 127.0.0.1:0) %s\n", res(bind(b, (struct sockaddr *)&lo, sizeof lo), rb, sizeof rb, 0));
    getsockname(b, (struct sockaddr *)&bn, &bl);
    say("b is %s\n", aname(&bn, an, sizeof an));
    pending(b, "b, nothing queued");

    /* A connected sender, as the resolver's: two queries in one call, the
       second gathered from two iovecs. */
    say("connect(a, b) %s\n", res(connect(a, (struct sockaddr *)&bn, sizeof bn), rb, sizeof rb, 0));
    struct iovec q1[1] = {{"first", 5}}, q2[2] = {{"sec", 3}, {"ond!", 4}};
    struct mmsghdr m[3];
    memset(m, 0, sizeof m);
    m[0].msg_hdr.msg_iov = q1;
    m[0].msg_hdr.msg_iovlen = 1;
    m[1].msg_hdr.msg_iov = q2;
    m[1].msg_hdr.msg_iovlen = 2;
    m[0].msg_len = m[1].msg_len = 77;
    long r = sendmmsg(a, m, 2, MSG_NOSIGNAL);
    say("sendmmsg(a, 2, MSG_NOSIGNAL) %s, msg_len %u %u\n", res(r, rb, sizeof rb, 1), m[0].msg_len, m[1].msg_len);
    pending(b, "b, two queued");
    take(b, "b");
    pending(b, "b, one queued");
    take(b, "b");
    pending(b, "b, none queued");
    take(b, "b");

    /* An unconnected sender: each message its own address; an empty
       datagram between two others. */
    int c = socket(AF_INET, SOCK_DGRAM, 0);
    struct iovec d1[1] = {{"x", 1}}, d3[1] = {{"zzz", 3}};
    memset(m, 0, sizeof m);
    for (int i = 0; i < 3; i++) {
        m[i].msg_hdr.msg_name = &bn;
        m[i].msg_hdr.msg_namelen = sizeof bn;
        m[i].msg_len = 77;
    }
    m[0].msg_hdr.msg_iov = d1;
    m[0].msg_hdr.msg_iovlen = 1;
    m[2].msg_hdr.msg_iov = d3;
    m[2].msg_hdr.msg_iovlen = 1;
    r = sendmmsg(c, m, 3, 0);
    say("sendmmsg(c, 3 addressed) %s, msg_len %u %u %u\n", res(r, rb, sizeof rb, 1), m[0].msg_len, m[1].msg_len, m[2].msg_len);
    pending(b, "b, three queued");
    take(b, "b");
    pending(b, "b, two queued (an empty one first)");
    take(b, "b");
    pending(b, "b, one queued");
    take(b, "b");

    /* vlen 0; no address on an unconnected socket; a later message's
       failure after one went. */
    r = sendmmsg(c, m, 0, 0);
    say("sendmmsg(c, 0) %s\n", res(r, rb, sizeof rb, 1));
    memset(m, 0, sizeof m);
    m[0].msg_hdr.msg_iov = d1;
    m[0].msg_hdr.msg_iovlen = 1;
    m[0].msg_len = 77;
    r = sendmmsg(c, m, 1, 0);
    say("sendmmsg(c, 1 with no address) %s, msg_len %u\n", res(r, rb, sizeof rb, 1), m[0].msg_len);
    m[0].msg_hdr.msg_name = &bn;
    m[0].msg_hdr.msg_namelen = sizeof bn;
    m[1].msg_hdr.msg_iov = d3;
    m[1].msg_hdr.msg_iovlen = 1;
    m[1].msg_len = 77;
    r = sendmmsg(c, m, 2, 0);
    say("sendmmsg(c, 2: addressed, then none) %s, msg_len %u %u\n", res(r, rb, sizeof rb, 1), m[0].msg_len, m[1].msg_len);
    take(b, "b");
    take(b, "b");

    /* Descriptors that are no datagram socket. */
    say("sendmmsg(-1) %s\n", res(sendmmsg(-1, m, 1, 0), rb, sizeof rb, 1));
    int p[2];
    if (pipe(p) == 0) {
        say("sendmmsg(a pipe) %s\n", res(sendmmsg(p[1], m, 1, 0), rb, sizeof rb, 1));
        close(p[0]);
        close(p[1]);
    }

    /* The error queue: nothing in it, with the option on and with a
       datagram waiting in the ordinary queue. */
    set(b, 1, "b");
    struct iovec q3[1] = {{"late", 4}};
    memset(m, 0, sizeof m);
    m[0].msg_hdr.msg_iov = q3;
    m[0].msg_hdr.msg_iovlen = 1;
    r = sendmmsg(a, m, 1, 0);
    say("sendmmsg(a, 1) %s, msg_len %u\n", res(r, rb, sizeof rb, 1), m[0].msg_len);
    char e[64];
    r = recv(b, e, sizeof e, MSG_ERRQUEUE | MSG_DONTWAIT);
    say("recv(b, MSG_ERRQUEUE|MSG_DONTWAIT) %s\n", res(r, rb, sizeof rb, 1));
    pending(b, "b, one queued");
    take(b, "b");
    close(a);
    close(b);
    close(c);
    say("dgramopts: done\n");
    return 0;
}
