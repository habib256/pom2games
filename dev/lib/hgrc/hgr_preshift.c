/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_preshift.c — Buzzard-Bait-style pre-shifted sprite blit (hgr_sprite).
 *
 * The "missing middle" of the HGR blit family: hgr_blit is 1px-precise
 * but slow (per-pixel mask walk); hgr_blit7 is byte-fast but snaps x to a
 * 7px grid. This one is BOTH fast AND 1px-precise, by trading memory: the sprite
 * is pre-shifted into 7 phase copies OFFLINE (build_preshift_sprites.py), and at
 * runtime we just pick the phase for x%7 and reuse the proven byte-aligned blit
 * kernel (hgr_blit7_run) at column x/7. No per-pixel shifting at all.
 *
 * This is a pure C clipping/selection wrapper around the asm kernels in
 * hgr_preshift_asm.s. Speed matters here: a single-buffer XOR program must fit its
 * erase+redraw inside V-blank (~4550 cyc) or the beam catches it mid-update
 * (flicker), so this path is tuned the Buzzard-Bait way:
 *   - x/7 and x%7 come from the hgr_col7[] / hgr_phase7[] TABLES, not cc65's
 *     16-bit software divide (~150-300 cyc each — the dominant per-call cost);
 *   - HGR_XOR (the hot animation path) uses hgr_preshift_xor_run, a dedicated
 *     XOR loop with no per-byte mode dispatch (~24 vs ~34 cyc/byte).
 * See hgr.h for the data ABI and DISASSEMBLY.md (S3) for the method. */

#include "hgr.h"
#include "hgr_internal.h"

void hgr_sprite(unsigned x, unsigned char y,
                     const hgr_sprite_t *spr, unsigned char mode)
{
    /* No stack locals for the clip math: write straight to the hgr_b_* zero-page
     * block (cf. the hgr_blit note — cc65 -Oirs reuses stack-local slots as
     * 16-bit scratch and silently clobbers them). phase_off is the only 16-bit
     * temp; it is consumed immediately. */
    unsigned char col, phase, stride, h;
    unsigned      phase_off;

    hgr_build_tables();
    stride = spr->stride;
    h      = spr->h;
    if (h == 0u || stride == 0u || y > 191u || x > 279u) return;

    /* Table lookups, NOT x/7 + x%7: cc65 has no hardware divide, so each of those
     * is a ~150-300 cyc runtime call. x <= 279 is guaranteed above, so the tables
     * (built by hgr_build_tables) are always in range; col is therefore <= 39. */
    col   = hgr_col7[x];
    phase = hgr_phase7[x];                     /* sub-byte phase 0..6           */

    /* Phase block p starts at p*(h*stride) bytes into the bank (see hgr.h ABI). */
    phase_off     = (unsigned)phase * ((unsigned)h * stride);
    hgr_b_src    = spr->bits + phase_off;
    hgr_b_col    = col;
    hgr_b_stride = stride;                     /* full source row length        */
    /* bytes actually drawn this row, right-clipped to the 40-byte page */
    hgr_b_w      = ((unsigned)col + stride > 40u)
                        ? (unsigned char)(40u - col)
                        : stride;
    hgr_b_y      = y;
    hgr_b_h      = ((unsigned)y + h > 192u)    /* bottom clip                   */
                        ? (unsigned char)(192u - y)
                        : h;
    if (mode == HGR_XOR) {
        hgr_preshift_xor_run();                /* hot path: no per-byte mode test */
    } else {
        hgr_b_mode = mode;
        hgr_blit7_run();
    }
}

/* XOR-only fast path: a THIN C entry that just stows the args in zero page and
 * jumps to the all-asm worker (hgr_xs_run in hgr_preshift_asm.s). All the per-call cost
 * the cc65 wrapper above pays -- the x/7 + x%7 (here table lookups, but still),
 * the phase*h*stride multiply, the 16-bit edge-clip ternaries -- moves into asm,
 * so an erase+redraw pair fits in V-blank and single-buffer animation is
 * flicker-free. Caller guarantees x <= 279 / y <= 191 (the asm still edge-clips). */
void hgr_sprite_xor(unsigned x, unsigned char y, const hgr_sprite_t *spr)
{
    hgr_build_tables();
    if (spr->stride == 0u || spr->h == 0u || y > 191u || x > 279u) return;
    hgr_xs_x   = x;
    hgr_xs_y   = y;
    hgr_xs_spr = spr;
    hgr_xs_run();
}
