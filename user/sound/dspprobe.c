/* dspprobe — what an OSS device answers at its edges (px30).
 *
 *   dspprobe [DEVICE]
 *
 * A static Linux program, run on Linux (under QEMU, with a sound card)
 * and on PAX: each line is one request and its answer, the value the
 * device chose or the errno by name. Lines that name a size print
 * whether it has the property the OSS guide asks of it rather than its
 * value, so two systems with different buffers can still agree.
 *
 * Exit 0 when it ran to its end, 1 when /dev/dsp cannot be opened.
 *
 * Written from the uapi `linux/soundcard.h` (through glibc's
 * <sys/soundcard.h>), open(2), ioctl(2), poll(2) and the OSS
 * programmer's guide; no kernel's or library's source.
 */
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/soundcard.h>
#include <unistd.h>

static void say(const char *fmt, ...)
{
    char b[512];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    if (n > (int)sizeof b - 1)
        n = sizeof b - 1;
    if (write(1, b, n) < 0)
        _exit(3);
}

static const char *ename(int e)
{
    switch (e) {
    case 0: return "0";
    case ENOENT: return "ENOENT";
    case EBUSY: return "EBUSY";
    case EINVAL: return "EINVAL";
    case ENOTTY: return "ENOTTY";
    case ENODEV: return "ENODEV";
    case ENXIO: return "ENXIO";
    case EAGAIN: return "EAGAIN";
    case EIO: return "EIO";
    case EFAULT: return "EFAULT";
    case EBADF: return "EBADF";
    case EACCES: return "EACCES";
    case EPERM: return "EPERM";
    case ENOSYS: return "ENOSYS";
    case EOPNOTSUPP: return "EOPNOTSUPP";
    case ESPIPE: return "ESPIPE";
    default: return "E?";
    }
}

static void req(int fd, const char *name, unsigned long r, int v)
{
    int in = v;
    if (ioctl(fd, r, &v) < 0)
        say("%s %d: %s\n", name, in, ename(errno));
    else
        say("%s %d -> %d\n", name, in, v);
}

int main(int argc, char **argv)
{
    const char *dev = argc > 1 ? argv[1] : "/dev/dsp";
    int fd = open(dev, O_WRONLY);
    if (fd < 0) {
        say("open %s O_WRONLY: %s\n", dev, ename(errno));
        return 1;
    }
    say("open %s O_WRONLY: ok\n", dev);

    /* a second open while the first is held */
    int fd2 = open(dev, O_WRONLY | O_NONBLOCK);
    say("second open O_WRONLY|O_NONBLOCK: %s\n", fd2 < 0 ? ename(errno) : "ok");
    if (fd2 >= 0)
        close(fd2);
    int fd3 = open(dev, O_RDONLY | O_NONBLOCK);
    say("open O_RDONLY|O_NONBLOCK beside it: %s\n", fd3 < 0 ? ename(errno) : "ok");
    if (fd3 >= 0)
        close(fd3);

    /* formats: what the device takes and what it substitutes */
    req(fd, "SETFMT AFMT_QUERY", SNDCTL_DSP_SETFMT, AFMT_QUERY);
    req(fd, "SETFMT AFMT_U8", SNDCTL_DSP_SETFMT, AFMT_U8);
    req(fd, "SETFMT AFMT_S16_LE", SNDCTL_DSP_SETFMT, AFMT_S16_LE);
    req(fd, "SETFMT AFMT_S16_BE", SNDCTL_DSP_SETFMT, AFMT_S16_BE);
    req(fd, "SETFMT AFMT_MU_LAW", SNDCTL_DSP_SETFMT, AFMT_MU_LAW);
    req(fd, "SETFMT AFMT_S8", SNDCTL_DSP_SETFMT, AFMT_S8);
    req(fd, "SETFMT AFMT_S16_LE", SNDCTL_DSP_SETFMT, AFMT_S16_LE);
    /* channels */
    req(fd, "CHANNELS", SNDCTL_DSP_CHANNELS, 1);
    req(fd, "CHANNELS", SNDCTL_DSP_CHANNELS, 6);
    req(fd, "CHANNELS", SNDCTL_DSP_CHANNELS, 0);
    req(fd, "STEREO", SNDCTL_DSP_STEREO, 1);
    req(fd, "CHANNELS", SNDCTL_DSP_CHANNELS, 2);
    /* rates */
    req(fd, "SPEED", SNDCTL_DSP_SPEED, 8000);
    req(fd, "SPEED", SNDCTL_DSP_SPEED, 44100);
    req(fd, "SPEED", SNDCTL_DSP_SPEED, 48000);
    req(fd, "SPEED", SNDCTL_DSP_SPEED, 11000);
    req(fd, "SPEED", SNDCTL_DSP_SPEED, 1000);
    req(fd, "SPEED", SNDCTL_DSP_SPEED, 400000);
    req(fd, "SPEED", SNDCTL_DSP_SPEED, 48000);

    /* fragments, before the first write */
    int frag = (16 << 16) | 12; /* 16 fragments of 4096 bytes */
    if (ioctl(fd, SNDCTL_DSP_SETFRAGMENT, &frag) < 0)
        say("SETFRAGMENT 16x4096: %s\n", ename(errno));
    else
        say("SETFRAGMENT 16x4096: ok\n");
    int bs = 0;
    if (ioctl(fd, SNDCTL_DSP_GETBLKSIZE, &bs) < 0)
        say("GETBLKSIZE: %s\n", ename(errno));
    else
        say("GETBLKSIZE: positive %d\n", bs > 0);
    audio_buf_info bi;
    memset(&bi, 0, sizeof bi);
    if (ioctl(fd, SNDCTL_DSP_GETOSPACE, &bi) < 0) {
        say("GETOSPACE: %s\n", ename(errno));
    } else {
        say("GETOSPACE: all free %d, fragsize positive %d, bytes = fragments*fragsize %d\n",
            bi.fragments == bi.fragstotal, bi.fragsize > 0, bi.bytes == bi.fragments * bi.fragsize);
    }
    int caps = 0;
    if (ioctl(fd, SNDCTL_DSP_GETCAPS, &caps) < 0)
        say("GETCAPS: %s\n", ename(errno));
    else
        say("GETCAPS: TRIGGER %d MMAP %d DUPLEX %d\n", (caps & DSP_CAP_TRIGGER) != 0, (caps & DSP_CAP_MMAP) != 0,
            (caps & DSP_CAP_DUPLEX) != 0);

    /* readiness before any data: room to write */
    struct pollfd p = { fd, POLLOUT, 0 };
    int pr = poll(&p, 1, 0);
    say("poll POLLOUT before a write: %d revents POLLOUT %d\n", pr, (p.revents & POLLOUT) != 0);

    /* a short write, then the calls that end it */
    short sil[2048];
    memset(sil, 0, sizeof sil);
    ssize_t w = write(fd, sil, sizeof sil);
    say("write 4096 bytes of silence: %s\n", w == (ssize_t)sizeof sil ? "4096" : ename(errno));
    w = write(fd, sil, 3);
    say("write 3 bytes (not a whole frame): %s\n", w < 0 ? ename(errno) : (w == 3 ? "3" : "short"));
    int od = -1;
    if (ioctl(fd, SNDCTL_DSP_GETODELAY, &od) < 0)
        say("GETODELAY: %s\n", ename(errno));
    else
        say("GETODELAY: non-negative %d\n", od >= 0);
    if (ioctl(fd, SNDCTL_DSP_SYNC, 0) < 0)
        say("SYNC: %s\n", ename(errno));
    else
        say("SYNC: ok\n");
    if (ioctl(fd, SNDCTL_DSP_GETODELAY, &od) < 0)
        say("GETODELAY after SYNC: %s\n", ename(errno));
    else
        say("GETODELAY after SYNC: %d\n", od);
    if (ioctl(fd, SNDCTL_DSP_RESET, 0) < 0)
        say("RESET: %s\n", ename(errno));
    else
        say("RESET: ok\n");
    req(fd, "SETFMT AFMT_QUERY after RESET", SNDCTL_DSP_SETFMT, AFMT_QUERY);
    int x = 0;
    if (ioctl(fd, SNDCTL_DSP_GETISPACE, &bi) < 0)
        say("GETISPACE on a playback open: %s\n", ename(errno));
    else
        say("GETISPACE on a playback open: ok\n");
    if (ioctl(fd, 0x5401 /* TCGETS */, &x) < 0)
        say("TCGETS: %s\n", ename(errno));
    else
        say("TCGETS: ok\n");
    char rb[4];
    ssize_t r = read(fd, rb, sizeof rb);
    say("read on a playback open: %s\n", r < 0 ? ename(errno) : "data");
    off_t o = lseek(fd, 0, SEEK_SET);
    say("lseek: %s\n", o < 0 ? ename(errno) : "ok");
    say("close: %s\n", close(fd) < 0 ? ename(errno) : "ok");
    say("end\n");
    return 0;
}
