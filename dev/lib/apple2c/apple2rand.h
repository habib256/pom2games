/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* apple2rand.h — 16-bit pseudo-random numbers for Apple II C programs (cc65).
 *
 * Link apple2rand.s (APPLE2C_RAND_SRCS, assembled with -I dev/lib/apple2):
 * the Galois LFSR of ../math/random.asm (taps $B400, period 65535), the
 * same sequence as the asm programs' rand8 for the same seed.
 *
 *     a2_rand_state ^= key_timing;          // seed (never 0: it stays 0)
 *     if (!a2_rand_state) a2_rand_state = 0xACE1u;
 *     x = a2_rand16() % 35u;
 */
#ifndef APPLE2RAND_H
#define APPLE2RAND_H

/* One step: state >>= 1, then ^= 0xB400 if the bit shifted out was 1.
 * Returns the new state. */
unsigned int a2_rand16(void);
extern unsigned int a2_rand_state;      /* 0xACE1 at load */

#endif /* APPLE2RAND_H */
