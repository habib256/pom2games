; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_puts8(unsigned x, byte y, string*), cc65 fastcall.
; A/X = string pointer, C stack = y, x low, x high.
; Native white 8x8 text; retain lazy table builds even on rejected calls.
.export _hgr_puts8
.import _hgr_build_rows, _hgr_build_columns, _hgr_build_phases
.import _hgr_col7, _hgr_phase7, _hgr_font, _hgr_puts_run8, incsp3
.importzp sp, _hgr_g_y, _hgr_t_col, _hgr_t_bit, _hgr_t_n, _hgr_t_s, _hgr_t_font
.code
_hgr_puts8:
        sta _hgr_t_s             ; builders do not touch the string state
        stx _hgr_t_s+1
        jsr _hgr_build_rows
        jsr _hgr_build_columns
        jsr _hgr_build_phases
        ldy #0
        lda (sp),y
        cmp #185
        bcs done
        sta _hgr_g_y
        ldy #2
        lda (sp),y
        beq low_x
        cmp #1
        bne done
        dey
        lda (sp),y
        cmp #18
        bcs done                ; x > 273
        tax
        lda _hgr_col7+256,x
        ldy _hgr_phase7+256,x
        bcc pen                 ; CMP #18 left C=0
low_x:
        dey
        lda (sp),y
        tax
        lda _hgr_col7,x
        ldy _hgr_phase7,x
pen:
        sta _hgr_t_col
        sty _hgr_t_bit
        ; floor((273-x)/8)+1 = floor((281-x)/8), for every valid x.
        ; The difference is <=281, so the high byte has just one bit.
        ldy #1
        lda #<281
        sec
        sbc (sp),y
        tax
        iny
        lda #>281
        sbc (sp),y
        lsr a
        txa
        ror a
        lsr a
        lsr a
        sta _hgr_t_n
        lda #<_hgr_font
        sta _hgr_t_font
        lda #>_hgr_font
        sta _hgr_t_font+1
        jsr _hgr_puts_run8
done:
        jmp incsp3
