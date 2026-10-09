/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_sprengine.c — masked save-under sprites for Apple II HGR (cc65).
 * Needs SPRMASK + CORE. Each sprite saves and restores its background.
 * Double buffering keeps separate backgrounds and previous positions per
 * page. A II/II+ has no readable V-blank flag: page flips are immediate,
 * and single-buffered updates may be visible while the beam scans the page.
 */
#include "hgr.h"
#include "hgr_internal.h"

/* --- per-sprite state: parallel static arrays ------------------------------ */
const hgr_mspr_t *spr_shape[HGR_SPR_MAX]; /* 0 = undefined            */
unsigned      spr_x[HGR_SPR_MAX];          /* target position (move)   */
unsigned char spr_y[HGR_SPR_MAX];
unsigned char spr_active[HGR_SPR_MAX];     /* 0 = hidden               */

/* Per PAGE (index 0 = page 1, 1 = page 2): where the sprite was drawn on THAT
 * page and whether it is currently drawn there. Two copies because in double-
 * buffer mode each page holds a 1-frame-old background with its own set of
 * sprites stamped in. Single-buffer mode only ever uses index 0's discipline
 * on whatever the draw page is (see hgr_spr_init). */
unsigned      spr_px[2][HGR_SPR_MAX];
unsigned char spr_py[2][HGR_SPR_MAX];
unsigned char spr_drawn[2][HGR_SPR_MAX];

/* Caller-owned save-under storage. The compatibility pool is in its own
 * archive object, so external-pool clients do not link its 1536 bytes. */
unsigned char *spr_under[2];
unsigned char spr_count, spr_capacity;

unsigned char spr_invalid;    /* explicit per-page redraw requests */
unsigned char spr_dbuf;       /* 1 = double-buffered                    */
unsigned char spr_drawpage;   /* page the NEXT update draws on (1 or 2) */

/* Optional overlap closure. Bounds describe whole save-under BYTES, including
 * padding, because restoration writes bytes beyond the visible mask. Compile
 * the engine C member with -DHGR_SPR_DAMAGE=1 to opt in. Boxes and their native
 * helper are linked only for that mode; shared dispatch state costs 3 bytes. */
#if HGR_SPR_DAMAGE
unsigned char spr_box[HGR_SPR_MAX][4];

void hgr_spr_damage(void);
#endif

unsigned char spr_block[HGR_SPR_MAX], spr_dirty;
void (*spr_damage_fn)(void);
const unsigned char spr_slots=HGR_SPR_MAX;

/* Init the engine. double_buffered = 1: the engine displays page 1, draws on
 * page 2, and flips every hgr_spr_update -- the caller must have drawn the
 * background on BOTH pages first. double_buffered = 0: everything happens on
 * page 1 (displayed immediately). Re-init FORGETS all under-buffers, so call
 * it only over clean backgrounds (e.g. right after redrawing them). */
unsigned char hgr_spr_init_pool(unsigned char double_buffered,
    unsigned char *pool, unsigned pool_bytes,
    unsigned char count, unsigned char capacity)
{
    unsigned char i;
    unsigned page_bytes;
    if (!pool || !count || count > HGR_SPR_MAX || !capacity) return 0u;
    page_bytes = (unsigned)count * capacity;
    if (pool_bytes < page_bytes * (double_buffered ? 2u : 1u)) return 0u;
    spr_under[0] = pool;
    spr_under[1] = double_buffered ? pool + page_bytes : pool;
    spr_invalid = 0u;
#if HGR_SPR_DAMAGE
    spr_damage_fn=hgr_spr_damage;
#else
    spr_damage_fn=0;
#endif
    spr_count = count;
    spr_capacity = capacity;
    spr_dbuf = double_buffered;
    for (i = 0u; i < HGR_SPR_MAX; ++i) {
        spr_shape[i]    = 0;
        spr_active[i]   = 0u;
        spr_drawn[0][i] = 0u;
        spr_drawn[1][i] = 0u;
    }
    /* Display page 1 in both modes (hgr_show_page shows the CURRENT draw
     * page, so select 1 first). Double buffering then moves the pen to the
     * hidden page 2. */
    hgr_set_draw_page(1u);
    hgr_show_page();
    spr_drawpage = double_buffered ? 2u : 1u;
    if (double_buffered) hgr_set_draw_page(2u);
    return 1u;
}

/* Definitions may change only when neither page holds this sprite. Hide and
 * render both pages first (one in single-buffer mode), or re-init on clean
 * backgrounds. A rejected redefinition keeps the old shape so restores remain
 * valid. Geometry/pointers are checked before the assembler kernels run. */
unsigned char hgr_spr_define(unsigned char id, const hgr_mspr_t *shape)
{
    if (id >= spr_count) return 0u;
    if (spr_drawn[0][id] || spr_drawn[1][id]) return 0u;
    if (shape != 0 &&
        (!shape->data || !shape->mask || !shape->stride || !shape->h ||
         shape->stride > 40u || shape->h > 192u ||
         (unsigned)shape->stride * shape->h > spr_capacity)) {
        spr_shape[id] = 0;
        spr_active[id] = 0u;
        return 0u;
    }
    spr_block[id] = shape ? (unsigned)shape->stride * shape->h : 0u;
    spr_shape[id] = shape;
    spr_active[id] = (shape != 0) ? 1u : 0u;
    return 1u;
}

/* move/hide/render/present/update/invalidate are in hgr_sprengine_asm.s. */
