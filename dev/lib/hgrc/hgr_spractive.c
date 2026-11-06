/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Visibility flags: follows target coordinates in the full state layout. */
#include "hgr.h"
#if defined(__CC65__) && !HGR_SPR_DAMAGE && (!defined(HGR_SPR_C_ENTRY) || !HGR_SPR_C_ENTRY)
unsigned char spr_active[HGR_SPR_MAX];
#endif
