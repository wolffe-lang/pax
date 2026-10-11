/* udpecho — a UDP echo server (px22; RFC 862's service): bind PORT on
   every address, tell READY-IP:READY-PORT it is listening, then send
   every datagram back to where it came from until one says "quit"
   (echoed too). The first SHOWN datagrams get a line each; the end is
   one line of totals with a sum over every byte echoed.

     udpecho PORT READY-IP READY-PORT */
#include "say.h"
#include <stdlib.h>

#define SHOWN 12

int main(int argc, char **argv)
{
    if (argc != 4) {
        say("usage: udpecho PORT READY-IP READY-PORT\n");
        return 2;
    }
    char ab[64], buf[2048];
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in me = sin_of("0.0.0.0", atoi(argv[1])), ready = sin_of(argv[2], atoi(argv[3])), from;
    if (fd < 0 || bind(fd, (struct sockaddr *)&me, sizeof me) < 0) {
        say("udpecho: socket or bind: %s\n", ename(errno));
        return 1;
    }
    socklen_t l = sizeof me;
    getsockname(fd, (struct sockaddr *)&me, &l);
    say("udpecho: listening on %s\n", aname(&me, ab, sizeof ab));
    if (sendto(fd, "ready", 5, 0, (struct sockaddr *)&ready, sizeof ready) != 5) {
        say("udpecho: ready: %s\n", ename(errno));
        return 1;
    }
    unsigned long count = 0, bytes = 0, sum = 0;
    for (;;) {
        l = sizeof from;
        ssize_t n = recvfrom(fd, buf, sizeof buf, 0, (struct sockaddr *)&from, &l);
        if (n < 0) {
            say("udpecho: recvfrom: %s\n", ename(errno));
            return 1;
        }
        count++;
        bytes += n;
        for (ssize_t i = 0; i < n; i++)
            sum = (sum * 31 + (unsigned char)buf[i]) & 0xffffffff;
        if (count <= SHOWN) {
            char ip[32];
            inet_ntop(AF_INET, &from.sin_addr, ip, sizeof ip);
            say("udpecho: %lu: %ld bytes from %s\n", count, (long)n, ip);
        }
        ssize_t w = sendto(fd, buf, n, 0, (struct sockaddr *)&from, l);
        if (w != n) {
            say("udpecho: sendto: %ld of %ld: %s\n", (long)w, (long)n, ename(errno));
            return 1;
        }
        if (n == 4 && memcmp(buf, "quit", 4) == 0)
            break;
    }
    say("udpecho: %lu datagrams, %lu bytes echoed, sum %08lx\n", count, bytes, sum);
    close(fd);
    return 0;
}
