/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_text8.c — native white text.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"

void hgr_puts8(unsigned x, unsigned char y, const char *s)
{
    hgr_build_tables();
    if (y > 184u || x > 273u) return;
    hgr_g_y    = y;
    hgr_t_col  = hgr_col7[x];                    /* tables: no runtime divide */
    hgr_t_bit  = hgr_phase7[x];
    hgr_t_n    = (unsigned char)(((273u - x) >> 3) + 1u);  /* 8x8 cells that fit */
    hgr_t_s    = (const unsigned char *)s;
    hgr_t_font = hgr_font;
    hgr_puts_run8();
}
