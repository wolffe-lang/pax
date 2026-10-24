/* px70 own black-box keyboard probe; public terminal interfaces only. */
#define main px59_unused_main
#include "../px59/vtprobe2.c"
#undef main
#include "keys70.h"
int main(void) {
    mkdir("/dev",0755); mount("devtmpfs","/dev","devtmpfs",0,0);
    out=open("/dev/console",O_RDWR|O_NOCTTY); vt=open("/dev/tty1",O_RDWR|O_NOCTTY);
    if (out<0 || vt<0 || tcgetattr(vt,&raw)<0) return 2;
    cfmakeraw(&raw);
#ifdef PX70_YEW_MODE
    /* termwolf's os_term_set_mode(RAW), observed on Linux: unlike
     * cfmakeraw this leaves ICRNL set. No expected bytes are changed here. */
    raw.c_iflag=0x100; raw.c_oflag=0x5; raw.c_cflag=0xbf; raw.c_lflag=0xa30;
    raw.c_cc[VMIN]=1; raw.c_cc[VTIME]=0;
#endif
    if (tcsetattr(vt,TCSANOW,&raw)<0 || tcgetattr(vt,&raw)<0) return 2;
    dprintf(out,"MODE iflag=%x oflag=%x cflag=%x lflag=%x vmin=%u vtime=%u\n",
            raw.c_iflag,raw.c_oflag,raw.c_cflag,raw.c_lflag,raw.c_cc[VMIN],raw.c_cc[VTIME]);
    for (unsigned i=0;i<sizeof labels/sizeof labels[0];i++) {
        tcflush(vt,TCIFLUSH); dprintf(out,"KEYREADY %u %s\n",i,labels[i]);
        unsigned char b[256]; int n=0; struct pollfd p={vt,POLLIN,0};
        if (poll(&p,1,3000)>0) {
            do { int k=read(vt,b+n,sizeof b-n); if(k<=0)break; n+=k; }
            while(n<(int)sizeof b && poll(&p,1,200)>0);
        }
        dprintf(out,"KEY %s",labels[i]);
        for(int j=0;j<n;j++)dprintf(out," %02x",b[j]);
        dprintf(out,"%s\n",n?"":" none");
    }
    dprintf(out,"DONE px70 keys\n"); sync(); reboot(RB_POWER_OFF); return 0;
}
