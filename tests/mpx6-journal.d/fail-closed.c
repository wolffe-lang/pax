/* Journal failure probe: Linux ABI calls only; each run owns its image. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/falloc.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

static void result(const char *name, long value) {
    int error = value < 0 ? errno : 0;
    printf("JF %s rc=%ld errno=%d\n", name, value, error);
    fflush(stdout);
}
static void done(void) {
    puts("JF DONE"); fflush(stdout);
    for (;;) pause(); /* The QEMU runner cuts power, not a guest process. */
}
int main(void) {
    char which[64] = {0}, data[4096];
    int c = open("/case", O_RDONLY);
    if (c < 0) return 2;
    ssize_t received = read(c, which, sizeof(which)-1);
    close(c);
    if (received <= 0) return 2;
    mkdir("/volume", 0755);
    if (!strcmp(which, "pre-mount-barrier") || !strcmp(which, "rw-barrier-error")) {
        memset(data, 'Q', sizeof(data));
        int raw = open("/dev/vda", O_WRONLY);
        result("prime-open", raw);
        if (raw >= 0) {
            result("prime-seek", lseek(raw, 64 * 1024 * 1024, SEEK_SET));
            result("prime-write", write(raw, data, sizeof(data)));
            close(raw); /* No fsync: make the backend dirty outside the filesystem. */
        }
    }
    unsigned long flags = (!strncmp(which, "ro-", 3) || !strncmp(which, "late-rw-", 8)
                           || !strcmp(which, "rw-barrier-error")) ? MS_RDONLY : 0;
    int mounted = mount("/dev/vda", "/volume", !strcmp(which, "plain-control") ? "ext2" : "ext3", flags, NULL);
    result("mount", mounted);
    if (mounted < 0 && (!strcmp(which, "mount-error") || !strcmp(which, "mount-state-flush"))) {
        result("mount-after", mount("/dev/vda", "/volume", "ext3", 0, NULL));
    }
    if (mounted < 0 || !strncmp(which, "refuse", 6) || !strcmp(which, "pre-mount-barrier")
        || !strcmp(which, "mount-error") || !strcmp(which, "mount-state-flush")
        || !strcmp(which, "ro-replay-refuse")) done();
    if (!strcmp(which, "rw-barrier-error")) {
        /* A writable remount's qualification barrier fails before any write:
           the volume stays read-only, can be let go, and the next mount
           qualifies its own barrier before its first write. */
        result("barrier-remount", mount(NULL, "/volume", "ext3", MS_REMOUNT, NULL));
        int fd = open("/volume/late", O_CREAT|O_WRONLY|O_EXCL, 0600);
        result("barrier-create-after", fd);
        if (fd >= 0) close(fd);
        result("barrier-unmount", umount("/volume"));
        int excl = open("/dev/vda", O_RDONLY|O_EXCL);
        result("barrier-excl-after", excl);
        if (excl >= 0) close(excl);
        result("barrier-mount-new", mount("/dev/vda", "/volume", "ext3", 0, NULL));
        fd = open("/volume/late", O_CREAT|O_WRONLY|O_EXCL, 0600);
        result("barrier-create-new", fd);
        if (fd >= 0) {
            result("barrier-fsync-new", fsync(fd));
            close(fd);
        }
        result("barrier-unmount-new", umount("/volume"));
        done();
    }
    if (!strncmp(which, "late-", 5)) {
        int ro = !strncmp(which, "late-ro-", 8);
        int unmounting = !strncmp(which, "late-unmount-", 13);
        int operation = unmounting ? umount("/volume")
            : mount(NULL, "/volume", "ext3", MS_REMOUNT | (ro ? MS_RDONLY : 0), NULL);
        result("late-operation", operation);
        if (strstr(which, "-error")) {
            /* After a device error the volume stays failed and its device claimed. */
            result("late-unmount-after", umount("/volume"));
            result("late-rw-after", mount(NULL, "/volume", "ext3", MS_REMOUNT, NULL));
            /* The block layer's own claim: an exclusive open, not the covered mount point. */
            int excl = open("/dev/vda", O_RDONLY|O_EXCL);
            result("late-excl-after", excl);
            if (excl >= 0) close(excl);
            mkdir("/again", 0755);
            int again = mount("/dev/vda", "/again", "ext3", 0, NULL);
            result("late-mount-after", again);
            if (again == 0) {
                int fd = open("/again/late", O_CREAT|O_WRONLY|O_EXCL, 0600);
                result("late-create-after", fd);
                if (fd >= 0) {
                    result("late-fsync-after", fsync(fd));
                    close(fd);
                }
            }
        } else if (!unmounting) {
            result("late-cleanup", umount("/volume"));
        }
        done();
    }
    if (!strncmp(which, "overwrite-", 10)) {
        char pair[8192];
        memset(pair, 'N', sizeof(pair));
        int fd = open("/volume/two", O_WRONLY);
        result("overwrite-open", fd);
        if (fd < 0) done();
        result("overwrite-write", write(fd, pair, sizeof(pair)));
        if (!strcmp(which, "overwrite-error")) {
            result("overwrite-after", write(fd, pair, sizeof(data)));
        }
        result("overwrite-sync", fsync(fd));
        close(fd);
        if (!strcmp(which, "overwrite-control")) result("unmount", umount("/volume"));
        done();
    }
    if (!strncmp(which, "punch-", 6)) {
        int fd = open("/volume/two", O_WRONLY);
        result("punch-open", fd);
        if (fd < 0) done();
        result("punch", fallocate(fd, FALLOC_FL_PUNCH_HOLE | FALLOC_FL_KEEP_SIZE, 0, 8192));
        if (!strcmp(which, "punch-error")) {
            result("punch-after", fallocate(fd, FALLOC_FL_PUNCH_HOLE | FALLOC_FL_KEEP_SIZE, 0, 4096));
        }
        result("punch-sync", fsync(fd));
        close(fd);
        if (!strcmp(which, "punch-control")) result("unmount", umount("/volume"));
        done();
    }
    if (!strncmp(which, "punchmap-", 9)) {
        /* Both pages in the tree's page cache through a shared mapping, then
           a punch whose second block fails: reads must match what the
           block cache holds where the punch zeroed it. */
        int fd = open("/volume/two", O_RDWR);
        result("punchmap-open", fd);
        if (fd < 0) done();
        char *map = mmap(NULL, 8192, PROT_READ, MAP_SHARED, fd, 0);
        result("punchmap-mmap", map == MAP_FAILED ? -1 : 0);
        if (map == MAP_FAILED) done();
        printf("JF punchmap-cached=%d\n", map[0] == 'A' && map[4096] == 'A');
        result("punchmap-punch", fallocate(fd, FALLOC_FL_PUNCH_HOLE | FALLOC_FL_KEEP_SIZE, 0, 8192));
        char back[8192];
        result("punchmap-read", pread(fd, back, sizeof(back), 0));
        int read_first = 1, map_first = 1, read_second = 1, coherent = 1;
        for (int i = 0; i < 8192; ++i) {
            if (back[i] != map[i]) coherent = 0;
            if (i < 4096 && back[i]) read_first = 0;
            if (i < 4096 && map[i]) map_first = 0;
            if (i >= 4096 && back[i]) read_second = 0;
        }
        printf("JF punchmap-read-first-zero=%d\nJF punchmap-map-first-zero=%d\n"
               "JF punchmap-read-second-zero=%d\nJF punchmap-coherent=%d\n",
               read_first, map_first, read_second, coherent);
        fflush(stdout);
        munmap(map, 8192);
        if (!strcmp(which, "punchmap-control")) {
            result("punchmap-sync", fsync(fd));
            close(fd);
            result("unmount", umount("/volume"));
        }
        done();
    }
    if (!strncmp(which, "otrunc-", 7)) {
        int fd = open("/volume/old", O_WRONLY|O_TRUNC);
        result("otrunc-open", fd);
        if (fd >= 0) {
            result("otrunc-fsync", fsync(fd));
            close(fd);
        }
        if (!strcmp(which, "otrunc-control")) {
            result("unmount", umount("/volume"));
            done();
        }
        int dir = open("/volume", O_RDONLY|O_DIRECTORY);
        result("otrunc-dir", dir);
        if (dir >= 0) {
            result("otrunc-syncfs-after", fsync(dir));
            close(dir);
        }
        int later = open("/volume/later", O_CREAT|O_WRONLY|O_EXCL, 0600);
        result("otrunc-create-after", later);
        if (later >= 0) close(later);
        done();
    }
    if (!strcmp(which, "ro-remount")) {
        result("remount", mount(NULL, "/volume", "ext3", MS_REMOUNT, NULL));
        done();
    }
    if (!strcmp(which, "prefix-recover")) {
        int anchor = open("/volume/anchor", O_RDONLY), good = 0;
        result("anchor-open", anchor);
        if (anchor >= 0) {
            ssize_t n = read(anchor, data, sizeof(data));
            good = n == (ssize_t)sizeof(data);
            for (int i=0; i<n; ++i) if (data[i] != 'A') good = 0;
            close(anchor);
        }
        printf("JF anchor-bytes=%d\n", good);
        int later = open("/volume/new", O_RDONLY);
        result("uncommitted-open", later);
        if (later >= 0) close(later);
        later = open("/volume/later", O_RDONLY);
        result("later-open", later);
        if (later >= 0) close(later);
        result("unmount", umount("/volume"));
        done();
    }
    if (!strcmp(which, "reuse-commit")) {
        result("unlink-old", unlink("/volume/old"));
        int directory = open("/volume", O_RDONLY|O_DIRECTORY);
        result("free-fsync", fsync(directory));
        if (directory >= 0) close(directory);
        int fd = open("/volume/new", O_CREAT|O_WRONLY|O_EXCL, 0600);
        result("open", fd);
        memset(data, 'N', sizeof(data));
        if (fd >= 0) {
            result("reuse-write", write(fd, data, sizeof(data)));
            result("reuse-fsync", fsync(fd));
            close(fd);
        }
        done();
    }
    if (!strcmp(which, "reuse-recover") || !strcmp(which, "ro-control")) {
        int fd = open("/volume/old", O_RDONLY);
        result("old-open", fd);
        int good = 0;
        if (fd >= 0) {
            ssize_t n = read(fd, data, sizeof(data));
            good = n == (ssize_t)sizeof(data);
            for (int i=0; i<n; ++i) if (data[i] != 'A') good=0;
            close(fd);
        }
        printf("JF old-bytes=%d\n", good);
        result("unmount", umount("/volume"));
        done();
    }
    if (!strcmp(which, "reuse")) {
        result("unlink-old", unlink("/volume/old"));
        int fd = open("/volume/new", O_CREAT|O_WRONLY|O_EXCL, 0600);
        result("open", fd);
        memset(data, 'N', sizeof(data));
        if (fd >= 0) result("reuse-write", write(fd, data, sizeof(data)));
        int filler = open("/volume/filler", O_RDONLY);
        result("filler-open", filler);
        long bytes = 0;
        if (filler >= 0) {
            for (int i=0; i<4096; ++i) {
                ssize_t n = read(filler, data, sizeof(data));
                if (n <= 0) break;
                bytes += n;
            }
            close(filler);
        }
        printf("JF pressure-bytes=%ld\n", bytes);
        if (fd >= 0) close(fd);
        done();
    }
    if (!strncmp(which, "recover", 7)) {
        int fd = open("/volume/new", O_RDONLY);
        result("recovered-open", fd);
        if (fd >= 0) {
            ssize_t n = read(fd, data, sizeof(data));
            result("recovered-read", n);
            int good = n == (ssize_t)sizeof(data);
            for (int i=0; i<n; ++i) if (data[i] != 'N') good=0;
            printf("JF recovered-bytes=%d\n", good);
            close(fd);
        }
        if (!strcmp(which, "recover-reuse")) {
            int old = open("/volume/old", O_RDONLY);
            result("old-after", old);
            if (old >= 0) close(old);
        }
        result("unmount", umount("/volume"));
        done();
    }
    if (!strncmp(which, "prefix-", 7)) {
        memset(data, 'A', sizeof(data));
        int anchor = open("/volume/anchor", O_CREAT|O_WRONLY|O_EXCL, 0600);
        result("anchor-open", anchor);
        if (anchor < 0) done();
        result("anchor-write", write(anchor, data, sizeof(data)));
        result("anchor-fsync", fsync(anchor));
        close(anchor);
    }
    memset(data, 'N', sizeof(data));
    int fd = open("/volume/new", O_CREAT|O_WRONLY|O_EXCL, 0600);
    result("open", fd);
    if (fd < 0) done();
    result("write", write(fd, data, sizeof(data)));
    if (!strcmp(which, "checkpoint-barrier")) {
        close(fd);
        result("unmount", umount("/volume"));
        done();
    }
    result("fsync", fsync(fd));
    if (!strcmp(which, "committed-cut")) {
        close(fd);
        done();
    }
    if (!strcmp(which, "cache-error")) {
        int pressure = open("/volume/pressure", O_RDONLY);
        result("pressure-open", pressure);
        long bytes = 0;
        if (pressure >= 0) {
            for (int i=0; i<4096; ++i) {
                ssize_t n = read(pressure, data, sizeof(data));
                if (n <= 0) break;
                bytes += n;
            }
            close(pressure);
        }
        printf("JF pressure-bytes=%ld\n", bytes);
        result("fsync-after", fsync(fd));
        int later = open("/volume/later", O_CREAT|O_WRONLY|O_EXCL, 0600);
        result("open-after", later);
        if (later >= 0) close(later);
        close(fd);
        result("unmount", umount("/volume"));
        done();
    }
    if (!strncmp(which, "checkpoint", 10) || !strncmp(which, "control", 7) || !strcmp(which, "plain-control") || !strcmp(which, "prefix-control")) {
        close(fd);
        result("unmount", umount("/volume"));
        done();
    }
    /* A one-shot device fault must remain a journal failure on later calls. */
    result("write-after", write(fd, data, sizeof(data)));
    result("fsync-after", fsync(fd));
    int later = open("/volume/later", O_CREAT|O_WRONLY|O_EXCL, 0600);
    result("open-after", later);
    if (later >= 0) close(later);
    close(fd);
    done();
    return 0;
}
