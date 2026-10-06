/* VERHILLE Arnaud — GPL-3.0. AppleMouse II slot firmware, polling. */
#ifndef APPLEMOUSE_H
#define APPLEMOUSE_H
/* Main ROM/RAM/ZP, 80STORE off. IIe: preserves IRQ mask, requests no IRQs.
 * IIc: enables native ROM mouse interrupts (required for IOU motion).
 * Coordinates clamped to DHGR color space (0..139, 0..191).
 * No software cursor: the game paddle follows X. */
extern unsigned char mouse_slot, mouse_x, mouse_y, mouse_buttons;
unsigned char mouse_init(void); /* returns slot 1..7, or 0 */
void mouse_poll(void);          /* buttons: bit 7 = current primary button */
void mouse_close(void);
#endif
