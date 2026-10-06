/* Shared screen geometry; generate_layout.py also emits the ASM constants. */
#ifndef CHROMA_LAYOUT_H
#define CHROMA_LAYOUT_H
#define CB_TILE_TOP 14
#define CB_GRID_END 106
#define CB_FIELD_TOP 11
#define CB_PAD_Y 184
/* The paddle rises to mid-field, and stays six lines below the bottom tile
 * row wherever a tile is above it (room for the attached ball). */
#define CB_PAD_MIN 100
#define CB_PAD_BLOCK 112
/* Level backgrounds cover the field above the paddle's highest line. */
#define CB_BG_END 100
#define CB_LOST_Y 187
#define CB_HUD_Y 1
/* Boards in the AUX level bank (src/levels.txt, tools/pack_levels.py). */
#define CB_LEVELS 60
/* HUD text cells: Beautiful Boot glyphs, two 7-dot units each. */
#define CB_HUD_COLS 37
#define CB_HUD_LEFT 3
#define CB_HUD_LIVES 13
#define CB_HUD_LEVEL 19
#define CB_HUD_MULT 24
#define CB_HUD_MESSAGE 27
#endif
