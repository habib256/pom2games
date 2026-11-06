/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Previous coordinates: extracted only when the renderer needs page history. */
#include "hgr.h"
#if defined(__CC65__) && !HGR_SPR_DAMAGE && (!defined(HGR_SPR_C_ENTRY) || !HGR_SPR_C_ENTRY)
unsigned spr_px[2][HGR_SPR_MAX];
unsigned char spr_py[2][HGR_SPR_MAX];
#endif
