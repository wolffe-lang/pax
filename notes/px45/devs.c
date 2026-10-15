/* devs.c — px45, Linux only (run under tools/linux-sound, as root of the
 * guest): what Linux's sound card and console answer a user, where PAX's
 * `/dev/dsp` and the speaker's ioctls have their equivalents. Black-box:
 * the guest is kasumi's own kernel and its own modules (virtio_snd and
 * the OSS emulation, snd-pcm-oss), run, never read; /dev is devtmpfs with
 * no udev, so every mode and owner is the kernel's own.
 *
 *   devs        rows as root and as a child that became 1000:1000 for good
 *
 * Written from soundcard.h (uapi), the OSS programmer's guide,
 * ioctl_console(2), KIOCSOUND(2const), tty(4), credentials(7); no
 * kernel's, libc's or ALSA's source. */
#include "../px38/probes/px38.h"
#include <dirent.h>
#include <linux/kd.h>
#include <sys/ioctl.h>
#include <sys/soundcard.h>
#include <sys/sysmacros.h>

static void node(const char *p)
{
    struct stat s;
    if (stat(p, &s) == 0) say("node %s: %u:%u %o, %u:%u\n", p, s.st_uid, s.st_gid, s.st_mode, major(s.st_rdev), minor(s.st_rdev));
    else say("node %s: %d\n", p, -errno);
}

static void dsp_ioctls(const char *who, int fd)
{
    int v = 44100, f = AFMT_S16_LE, c = 2;
    audio_buf_info bi;
    long a = rc(SYS_ioctl, fd, SNDCTL_DSP_RESET, 0, 0, 0);
    long b = rc(SYS_ioctl, fd, SNDCTL_DSP_SPEED, (long)&v, 0, 0);
    long d = rc(SYS_ioctl, fd, SNDCTL_DSP_SETFMT, (long)&f, 0, 0);
    long e = rc(SYS_ioctl, fd, SNDCTL_DSP_CHANNELS, (long)&c, 0, 0);
    long g = rc(SYS_ioctl, fd, SNDCTL_DSP_GETOSPACE, (long)&bi, 0, 0);
    static char z[4096];
    long w = rc(SYS_write, fd, (long)z, sizeof z, 0, 0);
    say("%s: on /dev/dsp root opened: RESET %ld, SPEED %ld, SETFMT %ld, CHANNELS %ld, GETOSPACE %ld, write 4096 %ld\n", who, a, b, d, e, g, w);
}

static void kd(const char *who, const char *what, int fd)
{
    long a = rc(SYS_ioctl, fd, KIOCSOUND, 0, 0, 0);
    long b = rc(SYS_ioctl, fd, KDMKTONE, 0, 0, 0);
    say("%s: %s: KIOCSOUND 0 %ld, KDMKTONE 0 %ld\n", who, what, a, b);
}

int main(void)
{
    say("== devs: uid %s\n", uids());
    node("/dev/dsp");
    node("/dev/mixer");
    node("/dev/audio");
    {
        DIR *d = opendir("/dev/snd");
        struct dirent *e;
        char p[300];
        while (d && (e = readdir(d)))
            if (e->d_name[0] != '.') { snprintf(p, sizeof p, "/dev/snd/%s", e->d_name); node(p); }
        if (d) closedir(d);
    }
    node("/dev/tty0"); node("/dev/tty1"); node("/dev/console"); node("/dev/ttyS0"); node("/dev/tty");

    int dsp = open("/dev/dsp", O_WRONLY | O_NONBLOCK);
    say("root: open /dev/dsp %d\n", dsp < 0 ? -errno : 0);
    int tty0 = open("/dev/tty0", O_RDWR | O_NOCTTY | O_NONBLOCK);
    say("root: open /dev/tty0 %d\n", tty0 < 0 ? -errno : 0);
    if (tty0 >= 0) kd("root", "/dev/tty0", tty0);
    {
        int c = open("/dev/console", O_RDWR | O_NOCTTY | O_NONBLOCK);
        if (c >= 0) { kd("root", "/dev/console (the serial console here)", c); close(c); }
        c = open("/dev/ttyS0", O_RDWR | O_NOCTTY | O_NONBLOCK);
        if (c >= 0) { kd("root", "/dev/ttyS0", c); close(c); }
    }
    pid_t p = fork();
    if (p == 0) {
        unsigned none[1] = { 0 };
        become(1000, 1000, 0, none);
        int o = open("/dev/dsp", O_WRONLY | O_NONBLOCK);
        say("user: its own open of /dev/dsp %d, of /dev/mixer %d, of /dev/tty0 %d\n", o < 0 ? -errno : 0,
            open("/dev/mixer", O_RDONLY) < 0 ? -errno : 0, open("/dev/tty0", O_RDWR | O_NOCTTY) < 0 ? -errno : 0);
        if (dsp >= 0) dsp_ioctls("user", dsp);
        if (tty0 >= 0) kd("user", "/dev/tty0 as root opened it", tty0);
        _exit(0);
    }
    reap(p);
    if (dsp >= 0) dsp_ioctls("root", dsp);

    /* the speaker's rule: a terminal that is the caller's own (its controlling terminal) */
    static const char *const VT[] = { "/dev/tty0", "/dev/tty1", "/dev/tty2" };
    for (int v = 0; v < 3; v++) {
        p = fork();
        if (p == 0) {
            long s = rc(SYS_setsid, 0, 0, 0, 0, 0);
            int t = open(VT[v], O_RDWR); /* no O_NOCTTY: a session leader takes it as its controlling terminal */
            int te = t < 0 ? -errno : 0;
            long sc = t >= 0 ? rc(SYS_ioctl, t, TIOCSCTTY, 0, 0, 0) : -1;
            int r = open("/dev/tty", O_RDWR | O_NONBLOCK);
            say("root, a session leader (setsid %s) that opened %s (%d, TIOCSCTTY %ld): /dev/tty %d\n", s > 0 ? "ok" : "failed", VT[v], te, sc,
                r < 0 ? -errno : 0);
            unsigned none[1] = { 0 };
            become(1000, 1000, 0, none);
            int m = open("/dev/tty", O_RDWR | O_NONBLOCK);
            say("user, the same process after it became 1000: /dev/tty %d\n", m < 0 ? -errno : 0);
            if (t >= 0) kd("user", "its controlling terminal's descriptor", t);
            if (m >= 0) kd("user", "its /dev/tty", m);
            _exit(0);
        }
        reap(p);
    }
    if (chown("/dev/tty0", 1000, 1000) == 0) {
        p = fork();
        if (p == 0) {
            unsigned none[1] = { 0 };
            become(1000, 1000, 0, none);
            int t = open("/dev/tty0", O_RDWR | O_NOCTTY | O_NONBLOCK);
            say("user: /dev/tty0 made 1000's by root, its own open %d\n", t < 0 ? -errno : 0);
            if (t >= 0) kd("user", "a /dev/tty0 it owns and opened, not its controlling terminal", t);
            _exit(0);
        }
        reap(p);
        if (chown("/dev/tty0", 0, 0) != 0) say("! chown back\n");
    } else say("! chown /dev/tty0: %d\n", -errno);
    say("devs: done\n");
    return 0;
}
