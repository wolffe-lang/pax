/* udphold — a receive queue filled from the wire (px22): bind PORT, tell
   READY-IP:READY-PORT so, sleep a second and a half while the other end
   sends 60 datagrams of 1472 bytes, then read until the socket is
   empty. How many waited is the receiving kernel's bound (PAX: 65536
   bytes a socket, 1480 a datagram of this size: 44), so this program's
   output is held to a file of PAX's own (udphold.expect), not to
   Linux's.

     udphold PORT READY-IP READY-PORT */
#include "say.h"
#include <stdlib.h>
#include <time.h>

int main(int argc, char **argv)
{
    if (argc != 4) {
        say("usage: udphold PORT READY-IP READY-PORT\n");
        return 2;
    }
    char buf[2048];
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in me = sin_of("0.0.0.0", atoi(argv[1])), ready = sin_of(argv[2], atoi(argv[3]));
    if (fd < 0 || bind(fd, (struct sockaddr *)&me, sizeof me) < 0 || sendto(fd, "ready", 5, 0, (struct sockaddr *)&ready, sizeof ready) != 5) {
        say("udphold: socket, bind or ready: %s\n", ename(errno));
        return 1;
    }
    struct timespec nap = {1, 500000000};
    nanosleep(&nap, 0);
    int kept = 0, in_order = 1;
    for (;;) {
        ssize_t n = recv(fd, buf, sizeof buf, MSG_DONTWAIT);
        if (n < 0)
            break;
        if (n != 1472 || (unsigned char)buf[0] != kept)
            in_order = 0;
        kept++;
    }
    say("udphold: %d datagrams of 1472 bytes waited (the first %d, %s); then -%s\n", kept, kept, in_order ? "in order" : "NOT in order", ename(errno));
    close(fd);
    return 0;
}
