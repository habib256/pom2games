/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* MB TRACKER: what the screens share (main.c, resident; insed.c and
 * fileui.c, the overlays MBT.OVL brings from aux memory). */
#ifndef UI_H
#define UI_H

#define K_LEFT 0x08
#define K_RIGHT 0x15
#define K_UP 0x0B
#define K_DOWN 0x0A
#define K_RET 0x0D
#define K_ESC 0x1B
#define K_TAB 0x09
#define K_DEL 0x7F
#define CTRL(c) ((c) & 0x1F)
/* mouse events (wait_key, event): the cell in ev_x, ev_y */
#define K_CLICK 0x80                /* the button pressed */
#define K_DRAG 0x81                 /* held, the pointer on another cell */
#define K_PAT 0x82                  /* the bar's PAT / ORD buttons */
#define K_ORD 0x83

#define GRID_Y 3
#define GRID_H 19
#define MSG_Y 22
#define KEYS_Y 23

#define RD_HEAD 1
#define RD_GRID 2
#define RD_ORDER 4
#define RD_INS 8
#define RD_MSG 16
#define RD_KEYS 32
#define RD_ALL 63

extern unsigned char slot, rd, screen, cur_ins, octave, modified, ev_x, ev_y;
extern char msg[80], line[81], input_buf[33];
extern const char hexd[];

void puts_at(unsigned char x, unsigned char y, const char *s);
void __fastcall__ clear_line(unsigned char y);
void hex2(char *d, unsigned char b);
void dec2(char *d, unsigned char b);
void __fastcall__ say(const char *s);
void touched(void);
void __fastcall__ blank(unsigned char n);
void redraw(void);
void full(void);
unsigned char wait_key(void);
unsigned char __fastcall__ ask(const char *q);
unsigned char input(const char *prompt, unsigned char max, unsigned char upper);
void audition(unsigned char ins, unsigned char note);
void stop(void);
void __fastcall__ ensure_ins(unsigned char i);
signed char __fastcall__ hexval(unsigned char k);
void help_page(unsigned char page, unsigned char x, unsigned char y);
void after_load(void);
void layout(void);
/* the segment of a key bar (" A B  C D  E": segments 0 1 2) at column x,
 * $FF on a gap */
unsigned char __fastcall__ seg_at(const char *bar, unsigned char x);

/* overlays */
void ins_editor(void);              /* OVL1 (insed.c) */
void load(void);                    /* OVL2 (fileui.c) */
void save(void);
void voices(void);                  /* OVL1 (voices.c) */

#endif
