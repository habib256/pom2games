/* Robot Space Station — the title screen. */
#ifndef TITLE_H
#define TITLE_H

void title_draw(void);
/* The mission on screen row y if it may be played (won or next), or NONE. */
unsigned char __fastcall__ title_mission_at(unsigned char x, unsigned char y);
/* The same, locked missions included. */
unsigned char __fastcall__ title_row_at(unsigned char x, unsigned char y);
extern unsigned char title_page;        /* 0: missions 1-14, 1: 15-28 */

/* Pages 0-8 the help's texts (how to play, the electronics in six pages,
 * the lab and chips, the keys: tools/gen_text.py HELP), 9 the rooms'
 * legend; 10 the records: each mission won and its fewest gates
 * (persist.best). */
#define TEXT_PAGES 9u
#define GATES_PAGE 1u
#define LAB_PAGE 7u
#define LEGEND_PAGE 9u
#define HELP_PAGES 10u
#define RECORDS_PAGE 10u
void __fastcall__ help_draw(unsigned char page);

#endif
