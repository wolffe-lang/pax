/* jbd2look: a static init for a Linux guest, black-box: what /proc/fs/jbd2 and
   /sys/dev/block show for an ext3 volume mounted read-write, read-only, after
   the documented `abort` remount option, after its unmount, and for plain ext2.
   Run by notes/px162/jbd2.sh; nothing of Linux's source is read. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/utsname.h>
#include <unistd.h>

static void say(const char *what, long r) {
    printf("LOOK %s rc=%ld errno=%d\n", what, r, r < 0 ? errno : 0);
    fflush(stdout);
}

static void list(const char *tag) {
    DIR *d = opendir("/proc/fs/jbd2");
    if (!d) { printf("LOOK %s jbd2-none errno=%d\n", tag, errno); fflush(stdout); return; }
    struct dirent *e;
    int n = 0;
    while ((e = readdir(d))) {
        if (e->d_name[0] == '.') continue;
        printf("LOOK %s jbd2 %s\n", tag, e->d_name);
        n++;
        char p[300];
        snprintf(p, sizeof(p), "/proc/fs/jbd2/%s", e->d_name);
        DIR *s = opendir(p);
        struct dirent *f;
        while (s && (f = readdir(s))) {
            if (f->d_name[0] == '.') continue;
            struct stat st;
            char q[600];
            snprintf(q, sizeof(q), "%s/%s", p, f->d_name);
            int ok = stat(q, &st);
            printf("LOOK %s jbd2 %s/%s mode=%o\n", tag, e->d_name, f->d_name, ok == 0 ? st.st_mode : 0);
        }
        if (s) closedir(s);
    }
    closedir(d);
    printf("LOOK %s jbd2-count %d\n", tag, n);
    fflush(stdout);
}

static void cat(const char *tag, const char *path) {
    char text[4096];
    int fd = open(path, O_RDONLY);
    if (fd < 0) { printf("LOOK %s cat-none %s errno=%d\n", tag, path, errno); fflush(stdout); return; }
    ssize_t n = read(fd, text, sizeof(text) - 1);
    close(fd);
    if (n < 0) n = 0;
    text[n] = 0;
    for (char *l = strtok(text, "\n"); l; l = strtok(NULL, "\n")) printf("LOOK %s cat %s\n", tag, l);
    fflush(stdout);
}

static void sysdev(const char *tag, const char *dir) {
    struct stat st;
    struct statfs sf;
    if (stat(dir, &st) < 0 || statfs(dir, &sf) < 0) { say("stat", -1); return; }
    char p[64], link[512];
    snprintf(p, sizeof(p), "/sys/dev/block/%u:%u", major(st.st_dev), minor(st.st_dev));
    ssize_t n = readlink(p, link, sizeof(link) - 1);
    if (n < 0) n = 0;
    link[n] = 0;
    struct stat ls;
    int l = lstat(p, &ls);
    printf("LOOK %s f_type=%lx st_dev=%u:%u %s lstat-mode=%o -> %s\n", tag, (unsigned long)sf.f_type,
           major(st.st_dev), minor(st.st_dev), p, l == 0 ? ls.st_mode : 0, link);
    fflush(stdout);
}

static void sysdevs(void) {
    DIR *d = opendir("/sys/dev/block");
    struct dirent *e;
    while (d && (e = readdir(d))) {
        if (e->d_name[0] == '.') continue;
        char p[300], link[512];
        snprintf(p, sizeof(p), "/sys/dev/block/%s", e->d_name);
        ssize_t n = readlink(p, link, sizeof(link) - 1);
        if (n < 0) n = 0;
        link[n] = 0;
        printf("LOOK sysdev %s -> %s\n", e->d_name, link);
    }
    if (d) closedir(d);
    struct stat st;
    printf("LOOK sys/dev mode=%o\n", stat("/sys/dev", &st) == 0 ? st.st_mode : 0);
    printf("LOOK proc/fs mode=%o\n", stat("/proc/fs", &st) == 0 ? st.st_mode : 0);
    printf("LOOK proc/fs/jbd2 mode=%o\n", stat("/proc/fs/jbd2", &st) == 0 ? st.st_mode : 0);
    fflush(stdout);
}

static void modules(void) {
    FILE *f = fopen("/lib/modules/order", "r");
    char name[128], path[300];
    while (f && fgets(name, sizeof(name), f)) {
        name[strcspn(name, "\n")] = 0;
        snprintf(path, sizeof(path), "/lib/modules/%s.ko", name);
        int fd = open(path, O_RDONLY | O_CLOEXEC);
        long r = fd < 0 ? -1 : syscall(SYS_finit_module, fd, "", 0);
        if (r < 0) printf("LOOK insmod %s errno=%d\n", name, errno);
        if (fd >= 0) close(fd);
    }
    if (f) fclose(f);
    for (int i = 0; i < 100 && (access("/dev/vda", F_OK) || access("/dev/vdb", F_OK)); i++) usleep(100000);
}

int main(void) {
    mount("proc", "/proc", "proc", 0, NULL);
    mount("sysfs", "/sys", "sysfs", 0, NULL);
    mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
    modules();
    struct utsname u;
    uname(&u);
    printf("LOOK uname %s\n", u.release);
    mkdir("/a", 0755);
    mkdir("/b", 0755);
    list("boot");
    say("mount-ext3-rw", mount("/dev/vda", "/a", "ext3", 0, NULL));
    list("rw");
    cat("rw", "/proc/fs/jbd2/vda-8/info");
    sysdev("rw", "/a");
    sysdevs();
    int fd = open("/a/f", O_CREAT | O_WRONLY, 0600);
    say("write", fd < 0 ? -1 : write(fd, "jbd2look\n", 9));
    say("fsync", fd < 0 ? -1 : fsync(fd));
    if (fd >= 0) close(fd);
    list("after-fsync");
    cat("after-fsync", "/proc/fs/jbd2/vda-8/info");
    say("mount-ext2", mount("/dev/vdb", "/b", "ext2", 0, NULL));
    list("ext2");
    sysdev("ext2", "/b");
    say("umount-ext2", umount("/b"));
    say("umount-ext3", umount("/a"));
    list("unmounted");
    say("mount-ext3-ro", mount("/dev/vda", "/a", "ext3", MS_RDONLY, NULL));
    list("ro");
    say("umount-ro", umount("/a"));
    say("mount-ext3-rw-again", mount("/dev/vda", "/a", "ext3", 0, NULL));
    list("rw-again");
    say("remount-abort", mount("/dev/vda", "/a", "ext3", MS_REMOUNT, "abort"));
    fd = open("/a/g", O_CREAT | O_WRONLY, 0600);
    say("open-after-abort", fd);
    if (fd >= 0) close(fd);
    list("aborted");
    cat("aborted", "/proc/fs/jbd2/vda-8/info");
    say("umount-aborted", umount("/a"));
    list("aborted-unmounted");
    puts("LOOK end");
    fflush(stdout);
    sync();
    reboot(RB_POWER_OFF);
    return 0;
}
