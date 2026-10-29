/* Black-box large-volume witness; Linux syscall ABI, not kernel source.
 * One file's inode and data are deliberately placed beyond 2 TiB.
 * Same static executable on PAX and Linux, deterministic bytes throughout.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <unistd.h>

static void fail(const char *what) {
    fprintf(stderr, "FAIL B-high-file: %s: %s\n", what, strerror(errno));
    exit(1);
}
static unsigned char pattern(unsigned long i, int seed) {
    return (unsigned char)(i * 17 + (unsigned)seed);
}
int main(int argc, char **argv) {
    if (argc != 5) return 2;
    int expected = atoi(argv[2]), next = atoi(argv[3]);
    size_t length = (size_t)strtoul(argv[4], NULL, 10);
    if (length != 4096 && length != 8192) return 2;
    int own_mount = strcmp(argv[1], "-") != 0;
    if (own_mount) {
        if (mkdir("/mnt", 0755) != 0 && errno != EEXIST) fail("mkdir");
        if (mount(argv[1], "/mnt", "ext2", 0, NULL) != 0) fail("mount");
    }
    int fd = open("/mnt/high", O_RDWR);
    if (fd < 0) fail("open");
    unsigned char b[8192];
    ssize_t n = pread(fd, b, sizeof b, 0);
    if (n != (ssize_t)length) fail("read length");
    for (size_t i = 0; i < length; ++i) {
        if (b[i] != pattern(i, expected)) {
            fprintf(stderr, "FAIL B-high-file: byte %zu got %u expected %u\n", i, b[i], pattern(i, expected));
            return 1;
        }
    }
    printf("PASS B-high-read: %zu bytes seed %d\n", length, expected);
    if (next >= 0) {
        for (size_t i = 0; i < sizeof b; ++i) b[i] = pattern(i, next);
        if (pwrite(fd, b, sizeof b, 0) != (ssize_t)sizeof b) fail("write");
        if (fsync(fd) != 0) fail("fsync");
        memset(b, 0, sizeof b);
        if (pread(fd, b, sizeof b, 0) != (ssize_t)sizeof b) fail("readback");
        for (size_t i = 0; i < sizeof b; ++i) if (b[i] != pattern(i, next)) fail("readback bytes");
        printf("PASS B-high-write: %zu bytes seed %d\n", sizeof b, next);
    }
    if (close(fd) != 0) fail("close");
    if (own_mount && umount("/mnt") != 0) fail("unmount");
    puts("PASS B-high-file: complete");
    return 0;
}
