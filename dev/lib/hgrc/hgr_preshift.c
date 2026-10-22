/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_preshift.c — Buzzard-Bait-style pre-shifted sprite blit (hgr_sprite).
 *
 * The "missing middle" of the HGR blit family: hgr_blit is 1px-precise
 * but slow (per-pixel mask walk); hgr_blit7 is byte-fast but snaps x to a
 * 7px grid. This one is BOTH fast AND 1px-precise, by trading memory: the sprite
 * is pre-shifted into 7 phase copies OFFLINE (dev/tools/assets/convert.py), and at
 * runtime we just pick the phase for x%7 and reuse the proven byte-aligned blit
 * kernel (hgr_blit7_run) at column x/7. No per-pixel shifting at all.
 *
 * This is a pure C clipping/selection wrapper around the asm kernels in
 * hgr_preshift_asm.s. Speed matters here: a single-buffer XOR program must fit its
 * erase+redraw inside V-blank (~4550 cyc) or the beam catches it mid-update
 * (flicker), so this path is tuned the Buzzard-Bait way:
 *   - x/7 and x%7 come from the hgr_col7[] / hgr_phase7[] TABLES, not cc65's
 *     16-bit software divide (~150-300 cyc each — the dominant per-call cost);
 *   - HGR_XOR (the hot animation path) uses hgr_preshift_xor_run, an XOR
 *     loop fused after the phase lookup. hgr_blit7_run's loop is specialised
 *     per mode too: both cost ~24 cyc/byte (CLEAR 26), no per-byte test.
 * See hgr.h for the data ABI and POM1's a2port_buzzard_bait/DISASSEMBLY.md (S3)
 * for the method. */

#include "hgr.h"
#include "hgr_internal.h"

void hgr_sprite(unsigned x, unsigned char y,
                     const hgr_sprite_t *spr, unsigned char mode)
{
    /* Clip, x/7 + x%7 from the hgr_col7[] / hgr_phase7[] tables and the
     * phase block offset p*(h*stride) (see hgr.h ABI) are hgr_xs_setup's,
     * in asm: no cc65 multiply. It writes the hgr_b_* zero-page block. */
    hgr_build_rows();
    if (spr->stride == 0u || spr->h == 0u || y > 191u || x > 279u) return;
    hgr_xs_x   = x;
    hgr_xs_y   = y;
    hgr_xs_spr = spr;
    if (mode == HGR_XOR) {
        hgr_xs_run();                          /* hot path: no per-byte mode test */
    } else {
        hgr_b_mode = mode;
        hgr_xs_setup();
        hgr_blit7_run();
    }
}

/* XOR-only fast path: a THIN C entry that just stows the args in zero page and
 * jumps to the all-asm worker (hgr_xs_run in hgr_preshift_asm.s). All the per-call cost
 * the cc65 wrapper above pays -- the x/7 + x%7 (here table lookups, but still),
 * the phase*h*stride multiply, the 16-bit edge-clip ternaries -- moves into asm,
 * reducing the cost of erase+redraw. Synchronization and the complete frame
 * budget remain the caller's responsibility. The asm still edge-clips. */
void hgr_sprite_xor(unsigned x, unsigned char y, const hgr_sprite_t *spr)
{
    hgr_build_rows();
    if (spr->stride == 0u || spr->h == 0u || y > 191u || x > 279u) return;
    hgr_xs_x   = x;
    hgr_xs_y   = y;
    hgr_xs_spr = spr;
    hgr_xs_run();
}
