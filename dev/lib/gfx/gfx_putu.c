/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Portable reference; hgrc.mk selects the matching native .s for cc65.
 * Separate archive member: link only the requested numeric text format. */
#include "gfx.h"

void gfx_putu(unsigned value)
{
    char buf[6];                     /* 65535 = 5 digits + NUL */
    gfx_utoa(buf, value);
    gfx_text(buf);
}
