/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"
void dhgr_plot_color(unsigned char x, unsigned char y, unsigned char color)
{
    dhgr_fill_rect(x, y, 1u, 1u, color);
}
