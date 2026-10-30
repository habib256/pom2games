/* Robot Space Station — the title screen. */
#ifndef TITLE_H
#define TITLE_H

void title_draw(void);
/* The mission on screen row y if it may be played (won or next), or NONE. */
unsigned char __fastcall__ title_mission_at(unsigned char x, unsigned char y);
extern unsigned char title_page;        /* 0: missions 1-14, 1: 15-28 */

/* Page 0, the help: the terminals, the parts, the keys. Page 1, the
 * records: each mission won and its fewest gates (persist.best). */
void __fastcall__ help_draw(unsigned char page);

#define LEGEND_N 10u
extern const char *const legend_text[LEGEND_N];   /* help page 2 (HI) */

#endif
