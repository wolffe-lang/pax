/* resolve — a stub resolver (px22; RFC 1035 §4): one question, NAME's A
   records in class IN, recursion desired, sent to SERVER port 53 over
   UDP; the answer's header checked against the question's and each A
   record printed. Two tries of 3 s each.

     resolve SERVER NAME */
#include "say.h"
#include <stdlib.h>
#include <sys/time.h>

#define ID 0x5058

/* Skip the name at `o` (labels, or a pointer that ends it): the offset
   past it, or -1 when it runs off the message. */
static int skip_name(const unsigned char *m, int len, int o)
{
    while (o < len) {
        int c = m[o];
        if (c == 0)
            return o + 1;
        if ((c & 0xc0) == 0xc0)
            return o + 2 <= len ? o + 2 : -1;
        if (c & 0xc0)
            return -1;
        o += 1 + c;
    }
    return -1;
}

int main(int argc, char **argv)
{
    if (argc != 3) {
        say("usage: resolve SERVER NAME\n");
        return 2;
    }
    const char *name = argv[2];
    unsigned char q[300], m[1500];
    char ab[64];
    int n = 0;
    q[n++] = ID >> 8, q[n++] = ID & 0xff;
    q[n++] = 0x01, q[n++] = 0x00; /* a query, recursion desired */
    q[n++] = 0, q[n++] = 1;       /* one question */
    memset(q + n, 0, 6), n += 6;
    for (const char *p = name; *p;) {
        const char *dot = strchr(p, '.');
        int l = dot ? (int)(dot - p) : (int)strlen(p);
        if (l < 1 || l > 63 || n + l + 6 > (int)sizeof q) {
            say("resolve: %s is not a name this program can ask for\n", name);
            return 2;
        }
        q[n++] = l;
        memcpy(q + n, p, l), n += l;
        p += l + (dot ? 1 : 0);
    }
    q[n++] = 0;
    q[n++] = 0, q[n++] = 1; /* type A */
    q[n++] = 0, q[n++] = 1; /* class IN */

    struct sockaddr_in srv = sin_of(argv[1], 53), from;
    struct timeval tv = {3, 0};
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0 || setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv) < 0) {
        say("resolve: socket or SO_RCVTIMEO: %s\n", ename(errno));
        return 1;
    }
    say("resolve: asking %s for %s (A, IN), %d bytes\n", argv[1], name, n);
    ssize_t len = -1;
    for (int try = 0; try < 2 && len < 0; try++) {
        if (sendto(fd, q, n, 0, (struct sockaddr *)&srv, sizeof srv) != n) {
            say("resolve: sendto: %s\n", ename(errno));
            return 1;
        }
        socklen_t l = sizeof from;
        len = recvfrom(fd, m, sizeof m, 0, (struct sockaddr *)&from, &l);
        if (len < 0 && errno != EAGAIN) {
            say("resolve: recvfrom: %s\n", ename(errno));
            return 1;
        }
    }
    if (len < 0) {
        say("resolve: no answer from %s in 6 s\n", argv[1]);
        return 1;
    }
    if (len < 12 || m[0] != (ID >> 8) || m[1] != (ID & 0xff) || !(m[2] & 0x80) || len < n || memcmp(m + 12, q + 12, n - 12) != 0) {
        say("resolve: %ld bytes from %s that do not answer the question\n", (long)len, aname(&from, ab, sizeof ab));
        return 1;
    }
    int rcode = m[3] & 15, an = m[6] << 8 | m[7];
    say("resolve: answer from %s: rcode %d, %d answers\n", aname(&from, ab, sizeof ab), rcode, an);
    int o = n, found = 0;
    for (int i = 0; i < an; i++) {
        o = skip_name(m, len, o);
        if (o < 0 || o + 10 > len)
            break;
        int type = m[o] << 8 | m[o + 1], class = m[o + 2] << 8 | m[o + 3];
        unsigned long ttl = (unsigned long)m[o + 4] << 24 | m[o + 5] << 16 | m[o + 6] << 8 | m[o + 7];
        int rd = m[o + 8] << 8 | m[o + 9];
        o += 10;
        if (o + rd > len)
            break;
        if (type == 1 && class == 1 && rd == 4) {
            say("resolve: %s is %d.%d.%d.%d (ttl %lu)\n", name, m[o], m[o + 1], m[o + 2], m[o + 3], ttl);
            found++;
        } else {
            say("resolve: a record of type %d, %d bytes\n", type, rd);
        }
        o += rd;
    }
    close(fd);
    return rcode == 0 && found > 0 ? 0 : 1;
}
