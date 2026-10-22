/* px59's second black-box measurement of a Linux VT: console_codes(4),
 * vcs(4), console_ioctl(4), termios(3). No kernel source. A static pid 1
 * in kasumi's own Linux image under QEMU (notes/px59/vt-run2.py sends the
 * keys through QEMU's monitor and runs it twice).
 *
 *   SCREEN name cursor=r,c cells= r,c[-c2]:CH/AT ...   /dev/vcsa1 after
 *          the case's bytes on a cleared screen; a run of equal cells on
 *          one row is r,c-c2; blanks in the default colours are left out
 *   QUERY  name hex...|none     what the VT put in the input (raw mode)
 *   ECHO   name cells...        the screen after a query in canonical
 *                               mode with ECHO and ECHOCTL
 *   KEY    name hex...|none [switched to N]   a key sent by the monitor
 */
#include <fcntl.h>
#include <linux/vt.h>
#include <poll.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <termios.h>
#include <unistd.h>

static int vt, out;
static struct termios cooked, raw;

static void emit(const char *s) { if (write(vt, s, strlen(s)) < 0) _exit(3); }

static void cells(const char *tag, const char *name) {
    int v = open("/dev/vcsa1", O_RDONLY);
    static unsigned char b[65536];
    int n = read(v, b, sizeof b);
    close(v);
    if (n < 4) { dprintf(out, "FAIL vcsa1 %d\n", n); return; }
    int cols = b[1];
    dprintf(out, "%s %s cursor=%u,%u cells=", tag, name, b[3] + 1, b[2] + 1);
    int i = 4;
    while (i + 1 < n) {
        int k = (i - 4) / 2, r = k / cols + 1, c = k % cols + 1;
        if (b[i] == 32 && b[i + 1] == 7) { i += 2; continue; }
        int j = i + 2, c2 = c;
        while (j + 1 < n && (j - 4) / 2 / cols + 1 == r && b[j] == b[i] && b[j + 1] == b[i + 1]) { j += 2; c2++; }
        if (c2 > c) dprintf(out, " %d,%d-%d:%02x/%02x", r, c, c2, b[i], b[i + 1]);
        else dprintf(out, " %d,%d:%02x/%02x", r, c, b[i], b[i + 1]);
        i = j;
    }
    dprintf(out, "\n");
}

static void screen(const char *name, const char *s) {
    emit("\033[0m\033[2J\033[H");
    emit(s);
    cells("SCREEN", name);
}

static void answer(const char *name, const char *s) {
    unsigned char b[256];
    int n = 0;
    tcflush(vt, TCIFLUSH);
    emit(s);
    struct pollfd p = {vt, POLLIN, 0};
    while (n < (int)sizeof b && poll(&p, 1, 300) > 0) {
        int k = read(vt, b + n, sizeof b - n);
        if (k <= 0) break;
        n += k;
    }
    dprintf(out, "QUERY %s", name);
    for (int i = 0; i < n; i++) dprintf(out, " %02x", b[i]);
    dprintf(out, "%s\n", n ? "" : " none");
}

static int active(void) {
    struct vt_stat st;
    if (ioctl(vt, VT_GETSTATE, &st) < 0) return -1;
    return st.v_active;
}

static const char *keys[] = {
    "up", "down", "right", "left",
    "shift-up", "shift-down", "shift-right", "shift-left",
    "ctrl-up", "ctrl-down", "ctrl-right", "ctrl-left",
    "alt-up", "alt-down",
    "shift-ctrl-up", "shift-ctrl-down", "shift-ctrl-right", "shift-ctrl-left",
    "shift-alt-up", "shift-alt-down", "shift-alt-right", "shift-alt-left",
    "ctrl-alt-up", "ctrl-alt-down",
    "shift-ctrl-alt-up", "shift-ctrl-alt-down", "shift-ctrl-alt-right", "shift-ctrl-alt-left",
    "home", "end", "pgup", "pgdn", "insert", "delete",
    "shift-home", "shift-end", "shift-insert", "shift-delete",
    "ctrl-home", "ctrl-end", "ctrl-pgup", "ctrl-pgdn", "ctrl-insert", "ctrl-delete",
    "alt-home", "alt-end", "alt-pgup", "alt-pgdn", "alt-insert", "alt-delete",
    "shift-ctrl-home", "shift-ctrl-end",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "shift-f1", "shift-f2", "shift-f3", "shift-f4", "shift-f5", "shift-f6",
    "shift-f7", "shift-f8", "shift-f9", "shift-f10", "shift-f11", "shift-f12",
    "ctrl-f1", "ctrl-f2", "ctrl-f5", "ctrl-f12",
    "shift-ctrl-f1", "shift-ctrl-f12",
    "alt-a", "alt-z", "alt-shift-a", "ctrl-alt-a", "alt-1", "alt-minus", "alt-equal",
    "alt-ret", "alt-backspace", "alt-tab", "alt-esc", "alt-spc",
    "alt-bracket_left", "alt-slash", "alt-dot", "alt-apostrophe", "alt-grave_accent",
    "shift-alt-1", "alt-kp_1", "alt-kp_enter",
    "alt_r-a", "alt_r-up", "alt_r-f1",
    "kp_1", "kp_enter", "kp_add", "kp_multiply", "kp_divide", "kp_subtract",
    "shift-pgup", "shift-pgdn",
    "alt-f1", "ctrl-alt-f1",
    "alt-left", "alt-right", "ctrl-alt-left", "ctrl-alt-right",
    "alt-f2",
    "dot",
};

int main(void) {
    mkdir("/dev", 0755);
    mount("devtmpfs", "/dev", "devtmpfs", 0, 0);
    out = open("/dev/console", O_RDWR | O_NOCTTY);
    vt = open("/dev/tty1", O_RDWR | O_NOCTTY);
    if (out < 0 || vt < 0) return 2;
    tcgetattr(vt, &cooked);
    raw = cooked;
    cfmakeraw(&raw);
    tcsetattr(vt, TCSANOW, &raw);
    dprintf(out, "STATE iflag 0x%x oflag 0x%x cflag 0x%x lflag 0x%x active %d\n",
            cooked.c_iflag, cooked.c_oflag, cooked.c_cflag, cooked.c_lflag, active());

    screen("SGR2", "\033[2mA\033[22mB");
    screen("SGR3", "\033[3mA\033[23mB");
    screen("SGR4", "\033[4mA\033[24mB");
    screen("SGR5", "\033[5mA\033[25mB");
    screen("SGR8", "\033[8mA\033[28mB");
    screen("SGR9", "\033[9mA\033[29mB");
    screen("SGR21", "\033[1m\033[21mA");
    screen("SGR2-colour", "\033[31;2mA\033[1mB\033[22mC");
    screen("SGR4-colour", "\033[32;4mA\033[7mB");
    screen("SGR-truecolour", "\033[38;2;255;0;0mR\033[48;2;0;0;255mB\033[0;38;2;10;200;30mG\033[38;2;128;128;128mM");
    screen("SGR-list", "\033[1;31;44mX\033[0;7;32mY");
    screen("SGR-colon", "\033[38:5:196mR\033[0mN");
    screen("SGR-empty", "\033[31mA\033[mB\033[;32mC");
    screen("CUP-private", "\033[?5;5HX");
    screen("CUP-nine", "\033[3;4;0;0;0;0;0;0;0HX");
    screen("CUP-seventeen", "\033[3;4;0;0;0;0;0;0;0;0;0;0;0;0;0;0;0HX");
    screen("CUP-big", "\033[99999;5HX");
    screen("CUP-intermediate", "\033[3;5 HX");
    screen("wrap", "\033[1;80HAB");
    screen("wrap-CUP", "\033[1;80HA\033[1;1HB");
    screen("wrap-BS", "\033[1;79HAB\010C");
    screen("wrap-CR", "\033[1;80HA\rB");
    screen("CNL-CPL", "\033[3;5H\033[2EX\033[1FY");
    screen("ICH", "abcde\033[1;2H\033[2@");
    screen("DCH", "abcde\033[1;2H\033[2P");
    screen("ECH", "abcde\033[1;2H\033[2X");
    screen("IL", "a\r\nb\r\nc\033[2;1H\033[L");
    screen("DL", "a\r\nb\r\nc\033[2;1H\033[M");
    screen("DECSTBM", "\033[2;3rT\033[3;1Hx\ny\nz\033[r");
    screen("scroll-background", "\033[25;1H\033[44mA\r\nB");
    screen("ED-background", "\033[44m\033[2J\033[0mX");
    screen("1049-background", "\033[44mMAIN\033[?1049hA");
    emit("\033[0m\033[?1049l");
    screen("1049-scroll-both",
           "L1\r\nL2\r\nL3\r\nL4\r\nL5\r\nL6\r\nL7\r\nL8\r\nL9\r\nL10\r\nL11\r\nL12\r\nL13\r\nL14\r\nL15\r\n"
           "L16\r\nL17\r\nL18\r\nL19\r\nL20\r\nL21\r\nL22\r\nL23\r\nL24\r\nL25\r\nL26\r\nL27\r\nL28"
           "\033[?1049h\033[HY1\r\nY2\r\nY3\r\nY4\r\nY5\r\nY6\r\nY7\r\nY8\r\nY9\r\nY10\r\nY11\r\nY12\r\nY13"
           "\r\nY14\r\nY15\r\nY16\r\nY17\r\nY18\r\nY19\r\nY20\r\nY21\r\nY22\r\nY23\r\nY24\r\nY25\r\nY26\r\nY27"
           "\033[?1049l\r\nE");
    screen("1049-cursor", "\033[5;5HMAIN\033[?1049h\033[20;20HX\033[?1049lZ");
    screen("1049-decsc", "\033[3;3H\0337\033[?1049h\033[9;9H\0337\033[?1049l\0338X");
    screen("1049-inside", "MAIN\033[?1049h\033[31mALT\033[?1049lX");
    screen("1047", "MAIN\033[?1047hA\033[?1047lB");
    screen("47", "MAIN\033[?47hA\033[?47lB");
    screen("DECTCEM-25", "\033[?25lA\033[?25hB");
    screen("DECSCUSR-all", "\033[1 qA\033[3 qB\033[4 qC\033[5 qD\033[6 qE\033[0 qF");
    screen("linux-cursor", "\033[?2cA\033[?0cB");
    screen("OSC-ESC", "A\033]52;c;eA==\033XB\033\\C");
    screen("OSC-C0", "A\033]0;title\nB\007C");
    screen("OSC-P", "A\033]P1ff0000B");
    screen("OSC-11", "A\033]11;?\007B");
    screen("private-modes", "A\033[?2004h\033[?1002h\033[?1006h\033[?1004h\033[?2026h\033[?2026l\033[?2004l\033[?1002l\033[?1006l\033[?1004lB");
    screen("kitty", "A\033[>21u\033[<uB\033[=1;1uC");
    screen("DECRQM", "A\033[?2026$pB");

    answer("DA1", "\033[c");
    answer("DA1-0", "\033[0c");
    answer("DECID", "\033Z");
    answer("DSR5", "\033[5n");
    answer("CPR-home", "\033[H\033[6n");
    answer("CPR-3-5", "\033[3;5H\033[6n");
    answer("CPR-wrap", "\033[1;80HX\033[6n");
    answer("CPR-last", "\033[25;80H\033[6n");
    answer("CPR-alt", "\033[?1049h\033[7;9H\033[6n");
    emit("\033[?1049l");
    answer("DA2", "\033[>c");
    answer("DECXCPR", "\033[?6n");
    answer("OSC11", "\033]11;?\007");
    answer("kitty", "\033[?u");
    answer("DECRQM2026", "\033[?2026$p");
    answer("yew-probe", "\033[?u\033[?2026$p\033[c");
    answer("two", "\033[c\033[6n");

    tcsetattr(vt, TCSANOW, &cooked);
    emit("\033[0m\033[2J\033[H");
    tcflush(vt, TCIFLUSH);
    emit("\033[c");
    usleep(400000);
    cells("ECHO", "DA1-canonical");
    tcflush(vt, TCIFLUSH);
    emit("\033[0m\033[2J\033[H\033[3;5H\033[6n");
    usleep(400000);
    cells("ECHO", "CPR-canonical");
    tcflush(vt, TCIFLUSH);
    tcsetattr(vt, TCSANOW, &raw);
    emit("\033[0m\033[2J\033[H");

    for (unsigned i = 0; i < sizeof keys / sizeof keys[0]; i++) {
        tcflush(vt, TCIFLUSH);
        dprintf(out, "KEYREADY %u %s\n", i, keys[i]);
        unsigned char b[256];
        int n = 0;
        struct pollfd p = {vt, POLLIN, 0};
        if (poll(&p, 1, 3000) > 0) {
            for (;;) {
                int k = read(vt, b + n, sizeof b - n);
                if (k <= 0) break;
                n += k;
                if (poll(&p, 1, 200) <= 0) break;
            }
        }
        dprintf(out, "KEY %s", keys[i]);
        for (int j = 0; j < n; j++) dprintf(out, " %02x", b[j]);
        dprintf(out, "%s", n ? "" : " none");
        int a = active();
        if (a != 1) {
            dprintf(out, " switched to %d", a);
            ioctl(vt, VT_ACTIVATE, 1);
            ioctl(vt, VT_WAITACTIVE, 1);
        }
        dprintf(out, "\n");
    }
    dprintf(out, "DONE px59 vt2\n");
    sync();
    reboot(RB_POWER_OFF);
    return 0;
}
