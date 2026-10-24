/* Black-box VT measurement, built on px59's own probe helpers.
 * Only public ioctl interfaces and measurements; no kernel source. */
#define main px59_unused_main
#include "../px59/vtprobe2.c"
#undef main
#include <linux/kd.h>
#include "cases70.h"

int main(void) {
    mkdir("/dev", 0755);
    if (mount("devtmpfs", "/dev", "devtmpfs", 0, 0) < 0) return 2;
    out = open("/dev/console", O_RDWR | O_NOCTTY);
    vt = open("/dev/tty1", O_RDWR | O_NOCTTY);
    if (out < 0 || vt < 0) return 2;
    if (tcgetattr(vt, &raw) < 0) return 3;
    cfmakeraw(&raw);
    if (tcsetattr(vt, TCSANOW, &raw) < 0) return 3;
    for (unsigned i = 0; i < sizeof cases / sizeof cases[0]; i++) {
        tcflush(vt, TCIFLUSH);
        emit(cases[i].data);
        cells("SCREEN", cases[i].name);
        unsigned char palette[48];
        if (ioctl(vt, GIO_CMAP, palette) < 0) return 4;
        dprintf(out, "CMAP %s", cases[i].name);
        for (unsigned j = 0; j < sizeof palette; j++) dprintf(out, " %02x", palette[j]);
        dprintf(out, "\n");
        if (cases[i].pixels) {
            dprintf(out, "READY %s\n", cases[i].name);
            unsigned char ack;
            if (read(vt, &ack, 1) != 1) return 5;
        }
    }
#ifndef PX70_NO_RGB
    /* An independently sampled RGB cube, not the indexed-colour table. */
    static const unsigned v[] = {0, 1, 2, 3, 31, 42, 43, 63, 84, 85, 86, 87, 95, 127, 128, 135, 159, 169, 170, 171, 172, 175, 191, 215, 223, 254, 255};
    int vcsa = open("/dev/vcsa1", O_RDONLY);
    if (vcsa < 0) return 6;
    emit("\033[0m\033[r\033[?25l\033]R\033[2J\033[H");
    for (unsigned r = 0; r < sizeof v / sizeof v[0]; r++)
        for (unsigned g = 0; g < sizeof v / sizeof v[0]; g++)
            for (unsigned b = 0; b < sizeof v / sizeof v[0]; b++) {
                unsigned char fg[6], bg[6];
                dprintf(vt, "\033[H\033[0;38;2;%u;%u;%umX", v[r], v[g], v[b]);
                if (pread(vcsa, fg, 6, 0) != 6) return 7;
                dprintf(vt, "\033[H\033[0;48;2;%u;%u;%umX", v[r], v[g], v[b]);
                if (pread(vcsa, bg, 6, 0) != 6) return 7;
                dprintf(out, "RGB %u %u %u %02x %02x\n", v[r], v[g], v[b], fg[5], bg[5]);
            }
    close(vcsa);
#endif
    dprintf(out, "DONE px70\n");
    sync(); reboot(RB_POWER_OFF); return 0;
}
