/* VERHILLE Arnaud — GPL-3.0. Minimal animated HGR starter. */
#include "hgr.h"
#include "gfx.h"
#include "ball.h"

static const hgr_mspr_t ball = {ball_data, ball_mask, BALL_STRIDE, BALL_HEIGHT};

static void background(void)
{
    unsigned x;
    unsigned char y;
    hgr_clear(0u);
    hgr_puts8(16u, 8u, "APPLE II HGR STARTER");
    hgr_puts8(16u, 24u, "FRAME");
    hgr_puts8(16u, 176u, "ARROWS: DIRECTION  SPACE: PAUSE");
    hgr_puts8(16u, 184u, "ESC: DOS");
    gfx_rect(8u, 60u, 271u, 168u);
    for (x = 28u; x < 270u; x += 28u) gfx_vline(x, 61u, 167u);
    for (y = 76u; y < 168u; y += 16u) gfx_hline(9u, 270u, y);
}

int main(void)
{
    unsigned x = 24u, frame = 0u;
    unsigned char y = 80u, key, paused = 0u;
    signed char dx = 1, dy = 1;
    hgr_init();
    a2_frame_init();
    /* Delay is added to render time on II/II+/IIc; tune for your workload. */
    a2_frame_set_delay(70u);
    hgr_set_draw_page(1u); background();
    hgr_set_draw_page(2u); background();
    hgr_spr_init(1u);
    if (!hgr_spr_define(0u, &ball)) return 1;
    for (;;) {
        key = apple2_readkey();
        if (key == KC_ESC) break;
        if (key == ' ') paused ^= 1u;
        if (key == KC_LEFT) dx = -1;
        if (key == KC_RIGHT) dx = 1;
        if (key == KC_UP) dy = -1;
        if (key == KC_DOWN) dy = 1;
        if (!paused) {
            if (x <= 10u) dx = 1;
            if (x >= 260u) dx = -1;
            if (y <= 62u) dy = 1;
            if (y >= 158u) dy = -1;
            x += dx;
            y += dy;
        }
        hgr_spr_move(0u, x, y);
        hgr_spr_render();
        /* HUD is outside the sprite area; draw into the same hidden page. */
        hgr_putu_field(72u, 24u, frame++, 5u);
        a2_frame_wait();
        hgr_spr_present();
    }
    /* Returning from main restores the text display and DOS via the CRT. */
    return 0;
}
