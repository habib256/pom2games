/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
#ifndef DHGR_INTERNAL_H
#define DHGR_INTERNAL_H
#include "dhgr.h"
#include "hgr_layout.h"

/* Shared main-RAM parameters for the bank-safe assembly primitives.
 * Internal ABI: keep definitions in dhgr.c / dhgr_transfer_params.c. */
extern unsigned char *dhgr_addr;
extern unsigned char dhgr_aux, dhgr_mask, dhgr_bits;
extern unsigned char dhgr_base, dhgr_display, dhgr_pattern[4];
extern unsigned char dhgr_first, dhgr_last, dhgr_first_mask, dhgr_last_mask;
extern unsigned char *dhgr_buffer;
extern unsigned char dhgr_count;
extern const unsigned char *dhgr_sprite_mask;

/* Per color pixel: interleaved byte (4x)/7 and first dot (4x)%7 (dhgr_cells.s). */
extern const unsigned char dhgr_cellbyte[140], dhgr_cellphase[140];
/* dhgr_span_asm: dots span_x..span_end (clipped) on rows_y>>8 (>=1) rows
 * from rows_y&255, in dhgr_pattern. */
extern unsigned dhgr_span_x, dhgr_span_end;
/* dhgr_color_dot: color pixel dhgr_dot_x, y, pen dhgr_dot_color (0..15). */
extern unsigned char dhgr_dot_x, dhgr_dot_color;

void dhgr_clear_asm(void);
void __fastcall__ dhgr_span_asm(unsigned rows_y);
void __fastcall__ dhgr_color_dot(unsigned char y);
void dhgr_read_block_asm(void);
void dhgr_write_block_asm(void);
void dhgr_sprite_asm(void);
void dhgr_byte_address(unsigned char bx, unsigned char y);
void dhgr_prepare_pattern(unsigned char color);
void dhgr_bit_rect(unsigned x, unsigned char y, unsigned width,
                   unsigned char height);
#endif
