/* dsptone — write a known PCM signal to an OSS device (px30).
 *
 *   dsptone [-d DEVICE] [-r RATE] [-c CHANNELS] [-f s16|u8] [-t MS]
 *           [-l HZ] [-R HZ] [-p tone|ramp] [-k BYTES] [-g MS] [-q] [-n]
 *
 * A static Linux program, the same file run on Linux and on PAX: it
 * opens DEVICE (/dev/dsp) for writing, asks the format, the channels
 * and the rate with the three requests every OSS program makes
 * (SNDCTL_DSP_SETFMT, SNDCTL_DSP_CHANNELS, SNDCTL_DSP_SPEED), says what
 * the device answered, writes MS milliseconds of signal in writes of
 * BYTES bytes, and closes (which plays out what is queued). Every line
 * it prints is the same on any system that answers alike; times are
 * printed only as whole tenths of a second.
 *
 *   -p tone  a sine of -l HZ on the left channel and -R HZ on the right
 *            (one channel: -l), at 3/8 of full scale, starting at phase 0
 *   -p ramp  16-bit only: frame i carries 7*i (mod 65536) on the left
 *            and its complement on the right, so a capture shows a lost,
 *            repeated or swapped frame exactly
 *   -g MS    stop writing for MS milliseconds half way (an underrun)
 *   -q       ask the queries first: OSS_GETVERSION, GETFMTS, GETCAPS,
 *            GETBLKSIZE, GETOSPACE, GETODELAY
 *   -n       no SNDCTL_DSP_* request at all: the device's defaults
 *            (8000 Hz, one channel, unsigned 8-bit)
 *   -X exit  half way, end the process with _exit(3) and the device
 *            still open: nothing drains it (what the kernel does with
 *            the queued sound is the test)
 *   -X fault half way, write through a null pointer (SIGSEGV)
 *   -S SECS  soak: after the -t signal, write it again and again until
 *            SECS seconds of sound have gone (each second's bytes the
 *            same), printing every 60 s what GETOPTR and GETOSPACE say
 *   -N       open with O_NONBLOCK: a full queue answers EAGAIN, which
 *            this program waits out with a 5 ms sleep and counts
 *
 * Exit 0, 1 when a call failed (named), 2 on usage.
 *
 * Written from the uapi `linux/soundcard.h` (through glibc's
 * <sys/soundcard.h>) and the OSS programmer's guide; no kernel's or
 * library's source.
 */
#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/soundcard.h>
#include <time.h>
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
    case EINTR: return "EINTR";
    case ENOSYS: return "ENOSYS";
    default: return "E?";
    }
}

static long now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
}

static int ask(int fd, const char *name, unsigned long req, int *v)
{
    int in = *v;
    if (ioctl(fd, req, v) < 0) {
        say("dsptone: %s %d: %s\n", name, in, ename(errno));
        return -1;
    }
    say("dsptone: %s %d -> %d\n", name, in, *v);
    return 0;
}

int main(int argc, char **argv)
{
    const char *dev = "/dev/dsp", *pat = "tone", *fmtname = "s16";
    int rate = 48000, ch = 2, ms = 1000, lhz = 440, rhz = 660;
    int chunk = 4096, gap = 0, queries = 0, defaults = 0, nonblock = 0, soak = 0;
    const char *end = NULL;
    int o;
    while ((o = getopt(argc, argv, "d:r:c:f:t:l:R:p:k:g:qnX:NS:")) != -1) {
        switch (o) {
        case 'd': dev = optarg; break;
        case 'r': rate = atoi(optarg); break;
        case 'c': ch = atoi(optarg); break;
        case 'f': fmtname = optarg; break;
        case 't': ms = atoi(optarg); break;
        case 'l': lhz = atoi(optarg); break;
        case 'R': rhz = atoi(optarg); break;
        case 'p': pat = optarg; break;
        case 'k': chunk = atoi(optarg); break;
        case 'g': gap = atoi(optarg); break;
        case 'q': queries = 1; break;
        case 'n': defaults = 1; break;
        case 'X': end = optarg; break;
        case 'N': nonblock = 1; break;
        case 'S': soak = atoi(optarg); break;
        default:
            say("usage: dsptone [-d DEV] [-r RATE] [-c CH] [-f s16|u8] [-t MS] [-l HZ] [-R HZ] [-p tone|ramp] [-k BYTES] [-g MS] [-q] [-n]\n");
            return 2;
        }
    }
    int fmt = strcmp(fmtname, "u8") == 0 ? AFMT_U8 : AFMT_S16_LE;
    int ramp = strcmp(pat, "ramp") == 0;
    if (defaults) {
        rate = 8000;
        ch = 1;
        fmt = AFMT_U8;
    }
    if (ch < 1 || ch > 2 || rate < 1 || ms < 0 || chunk < 1 || (ramp && fmt != AFMT_S16_LE)) {
        say("dsptone: bad arguments\n");
        return 2;
    }

    int fd = open(dev, O_WRONLY | (nonblock ? O_NONBLOCK : 0));
    if (fd < 0) {
        say("dsptone: open %s: %s\n", dev, ename(errno));
        return 1;
    }
    say("dsptone: open %s\n", dev);

    if (queries) {
        int v = 0;
        if (ioctl(fd, OSS_GETVERSION, &v) < 0)
            say("dsptone: OSS_GETVERSION: %s\n", ename(errno));
        else
            say("dsptone: OSS_GETVERSION 0x%06x\n", v);
        if (ioctl(fd, SNDCTL_DSP_GETFMTS, &v) < 0)
            say("dsptone: GETFMTS: %s\n", ename(errno));
        else
            say("dsptone: GETFMTS has u8 %d s16le %d\n", (v & AFMT_U8) != 0, (v & AFMT_S16_LE) != 0);
        if (ioctl(fd, SNDCTL_DSP_GETCAPS, &v) < 0)
            say("dsptone: GETCAPS: %s\n", ename(errno));
        else
            say("dsptone: GETCAPS answered\n");
    }
    if (!defaults) {
        int v = fmt;
        if (ask(fd, "SETFMT", SNDCTL_DSP_SETFMT, &v) < 0)
            return 1;
        fmt = v;
        v = ch;
        if (ask(fd, "CHANNELS", SNDCTL_DSP_CHANNELS, &v) < 0)
            return 1;
        ch = v;
        v = rate;
        if (ask(fd, "SPEED", SNDCTL_DSP_SPEED, &v) < 0)
            return 1;
        rate = v;
    }
    if (fmt != AFMT_U8 && fmt != AFMT_S16_LE) {
        say("dsptone: the device chose a format this program does not write: %d\n", fmt);
        return 1;
    }
    if (ch < 1 || ch > 2 || rate < 1) {
        say("dsptone: the device chose %d channels at %d Hz\n", ch, rate);
        return 1;
    }
    int width = fmt == AFMT_U8 ? 1 : 2;
    int frame = width * ch;
    if (queries) {
        int v = 0;
        audio_buf_info bi;
        if (ioctl(fd, SNDCTL_DSP_GETBLKSIZE, &v) < 0)
            say("dsptone: GETBLKSIZE: %s\n", ename(errno));
        else
            say("dsptone: GETBLKSIZE power of two %d, at least 16 %d\n", v > 0 && (v & (v - 1)) == 0, v >= 16);
        if (ioctl(fd, SNDCTL_DSP_GETOSPACE, &bi) < 0)
            say("dsptone: GETOSPACE: %s\n", ename(errno));
        else
            say("dsptone: GETOSPACE fragments free %d of %d, bytes %s\n", bi.fragments == bi.fragstotal,
                bi.fragstotal > 0, bi.bytes == bi.fragments * bi.fragsize ? "fragments*fragsize" : "other");
        if (ioctl(fd, SNDCTL_DSP_GETODELAY, &v) < 0)
            say("dsptone: GETODELAY: %s\n", ename(errno));
        else
            say("dsptone: GETODELAY before a write %d\n", v);
    }

    long frames = (long)rate * ms / 1000;
    long total = frames * frame;
    unsigned char *buf = malloc(total > 0 ? total : 1);
    if (!buf) {
        say("dsptone: no memory\n");
        return 1;
    }
    const double two_pi = 6.283185307179586476925286766559;
    for (long i = 0; i < frames; i++) {
        for (int c = 0; c < ch; c++) {
            int s;
            if (ramp) {
                unsigned u = (unsigned)(7 * i) & 0xffff;
                if (c == 1)
                    u = ~u & 0xffff;
                s = (int)(short)u;
            } else {
                int hz = c == 0 ? lhz : rhz;
                s = (int)lrint(12288.0 * sin(two_pi * hz * (double)i / rate));
            }
            unsigned char *p = buf + i * frame + c * width;
            if (width == 1) {
                p[0] = (unsigned char)((s >> 8) + 128);
            } else {
                p[0] = (unsigned char)(s & 0xff);
                p[1] = (unsigned char)((s >> 8) & 0xff);
            }
        }
    }

    long t0 = now_ms();
    long off = 0, writes = 0, eagain = 0, half = total / 2 / frame * frame;
    int gapped = gap == 0;
    while (off < total) {
        long n = total - off;
        if (n > chunk)
            n = chunk;
        if (!gapped && off + n > half)
            n = half - off;
        if (n > 0) {
            ssize_t w = write(fd, buf + off, n);
            if (w < 0) {
                if (errno == EINTR)
                    continue;
                if (errno == EAGAIN && nonblock) {
                    struct timespec ts = { 0, 5000000L };
                    nanosleep(&ts, NULL);
                    eagain++;
                    continue;
                }
                say("dsptone: write at %ld: %s\n", off, ename(errno));
                return 1;
            }
            if (w == 0) {
                say("dsptone: write at %ld answered 0\n", off);
                return 1;
            }
            off += w;
            writes++;
        }
        if (end && off >= half) {
            say("dsptone: ending (%s) at byte %ld with the device open\n", end, off);
            if (strcmp(end, "fault") == 0)
                *(volatile int *)0 = 1;
            _exit(3);
        }
        if (!gapped && off >= half) {
            struct timespec ts = { gap / 1000, (gap % 1000) * 1000000L };
            nanosleep(&ts, NULL);
            gapped = 1;
            say("dsptone: paused %d ms at byte %ld\n", gap, off);
        }
    }
    if (soak > 0 && total > 0) {
        long rounds = (long)soak * 1000 / (ms > 0 ? ms : 1), next = 60;
        for (long k = 1; k < rounds; k++) {
            long o2 = 0;
            while (o2 < total) {
                long n2 = total - o2 > chunk ? chunk : total - o2;
                ssize_t w = write(fd, buf + o2, n2);
                if (w < 0) {
                    if (errno == EINTR)
                        continue;
                    say("dsptone: soak write: %s\n", ename(errno));
                    return 1;
                }
                o2 += w;
            }
            off += total;
            if ((k + 1) * (long)ms / 1000 >= next) {
                count_info ci;
                audio_buf_info bi;
                memset(&ci, 0, sizeof ci);
                memset(&bi, 0, sizeof bi);
                ioctl(fd, SNDCTL_DSP_GETOPTR, &ci);
                ioctl(fd, SNDCTL_DSP_GETOSPACE, &bi);
                say("dsptone: soak %ld s written, GETOPTR bytes %d, GETOSPACE fragments %d of %d\n",
                    (k + 1) * (long)ms / 1000, ci.bytes, bi.fragments, bi.fragstotal);
                next += 60;
            }
        }
    }
    long t1 = now_ms();
    say("dsptone: wrote %ld bytes, %ld frames of %d bytes at %d Hz\n", off, frames, frame, rate);
    if (nonblock)
        say("dsptone: EAGAIN answered %s\n", eagain > 0 ? "while the queue was full" : "never");
    if (queries) {
        int v = 0;
        if (ioctl(fd, SNDCTL_DSP_GETODELAY, &v) < 0)
            say("dsptone: GETODELAY: %s\n", ename(errno));
        else
            say("dsptone: GETODELAY after the writes: whole frames %d, within the data %d\n", v % frame == 0,
                v >= 0 && v <= total);
    }
    if (close(fd) < 0) {
        say("dsptone: close: %s\n", ename(errno));
        return 1;
    }
    long t2 = now_ms();
    /* The device takes the signal at its own rate: the writes and the
       close together last about as long as the signal (less what a
       buffer holds while the last write returns). */
    fprintf(stderr, "dsptone: timing: writes %ld ms, close %ld ms, signal %d ms, %ld writes\n", t1 - t0, t2 - t1,
            ms + gap, writes);
    say("dsptone: closed; played out %s\n", (t2 - t0) * 10 >= (long)(ms + gap) * 8 ? "in step with the device" : "EARLY");
    return 0;
}
