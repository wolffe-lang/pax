/* termios.c: black-box — what TCGETS (0x5401) and TIOCGWINSZ (0x5413) fill on a
   Linux pseudo-terminal slave, as raw bytes. No header but the numbers. */
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/syscall.h>
int posix_openpt(int); int grantpt(int); int unlockpt(int); char *ptsname(int);
int main(void) {
    int m = posix_openpt(O_RDWR | O_NOCTTY); grantpt(m); unlockpt(m);
    int s = open(ptsname(m), O_RDWR | O_NOCTTY);
    unsigned char b[128]; long r;
    for (int i = 0; i < 128; i++) b[i] = 0xee;
    r = syscall(SYS_ioctl, s, 0x5401, b);
    printf("TCGETS rc %ld:", r); for (int i = 0; i < 64; i++) printf(" %02x", b[i]); printf("\n");
    for (int i = 0; i < 128; i++) b[i] = 0xee;
    r = syscall(SYS_ioctl, s, 0x5413, b);
    printf("TIOCGWINSZ rc %ld:", r); for (int i = 0; i < 16; i++) printf(" %02x", b[i]); printf("\n");
    r = syscall(SYS_ioctl, 1, 0x5401, b); printf("TCGETS on a pipe rc %ld\n", r);
    return 0;
}
