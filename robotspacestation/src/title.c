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

void title_draw(void)
{
    static unsigned char m, x, y;
    static char num[2];
    stars();
    ui_latch();
    dhgr_puts("ROBOT SPACE", 26, 4);
    dhgr_puts("STATION", 42, 16);
    station();
    ui_latch();
    dhgr_puts_small("MISSIONS", 0, LIST_Y - 10u);
    num[1] = 0;
    for (m = 0u; m < mission_count(); ++m) {
        y = LIST_Y + (m % LIST_N) * 9u;
        x = m < LIST_N ? 0u : LIST_DX;
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
    return m < mission_count() && m <= persist.reached ? m : NONE;
}

/* The help page (AIDE on the title, or H): what a board's terminals are,
 * the parts, the keys. 27 characters a line at most (5 pixels each). */
static const char *const help_lines[] = {
    "AIDE",
    "",
    "LE TECHNICIEN ENTRE DANS",
    "UN DRONE EN LE TOUCHANT.",
    "A GAUCHE DE SA PLANCHE :",
    " N E S O  CONTACT AU BORD",
    " T  LA PINCE TIENT",
    " R  RECU PAR RADIO",
    "A DROITE :",
    " N E S O  PROPULSEURS",
    "    N POUSSE VERS LE SUD",
    " P  PINCE  E  EMISSION",
    "ET OU OX NO  BA : BASCULE",
    "LABO : PUCES F1 A F8",
    "M MARCHE  P PAS  S SON",
    "H INDICE  ESC LACHE",
    "V VITE  CTRL-Q QUITTE",
};

void help_draw(void)
{
    static unsigned char i;
    for (i = 0u; i < sizeof help_lines / sizeof help_lines[0]; ++i)
        dhgr_puts_small(help_lines[i], i ? 4u : 60u, 4u + i * 9u);
}
