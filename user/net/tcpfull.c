/* tcpfull — a listen queue that nobody empties (px23): a listener with
   a backlog of 2 on 127.0.0.1 port 4060 and six clients, one after
   another, each giving up after one retransmitted SYN (TCP_SYNCNT 1).
   How many get in is the kernel's bound (Linux: three; PAX takes the
   same). Then the queue is emptied and every connection that got in is
   there. */
#include "say.h"
#include <netinet/tcp.h>

int main(void)
{
    int one = 1, fd = socket(AF_INET, SOCK_STREAM, 0), c[6], in = 0;
    struct sockaddr_in me = sin_of("127.0.0.1", 4060);
    if (fd < 0 || setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one) < 0
        || bind(fd, (struct sockaddr *)&me, sizeof me) < 0 || listen(fd, 2) < 0) {
        say("tcpfull: socket, bind or listen: %s\n", ename(errno));
        return 1;
    }
    for (int i = 0; i < 6; i++) {
        c[i] = socket(AF_INET, SOCK_STREAM, 0);
        setsockopt(c[i], IPPROTO_TCP, TCP_SYNCNT, &one, sizeof one);
        int r = connect(c[i], (struct sockaddr *)&me, sizeof me);
        say("tcpfull: client %d: %s\n", i + 1, r < 0 ? ename(errno) : "connected");
        if (r == 0) {
            in++;
            send(c[i], "x", 1, MSG_NOSIGNAL);
        }
    }
    say("tcpfull: %d of 6 got in with a backlog of 2 and nobody accepting\n", in);
    int taken = 0;
    for (int i = 0; i < in; i++) {
        int s = accept(fd, 0, 0);
        char x;
        if (s >= 0 && recv(s, &x, 1, 0) == 1 && x == 'x')
            taken++;
        close(s);
    }
    say("tcpfull: %d accepted afterwards, each with its byte\n", taken);
    for (int i = 0; i < 6; i++)
        close(c[i]);
    close(fd);
    return 0;
}
