/* px129: cpugaps -- how much of the CPU a busy program gets, and the gaps
 * when something else ran.
 *
 *   cpugaps [SECONDS]
 *
 * Spins in user mode for SECONDS (default 3) reading the TSC, and counts
 * every gap between two reads longer than 20 microseconds (an interrupt
 * handled, or another thread run): their number, their total, the
 * longest, and how many fall in each of 20-100 us, 0.1-1 ms, 1-10 ms and
 * over 10 ms. On one CPU a thread that never sleeps shows here as gaps of
 * a scheduler's quantum. The TSC's rate is measured against
 * CLOCK_MONOTONIC over an idle second first. Exit 0; 2 on a usage error.
 *
 * Written from the man pages of the calls named and the Intel SDM vol. 2
 * for RDTSC.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static inline uint64_t rdtsc(void) {
    uint32_t lo, hi;
    __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}

static uint64_t mono_ns(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000000000ull + (uint64_t)t.tv_nsec;
}

int main(int argc, char **argv) {
    double secs = argc > 1 ? strtod(argv[1], NULL) : 3;
    if (!(secs > 0) || secs > 600) { fprintf(stderr, "usage: cpugaps [SECONDS]\n"); return 2; }
    uint64_t m0 = mono_ns(), m;
    do { m = mono_ns(); } while (m == m0);
    uint64_t a = m, ta = rdtsc();
    do { m = mono_ns(); } while (m - a < 1000000000ull);
    uint64_t m1 = m;
    do { m = mono_ns(); } while (m == m1);
    double per_us = (double)(rdtsc() - ta) / ((double)(m - a) / 1e3);
    uint64_t span = (uint64_t)(secs * 1e6 * per_us), floor = (uint64_t)(20 * per_us);
    uint64_t t0 = rdtsc(), prev = t0, now, total = 0, longest = 0, n = 0, b[4] = {0, 0, 0, 0};
    do {
        now = rdtsc();
        uint64_t d = now - prev;
        if (d > floor) {
            n++;
            total += d;
            if (d > longest) longest = d;
            double us = (double)d / per_us;
            b[us < 100 ? 0 : us < 1000 ? 1 : us < 10000 ? 2 : 3]++;
        }
        prev = now;
    } while (now - t0 < span);
    double all = (double)(now - t0) / per_us;
    printf("cpugaps: %.2f s spun at TSC %.1f MHz: %llu gaps over 20 us, %.2f ms in all (the spinner had %.1f%% of the CPU); "
           "longest %.3f ms; 20-100 us %llu, 0.1-1 ms %llu, 1-10 ms %llu, over 10 ms %llu\n",
           all / 1e6, per_us, (unsigned long long)n, (double)total / per_us / 1e3, 100.0 * (1.0 - (double)total / per_us / all),
           (double)longest / per_us / 1e3, (unsigned long long)b[0], (unsigned long long)b[1], (unsigned long long)b[2],
           (unsigned long long)b[3]);
    return 0;
}
