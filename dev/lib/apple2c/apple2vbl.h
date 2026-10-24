/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Video clock for ProDOS games (apple2vbl.s, APPLE2C_VBL_SRCS): //e VBL
 * polling or the //c mouse firmware's VBL interrupt. Needs dev/lib/mouse
 * (mouse_init before a2_vbl_irq_init) and apple2frame.s. */
#ifndef APPLE2VBL_H
#define APPLE2VBL_H

#define A2_VBL_NONE 0u
#define A2_VBL_POLL 1u
#define A2_VBL_IRQ  2u

/* Mode, refreshes counted (modulo 256) and the last $C019 bit 7 (//e). */
extern unsigned char a2_vbl_mode, a2_vbl_count, a2_vbl_beam;
/* Called by the //c handler after each count (A/X/Y free, no ZP, no C
 * stack, C flag ignored); none while 0 (BSS). */
extern void *a2_vbl_hook;
/* //e with a VBL signal: A2_VBL_POLL, else A2_VBL_NONE (calls a2_frame_init). */
unsigned char a2_vbl_init(void);
/* Install the //c VBL interrupt: A2_VBL_IRQ, or A2_VBL_NONE (no mouse,
 * ALLOC_INTERRUPT refused). Enables interrupts. */
unsigned char a2_vbl_irq_init(void);
/* Back to A2_VBL_NONE, the interrupt (if any) removed. */
void a2_vbl_close(void);
/* //e: count a VBL edge. Call at most ~4 000 cycles apart while drawing. */
void a2_vbl_scan(void);

/* apple2vbl_pal.s (APPLE2C_VBL_PAL_SRCS): a2_vbl_pal = 1 on a 50 Hz
 * machine, after a2_vbl_measure (one or two frames; 0 without a clock). */
extern unsigned char a2_vbl_pal;
void a2_vbl_measure(void);

#endif
