/* udpfill — two of the kernel's bounds (px22). A receive queue filled
   past its bound: 200 datagrams of 1000 bytes sent over loopback to a
   socket nobody reads, then the socket read until it is empty; how
   many were kept is the receiving kernel's (PAX: 65536 bytes a socket,
   each datagram taking its length rounded up to 8 and 8 more; Linux:
   SO_RCVBUF's accounting). And a datagram of 1473 bytes, one more than
   an Ethernet frame carries: Linux sends it (in fragments where it
   must), PAX answers EMSGSIZE. So this program's output is held to a
   file of PAX's own (udpfill.expect), not to Linux's. */
#include "say.h"

int main(void)
{
    char buf[1000];
    int rx = socket(AF_INET, SOCK_DGRAM, 0), tx = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in at = sin_of("127.0.0.1", 4020);
    if (rx < 0 || tx < 0 || bind(rx, (struct sockaddr *)&at, sizeof at) < 0) {
        say("udpfill: socket or bind: %s\n", ename(errno));
        return 1;
    }
    int sent = 0;
    for (int i = 0; i < 200; i++) {
        memset(buf, 'a' + i % 26, sizeof buf);
        buf[0] = i;
        if (sendto(tx, buf, sizeof buf, 0, (struct sockaddr *)&at, sizeof at) == (ssize_t)sizeof buf)
            sent++;
    }
    int kept = 0, in_order = 1, last = -1;
    for (;;) {
        ssize_t n = recv(rx, buf, sizeof buf, MSG_DONTWAIT);
        if (n < 0)
            break;
        if (n != (ssize_t)sizeof buf || (unsigned char)buf[0] != kept)
            in_order = 0;
        last = (unsigned char)buf[0];
        kept++;
    }
    say("udpfill: %d sent, %d kept (the first %d, %s), the last numbered %d; then -%s\n", sent, kept, kept,
        in_order ? "in order" : "NOT in order", last, ename(errno));
    /* One byte more than a frame carries: Linux fragments, PAX refuses. */
    char big[1473];
    memset(big, 'x', sizeof big);
    ssize_t r = sendto(tx, big, sizeof big, 0, (struct sockaddr *)&at, sizeof at);
    if (r < 0)
        say("udpfill: 1473 bytes in one datagram: -%s\n", ename(errno));
    else
        say("udpfill: 1473 bytes in one datagram: %ld sent\n", (long)r);
    return 0;
}
