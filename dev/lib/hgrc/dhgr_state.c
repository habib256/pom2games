/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Double hi-res drawing; banked memory access lives in dhgr_asm.s.
 * Layout and color phase: Apple IIe Technical Note #3, November 1988.
 */
#include "dhgr_internal.h"

unsigned char *dhgr_addr;
unsigned char dhgr_aux, dhgr_mask, dhgr_bits;
unsigned char dhgr_base = 0x20; /* draw page 1 even before dhgr_init: never $0000 */
unsigned char dhgr_display;
unsigned char dhgr_pattern[4]; /* aux even, main even, aux odd, main odd */
unsigned char dhgr_first, dhgr_last, dhgr_first_mask, dhgr_last_mask;

