/* VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root). */
/* Auxiliary memory of a 128 KB //e / //c, whole pages (apple2aux.s:
 * APPLE2C_AUX_SRCS, apple2auxfetch.s: APPLE2C_AUXFETCH_SRCS; both on
 * dev/lib/apple2/auxmem.asm, see dev/lib/apple2/README.md). Main RAMRD/RAMWRT
 * and 80STORE off on entry and exit; interrupts masked during each copy
 * (aux_store: all of it, aux_fetch_pages: one page at a time), the I flag
 * restored. Not for an IRQ handler. */
#ifndef APPLE2AUX_H
#define APPLE2AUX_H

/* aux_store's main source page ($20 at first: DHGR page 1, free before the
 * video starts). */
extern unsigned char aux_store_src;
/* pages | aux_page << 8: one argument in A/X, no C stack. */
void __fastcall__ aux_store_packed(unsigned pages_page);
/* Copy `pages` pages of main memory from page aux_store_src to aux page
 * aux_page (0 pages = 256). */
#define aux_store(pages, aux_page) \
    aux_store_packed((unsigned char)(pages) | ((unsigned)(aux_page) << 8))

/* Copy `pages` pages of aux memory from page aux_page to main page
 * main_page (16 ZEROPAGE bytes for the copy stub). */
void __fastcall__ aux_fetch_pages(unsigned char pages, unsigned char aux_page,
                                  unsigned char main_page);

#endif
