/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Compatibility initializer: only this archive member reserves the pool. */
#include "hgr.h"
static unsigned char pool[2u * HGR_SPR_MAX * HGR_SPR_UNDER_BYTES];
void hgr_spr_init(unsigned char double_buffered)
{
    hgr_spr_init_pool(double_buffered, pool, sizeof(pool),
                      HGR_SPR_MAX, HGR_SPR_UNDER_BYTES);
}
