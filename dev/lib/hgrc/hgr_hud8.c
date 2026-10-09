/* VERHILLE Arnaud — GPL-3.0. Compact caller-owned HUD, history per page. */
#include "hgr.h"
#include "hgr_internal.h"

unsigned char hgr_hud8_init(hgr_hud8_field_t *field, unsigned x,
                          unsigned char y, unsigned char width)
{
    if (!field || !width || width > 5u || x >= 280u || y > 184u ||
        (unsigned)width*8u > 280u-x) return 0u;
    field->x=x; field->y=y; field->width=width; field->valid=0u;
    return 1u;
}

void hgr_hud8_invalidate(hgr_hud8_field_t *field, unsigned char page)
{
    if (!field) return;
    if (page == 1u) field->valid &= 2u;
    else if (page == 2u) field->valid &= 1u;
    else if (!page) field->valid=0u;
}

/* The frequently called putu entry is implemented in hgr_hud8_putu.s. */
