/* udpclient — a UDP client (px22): a socket connected to IP:PORT (the
   default peer) that writes and reads, then one with no peer that names
   its destination each time. The server answers each datagram with its
   bytes reversed. A receive that waits more than 5 s ends the program.

     udpclient IP PORT */
#include "say.h"
#include <stdlib.h>
#include <sys/time.h>

static char ab[64];

static void rev_ok(const char *what, const char *sent, size_t n, const char *got, ssize_t m)
{
    int ok = m == (ssize_t)n;
    for (size_t i = 0; ok && i < n; i++)
        ok = got[i] == sent[n - 1 - i];
    say("udpclient: %s: %ld bytes back, %s\n", what, (long)m, ok ? "the datagram reversed" : "NOT the datagram reversed");
}

int main(int argc, char **argv)
{
    if (argc != 3) {
        say("usage: udpclient IP PORT\n");
        return 2;
    }
    struct sockaddr_in srv = sin_of(argv[1], atoi(argv[2])), me, peer, from;
    struct timeval tv = {5, 0};
    char got[2048], big[1472];
    socklen_t l;

    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0 || setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv) < 0 || connect(fd, (struct sockaddr *)&srv, sizeof srv) < 0) {
        say("udpclient: socket, SO_RCVTIMEO or connect: %s\n", ename(errno));
        return 1;
    }
    l = sizeof me;
    getsockname(fd, (struct sockaddr *)&me, &l);
    say("udpclient: local %s\n", aname(&me, ab, sizeof ab));
    l = sizeof peer;
    getpeername(fd, (struct sockaddr *)&peer, &l);
    say("udpclient: peer %s\n", aname(&peer, ab, sizeof ab));
    const char *msgs[] = {"hello from PAX", "x", "the third datagram, on a connected socket"};
    for (int i = 0; i < 3; i++) {
        size_t n = strlen(msgs[i]);
        if (write(fd, msgs[i], n) != (ssize_t)n) {
            say("udpclient: write: %s\n", ename(errno));
            return 1;
        }
        ssize_t m = read(fd, got, sizeof got);
        if (m < 0) {
            say("udpclient: read: %s\n", ename(errno));
            return 1;
        }
        say("udpclient: wrote \"%s\", read \"%.*s\"\n", msgs[i], (int)m, got);
    }
    for (size_t i = 0; i < sizeof big; i++)
        big[i] = 'a' + i % 23;
    if (send(fd, big, sizeof big, 0) != (ssize_t)sizeof big) {
        say("udpclient: send of 1472: %s\n", ename(errno));
        return 1;
    }
    rev_ok("1472 bytes (the most one frame carries)", big, sizeof big, got, recv(fd, got, sizeof got, 0));
    close(fd);

    /* no default peer: sendto and recvfrom */
    fd = socket(AF_INET, SOCK_DGRAM, 0);
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv);
    const char *m2 = "sendto, no connect";
    if (sendto(fd, m2, strlen(m2), 0, (struct sockaddr *)&srv, sizeof srv) != (ssize_t)strlen(m2)) {
        say("udpclient: sendto: %s\n", ename(errno));
        return 1;
    }
    l = sizeof me;
    getsockname(fd, (struct sockaddr *)&me, &l);
    say("udpclient: local %s\n", aname(&me, ab, sizeof ab));
    l = sizeof from;
    ssize_t m = recvfrom(fd, got, sizeof got, 0, (struct sockaddr *)&from, &l);
    if (m < 0) {
        say("udpclient: recvfrom: %s\n", ename(errno));
        return 1;
    }
    say("udpclient: sent \"%s\", received \"%.*s\" from %s\n", m2, (int)m, got, aname(&from, ab, sizeof ab));
    close(fd);
    say("udpclient: done\n");
    return 0;
}
