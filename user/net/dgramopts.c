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
     - a receive with MSG_ERRQUEUE: the error queue, empty;
     - px127: recvmsg(2), what musl's resolver reads its answers with: the
       sender's address cut to msg_namelen (which then says 16), the
       datagram scattered over two iovecs, msg_controllen and msg_flags as
       the call leaves them (MSG_TRUNC for a short buffer), MSG_TRUNC and
       MSG_PEEK asked, no name buffer, no iovec, an empty datagram, nothing
       queued, the error queue, the receive timeout, more iovecs than
       UIO_MAXIOV, a header the caller cannot read, a bad descriptor and a
       descriptor that is no socket.
   Every datagram is read back with its source address and bytes. */
#define _GNU_SOURCE
#include "say.h"
#include <fcntl.h>
#include <netinet/ip.h>
#include <sys/ioctl.h>
#include <sys/time.h>

static char rb[64];
static struct iovec many[1025];

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

/* px127: one recvmsg(2) on `fd` with `flags`: `iovs` iovecs of `l0` and
   `l1` bytes, a name buffer of `namelen` bytes (none when `named` is 0),
   a 64-byte control buffer when `control`; msg_flags starts at 0x7f, so a
   call that leaves it is seen. Prints what the call answered and what it
   left in the header. */
static void rmsg(int fd, int flags, int iovs, size_t l0, size_t l1, int named, socklen_t namelen, int control,
                 const char *what)
{
    char p0[64], p1[64], ctl[64];
    unsigned char nb[32];
    struct iovec iov[2] = {{p0, l0}, {p1, l1}};
    struct msghdr h;
    memset(&h, 0, sizeof h);
    memset(p0, '.', sizeof p0);
    memset(p1, '.', sizeof p1);
    memset(nb, 0xee, sizeof nb);
    h.msg_name = named ? nb : 0;
    h.msg_namelen = namelen;
    h.msg_iov = iovs ? iov : 0;
    h.msg_iovlen = iovs;
    h.msg_control = control ? ctl : 0;
    h.msg_controllen = control ? sizeof ctl : 0;
    h.msg_flags = 0x7f;
    long r = recvmsg(fd, &h, flags);
    if (r < 0) {
        say("%s: recvmsg %s\n", what, res(r, rb, sizeof rb, 0));
        return;
    }
    char nm[96];
    if (named && h.msg_namelen >= sizeof(struct sockaddr_in) && namelen >= sizeof(struct sockaddr_in))
        aname((struct sockaddr_in *)nb, nm, sizeof nm);
    else
        snprintf(nm, sizeof nm, "%02x %02x %02x %02x", nb[0], nb[1], nb[2], nb[3]);
    int k0 = r < (long)l0 ? (int)r : (int)l0;
    int k1 = iovs > 1 && r > (long)l0 ? (int)(r - (long)l0 < (long)l1 ? r - (long)l0 : (long)l1) : 0;
    say("%s: recvmsg %ld, msg_namelen %d, name %s, msg_controllen %zu, msg_flags %#x, iov '%.*s' '%.*s'\n", what, r,
        (int)h.msg_namelen, nm, (size_t)h.msg_controllen, h.msg_flags, k0, p0, k1, p1);
}

static void put(int fd, const char *s, const char *what)
{
    long r = send(fd, s, strlen(s), 0);
    say("%s: send '%s' %s\n", what, s, res(r, rb, sizeof rb, 1));
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

    /* px127: recvmsg(2) on b, each datagram from a (connected to b). */
    put(a, "answer", "a");
    rmsg(b, 0, 1, 64, 0, 1, sizeof(struct sockaddr_in), 1, "b, a name and a control buffer");
    put(a, "scattered!", "a");
    rmsg(b, 0, 2, 3, 64, 1, sizeof(struct sockaddr_in), 0, "b, two iovecs of 3 and 64");
    put(a, "truncated!", "a");
    rmsg(b, 0, 1, 4, 0, 1, sizeof(struct sockaddr_in), 0, "b, one iovec of 4");
    put(a, "whole", "a");
    rmsg(b, MSG_TRUNC, 1, 2, 0, 1, sizeof(struct sockaddr_in), 0, "b, MSG_TRUNC, one iovec of 2");
    put(a, "peek", "a");
    rmsg(b, MSG_PEEK, 1, 64, 0, 1, sizeof(struct sockaddr_in), 0, "b, MSG_PEEK");
    rmsg(b, 0, 1, 64, 0, 1, sizeof(struct sockaddr_in), 0, "b, after the peek");
    put(a, "noname", "a");
    rmsg(b, 0, 1, 64, 0, 0, sizeof(struct sockaddr_in), 0, "b, no name buffer, msg_namelen 16");
    put(a, "nolen", "a");
    rmsg(b, 0, 1, 64, 0, 0, 0, 0, "b, no name buffer, msg_namelen 0");
    put(a, "zero", "a");
    rmsg(b, 0, 1, 64, 0, 1, 0, 0, "b, a name buffer, msg_namelen 0");
    put(a, "minus", "a");
    rmsg(b, 0, 1, 64, 0, 1, (socklen_t)-1, 0, "b, a name buffer, msg_namelen -1");
    rmsg(b, 0, 1, 64, 0, 1, sizeof(struct sockaddr_in), 0, "b, after msg_namelen -1");
    put(a, "short", "a");
    rmsg(b, 0, 1, 64, 0, 1, 2, 0, "b, a name buffer of 2");
    put(a, "", "a");
    rmsg(b, 0, 1, 64, 0, 1, sizeof(struct sockaddr_in), 0, "b, an empty datagram");
    put(a, "none", "a");
    rmsg(b, 0, 0, 0, 0, 1, sizeof(struct sockaddr_in), 0, "b, no iovec");
    rmsg(b, MSG_DONTWAIT, 1, 64, 0, 1, sizeof(struct sockaddr_in), 0, "b, MSG_DONTWAIT, nothing queued");
    rmsg(a, 0, 1, 64, 0, 1, sizeof(struct sockaddr_in), 0, "a (O_NONBLOCK), nothing queued");
    rmsg(b, MSG_ERRQUEUE | MSG_DONTWAIT, 1, 64, 0, 1, sizeof(struct sockaddr_in), 0, "b, MSG_ERRQUEUE|MSG_DONTWAIT");
    struct timeval tv = {0, 100000};
    say("setsockopt(b, SO_RCVTIMEO, 0.1 s) %s\n", res(setsockopt(b, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv), rb, sizeof rb, 0));
    rmsg(b, 0, 1, 64, 0, 1, sizeof(struct sockaddr_in), 0, "b, nothing queued, the timeout");
    put(a, "late", "a");
    rmsg(b, 0, 1, 64, 0, 1, sizeof(struct sockaddr_in), 0, "b, after the timeout");
    struct msghdr mh;
    memset(&mh, 0, sizeof mh);
    char one[8];
    for (int i = 0; i < 1025; i++)
        many[i] = (struct iovec){one, 1};
    mh.msg_iov = many;
    mh.msg_iovlen = 1025;
    say("recvmsg(b, 1025 iovecs) %s\n", res(recvmsg(b, &mh, MSG_DONTWAIT), rb, sizeof rb, 1));
    mh.msg_iovlen = 1024;
    say("recvmsg(b, 1024 iovecs, nothing queued) %s\n", res(recvmsg(b, &mh, MSG_DONTWAIT), rb, sizeof rb, 1));
    say("recvmsg(b, a header at address 8) %s\n", res(recvmsg(b, (struct msghdr *)8, MSG_DONTWAIT), rb, sizeof rb, 1));
    say("recvmsg(-1) %s\n", res(recvmsg(-1, &mh, MSG_DONTWAIT), rb, sizeof rb, 1));
    if (pipe(p) == 0) {
        say("recvmsg(a pipe) %s\n", res(recvmsg(p[0], &mh, MSG_DONTWAIT), rb, sizeof rb, 1));
        close(p[0]);
        close(p[1]);
    }
    close(a);
    close(b);
    close(c);
    say("dgramopts: done\n");
    return 0;
}
