/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "dhgr_internal.h"
void dhgr_clear(unsigned char color)
{
    dhgr_prepare_pattern(color);
    dhgr_clear_asm();
}
