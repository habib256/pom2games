/* Beautiful Boot 8x8 font: ASCII $20-$7F, shared by both text sizes.
 * Bit 0 is the leftmost pixel; bit 7 is blank. */
const unsigned char hgr_font[96u * 8u] = {
#include "hgr_bbfont.inc"
};
