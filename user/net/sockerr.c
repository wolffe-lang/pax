/* sockerr — what AF_INET/SOCK_DGRAM sockets answer when nothing is on
   the wire (px22): the refusals by errno, the port table, the default
   peer's filter, truncation, duplicates, the receive timeout. Every
   datagram here travels over loopback. Its output on PAX must be its
   output on Linux. */
#include "say.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/time.h>

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
    struct sockaddr_in a;
    socklen_t l = sizeof a;
    memset(&a, 0, sizeof a);
    ssize_t n = recvfrom(fd, buf, cap, flags, (struct sockaddr *)&a, &l);
    if (n < 0) {
        say("%s: -%s\n", label, ename(errno));
        return;
    }
    size_t shown = (size_t)n < cap ? (size_t)n : cap;
    say("%s: %ld bytes \"%.*s\" from %s\n", label, (long)n, (int)shown, buf, aname(&a, ab, sizeof ab));
}

int main(void)
{
    char big[65508];
    int one = 1;
    struct sockaddr_in a1 = sin_of("127.0.0.1", 4001), a2 = sin_of("127.0.0.1", 4002);
    struct sockaddr_in any1 = sin_of("0.0.0.0", 4001), own1 = sin_of("10.0.2.15", 4001);
    struct sockaddr_in far = sin_of("10.9.9.9", 4003), p0 = sin_of("127.0.0.1", 0);
    struct sockaddr_in unx = a1;
    struct sockaddr un = {0};
    socklen_t l;

    /* families, types, protocols */
    R("socket(9999, SOCK_DGRAM, 0)", socket(9999, SOCK_DGRAM, 0));
    R("socket(AF_UNSPEC, SOCK_DGRAM, 0)", socket(AF_UNSPEC, SOCK_DGRAM, 0));
    R("socket(AF_INET, SOCK_RDM, 0)", socket(AF_INET, SOCK_RDM, 0));
    R("socket(AF_INET, 77, 0)", socket(AF_INET, 77, 0));
    R("socket(AF_INET, SOCK_DGRAM, IPPROTO_TCP)", socket(AF_INET, SOCK_DGRAM, IPPROTO_TCP));
    int a = socket(AF_INET, SOCK_DGRAM, 0);
    int b = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    int c = socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
    say("three sockets: %d %d %d\n", a, b, c);
    say("c: FD_CLOEXEC %d, O_NONBLOCK %d; a: FD_CLOEXEC %d, O_NONBLOCK %d\n", fcntl(c, F_GETFD) & FD_CLOEXEC,
        (fcntl(c, F_GETFL) & O_NONBLOCK) != 0, fcntl(a, F_GETFD) & FD_CLOEXEC, (fcntl(a, F_GETFL) & O_NONBLOCK) != 0);
    struct stat st;
    R("fstat(a)", fstat(a, &st));
    say("a is a socket: %d\n", S_ISSOCK(st.st_mode));
    R("lseek(a, 0, SEEK_CUR)", lseek(a, 0, SEEK_CUR));
    int ty = 0;
    l = sizeof ty;
    R("getsockopt(a, SOL_SOCKET, SO_TYPE)", getsockopt(a, SOL_SOCKET, SO_TYPE, &ty, &l));
    say("SO_TYPE %d len %d\n", ty, (int)l);
    R("setsockopt(a, SOL_SOCKET, 9999)", setsockopt(a, SOL_SOCKET, 9999, &one, sizeof one));
    l = sizeof one;
    R("getsockopt(a, SOL_SOCKET, 9999)", getsockopt(a, SOL_SOCKET, 9999, &one, &l));
    R("setsockopt(a, 9999, 1)", setsockopt(a, 9999, 1, &one, sizeof one));
    R("listen(a, 1)", listen(a, 1));
    R("accept(a)", accept(a, 0, 0));

    /* names before and after bind; the port table */
    name_line("getsockname(a) unbound", a, 0);
    name_line("getpeername(a) unconnected", a, 1);
    R("bind(a, 127.0.0.1:4001, 8 bytes)", bind(a, (struct sockaddr *)&a1, 8));
    unx.sin_family = AF_UNIX;
    R("bind(a, an AF_UNIX address)", bind(a, (struct sockaddr *)&unx, sizeof unx));
    R("bind(a, 10.9.9.9:4003)", bind(a, (struct sockaddr *)&far, sizeof far));
    R("bind(a, 127.0.0.1:4001)", bind(a, (struct sockaddr *)&a1, sizeof a1));
    R("bind(a) again", bind(a, (struct sockaddr *)&a2, sizeof a2));
    R("bind(b, 127.0.0.1:4001)", bind(b, (struct sockaddr *)&a1, sizeof a1));
    R("bind(b, 0.0.0.0:4001)", bind(b, (struct sockaddr *)&any1, sizeof any1));
    R("bind(b, 127.0.0.1:4002)", bind(b, (struct sockaddr *)&a2, sizeof a2));
    R("bind(c, 10.0.2.15:4001)", bind(c, (struct sockaddr *)&own1, sizeof own1));
    name_line("getsockname(a)", a, 0);
    name_line("getsockname(c)", c, 0);
    R("bind(1, 127.0.0.1:4001)", bind(1, (struct sockaddr *)&a1, sizeof a1));
    R("bind(99, 127.0.0.1:4001)", bind(99, (struct sockaddr *)&a1, sizeof a1));
    R("close(c)", close(c));

    /* sending: the refusals */
    int t = socket(AF_INET, SOCK_DGRAM, 0);
    N("send(t) with no peer", send(t, "x", 1, 0));
    N("write(t) with no peer", write(t, "x", 1));
    memset(big, 'B', sizeof big);
    N("sendto(t, 65508 bytes)", sendto(t, big, sizeof big, 0, (struct sockaddr *)&a1, sizeof a1));
    N("sendto(t, port 0)", sendto(t, "x", 1, 0, (struct sockaddr *)&p0, sizeof p0));
    N("sendto(t, a 4-byte address)", sendto(t, "x", 1, 0, (struct sockaddr *)&a1, 4));
    N("sendto(t, an AF_UNIX address)", sendto(t, "x", 1, 0, (struct sockaddr *)&unx, sizeof unx));
    N("sendto(1)", sendto(1, "", 0, 0, (struct sockaddr *)&a1, sizeof a1));
    struct sockaddr_in bc = sin_of("10.0.2.255", 9), all = sin_of("255.255.255.255", 9), off = sin_of("10.0.2.2", 9);
    N("sendto(t, 10.0.2.255) with no SO_BROADCAST", sendto(t, "x", 1, 0, (struct sockaddr *)&bc, sizeof bc));
    N("sendto(t, 255.255.255.255)", sendto(t, "x", 1, 0, (struct sockaddr *)&all, sizeof all));
    N("sendto(a, 10.0.2.2): a is bound to 127.0.0.1", sendto(a, "x", 1, 0, (struct sockaddr *)&off, sizeof off));
    R("close(t)", close(t));
    int s = socket(AF_INET, SOCK_DGRAM, 0);

    /* demultiplexing by port: b's datagram must not reach a */
    name_line("getsockname(s) before it sends", s, 0);
    N("sendto(s, \"to-b\", 127.0.0.1:4002)", sendto(s, "to-b", 4, 0, (struct sockaddr *)&a2, sizeof a2));
    name_line("getsockname(s) after", s, 0);
    recv_line("a, MSG_DONTWAIT", a, 64, MSG_DONTWAIT);
    recv_line("b", b, 64, 0);
    recv_line("b, MSG_DONTWAIT", b, 64, MSG_DONTWAIT);
    struct sockaddr_in zero = sin_of("0.0.0.0", 4002);
    N("sendto(s, \"zero\", 0.0.0.0:4002)", sendto(s, "zero", 4, 0, (struct sockaddr *)&zero, sizeof zero));
    recv_line("b", b, 64, 0);

    /* the default peer, and filtering by it */
    R("connect(b, 127.0.0.1:4001)", connect(b, (struct sockaddr *)&a1, sizeof a1));
    name_line("getpeername(b)", b, 1);
    N("sendto(s, \"stranger\", b)", sendto(s, "stranger", 8, 0, (struct sockaddr *)&a2, sizeof a2));
    recv_line("b, MSG_DONTWAIT (a stranger wrote)", b, 64, MSG_DONTWAIT);
    N("sendto(a, \"peer\", b)", sendto(a, "peer", 4, 0, (struct sockaddr *)&a2, sizeof a2));
    recv_line("b", b, 64, 0);
    N("write(b, \"hi a\")", write(b, "hi a", 4));
    recv_line("a", a, 64, 0);
    N("send(b, \"again\")", send(b, "again", 5, 0));
    char rd[16];
    long n = read(a, rd, sizeof rd);
    say("read(a): %ld bytes \"%.*s\"\n", n, n > 0 ? (int)n : 0, rd);
    memset(&un, 0, sizeof un);
    un.sa_family = AF_UNSPEC;
    R("connect(b, AF_UNSPEC)", connect(b, &un, sizeof un));
    name_line("getpeername(b)", b, 1);
    name_line("getsockname(b)", b, 0);
    N("sendto(s, \"stranger2\", b)", sendto(s, "stranger2", 9, 0, (struct sockaddr *)&a2, sizeof a2));
    recv_line("b", b, 64, 0);

    /* truncation, MSG_TRUNC, MSG_PEEK */
    memset(big, 'T', 100);
    N("sendto(s, 100 bytes, b)", sendto(s, big, 100, 0, (struct sockaddr *)&a2, sizeof a2));
    recv_line("b, a 10-byte buffer", b, 10, 0);
    recv_line("b, MSG_DONTWAIT", b, 64, MSG_DONTWAIT);
    N("sendto(s, 100 bytes, b)", sendto(s, big, 100, 0, (struct sockaddr *)&a2, sizeof a2));
    recv_line("b, a 10-byte buffer, MSG_TRUNC", b, 10, MSG_TRUNC);
    N("sendto(s, \"peek\", b)", sendto(s, "peek", 4, 0, (struct sockaddr *)&a2, sizeof a2));
    recv_line("b, MSG_PEEK", b, 64, MSG_PEEK);
    recv_line("b", b, 64, 0);
    N("sendto(s, 0 bytes, b)", sendto(s, "", 0, 0, (struct sockaddr *)&a2, sizeof a2));
    recv_line("b", b, 64, 0);

    /* a duplicate shares the socket; the port is free after the last close */
    int d = dup(b);
    N("sendto(s, \"dup\", b)", sendto(s, "dup", 3, 0, (struct sockaddr *)&a2, sizeof a2));
    recv_line("d = dup(b)", d, 64, 0);
    R("close(b)", close(b));
    N("sendto(s, \"kept\", b's port)", sendto(s, "kept", 4, 0, (struct sockaddr *)&a2, sizeof a2));
    recv_line("d", d, 64, 0);
    int e = socket(AF_INET, SOCK_DGRAM, 0);
    R("bind(e, 127.0.0.1:4002) while d is open", bind(e, (struct sockaddr *)&a2, sizeof a2));
    R("close(d)", close(d));
    R("bind(e, 127.0.0.1:4002) after", bind(e, (struct sockaddr *)&a2, sizeof a2));

    /* the receive timeout: nothing comes, the call ends */
    struct timeval tv = {0, 200000};
    R("setsockopt(e, SO_RCVTIMEO, 0.2 s)", setsockopt(e, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv));
    recv_line("e, nothing sent", e, 64, 0);
    R("fcntl(e, F_SETFL, O_NONBLOCK)", fcntl(e, F_SETFL, O_NONBLOCK));
    n = read(e, rd, sizeof rd);
    say("read(e): %s\n", res(n, rb, sizeof rb, 1));
    R("close(a)", close(a));
    R("close(e)", close(e));
    R("close(s)", close(s));
    name_line("getsockname(s) closed", s, 0);
    return 0;
}
