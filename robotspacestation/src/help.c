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

void __fastcall__ help_draw(unsigned char page)
{
    static unsigned char i, y, n;
    static char num[3];
    if (page) {
        dhgr_puts_small("RECORDS : LE MOINS DE PORTES", 0, 4);
        for (i = 0u; i < mission_count(); ++i) {
            y = 18u + i * 9u;
            n = persist.best[i];
            dhgr_puts_small(i < persist.reached ? mission_name_of(i) : (const char *)"-", 4, y);
            if (!n) continue;
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
