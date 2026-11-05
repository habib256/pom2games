#!/usr/bin/env python3
"""Measure real cc65 calls (including argument setup), linker code/RAM/ZP.

HGR runs on portable a2run (NMOS); DHGR on a2shot --iie (65C02).
Use --check for regression gates, --update to intentionally accept a baseline.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import re
import sys
import tempfile
from functools import lru_cache
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from test_hgr import DEV, ROOT, build, run, a2test

CASES={
 'hgr_clear': ('hgr_clear(0);',False),
 'hgr_span': ('hgr_hline(0,279,40);',False),
 'hgr_rect': ('hgr_fill_pixrect(7,32,140,16);',False),
 'hgr_rect_clear': ('hgr_clear_pixrect(7,32,140,16);',False),
 'hgr_rect_single': ('hgr_fill_pixrect(2,32,3,16);',False),
 'hgr_rect_single_clear': ('hgr_clear_pixrect(2,32,3,16);',False),
 'hgr_rect_edges': ('hgr_fill_pixrect(6,32,2,16);',False),
 'hgr_rect_clip': ('hgr_fill_pixrect(255,190,255,255);',False),
 'hgr_cell': ('hgr_cell(1,4,1);',False),
 'hgr_byte_rect': ('hgr_fill_rect(32,16,0,40,0x7F);',False),
 'hgr_byte_rect_odd': ('hgr_fill_rect(32,16,1,39,0xD5);',False),
 'hgr_byte_rect_single': ('hgr_fill_rect(191,1,39,1,0x80);',False),
 'hgr_byte_rect_clip': ('hgr_fill_rect(190,255,38,255,0xA5);',False),
 'hgr_text': ('hgr_puts8(0,0,"APPLE II");',False),
 'hgr_text8_phase3': ('hgr_puts8(3,0,"APPLE II");',False),
 'hgr_text8_phase6': ('hgr_puts8(6,0,"APPLE II");',False),
 'hgr_text8_spaces': ('hgr_puts8(0,0,"        ");',False),
 'hgr_text_color': ('hgr_puts_color(0,0,"APPLE II",HGR_ORANGE);',False),
 'hgr_text_color_phase3': ('hgr_puts_color(3,0,"APPLE II",HGR_ORANGE);',False),
 'hgr_text_color_phase6': ('hgr_puts_color(6,0,"APPLE II",HGR_ORANGE);',False),
 'hgr_text16_phase0': ('hgr_puts(0,0,"APPLE II");',False),
 'hgr_text16_phase3': ('hgr_puts(3,0,"APPLE II");',False),
 'hgr_text16_phase6': ('hgr_puts(6,0,"APPLE II");',False),
 'hgr_text16_spaces': ('hgr_puts(0,0,"        ");',False),
 'hgr_text16_x9': ('hgr_puts(9,0,"APPLE II");',False),
 'hgr_text16_empty': ('hgr_puts(0,0,"");',False),
 'hgr_signed_min': ('hgr_puti(0,0,-32768);',False),
 'hgr_signed_negative': ('hgr_puti(0,0,-12345);',False),
 'hgr_signed_positive': ('hgr_puti(0,0,32767);',False),
 'hgr_field_pad': ('hgr_putu_field(0,0,42,14);',False),
 'hgr_field_overflow': ('hgr_putu_field(0,0,65535,1);',False),
 'hgr_field_clip': ('hgr_putu_field(250,176,42,5);',False),
 'hgr_colorize': ('hgr_colorize(7,32,140,16,HGR_ORANGE);',False),
 'hgr_colorize_even': ('hgr_colorize(0,32,140,16,HGR_BLUE);',False),
 'hgr_colorize_narrow': ('hgr_colorize(7,32,7,1,HGR_GREEN);',False),
 'hgr_plot': ('hgr_plot(139,40);',False),
 'hgr_unplot': ('hgr_unplot(279,191);',False),
 'hgr_sprite7': ('hgr_blit7(0,40,4,8,bits,HGR_SET);',False),
 'hgr_diagonal': ('hgr_line(0,0,279,191);',False),
 'gfx_diagonal': ('gfx_line(0,0,279,191);',False),
 'dhgr_clear': ('dhgr_clear(9);',True),
 'dhgr_span': ('dhgr_hline(0,559,40,1);',True),
 'dhgr_rect': ('dhgr_fill_rect(7,32,70,16,9);',True),
 'dhgr_block': ('dhgr_write_block(0,40,8,8,bits,8);',True),
 'dhgr_sprite': ('dhgr_sprite(7,40,2,2,2,bits,bits);',True),
 'dhgr_text': ('dhgr_puts("APPLE II",0,0);',True),
 'dhgr_text_x3': ('dhgr_puts("APPLE II",3,0);',True),
 'dhgr_text_x6': ('dhgr_puts("APPLE II",6,0);',True),
 'dhgr_text_spaces': ('dhgr_puts("        ",0,0);',True),
 'dhgr_clear_row': ('dhgr_clear_rows(40,1,9);',True),
 'dhgr_clear_rows16': ('dhgr_clear_rows(40,16,9);',True),
 'dhgr_clear_rows192': ('dhgr_clear_rows(0,192,9);',True),
 'dhgr_clear_rows_clip': ('dhgr_clear_rows(190,255,9);',True),
 'dhgr_small_text': ('dhgr_puts_small("APPLE II",0,0);',True),
}
# First call and steady-state frame workloads have their own budgets.
HUD = 'hgr_puts8(0,0,"SCORE"); hgr_putu_field(48,0,12345u,5); hgr_putu_field(160,0,42u,3);'
SPRITE_SETUP = '''
if (!hgr_spr_init_pool(1,pool,sizeof(pool),4,8)) return 2;
for (i=0; i<4; ++i) {
    if (!hgr_spr_define(i,&shape)) return 3;
    hgr_spr_move(i,28u+i*3u,60u+i*2u);
}
'''
FRAME = '''
for (i=0; i<4; ++i) hgr_spr_move(i,28u+i*3u+(frame&1u),60u+i*2u);
hgr_spr_render(); hgr_putu_field(48,0,frame,5); hgr_spr_present(); ++frame;
'''
SCENES = {
 'hgr_field_zero': dict(call='hgr_putu_field(0,0,0,1);'),
 'hgr_field_wide': dict(call='hgr_putu_field(0,0,65535u,255);'),
 'hgr_field_right': dict(call='hgr_putu_field(279,191,65535u,14);'),
 'hgr_field_empty': dict(call='hgr_putu_field(0,0,65535u,0);'),
 'hgr_field_outside': dict(call='hgr_putu_field(65535u,0,65535u,14);'),
 'hgr_field_below': dict(call='hgr_putu_field(0,255,65535u,14);'),
 'hgr_field_cold': dict(call='hgr_putu_field(0,0,42,5);',warmup=False),
 'hgr_hex_one_digit': dict(call='hgr_putx(0,0,15);'),
 'hgr_hex_two_digits': dict(call='hgr_putx(0,0,255);'),
 'hgr_hex_three_digits': dict(call='hgr_putx(0,0,4095);'),
 'hgr_hex_outside': dict(call='hgr_putx(65535u,255,65535u);'),
 'hgr_hex_cold': dict(call='hgr_putx(0,0,65535u);',warmup=False),
 'hgr_signed_zero': dict(call='hgr_puti(0,0,0);'),
 'hgr_signed_minus_one': dict(call='hgr_puti(0,0,-1);'),
 'hgr_signed_negative_ten': dict(call='hgr_puti(0,0,-10);'),
 'hgr_signed_clip': dict(call='hgr_puti(264,176,-32768);'),
 'hgr_signed_outside': dict(call='hgr_puti(65535u,255,-32768);'),
 'hgr_signed_cold': dict(call='hgr_puti(0,0,-32768);',warmup=False),
 'hgr_hline_reverse': dict(call='hgr_hline(279,0,40);'),
 'hgr_hline_clip': dict(call='hgr_hline(65535u,7,191);'),
 'hgr_hline_point': dict(call='hgr_hline(279,279,191);'),
 'hgr_hline_outside': dict(call='hgr_hline(65535u,280,40);'),
 'hgr_hline_below': dict(call='hgr_hline(0,279,255);'),
 'hgr_hline_cold': dict(call='hgr_hline(279,0,40);',warmup=False),
 'hgr_vline_full': dict(call='hgr_vline(279,0,191);'),
 'hgr_vline_reverse': dict(call='hgr_vline(279,191,0);'),
 'hgr_vline_clip': dict(call='hgr_vline(279,255,0);'),
 'hgr_vline_point': dict(call='hgr_vline(279,191,191);'),
 'hgr_vline_outside': dict(call='hgr_vline(65535u,0,191);'),
 'hgr_vline_below': dict(call='hgr_vline(7,255,192);'),
 'hgr_vline_cold': dict(call='hgr_vline(279,191,0);',warmup=False),
 'hgr_line_short': dict(call='hgr_line(7,8,9,9);'),
 'hgr_line_reverse': dict(call='hgr_line(279,191,0,0);'),
 'hgr_line_horizontal': dict(call='hgr_line(279,80,0,80);'),
 'hgr_line_vertical': dict(call='hgr_line(279,191,279,0);'),
 'hgr_line_point': dict(call='hgr_line(279,191,279,191);'),
 'hgr_line_outside_x': dict(call='hgr_line(65535u,0,7,8);'),
 'hgr_line_outside_y': dict(call='hgr_line(7,0,8,255);'),
 'gfx_hex_0': dict(call='gfx_hexstr(hexbuf,0u);',declarations='static char hexbuf[5];'),
 'gfx_hex_9': dict(call='gfx_hexstr(hexbuf,9u);',declarations='static char hexbuf[5];'),
 'gfx_hex_15': dict(call='gfx_hexstr(hexbuf,15u);',declarations='static char hexbuf[5];'),
 'gfx_hex_16': dict(call='gfx_hexstr(hexbuf,16u);',declarations='static char hexbuf[5];'),
 'gfx_hex_255': dict(call='gfx_hexstr(hexbuf,255u);',declarations='static char hexbuf[5];'),
 'gfx_hex_256': dict(call='gfx_hexstr(hexbuf,256u);',declarations='static char hexbuf[5];'),
 'gfx_hex_4095': dict(call='gfx_hexstr(hexbuf,4095u);',declarations='static char hexbuf[5];'),
 'gfx_hex_4096': dict(call='gfx_hexstr(hexbuf,4096u);',declarations='static char hexbuf[5];'),
 'gfx_hex_65535': dict(call='gfx_hexstr(hexbuf,65535u);',declarations='static char hexbuf[5];'),
 'hgr_hex_zero': dict(call='hgr_putx(0,0,0);'),
 'hgr_hex_maximum': dict(call='hgr_putx(0,0,65535u);'),
 'hgr_hex_clip': dict(call='hgr_putx(264,176,65535u);'),
 'hgr_putu_zero': dict(call='hgr_putu(0,0,0);'),
 'hgr_putu_nine': dict(call='hgr_putu(0,0,9);'),
 'hgr_putu_ten': dict(call='hgr_putu(0,0,10);'),
 'hgr_putu_four_digits': dict(call='hgr_putu(0,0,9999);'),
 'hgr_putu_maximum': dict(call='hgr_putu(0,0,65535u);'),
 'hgr_putu_clip': dict(call='hgr_putu(264,176,65535u);'),
 'hgr_putu_outside': dict(call='hgr_putu(65535u,255,65535u);'),
 'hgr_putu_cold': dict(call='hgr_putu(0,0,65535u);',warmup=False),
 'hgr_putu8_zero': dict(call='hgr_putu8(0,0,0);'),
 'hgr_putu8_nine': dict(call='hgr_putu8(0,0,9);'),
 'hgr_putu8_ten': dict(call='hgr_putu8(0,0,10);'),
 'hgr_putu8_four_digits': dict(call='hgr_putu8(0,0,9999);'),
 'hgr_putu8_maximum': dict(call='hgr_putu8(0,0,65535u);'),
 'hgr_putu8_clip': dict(call='hgr_putu8(264,176,65535u);'),
 'hgr_putu8_outside': dict(call='hgr_putu8(65535u,255,65535u);'),
 'hgr_putu8_cold': dict(call='hgr_putu8(0,0,65535u);',warmup=False),
 'hgr_text16_single': dict(call='hgr_puts(264,176,"A");'),
 'hgr_text16_clip': dict(call='hgr_puts(256,176,"ABCDEF");'),
 'hgr_text16_cold': dict(call='hgr_puts_color(256,176,"ABCDEF",HGR_ORANGE);',warmup=False),
 'hgr_text16_outside': dict(call='hgr_puts(65535u,40,"A");'),
 'hgr_text16_below': dict(call='hgr_puts_color(7,177,"A",HGR_GREEN);'),
 'hgr_text16_fallback': dict(call='hgr_puts_color(3,0,"APPLE II",255);'),
 'hgr_text8_single': dict(call='hgr_puts8(273,184,"A");'),
 'hgr_text8_clip': dict(call='hgr_puts8(256,184,"ABCDEF");'),
 'hgr_text8_cold': dict(call='hgr_puts8(256,184,"ABCDEF");',warmup=False),
 'hgr_text8_empty': dict(call='hgr_puts8(7,40,"");'),
 'hgr_text8_outside': dict(call='hgr_puts8(65535u,40,"A");'),
 'hgr_text8_below': dict(call='hgr_puts8(7,185,"A");'),
 'hgr_sprite7_single': dict(call='hgr_blit7(279,191,1,1,bits,HGR_SET);'),
 'hgr_sprite7_clear': dict(call='hgr_blit7(7,40,4,8,bits,HGR_CLEAR);'),
 'hgr_sprite7_xor': dict(call='hgr_blit7(7,40,4,8,bits,HGR_XOR);'),
 'hgr_sprite7_clip': dict(call='hgr_blit7(279,191,255,255,bits,HGR_XOR);'),
 'hgr_sprite7_cold': dict(call='hgr_blit7(279,191,255,255,bits,HGR_XOR);',warmup=False),
 'hgr_sprite7_empty': dict(call='hgr_blit7(0,0,0,255,bits,HGR_XOR);'),
 'hgr_sprite7_outside': dict(call='hgr_blit7(65535u,0,255,255,bits,HGR_XOR);'),
 'hgr_colorize_cold': dict(call='hgr_colorize(255,189,255,255,HGR_ORANGE);', warmup=False),
 'hgr_colorize_clip': dict(call='hgr_colorize(255,189,255,255,HGR_ORANGE);'),
 'hgr_colorize_invalid': dict(call='hgr_colorize(7,32,140,16,255);'),
 'hgr_colorize_empty': dict(call='hgr_colorize(7,32,0,16,HGR_ORANGE);'),
 'hgr_columns_cold': dict(call='hgr_build_columns();', warmup=False,
     declarations='void hgr_build_columns(void);'),
 'hgr_masks_cold': dict(call='hgr_build_masks();', warmup=False,
     declarations='void hgr_build_masks(void);'),
 'hgr_phases_cold': dict(call='hgr_build_phases();', warmup=False,
     declarations='void hgr_build_phases(void);'),
 'hgr_columns_warm': dict(call='hgr_build_columns();',
     declarations='void hgr_build_columns(void);'),
 'hgr_byte_rect_cold': dict(call='hgr_fill_rect(189,255,38,255,0xDA);', warmup=False),
 'hgr_byte_rect_empty': dict(call='hgr_fill_rect(0,0,0,40,0xDA);'),
 'hgr_byte_rect_outside': dict(call='hgr_fill_rect(255,255,39,1,0xDA);'),
 'hgr_rect_cold': dict(call='hgr_fill_pixrect(255,189,255,255);', warmup=False),
 'hgr_rect_empty': dict(call='hgr_fill_pixrect(0,0,0,1);'),
 'hgr_rect_outside': dict(call='hgr_fill_pixrect(65535u,0,255,1);'),
 'hgr_cell_cold': dict(call='hgr_cell(34,23,255);', warmup=False),
 'hgr_cell_outside': dict(call='hgr_cell(255,23,255);'),
 'hgr_rows_cold': dict(call='hgr_build_rows();', warmup=False,
     declarations='void hgr_build_rows(void);'),
 'hgr_rows_warm': dict(call='hgr_build_rows();', declarations='void hgr_build_rows(void);'),
 'hgr_row_query': dict(call='hgr_row(191);'),
 'hgr_row_outside': dict(call='hgr_row(255);'),
 'hgr_show_only': dict(call='hgr_show_page();'),
 'hgr_show_page2': dict(call='hgr_show_page();',
     declarations='#include "hgr_internal.h"', setup='hgr_draw_page2=1;'),
 'hgr_page_select_cold': dict(call='hgr_set_draw_page(2);', warmup=False),
 'hgr_page_select1_cold': dict(call='hgr_set_draw_page(1);', warmup=False),
 'hgr_page_same': dict(call='hgr_set_draw_page(2);', setup='hgr_set_draw_page(2);'),
 'hgr_page_flip': dict(call='hgr_set_draw_page(2); hgr_set_draw_page(1);'),
 'hgr_page_lores_flip': dict(call='hgr_set_draw_page(2); hgr_set_draw_page(1);',
     setup='hgr_lores_getblock(0,0);'),
 'lores_clear': dict(call='hgr_lores_clear(5);', setup='hgr_lores_init();'),
 'lores_clear_page2': dict(call='hgr_lores_clear(0xFA);',
     setup='hgr_lores_init(); hgr_set_draw_page(2);'),
 'lores_point_cold': dict(call='hgr_lores_setblock(39,47,5);',
     setup='hgr_lores_init();', warmup=False),
 'lores_point': dict(call='hgr_lores_setblock(39,47,5);', setup='hgr_lores_init();'),
 'lores_point_even': dict(call='hgr_lores_setblock(0,0,0xFA);', setup='hgr_lores_init();'),
 'lores_point_outside': dict(call='hgr_lores_setblock(40,47,5);', setup='hgr_lores_init();'),
 'lores_read_cold': dict(call='hgr_lores_getblock(39,47);',
     setup='hgr_lores_init();', warmup=False),
 'lores_read': dict(call='hgr_lores_getblock(39,47);', setup='hgr_lores_init();'),
 'lores_read_even': dict(call='hgr_lores_getblock(0,0);', setup='hgr_lores_init();'),
 'lores_read_outside': dict(call='hgr_lores_getblock(39,255);', setup='hgr_lores_init();'),
 'lores_hline': dict(call='hgr_lores_hlin(0,39,20,9);', setup='hgr_lores_init();'),
 'lores_hline_clip': dict(call='hgr_lores_hlin(38,255,47,0xFA);', setup='hgr_lores_init();'),
 'lores_vline': dict(call='hgr_lores_vlin(20,0,47,9);', setup='hgr_lores_init();'),
 'lores_vline_odd': dict(call='hgr_lores_vlin(39,1,46,0xFA);', setup='hgr_lores_init();'),
 'lores_vline_single': dict(call='hgr_lores_vlin(39,47,255,0xFA);', setup='hgr_lores_init();'),
 'lores_rect': dict(call='hgr_lores_fill_rect(7,9,20,16,9);', setup='hgr_lores_init();'),
 'lores_rect_full': dict(call='hgr_lores_fill_rect(0,0,40,48,5);', setup='hgr_lores_init();'),
 'lores_rect_clip': dict(call='hgr_lores_fill_rect(38,46,255,255,0xFA);', setup='hgr_lores_init();'),
 'lores_rect_empty': dict(call='hgr_lores_fill_rect(0,0,0,48,5);', setup='hgr_lores_init();'),
 'dhgr_block_read': dict(call='dhgr_read_block(0,40,8,8,data,8);',
     iie=True, dhgr=True, declarations='static unsigned char data[64];'),
 'dhgr_block_odd': dict(call='dhgr_write_block(1,40,7,8,bits,8);',
     iie=True, dhgr=True),
 'dhgr_sprite_partial': dict(call='dhgr_sprite(0,40,14,8,8,data,mask);',
     iie=True, dhgr=True,
     declarations='static unsigned char data[64],mask[64],j;',
     setup='for(j=0;j<64;++j){data[j]=j*13u;mask[j]=0x55;}'),
 'dhgr_sprite_opaque': dict(call='dhgr_sprite(0,40,14,8,8,data,mask);',
     iie=True, dhgr=True,
     declarations='static unsigned char data[64],mask[64],j;',
     setup='for(j=0;j<64;++j)data[j]=j*13u;'),
 'hgr_hud8_digit': dict(call='hgr_hud8_putu(&hud,12346u);', warmup=False,
     declarations='static hgr_hud8_field_t hud;',
     setup='hgr_hud8_init(&hud,48,0,5); hgr_hud8_putu(&hud,12345u);'),
 'hgr_text8_dense': dict(call='hgr_blit_glyph8();',
     declarations='#include "hgr_internal.h"\nvoid hgr_blit_glyph8(void);\nstatic const unsigned char dense[8]={255,255,255,255,255,255,255,255};',
     setup='hgr_build_tables(); hgr_g_glyph=dense; hgr_g_col=4; hgr_g_bit=6; hgr_g_y=40;'),
 'hgr_text16_dense': dict(call='hgr_blit_glyph();',
     declarations='#include "hgr_internal.h"\nstatic const unsigned char dense[8]={255,255,255,255,255,255,255,255};',
     setup='hgr_build_tables(); hgr_g_glyph=dense; hgr_g_col=4; hgr_g_bit=6; hgr_g_y=40; hgr_z_ce=127; hgr_z_co=127; hgr_z_hi=0;'),
 'hgr_diagonal_cold': dict(call='hgr_line(0,0,279,191);', warmup=False),
 'hgr_hud_cold': dict(call=HUD, warmup=False),
 'hgr_hud_warm': dict(call=HUD),
 'hgr_scene_cold': dict(call=FRAME, setup=SPRITE_SETUP, sprites=True, warmup=False),
 # Two warm-up frames populate both pages' save-under history.
 'hgr_scene_warm': dict(call=FRAME, setup=SPRITE_SETUP, sprites=True, warmup=2),
}
BITMAP = 'static const unsigned char packed[]={240,15,165,90,255,129,66,36,24,60,126,195,153,102,128,1};'
for phase in (0, 3, 6):
    for mode in ('SET', 'CLEAR', 'XOR'):
        SCENES['hgr_bitmap_'+mode.lower()+'_phase'+str(phase)] = dict(
            call='hgr_blit(%du,40,16,8,packed,HGR_%s);' % (28+phase, mode),
            declarations=BITMAP)
SCENES['hgr_bitmap_empty'] = dict(call='hgr_blit(31,40,16,8,packed,HGR_SET);',
    declarations='static const unsigned char packed[16]={0};')
SCENES['hgr_bitmap_solid'] = dict(call='hgr_blit(31,40,16,8,packed,HGR_SET);',
    declarations='static const unsigned char packed[16]={255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255};')
SCENES['hgr_bitmap_clip'] = dict(call='hgr_blit(276,190,16,8,packed,HGR_XOR);',
    declarations=BITMAP)
SCENES['hgr_bitmap_single'] = dict(call='hgr_blit(279,191,1,1,packed,HGR_SET);',
    declarations=BITMAP)
SCENES['hgr_bitmap_wide_clip'] = dict(call='hgr_blit(279,191,255,255,packed,HGR_XOR);',
    declarations=BITMAP)
SCENES['hgr_bitmap_cold'] = dict(call='hgr_blit(279,191,255,255,packed,HGR_XOR);',
    declarations=BITMAP,warmup=False)
SCENES['hgr_bitmap_zero_width'] = dict(call='hgr_blit(0,0,0,255,packed,HGR_SET);',
    declarations=BITMAP)
SCENES['hgr_bitmap_outside'] = dict(call='hgr_blit(65535u,0,255,255,packed,HGR_SET);',
    declarations=BITMAP)
for name, kernel in (('draw', 'hgr_ms_run'), ('save', 'hgr_ms_save_run'),
                     ('restore', 'hgr_ms_restore_run'), ('save_draw', 'hgr_msu_run')):
    SCENES['hgr_masked_generic_'+name] = dict(call=kernel+'();',
        declarations='#include "hgr_internal.h"\n'
            'static unsigned char pixels[392],keep[392],under[56];\n'
            'static const hgr_mspr_t shape={pixels,keep,7,8};\nstatic unsigned j;',
        setup='for(j=0;j<392;++j){pixels[j]=j&127u;keep[j]=128;}'
            'hgr_ms_x=17;hgr_ms_y=40;hgr_ms_spr=&shape;hgr_ms_under=under;')
for phase in (0, 3, 6):
    SCENES['hgr_preshift_phase'+str(phase)] = dict(
        call='hgr_sprite_xor(%du,40,&sprite);' % (28 + phase),
        sprite_width=7, sprite_height=16, sprite_stride=2,
        declarations='static const hgr_sprite_t sprite={bits,2,16};')
for name,call,cold,stride in (
    ('set','hgr_sprite(31,40,&sprite,HGR_SET);',False,2),
    ('clear','hgr_sprite(31,40,&sprite,HGR_CLEAR);',False,2),
    ('xor_general','hgr_sprite(31,40,&sprite,HGR_XOR);',False,2),
    ('other_mode','hgr_sprite(31,40,&sprite,255);',False,2),
    ('general_cold','hgr_sprite(31,40,&sprite,HGR_SET);',True,2),
    ('general_empty','hgr_sprite(31,40,&sprite,HGR_SET);',False,0),
    ('general_outside','hgr_sprite(65535u,40,&sprite,HGR_SET);',False,2),
    ('xor_cold','hgr_sprite_xor(31,40,&sprite);',True,2),
    ('xor_empty','hgr_sprite_xor(31,40,&sprite);',False,0),
    ('xor_clip','hgr_sprite_xor(279,191,&sprite);',False,2),
    ('xor_outside','hgr_sprite_xor(65535u,40,&sprite);',False,2),
    ('both','hgr_sprite(31,40,&sprite,HGR_SET); hgr_sprite_xor(38,40,&sprite);',False,2)):
    SCENES['hgr_preshift_'+name]=dict(call=call,warmup=not cold,
        sprite_width=7,sprite_height=16,sprite_stride=2,
        declarations='static const hgr_sprite_t sprite={bits,%d,16};'%stride)
for name,phase,stride,height in (('tall',6,3,255),('wide',3,255,1),
                                ('large',6,255,255),('square',3,8,8)):
    SCENES['hgr_preshift_setup_'+name]=dict(call='hgr_xs_setup();',
        declarations='#include "hgr_internal.h"\nstatic const hgr_sprite_t sprite={bits,%d,%d};'%(stride,height),
        setup='hgr_xs_x=%d; hgr_xs_y=0; hgr_xs_spr=&sprite;'%(28+phase))
SCENES.update({
 'hgr_hud_cached_same': dict(call='hgr_hud_putu(&hud,12345u);',
     setup='hgr_hud_init(&hud,48,0,5);', declarations='static hgr_hud_field_t hud;'),
 'hgr_hud_cached_digit': dict(call='hgr_hud_putu(&hud,12346u);',warmup=False,
     setup='hgr_hud_init(&hud,48,0,5); hgr_hud_putu(&hud,12345u);',
     declarations='static hgr_hud_field_t hud;'),
})
for phase in range(7):
    SCENES['hgr_scene_phase'+str(phase)] = dict(sprites=True, sprite_height=8,
        sprite_width=7, sprite_stride=2, warmup=2,
        declarations='static hgr_hud_field_t hud;',
        setup='hgr_hud_init(&hud,48,0,5);'+
        'if (!hgr_spr_init_pool(1,pool,sizeof(pool),4,16)) return 2;'+
        'for(i=0;i<4;++i) {if(!hgr_spr_define(i,&shape)) return 3;'+
        'hgr_spr_move(i,28u+%du+i*3u,60u+i*2u);}'%phase,
        call='hgr_spr_render(); hgr_hud_putu(&hud,frame++); hgr_spr_present();')
SCENES['hgr_scene_large_edge'] = dict(sprites=True, sprite_height=16,
    sprite_width=21, sprite_stride=4, warmup=2,
    declarations='static hgr_hud_field_t hud;',
    setup='hgr_hud_init(&hud,48,0,5);'+
    'if (!hgr_spr_init_pool(1,pool,sizeof(pool),4,64)) return 2;'+
    'for(i=0;i<4;++i) {if(!hgr_spr_define(i,&shape)) return 3; hgr_spr_move(i,262u+i*3u,180u+i);}',
    call='hgr_spr_render(); hgr_hud_putu(&hud,frame++); hgr_spr_present();')
SCENES['hgr_scene_large_full'] = dict(SCENES['hgr_scene_large_edge'],
    setup=SCENES['hgr_scene_large_edge']['setup'].replace('262u','28u').replace('180u','60u'))
for variant in ('compact','unrolled','fixed'):
    SCENES['hgr_rows_'+variant] = dict(call='bench_present();',presentation=variant,
        setup='hgr_build_tables();',warmup=False)
for mode in ('delay','vbl'):
    SCENES['hgr_loop_'+mode] = dict(sprites=True,sprite_width=7,sprite_height=8,sprite_stride=2,
        warmup=2,iie=(mode=='vbl'),cadence=True,declarations='static hgr_hud_field_t hud;',
        setup='a2_frame_init(); a2_frame_set_delay(40); hgr_hud_init(&hud,48,0,5);'+
        'if(!hgr_spr_init_pool(1,pool,sizeof(pool),4,16)) return 2;'+
        'for(i=0;i<4;++i) if(!hgr_spr_define(i,&shape)) return 3;',
        call='if(apple2_readkey()==KC_LEFT) frame=0;'+
        'for(i=0;i<4;++i) hgr_spr_move(i,28u+i*3u+(frame%7u),60u+i*2u);'+
        'hgr_spr_render(); hgr_hud_putu(&hud,frame); a2_frame_wait(); hgr_spr_present(); ++frame;')
# Keep historical stationary workloads; add movement across both page histories.
for name in list(SCENES):
    if name.startswith(('hgr_scene_phase','hgr_scene_large')):
        options=dict(SCENES[name])
        if name.startswith('hgr_scene_phase'):
            x='28u+%du+i*3u'%int(name[-1]); y='60u+i*2u'
        elif name.endswith('edge'):
            x='262u+i*3u'; y='180u+i'
        else:
            x='28u+i*3u'; y='60u+i'
        options['call']='for(i=0;i<4;++i) hgr_spr_move(i,'+x+'+(frame%3u),'+y+');'+options['call']
        SCENES[name+'_moving']=options
SCENES['hgr_hud_cached_cold']=dict(call='hgr_hud_putu(&hud,54321u);',warmup=False,
    setup='hgr_hud_init(&hud,48,0,5);',declarations='static hgr_hud_field_t hud;')
for phase in range(7):
    SCENES['hgr_hud_changed_phase'+str(phase)]=dict(call='hgr_hud_putu(&hud,65432u);',warmup=False,
        setup='hgr_hud_init(&hud,%d,0,5); hgr_hud_putu(&hud,12345u);'%(48+phase),
        declarations='static hgr_hud_field_t hud;')
SCENES['hgr_rows_explicit_asm']=dict(call='bench_present();',presentation='explicit',warmup=False)
SCENES['hgr_rows_explicit']=dict(call='for(y=0;y<192;++y) row=hgr_row_on_page(2,y);',
    declarations='static volatile unsigned char *row; unsigned char y;',warmup=False)
BASELINE=Path(__file__).with_name('baseline.json')
BUDGETS=Path(__file__).with_name('budgets.json')

# Representative work excludes waiting, but includes input, movement, render,
# changing every HUD digit and presentation. Initialization warms both pages.
for phase in range(7):
    SCENES['hgr_hud8_changed_phase'+str(phase)]=dict(
        call='hgr_hud8_putu(&hud,65432u);',warmup=False,
        setup='hgr_hud8_init(&hud,%d,0,5); hgr_hud8_putu(&hud,12345u);'%(48+phase),
        declarations='static hgr_hud8_field_t hud;')
for suffix, call in (('same','hgr_hud8_putu(&hud,12345u);'),
                     ('cold','hgr_hud8_putu(&hud,54321u);')):
    SCENES['hgr_hud8_'+suffix]=dict(call=call,warmup=(suffix=='same'),
        setup='hgr_hud8_init(&hud,48,0,5);', declarations='static hgr_hud8_field_t hud;')
SCENES['hgr_game_compact']=dict(sprites=True,sprite_width=7,sprite_height=8,sprite_stride=2,
    warmup=2,declarations='static hgr_hud8_field_t hud; unsigned char phase;'+
    'static const unsigned scores[3]={123u,654u,987u};',
    setup='hgr_hud8_init(&hud,48,0,3);'+
    'if(!hgr_spr_init_pool(1,pool,sizeof(pool),2,16)) return 2;'+
    'for(i=0;i<2;++i) if(!hgr_spr_define(i,&shape)) return 3;',
    call='if(apple2_readkey()==KC_LEFT) frame+=1; phase=frame%3u;'+
    'for(i=0;i<2;++i) hgr_spr_move(i,28u+i*3u+phase,60u+i*2u);'+
    'hgr_spr_render(); hgr_hud8_putu(&hud,scores[phase]);'+
    'hgr_spr_present(); ++frame;')
for damage in (False,True):
    SCENES['hgr_isolated_'+('damage' if damage else 'suffix')]=dict(
        sprites=True,sprite_width=21,sprite_height=16,sprite_stride=4,
        warmup=2,damage=damage,
        setup='if(!hgr_spr_init_pool(1,pool,sizeof(pool),4,64)) return 2;'+
              'for(i=0;i<4;++i) {if(!hgr_spr_define(i,&shape)) return 3;'+
              'hgr_spr_move(i,28u+i*56u,60u);}',
        call='hgr_spr_move(0,28u+(frame%3u),60u); hgr_spr_render(); hgr_spr_present(); ++frame;')
for name in ('hgr_game_compact','hgr_isolated_damage'):
    SCENES[name+'_pal']=dict(SCENES[name],iie=True,pal=True)
for phase in range(1,7):
    name='hgr_game_compact_phase'+str(phase)
    SCENES[name]=dict(SCENES['hgr_game_compact'],
        setup=SCENES['hgr_game_compact']['setup'].replace('48,0,3',f'{48+phase},0,3'),
        call=SCENES['hgr_game_compact']['call'].replace('28u+i',f'{28+phase}u+i'))
    SCENES[name+'_pal']=dict(SCENES[name],iie=True,pal=True)


SCENES['hgr_hud8_carry']=dict(call='hgr_hud8_putu(&hud,10000u);',warmup=False,
    setup='hgr_hud8_init(&hud,48,0,5);hgr_hud8_putu(&hud,9999u);',
    declarations='static hgr_hud8_field_t hud;')
SCENES['hgr_tile_background']=dict(sprites=True,sprite_width=7,sprite_height=8,sprite_stride=2,
    declarations='#include "hgr_internal.h"\nstatic hgr_tilemap_t background;'+
    'static unsigned char tilemap[960];static const unsigned char tiles[8]={85,42,85,42,85,42,85,42};',
    setup='if(!hgr_tilemap_init(&background,tilemap,tiles,1))return 2;hgr_set_draw_page(2);',
    call='hgr_tile_restore(&background,2,4,7,4,2);'+
    'hgr_ms_spr=&shape;hgr_ms_x=29;hgr_ms_y=60;hgr_ms_run();'+
    'hgr_ms_x=43;hgr_ms_y=60;hgr_ms_run();hgr_show_page();')
SCENES['hgr_tile_background_pal']=dict(SCENES['hgr_tile_background'],iie=True,pal=True)
# Isolated HUD initialization includes validation and caller-owned state writes.
for compact in (False,True):
    stem='hgr_hud8' if compact else 'hgr_hud'
    maximum=5 if compact else 14
    bottom=184 if compact else 176
    for suffix,x,y,width,pointer in (
        ('origin',0,0,maximum,'&hud'),
        ('edge',240 if compact else 30,bottom,maximum,'&hud'),
        ('single',272 if compact else 264,bottom,1,'&hud'),
        ('overrun',241 if compact else 31,bottom,maximum,'&hud'),
        ('outside',65535,0,1,'&hud'),
        ('below',0,bottom+1,1,'&hud'),
        ('empty',0,0,0,'&hud'),
        ('wide',0,0,255,'&hud'),
        ('null',0,0,1,'0')):
        SCENES[stem+'_init_'+suffix]=dict(
            call=f'{stem}_init({pointer},{x}u,{y},{width});',warmup=False,
            declarations=f'static {stem}_field_t hud;')

# Tile-map validation measures complete scans, the 256-ID shortcut and failures.
for suffix,count,setup,ctx,map_ptr,tiles in (
    ('one',1,'','&background','tilemap','tiles'),
    ('many',255,'tilemap[959]=254;','&background','tilemap','tiles'),
    ('all',256,'tilemap[959]=255;','&background','tilemap','tiles'),
    ('first_bad',8,'tilemap[0]=8;','&background','tilemap','tiles'),
    ('last_bad',8,'tilemap[959]=8;','&background','tilemap','tiles'),
    ('empty',0,'','&background','tilemap','tiles'),
    ('wide',65535,'','&background','tilemap','tiles'),
    ('null_context',8,'','0','tilemap','tiles'),
    ('null_map',8,'','&background','0','tiles'),
    ('null_tiles',8,'','&background','tilemap','0')):
    SCENES['hgr_tile_init_'+suffix]=dict(
        call=f'hgr_tilemap_init({ctx},{map_ptr},{tiles},{count}u);',
        warmup=False,setup=setup,
        declarations='static hgr_tilemap_t background; static unsigned char tilemap[960];'+
                     'static const unsigned char tiles[8]={0};')

for suffix,y,rows,color in (
    ('empty',0,0,9),('outside',255,255,9),('last',191,255,255),
    ('full_clip',0,255,255),('masked_color',40,1,249)):
    SCENES['dhgr_clear_rows_'+suffix]=dict(
        call=f'dhgr_clear_rows({y},{rows},{color});',iie=True,warmup=False)

for suffix,x,y,width,height in (
    ('small',3,4,16,1),('last',559,191,65535,255),
    ('wide',0,0,65535,1),('wrap',559,0,64977,1),
    ('full',0,0,560,192),('outside',65535,0,1,1),
    ('below',0,255,1,1),('empty_width',0,0,0,1),('empty_height',0,0,1,0)):
    SCENES['dhgr_bit_rect_'+suffix]=dict(
        call=f'dhgr_bit_rect({x}u,{y},{width}u,{height});',dhgr=True,iie=True,warmup=False,
        declarations='#include "dhgr_internal.h"',setup='dhgr_prepare_pattern(9);')

for suffix,x,y,width,height,set_bit in (
    ('clear',3,4,16,1,0),('set',3,4,16,1,1),('set_255',3,4,16,1,255),
    ('wide',0,0,65535,1,1),('last',559,191,65535,255,1),
    ('outside',65535,0,1,1,1),('empty_width',0,0,0,1,1),
    ('empty_height',0,0,1,0,0)):
    SCENES['dhgr_fill_bits_'+suffix]=dict(
        call=f'dhgr_fill_bits({x}u,{y},{width}u,{height},{set_bit});',
        dhgr=True,iie=True,warmup=False)

for suffix,x,y,width,height,color in (
    ('small',3,4,4,1,9),('boundary',63,4,2,1,9),('high',128,4,1,1,9),
    ('last',139,191,255,255,249),('wide',0,0,255,1,255),
    ('outside',255,0,1,1,9),('below',0,255,1,1,9),
    ('empty_width',0,0,0,1,9),('empty_height',0,0,1,0,9),
    ('masked_color',3,4,4,1,255)):
    SCENES['dhgr_fill_color_'+suffix]=dict(
        call=f'dhgr_fill_rect({x},{y},{width},{height},{color});',
        dhgr=True,iie=True,warmup=False)

for suffix,x0,x1,y,set_bit in (
    ('forward',3,20,4,1),('reverse',20,3,4,0),('clip',65535,551,191,255),
    ('outside',560,65535,4,1),('below',0,559,255,1)):
    SCENES['dhgr_hline_'+suffix]=dict(call=f'dhgr_hline({x0}u,{x1}u,{y},{set_bit});',
                                    dhgr=True,iie=True,warmup=False)
for suffix,x,y0,y1,set_bit in (
    ('forward',3,4,20,1),('reverse',3,20,4,0),('clip',559,255,189,255),
    ('outside',65535,0,191,1),('below',0,192,255,1)):
    SCENES['dhgr_vline_'+suffix]=dict(call=f'dhgr_vline({x}u,{y0},{y1},{set_bit});',
                                    dhgr=True,iie=True,warmup=False)

for suffix,call,setup in (
    ('draw_one','dhgr_draw_page(1);','dhgr_draw_page(2);'),
    ('draw_two','dhgr_draw_page(2);',''),
    ('draw_invalid','dhgr_draw_page(255);',''),
    ('get_one','dhgr_get_draw_page();',''),
    ('get_two','dhgr_get_draw_page();','dhgr_draw_page(2);'),
    ('get_display','dhgr_get_display_page();','dhgr_show_page(2);'),
    ('flip','dhgr_flip();','dhgr_draw_page(2);'),
    ('flip_unshown','dhgr_flip();','dhgr_display=0;')):
    SCENES['dhgr_pages_'+suffix]=dict(call=call,setup=setup,dhgr=True,iie=True,
        warmup=False,declarations='#include "dhgr_internal.h"')

for suffix,call in (
    ('empty','dhgr_puts_small("",0,0);'),
    ('last','dhgr_puts_small("A",135,187);'),
    ('outside','dhgr_puts_small("A",255,0);'),
    ('below','dhgr_puts_small("A",0,255);'),
    ('clip','dhgr_puts_small("AB",135,187);')):
    SCENES['dhgr_small_entry_'+suffix]=dict(call=call,dhgr=True,iie=True,warmup=False)
for color in (0,15,255):
    SCENES['dhgr_clear_color_'+str(color)]=dict(call=f'dhgr_clear({color});',
        dhgr=True,iie=True,warmup=False)

for direction in ('read','write'):
    for suffix,bx,y,width,height,stride in (
        ('byte',0,0,1,1,1), ('tall',1,0,1,192,1),
        ('clip',79,190,80,255,80), ('zero_height',0,0,1,0,1),
        ('zero_width',0,0,0,1,1), ('bad_stride',0,0,2,1,1),
        ('outside',255,0,1,1,1), ('below',0,255,1,1,1),
        ('stride255',78,190,2,2,255)):
        SCENES['dhgr_transfer_'+direction+'_'+suffix]=dict(
            call=f'dhgr_{direction}_block({bx},{y},{width},{height},data,{stride});',
            declarations='static unsigned char data[512];',dhgr=True,iie=True,warmup=False)

for suffix,x,y,width,height,stride in (
    *((f'phase{(x*4)%7}',x,40,2,8,8) for x in range(7)),
    ('height255',6,191,1,255,2), ('wide',139,191,255,1,255),
    ('zero_width',1,0,0,1,2), ('zero_height',1,0,1,0,2),
    ('bad_stride',1,0,2,1,1), ('outside',255,0,1,1,2),
    ('below',1,255,1,1,2)):
    SCENES['dhgr_sprite_entry_'+suffix]=dict(
        call=f'dhgr_sprite({x},{y},{width},{height},{stride},data,mask);',
        declarations='static unsigned char data[2048],mask[2048];',
        dhgr=True,iie=True,warmup=False)

for suffix,x,y in (('aux',0,0),('main',7,0),('phase6',6,40),
                   ('last',559,191),('outside',560,191),('high',65535,0),('below',0,255)):
    for value in (0,255):
        SCENES[f'dhgr_point_plot_{suffix}_{value}']=dict(call=f'dhgr_plot({x}u,{y},{value});',
            dhgr=True,iie=True,warmup=False)
    SCENES['dhgr_point_read_'+suffix]=dict(call=f'dhgr_getpixel({x}u,{y});',
        setup='dhgr_clear(15);',dhgr=True,iie=True,warmup=False)

for kind,values in (('u',(0,9,10,99,100,65535)),
                    ('i',(0,1,-1,32767,-32768,-100)),('x',(0,15,16,255,65535))):
    for value in values:
        SCENES[f'gfx_number_{kind}_{str(value).replace("-","minus")}']=dict(
            call=f'gfx_put{kind}({value});',
            setup='gfx_gotoxy(0,0);gfx_text(" ");gfx_gotoxy(0,0);',warmup=False)

# Non-default compile-time variants (dev/lib/ABI.md, "Speed/RAM options"):
# the listed members are reassembled with the define and linked before hgrc.lib.
for name in ('hgr_diagonal_cold','hgr_hud_cold','hgr_scene_cold'):
    SCENES[name+'_x7folded']=dict(SCENES[name],variant=('HGRC_X7_FOLDED',('hgr_columns.s',)))


# DHGR sprite compositor (opt-in HGRC_DHGR_SPR_SRCS, linked before hgrc.lib):
# a Robot Space Station room (tile map of RECTS tiles, rows 10..153) and its
# 10x12 drone; the measured call moves it one pixel (set + update).
SPR_SRCS=('dhgr_spr_api.s','dhgr_spr_palette.s','dhgr_spr_area.s','dhgr_spr_update.s','dhgr_spr_asm.s','dhgr_cv_asm.s',
          'dhgr_spr_overlay.s','dhgr_spr_cursor.s','dhgr_spr_cells.s','dhgr_cv_bitmap.s')
SPR_DECL='''
static unsigned char canvas[1024], map[360], i;
static const unsigned char floor_r[]={0,0,7,8,0, 3,3,1,2,4};
static const unsigned char wall_r[]={0,0,7,8,5, 0,7,7,1,2};
static const unsigned char drone_r[]={3,0,1,2,17, 2,2,6,4,16, 5,3,3,2,2, 6,3,2,1,15,
    1,6,8,4,10, 2,7,5,1,16, 7,8,3,1,18, 2,10,2,2,19, 6,10,2,2,19};
static const dhgr_shape_t floor_s={DHGR_SHAPE_RECTS,7,8,2,floor_r};
static const dhgr_shape_t wall_s={DHGR_SHAPE_RECTS,7,8,2,wall_r};
static const dhgr_shape_t drone_s={DHGR_SHAPE_RECTS,10,12,9,drone_r};
static const dhgr_shape_t *const set[2]={&floor_s,&wall_s};
static const unsigned char pal[4]={7,13,15,9};
static unsigned char tile_c[56], ship_c[30];
static const dhgr_shape_t tile_s={DHGR_SHAPE_TILE,7,8,0,tile_c};
static const dhgr_shape_t ship_s={DHGR_SHAPE_CHUNKY,6,5,0,ship_c};
static const dhgr_shape_t *const tset[2]={&tile_s,&wall_s};
static const unsigned char arrow[24]={1,0,0,0,3,0,0,0,7,0,0,0,15,0,0,0,3,0,0,0,1,0,0,0};
static unsigned char under[48];
static void paint(unsigned char col, unsigned char row) {
    static unsigned char x, y;
    x = col * 7u; y = 10u + (row << 3);
    if (map[row * 20u + col]) { dhgr_cv_rect(x, y, 7, 8, 5); dhgr_cv_rect(x, y + 7u, 7, 1, 2); }
    else { dhgr_cv_rect(x, y, 7, 8, 0); dhgr_cv_rect(x + 3u, y + 3u, 1, 2, 4); }
}
'''
SPR_ROOM='''
for(i=0;i<20;++i){map[i]=map[340+i]=1;} for(i=0;i<18;++i){map[i*20]=map[i*20+19]=1;}
if(!dhgr_spr_init(canvas,sizeof canvas,4)) return 2;
dhgr_spr_area(0,10,139,153);
'''
for name,x,background in (('dhgr_spr_move',30,'tiles'),('dhgr_spr_move_wide',33,'tiles'),
                          ('dhgr_spr_move_cells',30,'cells'),('dhgr_spr_move_solid',30,'solid')):
    bg={'tiles':'dhgr_spr_tiles(0,10,8,map,20,set);','cells':'dhgr_spr_cells(0,10,8,paint);',
        'solid':''}[background]
    SCENES[name]=dict(iie=True,dhgr=True,spr=(),declarations=SPR_DECL,
        setup=SPR_ROOM+bg+'dhgr_spr_invalidate(0,10,140,144); dhgr_spr_palette(0,pal);'
              'dhgr_spr_set(0,&drone_s,%du,40u,0); dhgr_spr_update();'%x,
        call='dhgr_spr_set(0,&drone_s,%du,40u,0); dhgr_spr_update();'%(x+1))
SCENES['dhgr_spr_move_tables']=dict(SCENES['dhgr_spr_move'],spr=('DHGR_SPR_PACK_TABLES',))
SCENES['dhgr_spr_move_chunky']=dict(SCENES['dhgr_spr_move'],
    setup='for(i=0;i<56;++i) tile_c[i]=DHGR_NIB(i%13u); for(i=0;i<30;++i) ship_c[i]=i%3u?9u:DHGR_CLEAR;'+
          SPR_ROOM+'dhgr_spr_tiles(0,10,8,map,20,tset); dhgr_spr_invalidate(0,10,140,144);'
          'dhgr_spr_set(0,&ship_s,30u,40u,0); dhgr_spr_update();',
    call='dhgr_spr_set(0,&ship_s,31u,40u,DHGR_SPR_MIRROR); dhgr_spr_update();')
# DHGR_SPR_DOUBLE: the same drone moving one pixel a frame on two pages,
# steady state (the update rewrites this move and the previous one).
SCENES['dhgr_spr_double_move']=dict(SCENES['dhgr_spr_move'],spr=('DHGR_SPR_DOUBLE',),
    setup='dhgr_draw_page(2);'+SPR_ROOM+'dhgr_spr_tiles(0,10,8,map,20,set);'
          'dhgr_spr_invalidate(0,10,140,144); dhgr_spr_palette(0,pal);'
          'dhgr_spr_set(0,&drone_s,30u,40u,0); dhgr_spr_update(); dhgr_flip();'
          'dhgr_spr_set(0,&drone_s,31u,40u,0); dhgr_spr_update(); dhgr_flip();',
    call='dhgr_spr_set(0,&drone_s,32u,40u,0); dhgr_spr_update();')
# DHGR_SPR_VBL with the //e VBL clock (apple2vbl): the same move, started
# right after a VBL edge (a2_frame_wait), composed, then written after the
# next edge: about one refresh, the wait included (17,030 cycles a refresh).
SCENES['dhgr_spr_vbl_move']=dict(SCENES['dhgr_spr_move'],spr=('DHGR_SPR_VBL',),clock=True,
    declarations=SPR_DECL+'unsigned char a2_vbl_init(void); unsigned char a2_frame_wait(void);\n',
    setup='a2_vbl_init();'+SCENES['dhgr_spr_move']['setup']+'a2_frame_wait();')
SCENES['dhgr_cursor_move']=dict(iie=True,dhgr=True,spr=(),declarations=SPR_DECL,
    setup='dhgr_cursor(20,60,4,6,arrow,under);', call='dhgr_cursor(21,61,4,6,arrow,under);')
SCENES['dhgr_spr_overlay_move']=dict(SCENES['dhgr_spr_move'],
    setup=SCENES['dhgr_spr_move']['setup']+'dhgr_spr_overlay(20,60,4,6,arrow,under); dhgr_spr_update();',
    call='dhgr_spr_overlay(21,61,4,6,arrow,under); dhgr_spr_update();')


def segment_sizes(mapfile):
    section=mapfile.read_text().split('Segment list:')[1].split('Exports list')[0]
    sizes={m[1]:int(m[2],16) for m in re.finditer(r'^([A-Z][A-Z0-9_]*)\s+[0-9A-F]+\s+[0-9A-F]+\s+([0-9A-F]+)',section,re.M)}
    return sizes


def segments(mapfile):
    sizes=segment_sizes(mapfile)
    init=sum(sizes.get(s,0) for s in ('ONCE','INIT','LOWCODE'))
    return dict(code_bytes=sizes.get('CODE',0)+sizes.get('STARTUP',0)+init,
                init_code_bytes=init,
                rodata_bytes=sizes.get('RODATA',0),
                ram_bytes=sum(sizes.get(s,0) for s in ('BSS','LOWBSS','DATA','ZPSAVE')),
                zp_bytes=sizes.get('ZEROPAGE',0))


def sprite_source(width,height,stride):
    data=[]; masks=[]
    for phase in range(7):
        for y in range(height):
            coverage=((1<<width)-1)<<phase
            bits=sum(1<<(phase+x) for x in range(width) if (x+y)%3)
            data.extend((bits>>(7*i))&127 for i in range(stride))
            masks.extend(255^((coverage>>(7*i))&127) for i in range(stride))
    return ('static const unsigned char bits[]={'+','.join(map(str,data))+'};\n'+
            'static const unsigned char mask[]={'+','.join(map(str,masks))+'};\n')


def presentation_source(variant):
    # Compare the same work: change draw page and resolve all 192 row pointers.
    # Fixed base is a prototype, not the current public table ABI.
    if variant=='explicit':
        return ('.export _bench_present\n.import hgr_fixed_rowlo, hgr_fixed_rowhi\n.importzp ptr1\n'
                '.data\nbase: .byte $20\n.code\n_bench_present:\n'
                'lda base\neor #$60\nsta base\nldx #191\n'
                'rows: lda hgr_fixed_rowlo,x\nsta ptr1\nlda hgr_fixed_rowhi,x\nora base\n'
                'sta ptr1+1\ndex\ncpx #$ff\nbne rows\nrts\n')
    prefix='.export _bench_present\n.import _hgr_rowhi, _hgr_rowlo\n.importzp ptr1\n.code\n_bench_present:\n'
    if variant=='unrolled':
        prefix='.import _hgr_flip_rows\n'+prefix+'jsr _hgr_flip_rows\n'
    elif variant=='compact':
        prefix+='ldx #191\nflip: lda _hgr_rowhi,x\neor #$60\nsta _hgr_rowhi,x\ndex\ncpx #$ff\nbne flip\n'
    else:
        prefix='.bss\nbase: .res 1\n'+prefix+'lda base\neor #$60\nsta base\n'
    prefix+='ldx #191\nrows: lda _hgr_rowlo,x\nsta ptr1\nlda _hgr_rowhi,x\n'
    if variant=='fixed': prefix+='eor base\n'
    return prefix+'sta ptr1+1\ndex\ncpx #$ff\nbne rows\nrts\n'


def measure(work,name,call,dhgr=False,setup='',sprites=False,warmup=True,
            declarations='',sprite_width=None,sprite_height=4,sprite_stride=2,presentation=None,iie=False,cadence=False,
            pal=False,damage=False,variant=None,spr=None,clock=False):
    source=work/(name+'.c'); obj=source.with_suffix('.o'); binary=source.with_suffix('.bin')
    source.write_text('#include "hgr.h"\n#include "gfx.h"\n#include "dhgr.h"\n#include "apple2io.h"\n'
      'void hgr_build_tables(void); void bench_begin(void); void bench_end(void); void bench_present(void);\n'+
      (sprite_source(sprite_width,sprite_height,sprite_stride) if sprite_width else
       'static const unsigned char bits[64]={127,85,42,127};\n')+
      (('' if sprite_width else 'static const unsigned char mask[56]={0};\n')+
       'static const hgr_mspr_t shape={bits,mask,%d,%d};\n'%(sprite_stride,sprite_height)+
       'static unsigned char pool[%d];\n'%(8*sprite_stride*sprite_height) if sprites else '')+
      declarations+'\n'+
      'int main(void) {\n'+('unsigned char i; unsigned frame=0;\n' if sprites else '')+
      ('if (!dhgr_init()) return 1;' if dhgr else 'hgr_init();')+setup+
      (call*int(warmup) if not dhgr else '')+
      '\nbench_begin();\n'+call+
      '\nbench_end();\napple2_getkey(); return 0; }\n')
    run(['cl65','-t','none','-Oirs','-I',DEV/'lib/hgrc','-I',DEV/'lib/apple2c','-I',DEV/'lib/gfx','-c','-o',obj,source])
    mapfile=source.with_suffix('.map'); labels=source.with_suffix('.lbl')
    extra=[]
    if damage:
        from test_hgr import compile_source
        damage_obj=work/(name+'_damage.o')
        compile_source(DEV/'lib/hgrc/hgr_sprengine.c',damage_obj,
                       ['-t','none','-Oirs','-DHGR_SPR_DAMAGE=1','-I',DEV/'lib/hgrc',
                        '-I',DEV/'lib/apple2c'])
        extra.append(damage_obj)
    if variant:
        define,members=variant
        for member in members:
            variant_obj=work/(name+'_'+Path(member).stem+'.o')
            run(['ca65','-t','none','-D',define+'=1','-I',DEV/'lib/hgrc','-o',variant_obj,DEV/'lib/hgrc'/member])
            extra.append(variant_obj)
    if spr is not None:
        for member in SPR_SRCS:
            spr_obj=work/(name+'_'+Path(member).stem+'.o')
            run(['ca65','-t','none',*('-D'+d+'=1' for d in spr),'-I',DEV/'lib/hgrc','-I',DEV/'lib/apple2',
                 '-o',spr_obj,DEV/'lib/hgrc'/member])
            extra.append(spr_obj)
    if clock:
        for src in (DEV/'lib/apple2c/apple2vbl.s',DEV/'lib/apple2c/apple2frame.s',DEV/'lib/mouse/mouse.s'):
            clock_obj=work/(name+'_'+src.stem+'.o')
            run(['ca65','-t','none','-o',clock_obj,src])
            extra.append(clock_obj)
    if cadence:
        frame_obj=work/(name+'_frame.o')
        run(['ca65','-t','none','-o',frame_obj,DEV/'lib/apple2c/apple2frame.s'])
        extra.append(frame_obj)
    if presentation:
        asm=source.with_suffix('.s'); asm.write_text(presentation_source(presentation))
        asm_obj=work/(name+'_asm.o')
        run(['ca65','-t','none','-o',asm_obj,asm]); extra.append(asm_obj)
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-m',mapfile,'-Ln',labels,
         '-o',binary,work/'crt0_apple2.o',obj,work/'markers.o',work/'apple2io_asm.o',*extra,work/'hgrc.lib'])
    points=a2test.labels(labels)
    disk=a2test.build_disk(work,'BENCH',binary)
    emulator=DEV/'tools'/('a2shot/a2shot' if dhgr or iie else 'a2run/a2run')
    output=run([emulator,*(['--iie'] if dhgr or iie else []),*(['--pal'] if pal else []),'--disk',disk,
                f'until:{points["_bench_begin"]:04X}:1500',
                'hwstackwatch',f'stackwatch:{points["sp"]:02X}:{points["__STACKSTART__"]:04X}:{points["__STACKSIZE__"]:04X}',
                f'until:{points["_bench_end"]:04X}:1500','stack','hwstack'])
    ticks=[int(c) for c in re.findall(r'cycles=(\d+)',output)]
    assert len(ticks)==2
    peak,reserved,overflow=map(int,re.search(r'stack peak=(\d+) reserved=(\d+) overflow=(\d+)',output).groups())
    assert not overflow and peak < reserved,(name,'C stack overflow')
    hw_peak,hw_available,hw_overflow=map(int,re.search(r'hwstack peak=(\d+) available=(\d+) overflow=(\d+)',output).groups())
    assert not hw_overflow and hw_peak < hw_available,(name,'hardware stack overflow')
    sizes=segment_sizes(mapfile)
    loaded=sum(sizes.get(s,0) for s in ('CODE','STARTUP','ONCE','INIT','LOWCODE','RODATA','DATA'))
    assert loaded==binary.stat().st_size,(name,'unaccounted loaded segment/padding')
    linked=mapfile.read_text().split('Segment list:')[0]
    row=re.search(r'hgr_rows_asm\.o\):\s+CODE\s+Offs=[0-9A-F]+\s+Size=([0-9A-F]+)',linked)
    return dict(segments(mapfile),binary_bytes=binary.stat().st_size,cycles=ticks[1]-ticks[0]-12,
                row_kernel_bytes=int(row[1],16) if row else 0,
                c_stack_peak_bytes=peak,c_stack_reserved_bytes=reserved,
                hardware_stack_peak_bytes=hw_peak,hardware_stack_available_bytes=hw_available)


@lru_cache(None)
def identity(path):
    return dict(name=Path(path).name,sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())


def environment(dhgr, pal=False):
    runner=DEV/'tools'/('a2shot/a2shot' if dhgr else 'a2run/a2run')
    paths=[runner,DEV/'tools/a2shot/roms'/('apple2e.rom' if dhgr else 'apple2p.rom'),
           DEV/'tools/a2shot/roms/disk2.rom',DEV/'tools/dos33_system.bin']
    host={'Darwin-arm64':'darwin-arm64','Linux-x86_64':'linux-x86_64'}.get(platform.system()+'-'+platform.machine(),'')
    paths += ([DEV/'tools/a2shot/sdk/lib'/host/'libpom2_core.a'] if dhgr else
              [DEV/'tools/a2run/cpu6502.c', DEV/'tools/a2run/a2run.c'])
    return dict(cpu='65C02' if dhgr else 'NMOS6502',model='IIe enhanced 128K' if dhgr else 'II+ 48K',
                frame_cycles=20280 if pal else 17030,artifacts=[identity(p) for p in paths])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dhgr',action='store_true'); ap.add_argument('--check',action='store_true')
    ap.add_argument('--update',action='store_true'); ap.add_argument('--out',type=Path)
    ap.add_argument('--only',help='measure only the cases whose names start with one of these (comma-separated)')
    args=ap.parse_args()
    if args.check and args.update:ap.error('choose --check or --update')
    run(['make','-s','-C',DEV/'tools/a2run'])
    with tempfile.TemporaryDirectory(prefix='apple2-bench-') as directory:
        work=Path(directory); build(work)
        markers=work/'markers.s'
        markers.write_text('.export _bench_begin, _bench_end\n.segment "CODE"\n_bench_begin: rts\n_bench_end: rts\n')
        run(['ca65','-t','none','-o',work/'markers.o',markers])
        wanted=lambda name:not args.only or name.startswith(tuple(args.only.split(',')))
        results={name:measure(work,name,call,dhgr) for name,(call,dhgr) in CASES.items() if (args.dhgr or not dhgr) and wanted(name)}
        results.update({name:measure(work,name,**options) for name,options in SCENES.items() if (args.dhgr or not options.get('iie',False)) and wanted(name)})
    import subprocess
    version_result=subprocess.run(['cl65','--version'],capture_output=True,text=True,check=True)
    version=(version_result.stdout+version_result.stderr).strip()
    case_environments={name:('iie_pal' if SCENES.get(name,{}).get('pal',False) else
                            'iie' if CASES.get(name,('',False))[1] or SCENES.get(name,{}).get('iie',False) else 'nmos') for name in results}
    report=dict(schema=2,case_environments=case_environments,stack_sampling='coherent cc65 call/return/jump/(sp),Y boundaries; observed workload, not a static bound',compiler=version,flags='-Oirs',results=results,
                environments={mode:environment(mode.startswith('iie'),mode=='iie_pal') for mode in sorted(set(case_environments.values()))})
    stress=[m['cycles'] for n,m in results.items() if n.startswith(('hgr_scene_phase','hgr_scene_large'))]
    report['scene_max_cycles']=max(stress,default=0)
    report['hud_changed_max_cycles']=max((m['cycles'] for n,m in results.items() if n.startswith('hgr_hud_changed_phase')),default=0)
    report['absolute_budgets']={}
    absolute_failures=[]
    for name,policy in json.loads(BUDGETS.read_text()).items():
        if name not in results: continue
        entry=dict(policy,measured_cycles=results[name]['cycles'])
        entry['limit_cycles']=policy['refreshes']*policy['frame_cycles']-policy['reserved_cycles']
        entry['spare_cycles']=entry['limit_cycles']-entry['measured_cycles']
        report['absolute_budgets'][name]=entry
        if entry['spare_cycles']<0: absolute_failures.append(f'{name}: absolute deadline exceeded by {-entry["spare_cycles"]} cycles')
    for name,metrics in results.items():
        print(f'{name:16} {metrics["cycles"]:8} cycles  {metrics["binary_bytes"]:5} B binary  '+
              f'{metrics["code_bytes"]:5} B code  {metrics["ram_bytes"]:4} B RAM  {metrics["zp_bytes"]:3} B ZP  '+
              f'{metrics["c_stack_peak_bytes"]:2} B C stack peak  {metrics["hardware_stack_peak_bytes"]:2} B hardware stack peak')
    baseline=json.loads(BASELINE.read_text()) if BASELINE.exists() else dict(compiler=version,flags='-Oirs',results={})
    if args.update:
        baseline['compiler']=version;baseline['results'].update(results)
        baseline['schema']=2
        baseline.setdefault('environments',{}).update(report['environments'])
        baseline.setdefault('case_environments',{}).update(report['case_environments'])
        BASELINE.write_text(json.dumps(baseline,indent=2)+'\n')
    if args.out:args.out.write_text(json.dumps(report,indent=2)+'\n')
    if args.check:
        failures=list(absolute_failures)
        changed=set()
        # Small compiler differences are permitted, concrete regressions fail.
        for name,metrics in results.items():
            if name not in baseline['results']:failures.append(name+': missing baseline');continue
            previous=baseline.get('environments',{}).get(baseline.get('case_environments',{}).get(name))
            current=report['environments'][report['case_environments'][name]]
            if not previous: failures.append(name+': missing environment reference')
            if previous:
                for key in ('cpu','model','frame_cycles'):
                    if previous[key]!=current[key]: failures.append(name+': changed '+key)
                # A new emulator core or ROM is not a regression in itself: the
                # metrics are still held to the baseline below (a core that
                # counted cycles differently would show there), and the change
                # is reported. The hashes are recorded by --update.
                old_hash={a['name']:a['sha256'] for a in previous['artifacts']}
                for artifact in current['artifacts']:
                    if artifact['name'] in ('cpu6502.c','libpom2_core.a','apple2e.rom','apple2p.rom'):
                        if old_hash.get(artifact['name'])!=artifact['sha256']:
                            changed.add(artifact['name'])
            for key,value in metrics.items():
                if key not in baseline['results'][name]:
                    failures.append(name+': missing '+key+' reference');continue
                old=baseline['results'][name][key]
                margin=max(16,int(old*.05)) if key=='cycles' else 0 if key=='zp_bytes' else max(16,int(old*.03))
                if value>old+margin:failures.append(f'{name}.{key}: {value} > {old}+{margin}')
        if changed:
            print('Note: core/ROM changed since the baseline ('+', '.join(sorted(changed))+
                  '): metrics compared anyway; --update records the new hashes.')
        if failures:raise SystemExit('\n'.join(failures))
        print('Performance budgets passed.')
    print('Maximum measured stress scene:',report['scene_max_cycles'],'cycles (without VBL/game logic).')
    for name,budget in report['absolute_budgets'].items():
        print(f'{name}: {budget["measured_cycles"]}/{budget["limit_cycles"]} cycles, '+
              f'{budget["reserved_cycles"]} additionally reserved for game/audio/IRQ')

if __name__=='__main__':main()
