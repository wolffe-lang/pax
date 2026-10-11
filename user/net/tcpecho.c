/* tcpecho — a TCP echo server (px23; RFC 862's service on a stream):
   listen on PORT on every address, tell READY-IP:READY-PORT so with one
   UDP datagram ("ready"), then take connections one at a time: every
   byte goes back where it came from until the other end closes its
   half, then one line more goes back — what was seen — and this end
   closes (a half-close exchange from the passive side). A connection
   whose first bytes are "quit" is the last. With `fork` each
   connection is served by a child of its own, which the parent waits
   for (its status 7 says "quit"). The first SHOWN connections get a line each; the end is one
   line of totals.

     tcpecho PORT READY-IP READY-PORT [fork] */
#include "say.h"
#include <stdlib.h>
#include <sys/wait.h>

#define SHOWN 12

/* Serve one connection: 0, or 1 when it said "quit"; -1 on an error. */
static int serve(int fd, unsigned long k, unsigned long *total)
{
    static unsigned char buf[16384];
    unsigned long bytes = 0, crc = 0;
    int quit = 0;
    for (;;) {
        ssize_t n = recv(fd, buf, sizeof buf, 0);
        if (n < 0) {
            if (k <= SHOWN)
                say("tcpecho: %lu: recv: %s after %lu bytes\n", k, ename(errno), bytes);
            return -1;
        }
        if (n == 0)
            break;
        if (bytes == 0 && n >= 4 && memcmp(buf, "quit", 4) == 0)
            quit = 1;
        crc = crc32_of(crc, buf, n);
        bytes += n;
        if (send_all(fd, buf, n) != n) {
            if (k <= SHOWN)
                say("tcpecho: %lu: send: %s after %lu bytes\n", k, ename(errno), bytes);
            return -1;
        }
    }
    char tail[96];
    int m = snprintf(tail, sizeof tail, "eof after %lu bytes, crc %08lx\n", bytes, crc);
    if (send_all(fd, tail, m) != m) {
        if (k <= SHOWN)
            say("tcpecho: %lu: the last line: %s\n", k, ename(errno));
        return -1;
    }
    if (k <= SHOWN)
        say("tcpecho: %lu: %lu bytes echoed, crc %08lx\n", k, bytes, crc);
    *total += bytes;
    return quit;
}

int main(int argc, char **argv)
{
    if (argc != 4 && !(argc == 5 && strcmp(argv[4], "fork") == 0)) {
        say("usage: tcpecho PORT READY-IP READY-PORT [fork]\n");
        return 2;
    }
    int forking = argc == 5, one = 1;
    char ab[64];
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in me = sin_of("0.0.0.0", atoi(argv[1])), ready = sin_of(argv[2], atoi(argv[3])), from;
    if (fd < 0 || setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one) < 0
        || bind(fd, (struct sockaddr *)&me, sizeof me) < 0 || listen(fd, 8) < 0) {
        say("tcpecho: socket, bind or listen: %s\n", ename(errno));
        return 1;
    }
    socklen_t l = sizeof me;
    getsockname(fd, (struct sockaddr *)&me, &l);
    say("tcpecho: listening on %s%s\n", aname(&me, ab, sizeof ab), forking ? ", a child a connection" : "");
    int u = socket(AF_INET, SOCK_DGRAM, 0);
    if (u < 0 || sendto(u, "ready", 5, 0, (struct sockaddr *)&ready, sizeof ready) != 5) {
        say("tcpecho: ready: %s\n", ename(errno));
        return 1;
    }
    close(u);
    unsigned long count = 0, bad = 0, total = 0;
    for (;;) {
        l = sizeof from;
        int c = accept(fd, (struct sockaddr *)&from, &l);
        if (c < 0) {
            say("tcpecho: accept: %s\n", ename(errno));
            return 1;
        }
        count++;
        if (count <= SHOWN) {
            char ip[32];
            inet_ntop(AF_INET, &from.sin_addr, ip, sizeof ip);
            say("tcpecho: %lu: a connection from %s\n", count, ip);
        }
        int r;
        if (forking) {
            pid_t pid = fork();
            if (pid < 0) {
                say("tcpecho: fork: %s\n", ename(errno));
                return 1;
            }
            if (pid == 0) {
                close(fd);
                unsigned long t = 0;
                r = serve(c, count, &t);
                close(c);
                _exit(r < 0 ? 9 : r ? 7 : 0);
            }
            close(c);
            int st = 0;
            waitpid(pid, &st, 0);
            r = WIFEXITED(st) ? (WEXITSTATUS(st) == 7 ? 1 : WEXITSTATUS(st) == 0 ? 0 : -1) : -1;
            if (count <= SHOWN)
                say("tcpecho: %lu: its child ended with status %d\n", count, WIFEXITED(st) ? WEXITSTATUS(st) : -1);
        } else {
            r = serve(c, count, &total);
            close(c);
        }
        if (r < 0)
            bad++;
        if (r == 1)
            break;
    }
    if (forking)
        say("tcpecho: %lu connections, %lu ended badly\n", count, bad);
    else
        say("tcpecho: %lu connections, %lu ended badly, %lu bytes echoed\n", count, bad, total);
    close(fd);
    return 0;
}
