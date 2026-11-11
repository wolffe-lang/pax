/* px120: an original black-box probe for USB hot-plug after boot. No kernel
 * or driver source was consulted. It first takes, touches and gives back
 * argv[1] MiB of anonymous memory (the kernel's frame allocator moves on
 * past it, as a system that has run for a while has), then prints, until
 * a byte 0x04 arrives, every record /dev/mouse0 gives (`HOTREC <64 hex>`,
 * whole, as notes/px109-the-mouse.md documents it: tools/hotplug-session
 * decodes it) and every byte the console gives (`HOTKEY <hex>`, raw).
 * /dev/mouse0 is opened again while it is missing (it appears with the
 * first pointer). Results go to stdout (COM1).
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <termios.h>
#include <unistd.h>

static void record(const unsigned char *r) {
    printf("HOTREC ");
    for (int i = 0; i < 32; i++) printf("%02x", r[i]);
    printf("\n");
}

int main(int argc, char **argv) {
    setvbuf(stdout, 0, _IONBF, 0);
    long mib = argc > 1 ? atol(argv[1]) : 0;
    struct termios raw;
    if (tcgetattr(0, &raw) == 0) {
        cfmakeraw(&raw);
        raw.c_cc[VMIN] = 1;
        raw.c_cc[VTIME] = 0;
        tcsetattr(0, TCSANOW, &raw);
    }
    printf("HOTSTART churn=%ld\n", mib);
    if (mib > 0) {
        size_t n = (size_t)mib << 20;
        unsigned char *p = mmap(0, n, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (p == MAP_FAILED) {
            printf("HOTERR mmap errno=%d\n", errno);
        } else {
            for (size_t i = 0; i < n; i += 4096) p[i] = (unsigned char)i;
            munmap(p, n);
        }
    }
    printf("HOTCHURNED %ld\n", mib);
    int fd = -1;
    for (;;) {
        if (fd < 0) fd = open("/dev/mouse0", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        struct pollfd p[2] = {{0, POLLIN, 0}, {fd, POLLIN, 0}};
        int k = poll(p, fd >= 0 ? 2 : 1, 100);
        if (k < 0) { printf("HOTERR poll errno=%d\n", errno); return 1; }
        if (fd >= 0 && (p[1].revents & POLLIN)) {
            unsigned char buf[32 * 8];
            for (;;) {
                ssize_t got = read(fd, buf, sizeof buf);
                if (got < 0) {
                    if (errno != EAGAIN) printf("HOTERR read errno=%d\n", errno);
                    break;
                }
                if (got == 0 || got % 32) { printf("HOTERR read size=%zd\n", got); break; }
                for (ssize_t i = 0; i < got; i += 32) record(buf + i);
            }
        }
        if (p[0].revents & POLLIN) {
            unsigned char c;
            if (read(0, &c, 1) == 1) {
                printf("HOTKEY %02x\n", c);
                if (c == 4) break;
            }
        }
    }
    printf("HOTDONE\n");
    return 0;
}
