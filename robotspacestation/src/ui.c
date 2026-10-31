/* Robot Space Station — pointer, input, messages, buttons, technician. */
#include <string.h>
#include "dhgr.h"
#include "apple2io.h"
#include "mouse.h"
#include "ui.h"
#include "zone.h"
#include "apple2game.h"

unsigned char screen, running;
unsigned char cur_drone;
unsigned char px = 70u, py = 80u;
unsigned char pressed, key, moved;
/* Tests (a2shot pokes, main loop idle): a click at test_x, test_y. */
unsigned char test_click, test_x, test_y;
unsigned char act_x, act_y;

static unsigned char shown, mouse_lx, mouse_ly, button_old, act_on, act_bx, act_by;
/* In the room (ui_room): the pointer's rows in the room are the
 * compositor's overlay, composed with the sprites in one pass; its rows
 * above or below the room (if any) are drawn by src/pointer.s. */
static unsigned char ov_mode, ptr_h_shown;
static unsigned char latched, latch_x, latch_y;
static unsigned char vbl_gate, vbl_armed, vbl_seen;   /* //e: one mouse read a frame */
static unsigned char act_bg[4u * ACT_H];

/* The pointer: a white arrow ORed into the 4 bytes x 6 rows under it,
 * saved first and written back by hide() (src/pointer.s), or in the room
 * the compositor's overlay (dhgr.h dhgr_spr_overlay). arrow_bits[p][r] holds row r's
 * bits for a pointer starting p mono pixels into its first byte (7 bits a
 * byte, the leftmost in bit 0), built once by pointer_init(). */
static const unsigned char arrow_w[6] = {1, 2, 3, 4, 2, 1};
#pragma bss-name (push, "LOW8BSS")      /* ($0800-$0FFF: not zeroed) */
static unsigned char arrow_bits[7][6][4];
/* With a part or a wire in hand (board_ui.c held_kind / held_part /
 * held_src): the arrow and a block of 2 x 3 pixels at its lower right. */
static unsigned char carry_bits[7][6][4];
#pragma bss-name (pop)
extern unsigned char held_kind, held_part, held_src;
/* src/pointer.s */
extern unsigned char ptr_bx, ptr_y, ptr_h;
extern const unsigned char *ptr_bits;
void pointer_draw(void);
void pointer_restore(void);

static void pointer_init(void)
{
    static unsigned char p, r, j, b, n;
    memset(arrow_bits, 0, sizeof arrow_bits);
    memset(carry_bits, 0, sizeof carry_bits);
    for (p = 0u; p < 7u; ++p)
        for (r = 0u; r < 6u; ++r)
            for (j = 0u; j < 5u; ++j) {
                /* Pixel j is lit if j < width, or the tail pixel 2 of row 5;
                 * the carried block: pixels 3-4 of rows 3-5. */
                b = j < arrow_w[r] || (r == 5u && j == 2u);
                if (!b && !(r >= 3u && j >= 3u)) continue;
                for (n = p + (j << 2); n < p + (j << 2) + 4u; ++n) {
                    if (b) arrow_bits[p][r][n / 7u] |= 1u << (n % 7u);
                    carry_bits[p][r][n / 7u] |= 1u << (n % 7u);
                }
            }
}

/* At px, py (shown). In the room: the rows inside it in one pass with
 * the room's update, the others (ptr_y, ptr_h: none, above or below)
 * restored and drawn again by src/pointer.s. */
static void cursor_show(void)
{
    static unsigned mono;
    static unsigned char h, y1, in0, in1;
    static const unsigned char *bits;
    if (ov_mode && shown && ptr_h_shown) pointer_restore();    /* (where it was) */
    mono = (unsigned)px << 2;
    ptr_bx = (unsigned char)(mono / 7u);
    h = py > 186u ? 192u - py : 6u;
    bits = (held_kind || (held_part & held_src) != 0xFFu ? carry_bits : arrow_bits)
           [(unsigned char)(mono - ptr_bx * 7u)][0];
    ptr_y = py;
    ptr_h = h;
    ptr_bits = bits;
    if (ov_mode) {
        y1 = py + h;
        in0 = py < ROOM_Y ? ROOM_Y : py;
        in1 = y1 > ROOM_Y + ROOM_H ? ROOM_Y + ROOM_H : y1;
        if (in0 < in1) {
            dhgr_spr_overlay(ptr_bx, in0, 4u, in1 - in0, bits + (unsigned char)((in0 - py) << 2), 0);
            ptr_h = in0 - py;                   /* the rows above the room */
            if (!ptr_h && y1 > in1) {           /* or below it */
                ptr_y = in1;
                ptr_h = y1 - in1;
                ptr_bits = bits + (unsigned char)((in1 - py) << 2);
            }
        } else {
            dhgr_spr_overlay(0u, 0u, 0u, 0u, bits, 0);
        }
        dhgr_spr_update();
    }
    ptr_h_shown = ptr_h;
    if (ptr_h) pointer_draw();
    shown = 1u;
}

/* In the room only the rows out of it go (the title or the buttons may be
 * drawn there): the room changes under the overlay. */
void hide(void)
{
    if (shown && ptr_h_shown) pointer_restore();
    shown = 0u;
}
void show(void) { if (!shown) cursor_show(); }

void ui_room(void)
{
    ov_mode = 1u;
}

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
    shown = ov_mode = 0u;                   /* (the pointer goes with the screen) */
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
        if (!ov_mode) hide();               /* (the overlay moves in one pass) */
        px = nx; py = ny;
        cursor_show();
    }
}

void __fastcall__ message(const char *s)
{
    dhgr_fill_rect(0, MSG_Y - 1u, 140, 7, DHGR_BLACK);
    dhgr_puts_small(s, 0, MSG_Y);
    hover_sync = 1u;
}

void __fastcall__ msg(unsigned char id)
{
    text_open(id);
    text_line();
    message(text_buf);
}

unsigned char page_x, page_y;

void __fastcall__ text_page(unsigned char id)
{
    static unsigned char more;
    text_open(id);
    do {
        more = text_line();
        dhgr_puts_small(text_buf, page_x, page_y);
        page_y += 9u;
    } while (more);
}

void __fastcall__ text_at(unsigned char id, unsigned char x, unsigned char y)
{
    text_open(id);
    text_line();
    dhgr_puts_small(text_buf, x, y);
}

/* -- buttons -------------------------------------------------------------- */

static const char *const *btn_label;
const unsigned char *btn_tip;
static unsigned char btn_n, btn_x[6], btn_w[6];

void __fastcall__ buttons_set(const char *const *labels, const unsigned char *tips, unsigned char n)
{
    static unsigned char i, x;
    static const char *s;
    btn_label = labels;
    btn_tip = tips;
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

/* On the board screen only (in the room he is a compositor sprite). */
void actor_show(void)
{
    static unsigned char x, y;
    if (act_on || screen != S_DRONE) return;
    x = act_x; y = act_y;
    act_bx = (unsigned char)(((unsigned)x << 2) / 7u);
    act_by = y;
    dhgr_read_block(act_bx, y, 4, ACT_H, act_bg, 4);
    tech_paint(x, y);                                     /* src/sprites.c */
    act_on = 1u;
}

void begin_draw(void)
{
    hide();
    actor_hide();
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
