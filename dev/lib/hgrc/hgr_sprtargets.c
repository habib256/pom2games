/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Target coordinates: needed by move/render, omitted by init/define. */
#include "hgr.h"
#if defined(__CC65__) && !HGR_SPR_DAMAGE && (!defined(HGR_SPR_C_ENTRY) || !HGR_SPR_C_ENTRY)
unsigned spr_x[HGR_SPR_MAX];
unsigned char spr_y[HGR_SPR_MAX];
#endif
