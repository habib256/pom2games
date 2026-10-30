/* Robot Space Station — the help and records pages (title: HELP, H,
 * RECORDS); their texts are in the bank (tools/gen_text.py). */
#include "dhgr.h"
#include "sim.h"
#include "zone.h"
#include "title.h"
#include "ui.h"
#include "board_ui.h"

/* Electronics 3/6 (AND, OR) and 4/6 (XOR, NOT): each gate's symbol
 * beside its truth table, at x 100 and these rows. */
static const unsigned char symbol_y[4] = { 78, 132, 51, 96 };

/* Page 2, the rooms: a sample of each tile (zone.c's colours), its rule. */
/* x, y, width, height, colour */
static const unsigned char swatch[][5] = {
    {4, 15, 7, 8, DHGR_GRAY1},                                  /* wall */
    {4, 29, 7, 1, DHGR_DARKBLUE}, {4, 33, 7, 1, DHGR_DARKBLUE},  /* grate */
    {4, 41, 7, 8, DHGR_GRAY1}, {6, 41, 3, 8, DHGR_BLACK},        /* tunnel */
    {4, 54, 7, 8, DHGR_ORANGE}, {5, 69, 5, 4, DHGR_BROWN},       /* door, plate */
    {4, 80, 7, 8, DHGR_VIOLET}, {12, 82, 3, 4, DHGR_MAGENTA},    /* the second */
    {4, 93, 7, 8, DHGR_DARKGREEN}, {7, 95, 1, 4, DHGR_GREEN},    /* charger */
    {4, 106, 7, 8, DHGR_YELLOW}, {5, 109, 5, 2, DHGR_ORANGE},    /* cell */
    {4, 119, 7, 8, DHGR_BROWN},                                  /* crate */
    {4, 131, 10, 12, DHGR_LIGHTBLUE}, {5, 132, 8, 10, DHGR_BLACK},   /* drones */
    {86, 131, 10, 12, DHGR_AQUA}, {87, 132, 8, 10, DHGR_BLACK},
};

static void legend_draw(void)
{
    static unsigned char i;
    static const unsigned char *r;
    text_at(T_H_ROOMS, 45, 4);
    for (i = 0u; i < 10u; ++i)
        text_at(T_LEGEND + i, 16, 17u + i * 13u);
    for (i = 0u; i < sizeof swatch / sizeof swatch[0]; ++i) {
        r = swatch[i];
        dhgr_fill_rect(r[0], r[1], r[2], r[3], r[4]);
    }
}

void __fastcall__ help_draw(unsigned char page)
{
    static unsigned char i, y, n;
    static char num[3];
    if (page == LEGEND_PAGE) { legend_draw(); return; }
    if (page < TEXT_PAGES) {
        page_x = 0u; page_y = 4u;
        text_page(T_HELP + page);
        if (page == 3u || page == 4u) {
            sym_x = 100u;
            for (i = page * 2u - 6u; i < page * 2u - 4u; ++i) {
                sym_y = symbol_y[i];
                draw_symbol(i);
            }
        }
        return;
    }
    text_at(T_H_RECORDS, 0, 4);
    for (i = title_page * 14u; i < mission_count() && i < title_page * 14u + 14u; ++i) {
        y = 18u + (i - title_page * 14u) * 9u;    /* the title's page */
        n = persist.best[i];            /* gates + 1, 0: never won */
        if (i < persist.reached) text_at(T_NAME + i, 4, y); else dhgr_puts_small("-", 4, y);
        if (!n--) continue;
        if (n > 99u) n = 99u;
        num[0] = n >= 10u ? '0' + n / 10u : ' ';
        num[1] = '0' + n % 10u;
        num[2] = 0;
        dhgr_puts_small(num, 84, y);
        dhgr_puts_small(n == 1u ? (const char *)"GATE" : (const char *)"GATES", 98, y);
    }
}
