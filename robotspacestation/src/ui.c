/* Robot Space Station — pointer, input, messages, buttons, technician. */
#include "dhgr.h"
#include "apple2io.h"
#include "mouse.h"
#include "ui.h"
#include "apple2game.h"

unsigned char screen, running;
unsigned char cur_drone;
unsigned char px = 70u, py = 80u;
unsigned char pressed, key, moved;
/* Tests (a2shot pokes, main loop idle): a click at test_x, test_y. */
unsigned char test_click, test_x, test_y;
unsigned char act_x, act_y;

static unsigned char shown, mouse_lx, mouse_ly, button_old, act_on, act_bx, act_by;
static unsigned char latched, latch_x, latch_y;
static unsigned char vbl_gate, vbl_armed, vbl_seen;   /* //e: one mouse read a frame */
static unsigned char act_bg[4u * ACT_H];

/* The pointer: a white arrow ORed into the 4 bytes x 6 rows under it,
 * saved first and written back by hide(). arrow_bits[p][r] holds row r's
 * bits for a pointer starting p mono pixels into its first byte (7 bits a
 * byte, the leftmost in bit 0), built once by pointer_init(). */
static const unsigned char arrow_w[6] = {1, 2, 3, 4, 2, 1};
static unsigned char arrow_bits[7][6][4];
/* src/pointer.s */
extern unsigned char ptr_bx, ptr_y, ptr_h;
extern const unsigned char *ptr_bits;
void pointer_draw(void);
void pointer_restore(void);

static void pointer_init(void)
{
    static unsigned char p, r, j, b, n;
    for (p = 0u; p < 7u; ++p)
        for (r = 0u; r < 6u; ++r)
            for (j = 0u; j < 4u; ++j) {
                /* Pixel j is lit if j < width, or the tail pixel 2 of row 5. */
                if (!(j < arrow_w[r] || (r == 5u && j == 2u))) continue;
                for (b = 0u; b < 4u; ++b) {
                    n = p + (j << 2) + b;          /* mono pixel in the window */
                    arrow_bits[p][r][n / 7u] |= 1u << (n % 7u);
                }
            }
}

static void cursor_show(void)
{
    static unsigned mono;
    mono = (unsigned)px << 2;
    ptr_bx = (unsigned char)(mono / 7u);
    ptr_y = py;
    ptr_h = py > 186u ? 192u - py : 6u;
    ptr_bits = arrow_bits[(unsigned char)(mono - ptr_bx * 7u)][0];
    pointer_draw();
    shown = 1u;
}

static void cursor_hide(void)
{
    pointer_restore();
    shown = 0u;
}

void hide(void) { if (shown) cursor_hide(); }
void show(void) { if (!shown) cursor_show(); }

/* A press between two polls of the main loop would be lost: the drawings
 * that take several frames call this every few steps. Not more often: two
 * READMOUSE calls in a row lose part of the motion. */
void ui_latch(void)
{
    static unsigned char b;
    if (!mouse_slot || latched) return;
    if (vbl_gate) {
        /* $C019 bit 7 is clear during the vertical blank: read again only
         * after the beam left the blank, then entered the next one. */
        if (*(volatile unsigned char *)0xC019 & 0x80u) vbl_armed = 1u;
        else if (vbl_armed) vbl_seen = 1u;
        if (!vbl_seen) return;
        vbl_seen = vbl_armed = 0u;
    }
    mouse_poll();
    b = mouse_buttons & 0x80u;
    if (b && !button_old) {
        latched = 1u;
        latch_x = mouse_x;
        latch_y = mouse_y;
    }
    button_old = b;
}

void screen_clear(void)
{
    static unsigned char y;
    for (y = 0u; y < 192u; y += 24u) {
        ui_latch();
        dhgr_clear_rows(y, 24, DHGR_BLACK);
    }
}

void ui_poll(void)
{
    static unsigned char nx, ny, b;
    static unsigned char ready;
    if (!ready) {
        pointer_init();
        vbl_gate = *(unsigned char *)0xFBC0 == 0xE0u;     /* enhanced //e */
        ready = 1u;
    }
    nx = px; ny = py;
    pressed = 0u;
    if (test_click) {
        test_click = 0u;
        pressed = 1u;
        nx = test_x;
        ny = test_y;
    } else if (latched) {
        /* The click happened during a drawing, where the mouse was then. */
        latched = 0u;
        pressed = 1u;
        nx = mouse_lx = latch_x;
        ny = mouse_ly = latch_y;
    } else if (mouse_slot) {
        mouse_poll();
        vbl_seen = vbl_armed = 0u;
        if (mouse_x != mouse_lx || mouse_y != mouse_ly) {
            nx = mouse_lx = mouse_x;
            ny = mouse_ly = mouse_y;
        }
        b = mouse_buttons & 0x80u;
        if (b && !button_old) pressed = 1u;
        button_old = b;
    }
    key = apple2_readkey();
    if (key >= 'a' && key <= 'z') key -= 32;
    switch (key) {
    case KC_LEFT: nx = nx > 2u ? nx - 2u : 0u; break;
    case KC_RIGHT: nx = nx < 137u ? nx + 2u : 139u; break;
    case KC_UP: ny = ny > 2u ? ny - 2u : 0u; break;
    case KC_DOWN: ny = ny < 189u ? ny + 2u : 191u; break;
    case ' ': case KC_RET: pressed = 1u; break;
    }
    moved = nx != px || ny != py;
    if (moved) {
        hide();
        px = nx; py = ny;
        show();
    }
}

void __fastcall__ message(const char *s)
{
    dhgr_fill_rect(0, MSG_Y - 1u, 140, 7, DHGR_BLACK);
    dhgr_puts_small(s, 0, MSG_Y);
}

/* -- buttons -------------------------------------------------------------- */

static const char *const *btn_label;
static unsigned char btn_n, btn_x[6], btn_w[6];

void __fastcall__ buttons_set(const char *const *labels, unsigned char n)
{
    static unsigned char i, x;
    static const char *s;
    btn_label = labels;
    btn_n = n;
    for (i = 0u, x = 0u; i < n; ++i) {
        btn_x[i] = x;
        for (s = labels[i]; *s; ++s) x += 5u;
        btn_w[i] = x - btn_x[i];
        x += 3u;
    }
    buttons_draw();
}

void buttons_draw(void)
{
    static unsigned char i;
    dhgr_fill_rect(0, BTN_Y - 1u, 140, 9, DHGR_BLACK);
    for (i = 0u; i < btn_n; ++i) {
        dhgr_fill_rect(btn_x[i], BTN_Y + 6u, btn_w[i], 1, DHGR_AQUA);
        dhgr_puts_small(i == 0u && running ? (const char *)"PAUSE" : btn_label[i], btn_x[i], BTN_Y);
    }
}

unsigned char __fastcall__ button_at(unsigned char x)
{
    static unsigned char i;
    for (i = 0u; i < btn_n; ++i)
        if (x >= btn_x[i] && x < btn_x[i] + btn_w[i]) return i;
    return 0xFFu;
}

/* -- technician -------------------------------------------------------------- */

void actor_show(void)
{
    static unsigned char x, y;
    if (act_on) return;
    x = act_x; y = act_y;
    act_bx = (unsigned char)(((unsigned)x << 2) / 7u);
    act_by = y;
    dhgr_read_block(act_bx, y, 4, ACT_H, act_bg, 4);
    dhgr_fill_rect(x + 1u, y, 3, 2, DHGR_WHITE);          /* helmet */
    dhgr_fill_rect(x + 1u, y + 2u, 3, 1, DHGR_AQUA);      /* visor */
    dhgr_fill_rect(x, y + 3u, 5, 4, DHGR_ORANGE);         /* suit */
    dhgr_fill_rect(x + 1u, y + 7u, 1, 2, DHGR_GRAY2);     /* legs */
    dhgr_fill_rect(x + 3u, y + 7u, 1, 2, DHGR_GRAY2);
    act_on = 1u;
}

void begin_draw(void)
{
    hide();
    actor_hide();
}

void begin_draw_box(unsigned char x0, unsigned char y0, unsigned char x1, unsigned char y1)
{
    /* The pointer is 4 x 6, the technician ACT_W x ACT_H. */
    if (px <= x1 && px + 4u > x0 && py <= y1 && py + 6u > y0) hide();
    if (act_x <= x1 && act_x + ACT_W > x0 && act_y <= y1 && act_y + ACT_H > y0) actor_hide();
}

void actor_hide(void)
{
    if (!act_on) return;
    dhgr_write_block(act_bx, act_by, 4, ACT_H, act_bg, 4);
    act_on = 0u;
}

/* -- sound ------------------------------------------------------------------ */

unsigned char sound_on = 1u, sfx_count;
/* a2_tone(flips, period): a few milliseconds each (the drone runs on); the
 * win's three notes go up, after the last one the next. */
static const unsigned char sfx_flips[] = { 0x08u, 0x18u, 0x0Cu, 0x20u, 0x40u, 0x40u };
static const unsigned char sfx_period[] = { 0xE0u, 0x30u, 0x60u, 0x1Cu, 0x48u, 0x60u };

void __fastcall__ sfx(unsigned char n)
{
    ++sfx_count;
    if (!sound_on) return;
    a2_tone(sfx_flips[n], sfx_period[n]);
    if (n == SFX_WIN) {
        a2_tone(0x50u, 0x4Cu);
        a2_tone(0x80u, 0x3Cu);
    }
}
