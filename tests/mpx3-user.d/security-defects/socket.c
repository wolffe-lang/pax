/* W1: source-address copies retain their checked capacity. The read-only
   witness page is anonymous and belongs only to this test process. */
#include "common.h"
struct iovec { void *base; u64 len; };
struct msghdr { void *name; unsigned namelen, pad; struct iovec *iov; u64 iovlen; void *control; u64 controllen; unsigned flags, pad2; };

static void udp(int message, unsigned cap) {
    int rx = (int)sys(41, 2, 2, 0), tx = (int)sys(41, 2, 2, 0);
    require(rx >= 0 && tx >= 0);
    unsigned char sin[16] = {2, 0, 0x9c, 0x40, 127, 0, 0, 1};
    require(sys(49, rx, (i64)sin, 16) == 0);
    unsigned sixteen = 16;
    require(sys6(44, tx, (i64)&sixteen, 4, 0, (i64)sin, 16) == 4);
    unsigned char *page = (unsigned char *)sys6(9, 0, 4096, 3, 0x22, -1, 0);
    require((i64)page > 0);
    for (int i = 0; i < 32; i++) page[i] = 0xaa;
    if (!cap) require(sys(10, (i64)page, 4096, 1) == 0);
    unsigned len = cap;
    i64 r;
    if (message) {
        struct msghdr msg = {0};
        struct iovec iov = {&msg.namelen, 4};
        msg.name = page; msg.namelen = cap; msg.iov = &iov; msg.iovlen = 1;
        r = sys(47, rx, (i64)&msg, 0);
        len = msg.namelen;
    } else {
        r = sys6(45, rx, (i64)&len, 4, 0, (i64)page, (i64)&len);
    }
    int intact = 1;
    for (unsigned i = cap; i < 32; i++) intact &= page[i] == 0xaa;
    if (cap) intact &= page[0] == 2;
    if (cap >= 2) intact &= page[1] == 0;
    out("security: W1 "); out(message ? "recvmsg" : "recvfrom");
    out(" cap "); dec(cap); out(" result "); dec(r); out(" length "); dec(len);
    out(" bounded "); dec(intact); out("\n");
    require(sys(11, (i64)page, 4096, 0) == 0);
    require(sys(3, rx, 0, 0) == 0 && sys(3, tx, 0, 0) == 0);
}
void wit_main(i64 *sp) {
    (void)sp;
    for (int msg = 0; msg < 2; msg++) {
        udp(msg, 0); udp(msg, 1); udp(msg, 8); udp(msg, 16);
    }
    finish(0);
}
