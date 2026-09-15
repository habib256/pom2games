/* hello_c.c — smallest Apple II program on dev/lib/apple2c (C track).
 *
 * Text through COUT, a hex word, a key, then back to DOS by returning from
 * main() (crt0_apple2.s restores the zero page and warm-starts DOS).
 * On the disk: BRUN HELLOC. */
#include "apple2c.h"

void main(void)
{
    unsigned char k;

    a2_text();
    a2_home();
    puts_apple2("HELLO FROM THE APPLE II (C)\r");
    puts_apple2("A2_PRINT_HEXWORD(0x1234) = ");
    a2_print_hexword(0x1234u);
    a2_putc('\r');
    puts_apple2("PRESS A KEY: ");
    k = apple2_getkey();
    a2_putc(k);
    a2_putc('\r');
}
