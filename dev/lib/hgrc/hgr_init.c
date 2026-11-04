/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Draw-page management and shared LORES state. Globals use BSS defaults.
 * crt0 calls copydata, but load==run does not restore mutated DATA on CALL
 * re-entry. BSS is cleared at each entry; table defaults are built lazily.
 * Main RAM/ZP, non-reentrant. Column/mask/phase tables are separate objects.
 */

#include "hgr.h"
#include "hgr_internal.h"

extern void hgr_flip_rows(void);      /* hgr_rows_asm.s: rowhi ^= $60 */

/* HGR state lives in hgr_state.c; mutable row tables and their lazy builder
 * live in hgr_build_rows.s. Drawing and display-only clients can therefore
 * omit this page manager and the LORES state below. */

/* LORES tables + state live here so hgr_set_draw_page can shift them in
 * place without forcing hgr_lores.s to link. A HIRES-only client that
 * changes draw pages pays the 50 bytes (hgr_lo_rowlo[24] + hgr_lo_rowhi[24] + 2 flags) but does NOT
 * pull in the LORES drawing functions. hgr_lo_ready stays 0
 * until hgr_lores.s's first build call, so the shift below is a harmless
 * no-op for HIRES-only programs (the zero array stays zero).
 * hgr_lo_base is BSS like hgr_base: 0 = unset, lazily defaulted to $04
 * (page 1) by its readers in hgr_lores.s and hgr_lores_clear.s. */
unsigned char hgr_lo_rowlo[24];
unsigned char hgr_lo_rowhi[24];
unsigned char hgr_lo_base;
unsigned char hgr_lo_ready;

/* ===========================================================================
 * Double buffering — draw page vs display page (PAGE2)
 * ===========================================================================
 * The card has two framebuffers: page 1 (HIRES $2000 / LORES $0400) and page 2
 * (HIRES $4000 / LORES $0800). hgr_set_draw_page picks where the drawing
 * primitives WRITE; hgr_show_page flips the card to DISPLAY the current draw
 * page (the $C054/$C055 soft switch). Draw into the
 * hidden page, then show it. Both pages share the same mode — pick it once
 * (hgr_init / hgr_lores_init, which also display PAGE1). The LORES branch
 * below is LAZY (guarded by hgr_lo_ready) so a HIRES-only program does not pull
 * hgr_lores.s into the link; hgr_lores_build() will pick up the right
 * hgr_lo_base on first lores use anyway.
 *
 * INVERTED ENCODING (BSS-zero-default rule, see the header): the flag stores
 * "drawing on page 2", so the BSS zero IS the page-1 default — no DATA
 * initializer, no lazy fixup at the read site. */
/* Page state and getter are independent archive members (hgr_state/draw_page).
 * Reading the page alone must not link mutable row or LORES tables. */

void hgr_set_draw_page(unsigned char page)
{
    unsigned char newh, newl, i;
    page = (page == 2u) ? 2u : 1u;
    newh = (page == 2u) ? 0x40u : 0x20u;            /* HIRES $4000 / $2000 */
    newl = (page == 2u) ? 0x08u : 0x04u;            /* LORES $0800 / $0400 */
    /* Ensure the HIRES row tables exist; column families are independent.
     * Later calls are guarded no-ops. LORES tables are built lazily
     * by hgr_lores.s — see the conditional shift below. */
    hgr_build_rows();
    hgr_draw_page2 = (unsigned char)(page == 2u);
    /* Flip HIRES pages by moving the existing scanline-base HIGH bytes to the
     * other page ($2x <-> $4x is one EOR $60 per entry, in asm) — the low
     * bytes are page-independent. */
    if (newh != hgr_base) {
        hgr_flip_rows();
        hgr_base = newh;
    }
    /* LORES: only shift the existing tables if hgr_lores_build has run. A
     * HIRES-only program will leave hgr_lo_ready = 0 forever and never pull
     * hgr_lores.s into the link. When LORES IS used later, hgr_lores_build
     * sees hgr_lo_base = newl (set unconditionally below) and computes the
     * right values for the current page. */
    if (hgr_lo_ready && newl != hgr_lo_base) {
        unsigned char dl = (unsigned char)(newl - hgr_lo_base);
        for (i = 0u; i < 24u; ++i)
            hgr_lo_rowhi[i] = (unsigned char)(hgr_lo_rowhi[i] + dl);
    }
    hgr_lo_base = newl;
}
