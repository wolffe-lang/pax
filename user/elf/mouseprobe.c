/* px109: an original black-box probe of /dev/mouse0. No kernel or driver
 * source was consulted. The kernel's record is read only as the note
 * documents it (notes/px109-the-mouse.md, "The record"): 32 bytes, little
 * endian. Every record is printed whole, as hex, so tools/mouse-session
 * decodes it independently of this program. Results go to stdout (COM1).
 *
 * For each row: `MOUSEREADY <i> <label>`, then the records that arrive
 * (`MOUSEREC <64 hex digits>`), then `MOUSEROW <label> <count>`. A row
 * waits up to 5 s for its first record, then reads until 400 ms pass with
 * none (800 ms for the keys row, 1.5 s and 3 s for unplug and replug).
 * The burst row reads nothing for 4.5 s first (the queue fills while
 * the host injects), then drains. The keys row reads the console too and
 * prints each byte typed as `MOUSEKEY <ns> <hex>` (CLOCK_MONOTONIC).
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

static const char *labels[] = {
    "mouse-open", "mouse-move", "mouse-left", "mouse-right", "mouse-middle",
    "mouse-wheel", "mouse-drag", "tablet-move", "tablet-left", "tablet-wheel",
    "tablet-drag", "burst-edges", "two-mice", "unplug-held", "replug",
    "keys-during-motion", "finish"
};
enum { BURST = 11, UNPLUG = 13, REPLUG = 14, KEYS = 15, FINISH = 16 };

static long long now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return -1;
    return (long long)t.tv_sec * 1000000000LL + t.tv_nsec;
}

static void record(const unsigned char *r) {
    printf("MOUSEREC ");
    for (int i = 0; i < 32; i++) printf("%02x", r[i]);
    printf("\n");
}

/* Every record waiting now, printed; the count. */
static int drain(int fd) {
    unsigned char buf[32 * 8];
    int n = 0;
    for (;;) {
        ssize_t k = read(fd, buf, sizeof buf);
        if (k < 0) {
            if (errno != EAGAIN) printf("MOUSEERR read errno=%d\n", errno);
            return n;
        }
        if (k == 0 || k % 32) { printf("MOUSEERR read size=%zd\n", k); return n; }
        for (ssize_t i = 0; i < k; i += 32) { record(buf + i); n++; }
    }
}

int main(void) {
    setvbuf(stdout, 0, _IONBF, 0);
    int fd = open("/dev/mouse0", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
    int open_errno = fd < 0 ? errno : 0;
    struct termios raw;
    int have_tty = tcgetattr(0, &raw) == 0;
    if (have_tty) {
        cfmakeraw(&raw);
        raw.c_cc[VMIN] = 1;
        raw.c_cc[VTIME] = 0;
        if (tcsetattr(0, TCSANOW, &raw)) have_tty = 0;
    }
    for (unsigned row = 0; row < sizeof labels / sizeof labels[0]; row++) {
        if (have_tty) tcflush(0, TCIFLUSH);
        printf("MOUSEREADY %u %s\n", row, labels[row]);
        int n = 0;
        if (row == 0) {
            /* The device's shape: what open, fstat, a short read, an
             * empty read and poll answer. */
            struct stat st;
            int mode = -1, shortread = 0, empty = 0, ready = -1;
            if (fd >= 0) {
                if (fstat(fd, &st) == 0) mode = (int)st.st_mode;
                unsigned char b[32];
                shortread = read(fd, b, 31) < 0 ? -errno : 0;
                empty = read(fd, b, 32) < 0 ? -errno : 0;
                struct pollfd p = {fd, POLLIN, 0};
                ready = poll(&p, 1, 0);
            }
            printf("MOUSEAPI open=%d mode=%o short=%d empty=%d poll=%d\n",
                   -open_errno, mode, shortread, empty, ready);
        } else if (row == FINISH) {
            /* nothing to read */
        } else if (fd < 0) {
            /* No device: the host sees no records and names the row. */
            struct timespec pause = {0, 300000000};
            nanosleep(&pause, 0);
        } else {
            if (row == BURST) {
                struct timespec pause = {4, 500000000};
                nanosleep(&pause, 0);
            }
            struct pollfd p[2] = {{fd, POLLIN, 0}, {0, POLLIN, 0}};
            int nfds = (row == KEYS && have_tty) ? 2 : 1;
            int timeout = 5000;
            for (;;) {
                int k = poll(p, nfds, timeout);
                if (k < 0) { printf("MOUSEERR poll errno=%d\n", errno); break; }
                if (k == 0) break;
                if (p[0].revents & POLLIN) n += drain(fd);
                if (nfds == 2 && (p[1].revents & POLLIN)) {
                    unsigned char c;
                    if (read(0, &c, 1) == 1) { printf("MOUSEKEY %lld %02x\n", now(), c); }
                }
                /* An unplug and a replug wait on the enumeration thread's
                 * scan and an attach: a longer quiet. */
                timeout = row == KEYS ? 800 : row == UNPLUG ? 1500 : row == REPLUG ? 3000 : 400;
            }
        }
        printf("MOUSEROW %s %d\n", labels[row], n);
    }
    printf("MOUSEDONE\n");
    return 0;
}
