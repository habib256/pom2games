/* Robot Space Station — the help and records pages (title: AIDE, H,
 * RECORDS), in main memory: HI (zone.c, title.c) is full. */
#include "dhgr.h"
#include "sim.h"
#include "zone.h"
#include "title.h"

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

/* Page 2, the rooms: a sample of each tile (zone.c's colours), its rule
 * (title.c legend_text: HI). */
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
    dhgr_puts_small("LES SALLES", 45, 4);
    for (i = 0u; i < LEGEND_N; ++i)
        dhgr_puts_small(legend_text[i], 16, 17u + i * 13u);
    for (i = 0u; i < sizeof swatch / sizeof swatch[0]; ++i) {
        r = swatch[i];
        dhgr_fill_rect(r[0], r[1], r[2], r[3], r[4]);
    }
}

void __fastcall__ help_draw(unsigned char page)
{
    if (page == 2u) { legend_draw(); return; }
    {
    static unsigned char i, y, n;
    static char num[3];
    if (page) {
        dhgr_puts_small("RECORDS : LE MOINS DE PORTES", 0, 4);
        for (i = title_page * 14u; i < mission_count() && i < title_page * 14u + 14u; ++i) {
            y = 18u + (i - title_page * 14u) * 9u;    /* the title's page */
            n = persist.best[i];            /* gates + 1, 0: never won */
            dhgr_puts_small(i < persist.reached ? mission_name_of(i) : (const char *)"-", 4, y);
            if (!n--) continue;
            if (n > 99u) n = 99u;
            num[0] = n >= 10u ? '0' + n / 10u : ' ';
            num[1] = '0' + n % 10u;
            num[2] = 0;
            dhgr_puts_small(num, 84, y);
            dhgr_puts_small(n == 1u ? (const char *)"PORTE" : (const char *)"PORTES", 98, y);
        }
        return;
    }
    for (i = 0u; i < sizeof help_lines / sizeof help_lines[0]; ++i)
        dhgr_puts_small(help_lines[i], i ? 4u : 60u, 4u + i * 9u);
}
}
