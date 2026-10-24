/* mounts.c — px67's probe of the mount table and the mount calls: one
   static glibc program run unmodified on Linux (the Linux guest booted
   with `root=` on an ext2 partition, this program its init:
   tools/linux-root) and on PAX (the root on the disk that boots), the
   two outputs compared line by line (tests/mpx6-root).

     mounts init        (the guest's pid 1 only) mount /proc, /sys, /dev
                        and /tmp as a distribution's init does (the
                        flags kasumi's systemd gives them, measured:
                        proc and sysfs nosuid,nodev,noexec,relatime;
                        devtmpfs nosuid, mode=755; tmpfs nosuid,nodev,
                        mode=1777), then `table`, `calls`, `user` and
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
     mounts end         `/` remounted read-only and sync(2), as an init
                        does before reboot(2)
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
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
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
    say("statfs %s: type 0x%lx bsize %ld frsize %ld namelen %ld flags 0x%lx blocks %lu files %lu\n", path,
        (unsigned long)f.f_type, (long)f.f_bsize, (long)f.f_frsize, (long)f.f_namelen, (unsigned long)f.f_flags,
        (unsigned long)f.f_blocks, (unsigned long)f.f_files);
    say("~statfs %s: bfree %lu bavail %lu ffree %lu fsid %08x%08x\n", path, (unsigned long)f.f_bfree,
        (unsigned long)f.f_bavail, (unsigned long)f.f_ffree, (unsigned)f.f_fsid.__val[0], (unsigned)f.f_fsid.__val[1]);
    if (statvfs(path, &v) < 0) {
        say("statvfs %s = -1 %s\n", path, ename(errno));
        return;
    }
    say("statvfs %s: bsize %lu frsize %lu namemax %lu flag 0x%lx blocks %lu files %lu\n", path, v.f_bsize, v.f_frsize,
        v.f_namemax, v.f_flag, (unsigned long)v.f_blocks, (unsigned long)v.f_files);
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
    if (argc >= 2 && strcmp(argv[1], "linger") == 0) {
        linger(argc >= 3 ? argv[2] : NULL);
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
    say("usage: mounts table | calls DEV DIR | user UID DEV DIR | end | linger [halt|restart] | init [DEV DIR [disk-tmp [no-end]]]\n");
    return 2;
}
