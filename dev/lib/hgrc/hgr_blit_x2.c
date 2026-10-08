/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* hgr_blit_x2.c — draw a mono ×1 sprite doubled to ×2 in a chosen colour,
 * inflating ON THE FLY (no persistent buffer). The RAM-lean, cycle-costly twin of
 * the recommended inflate-once pattern (hgr_inflate_x2 at init + a byte-
 * aligned blit every frame): use this only when RAM is tighter than CPU time.
 *
 * Byte-aligned (it forwards to hgr_blit7), so honour the ×2 parity contract:
 * an EVEN byte column (x = 14*n) keeps the chosen hue; an odd one flips it
 * (Violet<->Green / Blue<->Orange). Needs CORE (blit7) + hgr_x2 (inflate). */

#include "hgr.h"
#include "hgr_host.h"

/* Scratch for the inflated ×2 sprite. Bounds the au-vol path to a 2*wbytes × 2*h
 * that fits HGR_X2_MAX_BYTES — a 16×16 (wbytes 3) doubles to 6×32 = 192. Bigger
 * sprites: inflate-once into your own buffer instead. */
static unsigned char gx2_buf[HGR_X2_MAX_BYTES];

void hgr_blit_x2(unsigned x, unsigned char y, const unsigned char *mono,
                      unsigned char wbytes, unsigned char h, unsigned char color,
                      unsigned char mode)
{
    /* Multiply the original dimensions before narrowing doubled dimensions.
     * Their product fits 16-bit unsigned even on cc65 (255*255 <= 65535).
     * Checking the quarter-buffer limit also bounds the doubled byte fields. */
    unsigned need = (unsigned)wbytes * (unsigned)h;
    if (need == 0u || need > HGR_X2_MAX_BYTES / 4u) return;
    hgr_inflate_x2(mono, wbytes, h, color, gx2_buf);
    hgr_blit7(x, y, (unsigned char)(wbytes << 1), (unsigned char)(h << 1),
                   gx2_buf, mode);
}
