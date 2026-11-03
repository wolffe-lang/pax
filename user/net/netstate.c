/* netstate — what a program sees of the network's configuration (px89):
   after SECS seconds (0: at once), the bytes of /etc/resolv.conf, one
   line of output per line of the file, or that it is absent or empty.
   The kernel's DHCP client writes the file; this reads it the way any
   program would, through open(2) and read(2).

     netstate SECS */
#include "say.h"
#include <fcntl.h>
#include <stdlib.h>
#include <time.h>

int main(int argc, char **argv)
{
    if (argc != 2) {
        say("usage: netstate SECS\n");
        return 2;
    }
    int secs = atoi(argv[1]);
    if (secs > 0) {
        struct timespec t = {secs, 0};
        while (nanosleep(&t, &t) != 0 && errno == EINTR)
            ;
    }
    int fd = open("/etc/resolv.conf", O_RDONLY);
    if (fd < 0) {
        say("netstate: /etc/resolv.conf: %s\n", ename(errno));
        return 1;
    }
    char b[4096];
    size_t n = 0;
    for (;;) {
        ssize_t r = read(fd, b + n, sizeof b - 1 - n);
        if (r < 0) {
            say("netstate: read: %s\n", ename(errno));
            return 1;
        }
        if (r == 0 || n + r >= sizeof b - 1)
            break;
        n += r;
    }
    close(fd);
    b[n] = 0;
    if (n == 0) {
        say("netstate: /etc/resolv.conf: empty\n");
        return 0;
    }
    char *line = b;
    while (*line) {
        char *e = strchr(line, '\n');
        if (e)
            *e = 0;
        say("netstate: /etc/resolv.conf: %s\n", line);
        if (!e)
            break;
        line = e + 1;
    }
    return 0;
}
