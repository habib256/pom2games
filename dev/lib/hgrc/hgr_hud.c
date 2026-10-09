/* VERHILLE Arnaud — GPL-3.0. Caller-owned numeric HUD, history per page. */
#include "hgr.h"
#include "hgr_internal.h"

unsigned char hgr_hud_init(hgr_hud_field_t *field, unsigned x,
                         unsigned char y, unsigned char width)
{
    unsigned extent;
    if (!field || !width || width > 14u || x >= 280u || y > 176u) return 0u;
    extent = (unsigned)(width-1u)*18u + 16u;
    if (extent > 280u-x) return 0u;
    field->x=x; field->y=y; field->width=width; field->valid=0u;
    return 1u;
}

void hgr_hud_invalidate(hgr_hud_field_t *field, unsigned char page)
{
    if (!field) return;
    if (page == 1u) field->valid &= 2u;
    else if (page == 2u) field->valid &= 1u;
    else if (!page) field->valid=0u;
}

/* The frequently called putu entry is implemented in hgr_hud_putu.s. */
