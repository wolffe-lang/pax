/* tcpend — how a connection that cannot go on ends (px23): connect to
   IP:PORT, send five bytes, read, send again, and say what each call
   answered and what SO_ERROR holds. What the other end does decides
   the lines: nobody listening (the connect is refused), nobody there
   at all (with `syncnt N`, TCP_SYNCNT: the connect times out after N
   retransmissions), a reset after the data, or silence after the
   handshake (with `timeout MS`, TCP_USER_TIMEOUT: the read gives up).

     tcpend IP PORT [syncnt N] [timeout MS] */
#include "say.h"
#include <netinet/tcp.h>
#include <stdlib.h>

static char rb[64];

int main(int argc, char **argv)
{
    if (argc != 3 && argc != 5 && argc != 7) {
        say("usage: tcpend IP PORT [syncnt N] [timeout MS]\n");
        return 2;
    }
    struct sockaddr_in srv = sin_of(argv[1], atoi(argv[2]));
    int fd = socket(AF_INET, SOCK_STREAM, 0), v;
    for (int i = 3; i + 1 < argc; i += 2) {
        v = atoi(argv[i + 1]);
        int opt = strcmp(argv[i], "syncnt") == 0 ? TCP_SYNCNT : TCP_USER_TIMEOUT;
        if (setsockopt(fd, IPPROTO_TCP, opt, &v, sizeof v) < 0)
            say("tcpend: setsockopt %s: %s\n", argv[i], ename(errno));
    }
    long r = connect(fd, (struct sockaddr *)&srv, sizeof srv);
    say("tcpend: connect: %s\n", res(r, rb, sizeof rb, 0));
    if (r < 0) {
        socklen_t l = sizeof v;
        getsockopt(fd, SOL_SOCKET, SO_ERROR, &v, &l);
        say("tcpend: SO_ERROR after it: %s\n", ename(v));
        close(fd);
        return 0;
    }
    r = send(fd, "hello", 5, MSG_NOSIGNAL);
    say("tcpend: send: %s\n", res(r, rb, sizeof rb, 1));
    char buf[64];
    r = recv(fd, buf, sizeof buf, 0);
    if (r > 0)
        say("tcpend: recv: %ld bytes \"%.*s\"\n", r, (int)r, buf);
    else
        say("tcpend: recv: %s\n", res(r, rb, sizeof rb, 1));
    r = send(fd, "again", 5, MSG_NOSIGNAL);
    say("tcpend: send again: %s\n", res(r, rb, sizeof rb, 1));
    socklen_t l = sizeof v;
    getsockopt(fd, SOL_SOCKET, SO_ERROR, &v, &l);
    say("tcpend: SO_ERROR: %s\n", ename(v));
    close(fd);
    return 0;
}
