# VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
# Apple II HGR source families for cc65. Set HGRC and GFX before including.
# Build an ar65 archive from HGRC_ALL_SRCS: ld65 extracts only called families.
# The ASM_SRC list is shared because its members have independent code/ZP.
# Source families can also be selected for an archive; the assembly members
# below provide their common dependencies without forcing them into the binary.
HGRC_BUILD ?= $(BUILD)/hgrc
HGRC_LIB ?= $(HGRC_BUILD)/hgrc.lib

HGRC_ASM_SRCS := $(addprefix $(HGRC)/,hgr_mode_asm.s hgr_mode_clear_asm.s \
    hgr_lores_init_asm.s hgr_native_asm.s hgr_rows_asm.s hgr_clear_asm.s \
    hgr_text16_asm.s hgr_text8_asm.s hgr_text_params.s hgr_text_addr.s hgr_glyph_params.s hgr_utoa_asm.s \
    hgr_byte_rect_asm.s hgr_pixrect_asm.s hgr_pixrect_params.s hgr_fill_span.s hgr_cell_asm.s \
    hgr_pixel_asm.s hgr_colorize_asm.s hgr_carrier_params.s \
    hgr_bitmap_asm.s hgr_blit7_asm.s hgr_preshift_asm.s hgr_sprite_params.s \
    hgr_glyph_shift.s)
HGRC_CORE_SRCS := $(addprefix $(HGRC)/,hgr_state.c hgr_set_draw_page.s hgr_lores_state.s hgr_build_rows.s hgr_row.s hgr_show_page.s hgr_draw_page.s hgr_row_page.s hgr_fixed_rows.s hgr_tables.c hgr_columns.s hgr_masks.s hgr_phases.s) $(HGRC_ASM_SRCS)
HGRC_PIXEL_SRCS := $(HGRC)/hgr_pixel_asm.s
HGRC_RECT_SRCS := $(addprefix $(HGRC)/,hgr_rect.s hgr_pixrect.s hgr_cell.s \
    hgr_colorize.s hgr_carrier.s)
HGRC_TEXT_SRCS := $(addprefix $(HGRC)/,hgr_font.c hgr_text.s hgr_text8.s hgr_text_cells.s \
    hgr_num_unsigned.s hgr_num_field.s hgr_num_signed.s hgr_num_hex.s \
    hgr_num_small.s hgr_num_prepare.s hgr_carrier.s hgr_hud.s hgr_hud_init.s hgr_hud_asm.s hgr_hud_putu.s \
    hgr_hud8.s hgr_hud8_asm.s hgr_hud8_putu.s hgr_hud8_digits.s \
    hgr_hud_invalidate.s)
HGRC_SPRITES_SRCS := $(HGRC)/hgr_sprites.s $(HGRC)/hgr_blit7.s
HGRC_PRESHIFT_SRCS := $(addprefix $(HGRC)/,hgr_preshift.s hgr_preshift_xor.s hgr_preshift_validate.s)
HGRC_X2_SRCS := $(HGRC)/hgr_x2_target.s $(HGRC)/hgr_inflate_x2_asm.s $(HGRC)/hgr_blit_x2.s
HGRC_SPRMASK_SRCS := $(HGRC)/hgr_sprmask.s
HGRC_SPRENGINE_SRCS := $(HGRC)/hgr_sprengine.c $(HGRC)/hgr_sprengine_asm.s $(HGRC)/hgr_sprdamage.s $(HGRC)/hgr_sprdefault.c
HGRC_GEOM_SRCS := $(addprefix $(HGRC)/,hgr_hline.s hgr_vline.s hgr_line.s hgr_outline.s \
    hgr_circle.s hgr_ellipse.s hgr_line_asm.s)
HGRC_LORES_SRCS := $(addprefix $(HGRC)/,hgr_lores.s hgr_lores_cell.s hgr_lores_clear.s hgr_lores_setblock.s \
    hgr_lores_getblock.s hgr_lores_hlin.s hgr_lores_vlin.s hgr_lores_rect.s hgr_lores_draw.s)
HGRC_TILEMAP_SRCS := $(HGRC)/hgr_tilemap.s $(HGRC)/hgr_tile_restore.s
HGRC_NUM_SRCS := $(GFX)/gfx_num_hex.s $(GFX)/gfx_num_dec.s $(GFX)/gfx_num_signed.s
HGRC_GFX_TEXT_SRCS := $(addprefix $(GFX)/,gfx_cursor_state.s gfx_gotoxy.s gfx_putc.s gfx_text.s gfx_text_backend_hgr.s \
    gfx_cell_glyph_hgr.s gfx_cell_color_hgr.s \
    gfx_putu.s gfx_puti.s gfx_putx.s)
HGRC_GENERIC_VECTOR_SRCS := $(GFX)/gfx_line.c $(GFX)/gfx_rect.s
HGRC_VECTOR_SRCS := $(GFX)/gfx_line_hgr.s $(GFX)/gfx_rect.s
HGRC_BACKEND_SRCS := $(addprefix $(GFX)/,gfx_backend_hgr.s gfx_backend_hgr_plot.s \
    gfx_backend_hgr_hline.s gfx_backend_hgr_vline.s gfx_backend_hgr_rect.s gfx_backend_hgr_clear.s)
HGRC_GFX_SRCS := $(HGRC_VECTOR_SRCS) $(GFX)/gfx_circle.c $(GFX)/gfx_ellipse.c \
    $(HGRC_BACKEND_SRCS)

HGRC_ALL_SRCS := $(sort $(HGRC_CORE_SRCS) $(HGRC_PIXEL_SRCS) $(HGRC_RECT_SRCS) \
    $(HGRC_TEXT_SRCS) $(HGRC_SPRITES_SRCS) $(HGRC_PRESHIFT_SRCS) $(HGRC_X2_SRCS) \
    $(HGRC_SPRMASK_SRCS) $(HGRC_SPRENGINE_SRCS) $(HGRC_GEOM_SRCS) \
    $(HGRC_LORES_SRCS) $(HGRC_TILEMAP_SRCS) $(HGRC_NUM_SRCS) $(HGRC_GFX_SRCS) $(HGRC_GFX_TEXT_SRCS))
HGRC_INCS := -I $(HGRC) -I $(GFX)
HGRC_AFLAGS := -I $(HGRC) -I $(HGRC)/../apple2
HGRC_HEADERS := $(wildcard $(HGRC)/*.h $(HGRC)/*.inc $(HGRC)/../font/*.inc $(HGRC)/../apple2c/*.h $(GFX)/*.h)
HGRC_ASM_DEPS := $(wildcard $(HGRC)/*.inc $(HGRC)/../apple2/*.inc $(HGRC)/../apple2/*.asm)

# X2 C references: hgr_x2.c (host), hgr_x2_target.c (cc65); native members above.
# IIe/IIc DHGR stays opt-in, independent from HGR and gfx.
HGRC_DHGR_STATE_SRCS := $(HGRC)/dhgr_state.c $(HGRC)/dhgr_draw_page.s $(HGRC)/dhgr_get_draw_page.s $(HGRC)/dhgr_get_display_page.s $(HGRC)/dhgr_flip.s $(HGRC)/dhgr_asm.s
HGRC_DHGR_TABLE_SRCS := $(HGRC)/dhgr_rows.s $(HGRC)/dhgr_cells.s
HGRC_DHGR_PIXEL_SRCS := $(addprefix $(HGRC)/,dhgr_pixel_asm.s dhgr_getpixel_asm.s dhgr_locate.s) $(HGRC_DHGR_TABLE_SRCS)
HGRC_DHGR_CLEAR_SRCS := $(addprefix $(HGRC)/,dhgr_clear.s dhgr_pattern_asm.s dhgr_clear_asm.s dhgr_clear_rows.s dhgr_clear_rows_asm.s dhgr_rows.s)
HGRC_DHGR_FILL_SRCS := $(sort $(HGRC_DHGR_CLEAR_SRCS) $(addprefix $(HGRC)/,dhgr_fill.s dhgr_plot_color_asm.s dhgr_color_state.s dhgr_fill_bits.s dhgr_bit_rect.s dhgr_span_asm.s) $(HGRC_DHGR_TABLE_SRCS))
HGRC_DHGR_TRANSFER_SRCS := $(addprefix $(HGRC)/,dhgr_address_asm.s dhgr_block.s dhgr_read_block.s dhgr_write_block.s dhgr_sprite.s dhgr_transfer_params.c dhgr_block_asm.s) $(HGRC_DHGR_TABLE_SRCS)
HGRC_DHGR_CORE_SRCS := $(sort $(HGRC_DHGR_STATE_SRCS) $(HGRC_DHGR_PIXEL_SRCS) $(HGRC_DHGR_FILL_SRCS))
HGRC_DHGR_SRCS := $(sort $(HGRC_DHGR_CORE_SRCS) $(HGRC)/dhgr_hline.s $(HGRC)/dhgr_vline.s $(HGRC_DHGR_TRANSFER_SRCS) $(HGRC)/dhgr_text_asm.s $(HGRC)/hgr_font.c)
HGRC_DHGR_SMALL_TEXT_SRCS := $(HGRC)/dhgr_small.s $(HGRC)/dhgr_small_params.c $(HGRC)/dhgr_small_asm.s $(HGRC)/dhgr_small_string.s
HGRC_65C02_NUM_SRCS := $(GFX)/gfx_u16_digits.s
HGRC_DHGR_COLOR_BACKEND := $(addprefix $(GFX)/,gfx_backend_dhgr_color.s \
    gfx_backend_dhgr_color_set_color.s gfx_backend_dhgr_color_plot.s \
    gfx_backend_dhgr_color_hline.s gfx_backend_dhgr_color_vline.s \
    gfx_backend_dhgr_color_rect.s gfx_backend_dhgr_color_clear.s)
HGRC_DHGR_MONO_BACKEND := $(addprefix $(GFX)/,gfx_backend_dhgr_mono.s \
    gfx_backend_dhgr_mono_state.s gfx_backend_dhgr_mono_set_color.s \
    gfx_backend_dhgr_mono_plot.s gfx_backend_dhgr_mono_hline.s \
    gfx_backend_dhgr_mono_vline.s gfx_backend_dhgr_mono_rect.s gfx_backend_dhgr_mono_clear.s)

# Flicker-free DHGR sprite compositor (dhgr.h dhgr_spr_*, dhgr_cursor): opt-in,
# NOT in HGRC_ALL_SRCS, so programs that do not ask for it keep the same
# archive members. Add it to HGRC_EXTRA_SRCS (or to a program's own library
# sources) with HGRC_DHGR_SRCS; members are extracted when referenced
# (palette, area, cells/tiles backgrounds, bitmap shapes, overlay, save-under
# cursor are separate). dhgr_spr_present.s (DHGR_SPR_DOUBLE) and the
# DHGR_SPR_VBL update import dev/lib/apple2c/apple2vbl (APPLE2C_VBL_SRCS).
HGRC_DHGR_SPR_SRCS := $(addprefix $(HGRC)/,dhgr_spr_api.s dhgr_spr_palette.s dhgr_spr_area.s dhgr_spr_update.s dhgr_spr_asm.s \
    dhgr_cv_asm.s dhgr_cv_bitmap.s dhgr_spr_cells.s dhgr_spr_overlay.s dhgr_spr_cursor.s \
    dhgr_spr_present.s)

# Optional DHGR members are extracted only when referenced. gfx backends remain explicit.
HGRC_ALL_SRCS := $(sort $(HGRC_ALL_SRCS) $(HGRC_DHGR_SRCS) $(HGRC_DHGR_SMALL_TEXT_SRCS) $(HGRC_65C02_NUM_SRCS))
