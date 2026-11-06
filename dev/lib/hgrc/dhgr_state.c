/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Double hi-res drawing; banked memory access lives in dhgr_asm.s.
 * Layout and color phase: Apple IIe Technical Note #3, November 1988.
 */
#include "dhgr_internal.h"

unsigned char dhgr_base = 0x20; /* draw page 1 even before dhgr_init: never $0000 */
unsigned char dhgr_display;
