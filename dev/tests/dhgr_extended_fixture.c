#include "dhgr.h"
#include "apple2io.h"
#include "gfx.h"
#include "sprite.h"
void hgr_init(void);
void hgr_text_restore(void);
#define STAGE (*(volatile unsigned char *)0x1000)
#define RESULT (*(volatile unsigned char *)0x1001)
static unsigned char buffer[12];
static void checkpoint(unsigned char stage) { STAGE=stage; apple2_getkey(); }
int main(void)
{
    unsigned char page, phase, i;
    RESULT=0;
    if (!dhgr_init()) { checkpoint(99); return 0; }
    if (dhgr_capabilities()!=3) RESULT=1;
    dhgr_clear(6);
    dhgr_draw_page(2);
    dhgr_clear(9);
    checkpoint(0);
    for (page=1; page<=2; ++page) {
        dhgr_draw_page(page);
        /* Draw to each page while showing the opposite one. */
        dhgr_show_page(3-page);
        dhgr_hline(65535u,551u,190u,1);
        dhgr_vline(559u,255u,189u,0);
        dhgr_fill_bits(6,20,8,2,1);
        if (!dhgr_getpixel(6,20) || dhgr_getpixel(559,191)) RESULT=2;
        checkpoint(page);
    }
    for (page=1; page<=2; ++page) {
        dhgr_draw_page(page);
        dhgr_show_page(3-page);
        for (phase=0; phase<7; ++phase) {
            dhgr_sprite(phase,30+phase*3,SPRITE_WIDTH,SPRITE_HEIGHT,SPRITE_STRIDE,sprite_data,sprite_mask);
            checkpoint(3+(page-1)*7+phase);
        }
    }
    dhgr_draw_page(2);
    for (i=0; i<12; ++i) buffer[i]=0x55;
    dhgr_read_block(1,30,3,2,buffer,6);
    dhgr_draw_page(1);
    dhgr_write_block(77,190,3,2,buffer,6);
    dhgr_show_page(2);
    checkpoint(17);
    /* Clip preserves off-screen bytes in the caller's buffer. */
    for (i=0; i<12; ++i) buffer[i]=0x55;
    dhgr_read_block(79,191,3,2,buffer,6);
    if (buffer[1]!=0x55 || buffer[6]!=0x55) RESULT=3;
    dhgr_flip();
    if (dhgr_get_draw_page()!=2 || dhgr_get_display_page()!=1) RESULT=4;
    checkpoint(18);
    dhgr_puts("A",130,180);
    for(phase=0;phase<7;++phase) dhgr_puts_small("a?",phase,130+phase*6);
    dhgr_puts_small("A",135,187);
    dhgr_puts_small("A",136,187); /* incomplete cell must not wrap */
    dhgr_puts_small("A",135,188); /* incomplete height must not wrap */
    dhgr_puts_small("AB",255,130); /* rejected x must not wrap on advance */
    dhgr_puts_small("AB",0,255); /* rejected y must leave both banks intact */
    checkpoint(19);
    dhgr_set_color(15);
    gfx_filled_rect(65535u,255,0,188);
    checkpoint(20);
    hgr_init();
    checkpoint(21);
    dhgr_init();
    checkpoint(22);
    dhgr_text_restore();
    checkpoint(23);
    dhgr_init();
    return 0; /* crt0 must reset extended video switches without explicit restore */
}
