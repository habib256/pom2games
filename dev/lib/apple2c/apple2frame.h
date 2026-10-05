/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Optional animation cadence. Link APPLE2C_FRAME_SRCS from apple2c.mk.
 * Requires main ROM/RAM and main zero page; not reentrant or IRQ-callable.
 * Init detects IIe VBLBAR; II/II+, IIc and IIgs use a delay without accessing
 * C019 or changing interrupt/video switches. Wait preserves the IRQ mask.
 */
#ifndef APPLE2FRAME_H
#define APPLE2FRAME_H

#define A2_FRAME_DELAY 0u
#define A2_FRAME_VBL   1u
#define A2_FRAME_DEFAULT_DELAY 80u

/* Reset default delay and detect the mode. Call once before animation.
 * IIe: C019 bit 7 is clear during VBL (Apple Technical Note IIGS #40).
 * IIc: C019 is a latched interrupt flag, so use the non-invasive fallback.
 * IIgs is explicitly excluded because its VBL polarity differs. */
unsigned char a2_frame_init(void);
unsigned char a2_frame_mode(void);
/* Set ROM WAIT argument (0 normalized to 1). Does not change selected mode.
 * WAIT(80) is about 17,093 CPU cycles (~16.7 ms at 1.02 MHz); drawing time is
 * ADDED to this delay. This is not a timer or an exact 60 Hz frame deadline.
 * Adjust for drawing cost, PAL displays and accelerator speed as needed. */
void __fastcall__ a2_frame_set_delay(unsigned char delay);
/* Wait for the NEXT IIe VBL edge, even when entered inside VBL. Both polling
 * phases are bounded; timeout permanently selects delay until next init.
 * Returns the actual mode used. Draw into a hidden page before waiting, then
 * flip promptly. On delay-only machines tearing remains possible. */
unsigned char a2_frame_wait(void);

#endif
