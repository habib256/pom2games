/*
 * apple2io.h — Apple II text + keyboard I/O for C (cc65), graphics-neutral.
 *
 * The Apple II counterpart of POM1's dev/lib/apple1c/apple1io.h. Output goes
 * through the Monitor's COUT ($FDED) onto the text screen; input reads the
 * keyboard latch ($C000, cleared through $C010).
 *
 *   Apple-1 (apple1c)          Apple II (this lib)
 *   woz_putc(c)                a2_putc(c)          '\r' = new line
 *   woz_puts(s)                a2_puts(s)
 *   woz_print_hex(b)           a2_print_hex(b)
 *   woz_print_hexword(w)       a2_print_hexword(w)
 *   woz_mon()                  a2_dos()            back to the ']' prompt
 *   apple1_iskeypressed()      apple2_iskeypressed()
 *   apple1_getkey()            apple2_getkey()
 *   apple1_readkey()           apple2_readkey()
 *   —                          a2_home(), a2_text()
 *
 * Differences that matter:
 *   - One screen: text printed while a graphics mode is shown lands on the
 *     text page and becomes visible after a2_text().
 *   - Keys are folded to upper case (a //e or a host keyboard sends lower
 *     case); the arrows arrive as control codes (KC_LEFT ...).
 *   - a2_dos() needs dev/cc65/crt0_apple2.s, whose _exit restores the zero
 *     page it saved at startup before jumping to DOS. Returning from main()
 *     does the same.
 *   - COUT uses the Monitor zero page ($20-$4F); dev/cc65/apple2_hgr_c.cfg
 *     keeps the C runtime's zero page at $50+.
 */
#ifndef APPLE2IO_H
#define APPLE2IO_H

#define A2_COUT     0xFDEDU   /* Monitor character output (A | $80)          */
#define A2_PRBYTE   0xFDDAU   /* Monitor: print A as two hex digits          */
#define A2_HOME     0xFC58U   /* Monitor: clear the text window              */
#define A2_DOSWARM  0x03D0U   /* DOS 3.3 warm start (']' prompt)             */
#define A2_KBD      0xC000U   /* keyboard latch: bit 7 = key ready           */
#define A2_KBDSTRB  0xC010U   /* any access clears the strobe                */

/* 7-bit key codes returned by apple2_getkey / apple2_readkey. */
#define KC_LEFT   0x08        /* left arrow                                   */
#define KC_RIGHT  0x15        /* right arrow                                  */
#define KC_UP     0x0B        /* up arrow (//e; Ctrl-K on a II+)              */
#define KC_DOWN   0x0A        /* down arrow (//e; Ctrl-J on a II+)            */
#define KC_RET    0x0D
#define KC_ESC    0x1B

/* ---- Output (text screen, via COUT) ---- */
void a2_putc(unsigned char c);           /* print one character                */
void a2_puts(const unsigned char *s);    /* print a NUL-terminated string       */
void a2_print_hex(unsigned char c);      /* print a byte as two hex digits      */
void a2_print_hexword(unsigned w);       /* print a 16-bit word as four digits  */
void a2_home(void);                      /* clear the text screen               */
void a2_text(void);                      /* TEXT + full screen + page 1         */
void a2_dos(void);                       /* restore ZP, back to DOS (no return) */
void a2_wait(unsigned char a);           /* Monitor WAIT: ~(26+27a+5a*a)/2 cycles */
#define A2_WAIT_FRAME 80u                /* a2_wait(80) ~ 17 000 cycles = 1 frame */

/* ---- Keyboard ($C000 latch / $C010 strobe) ---- */
unsigned char apple2_iskeypressed(void); /* nonzero (bit 7) if a key is waiting */
unsigned char apple2_getkey(void);       /* block until a key, key & 0x7F       */
unsigned char apple2_readkey(void);      /* 0 if no key, else key & 0x7F        */

/* Zero-cost conveniences (no cast needed for string literals). */
#define puts_apple2(s)     a2_puts((const unsigned char *)(s))
#define println_apple2(s)  do { a2_puts((const unsigned char *)(s)); a2_putc('\r'); } while (0)
#define getchar_apple2()   ((char)apple2_getkey())

#endif /* APPLE2IO_H */
