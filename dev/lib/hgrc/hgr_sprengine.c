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

/* Bind a shape to a sprite slot. Rejected (slot deactivated) when the covered
 * rectangle stride*h exceeds the HGR_SPR_UNDER_BYTES save-under cap.
 * Redefining a shape while the sprite is still drawn on a page is undefined
 * (the pending restore would use the new geometry) -- hide + update first. */
void hgr_spr_define(unsigned char id, const hgr_mspr_t *shape)
{
    if (id >= HGR_SPR_MAX) return;
    if (shape != 0 &&
        (unsigned)shape->stride * shape->h > HGR_SPR_UNDER_BYTES) {
        spr_shape[id]  = 0;
        spr_active[id] = 0u;
        return;
    }
    spr_shape[id]  = shape;
    spr_active[id] = (shape != 0) ? 1u : 0u;
}

/* Record the target position; nothing is drawn until hgr_spr_update. */
void hgr_spr_move(unsigned char id, unsigned x, unsigned char y)
{
    if (id >= HGR_SPR_MAX) return;
    spr_x[id]      = x;
    spr_y[id]      = y;
    spr_active[id] = (spr_shape[id] != 0) ? 1u : 0u;
}

/* Hide a sprite: it stops being drawn and its under-rect is restored by the
 * next update (the next TWO updates in double-buffer mode -- one per page). */
void hgr_spr_hide(unsigned char id)
{
    if (id >= HGR_SPR_MAX) return;
    spr_active[id] = 0u;
}

/* One frame: restore every drawn sprite (REVERSE draw order, so overlapping
 * under-rects unwind exactly), then save-under + masked-draw every active one
 * at its CURRENT position. Double-buffer: all of it on the hidden page, then
 * flip in V-blank and swap the pen. Single-buffer: V-blank first, then the
 * whole restore+draw races the beam (see the budget note above). */
void hgr_spr_update(void)
{
    unsigned char pg, id;
    unsigned char *ub;

    /* Apple II: no V-blank input, the single-buffer pass races the beam. */

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

    if (spr_dbuf) {
        /* Apple II: no V-blank to wait for -- flip right away. */
        hgr_show_page();                    /* $C054/$C055 READ = the flip   */
        spr_drawpage = (spr_drawpage == 1u) ? 2u : 1u;
    }
}
