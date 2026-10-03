/* hgr_carrier.c — shared NTSC carrier selection.
 * One archive member: unused families add neither code nor zero-page state. */
#include "hgr.h"
#include "hgr_internal.h"

unsigned char hgr_set_carrier(unsigned char color)
{
    switch (color) {
        case HGR_GREEN:  hgr_z_ce = 0x2Au; hgr_z_co = 0x55u; hgr_z_hi = 0x00u; break;
        case HGR_ORANGE: hgr_z_ce = 0x2Au; hgr_z_co = 0x55u; hgr_z_hi = 0x80u; break;
        case HGR_BLUE:   hgr_z_ce = 0x55u; hgr_z_co = 0x2Au; hgr_z_hi = 0x80u; break;
        case HGR_VIOLET: hgr_z_ce = 0x55u; hgr_z_co = 0x2Au; hgr_z_hi = 0x00u; break;
        default: return 0u;                 /* unknown / white -> leave as drawn */
    }
    return 1u;
}
