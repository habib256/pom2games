/* DHGR color introduction, then three bouncing masked sprites on two pages. */
#include "dhgr.h"
#include "apple2io.h"
#include "apple2frame.h"
#include "gfx.h"
#define BALL_COUNT 3u
void __fastcall__ ball_restore(unsigned char id);
void __fastcall__ ball_draw(unsigned char id);
void __fastcall__ counter_digit(unsigned char column);
unsigned char old_x[2][BALL_COUNT], old_y[2][BALL_COUNT];
unsigned char ball_x[BALL_COUNT] = {12u, 64u, 116u};
unsigned char ball_y[BALL_COUNT] = {80u, 112u, 144u};
static unsigned char saved[2], previous_digits[2][5];
static signed char ball_dx[BALL_COUNT] = {1, -1, 1};
static signed char ball_dy[BALL_COUNT] = {1, 1, -1};
char frame_text[] = "00000";

static void introduction(void)
{
    unsigned char color;
    dhgr_clear(DHGR_BLACK);
    dhgr_puts("APPLE II DHGR",10,8);
    for (color=0; color<16u; ++color)
        dhgr_fill_rect(color*8u+6u,32,8,72,color);
    dhgr_set_color(DHGR_AQUA);
    gfx_circle(70,142,30);
    dhgr_puts("KEY: ANIMATION",10,178);
}

static void background(void)
{
    unsigned char x, y;
    dhgr_clear(DHGR_BLACK);
    dhgr_puts("DHGR STARTER",10,8);
    dhgr_puts("FRAME",10,24);
    dhgr_puts("ARROWS: DIRECTION",2,176);
    dhgr_puts("SPACE:PAUSE ESC",2,184);
    dhgr_fill_rect(4,60,132,1,DHGR_AQUA);
    dhgr_fill_rect(4,168,132,1,DHGR_AQUA);
    dhgr_fill_rect(4,60,1,109,DHGR_AQUA);
    dhgr_fill_rect(135,60,1,109,DHGR_AQUA);
    for (x=18u; x<135u; x+=14u)
        dhgr_fill_rect(x,61,1,107,DHGR_DARKBLUE);
    for (y=76u; y<168u; y+=16u)
        dhgr_fill_rect(5,y,130,1,DHGR_DARKBLUE);
}

static void collisions(void)
{
    static unsigned char i, j;
    static int x, y, vx, vy;
    static signed char direction;
    for (i=0u; i<BALL_COUNT; ++i) {
        for (j=i+1u; j<BALL_COUNT; ++j) {
            x=(int)ball_x[i]-(int)ball_x[j];
            y=(int)ball_y[i]-(int)ball_y[j];
            if (x < -6 || x > 6 || y < -6 || y > 6) continue;
            if (x*x+y*y > 36) continue;
            vx=(int)ball_dx[i]-(int)ball_dx[j];
            vy=(int)ball_dy[i]-(int)ball_dy[j];
            if (x*vx+y*vy >= 0) continue;
            direction=ball_dx[i]; ball_dx[i]=ball_dx[j]; ball_dx[j]=direction;
            direction=ball_dy[i]; ball_dy[i]=ball_dy[j]; ball_dy[j]=direction;
        }
    }
}

static void render(void)
{
    static unsigned char page, i, changed;
    page=dhgr_get_draw_page()-1u;
    changed=!saved[page];
    for (i=0u; i<BALL_COUNT; ++i)
        if (old_x[page][i] != ball_x[i] || old_y[page][i] != ball_y[i])
            changed=1u;
    if (changed) {
        /* Undo in reverse order, then save/draw in forward order so even
         * overlapping sprites restore both the grid and each other's pixels. */
        if (saved[page]) {
            i=BALL_COUNT;
            while (i-- > 0u)
                ball_restore(i);
        }
        for (i=0u; i<BALL_COUNT; ++i) {
            ball_draw(i);
        }
        saved[page]=1u;
    }
    /* Update only digits changed on this page, with pre-expanded DHGR bytes. */
    for (i=0u; i<5u; ++i) {
        if (previous_digits[page][i] != frame_text[i]) {
            counter_digit(i);
            previous_digits[page][i]=frame_text[i];
        }
    }
    i=5u;
    while (i-- > 0u) {
        if (++frame_text[i] <= '9') break;
        frame_text[i]='0';
    }
}
int main(void)
{
    static unsigned char i, key, paused=0u;
    if (!dhgr_init()) {
        a2_puts("DHGR REQUIRES IIE 128K OR IIC\r");
        return 0;
    }
    a2_frame_init();
    a2_frame_set_delay(70u);
    introduction();
    while (!apple2_iskeypressed()) {}
    key=apple2_readkey();
    if (key != KC_ESC) {
        /* Prepare a hidden page before replacing the introduction. */
        dhgr_draw_page(2);
        background();
        a2_frame_wait();
        dhgr_flip();
        background();
        for (;;) {
            key=apple2_readkey();
            if (key == KC_ESC) break;
            if (key == ' ') paused^=1u;
            for (i=0u; i<BALL_COUNT; ++i) {
                if (key == KC_LEFT) ball_dx[i]=-1;
                if (key == KC_RIGHT) ball_dx[i]=1;
                if (key == KC_UP) ball_dy[i]=-1;
                if (key == KC_DOWN) ball_dy[i]=1;
                if (!paused) {
                    if (ball_x[i] <= 6u) ball_dx[i]=1;
                    if (ball_x[i] >= 128u) ball_dx[i]=-1;
                    if (ball_y[i] <= 62u) ball_dy[i]=1;
                    if (ball_y[i] >= 160u) ball_dy[i]=-1;
                    ball_x[i]+=ball_dx[i]; ball_y[i]+=ball_dy[i];
                }
            }
            if (!paused) collisions();
            render();
            a2_frame_wait();
            dhgr_flip();
        }
    }
    dhgr_text_restore();
    a2_home();
    return 0;
}
