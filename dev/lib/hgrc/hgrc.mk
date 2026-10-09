# VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
# Apple II HGR source families for cc65. Set HGRC and GFX before including.
# Build an ar65 archive from HGRC_ALL_SRCS: ld65 extracts only called families.
# The ASM_SRC list is shared because its members have independent code/ZP.
# Source families can also be selected for an archive; the assembly members
# below provide their common dependencies without forcing them into the binary.
HGRC_BUILD ?= $(BUILD)/hgrc
HGRC_LIB ?= $(HGRC_BUILD)/hgrc.lib

HGRC_ASM_SRCS := $(addprefix $(HGRC)/,hgr_mode_asm.s hgr_mode_clear_asm.s \
    hgr_lores_init_asm.s hgr_rows_asm.s hgr_clear_asm.s \
    hgr_text16_asm.s hgr_text8_asm.s hgr_text_params.s hgr_utoa_asm.s \
    hgr_byte_rect_asm.s hgr_pixrect_asm.s hgr_pixrect_params.s hgr_cell_asm.s \
    hgr_pixel_asm.s hgr_colorize_asm.s hgr_carrier_params.s \
    hgr_bitmap_asm.s hgr_blit7_asm.s hgr_preshift_asm.s hgr_sprite_params.s)
HGRC_CORE_SRCS := $(addprefix $(HGRC)/,hgr_state.c hgr_init.c hgr_draw_page.s hgr_row_page.s hgr_fixed_rows.s hgr_tables.c hgr_columns.s hgr_masks.s hgr_phases.s) $(HGRC_ASM_SRCS)
HGRC_PIXEL_SRCS := $(HGRC)/hgr_pixel.c
HGRC_RECT_SRCS := $(addprefix $(HGRC)/,hgr_rect.c hgr_pixrect.c hgr_cell.c \
    hgr_colorize.c hgr_carrier.c)
HGRC_TEXT_SRCS := $(addprefix $(HGRC)/,hgr_font.c hgr_text.c hgr_text8.c \
    hgr_num_unsigned.c hgr_num_field.c hgr_num_signed.c hgr_num_hex.c \
    hgr_num_small.c hgr_carrier.c hgr_hud.c hgr_hud_asm.s hgr_hud_putu.s \
    hgr_hud8.c hgr_hud8_asm.s hgr_hud8_putu.s hgr_hud8_digits.s)
HGRC_SPRITES_SRCS := $(HGRC)/hgr_sprites.c $(HGRC)/hgr_blit7.c
HGRC_PRESHIFT_SRCS := $(HGRC)/hgr_preshift.c
HGRC_SPRMASK_SRCS := $(HGRC)/hgr_sprmask.s
HGRC_SPRENGINE_SRCS := $(HGRC)/hgr_sprengine.c $(HGRC)/hgr_sprengine_asm.s $(HGRC)/hgr_sprdamage.s $(HGRC)/hgr_sprdefault.c
HGRC_GEOM_SRCS := $(addprefix $(HGRC)/,hgr_geom.c hgr_line.c hgr_outline.c \
    hgr_circle.c hgr_ellipse.c hgr_line_asm.s)
HGRC_LORES_SRCS := $(HGRC)/hgr_lores.c
HGRC_TILEMAP_SRCS := $(HGRC)/hgr_tilemap.c $(HGRC)/hgr_tile_restore.s
HGRC_NUM_SRCS := $(GFX)/gfx_num_hex.c $(GFX)/gfx_num_dec.c
HGRC_GFX_TEXT_SRCS := $(GFX)/gfx_text.c $(GFX)/gfx_text_backend_hgr.c
HGRC_GENERIC_VECTOR_SRCS := $(GFX)/gfx_line.c $(GFX)/gfx_rect.c
HGRC_VECTOR_SRCS := $(GFX)/gfx_line_hgr.c $(GFX)/gfx_rect.c
HGRC_BACKEND_SRCS := $(GFX)/gfx_backend_hgr.c $(GFX)/gfx_backend_hgr_rect.c
HGRC_GFX_SRCS := $(HGRC_VECTOR_SRCS) $(GFX)/gfx_circle.c $(GFX)/gfx_ellipse.c \
    $(HGRC_BACKEND_SRCS)

HGRC_ALL_SRCS := $(sort $(HGRC_CORE_SRCS) $(HGRC_PIXEL_SRCS) $(HGRC_RECT_SRCS) \
    $(HGRC_TEXT_SRCS) $(HGRC_SPRITES_SRCS) $(HGRC_PRESHIFT_SRCS) \
    $(HGRC_SPRMASK_SRCS) $(HGRC_SPRENGINE_SRCS) $(HGRC_GEOM_SRCS) \
    $(HGRC_LORES_SRCS) $(HGRC_TILEMAP_SRCS) $(HGRC_NUM_SRCS) $(HGRC_GFX_SRCS) $(HGRC_GFX_TEXT_SRCS))
HGRC_INCS := -I $(HGRC) -I $(GFX)
HGRC_AFLAGS := -I $(HGRC) -I $(HGRC)/../apple2
HGRC_HEADERS := $(wildcard $(HGRC)/*.h $(HGRC)/*.inc $(HGRC)/../font/*.inc $(GFX)/*.h)
HGRC_ASM_DEPS := $(wildcard $(HGRC)/*.inc $(HGRC)/../apple2/*.inc $(HGRC)/../apple2/*.asm)

# Host-only x2 reference: hgr_x2.c. No target inflation kernel is supplied.
# IIe/IIc DHGR stays opt-in, independent from HGR and gfx.
HGRC_DHGR_STATE_SRCS := $(HGRC)/dhgr.c $(HGRC)/dhgr_asm.s
HGRC_DHGR_PIXEL_SRCS := $(addprefix $(HGRC)/,dhgr_pixel.c dhgr_getpixel.c dhgr_pixel_address.c dhgr_access_asm.s dhgr_write_asm.s dhgr_read_asm.s)
HGRC_DHGR_CLEAR_SRCS := $(addprefix $(HGRC)/,dhgr_clear.c dhgr_pattern.c dhgr_clear_asm.s dhgr_clear_rows.c dhgr_clear_rows_asm.s)
HGRC_DHGR_FILL_SRCS := $(HGRC_DHGR_CLEAR_SRCS) $(addprefix $(HGRC)/,dhgr_fill.c dhgr_plot_color.c dhgr_fill_bits.c dhgr_bit_rect.c dhgr_span_asm.s)
HGRC_DHGR_TRANSFER_SRCS := $(addprefix $(HGRC)/,dhgr_address.c dhgr_block.c dhgr_sprite.c dhgr_transfer_params.c dhgr_block_asm.s)
HGRC_DHGR_CORE_SRCS := $(HGRC_DHGR_STATE_SRCS) $(HGRC_DHGR_PIXEL_SRCS) $(HGRC_DHGR_FILL_SRCS)
HGRC_DHGR_SRCS := $(sort $(HGRC_DHGR_CORE_SRCS) $(HGRC)/dhgr_span.c $(HGRC_DHGR_TRANSFER_SRCS) $(HGRC)/dhgr_text.c $(HGRC)/dhgr_text_asm.s $(HGRC)/dhgr_access_asm.s $(HGRC)/dhgr_write_asm.s $(HGRC)/hgr_font.c)
HGRC_DHGR_SMALL_TEXT_SRCS := $(HGRC)/dhgr_small.c $(HGRC)/dhgr_small_params.c $(HGRC)/dhgr_small_asm.s $(HGRC)/dhgr_small_string.s
HGRC_65C02_NUM_SRCS := $(GFX)/gfx_u16_digits.s
HGRC_DHGR_COLOR_BACKEND := $(GFX)/gfx_backend_dhgr_color.c
HGRC_DHGR_MONO_BACKEND := $(GFX)/gfx_backend_dhgr_mono.c

# Optional DHGR members are extracted only when referenced. gfx backends remain explicit.
HGRC_ALL_SRCS := $(sort $(HGRC_ALL_SRCS) $(HGRC_DHGR_SRCS) $(HGRC_DHGR_SMALL_TEXT_SRCS) $(HGRC_65C02_NUM_SRCS))
