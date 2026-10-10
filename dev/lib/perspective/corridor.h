/* GPL-3.0. Optional 6502 corridor projection, configured by corridor.asm. */
#ifndef A2_CORRIDOR_H
#define A2_CORRIDOR_H

/* Select two spans from caller-owned 256-byte tables. The table index is
 * min(distance >> PC_DEPTH_SHIFT, 255); shift defaults to one (two world
 * units per entry). Centers are build-time PC_CENTER_X/Y, default 128/80.
 * State is shared, non-reentrant; no clipping, allocation or video effects.
 * Main RAM/ZP, D=0, outside IRQs; caller IRQ mask is preserved.
 */
void __fastcall__ a2_corridor_select(unsigned distance);
unsigned char __fastcall__ a2_corridor_x(unsigned char x);
unsigned char __fastcall__ a2_corridor_y(unsigned char y);

/* Read-only to C callers after select. x/y input units are 0..127;
 * output = origin + floor(value * span / 128), with byte-sized results.
 * origin = center - floor(span/2). Tables must keep each projected axis
 * within 0..255. The module does not validate pointers or coordinates.
 */
extern unsigned char a2_corridor_sx, a2_corridor_sy;
extern unsigned char a2_corridor_left, a2_corridor_top, a2_corridor_depth;

#endif
