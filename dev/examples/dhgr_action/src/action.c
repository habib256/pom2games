/* VERHILLE Arnaud — GPL-3.0. DHGR ACTION: a small action demo on the DHGR
 * compositor (dev/lib/hgrc dhgr_spr_*) built with DHGR_SPR_DOUBLE: an arena
 * of tiles, five bouncing enemies, a ship and its shot, drawn on the hidden
 * page and shown at the VBL edge (//e $C019, //c mouse VBL interrupt).
 * ProDOS 8, Apple //e enhanced 128K or //c. README.md (French). */
#include "dhgr.h"
#include "prodos.h"
#include "apple2io.h"
#include "apple2game.h"
#include "apple2vbl.h"
#include "mouse.h"

#define ENEMIES 5u              /* slots 0..4, back to front */
#define SHOT 5u
#define PLAYER 6u
#define TOP 16u                 /* the arena: rows 16..191, 20 x 22 tiles of 7 x 8 */
#define XMIN 7u                 /* the floor inside the walls */
#define XEND 133u
#define YMIN 24u
#define YEND 184u
#define SHIP_X 66u
#define SHIP_Y 170u

#define C DHGR_CLEAR
#define W DHGR_WHITE
#define L DHGR_LIGHTBLUE
#define O DHGR_ORANGE
#define R DHGR_MAGENTA
#define G DHGR_GREEN
#define Y DHGR_YELLOW
#define P DHGR_PINK
#define V DHGR_VIOLET
#define A DHGR_AQUA
#define K DHGR_BLACK

static const unsigned char ship_d[7 * 7] = {
    C, C, C, W, C, C, C,
    C, C, W, W, W, C, C,
    C, C, W, L, W, C, C,
    C, W, W, W, W, W, C,
    W, W, O, W, O, W, W,
    W, C, C, O, C, C, W,
    C, C, C, R, C, C, C};
static const unsigned char bug_d[2][6 * 6] = {{
    C, G, C, C, G, C,
    C, C, G, G, C, C,
    C, G, Y, Y, G, C,
    G, G, K, G, K, G,
    C, G, G, G, G, C,
    G, C, C, C, C, G}, {
    G, C, C, C, C, G,
    C, C, G, G, C, C,
    C, G, Y, Y, G, C,
    G, G, G, K, G, K,
    C, G, G, G, G, C,
    C, G, C, C, G, C}};
static const unsigned char saucer_d[2][6 * 6] = {{
    C, C, A, A, C, C,
    C, A, W, W, A, C,
    P, P, P, P, P, P,
    V, Y, V, V, Y, V,
    C, P, P, P, P, C,
    C, C, R, R, C, C}, {
    C, C, A, A, C, C,
    C, A, W, W, A, C,
    P, P, P, P, P, P,
    V, V, Y, V, V, Y,
    C, P, P, P, P, C,
    C, R, C, C, R, C}};
static const unsigned char shot_r[] = {0, 0, 1, 4, DHGR_YELLOW};
static const dhgr_shape_t ship = {DHGR_SHAPE_CHUNKY, 7, 7, 0, ship_d};
static const dhgr_shape_t shot = {DHGR_SHAPE_RECTS, 1, 4, 1, shot_r};
static const dhgr_shape_t enemy_s[4] = {
    {DHGR_SHAPE_CHUNKY, 6, 6, 0, bug_d[0]}, {DHGR_SHAPE_CHUNKY, 6, 6, 0, bug_d[1]},
    {DHGR_SHAPE_CHUNKY, 6, 6, 0, saucer_d[0]}, {DHGR_SHAPE_CHUNKY, 6, 6, 0, saucer_d[1]}};

/* Tiles: 7 x 8. */
#define N2 DHGR_NIB(DHGR_DARKBLUE)
#define N5 DHGR_NIB(DHGR_GRAY1)
#define NA DHGR_NIB(DHGR_GRAY2)
#define N0 DHGR_NIB(DHGR_BLACK)
#define N6 DHGR_NIB(DHGR_BLUE)
/* The floor: rectangles (filled 5 cycles a byte); the walls: TILE nibbles. */
static const unsigned char floor_a_r[] = {0, 0, 7, 8, DHGR_DARKBLUE, 3, 3, 1, 2, DHGR_BLUE};
static const unsigned char floor_b_r[] = {0, 0, 7, 8, DHGR_BLACK};
static const unsigned char wall_d[56] = {
    NA, NA, NA, NA, NA, NA, N5,  NA, N5, N5, N5, N5, N5, N0,
    NA, N5, N5, N5, N5, N5, N0,  NA, N5, N5, N5, N5, N5, N0,
    NA, N5, N5, N5, N5, N5, N0,  NA, N5, N5, N5, N5, N5, N0,
    NA, N5, N5, N5, N5, N5, N0,  N5, N0, N0, N0, N0, N0, N0};
static const dhgr_shape_t floor_a = {DHGR_SHAPE_RECTS, 7, 8, 2, floor_a_r};
static const dhgr_shape_t floor_b = {DHGR_SHAPE_RECTS, 7, 8, 1, floor_b_r};
static const dhgr_shape_t wall = {DHGR_SHAPE_TILE, 7, 8, 0, wall_d};
static const dhgr_shape_t *const tset[3] = {&floor_a, &floor_b, &wall};
static unsigned char map[20u * 22u];

/* The enemies' start: tests/test_dhgr_action.py's model plays the same. */
static const unsigned char ex0[ENEMIES] = {20, 50, 84, 110, 35};
static const unsigned char ey0[ENEMIES] = {30, 64, 40, 92, 120};
static const signed char edx0[ENEMIES] = {1, -1, 1, -1, 1};
static const signed char edy0[ENEMIES] = {1, 1, -1, 1, -1};

static unsigned char canvas[255];
static unsigned char ex[ENEMIES], ey[ENEMIES];
static signed char edx[ENEMIES], edy[ENEMIES];
static unsigned char px, py, sx, sy, shot_on, invuln, lives, seed, hud;
static unsigned char dir, stick, debug, dframes, vbl_mark, claimed;
static unsigned score, budget;
unsigned frame;                 /* frames shown (the test reads it) */
static char line[28], shown1[28], shown2[28];   /* (BSS: 0, drawn as blank) */

void frame_end(void);           /* hooks.s: the test's probe, an RTS */

void game_shutdown(void)
{
    a2_vbl_close();
    dhgr_text_restore();
    if (claimed) { prodos_video_release(); claimed = 0u; }
}

static unsigned char touch(unsigned char x0, unsigned char y0, unsigned char w0, unsigned char h0,
                           unsigned char x1, unsigned char y1, unsigned char w1, unsigned char h1)
{
    return x0 < x1 + w1 && x1 < x0 + w0 && y0 < y1 + h1 && y1 < y0 + h0;
}

static char *put_u(char *p, unsigned v, unsigned char digits)
{
    p += digits;
    do { *--p = (char)('0' + v % 10u); v /= 10u; } while (--digits);
    return p;
}

static void put_s(const char *s, unsigned char at)
{
    while (*s) line[at++] = *s++;
}

/* The score line (rows 0..15, outside the compositor's area) on the draw
 * page: only the characters that page does not show yet (a 5 x 5 character
 * costs ~1,800 cycles). */
static void draw_hud(void)
{
    static unsigned char page, i;
    static char *shown;
    page = dhgr_get_draw_page();
    if (!(hud & page)) return;
    hud &= (unsigned char)~page;
    for (i = 0; i < 28u; ++i) line[i] = ' ';
    put_s("SCORE", 0);
    put_u(line + 6, score, 5u);
    put_s("VIES", 13);
    line[18] = (char)('0' + lives);
    if (debug) {                        /* cycles a frame, 32-frame average */
        line[21] = 'C';
        if (budget) put_u(line + 23, budget, 5u); else put_s("-----", 23);
    } else {
        put_s(stick ? "MANETTE" : "CLAVIER", 21);
    }
    shown = page == 1u ? shown1 : shown2;
    dhgr_small_y = 5u;
    for (i = 0; i < 28u; ++i)           /* 28 characters of 5 pixels: 140 */
        if (shown[i] != line[i]) {
            shown[i] = line[i];
            dhgr_small_x = (unsigned char)(i * 5u);
            dhgr_small_char((unsigned char)line[i]);
        }
}

static void new_enemy(unsigned char i)
{
    seed = (unsigned char)(seed * 5u + 17u);
    ex[i] = (unsigned char)(XMIN + seed % (XEND - XMIN - 6u));
    ey[i] = YMIN;
}

static void move_enemies(void)
{
    static unsigned char i, n;
    for (i = 0; i < ENEMIES; ++i) {
        n = (unsigned char)(ex[i] + edx[i]);
        if (n < XMIN || n > XEND - 6u) { edx[i] = (signed char)-edx[i]; n = (unsigned char)(ex[i] + edx[i]); }
        ex[i] = n;
        n = (unsigned char)(ey[i] + edy[i]);
        if (n < YMIN || n > YEND - 6u) { edy[i] = (signed char)-edy[i]; n = (unsigned char)(ey[i] + edy[i]); }
        ey[i] = n;
    }
}

static void input(void)
{
    static unsigned char key, fire, joy;
    fire = 0;
    key = apple2_readkey();
    if (key >= 'a' && key <= 'z') key -= 32u;
    switch (key) {
    case 0: break;
    case KC_ESC: dir = 0xFF; return;
    case 'F': debug ^= 1u; budget = 0; dframes = 0; vbl_mark = a2_vbl_count; hud = 3u; break;
    case 'S': stick ^= 1u; hud = 3u; break;
    case ' ': fire = 1u; break;
    case KC_LEFT: case 'J': dir = 1u; break;
    case KC_RIGHT: case 'L': dir = 2u; break;
    case KC_UP: case 'I': dir = 3u; break;
    case KC_DOWN: case 'K': dir = 4u; break;
    }
    if (stick) {
        joy = a2_read_stick();
        dir = joy == A2_JOY_LEFT ? 1u : joy == A2_JOY_RIGHT ? 2u : joy == A2_JOY_UP ? 3u :
              joy == A2_JOY_DOWN ? 4u : 0u;
        if (a2_button(0)) fire = 1u;
    } else if (!(*(volatile unsigned char *)0xC010 & 0x80u)) {
        dir = 0;                /* no key held any more */
    }
    switch (dir) {
    case 1: if (px > XMIN + 1u) px -= 2u; break;
    case 2: if (px < XEND - 9u) px += 2u; break;
    case 3: if (py > YMIN + 1u) py -= 2u; break;
    case 4: if (py < YEND - 9u) py += 2u; break;
    }
    if (fire && !shot_on) {
        shot_on = 1u;
        sx = (unsigned char)(px + 3u);
        sy = (unsigned char)(py - 4u);
    }
}

static void play(void)
{
    static unsigned char i;
    if (shot_on) {
        if (sy < YMIN + 4u) shot_on = 0;
        else sy -= 4u;
    }
    move_enemies();
    for (i = 0; i < ENEMIES; ++i) {
        if (shot_on && touch(sx, sy, 1u, 4u, ex[i], ey[i], 6u, 6u)) {
            shot_on = 0;
            new_enemy(i);
            score += 10u;
            hud = 3u;
            a2_tone(10u, 0x30u);
        }
        if (!invuln && touch(px, py, 7u, 7u, ex[i], ey[i], 6u, 6u)) {
            invuln = 60u;
            a2_tone(4u, 0xFFu);
            if (!--lives) { lives = 3u; score = 0; }
            hud = 3u;
        }
    }
    if (invuln) --invuln;
    for (i = 0; i < ENEMIES; ++i)
        dhgr_spr_set(i, &enemy_s[(i & 1u) * 2u + ((frame >> 3) & 1u)], ex[i], ey[i],
                     edx[i] < 0 ? DHGR_SPR_MIRROR : 0u);
    dhgr_spr_set(SHOT, shot_on ? &shot : 0, sx, sy, 0u);
    dhgr_spr_set(PLAYER, &ship, px, py, invuln & 4u ? DHGR_SPR_HIDDEN : 0u);
}

int main(void)
{
    static unsigned char i, col, row;
    static unsigned long cycles;
    if (prodos_video_claim(PD_VIDEO_DISCARD_RAM) != PD_VIDEO_OK) {
        a2_puts("DHGR ACTION: AUX MEMORY BUSY.\r");
        apple2_getkey();
        return 1;
    }
    claimed = 1u;
    if (!dhgr_init()) {
        a2_puts("DHGR ACTION NEEDS A //E 128K OR A //C.\r");
        apple2_getkey();
        return 1;
    }
    for (i = 1; i <= 2u; ++i) {             /* both pages black */
        dhgr_draw_page(i);
        for (row = 0; row < 192u; row += 8u) dhgr_clear_rows(row, 8u, DHGR_BLACK);
    }
    /* The clock: a mouse's VBL interrupt (//c, //e with an AppleMouse)
     * counts every refresh; else the //e polls $C019 (counted only while
     * dhgr_spr_present waits: no cycle figure on the F key). */
    if (!mouse_init() || !a2_vbl_irq_init()) a2_vbl_init();
    for (row = 0; row < 22u; ++row)
        for (col = 0; col < 20u; ++col)
            map[row * 20u + col] = row == 0 || row == 21u || col == 0 || col == 19u ? 2u :
                                   (unsigned char)((row + col) & 1u);
    dhgr_spr_init(canvas, sizeof canvas, 4u);
    dhgr_spr_area(0, TOP, 139u, 191u);
    dhgr_spr_tiles(0, TOP, 8u, map, 20u, tset);
    dhgr_spr_invalidate(0, TOP, 140u, 192u - TOP);
    for (i = 0; i < ENEMIES; ++i) {
        ex[i] = ex0[i]; ey[i] = ey0[i]; edx[i] = edx0[i]; edy[i] = edy0[i];
    }
    px = SHIP_X; py = SHIP_Y; lives = 3u; seed = 1u; hud = 3u;
    dhgr_draw_page(2);                      /* shown: page 1; drawn: page 2 */
    for (;;) {
        input();
        if (dir == 0xFFu) return 0;
        play();
        draw_hud();
        dhgr_spr_update();
        dhgr_spr_present();
        ++frame;
        frame_end();
        if (debug && ++dframes == 32u) {   /* refreshes over 32 frames */
            dframes = 0;
            cycles = ((unsigned long)(unsigned char)(a2_vbl_count - vbl_mark) * 17030u) >> 5;
            budget = a2_vbl_mode != A2_VBL_IRQ ? 0u : cycles > 65535u ? 65535u : (unsigned)cycles;
            vbl_mark = a2_vbl_count;
            hud = 3u;
        }
    }
}
