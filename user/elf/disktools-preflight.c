/* px69: non-destructive userspace prerequisites for pax#144.
 * Compile once for baseline Linux; run unchanged on PAX with two blank
 * virtio disks. No formatting, partition re-read or disk write occurs.
 * Interfaces: open(2), fstat(2), ioctl(2), read(2); BLKGETSIZE64 from uapi.
 */
#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>

static void device(const char *path) {
    struct stat st;
    uint64_t size = 0;
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        printf("disktools-preflight: %s open errno=%d\n", path, errno);
        return;
    }
    if (fstat(fd, &st) < 0)
        printf("disktools-preflight: %s fstat errno=%d\n", path, errno);
    else
        printf("disktools-preflight: %s block=%d\n", path, !!S_ISBLK(st.st_mode));
    if (ioctl(fd, BLKGETSIZE64, &size) < 0)
        printf("disktools-preflight: %s BLKGETSIZE64 errno=%d\n", path, errno);
    else
        printf("disktools-preflight: %s bytes=%llu\n", path, (unsigned long long)size);
    close(fd);
}

int main(void) {
    char buf[1024];
    ssize_t n;
    puts("disktools-preflight: begin (pax#144; read-only)");
    device("/dev/vda");
    device("/dev/vda1");
    device("/dev/vdb");
    puts("disktools-preflight: partitions begin");
    int fd = open("/proc/partitions", O_RDONLY);
    if (fd < 0) printf("disktools-preflight: partitions errno=%d\n", errno);
    else {
        while ((n = read(fd, buf, sizeof buf)) > 0) fwrite(buf, 1, (size_t)n, stdout);
        if (n < 0) printf("disktools-preflight: partitions read errno=%d\n", errno);
        close(fd);
    }
    puts("disktools-preflight: partitions end");
    puts("disktools-preflight: end");
    return 0;
}
