/* VERHILLE Arnaud — GPL-3.0. II/II+/IIe/IIc, DOS 3.3, NMOS 6502. */
#include "hgr.h"
#include "gfx.h"
#ifndef DOUBLE_BUFFERED
#define DOUBLE_BUFFERED 0
#endif

unsigned frame;
unsigned char draw_page;
static hgr_hud_field_t counter;

/* Separate entry also makes a convenient debugger/profiler checkpoint. */
void minimal_present(void)
{
    a2_frame_wait();
    hgr_show_page();
#if DOUBLE_BUFFERED
    draw_page = (draw_page == 1u) ? 2u : 1u;
    hgr_set_draw_page(draw_page);
#endif
}

int main(void)
{
    unsigned char page;
    hgr_init();
    a2_frame_init();
    a2_frame_set_delay(40u);
    for (page=1; page<=(DOUBLE_BUFFERED ? 2u : 1u); ++page) {
        hgr_set_draw_page(page);
        hgr_clear(0u);
        hgr_puts8(0u,0u,"ESC: DOS");
        gfx_line(0u,32u,279u,63u);
    }
    draw_page = DOUBLE_BUFFERED ? 2u : 1u;
    hgr_set_draw_page(draw_page);
    if (!hgr_hud_init(&counter,0u,16u,5u)) return 1;
    while (apple2_readkey() != KC_ESC) {
        /* Erase a visible strip, preserving the header and diagonal. */
        hgr_fill_rect(80u,8u,0u,40u,0u);
        hgr_fill_pixrect(frame % 273u,80u,7u,7u);
        hgr_hud_putu(&counter,frame);
        minimal_present();
        ++frame;
    }
    return 0; /* CRT restores video, ZP and the DOS return path. */
}
