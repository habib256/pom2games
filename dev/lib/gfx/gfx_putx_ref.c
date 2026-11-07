/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Portable reference; hgrc.mk selects the matching native .s for cc65.
 * Separate archive member: link only the requested numeric text format. */
#include "gfx.h"

void gfx_putx(unsigned value)
{
    char buf[5];                     /* 4 hex digits + NUL */
    gfx_hexstr(buf, value);
    gfx_text(buf);
}
