/*
 * apple2io.c — small C layer over apple2io_asm.s. See apple2io.h.
 */
#include "apple2io.h"

void a2_puts(const unsigned char *s) {
    unsigned char c;
    while ((c = *s++) != 0) {
        a2_putc(c);
    }
}

void a2_print_hexword(unsigned w) {
    /* cc65 is little-endian: print the high byte first. */
    a2_print_hex(*((unsigned char *)&w + 1));
    a2_print_hex(*(unsigned char *)&w);
}
