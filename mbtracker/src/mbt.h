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

/* ---- dev/lib/apple2c apple2t80.s: 80-column text; apple2t80_ptr.s: the
 * mouse pointer (a cell shown inverse / normal; the text routines draw
 * under it: apple2t80.s assembled with T80_PTR=1) ---- */
#include "apple2t80.h"
#define AT(x, y) T80_AT(x, y)
/* t80_scroll: the grid's columns (t80_sw: main.c layout()) */

/* ---- mbt_asm.s: mouse helpers ---- */
void mouse_read(void);                         /* mouse_poll with 80STORE off */

/* ---- mbt_asm.s: keyboard, aux memory ---- */
unsigned char kbd_get(void);                   /* 7-bit key, 0 = none */
extern unsigned char *ax_main;
extern unsigned ax_aux, ax_len;
void aux_put(void);                            /* main -> aux */
void aux_get(void);                            /* aux -> main */
void lc_put(void);                             /* main -> the aux LC, bank 1 */
void lc_get(void);                             /* the aux LC -> main */

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
void __fastcall__ song_new(unsigned char voices);
void ins_default(unsigned char i);
void pat_select(unsigned char p);              /* store the grid, fetch p */
void pat_flush(void);                          /* the grid back to aux */
unsigned char pat_new(unsigned char copy);     /* a new pattern (copy of the grid) */
void __fastcall__ pat_delete(unsigned char p); /* the pattern out, the next ones down */
/* OVL1: voices 4-6 not empty; the song 3 <-> 6 voices (main.c's ^W) */
unsigned char song_hi_used(void);
void song_voices(void);
unsigned song_encode(void);                    /* -> song_buf, length or 0 (too big) */
unsigned char song_decode(unsigned len);       /* song_buf -> the song; 0 = ok */
unsigned audition_encode(unsigned char *buf, unsigned char ins, unsigned char note);
#define CELLP(v, r) (grid + ((v) * MAXROWS + (r)) * CELL)
#define scratch (grid + MAXVOICES * TRACK)

/* aux memory (/RAM disconnected): the patterns $0800-$97FF, the help
 * pages, the block clipboard, the undo pattern; in the aux language card
 * (bank 1, lc_put / lc_get) the overlays (MBT.OVL) */
#define AUX_PATTERNS 0x0800u
#define AUX_HELP 0x9800u
#define HELP_MAX 0x0C00u
#define AUX_CLIP (AUX_HELP + HELP_MAX)
#define AUX_UNDO (AUX_CLIP + MAXVOICES * TRACK)
#define LC_OVL 0xD000u
#define OVL_SIZE 0x1110u                       /* src/mbt.cfg: OVL1, OVL2 */
#define OVL_RUN (0x8E00u - OVL_SIZE)

/* ---- files.c ---- */
#define MAXFILES 40
/* the names of the load screen: the encoder's scratch pattern (free there) */
#define file_names ((char (*)[16])scratch)
extern char cur_file[16];                      /* the song's file name */
extern unsigned char file_iobuf[1024];         /* the OPEN buffer, $1000 */
/* .AYS names of the prefix (dev/lib/prodos dir.c, in OVL2); MLI error */
#define file_count prodos_dir_count
#define dir_list() (prodos_file_iobuf = file_iobuf, \
                    prodos_dir_list((char *)file_names, 16, MAXFILES, ".AYS"))
unsigned char file_load(const char *name);     /* 0 ok, MLI error, $FE bad song, $FD too big */
unsigned char file_save(const char *name);     /* 0 ok, MLI error, $FD too big */

#endif
