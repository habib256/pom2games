/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#include "hgr.h"

unsigned char hgr_tilemap_init(hgr_tilemap_t *ctx, const unsigned char *map,
                              const unsigned char *tiles, unsigned count)
{
    unsigned i;
    if (!ctx || !map || !tiles || !count || count > 256u) return 0;
    if (count < 256u)
        for (i=0; i<960u; ++i) if (map[i] >= count) return 0;
    ctx->map=map; ctx->tiles=tiles; ctx->count=count;
    return 1;
}
