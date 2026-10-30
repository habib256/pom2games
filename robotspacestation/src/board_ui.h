/* Robot Space Station — the board editor (lab and drone inside). */
#ifndef BOARD_UI_H
#define BOARD_UI_H

#define PAL_Y 152u              /* palette: 5 gates x 12, 8 chips x 10 */
/* The drone's door, under the grid: walk there to get out. */
#define DOOR_X 62u
#define DOOR_Y 145u
#define DOOR_W 16u

enum { M_EDIT, M_BURN, M_OPEN, M_CLEAR };

extern unsigned char lab_inputs[4];
extern unsigned char mode, held_kind, held_part, held_src;

void board_draw(void);          /* clear the board area, draw it all */
void board_update(void);        /* after an edit: what changed, no clear */
void board_refresh(void);       /* after a tick: changed values only */
void board_recompile(void);
void board_palette(void);
void board_click(unsigned char x, unsigned char y);
void board_drop(void);
void board_clear_all(void);
/* main.c: write RSS.SAVE (1 = written). */
unsigned char board_saved(void);

#endif
