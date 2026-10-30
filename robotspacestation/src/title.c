/* Robot Space Station — the title screen: the station among the stars and
 * the missions, won, next or still locked. */
#include "dhgr.h"
#include "sim.h"
#include "ui.h"
#include "zone.h"
#include "title.h"

#define LIST_Y 92u              /* mission m on row LIST_Y + 9 * (m % LIST_N), */
#define LIST_N 7u               /* column 72 * (m / LIST_N): two columns */
#define LIST_DX 72u

static void stars(void)
{
    static unsigned char i, x, y;
    static unsigned seed;
    seed = 0x2A5Bu;
    for (i = 0u; i < 60u; ++i) {
        seed = seed * 109u + 89u;                  /* the same sky every time */
        x = (unsigned char)(seed >> 8) % 140u;
        y = (unsigned char)seed % 80u;
        dhgr_plot_color(x, y, i & 3u ? DHGR_GRAY2 : DHGR_WHITE);
    }
}

static void station(void)
{
    static unsigned char i;
    dhgr_fill_rect(12, 44, 108 + 8, 2, DHGR_GRAY1);         /* truss */
    for (i = 0u; i < 2u; ++i) {                              /* solar wings */
        dhgr_fill_rect(i ? 112u : 6u, 34, 18, 22, DHGR_DARKBLUE);
        dhgr_fill_rect(i ? 112u : 6u, 44, 18, 2, DHGR_BLUE);
    }
    dhgr_fill_rect(56, 36, 28, 18, DHGR_GRAY2);              /* the hub */
    dhgr_fill_rect(58, 38, 24, 14, DHGR_GRAY1);
    for (i = 0u; i < 4u; ++i)                                /* windows */
        dhgr_fill_rect(60u + i * 6u, 42, 3, 3, i == 2u ? DHGR_ORANGE : DHGR_YELLOW);
    dhgr_fill_rect(36, 40, 14, 10, DHGR_GRAY2);              /* modules */
    dhgr_fill_rect(90, 40, 14, 10, DHGR_GRAY2);
    dhgr_fill_rect(92, 43, 2, 2, DHGR_GREEN);
    dhgr_fill_rect(66, 54, 8, 10, DHGR_GRAY1);               /* the dock */
}

/* The title's words in the compact font, each dot a 2 x 2 block (10
 * pixels a character): not dhgr_puts, whose 8 x 8 font and code (~1.3 KB
 * of main memory) served only these two lines. */
static void __fastcall__ big_text(const char *s, unsigned char x, unsigned char y)
{
    static const unsigned char *g;
    static unsigned char r, c, bits;
    for (; *s; ++s, x += 10u) {
        g = dhgr_small_font + (unsigned)(*s - 32) * DHGR_SMALL_FONT_STRIDE;
        for (r = 0u; r < DHGR_SMALL_HEIGHT; ++r)
            for (c = 0u, bits = g[r]; bits; ++c, bits >>= 1)
                if (bits & 1u) dhgr_fill_rect(x + 2u * c, y + 2u * r, 2, 2, DHGR_WHITE);
    }
}

/* Fourteen missions a page (PAGE on the title turns them). */
#define PAGE_N (2u * LIST_N)
unsigned char title_page;

void title_draw(void)
{
    static unsigned char m, k, x, y;
    static char num[2];
    stars();
    ui_latch();
    big_text("ROBOT SPACE", 16, 4);
    big_text("STATION", 36, 17);
    station();
    ui_latch();
    dhgr_puts_small(title_page ? "MISSIONS 15-" : "MISSIONS", 0, LIST_Y - 10u);
    num[1] = 0;
    for (m = title_page * PAGE_N, k = 0u; m < mission_count() && k < PAGE_N; ++m, ++k) {
        y = LIST_Y + (k % LIST_N) * 9u;
        x = k < LIST_N ? 0u : LIST_DX;
        /* green: won, orange: the next, gray: locked */
        dhgr_fill_rect(x, y, 5, 5, m < persist.reached ? DHGR_GREEN
                       : m == persist.reached ? DHGR_ORANGE : DHGR_GRAY1);
        num[0] = m < 9u ? '1' + m : '0';            /* its key (10: 0; */
        if (m < 10u) dhgr_puts_small(num, x + 8u, y);   /* none after) */
        if (m <= persist.reached) dhgr_puts_small(mission_name_of(m), x + 15u, y);
    }
}

unsigned char __fastcall__ title_mission_at(unsigned char x, unsigned char y)
{
    static unsigned char m;
    if (y < LIST_Y - 2u) return NONE;
    m = (unsigned char)(y - LIST_Y + 2u) / 9u;
    if (m >= LIST_N) return NONE;
    if (x >= LIST_DX) m += LIST_N;
    m += title_page * PAGE_N;
    return m < mission_count() && m <= persist.reached ? m : NONE;
}
