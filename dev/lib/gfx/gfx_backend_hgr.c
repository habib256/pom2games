/* gfx_backend_hgr.c — Apple II HGR backend for shared geometry.
 * Span primitives use the HGR rectangle fast paths. Fill/clear forwarders
 * are separate so archive links can omit them when unused.
 */
#include "gfx.h"
/* The backend needs hgr_* prototypes only — skip hgr.h's apple2c
 * include so this TU compiles without -I dev/lib/apple2c. */
#define HGR_NO_APPLE2
#include "hgr.h"          /* -I dev/lib/hgrc */

const unsigned      gfx_width  = 280u;
const unsigned char gfx_height = 192u;

void gfx_plot(unsigned x, unsigned char y)                 { hgr_plot(x, y); }
void gfx_hline(unsigned x0, unsigned x1, unsigned char y)  { hgr_hline(x0, x1, y); }
void gfx_vline(unsigned x, unsigned char y0, unsigned char y1) { hgr_vline(x, y0, y1); }

/* gfx_filled_rect + gfx_clear forwarders live in gfx_backend_hgr_rect.c so
 * the dead-strip is symmetric with the TMS side: a hgr program that never
 * calls them won't drag hgr_fill_pixrect / hgr_clear in. */
