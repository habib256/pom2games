/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Optional doubled, single-colour sprites for host C and cc65. */
#ifndef HGR_X2_H
#define HGR_X2_H
/* --- ×1 mono / ×2 chosen-colour sprites (Woz artifact vs doubled clock) -----
 * A HIRES sprite has no per-pixel colour. Two regimes from ONE compact master:
 *   ×1 — blit the mono bytes as-is (hgr_blit7 / hgr_sprite). Colour is
 *        a pure NTSC ARTIFACT: uncontrollable, parity-dependent, but compact.
 *   ×2 — DOUBLE the sprite so each source pixel spans a full NTSC colour clock
 *        (2 dots): light the even OR odd dot (+ the palette bit) so it reads as
 *        one CHOSEN hue instead of solid white. hgr_inflate_x2 bakes that
 *        from the mono master (store 48 B, inflate 192 B once at init, then blit);
 *        hgr_blit_x2 does it on the fly. Both mirror the POM1 HGR Sprite
 *        editor's ×2 export byte-for-byte.
 *
 * PARITY CONTRACT (×2): the sprite must land on an EVEN pixel column — byte-
 * aligned, an even byte column, x = 14*n — or the hue flips (Violet<->Green,
 * Blue<->Orange): HIRES colour is parity-locked. Move ×2 sprites in steps of 2 px
 * (pixel-precise paths) or 14 px (byte-aligned blit7).
 *
 * HGR_X2_* is one hue for the whole sprite; the order matches the editor's
 * HgrColor so the two inflates agree. HGR_X2_BLACK lights nothing (all-zero) —
 * for a black silhouette inflate HGR_X2_WHITE and blit HGR_CLEAR. */
#define HGR_X2_BLACK      0u
#define HGR_X2_WHITE      1u
#define HGR_X2_VIOLET     2u
#define HGR_X2_GREEN      3u
#define HGR_X2_BLUE       4u
#define HGR_X2_ORANGE     5u
#define HGR_X2_MAX_BYTES  256u   /* hgr_blit_x2 au-vol scratch cap (2*wb × 2*h) */

/* Inflate a mono ×1 sprite (wbytes×h, 7px/byte, bit 0 leftmost, bit 7 ignored)
 * into its ×2 single-colour form in caller-owned `out` (2*wbytes × 2*h bytes).
 * Do it ONCE at init, then blit `out` every frame. See the parity contract.
 * Source and output must not overlap; reserve 4*wbytes*h output bytes.
 * cc65 rejects output extents above 65535 bytes without writing. Zero
 * dimensions are a no-op. Main RAM, D=0, not callable from IRQ. */
void hgr_inflate_x2(const unsigned char *mono, unsigned char wbytes,
                         unsigned char h, unsigned char color, unsigned char *out);

/* Draw a mono ×1 sprite doubled to ×2 in `color` at (x, y), inflating on the fly
 * (no caller buffer; capped at HGR_X2_MAX_BYTES — bigger sprites use inflate-once).
 * Byte-aligned: keep x on an even byte column to hold the hue. HGR_SET/CLEAR/XOR. */
void hgr_blit_x2(unsigned x, unsigned char y, const unsigned char *mono,
                      unsigned char wbytes, unsigned char h, unsigned char color,
                      unsigned char mode);

#endif
