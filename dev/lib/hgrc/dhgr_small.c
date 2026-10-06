/* VERHILLE Arnaud — GPL-3.0. Compact white DHGR text, color-safe cells. */
#include "dhgr.h"
unsigned char dhgr_small_x, dhgr_small_y;
void dhgr_puts_small(const char *s,unsigned char x,unsigned char y)
{
    dhgr_small_y=y;
    if(y>187u) return;
    while(*s && x<=135u) {
        dhgr_small_x=x;
        dhgr_small_char((unsigned char)*s++);
        x+=5u;
    }
}
