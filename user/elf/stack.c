/* PAX ELF-stack witness: a real automatic object larger than the old stack. */
#include <stdint.h>
#include <stdio.h>
#include <sys/resource.h>

__attribute__((noinline)) static int touch_stack(void) {
    volatile unsigned char bytes[256 * 1024];
    unsigned int sum = 0;
    for (unsigned int i = 0; i < sizeof bytes; i += 4096) bytes[i] = (unsigned char)(i / 4096);
    bytes[sizeof bytes - 1] = 63;
    for (unsigned int i = 0; i < sizeof bytes; i += 4096) sum += bytes[i];
    return sum == 2016 && bytes[sizeof bytes - 1] == 63;
}

int main(void) {
    struct rlimit limit;
    if (getrlimit(RLIMIT_STACK, &limit) != 0) return 2;
    if (!touch_stack()) return 3;
    printf("stack-probe: touched 262144 bytes; limit %llu %llu\n",
           (unsigned long long)limit.rlim_cur, (unsigned long long)limit.rlim_max);
    return limit.rlim_cur == 1048576 && limit.rlim_max == 1048576 ? 0 : 4;
}
