/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* MB TRACKER: shared declarations (song.c, files.c, main.c, mbt_asm.s). */
#ifndef MBT_H
#define MBT_H

/* ---- mbt_asm.s: sound (mb_irq.asm + aysong.asm, 50 Hz) ---- */
unsigned char snd_detect(void);      /* slot of the Mockingboard, 0 = none */
unsigned char snd_start(void);       /* the interrupt on: its number, 0 = failed */
void snd_shutdown(void);
void snd_play(void);                 /* ays_init(snd_song) [+ set_pos], gate on */
void snd_stop(void);                 /* gate off, voices off, chip 1 hushed */
void __fastcall__ snd_mute_set(unsigned char mask);
extern unsigned char snd_gate, snd_loop, snd_order0, snd_row0, snd_mute;
extern unsigned char *snd_song;
extern volatile unsigned char snd_ticks;
extern volatile unsigned char ays_order, ays_row, ays_play;

/* ---- mbt_asm.s: 80-column text ---- */
extern unsigned char txt_x, txt_y, txt_mode;   /* mode 0 normal, 1 inverse, 2 raw */
void txt_init(void);
void __fastcall__ txt_putc(unsigned char c);
void __fastcall__ txt_puts(const char *s);
void __fastcall__ txt_fill(unsigned char c, unsigned char n);
/* columns 0-39 of rows txt_y.. (txt_x rows) one row up (0) or down (1) */
void __fastcall__ txt_scroll(unsigned char down);
#define AT(x, y) (txt_x = (x), txt_y = (y))

/* ---- mbt_asm.s: keyboard, aux memory ---- */
unsigned char kbd_get(void);                   /* 7-bit key, 0 = none */
extern unsigned char *ax_main;
extern unsigned ax_aux, ax_len;
void aux_put(void);                            /* main -> aux */
void aux_get(void);                            /* aux -> main */

/* ---- song.c: the song being edited ---- */
#define MAXROWS 64
#define MAXVOICES 6
#define CELL 3                    /* note, ins | (fx + 1) << 4, param */
#define TRACK (MAXROWS * CELL)    /* 192 bytes a voice */
#define MAXINS 15
#define MAXTICKS 64
#define NOTE_EMPTY 0xFF
#define NOTE_OFF 96
#define NP_NONE 0xFF
#define SONGBUF_SIZE 0x3000

typedef struct {
    unsigned char n, loop, shape, eper;       /* ticks, loop tick, R13 ($FF none), R12 */
    unsigned char t[MAXTICKS];                /* %0ENTVVVV */
    unsigned char np[MAXTICKS];               /* noise period from this tick, NP_NONE */
    char name[16];
} Instrument;

extern unsigned char s_voices, s_rows, s_speed, s_rate, s_nord, s_loop, s_nins, s_npat;
extern unsigned char s_order[256];
extern Instrument s_ins[MAXINS];
extern char s_name[32], s_author[32];
/* the current pattern, then the encoder's scratch pattern (also the help
 * pages on their way from aux memory) */
extern unsigned char grid[2 * MAXVOICES * TRACK];
extern unsigned char cur_pat, grid_dirty;
extern unsigned char song_buf[SONGBUF_SIZE];   /* the AYS bytes */
extern unsigned song_len;                      /* valid encoded bytes, 0 = stale */

unsigned char max_patterns(void);
void song_new(void);
void ins_default(unsigned char i);
void pat_select(unsigned char p);              /* store the grid, fetch p */
void pat_flush(void);                          /* the grid back to aux */
unsigned char pat_new(unsigned char copy);     /* a new pattern (copy of the grid) */
unsigned song_encode(void);                    /* -> song_buf, length or 0 (too big) */
unsigned char song_decode(unsigned len);       /* song_buf -> the song; 0 = ok */
unsigned audition_encode(unsigned char *buf, unsigned char ins, unsigned char note);
#define CELLP(v, r) (grid + ((v) * MAXROWS + (r)) * CELL)

/* ---- files.c ---- */
#define MAXFILES 40
extern char file_names[MAXFILES][16];
extern unsigned char file_count;
extern char cur_file[16];
extern unsigned char file_iobuf[1024];         /* the OPEN buffer, $1000 */                      /* the song's file name */
unsigned char dir_list(void);                  /* .AYS names of the prefix; MLI error */
unsigned char file_load(const char *name);     /* 0 ok, MLI error, $FE bad song, $FD too big */
unsigned char file_save(const char *name);     /* 0 ok, MLI error, $FD too big */

#endif
