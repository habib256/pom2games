/* Robot Space Station — pointer, input, messages, buttons and the
 * technician's sprite. Draw only with the pointer hidden (hide/show): it is
 * drawn by inverting pixels. The sprite saves what it covers; hide it too
 * before drawing under it. */
#ifndef UI_H
#define UI_H

#define S_LAB 0u
#define S_ZONE 1u
#define S_DRONE 2u
#define S_TITLE 3u
#define S_HELP 4u                      /* the title's help page */
#define S_BRIEF 5u                     /* a mission's briefing and hints */

#define BOARD_TOP 10u
#define BTN_Y 165u
#define MSG_Y 181u

extern unsigned char screen, running;
extern unsigned char cur_drone;        /* the drone whose board is loaded (0 = A) */
extern unsigned char px, py;          /* pointer, color pixels */
extern unsigned char pressed, key;    /* this frame: a click, a key (upper case) */
extern unsigned char moved;           /* the pointer moved in this ui_poll() */

void ui_poll(void);
/* During a long drawing: remember a mouse click for the next ui_poll(). */
void ui_latch(void);
/* Clear the whole screen in strips, latching clicks between them. */
void screen_clear(void);
void hide(void);
void show(void);
void __fastcall__ message(const char *s);

/* The text bank (tools/gen_text.py, src/text.s): ids T_... in text.h. */
#include "text.h"
extern char text_buf[32];
/* At boot, before dhgr_init: pages (low byte) from main $2000 to aux (high byte). */
void __fastcall__ text_store(unsigned pages_page);
void __fastcall__ text_open(unsigned char id);
unsigned char text_line(void);          /* into text_buf; 1: another line follows */
void __fastcall__ msg(unsigned char id);              /* on the message line */
/* Text id's lines from page_x, page_y down, 9 pixels apart; page_y ends
 * below the last one. */
extern unsigned char page_x, page_y;
void __fastcall__ text_page(unsigned char id);
/* Its first line at x, y. */
void __fastcall__ text_at(unsigned char id, unsigned char x, unsigned char y);

/* Buttons on row BTN_Y; button 0 reads MARCHE or PAUSE after `running`.
 * tips: each button's text id, shown while the pointer is over it. */
void __fastcall__ buttons_set(const char *const *labels, const unsigned char *tips, unsigned char n);
void buttons_draw(void);
unsigned char __fastcall__ button_at(unsigned char x);
extern const unsigned char *btn_tip;

/* The message line follows the pointer (src/hover.c): what it is over, or
 * else what to do next. hover_force: show it on the next loop even if the
 * pointer stays (a new screen). */
extern unsigned char hover_force, hover_sync;
/* The main loop: 1 if the line must change, then hover_draw(). */
unsigned char hover_poll(void);
void hover_draw(void);

/* The technician: 5 x 9 color pixels with the background saved. */
#define ACT_W 5u
#define ACT_H 9u
extern unsigned char act_x, act_y;
void actor_show(void);
/* src/sprites.c: the technician in profile at x, y (facing his last walk). */
void __fastcall__ tech_paint(unsigned char x, unsigned char y);
void actor_hide(void);
/* Before drawing: pointer and technician off (the loop puts them back). */
void begin_draw(void);
/* The same, only for what overlaps the screen box x0..x1, y0..y1. */
void begin_draw_box(unsigned char x0, unsigned char y0, unsigned char x1, unsigned char y1);

/* Sound effects on the speaker (S toggles them; sfx_count: tests). */
#define SFX_CONTACT 0u                 /* a sensor touches */
#define SFX_GRAB 1u                    /* the claw takes */
#define SFX_DROP 2u                    /* and lets go */
#define SFX_RADIO 3u                   /* a drone starts sending */
#define SFX_BURN 4u                    /* a chip burned */
#define SFX_WIN 5u                     /* mission accomplished (three notes) */
extern unsigned char sound_on, sfx_count;
void __fastcall__ sfx(unsigned char n);

#endif
