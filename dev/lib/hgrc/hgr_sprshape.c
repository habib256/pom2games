/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Definition pointers: the first part of native default sprite state. */
#include "hgr.h"
#if defined(__CC65__) && !HGR_SPR_DAMAGE && (!defined(HGR_SPR_C_ENTRY) || !HGR_SPR_C_ENTRY)
const hgr_mspr_t *spr_shape[HGR_SPR_MAX];
#endif
