/* Read keyboard input as bytes, without a shell or terminal multiplexer. */
#define _GNU_SOURCE
#include <poll.h>
#include <stdio.h>
#include <termios.h>
#include <unistd.h>

int main(void) {
    struct termios t;
    if (tcgetattr(0, &t)) return 2;
    cfmakeraw(&t);
    t.c_cc[VMIN] = 1;
    t.c_cc[VTIME] = 0;
    if (tcsetattr(0, TCSANOW, &t)) return 2;
    for (int row = 0; row < 34; row++) {
        if (tcflush(0, TCIFLUSH)) return 2;
        dprintf(1, "KEYREADY %d\n", row);
        struct pollfd p = {0, POLLIN, 0};
        unsigned char b;
        unsigned char bytes[32]; int n = 0;
        if (poll(&p, 1, 1500) > 0) {
            do {
                if (read(0, &b, 1) != 1) return 3;
                bytes[n++] = b;
            } while (n < 32 && poll(&p, 1, 100) > 0);
        }
        dprintf(1, "KEYROW %d", row);
        for (int i = 0; i < n; i++) dprintf(1, " %02x", bytes[i]);
        dprintf(1, "\n");
    }
    dprintf(1, "KEYDONE\n");
    return 0;
}
