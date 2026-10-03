/* Emulator fixture: host checks both banks independently at each checkpoint. */
#include "dhgr.h"
#include "apple2io.h"
#define STAGE (*(volatile unsigned char *)0x1000)
#define RESULT (*(volatile unsigned char *)0x1001)
static void checkpoint(unsigned char stage)
{
    STAGE = stage;
    apple2_getkey();
}
int main(void)
{
    unsigned x;
    unsigned char c;
    RESULT = 0;
    dhgr_init();
    for (c = 0; c < 16u; ++c) {
        dhgr_clear(c);
        checkpoint(c);
    }
    dhgr_clear(DHGR_BLACK);
    for (x = 0; x < 560u; ++x) {
        dhgr_plot(x, (unsigned char)(x % 192u), 1u);
        if (!dhgr_getpixel(x, (unsigned char)(x % 192u))) RESULT = 1;
    }
    for (x = 0; x < 560u; x += 3u)
        dhgr_plot(x, (unsigned char)(x % 192u), 0u);
    dhgr_plot(560u, 0u, 1u);
    dhgr_plot(65535u, 0u, 1u);
    dhgr_plot(0u, 192u, 1u);
    if (dhgr_getpixel(560u, 0u) || dhgr_getpixel(0u, 192u)) RESULT = 2;
    checkpoint(16u);
    for (c = 0; c < 140u; ++c) {
        dhgr_plot_color(c, 0u, c & 15u);
        dhgr_plot_color(c, 191u, (unsigned char)(15u - (c & 15u)));
    }
    dhgr_plot_color(140u, 0u, 15u);
    dhgr_plot_color(0u, 192u, 15u);
    checkpoint(17u);
    dhgr_fill_rect(138u, 190u, 255u, 255u, DHGR_ORANGE);
    dhgr_fill_rect(0u, 0u, 0u, 255u, DHGR_WHITE);
    dhgr_fill_rect(0u, 0u, 255u, 0u, DHGR_WHITE);
    dhgr_fill_rect(140u, 0u, 255u, 255u, DHGR_WHITE);
    checkpoint(18u);
    dhgr_text_restore();
    checkpoint(19u);
    dhgr_init();
    dhgr_clear(DHGR_WHITE);
    checkpoint(20u);
    dhgr_text_restore();
    return 0;
}
