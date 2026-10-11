/* tcpclient — a TCP client (px23): connect to an echo server at
   IP:PORT, say where both ends are, send the stream pattern in pieces
   of 1, 13, 1460, 1461, 4096 and 32768 bytes and read each back, then
   close this end's half and read what the server says after it (a
   half-close exchange from the active side).

     tcpclient IP PORT */
#include "say.h"
#include <stdlib.h>

int main(int argc, char **argv)
{
    if (argc != 3) {
        say("usage: tcpclient IP PORT\n");
        return 2;
    }
    static unsigned char out[32768], in[32768];
    static const size_t sizes[] = {1, 13, 1460, 1461, 4096, 32768};
    char ab[64], bb[64];
    struct sockaddr_in srv = sin_of(argv[1], atoi(argv[2])), me, peer;
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0 || connect(fd, (struct sockaddr *)&srv, sizeof srv) < 0) {
        say("tcpclient: socket or connect: %s\n", ename(errno));
        return 1;
    }
    socklen_t l = sizeof me;
    getsockname(fd, (struct sockaddr *)&me, &l);
    l = sizeof peer;
    getpeername(fd, (struct sockaddr *)&peer, &l);
    say("tcpclient: connected: this end %s, the other %s\n", aname(&me, ab, sizeof ab), aname(&peer, bb, sizeof bb));
    unsigned long long off = 0;
    unsigned long total = 0, crc = 0;
    int bad = 0;
    for (size_t k = 0; k < sizeof sizes / sizeof sizes[0]; k++) {
        size_t n = sizes[k];
        pattern_fill(out, off, n);
        off += n;
        if (send_all(fd, out, n) != (ssize_t)n) {
            say("tcpclient: send %lu: %s\n", (unsigned long)n, ename(errno));
            return 1;
        }
        ssize_t m = recv_all(fd, in, n);
        if (m < 0) {
            say("tcpclient: recv: %s\n", ename(errno));
            return 1;
        }
        int right = m == (ssize_t)n && memcmp(in, out, n) == 0;
        crc = crc32_of(crc, in, m);
        total += m;
        bad += !right;
        say("tcpclient: %lu bytes sent, %ld came back, %s\n", (unsigned long)n, (long)m, right ? "the same" : "NOT the same");
    }
    if (shutdown(fd, SHUT_WR) < 0) {
        say("tcpclient: shutdown: %s\n", ename(errno));
        return 1;
    }
    char tail[128];
    ssize_t t = recv_all(fd, tail, sizeof tail - 1);
    if (t < 0) {
        say("tcpclient: after the half-close: %s\n", ename(errno));
        return 1;
    }
    while (t > 0 && tail[t - 1] == '\n')
        t--;
    say("tcpclient: %lu bytes in all, crc %08lx; after this end's half closed the server said \"%.*s\"\n", total, crc, (int)t, tail);
    close(fd);
    return bad ? 1 : 0;
}
