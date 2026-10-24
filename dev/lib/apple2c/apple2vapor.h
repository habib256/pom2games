/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* apple2vapor.h — vapor lock: frame sync through the floating bus (cc65).
 *
 * Link apple2vapor_asm.s (assembled with -I dev/lib/apple2): the same code as
 * ../apple2/vapor.asm. For a program showing HGR page 1 on a II, II+ or //e
 * (none of which has a VBL interrupt; the II and II+ have no VBL flag at all).
 *
 *     a2_vapor_mark();                 // after every clear of the page
 *     if (a2_vapor_sync() == 0) ...    // the beam is on line 191: VBL next
 *
 * The marker is $80 in the first 24 bytes of line 191 ($3FD0-$3FE7): black,
 * and the program must not draw there. No floating bus (//c, IIgs) or no
 * marker: a2_vapor_sync() returns 1 after ~0.8 s, so test it once and
 * fall back to another pace. */
#ifndef APPLE2VAPOR_H
#define APPLE2VAPOR_H

void a2_vapor_mark(void);
/* 0 = synced on line 191, 1 = no lock within ~0.8 s. */
unsigned char a2_vapor_sync(void);
/* One frame in 13-cycle polls (~1310 NTSC at 1 MHz, ~1560 PAL, more with an
 * accelerator), 0 when the lock fails. */
unsigned int a2_vapor_count(void);
#define A2_VAPOR_NTSC_COUNT 1310u

#endif /* APPLE2VAPOR_H */
