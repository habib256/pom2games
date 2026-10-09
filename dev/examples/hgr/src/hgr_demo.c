/* VERHILLE Arnaud — GPL-3.0. Minimal animated HGR starter. */
#include "hgr.h"
#include "gfx.h"
#include "ball.h"

static const hgr_mspr_t ball = {ball_data, ball_mask, BALL_STRIDE, BALL_HEIGHT};
#define BALL_COUNT 3u
static unsigned char sprite_pool[2u * BALL_COUNT * BALL_STRIDE * BALL_HEIGHT];
static hgr_hud_field_t frame_field;

static unsigned ball_x[BALL_COUNT] = {24u, 128u, 232u};
static unsigned char ball_y[BALL_COUNT] = {80u, 112u, 144u};
static signed char ball_dx[BALL_COUNT] = {1, -1, 1};
static signed char ball_dy[BALL_COUNT] = {1, 1, -1};

static void ball_collisions(void)
{
    static unsigned char i, j;
    static int x, y, vx, vy;
    static signed char direction;

    for (i = 0u; i < BALL_COUNT; ++i) {
        for (j = i + 1u; j < BALL_COUNT; ++j) {
            x = (int)ball_x[i] - (int)ball_x[j];
            y = (int)ball_y[i] - (int)ball_y[j];
            /* Bound the differences before squaring on a 16-bit CPU. */
            if (x < -7 || x > 7 || y < -7 || y > 7) continue;
            if (x * x + y * y > 49) continue;
            vx = (int)ball_dx[i] - (int)ball_dx[j];
            vy = (int)ball_dy[i] - (int)ball_dy[j];
            /* Only approaching pairs bounce, so contact cannot flip them
             * back again while they are separating. Equal-speed balls
             * exchange their velocities for this simple arcade response. */
            if (x * vx + y * vy >= 0) continue;
            direction = ball_dx[i];
            ball_dx[i] = ball_dx[j];
            ball_dx[j] = direction;
            direction = ball_dy[i];
            ball_dy[i] = ball_dy[j];
            ball_dy[j] = direction;
        }
    }
}

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
    static unsigned frame = 0u;
    static unsigned char i, key, paused = 0u;
    hgr_init();
    a2_frame_init();
    /* Delay is added to render time on II/II+/IIc; tune for your workload. */
    a2_frame_set_delay(70u);
    hgr_set_draw_page(1u); background();
    hgr_set_draw_page(2u); background();
    if (!hgr_hud_init(&frame_field,72u,24u,5u)) return 1;
    /* Build the HUD tables and both page histories before animation. */
    for (i=1u; i<=2u; ++i) {
        hgr_set_draw_page(i);
        hgr_hud_putu(&frame_field,0u);
    }
    if (!hgr_spr_init_pool(1u, sprite_pool, sizeof(sprite_pool),
                          BALL_COUNT, BALL_STRIDE * BALL_HEIGHT)) return 1;
    for (i = 0u; i < BALL_COUNT; ++i) {
        if (!hgr_spr_define(i, &ball)) return 1;
    }
    for (;;) {
        key = apple2_readkey();
        if (key == KC_ESC) break;
        if (key == ' ') paused ^= 1u;
        for (i = 0u; i < BALL_COUNT; ++i) {
            if (key == KC_LEFT) ball_dx[i] = -1;
            if (key == KC_RIGHT) ball_dx[i] = 1;
            if (key == KC_UP) ball_dy[i] = -1;
            if (key == KC_DOWN) ball_dy[i] = 1;
            if (!paused) {
                if (ball_x[i] <= 10u) ball_dx[i] = 1;
                if (ball_x[i] >= 260u) ball_dx[i] = -1;
                if (ball_y[i] <= 62u) ball_dy[i] = 1;
                if (ball_y[i] >= 158u) ball_dy[i] = -1;
                ball_x[i] += ball_dx[i];
                ball_y[i] += ball_dy[i];
            }
        }
        if (!paused) ball_collisions();
        for (i = 0u; i < BALL_COUNT; ++i)
            hgr_spr_move(i, ball_x[i], ball_y[i]);
        hgr_spr_render();
        /* HUD is outside the sprite area; draw into the same hidden page. */
        hgr_hud_putu(&frame_field, frame++);
        a2_frame_wait();
        hgr_spr_present();
    }
    /* Returning from main restores the text display and DOS via the CRT. */
    return 0;
}
