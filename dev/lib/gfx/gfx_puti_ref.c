/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Portable reference; hgrc.mk selects the matching native .s for cc65.
 * Separate archive member: link only the requested numeric text format. */
#include "gfx.h"

void gfx_puti(int value)
{
    char buf[7];                     /* '-' + 5 digits + NUL */
    gfx_itoa(buf, value);
    gfx_text(buf);
}
