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

unsigned char hgr_hud_putu(hgr_hud_field_t *field, unsigned value)
{
    char number[6], glyph[2];
    unsigned x;
    unsigned char page, bit, len, i, leading, changed=0u;
    char ch;
    if (!field || !field->width || field->width > 14u) return HGR_HUD_INVALID;
    page=hgr_get_draw_page()-1u; bit=1u << page;
    if ((field->valid & bit) && field->value[page] == value) return 0u;
    hgr_u_lo=(unsigned char)value; hgr_u_hi=(unsigned char)(value >> 8);
    hgr_u_ptr=number; hgr_utoa();
    len=0u; while (number[len]) ++len;
    if (len > field->width) return HGR_HUD_INVALID;
    leading=field->width-len; x=field->x; glyph[1]=0;
    for (i=0u; i<field->width; ++i, x+=18u) {
        ch=(i < leading) ? ' ' : number[i-leading];
        if (!(field->valid & bit) || ch != field->digits[page][i]) {
            hgr_clear_pixrect(x,field->y,(i+1u == field->width) ? 16u : 18u,16u);
            if (ch != ' ') { glyph[0]=ch; hgr_puts(x,field->y,glyph); }
            field->digits[page][i]=ch;
            ++changed;
        }
    }
    field->value[page]=value; field->valid |= bit;
    return changed;
}
