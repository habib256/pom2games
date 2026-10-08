/* VERHILLE Arnaud — GPL-3.0. Rebuild /RAM after DHGR auxiliary video use. */
#include "prodos.h"
#define BYTE(a) (*(volatile unsigned char *)(a))
static unsigned char ram_unit, claimed;
unsigned char __fastcall__ prodos_format_ram(unsigned char unit);
void prodos_video_claim(void)
{
    unsigned char i, unit, index;
    claimed=1; ram_unit=0;
    i=BYTE(0xBF31);
    /* DEVCNT is count-1; DEVLST occupies $BF32..$BF3F (14 entries).
     * $FF means empty. Larger indices would read the copyright area. */
    if (i>=14u) return;
    do {
        unit=BYTE(0xBF32u+i)&0xF0u;
        index=unit>>3;
        if (BYTE(0xBF10u+index)==0 && BYTE(0xBF11u+index)==0xFFu) {
            ram_unit=unit; return;
        }
    } while (i--);
}
unsigned char prodos_video_release(void)
{
    unsigned char ok=1;
    if (claimed && ram_unit) ok=prodos_format_ram(ram_unit);
    claimed=0;
    return ok;
}
