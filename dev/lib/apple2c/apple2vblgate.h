/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* At most one go a //e refresh (apple2vblgate.s: APPLE2C_VBL_GATE_SRCS),
 * e.g. the AppleMouse read once a frame: nonzero on the first call in the
 * vertical blank after a call in the picture, else 0. Call it more often
 * than the blank lasts (~4 500 cycles) to miss none. //e only ($C019; the
 * caller checks the model). a2_vbl_armed = 0: the next go only after a call
 * in the picture (a read just made without the gate). No zero page. */
#ifndef APPLE2VBLGATE_H
#define APPLE2VBLGATE_H

extern unsigned char a2_vbl_armed;
unsigned char a2_vbl_gate(void);

#endif
