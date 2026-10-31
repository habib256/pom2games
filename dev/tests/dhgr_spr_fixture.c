/* DHGR compositor fixture (test_dhgr_spr.py): plays the generated op list in
 * dhgr_spr_ops.inc; every update sits between begin() and end() and waits
 * for a key, so the host can watch its screen stores and dump both banks.
 * FIXTURE_DOUBLE (DHGR_SPR_DOUBLE): draws on page 2 first, each update is
 * followed by dhgr_spr_present() inside the window (a2_vbl_init first).
 * FIXTURE_VBL (DHGR_SPR_VBL): a2_vbl_init first. */
#include "dhgr.h"
#include "apple2io.h"
#if defined(FIXTURE_DOUBLE) || defined(FIXTURE_VBL)
#include "apple2vbl.h"
#endif
#include "dhgr_spr_ops.inc"     /* CANVAS_BYTES, CANVAS_GROUPS, shapes, ops, tiles */

void begin(void);
void end(void);
void irq_on(void);
static unsigned char canvas[CANVAS_BYTES];
#ifdef FIXTURE_DOUBLE
static unsigned char under[254 + 2 * 127];   /* page 2 from under + 254 */
#else
static unsigned char under[2 * 127];
#endif
static unsigned char cell_x, cell_y, cell_h;

/* A cell: its colour, and a detail colour inside if the high nibble is set. */
static void paint(unsigned char col, unsigned char row)
{
    static unsigned char t, x, y;
    t = tiles[row * 20u + col];
    x = cell_x + col * 7u;
    y = cell_y + row * cell_h;
    dhgr_cv_rect(x, y, 7u, cell_h, t & 15u);
    if (t >> 4) dhgr_cv_rect(x + 1u, y + 2u, 5u, cell_h - 4u, t >> 4);
}

int main(void)
{
    static const unsigned char *p;
    static const dhgr_shape_t *s;
    p = ops;
    if (!dhgr_init()) return 1;
    dhgr_draw_page(2);
    dhgr_clear(10);
    dhgr_draw_page(1);
    dhgr_clear(5);
    if (dhgr_spr_init(canvas, 0u, 1u) || dhgr_spr_init(canvas, 70u, 21u)) return 2;
    if (!dhgr_spr_init(canvas, CANVAS_BYTES, CANVAS_GROUPS)) return 3;
    if (dhgr_spr_set(DHGR_SPR_MAX, shapes, 0u, 0u, 0u)) return 4;
#if defined(FIXTURE_DOUBLE) || defined(FIXTURE_VBL)
    a2_vbl_init();
#endif
#ifdef FIXTURE_DOUBLE
    dhgr_draw_page(2);
#endif
    irq_on();
    for (;;) {
        switch (*p++) {
        case 0: return 0;
        case 1:
            s = p[1] == 255u ? 0 : shapes + p[1];
            dhgr_spr_set(p[0], s, p[2], p[3], p[4]);
            p += 5;
            break;
        case 2: dhgr_spr_palette(p[0], p + 1); p += 5; break;
        case 3: dhgr_spr_invalidate(p[0], p[1], p[2], p[3]); p += 4; break;
        case 4: dhgr_spr_overlay(p[0], p[1], p[2], p[3], ovbits, under); p += 4; break;
        case 5:
            begin();
            dhgr_spr_update();
#ifdef FIXTURE_DOUBLE
            dhgr_spr_present();
#endif
            end();
            apple2_getkey();
            break;
        case 6: dhgr_spr_area(p[0], p[1], p[2], p[3]); p += 4; break;
        case 7: dhgr_spr_solid(*p++); break;
        case 8:
            cell_x = p[0]; cell_y = p[1]; cell_h = p[2];
            dhgr_spr_cells(p[0], p[1], p[2], paint);
            p += 3;
            break;
        case 9: tiles[p[1] * 20u + p[0]] = p[2]; p += 3; break;
        case 10: dhgr_spr_tiles(p[0], p[1], p[2], tmap, 20u, tset); p += 3; break;
        case 11: tset[p[0]] = shapes + p[1]; p += 2; break;
        case 12: tmap[p[1] * 20u + p[0]] = p[2]; p += 3; break;
        case 13:
            begin();
            dhgr_cursor(p[0], p[1], p[2], p[3], ovbits, under);
            end();
            apple2_getkey();
            p += 4;
            break;
        }
    }
}
