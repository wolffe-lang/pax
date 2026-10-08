/* bits.c: black-box — set one termios flag bit at a time with TCSETS
   (0x5402) on a pseudo-terminal, so strace -X verbose names each bit. */
#include <fcntl.h>
#include <unistd.h>
#include <sys/syscall.h>
int posix_openpt(int); int grantpt(int); int unlockpt(int); char *ptsname(int);
int main(void) {
    int m = posix_openpt(O_RDWR | O_NOCTTY); grantpt(m); unlockpt(m);
    int s = open(ptsname(m), O_RDWR | O_NOCTTY);
    unsigned int t[9] = {0};
    syscall(SYS_ioctl, s, 0x5401, t);
    unsigned int keep[9]; for (int i = 0; i < 9; i++) keep[i] = t[i];
    for (int w = 0; w < 4; w++)
        for (int b = 0; b < 17; b++) {
            for (int i = 0; i < 9; i++) t[i] = keep[i];
            t[w] = 1u << b;
            syscall(SYS_ioctl, s, 0x5402, t);
        }
    syscall(SYS_ioctl, s, 0x5402, keep);
    return 0;
}
