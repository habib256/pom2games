/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Compatibility initializer for direct ASM users requiring every table. */
#include "hgr_internal.h"
void hgr_build_tables(void)
{
    hgr_build_rows();
    hgr_build_columns();
    hgr_build_masks();
    hgr_build_phases();
}
