/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Compatibility initializer: only this archive member reserves the pool. */
#include "hgr.h"
#if !defined(__CC65__) || (defined(HGR_SPR_C_ENTRY) && HGR_SPR_C_ENTRY)
static unsigned char pool[2u * HGR_SPR_MAX * HGR_SPR_UNDER_BYTES];
void hgr_spr_init(unsigned char double_buffered)
{
    hgr_spr_init_pool(double_buffered, pool, sizeof(pool),
                      HGR_SPR_MAX, HGR_SPR_UNDER_BYTES);
}

#else
/* This archive member is extracted only by the compatibility initializer. */
unsigned char spr_default_pool[2u * HGR_SPR_MAX * HGR_SPR_UNDER_BYTES];
const unsigned spr_default_bytes = sizeof(spr_default_pool);
const unsigned char spr_default_capacity = HGR_SPR_UNDER_BYTES;
const unsigned char spr_default_count = HGR_SPR_MAX;
#endif
