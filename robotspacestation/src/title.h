/* Robot Space Station — the title screen. */
#ifndef TITLE_H
#define TITLE_H

void title_draw(void);
/* The mission on screen row y if it may be played (won or next), or NONE. */
unsigned char __fastcall__ title_mission_at(unsigned char y);

#endif
