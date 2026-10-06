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

void dhgr_write_asm(void);
unsigned char dhgr_read_asm(void);
void dhgr_clear_asm(void);
void dhgr_span_asm(void);
void dhgr_read_block_asm(void);
void dhgr_write_block_asm(void);
void dhgr_sprite_asm(void);
void dhgr_byte_address(unsigned char bx, unsigned char y);
void dhgr_pixel_address(unsigned x, unsigned char y);
void dhgr_prepare_pattern(unsigned char color);
void dhgr_bit_rect(unsigned x, unsigned char y, unsigned width,
                   unsigned char height);
#endif
