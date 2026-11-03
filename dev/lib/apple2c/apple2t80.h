/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* 80-column text written directly (apple2t80.s: APPLE2C_T80_SRCS), //e with
 * an 80-column card / //c, 65C02: 80STORE (even columns in aux through
 * PAGE2, odd ones in main), ALTCHARSET (inverse lower case, MouseText),
 * text page 1. Borrows cc65's ptr1/ptr2/tmp1/tmp2. Optional pointer
 * (apple2t80_ptr.s: APPLE2C_T80_PTR_SRCS, apple2t80.s assembled with
 * APPLE2C_T80_PTR_AFLAGS). */
#ifndef APPLE2T80_H
#define APPLE2T80_H

/* The cursor (column 0-79, row 0-23; nothing is written past column 79)
 * and the mode: T80_NORMAL, T80_INVERSE (@-_ and lower case inverse), T80_RAW
 * (the bytes are screen codes). */
extern unsigned char t80_x, t80_y, t80_mode;
#define T80_NORMAL 0
#define T80_INVERSE 1
#define T80_RAW 2
#define T80_AT(x, y) (t80_x = (x), t80_y = (y))

/* The 80-column text mode on, both halves cleared (not the screen holes),
 * mode T80_NORMAL (and the pointer off). */
void t80_init(void);
/* At (t80_x, t80_y), t80_x advanced up to 80. Strings and fills clip
 * at the right edge; further calls at column 80 leave the row unchanged. */
void __fastcall__ t80_putc(unsigned char c);
void __fastcall__ t80_puts(const char *s);
void __fastcall__ t80_fill(unsigned char c, unsigned char n);
/* Columns 0 .. 2 t80_sw + 1 (t80_sw 39 at first: all 80) of the t80_x
 * rows from t80_y one row up (down = 0: the last row keeps its text) or
 * down (the first one keeps it); t80_y is left moved. Zero or one row
 * is a no-op. The requested rows must fit within the 24-row text page. */
extern unsigned char t80_sw;
void __fastcall__ t80_scroll(unsigned char down);

/* apple2t80_ptr.s: the cell (t80_ptr_x, t80_ptr_y) shown inverse while
 * t80_ptr_on; move it between t80_ptr_hide and t80_ptr_show. */
extern unsigned char t80_ptr_x, t80_ptr_y, t80_ptr_on;
void t80_ptr_show(void);
void t80_ptr_hide(void);

#endif
