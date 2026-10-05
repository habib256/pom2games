/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* apple2c.h — umbrella header for the Apple II C base (dev/lib/apple2c).
 *
 * One include for an Apple II C program:
 *     #include "apple2c.h"
 *
 * Includes apple2io.h, apple2game.h (speaker,
 * joystick) and apple2dos.h (DOS commands); the last two need their own
 * object at link time (apple2c.mk). Pure preprocessor, zero bytes. */
#ifndef APPLE2C_H
#define APPLE2C_H

#include "apple2io.h"
#include "apple2frame.h" /* needs APPLE2C_FRAME_SRCS at link time */
#include "apple2game.h"  /* needs apple2game_asm.s at link time */
#include "apple2dos.h"   /* needs apple2dos_asm.s at link time  */

#endif /* APPLE2C_H */
