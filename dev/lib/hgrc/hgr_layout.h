/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Shared scanline address for Apple II HGR and DHGR (y: 0..191).
 * base is the page high byte ($20 or $40). Arguments must have no side effects.
 * Keep the additions flat: cc65 generates smaller code than base+(offset).
 * (y >> 6) * 40 is written as two shifts so cc65 emits no multiply call.
 */
#ifndef HGR_LAYOUT_H
#define HGR_LAYOUT_H
#define HGR_ROW_ADDR(base, y) (((unsigned)(base) << 8) \
    + ((unsigned)((y) & 7) << 10) + ((unsigned)(((y) >> 3) & 7) << 7) \
    + ((unsigned)((y) >> 6) << 5) + ((unsigned)((y) >> 6) << 3))
#endif
