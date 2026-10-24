/* mounts.c — px67's probe of the mount table and the mount calls: one
   static glibc program run unmodified on Linux (the Linux guest booted
   with `root=` on an ext2 partition, this program its init:
   tools/linux-root) and on PAX (the root on the disk that boots), the
   two outputs compared line by line (tests/mpx6-root).

     mounts init        (the guest's pid 1 only) mount /proc, /sys, /dev
                        and /tmp as a distribution's init does (the
                        flags kasumi's systemd gives them, measured in
                        its mountinfo: proc and sysfs
                        nosuid,nodev,noexec,relatime; devtmpfs nosuid,
                        mode=755; a tmpfs nosuid,nodev, as its /run and
                        /dev/shm, mode=1777), then `table`, `calls`, `user` and
                        `end` below, then reboot(2)
     mounts table       /proc/self/mountinfo, /proc/self/mounts, the
                        links /proc/mounts and /etc/mtab (lstat, target,
                        bytes read through them), statfs(2) and
                        statvfs(3) of `/`
     mounts calls DEV DIR
                        mount(2) and umount2(2) as root: `/` remounted
                        read-only (refused while a file is open for
                        writing), a change refused EROFS, remounted
                        read-write; DEV (an ext2 volume) mounted at DIR,
                        the table, a file written there, umount2 refused
                        while a working directory or an open file is in
                        it, then unmounted; the errors (ENOTDIR, ENOENT,
                        ENODEV, ENOTBLK, EBUSY, EINVAL)
     mounts user UID DEV DIR
                        the same calls after setresgid/setresuid(UID):
                        EPERM, the path's errors first
     mounts root        `..` at the root: `/` and `/..` one directory
                        (its device and inode), getcwd after chdir("/..")
                        and through `..` from below, a path through
                        `/..`, a listing of `/..` and of `/`, openat of
                        `../..` from a directory, chroot("/")
     mounts twice MARKER
                        `/etc` across a reboot: without MARKER, it edits
                        /etc/motd, writes /root/px67-note and
                        /tmp/px67-tmp, makes MARKER, syncs and asks
                        reboot(2) to restart; with it (the second boot)
                        it prints /etc/motd and /root/px67-note and
                        stats /tmp/px67-tmp (a tmpfs /tmp: gone)
     mounts churn N     the crash row's write session (tools/root-crash):
                        N operations in /churn chosen by a fixed
                        generator (xorshift64, seed 0x9e3779b97f4a7c15):
                        make a file of 1 to 16 KiB, append 4 KiB, rename,
                        unlink, make a directory with a file in it, cut a
                        file to half; `churn: K S.N` after operation K
                        is done (px68: S.N the realtime clock read when
                        it returned, which the journal's commit blocks
                        are held to), 10 ms apart, no fsync (the
                        flusher's 5 s are what reaches the disk);
                        tools/root-crash replays the same operations to
                        know what the disk should hold
     mounts end         `/` remounted read-only and sync(2), as an init
                        does before reboot(2)
     mounts term WAIT PROG [ARG...]
                        R-px67-4's measurement: PROG started as a child
                        (the console its descriptors), WAIT seconds later
                        sent SIGTERM, its end waited for up to 10 s
                        (waitpid WNOHANG every millisecond, the
                        monotonic clock), then SIGKILL; one `~term:` line
                        with the milliseconds and how it ended
     mounts linger [halt|restart]
                        two children left running when it returns, for
                        the end's rows, each in a session of its own
                        (setsid: a daemon, which no terminal's hang-up
                        reaches): one waits in pause(2) (SIGTERM's
                        default ends it), one ignores SIGTERM (only
                        SIGKILL ends it); each says it has started;
                        with `halt` or `restart` it then asks reboot(2)
                        for that itself (sync(2) first, as reboot(8) does)

   Every call is printed with its answer (`= 0` or `= -1 ENAME`). Lines
   that begin `~` hold what is the kernel's own to choose (mount ids,
   free counts, a device's anonymous numbers): printed, not compared.
   Built by tools/mkrootprobe: cc -static -no-pie -O1. Written from the
   man pages mount(2), umount2(2), proc(5) (/proc/pid/mounts and
   mountinfo), statfs(2), statvfs(3), reboot(2) and the uapi headers'
   numbers; nothing here reads a kernel's, a libc's or a mount tool's
   source. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <signal.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static void say(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void say(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    fflush(stdout);
}

static const char *ename(int e) {
    switch (e) {
    case EPERM: return "EPERM";
    case ENOENT: return "ENOENT";
    case EIO: return "EIO";
    case ENXIO: return "ENXIO";
    case EBADF: return "EBADF";
    case ENOMEM: return "ENOMEM";
    case EACCES: return "EACCES";
    case EFAULT: return "EFAULT";
    case ENOTBLK: return "ENOTBLK";
    case EBUSY: return "EBUSY";
    case EEXIST: return "EEXIST";
    case EXDEV: return "EXDEV";
    case ENODEV: return "ENODEV";
    case ENOTDIR: return "ENOTDIR";
    case EISDIR: return "EISDIR";
    case EINVAL: return "EINVAL";
    case ENOSPC: return "ENOSPC";
    case EROFS: return "EROFS";
    case ENAMETOOLONG: return "ENAMETOOLONG";
    case ENOSYS: return "ENOSYS";
    case ELOOP: return "ELOOP";
    case EOPNOTSUPP: return "EOPNOTSUPP";
    default: return "E?";
    }
}

/* `= 0` or `= -1 ENAME`, as one call's answer. */
static const char *ans(long r) {
    static char b[64];
    if (r >= 0)
        snprintf(b, sizeof b, "= %ld", r);
    else
        snprintf(b, sizeof b, "= -1 %s", ename(errno));
    return b;
}

static long mnt(const char *src, const char *tgt, const char *type, unsigned long fl, const char *data) {
    errno = 0;
    long r = mount(src, tgt, type, fl, data);
    say("mount(%s, %s, %s, 0x%lx, %s) %s\n", src ? src : "NULL", tgt, type ? type : "NULL", fl, data ? data : "NULL", ans(r));
    return r;
}

static long umnt(const char *tgt, int fl) {
    errno = 0;
    long r = umount2(tgt, fl);
    say("umount2(%s, 0x%x) %s\n", tgt, fl, ans(r));
    return r;
}

/* A file's bytes, each line prefixed. Mount ids in mountinfo and the
   anonymous devices' numbers are the kernel's to choose: the whole of
   mountinfo is printed `~` and compared field by field by the suite. */
static void cat(const char *path, const char *prefix) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        say("%sopen %s = -1 %s\n", prefix, path, ename(errno));
        return;
    }
    char buf[8192];
    size_t n = 0;
    ssize_t k;
    while (n < sizeof buf - 1 && (k = read(fd, buf + n, sizeof buf - 1 - n)) > 0)
        n += (size_t)k;
    close(fd);
    buf[n] = 0;
    char *p = buf;
    while (*p) {
        char *e = strchr(p, '\n');
        if (e)
            *e = 0;
        say("%s%s\n", prefix, p);
        if (!e)
            break;
        p = e + 1;
    }
}

static void link_of(const char *path) {
    struct stat s;
    if (lstat(path, &s) < 0) {
        say("lstat %s = -1 %s\n", path, ename(errno));
        return;
    }
    char t[256];
    ssize_t n = readlink(path, t, sizeof t - 1);
    if (n < 0) {
        say("%s: mode %o, readlink = -1 %s\n", path, s.st_mode, ename(errno));
        return;
    }
    t[n] = 0;
    say("%s: mode %o, -> %s\n", path, s.st_mode, t);
}

static void fs_of(const char *path) {
    struct statfs f;
    struct statvfs v;
    struct stat s;
    if (stat(path, &s) == 0)
        say("~stat %s: dev %u:%u ino %lu\n", path, major(s.st_dev), minor(s.st_dev), (unsigned long)s.st_ino);
    if (statfs(path, &f) < 0) {
        say("statfs %s = -1 %s\n", path, ename(errno));
        return;
    }
    say("statfs %s: type 0x%lx bsize %ld frsize %ld namelen %ld flags 0x%lx\n", path,
        (unsigned long)f.f_type, (long)f.f_bsize, (long)f.f_frsize, (long)f.f_namelen, (unsigned long)f.f_flags);
    say("~statfs %s: blocks %lu files %lu bfree %lu bavail %lu ffree %lu fsid %08x%08x\n", path, (unsigned long)f.f_blocks,
        (unsigned long)f.f_files, (unsigned long)f.f_bfree, (unsigned long)f.f_bavail, (unsigned long)f.f_ffree,
        (unsigned)f.f_fsid.__val[0], (unsigned)f.f_fsid.__val[1]);
    if (statvfs(path, &v) < 0) {
        say("statvfs %s = -1 %s\n", path, ename(errno));
        return;
    }
    say("statvfs %s: bsize %lu frsize %lu namemax %lu flag 0x%lx\n", path, v.f_bsize, v.f_frsize, v.f_namemax, v.f_flag);
}

static void table(void) {
    say("table: begin\n");
    cat("/proc/self/mountinfo", "~mountinfo: ");
    cat("/proc/self/mounts", "mounts: ");
    link_of("/proc/mounts");
    link_of("/etc/mtab");
    cat("/etc/mtab", "mtab: ");
    fs_of("/");
    say("table: end\n");
}

static long make(const char *path) {
    errno = 0;
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    say("open(%s, O_WRONLY|O_CREAT) %s\n", path, ans(fd));
    if (fd >= 0) {
        ssize_t w = write(fd, "px67\n", 5);
        say("write %s = %ld\n", path, (long)w);
        close(fd);
    }
    return fd;
}

static void calls(const char *dev, const char *dir) {
    say("calls: begin\n");
    /* `/` read-only and back. */
    errno = 0;
    int w = open("/px67-held", O_WRONLY | O_CREAT | O_TRUNC, 0644);
    say("open(/px67-held, O_WRONLY|O_CREAT) %s\n", ans(w));
    mnt("none", "/", NULL, MS_REMOUNT | MS_RDONLY, NULL);
    if (w >= 0)
        close(w);
    errno = 0;
    say("unlink(/px67-held) %s\n", ans(unlink("/px67-held")));
    mnt("none", "/", NULL, MS_REMOUNT | MS_RDONLY, NULL);
    make("/px67-ro");
    errno = 0;
    say("mkdir(/px67-ro.d) %s\n", ans(mkdir("/px67-ro.d", 0755)));
    struct statvfs v;
    if (statvfs("/", &v) == 0)
        say("statvfs /: flag 0x%lx (ST_RDONLY %d)\n", v.f_flag, (int)!!(v.f_flag & ST_RDONLY));
    cat("/proc/self/mounts", "mounts: ");
    mnt("none", "/etc", NULL, MS_REMOUNT | MS_RDONLY, NULL);
    mnt("none", "/", NULL, MS_REMOUNT, NULL);
    make("/px67-rw");
    errno = 0;
    say("unlink(/px67-rw) %s\n", ans(unlink("/px67-rw")));
    /* A volume at a directory. */
    mnt(dev, dir, "ext2", 0, NULL);
    cat("/proc/self/mounts", "mounts: ");
    char f[256];
    snprintf(f, sizeof f, "%s/px67-note", dir);
    make(f);
    struct stat s;
    if (stat(dir, &s) == 0)
        say("~stat %s: dev %u:%u ino %lu\n", dir, major(s.st_dev), minor(s.st_dev), (unsigned long)s.st_ino);
    fs_of(dir);
    mnt(dev, dir, "ext2", 0, NULL);
    errno = 0;
    say("chdir(%s) %s\n", dir, ans(chdir(dir)));
    umnt(dir, 0);
    errno = 0;
    say("chdir(/) %s\n", ans(chdir("/")));
    errno = 0;
    int h = open(f, O_RDONLY);
    say("open(%s, O_RDONLY) %s\n", f, ans(h));
    umnt(dir, 0);
    if (h >= 0)
        close(h);
    umnt(dir, 0);
    umnt(dir, 0);
    cat("/proc/self/mounts", "mounts: ");
    /* The errors. */
    mnt(dev, "/etc/motd", "ext2", 0, NULL);
    mnt(dev, "/px67-nosuch", "ext2", 0, NULL);
    mnt("/dev/px67-nosuch", dir, "ext2", 0, NULL);
    mnt(dev, dir, "px67fs", 0, NULL);
    mnt("/etc/motd", dir, "ext2", 0, NULL);
    umnt("/", 0);
    cat("/proc/self/mounts", "mounts: ");
    mnt("none", "/", NULL, MS_REMOUNT, NULL);
    umnt("/etc", 0);
    umnt("/px67-nosuch", 0);
    umnt(dir, 0x80000000);
    say("calls: end\n");
}

static void user(int uid, const char *dev, const char *dir) {
    say("user %d: begin\n", uid);
    pid_t p = fork();
    if (p == 0) {
        if (setresgid(uid, uid, uid) < 0 || setresuid(uid, uid, uid) < 0) {
            say("setresuid(%d) = -1 %s\n", uid, ename(errno));
            _exit(1);
        }
        mnt(dev, dir, "ext2", 0, NULL);
        mnt("none", "/", NULL, MS_REMOUNT | MS_RDONLY, NULL);
        umnt(dir, 0);
        umnt("/", 0);
        umnt("/px67-nosuch", 0);
        fs_of("/");
        _exit(0);
    }
    int st = 0;
    waitpid(p, &st, 0);
    say("user %d: end, status %d\n", uid, WIFEXITED(st) ? WEXITSTATUS(st) : -1);
}

static void linger(const char *then) {
    for (int k = 0; k < 2; k++) {
        pid_t p = fork();
        if (p == 0) {
            setsid();
            if (k == 1)
                signal(SIGTERM, SIG_IGN);
            say("linger %d: pid %d, SIGTERM %s\n", k, (int)getpid(), k == 1 ? "ignored" : "default");
            for (;;)
                pause();
        }
    }
    sleep(1); /* both have said so before the parent returns */
    if (then) {
        sync();
        errno = 0;
        long r = reboot(strcmp(then, "restart") == 0 ? RB_AUTOBOOT : RB_HALT_SYSTEM);
        say("reboot(%s) %s\n", then, ans(r));
    }
}

static const char *how(int st) {
    static char b[64];
    if (WIFEXITED(st))
        snprintf(b, sizeof b, "exit %d", WEXITSTATUS(st));
    else if (WIFSIGNALED(st))
        snprintf(b, sizeof b, "signal %d", WTERMSIG(st));
    else
        snprintf(b, sizeof b, "status 0x%x", st);
    return b;
}

static void term(int wait, char **argv) {
    pid_t p = fork();
    if (p == 0) {
        execv(argv[0], argv);
        say("term: exec %s = -1 %s\n", argv[0], ename(errno));
        _exit(127);
    }
    sleep(wait);
    struct timespec a, b;
    clock_gettime(CLOCK_MONOTONIC, &a);
    kill(p, SIGTERM);
    int st = 0;
    long ms = -1;
    for (int i = 0; i < 10000; i++) {
        if (waitpid(p, &st, WNOHANG) == p) {
            clock_gettime(CLOCK_MONOTONIC, &b);
            ms = (b.tv_sec - a.tv_sec) * 1000 + (b.tv_nsec - a.tv_nsec) / 1000000;
            break;
        }
        usleep(1000);
    }
    if (ms < 0) {
        kill(p, SIGKILL);
        waitpid(p, &st, 0);
        say("~term: %s still there 10000 ms after SIGTERM; SIGKILL: %s\n", argv[0], how(st));
    } else {
        say("~term: %s ended %ld ms after SIGTERM: %s\n", argv[0], ms, how(st));
    }
}

/* The sorted names of directory `d` (getdents through readdir), as one
   line's text: their count and an FNV-1a 64 of them, so two listings
   compare without printing a root's every name. */
static int namecmp(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }
static void listing(const char *d, unsigned *count, uint64_t *sum) {
    DIR *x = opendir(d);
    *count = 0;
    *sum = 1469598103934665603ULL;
    if (!x)
        return;
    char *names[4096];
    unsigned n = 0;
    struct dirent *e;
    while ((e = readdir(x)) && n < 4096)
        names[n++] = strdup(e->d_name);
    closedir(x);
    qsort(names, n, sizeof names[0], namecmp);
    for (unsigned i = 0; i < n; i++) {
        for (const char *p = names[i]; *p; p++) {
            *sum ^= (unsigned char)*p;
            *sum *= 1099511628211ULL;
        }
        *sum ^= 10;
        *sum *= 1099511628211ULL;
        free(names[i]);
    }
    *count = n;
}

static void cwd_line(const char *what) {
    char b[512];
    errno = 0;
    if (getcwd(b, sizeof b))
        say("dotdot: getcwd after %s: %s\n", what, b);
    else
        say("dotdot: getcwd after %s = -1 %s\n", what, ename(errno));
}

static void root(void) {
    say("dotdot: begin\n");
    struct stat a, b;
    int sa = stat("/", &a), sb = stat("/..", &b);
    say("~dotdot: / dev %u:%u ino %lu, /.. dev %u:%u ino %lu\n", major(a.st_dev), minor(a.st_dev), (unsigned long)a.st_ino,
        major(b.st_dev), minor(b.st_dev), (unsigned long)b.st_ino);
    say("dotdot: / and /.. one directory: %s\n", sa == 0 && sb == 0 && a.st_dev == b.st_dev && a.st_ino == b.st_ino ? "yes" : "no");
    errno = 0;
    say("dotdot: chdir(/..) %s\n", ans(chdir("/..")));
    cwd_line("chdir(/..)");
    errno = 0;
    say("dotdot: chdir(/etc) %s\n", ans(chdir("/etc")));
    errno = 0;
    say("dotdot: chdir(../../..) %s\n", ans(chdir("../../..")));
    cwd_line("chdir(../../..) from /etc");
    struct stat c;
    say("dotdot: . is /: %s\n", stat(".", &c) == 0 && c.st_dev == a.st_dev && c.st_ino == a.st_ino ? "yes" : "no");
    errno = 0;
    int fd = open("/../etc/../etc/motd", O_RDONLY);
    say("dotdot: open(/../etc/../etc/motd) %s\n", ans(fd));
    if (fd >= 0)
        close(fd);
    unsigned n1, n2;
    uint64_t s1, s2;
    listing("/", &n1, &s1);
    listing("/..", &n2, &s2);
    say("~dotdot: / lists %u names (%016llx), /.. %u (%016llx)\n", n1, (unsigned long long)s1, n2, (unsigned long long)s2);
    say("dotdot: /.. lists what / lists: %s\n", n1 > 0 && n1 == n2 && s1 == s2 ? "yes" : "no");
    int e = open("/etc", O_RDONLY | O_DIRECTORY);
    errno = 0;
    int up = openat(e, "../..", O_RDONLY | O_DIRECTORY);
    say("dotdot: openat(/etc, ../..) %s\n", up >= 0 ? "= a descriptor" : ans(up));
    struct stat u;
    say("dotdot: it is /: %s\n", up >= 0 && fstat(up, &u) == 0 && u.st_dev == a.st_dev && u.st_ino == a.st_ino ? "yes" : "no");
    if (up >= 0)
        close(up);
    if (e >= 0)
        close(e);
    errno = 0;
    say("dotdot: chroot(/) %s\n", ans(chroot("/")));
    cwd_line("chroot(/)");
    say("dotdot: end\n");
}

static void put(const char *path, const char *text) {
    errno = 0;
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) {
        say("twice: open(%s) = -1 %s\n", path, ename(errno));
        return;
    }
    ssize_t w = write(fd, text, strlen(text));
    close(fd);
    say("twice: wrote %s (%ld bytes)\n", path, (long)w);
}

static void show(const char *path) {
    char b[256];
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        say("twice: %s = -1 %s\n", path, ename(errno));
        return;
    }
    ssize_t n = read(fd, b, sizeof b - 1);
    close(fd);
    b[n > 0 ? n : 0] = 0;
    if (n > 0 && b[n - 1] == '\n')
        b[n - 1] = 0;
    say("twice: %s: %s\n", path, b);
}

static void twice(const char *marker) {
    if (access(marker, F_OK) != 0) {
        say("twice: the first boot\n");
        put("/etc/motd", "px67: /etc/motd, edited before the reboot\n");
        mkdir("/root", 0700);
        put("/root/px67-note", "px67: a note in /root\n");
        put("/tmp/px67-tmp", "px67: in /tmp, the memory's\n");
        put(marker, "1\n");
        sync();
        errno = 0;
        long r = reboot(RB_AUTOBOOT);
        say("twice: reboot = %s\n", ans(r));
        return;
    }
    say("twice: the second boot\n");
    show("/etc/motd");
    show("/root/px67-note");
    struct stat s;
    errno = 0;
    say("twice: stat(/tmp/px67-tmp) %s\n", ans(stat("/tmp/px67-tmp", &s)));
    say("twice: end\n");
}

static uint64_t churn_x = 0x9e3779b97f4a7c15ULL;
static uint64_t churn_next(void) {
    churn_x ^= churn_x << 13;
    churn_x ^= churn_x >> 7;
    churn_x ^= churn_x << 17;
    return churn_x;
}

static void churn_fill(int fd, unsigned long n, unsigned long tag) {
    char b[4096];
    for (unsigned long i = 0; i < sizeof b; i++)
        b[i] = (char)('a' + (i + tag) % 26);
    while (n > 0) {
        unsigned long k = n < sizeof b ? n : sizeof b;
        if (write(fd, b, k) != (ssize_t)k)
            return;
        n -= k;
    }
}

/* The names alive, as the generator picks among them: f<k>, r<k>, d<k>/f. */
static char churn_names[4096][24];
static int churn_count = 0;

static void churn(int n) {
    mkdir("/churn", 0755);
    say("churn: begin\n");
    for (int k = 0; k < n; k++) {
        uint64_t r = churn_next();
        int op = (int)(r % 6);
        int pick = churn_count > 0 ? (int)((r >> 8) % (uint64_t)churn_count) : -1;
        char path[64];
        if (op == 0 || pick < 0) {
            snprintf(path, sizeof path, "/churn/f%d", k);
            int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
            if (fd >= 0) {
                churn_fill(fd, 1024 * (1 + (r >> 20) % 16), (unsigned long)k);
                close(fd);
                if (churn_count < 4096)
                    snprintf(churn_names[churn_count++], 24, "f%d", k);
            }
        } else if (op == 1) {
            snprintf(path, sizeof path, "/churn/%s", churn_names[pick]);
            int fd = open(path, O_WRONLY | O_APPEND);
            if (fd >= 0) {
                churn_fill(fd, 4096, (unsigned long)k);
                close(fd);
            }
        } else if (op == 2 && strchr(churn_names[pick], '/') == NULL) {
            char to[64];
            snprintf(path, sizeof path, "/churn/%s", churn_names[pick]);
            snprintf(to, sizeof to, "/churn/r%d", k);
            if (rename(path, to) == 0)
                snprintf(churn_names[pick], 24, "r%d", k);
        } else if (op == 3) {
            snprintf(path, sizeof path, "/churn/%s", churn_names[pick]);
            if (unlink(path) == 0) {
                memcpy(churn_names[pick], churn_names[churn_count - 1], 24);
                churn_count--;
            }
        } else if (op == 4) {
            snprintf(path, sizeof path, "/churn/d%d", k);
            if (mkdir(path, 0755) == 0) {
                char f[80];
                snprintf(f, sizeof f, "%s/f", path);
                int fd = open(f, O_WRONLY | O_CREAT | O_TRUNC, 0644);
                if (fd >= 0) {
                    churn_fill(fd, 2048, (unsigned long)k);
                    close(fd);
                    if (churn_count < 4096)
                        snprintf(churn_names[churn_count++], 24, "d%d/f", k);
                }
            }
        } else if (op == 5) {
            snprintf(path, sizeof path, "/churn/%s", churn_names[pick]);
            struct stat st;
            if (stat(path, &st) == 0)
                truncate(path, st.st_size / 2);
        }
        struct timespec ts;
        clock_gettime(CLOCK_REALTIME, &ts);
        say("churn: %d %lld.%09ld\n", k, (long long)ts.tv_sec, ts.tv_nsec);
        usleep(10000);
    }
    say("churn: end\n");
}

static void end(void) {
    mnt("none", "/", NULL, MS_REMOUNT | MS_RDONLY, NULL);
    sync();
    say("end: synced\n");
}

int main(int argc, char **argv) {
    if (argc >= 2 && strcmp(argv[1], "table") == 0) {
        table();
        return 0;
    }
    if (argc >= 4 && strcmp(argv[1], "calls") == 0) {
        calls(argv[2], argv[3]);
        return 0;
    }
    if (argc >= 5 && strcmp(argv[1], "user") == 0) {
        user(atoi(argv[2]), argv[3], argv[4]);
        return 0;
    }
    if (argc >= 2 && strcmp(argv[1], "root") == 0) {
        root();
        return 0;
    }
    if (argc >= 3 && strcmp(argv[1], "twice") == 0) {
        twice(argv[2]);
        return 0;
    }
    if (argc >= 3 && strcmp(argv[1], "churn") == 0) {
        churn(atoi(argv[2]));
        return 0;
    }
    if (argc >= 2 && strcmp(argv[1], "linger") == 0) {
        linger(argc >= 3 ? argv[2] : NULL);
        return 0;
    }
    if (argc >= 4 && strcmp(argv[1], "term") == 0) {
        term(atoi(argv[2]), argv + 3);
        return 0;
    }
    if (argc >= 2 && strcmp(argv[1], "end") == 0) {
        end();
        return 0;
    }
    if (argc >= 2 && strcmp(argv[1], "init") == 0) {
        /* The guest: a distribution's init's mounts, then the rows. */
        say("mounts: init pid %d\n", (int)getpid());
        const char *dev = argc >= 3 ? argv[2] : "/dev/vda3";
        const char *dir = argc >= 4 ? argv[3] : "/mnt";
        mnt("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC | MS_RELATIME, NULL);
        mnt("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC | MS_RELATIME, NULL);
        mnt("devtmpfs", "/dev", "devtmpfs", MS_NOSUID, "mode=755");
        if (argc < 5 || strcmp(argv[4], "disk-tmp") != 0)
            mnt("tmpfs", "/tmp", "tmpfs", MS_NOSUID | MS_NODEV, "mode=1777");
        table();
        root();
        calls(dev, dir);
        user(1000, dev, dir);
        if (argc < 6 || strcmp(argv[5], "no-end") != 0)
            end();
        say("mounts: init done\n");
        reboot(RB_POWER_OFF);
        say("reboot = -1 %s\n", ename(errno));
        for (;;)
            pause();
    }
    say("usage: mounts table | calls DEV DIR | user UID DEV DIR | root | twice MARKER | churn N | term WAIT PROG [ARG...] | end | linger [halt|restart] | init [DEV DIR [disk-tmp [no-end]]]\n");
    return 2;
}
