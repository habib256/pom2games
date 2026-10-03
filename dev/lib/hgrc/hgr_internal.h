/* Private declarations shared by the HGR C wrappers.
 * The assembler kernels own their per-family zero-page parameter blocks;
 * shared text/sprite/carrier blocks live in *_params.s. Each C declaration
 * needs a matching zpsym so cc65 uses zero-page addressing.
 * Lookup tables and draw-page state live in hgr_init.c.
 */
#ifndef HGR_INTERNAL_H
#define HGR_INTERNAL_H

extern const unsigned char hgr_font[96u * 8u];
unsigned char hgr_set_carrier(unsigned char color);

/* --- Zero-page parameter blocks (owned by the corresponding assembler kernels) -------------------- */
extern const unsigned char *hgr_g_glyph;
extern unsigned char hgr_g_col, hgr_g_mask, hgr_g_y;
extern void hgr_blit_glyph(void);
extern void hgr_blit_glyph_color(void);

extern unsigned char hgr_f_y0, hgr_f_rows, hgr_f_col0, hgr_f_cols, hgr_f_val;
extern void hgr_fill_rect_asm(void);

extern unsigned hgr_p_x;
extern unsigned char hgr_p_y;
extern void hgr_plot_asm(void);
extern void hgr_unplot_asm(void);

extern unsigned hgr_r_x, hgr_r_xr;
extern unsigned char hgr_r_y0, hgr_r_rows, hgr_r_mode;
extern void hgr_pixrect_asm(void);

/* hgr_cell parameter block (8x8-grid cell blitter, see hgr_rect.c). */
extern unsigned char hgr_c_cx, hgr_c_cy, hgr_c_set;
extern void hgr_cell_asm(void);

extern unsigned char hgr_z_col0, hgr_z_ncols, hgr_z_y0, hgr_z_rows;
extern unsigned char hgr_z_ce, hgr_z_co, hgr_z_hi;
extern void hgr_colorize_asm(void);

extern unsigned char hgr_t_col, hgr_t_bit, hgr_t_n, hgr_t_color;
extern const unsigned char *hgr_t_s;
extern const unsigned char *hgr_t_font;
extern void hgr_puts_run(void);
extern void hgr_puts_run8(void);

extern unsigned char hgr_u_lo, hgr_u_hi;
extern char *hgr_u_ptr;
extern void hgr_utoa(void);

extern unsigned char hgr_b_col, hgr_b_mask, hgr_b_w, hgr_b_h;
extern unsigned char hgr_b_stride, hgr_b_y, hgr_b_mode;
extern const unsigned char *hgr_b_src;
extern void hgr_blit_run(void);
extern void hgr_blit7_run(void);
extern void hgr_preshift_xor_run(void);   /* dedicated XOR fast path (no mode dispatch) */

/* hgr_sprite_xor's all-asm worker: the C entry only stores these zp args. */
extern unsigned hgr_xs_x;
extern unsigned char hgr_xs_y;
extern const hgr_sprite_t *hgr_xs_spr;
extern void hgr_xs_run(void);

/* Masked pre-shifted sprite kernels (hgr_sprmask.s -- the SPRMASK family).
 * The sprite engine (hgr_sprengine.c) only stores these zp args and JSRs. */
extern unsigned hgr_ms_x;
extern unsigned char hgr_ms_y;
extern const hgr_mspr_t *hgr_ms_spr;
extern unsigned char *hgr_ms_under;
extern void hgr_ms_run(void);          /* masked draw: dst = (dst & mask) | data */
extern void hgr_ms_save_run(void);     /* framebuffer rect -> under buffer       */
extern void hgr_ms_restore_run(void);  /* under buffer -> framebuffer rect       */
extern void hgr_msu_run(void);         /* save-under + masked draw, one pass     */

#pragma zpsym("hgr_g_glyph")
#pragma zpsym("hgr_g_col")
#pragma zpsym("hgr_g_mask")
#pragma zpsym("hgr_g_y")
#pragma zpsym("hgr_f_y0")
#pragma zpsym("hgr_f_rows")
#pragma zpsym("hgr_f_col0")
#pragma zpsym("hgr_f_cols")
#pragma zpsym("hgr_f_val")
#pragma zpsym("hgr_p_x")
#pragma zpsym("hgr_p_y")
#pragma zpsym("hgr_r_x")
#pragma zpsym("hgr_r_xr")
#pragma zpsym("hgr_r_y0")
#pragma zpsym("hgr_r_rows")
#pragma zpsym("hgr_r_mode")
#pragma zpsym("hgr_c_cx")
#pragma zpsym("hgr_c_cy")
#pragma zpsym("hgr_c_set")
#pragma zpsym("hgr_z_col0")
#pragma zpsym("hgr_z_ncols")
#pragma zpsym("hgr_z_y0")
#pragma zpsym("hgr_z_rows")
#pragma zpsym("hgr_z_ce")
#pragma zpsym("hgr_z_co")
#pragma zpsym("hgr_z_hi")
#pragma zpsym("hgr_t_col")
#pragma zpsym("hgr_t_bit")
#pragma zpsym("hgr_t_n")
#pragma zpsym("hgr_t_color")
#pragma zpsym("hgr_t_s")
#pragma zpsym("hgr_t_font")
#pragma zpsym("hgr_u_lo")
#pragma zpsym("hgr_u_hi")
#pragma zpsym("hgr_u_ptr")
#pragma zpsym("hgr_b_col")
#pragma zpsym("hgr_b_mask")
#pragma zpsym("hgr_b_w")
#pragma zpsym("hgr_b_h")
#pragma zpsym("hgr_b_stride")
#pragma zpsym("hgr_b_y")
#pragma zpsym("hgr_b_mode")
#pragma zpsym("hgr_b_src")
#pragma zpsym("hgr_xs_x")
#pragma zpsym("hgr_xs_y")
#pragma zpsym("hgr_xs_spr")
#pragma zpsym("hgr_ms_x")
#pragma zpsym("hgr_ms_y")
#pragma zpsym("hgr_ms_spr")
#pragma zpsym("hgr_ms_under")

/* --- Cross-module globals (defined in hgr_init.c) -------------------------- */
extern unsigned char hgr_rowlo[192];          /* HIRES scanline base low byte  */
extern unsigned char hgr_rowhi[192];          /* HIRES scanline base high byte */
extern unsigned char hgr_col7[280];           /* x / 7 (byte column)           */
extern unsigned char hgr_mask7[280];          /* 1 << (x % 7) (bit mask)       */
extern unsigned char hgr_phase7[280];         /* x % 7 (sub-byte phase 0..6)    */
extern unsigned char hgr_lo_rowlo[24];        /* LORES text-row base low byte  */
extern unsigned char hgr_lo_rowhi[24];        /* LORES text-row base high byte */
extern unsigned char hgr_lo_base;             /* LORES page base ($04 or $08;
                                                  BSS 0 = unset, lazy -> $04)  */
extern unsigned char hgr_lo_ready;            /* LORES tables built once       */

/* --- Cross-module helpers (defined in hgr_init.c) -------------------------- */
extern void hgr_build_tables(void);           /* idempotent table build        */

#endif /* HGR_INTERNAL_H */
