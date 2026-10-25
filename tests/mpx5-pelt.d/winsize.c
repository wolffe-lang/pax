/* A public ioctl ABI witness; do not infer a zero size from stty's prose. */
#include <stdio.h>
#include <sys/ioctl.h>
#include <unistd.h>
int main(void) {
    struct winsize size = {0};
    if (ioctl(STDIN_FILENO, TIOCGWINSZ, &size) != 0) {
        perror("winsize: TIOCGWINSZ");
        return 1;
    }
    printf("%u %u\n", (unsigned)size.ws_row, (unsigned)size.ws_col);
    return 0;
}
