/* px130: the kernel's log, asked of the kernel: /dev/kmsg (its node, its
 * records, a reader's place, a write's level and facility, a reader that
 * waits, poll, the seek rules, a reader the ring overtakes) and syslog(2)
 * (READ_ALL, SIZE_BUFFER, SIZE_UNREAD, CLEAR, the console level), with
 * /proc/sys/kernel/printk and dmesg_restrict; and what is refused to a
 * user. Run as the first program on PAX's console (as root, then through
 * `as 1000 1000`) and on a real Linux under QEMU (notes/px111/vminit.c:
 * /proc, devtmpfs at /dev), its transcript held line for line
 * (tests/mpx5-kmsg). Every line is `K<n>: answer`; no time, sequence
 * number or buffer size is printed, only what the rules say of them, so
 * the two kernels' different histories and sizes read the same. Each
 * record this program writes starts `kmsgprobe `, and the suite takes
 * the kernel's console copies of them out of PAX's transcript.
 *
 *   kmsgprobe        as root: every row
 *   kmsgprobe user   as a user: the refusals (K30-K36)
 *
 * Written from the kernel's Documentation/ABI/testing/dev-kmsg (the
 * record's form, one record a read, -EAGAIN, -EPIPE, the seeks and their
 * errors, the `<N>` prefix and LOG_USER), Documentation/admin-guide/
 * sysctl/kernel.rst (printk, dmesg_restrict) and syslog(2) (man-pages
 * 6.19). No C library's or kernel's source was read. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#ifndef SEEK_DATA
#define SEEK_DATA 3
#endif

static void out(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void out(const char *fmt, ...)
{
    char b[1024];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    if (n > (int)sizeof b - 1) n = sizeof b - 1;
    (void)!write(1, b, (size_t)n);
}

/* syslog(2): its answer, or -errno. */
static long klog(int type, char *buf, int len) { long r = syscall(SYS_syslog, type, buf, len); return r < 0 ? -errno : r; }

/* An answer as a word: `ok`, or the errno's name (each its own string: several in one line). */
static const char *err(long r) {
    static char b[8][32];
    static int k;
    if (r >= 0) return "ok";
    int e = (int)-r;
    const char *n = e == EPERM ? "-EPERM" : e == EACCES ? "-EACCES" : e == EINVAL ? "-EINVAL" : e == EAGAIN ? "-EAGAIN"
        : e == EPIPE ? "-EPIPE" : e == ESPIPE ? "-ESPIPE" : e == ENOENT ? "-ENOENT" : e == EFAULT ? "-EFAULT" : e == ENOSYS ? "-ENOSYS" : 0;
    if (n) return n;
    k = (k + 1) % 8;
    snprintf(b[k], sizeof b[k], "-%d", e);
    return b[k];
}

static long sys(long r) { return r < 0 ? -errno : r; }

/* A record: `PRI,SEQ,USEC,FLAGS;TEXT\n`. Parsed into its parts; 0 when it is not that shape. */
struct rec { unsigned long pri, seq, usec; char flag; char text[1100]; };

static int parse(const char *b, long n, struct rec *r)
{
    if (n < 8 || b[n - 1] != '\n') return 0;
    char tmp[4200];
    if (n >= (long)sizeof tmp) return 0;
    memcpy(tmp, b, (size_t)n);
    tmp[n - 1] = 0;
    char *semi = strchr(tmp, ';');
    if (!semi) return 0;
    *semi = 0;
    char flag[8] = "";
    if (sscanf(tmp, "%lu,%lu,%lu,%7[^,]", &r->pri, &r->seq, &r->usec, flag) != 4) return 0;
    r->flag = flag[0];
    snprintf(r->text, sizeof r->text, "%s", semi + 1);
    return 1;
}

/* The next record of `fd`, parsed: the read's answer (its length or -errno). */
static long next_rec(int fd, struct rec *r)
{
    char b[4200];
    long n = sys(read(fd, b, sizeof b));
    if (n > 0 && !parse(b, n, r)) return -1000;
    return n;
}

/* Read `fd` to its end (-EAGAIN); the last record read in `last`. */
static long drain(int fd, struct rec *last, long *count, int *consecutive, int *shaped)
{
    struct rec r;
    long n, k = 0;
    unsigned long prev = 0;
    *consecutive = 1;
    *shaped = 1;
    while ((n = next_rec(fd, &r)) > 0) {
        if (k && r.seq != prev + 1) *consecutive = 0;
        if (r.flag != '-' && r.flag != 'c') *shaped = 0;
        prev = r.seq;
        *last = r;
        k++;
    }
    if (n == -1000) *shaped = 0;
    *count = k;
    return n;
}

/* Write `s` to /dev/kmsg through `fd`: the write's answer. */
static long put(int fd, const char *s) { return sys(write(fd, s, strlen(s))); }

/* The first record after SEEK_END that this program wrote (`kmsgprobe ` first), read from `fd`. */
static int mine(int fd, struct rec *r)
{
    for (int i = 0; i < 64; i++) {
        long n = next_rec(fd, r);
        if (n <= 0) return 0;
        if (!strncmp(r->text, "kmsgprobe ", 10)) return 1;
    }
    return 0;
}

static void root_rows(void)
{
    struct stat st;
    int s = stat("/dev/kmsg", &st);
    if (s) out("K1: stat -%d\n", errno);
    else out("K1: %s %u:%u mode %04o owner %u:%u\n", S_ISCHR(st.st_mode) ? "chr" : "not chr", major(st.st_rdev),
             minor(st.st_rdev), st.st_mode & 07777, st.st_uid, st.st_gid);

    int fd = open("/dev/kmsg", O_RDONLY | O_NONBLOCK);
    out("K2: open O_RDONLY|O_NONBLOCK %s\n", err(fd < 0 ? -errno : 0));
    if (fd < 0) return;
    struct rec r, last;
    long n = next_rec(fd, &r);
    out("K3: the first read %s, %s, flag %c, its number %s\n", n > 0 ? "a record" : err(n), n > 0 ? "PRI,SEQ,USEC,FLAGS;TEXT" : "-",
        n > 0 ? r.flag : '?', n > 0 && r.seq <= 1 ? "the boot's first or second" : n > 0 ? "later" : "-");
    long count; int consecutive, shaped;
    n = drain(fd, &last, &count, &consecutive, &shaped);
    out("K4: read to the end: %s at the end, records %s, numbers %s, every one %s\n", err(n), count > 0 ? "some" : "none",
        consecutive ? "consecutive" : "NOT consecutive", shaped ? "whole" : "NOT whole");

    char small[8];
    lseek(fd, 0, SEEK_SET);
    out("K5: a read into 8 bytes %s\n", err(sys(read(fd, small, sizeof small))));
    out("K6: lseek(0, SEEK_SET) %s; (0, SEEK_END) %s; (0, SEEK_DATA) %s; (0, SEEK_CUR) %s; (1, SEEK_SET) %s; (1, SEEK_CUR) %s\n",
        err(sys(lseek(fd, 0, SEEK_SET))), err(sys(lseek(fd, 0, SEEK_END))), err(sys(lseek(fd, 0, SEEK_DATA))),
        err(sys(lseek(fd, 0, SEEK_CUR))), err(sys(lseek(fd, 1, SEEK_SET))), err(sys(lseek(fd, 1, SEEK_CUR))));
    lseek(fd, 0, SEEK_END);
    out("K7: after SEEK_END a read %s\n", err(next_rec(fd, &r)));
    struct pollfd p = { fd, POLLIN, 0 };
    int pr = poll(&p, 1, 0);
    out("K8: poll at the end: %d, POLLIN %s\n", pr, p.revents & POLLIN ? "set" : "clear");

    int w = open("/dev/kmsg", O_WRONLY);
    out("K9: open O_WRONLY %s\n", err(w < 0 ? -errno : 0));
    if (w < 0) return;
    const char *m1 = "<4>kmsgprobe K10 a warning, its facility the kernel's\n";
    long wr = put(w, m1);
    pr = poll(&p, 1, 0);
    out("K10: write `<4>…` %s (%s), poll POLLIN %s\n", wr == (long)strlen(m1) ? "the whole length" : err(wr), wr >= 0 ? "answered" : "refused",
        p.revents & POLLIN ? "set" : "clear");
    if (mine(fd, &r)) out("K10: read back: priority %lu, flag %c, text `%s`\n", r.pri, r.flag, r.text);
    else out("K10: not read back\n");
    put(w, "kmsgprobe K11 no prefix\n");
    if (mine(fd, &r)) out("K11: no prefix: priority %lu, text `%s`\n", r.pri, r.text); else out("K11: not read back\n");
    put(w, "<14>kmsgprobe K12 user info\n");
    if (mine(fd, &r)) out("K12: `<14>`: priority %lu, text `%s`\n", r.pri, r.text); else out("K12: not read back\n");
    put(w, "<30>kmsgprobe K13 daemon info\n");
    if (mine(fd, &r)) out("K13: `<30>`: priority %lu, text `%s`\n", r.pri, r.text); else out("K13: not read back\n");
    put(w, "kmsgprobe K14 tab\there back\\slash bell\a end\n");
    if (mine(fd, &r)) out("K14: escapes: text `%s`\n", r.text); else out("K14: not read back\n");
    put(w, "<9999>kmsgprobe K15 a large prefix\n");
    if (mine(fd, &r)) out("K15: `<9999>`: priority %lu (level %lu, facility %lu), text `%s`\n", r.pri, r.pri & 7, r.pri >> 3, r.text);
    else out("K15: not read back\n");
    /* `<x>` is no prefix: the record's text keeps it (so it does not start `kmsgprobe `). */
    put(w, "<x>kmsgprobe K16 not a prefix\n");
    if (next_rec(fd, &r) > 0) out("K16: `<x>…`: priority %lu, text `%s`\n", r.pri, r.text); else out("K16: not read back\n");
    out("K17: a write of 0 bytes %s\n", err(sys(write(w, "", 0))));

    /* K18: a reader that waits: a child writes 300 ms later; the blocking read takes it. */
    int b = open("/dev/kmsg", O_RDONLY);
    lseek(b, 0, SEEK_END);
    pid_t c = fork();
    if (c == 0) {
        struct timespec t = { 0, 300000000 };
        nanosleep(&t, 0);
        put(w, "<6>kmsgprobe K18 written while a reader waits\n");
        _exit(0);
    }
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    int got = 0;
    for (int i = 0; i < 8 && !got; i++) {
        long rn = next_rec(b, &r);
        if (rn > 0 && !strncmp(r.text, "kmsgprobe K18", 13)) got = 1;
        if (rn < 0) break;
    }
    clock_gettime(CLOCK_MONOTONIC, &t1);
    long ms = (t1.tv_sec - t0.tv_sec) * 1000 + (t1.tv_nsec - t0.tv_nsec) / 1000000;
    waitpid(c, 0, 0);
    out("K18: a blocking read at the end %s the record written later (%s 200 ms)\n", got ? "returned" : "did NOT return",
        ms >= 200 ? "after" : "within");
    close(b);

    /* syslog(2) */
    long size = klog(10, 0, 0);
    out("K19: SIZE_BUFFER %s, %s\n", size > 0 ? "positive" : err(size), size > 0 && (size & (size - 1)) == 0 ? "a power of two" : "not a power of two");
    static char all[1 << 20];
    long an = klog(3, all, size > 0 && size < (long)sizeof all ? (int)size : (int)sizeof all);
    int lines = 0, form = 1, newest = 0;
    for (long i = 0; i < an;) {
        long j = i;
        while (j < an && all[j] != '\n') j++;
        unsigned pri; char sec[24];
        if (sscanf(all + i, "<%u>[%23[ 0-9.]]", &pri, sec) != 2) form = 0;
        if (j - i > 22 && memmem(all + i, (size_t)(j - i), "kmsgprobe K18", 13)) newest = 1;
        lines++;
        i = j + 1;
    }
    out("K20: READ_ALL %s, lines %s, every one `<PRI>[SECONDS.MICROS] ` %s, the newest of this program's there %s\n",
        an > 0 ? "some bytes" : err(an), lines > 0 ? "some" : "none", form ? "yes" : "NO", newest ? "yes" : "no");
    char tiny[100];
    long tn = klog(3, tiny, sizeof tiny);
    out("K21: READ_ALL into 100 bytes: %s, %s\n", tn > 0 && tn <= 100 ? "at most 100" : err(tn),
        tn > 0 && tiny[tn - 1] == '\n' ? "whole lines" : "a line cut");
    out("K22: READ_ALL with no buffer %s; a negative length %s; SIZE_UNREAD %s\n", err(klog(3, 0, 100)), err(klog(3, all, -1)),
        klog(9, 0, 0) >= 0 ? "a count" : "refused");
    out("K23: CONSOLE_LEVEL 0 %s, 9 %s; type 11 %s; type -1 %s\n", err(klog(8, 0, 0)), err(klog(8, 0, 9)), err(klog(11, 0, 0)), err(klog(-1, 0, 0)));

    char pk[128] = "";
    int pf = open("/proc/sys/kernel/printk", O_RDONLY);
    long pn = pf >= 0 ? read(pf, pk, sizeof pk - 1) : -1;
    if (pf >= 0) close(pf);
    pk[pn > 0 ? pn : 0] = 0;
    int c0 = -1, c1 = -1, c2 = -1, c3 = -1;
    int fields = sscanf(pk, "%d\t%d\t%d\t%d\n", &c0, &c1, &c2, &c3);
    out("K24: /proc/sys/kernel/printk: %d tab-separated numbers, default message level %d, minimum %d\n", fields, c1, c2);
    out("K25: CONSOLE_LEVEL 3 %s, then printk's first %s", err(klog(8, 0, 3)), "");
    pf = open("/proc/sys/kernel/printk", O_RDONLY);
    pn = pf >= 0 ? read(pf, pk, sizeof pk - 1) : -1;
    if (pf >= 0) close(pf);
    pk[pn > 0 ? pn : 0] = 0;
    int d0 = -1;
    sscanf(pk, "%d", &d0);
    out("%d\n", d0);
    out("K26: CONSOLE_OFF %s, printk's first ", err(klog(6, 0, 0)));
    pf = open("/proc/sys/kernel/printk", O_RDONLY);
    pn = pf >= 0 ? read(pf, pk, sizeof pk - 1) : -1;
    if (pf >= 0) close(pf);
    pk[pn > 0 ? pn : 0] = 0;
    sscanf(pk, "%d", &d0);
    out("%d; CONSOLE_ON %s, ", d0, err(klog(7, 0, 0)));
    pf = open("/proc/sys/kernel/printk", O_RDONLY);
    pn = pf >= 0 ? read(pf, pk, sizeof pk - 1) : -1;
    if (pf >= 0) close(pf);
    pk[pn > 0 ? pn : 0] = 0;
    sscanf(pk, "%d", &d0);
    out("printk's first %d\n", d0);
    int restore = c0 >= 1 && c0 <= 8 ? c0 : 1; /* a level 0 (Linux's loglevel=0) put back as the least */
    klog(8, 0, restore);

    char dr[16] = "";
    int df = open("/proc/sys/kernel/dmesg_restrict", O_RDONLY);
    long dn = df >= 0 ? read(df, dr, sizeof dr - 1) : -1;
    if (df >= 0) close(df);
    dr[dn > 0 ? dn : 0] = 0;
    out("K27: /proc/sys/kernel/dmesg_restrict `%.*s`\n", dn > 0 ? (int)dn - 1 : 0, dr);

    /* K28: the ring overtakes a reader: one held at the oldest record, then records written until
     * its record is gone (twice the buffer's size at most). */
    klog(8, 0, 1); /* the flood spares the screen (the serial port and the ring keep it) */
    int h = open("/dev/kmsg", O_RDONLY | O_NONBLOCK);
    struct rec first;
    long fn = next_rec(h, &first);
    lseek(h, 0, SEEK_SET);
    char line[200];
    long wrote = 0, limit = size > 0 ? 2 * size / 150 + 64 : 4096, firstnow = -1;
    int lost = 0;
    while (wrote < limit && !lost) {
        snprintf(line, sizeof line, "<7>kmsgprobe K28 record %06ld of a flood that overtakes a reader, padded to about one hundred and fifty bytes\n", wrote);
        put(w, line);
        wrote++;
        if (wrote % 32 == 0) {
            int t = open("/dev/kmsg", O_RDONLY | O_NONBLOCK);
            struct rec o;
            if (t >= 0 && next_rec(t, &o) > 0 && fn > 0 && o.seq > first.seq) { lost = 1; firstnow = (long)o.seq; }
            close(t);
        }
    }
    long e1 = next_rec(h, &r);
    long e2 = next_rec(h, &r);
    out("K28: a reader held at the oldest record, the ring overtaken: %s; then %s, its number %s the held one's\n",
        err(e1), e2 > 0 ? "a record" : err(e2), e2 > 0 && (long)r.seq >= firstnow && r.seq > first.seq ? "past" : "NOT past");
    long cnt; struct rec lastr;
    n = drain(h, &lastr, &cnt, &consecutive, &shaped);
    char want[200];
    snprintf(want, sizeof want, "kmsgprobe K28 record %06ld of a flood that overtakes a reader, padded to about one hundred and fifty bytes", wrote - 1);
    out("K28: read on to the end: numbers %s, the newest whole and the last written: %s\n", consecutive ? "consecutive" : "NOT consecutive",
        !strcmp(lastr.text, want) ? "yes" : "NO");
    close(h);
    klog(8, 0, restore);
    long before = klog(3, all, sizeof all);
    long cr = klog(5, 0, 0);
    an = klog(3, all, sizeof all);
    out("K29: CLEAR %s; then READ_ALL %s\n", err(cr), an == 0 ? "empty" : an < 0 ? err(an) : an == before ? "NOT empty: every byte it read before" : "NOT empty: some");
    if (an > 0) {
        char *e = memchr(all, '\n', (size_t)an), *t = memchr(all, ']', (size_t)an);
        if (e && t && t < e) out("K29: its first line `%.*s`\n", (int)(e - t - 2), t + 2);
    }
    int sd = open("/dev/kmsg", O_RDONLY | O_NONBLOCK);
    lseek(sd, 0, SEEK_DATA);
    out("K29: after CLEAR, SEEK_DATA then a read %s\n", err(next_rec(sd, &r)));
    close(sd);
    close(w);
    close(fd);
}

static void user_rows(void)
{
    out("K30: open O_RDONLY %s\n", err(open("/dev/kmsg", O_RDONLY | O_NONBLOCK) < 0 ? -errno : 0));
    out("K31: open O_WRONLY %s\n", err(open("/dev/kmsg", O_WRONLY) < 0 ? -errno : 0));
    char b[256];
    out("K32: READ_ALL %s; SIZE_BUFFER %s; CLOSE %s\n", err(klog(3, b, sizeof b)), err(klog(10, 0, 0)), err(klog(0, 0, 0)));
    out("K33: CLEAR %s; CONSOLE_LEVEL 4 %s; CONSOLE_OFF %s; type 99 %s\n", err(klog(5, 0, 0)), err(klog(8, 0, 4)), err(klog(6, 0, 0)), err(klog(99, 0, 0)));
    out("K34: SIZE_UNREAD %s; READ %s\n", err(klog(9, 0, 0)), err(klog(2, b, sizeof b)));
    int f = open("/proc/sys/kernel/dmesg_restrict", O_WRONLY);
    out("K35: dmesg_restrict opened to write %s\n", err(f < 0 ? -errno : 0));
    f = open("/proc/sys/kernel/printk", O_RDONLY);
    out("K36: printk opened to read %s\n", err(f < 0 ? -errno : 0));
}

int main(int argc, char **argv)
{
    if (argc > 1 && !strcmp(argv[1], "user")) user_rows();
    else root_rows();
    out("K99: done\n");
    return 0;
}
