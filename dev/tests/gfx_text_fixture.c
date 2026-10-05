/* VERHILLE Arnaud — GPL-3.0. Cell text through the default HGR archive. */
#include "hgr.h"
#include "gfx.h"
#define STAGE (*(volatile unsigned char *)0x1000)
static void checkpoint(unsigned char n)
{
    STAGE = n;
    apple2_getkey();
}
int main(void)
{
    hgr_init(); hgr_set_draw_page(1u); hgr_clear(0x2Au);
    hgr_set_draw_page(2u); hgr_clear(0u);
    checkpoint(0u);
    gfx_cell_color(3u); /* native HGR text remains white */
    gfx_gotoxy(34u,0u); gfx_text("AB\nC\rD"); checkpoint(1u);
    gfx_gotoxy(2u,3u); gfx_putu(65535u);
    gfx_gotoxy(2u,4u); gfx_puti(-32767-1);
    gfx_gotoxy(2u,5u); gfx_putx(0xABCDu); checkpoint(2u);
    gfx_gotoxy(255u,255u); gfx_text("ZQ"); checkpoint(3u);
    return 0;
}
