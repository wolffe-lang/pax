/* Journal failure probe: Linux ABI calls only; each run owns its image. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
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
    if (!strcmp(which, "pre-mount-barrier")) {
        memset(data, 'Q', sizeof(data));
        int raw = open("/dev/vda", O_WRONLY);
        result("prime-open", raw);
        if (raw >= 0) {
            result("prime-seek", lseek(raw, 64 * 1024 * 1024, SEEK_SET));
            result("prime-write", write(raw, data, sizeof(data)));
            close(raw); /* No fsync: make the backend dirty outside the filesystem. */
        }
    }
    int mounted = mount("/dev/vda", "/volume", !strcmp(which, "plain-control") ? "ext2" : "ext3", 0, NULL);
    result("mount", mounted);
    if (mounted < 0 && (!strcmp(which, "mount-error") || !strcmp(which, "mount-state-flush"))) {
        result("mount-after", mount("/dev/vda", "/volume", "ext3", 0, NULL));
    }
    if (mounted < 0 || !strncmp(which, "refuse", 6) || !strcmp(which, "pre-mount-barrier")
        || !strcmp(which, "mount-error") || !strcmp(which, "mount-state-flush")) done();
    if (!strcmp(which, "reuse-recover")) {
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
        result("unmount", umount("/volume"));
        done();
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
    if (!strncmp(which, "checkpoint", 10) || !strncmp(which, "control", 7) || !strcmp(which, "plain-control")) {
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
