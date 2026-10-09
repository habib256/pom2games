/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* HGR row tables and draw-page management. Globals use BSS defaults.
 * crt0 calls copydata, but load==run does not restore mutated DATA on CALL
 * re-entry. BSS is cleared at each entry; table defaults are built lazily.
 * Main RAM/ZP, non-reentrant. Column/mask/phase tables are separate objects.
 */

#include "hgr.h"
#include "hgr_internal.h"

extern void hgr_flip_rows(void);      /* hgr_rows_asm.s: rowhi ^= $60 */

/* Sink for the individual soft-switch macros. A soft-switch READ is the toggle;
 * its value is meaningless. cc65 -Oirs drops a volatile read cast to void, so
 * the macros store the read into this sink — a store cc65 cannot prove dead, so
 * the (volatile) load that feeds it is always emitted. The whole-mode init
 * routines hgr_init / hgr_lores_init live in asm (hgr_mode_asm.s) for the
 * same reason; see the note there and hgr.h. */
/* hgr_ss_sink lives in hgr_state.c. */

/* HIRES draw-page high-byte base: $20 = page 1 ($2000), $40 = page 2 ($4000).
 * GLOBAL (not static) on purpose: the asm _hgr_clear imports _hgr_base
 * so it erases whichever page is currently being drawn. Set by
 * hgr_set_draw_page. BSS (no initializer — see the header): 0 means "unset",
 * lazily defaulted to $20 (page 1) at every read site that can run before
 * hgr_set_draw_page — here, hgr_build_rows, and _hgr_clear in
 * hgr_clear_asm.s. 0 is never a legal base, so the encoding is unambiguous. */
/* hgr_base lives in hgr_state.c: clear-only clients need no tables. */

/* Apple II interleaved HIRES scanline base, in the CURRENT draw page:
   (hgr_base<<8) + (y&7)*$400 + ((y>>3)&7)*$80 + (y>>6)*40
   hgr_base=$20 gives the classic $2000 page-1 layout; $40 is page 2.
   Read from the tables (built on first use): no 16-bit multiply. */
unsigned char *hgr_row(unsigned char y)
{
    if (y > 191u) return 0;
    hgr_build_rows();
    return (unsigned char *)(((unsigned)hgr_rowhi[y] << 8) | hgr_rowlo[y]);
}

/* --- Look-up tables (referenced by every drawing module via hgr_internal.h) */
unsigned char hgr_rowlo[192];
unsigned char hgr_rowhi[192];

/* LORES tables + state live here so hgr_set_draw_page can shift them in
 * place without forcing hgr_lores.c to link. A HIRES-only program pays the
 * 50 bytes (hgr_lo_rowlo[24] + hgr_lo_rowhi[24] + 2 flags) but does NOT
 * pull in the 8 LORES drawing functions (~200 bytes). hgr_lo_ready stays 0
 * until hgr_lores.c's first build call, so the shift below is a harmless
 * no-op for HIRES-only programs (the zero array stays zero).
 * hgr_lo_base is BSS like hgr_base: 0 = unset, lazily defaulted to $04
 * (page 1) by its readers in hgr_lores.c (build + clear). */
unsigned char hgr_lo_rowlo[24];
unsigned char hgr_lo_rowhi[24];
unsigned char hgr_lo_base;
unsigned char hgr_lo_ready;

/* Derive the HIRES scanline-base tables for the current hgr_base, with 8-bit
 * arithmetic only (no multiply runtime): for y = 64*third + 8*group + line,
 *   low  = (group & 1) * 128 + third * 40
 *   high = base + line * 4 + group / 2
 * The low bytes are page-independent; a page flip only EORs the high bytes
 * (hgr_flip_rows). */
static void hgr_fill_rows(void)
{
    unsigned char y = 0u, third, group, line, lo;
    for (third = 0u; third < 3u; ++third) {
        for (group = 0u; group < 8u; ++group) {
            lo = (unsigned char)(((group & 1u) ? 128u : 0u) + third * 40u);
            for (line = 0u; line < 8u; ++line, ++y) {
                hgr_rowlo[y] = lo;
                hgr_rowhi[y] = (unsigned char)(hgr_base + (line << 2) + (group >> 1));
            }
        }
    }
}

static unsigned char hgr_tables_ready;      /* BSS: 0 = not built yet */
/* Build only page-dependent row tables; no column families are pulled in. */
void hgr_build_rows(void)
{
    if (hgr_tables_ready) return;
    if (!hgr_base) hgr_base = 0x20u;
    hgr_fill_rows();
    hgr_tables_ready = 1;
}

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
 * hgr_lores.c into the link; hgr_lores_build() will pick up the right
 * hgr_lo_base on first lores use anyway.
 *
 * INVERTED ENCODING (BSS-zero-default rule, see the header): the flag stores
 * "drawing on page 2", so the BSS zero IS the page-1 default — no DATA
 * initializer, no lazy fixup at the read site. */
static unsigned char hgr_draw_page2;        /* 0 = page 1, nonzero = page 2 */

unsigned char hgr_get_draw_page(void)
{
    return hgr_draw_page2 ? 2u : 1u;
}

void hgr_set_draw_page(unsigned char page)
{
    unsigned char newh, newl, i;
    page = (page == 2u) ? 2u : 1u;
    newh = (page == 2u) ? 0x40u : 0x20u;            /* HIRES $4000 / $2000 */
    newl = (page == 2u) ? 0x08u : 0x04u;            /* LORES $0800 / $0400 */
    /* Ensure the HIRES row tables exist; column families are independent.
     * Later calls are guarded no-ops. LORES tables are built lazily
     * by hgr_lores.c — see the conditional shift below. */
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
     * hgr_lores.c into the link. When LORES IS used later, hgr_lores_build
     * sees hgr_lo_base = newl (set unconditionally below) and computes the
     * right values for the current page. */
    if (hgr_lo_ready && newl != hgr_lo_base) {
        unsigned char dl = (unsigned char)(newl - hgr_lo_base);
        for (i = 0u; i < 24u; ++i)
            hgr_lo_rowhi[i] = (unsigned char)(hgr_lo_rowhi[i] + dl);
    }
    hgr_lo_base = newl;
}

void hgr_show_page(void)
{
    if (hgr_draw_page2) hgr_page2();
    else                 hgr_page1();
}
