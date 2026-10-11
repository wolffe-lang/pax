/* udploop — a client and a server on one machine, over loopback (px22):
   the parent binds PORT on every address and answers each datagram with
   "re: " and its text; its child, made by fork, asks it through
   127.0.0.1 and then through the machine's own address, and says what
   came back and from where. Each waits for the other, so the lines come
   in one order. */
#include "say.h"
#include <stdlib.h>
#include <sys/time.h>
#include <sys/wait.h>

#define PORT 4010
static char ab[64], bb[64];

static int client(const char *own)
{
    struct timeval tv = {5, 0};
    const char *to[] = {"127.0.0.1", own, "127.0.0.1"};
    const char *text[] = {"through 127.0.0.1", "through this machine's own address", "bye"};
    char got[256];
    for (int i = 0; i < 3; i++) {
        int fd = socket(AF_INET, SOCK_DGRAM, 0);
        struct sockaddr_in dst = sin_of(to[i], PORT), from, me;
        socklen_t l = sizeof from;
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv);
        if (sendto(fd, text[i], strlen(text[i]), 0, (struct sockaddr *)&dst, sizeof dst) < 0) {
            say("client: sendto %s: %s\n", to[i], ename(errno));
            return 1;
        }
        ssize_t n = recvfrom(fd, got, sizeof got, 0, (struct sockaddr *)&from, &l);
        if (n < 0) {
            say("client: recvfrom: %s\n", ename(errno));
            return 1;
        }
        l = sizeof me;
        getsockname(fd, (struct sockaddr *)&me, &l);
        say("client: \"%.*s\" from %s; this end is %s\n", (int)n, got, aname(&from, ab, sizeof ab), aname(&me, bb, sizeof bb));
        close(fd);
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *own = argc > 1 ? argv[1] : "10.0.2.15";
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in me = sin_of("0.0.0.0", PORT), from;
    if (fd < 0 || bind(fd, (struct sockaddr *)&me, sizeof me) < 0) {
        say("server: socket or bind: %s\n", ename(errno));
        return 1;
    }
    say("server: bound %s\n", aname(&me, ab, sizeof ab));
    pid_t pid = fork();
    if (pid < 0) {
        say("server: fork: %s\n", ename(errno));
        return 1;
    }
    if (pid == 0) {
        close(fd); /* the child's copy: the parent's socket stays bound */
        _exit(client(own));
    }
    char buf[256], out[300];
    for (;;) {
        socklen_t l = sizeof from;
        ssize_t n = recvfrom(fd, buf, sizeof buf, 0, (struct sockaddr *)&from, &l);
        if (n < 0) {
            say("server: recvfrom: %s\n", ename(errno));
            return 1;
        }
        say("server: \"%.*s\" from %s\n", (int)n, buf, aname(&from, ab, sizeof ab));
        int m = snprintf(out, sizeof out, "re: %.*s", (int)n, buf);
        if (sendto(fd, out, m, 0, (struct sockaddr *)&from, l) != m) {
            say("server: sendto: %s\n", ename(errno));
            return 1;
        }
        if (n == 3 && memcmp(buf, "bye", 3) == 0)
            break;
    }
    int st = 0;
    waitpid(pid, &st, 0);
    say("server: the client ended with status %d\n", WIFEXITED(st) ? WEXITSTATUS(st) : -1);
    close(fd);
    return 0;
}
