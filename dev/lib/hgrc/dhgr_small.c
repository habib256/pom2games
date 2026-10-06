/* VERHILLE Arnaud — GPL-3.0. Compact white DHGR text, color-safe cells. */
#include "dhgr.h"
void dhgr_puts_small(const char *s,unsigned char x,unsigned char y)
{
    dhgr_small_x=x;
    dhgr_small_y=y;
    dhgr_small_string(s);
}
