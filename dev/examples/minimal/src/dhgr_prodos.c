/* VERHILLE Arnaud — GPL-3.0. ProDOS 8, IIe 128K / IIc, NMOS 6502. */
#include "dhgr.h"
#include "prodos.h"
#include "apple2c.h"

unsigned frame;
unsigned char claimed;

void game_shutdown(void)
{
    dhgr_text_restore();
    if (claimed) { prodos_video_release(); claimed=0u; }
}

void minimal_present(void)
{
    a2_frame_wait();
    dhgr_flip();
}

int main(void)
{
    unsigned char page, y;
    /* Safe default: an installed /RAM is preserved by refusing AUX use. */
    if (prodos_video_claim(PD_VIDEO_PRESERVE_RAM) != PD_VIDEO_OK) {
        a2_puts("/RAM INSTALLED: AUX VIDEO REFUSED.\r");
        apple2_getkey();
        return 1;
    }
    claimed=1u;
    if (!dhgr_init()) return 1;
    a2_frame_init();
    a2_frame_set_delay(40u);
    for (page=1; page<=2; ++page) {
        dhgr_draw_page(page);
        for (y=0; y<192; y+=8) dhgr_clear_rows(y,8,0);
        dhgr_puts_small("ESC: PRODOS",0,0);
    }
    dhgr_draw_page(2);
    while (apple2_readkey() != KC_ESC) {
        dhgr_clear_rows(80,8,0);
        dhgr_fill_rect((unsigned char)(frame % 133u),80,7,7,DHGR_ORANGE);
        minimal_present();
        ++frame;
    }
    return 0; /* crt0_prodos invokes game_shutdown, then MLI QUIT. */
}
