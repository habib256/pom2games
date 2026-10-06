/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Double hi-res drawing; banked memory access lives in dhgr_asm.s.
 * Layout and color phase: Apple IIe Technical Note #3, November 1988.
 */
#include "dhgr_internal.h"

unsigned char *dhgr_addr;
unsigned char dhgr_aux, dhgr_mask, dhgr_bits;
unsigned char dhgr_base;
unsigned char dhgr_display;
unsigned char dhgr_pattern[4]; /* aux even, main even, aux odd, main odd */
unsigned char dhgr_first, dhgr_last, dhgr_first_mask, dhgr_last_mask;

void __fastcall__ dhgr_draw_page(unsigned char page)
{
    if (page == 1 || page == 2) dhgr_base = page == 1 ? 0x20 : 0x40;
}

unsigned char dhgr_get_draw_page(void) { return dhgr_base == 0x20 ? 1 : 2; }
unsigned char dhgr_get_display_page(void) { return dhgr_display; }

void dhgr_flip(void)
{
    unsigned char previous = dhgr_display;
    dhgr_show_page(dhgr_get_draw_page());
    dhgr_draw_page(previous);
}
