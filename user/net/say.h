/* say.h — what the network witnesses share (px22, px23, px24): one line to
   descriptor 1 with write(2) and no stdio buffer (a fork must not copy
   unwritten text), errno by its name, sockaddr_in helpers, and (px23)
   the stream witnesses' byte pattern and its CRC-32. */
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static void say(const char *fmt, ...)
{
    char b[768];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    if (n > (int)sizeof b - 1)
        n = sizeof b - 1;
    int off = 0;
    while (off < n) {
        ssize_t w = write(1, b + off, n - off);
        if (w <= 0)
            break;
        off += w;
    }
}

static const char *ename(int e)
{
    switch (e) {
    case 0: return "0";
    case EBADF: return "EBADF";
    case EAGAIN: return "EAGAIN";
    case EFAULT: return "EFAULT";
    case EINVAL: return "EINVAL";
    case ESPIPE: return "ESPIPE";
    case EPIPE: return "EPIPE";
    case ENOTSOCK: return "ENOTSOCK";
    case EDESTADDRREQ: return "EDESTADDRREQ";
    case EMSGSIZE: return "EMSGSIZE";
    case EPROTOTYPE: return "EPROTOTYPE";
    case ENOPROTOOPT: return "ENOPROTOOPT";
    case EPROTONOSUPPORT: return "EPROTONOSUPPORT";
    case ESOCKTNOSUPPORT: return "ESOCKTNOSUPPORT";
    case EOPNOTSUPP: return "EOPNOTSUPP";
    case EAFNOSUPPORT: return "EAFNOSUPPORT";
    case EADDRINUSE: return "EADDRINUSE";
    case EADDRNOTAVAIL: return "EADDRNOTAVAIL";
    case ENETDOWN: return "ENETDOWN";
    case ENETUNREACH: return "ENETUNREACH";
    case ENOBUFS: return "ENOBUFS";
    case EISCONN: return "EISCONN";
    case ENOTCONN: return "ENOTCONN";
    case ECONNREFUSED: return "ECONNREFUSED";
    case EHOSTUNREACH: return "EHOSTUNREACH";
    case ENOSYS: return "ENOSYS";
    case EACCES: return "EACCES";
    case EPERM: return "EPERM";
    case ENOMEM: return "ENOMEM";
    case EMFILE: return "EMFILE";
    case ENFILE: return "ENFILE";
    case EINTR: return "EINTR";
    case ECONNRESET: return "ECONNRESET";
    case ECONNABORTED: return "ECONNABORTED";
    case ETIMEDOUT: return "ETIMEDOUT";
    case EINPROGRESS: return "EINPROGRESS";
    case EALREADY: return "EALREADY";
    case ENETRESET: return "ENETRESET";
    case ESHUTDOWN: return "ESHUTDOWN";
    case ENOENT: return "ENOENT";
    case EEXIST: return "EEXIST";
    case ELOOP: return "ELOOP";
    case ENOTDIR: return "ENOTDIR";
    case EISDIR: return "EISDIR";
    case ENOTTY: return "ENOTTY";
    case EROFS: return "EROFS";
    case EOVERFLOW: return "EOVERFLOW";
    case ENXIO: return "ENXIO";
    }
    return "E?";
}

/* "ok" or "<n>" for a call that worked, "-ENAME" for one that did not. */
__attribute__((unused)) static const char *res(long r, char *buf, size_t cap, int show)
{
    if (r < 0)
        snprintf(buf, cap, "-%s", ename(errno));
    else if (show)
        snprintf(buf, cap, "%ld", r);
    else
        snprintf(buf, cap, "ok");
    return buf;
}

__attribute__((unused)) static struct sockaddr_in sin_of(const char *ip, int port)
{
    struct sockaddr_in a;
    memset(&a, 0, sizeof a);
    a.sin_family = AF_INET;
    a.sin_port = htons(port);
    inet_pton(AF_INET, ip, &a.sin_addr);
    return a;
}

/* a.b.c.d:port, with the port as "ephemeral" when it lies in Linux's
   default local range (ip(7): 32768 to 60999), whose pick differs from
   run to run. */
__attribute__((unused)) static const char *aname(const struct sockaddr_in *a, char *buf, size_t cap)
{
    char ip[32];
    int p = ntohs(a->sin_port);
    inet_ntop(AF_INET, &a->sin_addr, ip, sizeof ip);
    if (p >= 32768 && p <= 60999)
        snprintf(buf, cap, "%s:ephemeral", ip);
    else
        snprintf(buf, cap, "%s:%d", ip, p);
    return buf;
}

/* px23: the CRC-32 of ISO 3309 (the reflected polynomial 0xedb88320, as
   zlib's crc32 computes it), a byte at a time: `crc` is the running
   value, 0 to begin. */
__attribute__((unused)) static unsigned long crc32_of(unsigned long crc, const unsigned char *p, size_t n)
{
    static unsigned long table[256];
    if (!table[1])
        for (unsigned long i = 0; i < 256; i++) {
            unsigned long c = i;
            for (int k = 0; k < 8; k++)
                c = c & 1 ? 0xedb88320UL ^ (c >> 1) : c >> 1;
            table[i] = c;
        }
    crc ^= 0xffffffffUL;
    while (n--)
        crc = table[(crc ^ *p++) & 0xff] ^ (crc >> 8);
    return (crc ^ 0xffffffffUL) & 0xffffffffUL;
}

/* px23: the stream every bulk transfer carries, so both ends can make
   it and neither needs a file: 1024-byte records, record r its number
   in 8 bytes (least significant first) and then byte j = r * 31 + j * 7
   (mod 256) for j from 8. Fills `buf` with the `n` bytes from offset
   `off`. */
__attribute__((unused)) static void pattern_fill(unsigned char *buf, unsigned long long off, size_t n)
{
    for (size_t i = 0; i < n; i++, off++) {
        unsigned long long r = off >> 10;
        unsigned j = off & 1023;
        buf[i] = j < 8 ? (unsigned char)(r >> (8 * j)) : (unsigned char)(r * 31 + j * 7);
    }
}

/* px23: send all `n` bytes (a blocking socket takes them all or fails);
   MSG_NOSIGNAL, so a reset is an errno and not a signal. */
__attribute__((unused)) static ssize_t send_all(int fd, const void *p, size_t n)
{
    size_t off = 0;
    while (off < n) {
        ssize_t w = send(fd, (const char *)p + off, n - off, MSG_NOSIGNAL);
        if (w < 0)
            return -1;
        off += w;
    }
    return (ssize_t)off;
}

/* px23: read exactly `n` bytes unless the stream ends first: the bytes
   read, or -1. */
__attribute__((unused)) static ssize_t recv_all(int fd, void *p, size_t n)
{
    size_t off = 0;
    while (off < n) {
        ssize_t r = recv(fd, (char *)p + off, n - off, 0);
        if (r < 0)
            return -1;
        if (r == 0)
            break;
        off += r;
    }
    return (ssize_t)off;
}
