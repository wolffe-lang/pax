/* px145: execve(2) of a dynamic program. For each path in argv[1..],
 * execve(path, {path, NULL}, environ); each call that returns prints
 * `execdyn: <path>: errno <n>` (PAX refuses an ET_DYN or PT_INTERP
 * program, -ENOEXEC, and names the interpreter in its own line). A call
 * that succeeds replaces this program, so on Linux the first path runs.
 * Then `execdyn: done`. Written from execve(2); no C library's or
 * kernel's source was read. */
#include <errno.h>
#include <stdio.h>
#include <unistd.h>

extern char **environ;

int main(int argc, char **argv) {
    for (int i = 1; i < argc; i++) {
        char *v[] = {argv[i], NULL};
        execve(argv[i], v, environ);
        printf("execdyn: %s: errno %d\n", argv[i], errno);
        fflush(stdout);
    }
    printf("execdyn: done\n");
    return 0;
}
