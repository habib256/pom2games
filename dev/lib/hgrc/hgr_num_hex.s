; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_putx(x,y,value), cc65 fastcall: A/X=value, C stack=y,xlo,xhi.
; Keep the value in tmp3/X while arranging the conversion pointer,
; relocated coordinates and five-byte local buffer in one stack reservation.
.include "hgr_num_frame.inc"
.export _hgr_putx
.import addysp, _gfx_hexstr, _hgr_puts
.importzp sp, ptr1, tmp3
.code
_hgr_putx:
        sta tmp3
        ; A is saved and X remains untouched throughout frame preparation.
        hgr_reserve_stack 7
        hgr_move_coords 7, 2
        ; Stack: conversion buffer pointer, y/x, buffer[5]. gfx_hexstr
        ; consumes its pointer; puts consumes y/x; then release the buffer.
        ldy #0
        clc
        lda sp
        adc #5
        sta (sp),y
        lda sp+1
        adc #0
        iny
        sta (sp),y
        lda tmp3
        jsr _gfx_hexstr
        lda ptr1                ; converter leaves its destination intact
        ldx ptr1+1
        hgr_draw_number _hgr_puts, 5
