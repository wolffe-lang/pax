/* px38.h — what the px38 probes share. Static, glibc only for printf and
 * fork; every call under test is a raw `syscall(2)` so the answer is the
 * kernel's, not a wrapper's (glibc's set*id wrappers signal every thread;
 * its faccessat emulates a flag).
 *
 * Written from the man pages named in notes/px38-the-users.md and the
 * uapi headers; no kernel's or libc's source. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

/* A raw call: the result, or -errno. */
static long rc(long nr, long a, long b, long c, long d, long e)
{
    long r = syscall(nr, a, b, c, d, e);
    return r == -1 ? -(long)errno : r;
}

static void say(const char *fmt, ...)
{
    char b[2048];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    if (n > (int)sizeof b - 1) n = sizeof b - 1;
    int o = 0;
    while (o < n) {
        long w = write(1, b + o, n - o);
        if (w <= 0) break;
        o += w;
    }
}

/* One line of /proc/self/status (or of /proc/<pid>/status), without its
 * name; "" when the file or the line is not there. Tabs become spaces. */
static const char *status_line(const char *path, const char *name)
{
    static char buf[8192], out[256];
    out[0] = 0;
    int fd = open(path, O_RDONLY);
    if (fd < 0) return out;
    int n = 0, k;
    while (n < (int)sizeof buf - 1 && (k = read(fd, buf + n, sizeof buf - 1 - n)) > 0) n += k;
    close(fd);
    buf[n] = 0;
    size_t l = strlen(name);
    for (char *p = buf; p && *p; p = strchr(p, '\n'), p = p ? p + 1 : p) {
        if (strncmp(p, name, l) == 0 && p[l] == ':') {
            p += l + 1;
            while (*p == '\t' || *p == ' ') p++;
            int i = 0;
            while (*p && *p != '\n' && i < (int)sizeof out - 1) { out[i++] = *p == '\t' ? ' ' : *p; p++; }
            while (i > 0 && out[i - 1] == ' ') i--;
            out[i] = 0;
            return out;
        }
    }
    return out;
}

/* The effective capability set, by class: every capability the kernel
 * has ("full"), none, or the mask. */
static const char *capeff(void)
{
    static char o[64];
    const char *s = status_line("/proc/self/status", "CapEff");
    const char *b = status_line("/proc/self/status", "CapBnd");
    char bb[64];
    snprintf(bb, sizeof bb, "%s", b);
    s = status_line("/proc/self/status", "CapEff");
    if (!*s) return "?";
    if (strspn(s, "0") == strlen(s)) return "none";
    if (strcmp(s, bb) == 0) return "full";
    snprintf(o, sizeof o, "%s", s);
    return o;
}

/* "r e s fs" of the calling thread, user ids then group ids. */
static const char *uids(void)
{
    static char o[96];
    snprintf(o, sizeof o, "%s", status_line("/proc/self/status", "Uid"));
    return o;
}
static const char *gids(void)
{
    static char o[96];
    snprintf(o, sizeof o, "%s", status_line("/proc/self/status", "Gid"));
    return o;
}
static const char *groups(void)
{
    static char o[256];
    snprintf(o, sizeof o, "%s", status_line("/proc/self/status", "Groups"));
    return o;
}

/* Become (uid, gid) with exactly the supplementary groups given, for
 * good: groups, then the three group ids, then the three user ids. The
 * caller is root. Exits 99 if any step fails. */
static void become(unsigned uid, unsigned gid, int ng, const unsigned *gs)
{
    if (rc(SYS_setgroups, ng, (long)gs, 0, 0, 0) != 0) { say("! setgroups failed %d\n", errno); _exit(99); }
    if (rc(SYS_setresgid, gid, gid, gid, 0, 0) != 0) { say("! setresgid failed %d\n", errno); _exit(99); }
    if (rc(SYS_setresuid, uid, uid, uid, 0, 0) != 0) { say("! setresuid failed %d\n", errno); _exit(99); }
}

/* Wait for one child; its exit status, or 1000 + the signal. */
static int reap(pid_t p)
{
    int st = 0;
    if (waitpid(p, &st, 0) < 0) return -errno;
    if (WIFEXITED(st)) return WEXITSTATUS(st);
    return 1000 + WTERMSIG(st);
}

static unsigned mode_of(const char *p)
{
    struct stat s;
    if (lstat(p, &s) != 0) return 0xffffffff;
    return s.st_mode & 07777;
}

static const char *own_of(const char *p)
{
    static char o[64];
    struct stat s;
    if (lstat(p, &s) != 0) { snprintf(o, sizeof o, "? (%d)", -errno); return o; }
    snprintf(o, sizeof o, "%u:%u", s.st_uid, s.st_gid);
    return o;
}

static int copy_file(const char *from, const char *to, unsigned mode)
{
    char b[65536];
    int i = open(from, O_RDONLY);
    if (i < 0) return -errno;
    int o = open(to, O_WRONLY | O_CREAT | O_TRUNC, 0700);
    if (o < 0) { close(i); return -errno; }
    long n;
    while ((n = read(i, b, sizeof b)) > 0)
        if (write(o, b, n) != n) { close(i); close(o); return -EIO; }
    close(i);
    close(o);
    return chmod(to, mode) ? -errno : 0;
}

static void put_file(const char *p, const char *text, unsigned mode, unsigned uid, unsigned gid)
{
    int fd = open(p, O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd < 0) { say("! cannot make %s: %d\n", p, errno); _exit(98); }
    if (write(fd, text, strlen(text)) < 0) _exit(98);
    close(fd);
    if (chown(p, uid, gid) != 0) { say("! chown %s %u:%u: %d\n", p, uid, gid, errno); _exit(98); }
    if (chmod(p, mode) != 0) { say("! chmod %s: %d\n", p, errno); _exit(98); }
}
