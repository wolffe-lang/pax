/* px75b: a bounded LBA48 witness; the same static binary on PAX/Linux.
 * Never more than 128 KiB in memory. Images are sparse, not host devices.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static unsigned char data[131072], check[131072];
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    int fd = open(argv[1], O_RDWR);
    if (fd < 0) { printf("FAIL LBA48 open: %d\n", errno); return 1; }
    const uint64_t low = 17 * 512;
    const uint64_t high = (UINT64_C(1) << 41) + low;
    memset(data, 0x6b, sizeof data);
    if (pwrite(fd, data, sizeof data, low) != sizeof data) {
        puts("FAIL LBA48 low sentinel write"); return 1;
    }
    for (unsigned i = 0; i < sizeof data; i++) data[i] = (i * 31 + i / 512 + 7) & 255;
    if (pwrite(fd, data, sizeof data, high) != sizeof data || fsync(fd)) {
        puts("FAIL LBA48 high write/flush"); return 1;
    }
    if (pread(fd, check, sizeof check, high) != sizeof check || memcmp(data, check, sizeof data)) {
        puts("FAIL LBA48 high readback"); return 1;
    }
    if (pread(fd, check, sizeof check, low) != sizeof check) {
        puts("FAIL LBA48 low readback"); return 1;
    }
    for (unsigned i = 0; i < sizeof check; i++) {
        if (check[i] != 0x6b) { puts("FAIL LBA48 aliased below 2^32 sectors"); return 1; }
    }
    close(fd);
    puts("PASS LBA48: 128 KiB above sector 2^32; low sentinel intact");
    return 0;
}
