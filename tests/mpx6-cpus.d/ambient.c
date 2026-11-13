/* Black-box the freestanding runtime's documented ambient get/set pair.
 * Two real host threads stand for two CPUs; no other runtime source is read.
 * The addresses are opaque: the getter/setter never dereference either.
 */
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <sys/resource.h>
extern void *wolf_rt_ambient_get(void);
extern void wolf_rt_ambient_set(void *);
static pthread_barrier_t bar;
static uintptr_t a, b;
static void *observed;
void *wolf_alloc(size_t size, size_t align) { void *p=0; if(posix_memalign(&p,align<sizeof(void*)?sizeof(void*):align,size)) abort();return p; }
void wolf_free(void *p,size_t size,size_t align) { (void)size;(void)align;free(p); }
void wolf_trap(void) { abort(); }
static void *first(void *unused) {
    (void)unused;
    wolf_rt_ambient_set(&a);
    pthread_barrier_wait(&bar);
    pthread_barrier_wait(&bar);
    observed=wolf_rt_ambient_get();
    return 0;
}
static void *second(void *unused) {
    (void)unused;
    pthread_barrier_wait(&bar);
    wolf_rt_ambient_set(&b);
    pthread_barrier_wait(&bar);
    return 0;
}
int main(void) {
    pthread_t x,y;
    struct timespec start,end;struct rusage before,after;
    clock_gettime(CLOCK_MONOTONIC,&start);getrusage(RUSAGE_SELF,&before);
    if(pthread_barrier_init(&bar,0,2)||pthread_create(&x,0,first,0)||pthread_create(&y,0,second,0)) return 2;
    if(pthread_join(x,0)||pthread_join(y,0))return 2;
    clock_gettime(CLOCK_MONOTONIC,&end);getrusage(RUSAGE_SELF,&after);
    double wall=(end.tv_sec-start.tv_sec)+(end.tv_nsec-start.tv_nsec)/1e9;
    double cpu=(after.ru_utime.tv_sec-before.ru_utime.tv_sec)+(after.ru_utime.tv_usec-before.ru_utime.tv_usec)/1e6
              +(after.ru_stime.tv_sec-before.ru_stime.tv_sec)+(after.ru_stime.tv_usec-before.ru_stime.tv_usec)/1e6;
    printf("MEASURE ambient busy_cpus=%.3f cpu_s=%.6f wall_s=%.6f\n",cpu/wall,cpu,wall);
    if(observed==&b){puts("FAIL CPU-AMBIENT-ISOLATION A reads B after concurrent CPU publication");return 1;}
    if(observed==&a){puts("PASS CPU-AMBIENT-ISOLATION A retains A");return 0;}
    puts("FAIL CPU-AMBIENT-ISOLATION unexpected ambient pointer");return 2;
}
