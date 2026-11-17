/* A directory name with an invalid target is damage, never absence.
 * Built static with the same Ubuntu toolchain as the other ABI probes.
 * The host inspects directory entries after this probe, independently
 * of getdents/lstat in the kernel under test. */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <sys/stat.h>
#include <unistd.h>

static int failures;
static void row(const char *name, int ok, int result, int error) {
    printf("%s %s result=%d errno=%d\n", ok ? "PASS" : "FAIL", name, result, error);
    fflush(stdout);
    if (!ok) failures++;
}

int main(void) {
    struct stat st;
    const char *path = "/mnt/bin/burrowd.pax-tmp";
    errno = 0;
    int rc = lstat("/mnt/bin/kept", &st);
    row("damage-control-present", rc == 0 && S_ISREG(st.st_mode), rc, errno);
    errno = 0;
    rc = lstat("/mnt/bin/absent", &st);
    row("damage-control-absent", rc == -1 && errno == ENOENT, rc, errno);

    errno = 0;
    rc = lstat(path, &st);
    row("damage-lookup", rc == -1 && errno == EIO, rc, errno);
    for (int i = 0; i < 3; i++) {
        errno = 0;
        int fd = open(path, O_WRONLY | O_CREAT, 0600);
        int error = errno;
        row("damage-create", fd == -1 && (error == EIO || error == EEXIST), fd, error);
        if (fd >= 0) close(fd);
    }
    errno = 0;
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    int error = errno;
    row("damage-create-exclusive", fd == -1 && (error == EIO || error == EEXIST), fd, error);
    if (fd >= 0) close(fd);
    sync();
    printf("%s damage-probe failures=%d\n", failures ? "FAIL" : "PASS", failures);
    fflush(stdout);
    return failures != 0;
}
