/* Robot Space Station — boards, chips and the logic simulation.
 * Same rules and byte images as tools/model.py (docs/SPEC.md). */
#ifndef SIM_H
#define SIM_H

#define NONE 0xFFu
#define POWER 7u                /* source 7: the board's power, always 1 */
#define CHIP_POWER 0xFEu        /* the same inside a burned chip */
#define PARTS 16u
#define BOARD_GATES 64u
#define CHIP_GATES 32u
#define CHIPS 8u
#define TERMINALS 8u
#define LAYOUT_IDS 72u
#define LAYOUT_SIZE 120u

#define K_AND 1u
#define K_OR 2u
#define K_XOR 3u
#define K_NOT 4u
#define K_FLIP 5u
#define K_BUF 6u
#define K_CHIP0 8u

/* The edited layout: parts[i*3] = kind (0 = free), x, y; wires[sink] = source.
 * Layout ids: 0-7 terminals, 8 + part*4 + k pin k of a part. */
extern unsigned char parts[PARTS * 3u];
extern unsigned char wires[LAYOUT_IDS];

/* The compiled board (flat_bytes): flat ids 0-7 sources, 8+g gate g. */
extern unsigned char fl_count;
extern unsigned char fl_kind[BOARD_GATES], fl_a[BOARD_GATES], fl_b[BOARD_GATES];
extern unsigned char fl_sinks[TERMINALS];
extern unsigned char values[TERMINALS + BOARD_GATES];

/* What the save file RSS.SAVE holds, in low memory (LOWBSS): burned chips
 * (chip_bytes, planar), their editable layouts, the lab and drone boards
 * and the missions reached. tools/model.py save_bytes() has the same image. */
#define BEST_SLOTS 28u                  /* tools/model.py BEST_SLOTS */
typedef struct {
    char magic[4];                              /* "RSS3" ("RSS2": no best, "RSS1": no drone2) */
    unsigned char reached;                      /* missions won so far */
    unsigned char count[CHIPS];
    unsigned char kind[CHIPS][CHIP_GATES], a[CHIPS][CHIP_GATES], b[CHIPS][CHIP_GATES];
    unsigned char out[CHIPS][4];
    unsigned char layout[CHIPS][LAYOUT_SIZE];
    unsigned char lab[LAYOUT_SIZE], drone[LAYOUT_SIZE], drone2[LAYOUT_SIZE];
    unsigned char best[BEST_SLOTS];             /* fewest gates a mission was won with, + 1 (0: never) */
} Persist;
extern Persist persist;
#define chip_count persist.count
#define chip_kind persist.kind
#define chip_a persist.a
#define chip_b persist.b
#define chip_out persist.out
#define chip_layout persist.layout

unsigned char __fastcall__ part_inputs(unsigned char kind);
unsigned char __fastcall__ part_outputs(unsigned char kind);
/* First free slot, or NONE. */
unsigned char part_place(unsigned char kind, unsigned char x, unsigned char y);
void __fastcall__ part_remove(unsigned char i);
unsigned char part_at(unsigned char x, unsigned char y);
void board_clear(void);
/* 1 = compiled (values reset), 0 = over BOARD_GATES (nothing changed). */
unsigned char board_compile(void);
/* Burn the layout into chip c: 1 = done, 0 = over the gate limits. */
unsigned char __fastcall__ board_burn(unsigned char c);
/* One synchronous turn: values[0..7] already hold the sources. */
void board_tick(void);
unsigned char __fastcall__ sink_value(unsigned char k);
/* A second board (layout, compiled gates, values) kept aside: swap it
 * with the one above to edit or run the other drone. */
void board_swap(void);
/* Only what a turn needs (compiled gates, values): around board_tick(). */
void board_swap_run(void);
/* Value of a layout source id (after a compile). */
unsigned char __fastcall__ source_value(unsigned char s);

#endif
