/* A deterministic shell for the USB refusal session, entered by real login.
 * It runs real sudo/dmesg; no replacement for their permission or log paths.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    int mouse = open("/dev/mouse0", O_RDONLY | O_NONBLOCK);
    printf("REFUSAL-SHELL uid=%d mouse=%d\n", (int)getuid(), mouse >= 0);
    char line[64];
    while (fgets(line, sizeof line, stdin)) {
        if (!strcmp(line, "again\n")) {
            if (mouse >= 0) close(mouse);
            execl("/bin/login", "login", (char *)NULL);
            perror("login");
            return 1;
        }
        if (!strcmp(line, "mouse\n")) {
            unsigned char b[32];
            int moved = 0;
            ssize_t n;
            while ((n = read(mouse, b, sizeof b)) == (ssize_t)sizeof b) {
                int32_t dx;
                memcpy(&dx, b + 16, sizeof dx);
                if (dx == 7) moved = 1;
            }
            printf("REFUSAL-MOUSE moved=%d\n", moved);
        } else if (!strcmp(line, "log\n")) {
            puts("REFUSAL-LOG-BEGIN");
            pid_t p = fork();
            if (p == 0) {
                execl("/bin/sudo", "sudo", "/bin/dmesg", "-r", "-t", (char *)NULL);
                _exit(127);
            }
            int status = -1;
            if (p > 0 && waitpid(p, &status, 0) == p && WIFEXITED(status))
                printf("REFUSAL-LOG-END status=%d\n", WEXITSTATUS(status));
            else puts("REFUSAL-LOG-END status=wait-failed");
        } else puts("REFUSAL-BAD-COMMAND");
    }
    return 0;
}
