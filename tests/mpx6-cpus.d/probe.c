/* Read the census in small pieces. No libc. */
typedef unsigned long U;
static long call(U n,U a,U b,U c){long r; __asm__ volatile("syscall":"=a"(r):"a"(n),"D"(a),"S"(b),"d"(c):"rcx","r11","memory");return r;}
static void out(const char*s,U n){call(1,1,(U)s,n);}
void _start(void){
    char buf[512]; U n=0; long fd=call(2,(U)"/proc/pax-cpus",0,0);
    if(fd<0){out("CPU-PROC missing\n",17);call(60,1,0,0);}
    for(;;){long k=call(0,fd,(U)(buf+n),7);if(k<0||n+(U)k>=sizeof buf){out("CPU-PROC read failed\n",21);call(60,2,0,0);}if(!k)break;n+=k;}
    out("CPU-PROC begin\n",15);out(buf,n);out("CPU-PROC end\n",13);
    call(3,fd,0,0);call(60,0,0,0);for(;;){}
}
