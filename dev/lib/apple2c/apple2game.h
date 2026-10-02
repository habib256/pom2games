/* apple2game.h — speaker and joystick for Apple II C programs (cc65).
 *
 * Link apple2game_asm.s (assembled with -I dev/lib/apple2): the same code as
 * the asm modules ../apple2/sound.asm and ../apple2/joy.asm. */
#ifndef APPLE2GAME_H
#define APPLE2GAME_H

/* Square wave: `flips` speaker toggles (0 = 256), `period` delay between them
 * (0 = 256), ~(13 + 5*period) cycles per flip at 1.02 MHz. The CPU is busy
 * meanwhile. Examples: a2_tone(0x30, 0x28) short high blip, a2_tone(0x60,
 * 0xC0) ~95 ms at ~1 kHz, a2_tone(0x06, 0xFF) dull thud. */
void a2_tone(unsigned char flips, unsigned char period);

/* Sample both paddle timers (~6 ms), leave the counts in a2_joy_x / a2_joy_y
 * (0 = left/up, ~60 centred, ~120 = right/down) and return the direction:
 * the vertical axis wins a diagonal, dead zone 30..90. */
#define A2_JOY_NONE   0u
#define A2_JOY_UP     1u
#define A2_JOY_DOWN   2u
#define A2_JOY_LEFT   3u
#define A2_JOY_RIGHT  4u
unsigned char a2_read_stick(void);
extern unsigned char a2_joy_x, a2_joy_y;

/* Nonzero (0x80) while game-port button n (0, 1 or 2) is held. */
unsigned char a2_button(unsigned char n);

#endif /* APPLE2GAME_H */
