/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_text.c — doubled white/color text.
 * One archive member: unused families add neither code nor zero-page state.
 * One blitter draws both: white is the $7F/$7F carrier pair with no palette
 * bit (every doubled pixel ORed in), colour a carrier pair + palette bit. */
#include "hgr.h"
#include "hgr_internal.h"

static void hgr_puts_common(unsigned x, unsigned char y, const char *s)
{
    unsigned char n;
    unsigned room;
    hgr_build_rows();
    hgr_build_columns();
    hgr_build_phases();
    if (y > 176u || x > 264u) return;        /* cell needs y+15<=191 and a fitting x */
    hgr_g_y     = y;
    hgr_t_col   = hgr_col7[x];
    hgr_t_bit   = hgr_phase7[x];
    room = 264u - x;                         /* glyph cells that fit: (264-x)/18 + 1 */
    for (n = 1u; room >= 18u; room -= 18u) ++n;
    hgr_t_n     = n;
    hgr_t_s     = (const unsigned char *)s;
    hgr_t_font  = hgr_font;
    hgr_puts_run();
}

void hgr_puts(unsigned x, unsigned char y, const char *s)
{
    hgr_z_ce = 0x7Fu;                        /* white: keep every doubled pixel */
    hgr_z_co = 0x7Fu;
    hgr_z_hi = 0x00u;
    hgr_puts_common(x, y, s);
}

void hgr_puts_color(unsigned x, unsigned char y, const char *s, unsigned char color)
{
    if (!hgr_set_carrier(color)) {         /* white / unknown -> plain white text */
        hgr_puts(x, y, s);
        return;
    }
    hgr_puts_common(x, y, s);              /* one tinted pass per glyph */
}
