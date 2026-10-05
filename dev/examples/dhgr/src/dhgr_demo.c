/* Animated masked sprite on two DHGR pages, with save-under restoration. */
#include "dhgr.h"
#include "apple2io.h"
#include "apple2frame.h"
#include "gfx.h"
#include "ball.h"
static unsigned char under[2][BALL_STRIDE*BALL_HEIGHT];
static unsigned char old_x[2], saved[2];
static void background(void)
{
    unsigned char color;
    dhgr_clear(DHGR_BLACK);
    dhgr_puts("APPLE II DHGR",10,8);
    for (color=0; color<16u; ++color)
        dhgr_fill_rect(color*8u+6u,32,8,72,color);
    dhgr_set_color(DHGR_AQUA);
    gfx_circle(70,142,30);
    dhgr_puts("KEY TO EXIT",18,178);
}
int main(void)
{
    unsigned char page, x=6;
    if (!dhgr_init()) {
        a2_puts("DHGR REQUIRES IIE 128K OR IIC\r");
        return 0;
    }
    a2_frame_init();
    background();
    dhgr_draw_page(2);
    background();
    while (!apple2_iskeypressed()) {
        page=dhgr_get_draw_page()-1u;
        if (saved[page])
            dhgr_write_block((unsigned char)((unsigned)old_x[page]*4u/7u),138,
                             BALL_STRIDE,BALL_HEIGHT,under[page],BALL_STRIDE);
        dhgr_read_block((unsigned char)((unsigned)x*4u/7u),138,
                        BALL_STRIDE,BALL_HEIGHT,under[page],BALL_STRIDE);
        dhgr_sprite(x,138,BALL_WIDTH,BALL_HEIGHT,BALL_STRIDE,ball_data,ball_mask);
        old_x[page]=x;
        saved[page]=1;
        a2_frame_wait();
        dhgr_flip();
        if (++x>127u) x=6;
    }
    apple2_readkey();
    dhgr_text_restore();
    a2_home();
    return 0;
}
