/* hgr_text.c — doubled white/color text.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"

static void hgr_puts_common(unsigned x, unsigned char y, const char *s,
                             unsigned char colorMode)
{
    hgr_build_tables();
    if (y > 176u || x > 264u) return;        /* cell needs y+15<=191 and a fitting x */
    hgr_g_y     = y;
    hgr_t_col   = (unsigned char)(x / 7u);
    hgr_t_bit   = (unsigned char)(x % 7u);
    hgr_t_n     = (unsigned char)((264u - x) / 18u + 1u);  /* glyph cells that fit */
    hgr_t_s     = (const unsigned char *)s;
    hgr_t_font  = hgr_font;
    hgr_t_color = colorMode;
    hgr_puts_run();
}

void hgr_puts(unsigned x, unsigned char y, const char *s)
{
    hgr_puts_common(x, y, s, 0u);
}

void hgr_puts_color(unsigned x, unsigned char y, const char *s, unsigned char color)
{
    if (!hgr_set_carrier(color)) {         /* white / unknown -> plain white text */
        hgr_puts_common(x, y, s, 0u);
        return;
    }
    hgr_puts_common(x, y, s, 1u);          /* one tinted pass per glyph */
}
