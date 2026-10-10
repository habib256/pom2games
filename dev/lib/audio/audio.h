/* GPL-3.0. Optional synchronous Apple II speaker samples. */
#ifndef A2_AUDIO_H
#define A2_AUDIO_H

/* Encoded by dev/tools/audio/pack_wav.py (fixed nominal 8000 Hz).
 * Main RAM/ZP, D=0, CPU at nominal 1 MHz. No accelerator detection.
 * Blocks until the $92 terminator, masking IRQs and restoring their mask.
 * Do not call from IRQs. No video/bank changes, no heap/BSS allocation.
 * Borrows cc65 ptr1, ptr3, ptr4 low byte and tmp3; not reentrant.
 * Source is immutable main RAM, includes a terminator, cannot wrap $FFFF.
 * Null is a no-op. Arbitrary/unencoded data is not a valid input.
 * Two 63-cycle PWM periods/sample: actual rate is CPU Hz / 126.
 */
void __fastcall__ a2_sample_play(const unsigned char *sample);

#endif
