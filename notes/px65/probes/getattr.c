/* px65 scratch probe: pthread_getattr_np for the main thread (glibc reads
 * /proc/self/maps for it), and whether /proc/self/maps opens. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
int main(void) {
    pthread_attr_t a;
    int rc = pthread_getattr_np(pthread_self(), &a);
    printf("getattr: pthread_getattr_np of the main thread: %d (%s)\n", rc, rc ? strerror(rc) : "ok");
    if (rc == 0) {
        void *lo; size_t len, g;
        pthread_attr_getstack(&a, &lo, &len);
        pthread_attr_getguardsize(&a, &g);
        printf("getattr: a stack of %s, guard %zu\n", len ? "some bytes" : "0 bytes", g);
        pthread_attr_destroy(&a);
    }
    int fd = open("/proc/self/maps", O_RDONLY);
    printf("getattr: open /proc/self/maps: %s\n", fd >= 0 ? "ok" : strerror(errno));
    return 0;
}
