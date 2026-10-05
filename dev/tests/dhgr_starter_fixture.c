/* Compare the starter's fast renderer with the general DHGR primitives. */
#include "dhgr.h"
#include "apple2io.h"
#include "ball.h"
void __fastcall__ ball_restore(unsigned char id);
void __fastcall__ ball_draw(unsigned char id);
void __fastcall__ counter_digit(unsigned char column);
unsigned char ball_x[3], ball_y[3], old_x[2][3], old_y[2][3];
char frame_text[] = "00000";
static const char * const counts[] = {
    "00000", "00009", "01234", "56789", "00100", "00999", "01000", "99999"
};
#define STAGE (*(volatile unsigned char *)0x1000)
static void background(void)
{
    dhgr_clear(DHGR_BLUE);
    dhgr_fill_rect(63,24,36,8,DHGR_BLACK);
}
int main(void)
{
    unsigned char stage, i;
    char digit[2];
    if (!dhgr_init()) return 1;
    dhgr_draw_page(2);
    background();
    digit[1]=0;
    for (stage=0; stage<8u; ++stage) {
        dhgr_draw_page(2);
        if (stage) {
            i=3u;
            while (i-- > 0u) ball_restore(i);
        }
        for (i=0; i<3u; ++i) {
            ball_x[i]=20u+stage;
            ball_y[i]=1u+stage*24u;
            if (stage==7u) { ball_x[i]=126u; ball_y[i]=184u; }
            if (i==1u) ball_x[i]+=4u;
            else ball_x[i]+=i;
            ball_y[i]+=i;
            ball_draw(i);
        }
        for (i=0; i<5u; ++i) {
            frame_text[i]=counts[stage][i];
            counter_digit(i);
        }
        dhgr_draw_page(1);
        background();
        for (i=0; i<3u; ++i)
            dhgr_sprite(ball_x[i],ball_y[i],BALL_WIDTH,BALL_HEIGHT,BALL_STRIDE,
                        ball_data,ball_mask);
        for (i=0; i<5u; ++i) {
            digit[0]=frame_text[i];
            dhgr_puts(digit,63u+i*7u,24u);
        }
        STAGE=stage;
        apple2_getkey();
    }
    dhgr_draw_page(2);
    i=3u;
    while (i-- > 0u) ball_restore(i);
    dhgr_fill_rect(63,24,36,8,DHGR_BLACK);
    dhgr_draw_page(1);
    background();
    STAGE=8u;
    apple2_getkey();
    return 0;
}
