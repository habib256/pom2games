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

/* Buttons on row BTN_Y; button 0 reads MARCHE or PAUSE after `running`. */
void __fastcall__ buttons_set(const char *const *labels, unsigned char n);
void buttons_draw(void);
unsigned char __fastcall__ button_at(unsigned char x);

/* The technician: 5 x 9 color pixels with the background saved. */
#define ACT_W 5u
#define ACT_H 9u
extern unsigned char act_x, act_y;
void actor_show(void);
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
