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
static const hgr_mspr_t *spr_shape[HGR_SPR_MAX]; /* 0 = undefined            */
static unsigned      spr_x[HGR_SPR_MAX];          /* target position (move)   */
static unsigned char spr_y[HGR_SPR_MAX];
static unsigned char spr_active[HGR_SPR_MAX];     /* 0 = hidden               */

/* Per PAGE (index 0 = page 1, 1 = page 2): where the sprite was drawn on THAT
 * page and whether it is currently drawn there. Two copies because in double-
 * buffer mode each page holds a 1-frame-old background with its own set of
 * sprites stamped in. Single-buffer mode only ever uses index 0's discipline
 * on whatever the draw page is (see hgr_spr_init). */
static unsigned      spr_px[2][HGR_SPR_MAX];
static unsigned char spr_py[2][HGR_SPR_MAX];
static unsigned char spr_drawn[2][HGR_SPR_MAX];

/* The engine-owned save-under pool: HGR_SPR_MAX slots of HGR_SPR_UNDER_BYTES
 * per page = 2 * 8 * 96 = 1536 bytes of BSS. A slot holds the stride*h byte
 * rectangle a draw covered (cap documented in hgr.h; hgr_spr_define rejects
 * bigger shapes). */
static unsigned char spr_under[2][HGR_SPR_MAX * HGR_SPR_UNDER_BYTES];

static unsigned char spr_dbuf;       /* 1 = double-buffered                    */
static unsigned char spr_drawpage;   /* page the NEXT update draws on (1 or 2) */

/* Init the engine. double_buffered = 1: the engine displays page 1, draws on
 * page 2, and flips every hgr_spr_update -- the caller must have drawn the
 * background on BOTH pages first. double_buffered = 0: everything happens on
 * page 1 (displayed immediately). Re-init FORGETS all under-buffers, so call
 * it only over clean backgrounds (e.g. right after redrawing them). */
void hgr_spr_init(unsigned char double_buffered)
{
    unsigned char i;
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
}

/* Definitions may change only when neither page holds this sprite. Hide and
 * render both pages first (one in single-buffer mode), or re-init on clean
 * backgrounds. A rejected redefinition keeps the old shape so restores remain
 * valid. Geometry/pointers are checked before the assembler kernels run. */
unsigned char hgr_spr_define(unsigned char id, const hgr_mspr_t *shape)
{
    if (id >= HGR_SPR_MAX) return 0u;
    if (spr_drawn[0][id] || spr_drawn[1][id]) return 0u;
    if (shape != 0 &&
        (!shape->data || !shape->mask || !shape->stride || !shape->h ||
         shape->stride > 40u || shape->h > 192u ||
         (unsigned)shape->stride * shape->h > HGR_SPR_UNDER_BYTES)) {
        spr_shape[id] = 0;
        spr_active[id] = 0u;
        return 0u;
    }
    spr_shape[id] = shape;
    spr_active[id] = (shape != 0) ? 1u : 0u;
    return 1u;
}

/* Record the target position; nothing is drawn until render/update. */
void hgr_spr_move(unsigned char id, unsigned x, unsigned char y)
{
    if (id >= HGR_SPR_MAX) return;
    spr_x[id]      = x;
    spr_y[id]      = y;
    spr_active[id] = (spr_shape[id] != 0) ? 1u : 0u;
}

/* Hide a sprite: it stops being drawn and its under-rect is restored by the
 * next render (TWO render/present cycles in double-buffer mode). */
void hgr_spr_hide(unsigned char id)
{
    if (id >= HGR_SPR_MAX) return;
    spr_active[id] = 0u;
}

/* Restore in reverse draw order, then draw active sprites in forward order.
 * This preserves overlapping backgrounds. Rendering never waits or flips;
 * double-buffer users can draw a HUD and wait before hgr_spr_present(). */
void hgr_spr_render(void)
{
    unsigned char pg, id;
    unsigned char *ub;

    pg = (unsigned char)(spr_drawpage - 1u); /* page index 0/1                */
    hgr_set_draw_page(spr_drawpage);        /* row tables -> this page       */

    /* restore pass, reverse order; ub walks the pool backwards slot by slot
     * (no per-sprite 16-bit multiply) */
    ub = &spr_under[pg][HGR_SPR_MAX * HGR_SPR_UNDER_BYTES];
    id = HGR_SPR_MAX;
    while (id-- > 0u) {
        ub -= HGR_SPR_UNDER_BYTES;
        if (!spr_drawn[pg][id]) continue;
        hgr_ms_x     = spr_px[pg][id];
        hgr_ms_y     = spr_py[pg][id];
        hgr_ms_spr   = spr_shape[id];
        hgr_ms_under = ub;
        hgr_ms_restore_run();
        spr_drawn[pg][id] = 0u;
    }

    /* draw pass, forward order (later ids paint over earlier ones) */
    ub = &spr_under[pg][0];
    for (id = 0u; id < HGR_SPR_MAX; ++id, ub += HGR_SPR_UNDER_BYTES) {
        if (!spr_active[id] || spr_shape[id] == 0) continue;
        if (spr_x[id] > 279u || spr_y[id] > 191u) continue;  /* off-screen    */
        hgr_ms_x     = spr_x[id];
        hgr_ms_y     = spr_y[id];
        hgr_ms_spr   = spr_shape[id];
        hgr_ms_under = ub;
        hgr_msu_run();                      /* save-under + draw, one pass   */
        spr_px[pg][id]    = spr_x[id];
        spr_py[pg][id]    = spr_y[id];
        spr_drawn[pg][id] = 1u;
    }
}

/* Present the rendered page and select the next draw page. No synchronization.
 * In single-buffer mode rendering is already visible; this is a no-op. */
void hgr_spr_present(void)
{
    if (spr_dbuf) {
        hgr_show_page();
        spr_drawpage = (spr_drawpage == 1u) ? 2u : 1u;
        hgr_set_draw_page(spr_drawpage);
    }
}

/* Backward-compatible immediate restore/draw/present. */
void hgr_spr_update(void)
{
    hgr_spr_render();
    hgr_spr_present();
}
