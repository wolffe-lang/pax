/* udpsoak — N datagrams out and N back, one at a time (px22): datagram
   i is 64 bytes, its first four the number i, and the server answers
   each with its bytes reversed. One line at the end.

     udpsoak IP PORT N */
#include "say.h"
#include <stdlib.h>
#include <sys/time.h>

int main(int argc, char **argv)
{
    if (argc != 4) {
        say("usage: udpsoak IP PORT N\n");
        return 2;
    }
    struct sockaddr_in srv = sin_of(argv[1], atoi(argv[2]));
    struct timeval tv = {5, 0};
    long n = atol(argv[3]), i, good = 0;
    unsigned char out[64], in[128];
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0 || setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv) < 0 || connect(fd, (struct sockaddr *)&srv, sizeof srv) < 0) {
        say("udpsoak: socket, SO_RCVTIMEO or connect: %s\n", ename(errno));
        return 1;
    }
    for (i = 0; i < n; i++) {
        for (int k = 0; k < 64; k++)
            out[k] = (unsigned char)(i * 7 + k * 13);
        out[0] = i >> 24, out[1] = i >> 16, out[2] = i >> 8, out[3] = i;
        if (send(fd, out, sizeof out, 0) != (ssize_t)sizeof out) {
            say("udpsoak: send %ld: %s\n", i, ename(errno));
            return 1;
        }
        ssize_t m = recv(fd, in, sizeof in, 0);
        if (m < 0) {
            say("udpsoak: recv %ld: %s\n", i, ename(errno));
            return 1;
        }
        int ok = m == 64;
        for (int k = 0; ok && k < 64; k++)
            ok = in[k] == out[63 - k];
        good += ok;
    }
    say("udpsoak: %ld datagrams sent, %ld answers, %ld right\n", n, i, good);
    close(fd);
    return good == n ? 0 : 1;
}
