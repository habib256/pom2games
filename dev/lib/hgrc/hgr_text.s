; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Doubled white/color text, cc65 fastcall. One shared rendering path.
; puts: A/X = string, C stack = y, x low, x high.
; color: A = color, C stack = string low/high, y, x low/high.
.export _hgr_puts, _hgr_puts_color
.import _hgr_set_carrier, popax, incsp3
.import _hgr_build_rows, _hgr_build_columns, _hgr_build_phases
.import _hgr_col7, _hgr_phase7, _hgr_font, _hgr_puts_run
.importzp sp, _hgr_g_y, _hgr_t_col, _hgr_t_bit, _hgr_t_n, _hgr_t_s, _hgr_t_font
.importzp _hgr_z_ce, _hgr_z_co, _hgr_z_hi
.code
_hgr_puts_color:
        jsr _hgr_set_carrier
        cmp #0                  ; carrier result is in A, not the return flags
        beq white_color
        jsr popax
        jmp common
white_color:
        jsr popax
_hgr_puts:
        ldy #$7f
        sty _hgr_z_ce
        sty _hgr_z_co
        ldy #0
        sty _hgr_z_hi
common:
        sta _hgr_t_s             ; builders preserve text and carrier parameters
        stx _hgr_t_s+1
        jsr _hgr_build_rows
        jsr _hgr_build_columns
        jsr _hgr_build_phases
        ldy #0
        lda (sp),y
        cmp #177
        bcs done
        sta _hgr_g_y
        ldy #2
        lda (sp),y
        beq low_x
        cmp #1
        bne done
        dey
        lda (sp),y
        cmp #9
        bcs done                ; x > 264
        tax
        lda #1                  ; x=256..264 always fits one cell
        sta _hgr_t_n
        lda _hgr_col7+256,x
        ldy _hgr_phase7+256,x
        bcc pen                 ; CMP #9 left C=0
low_x:
        dey
        lda (sp),y
        tax
        lda #<264
        sec
        sbc (sp),y
        ldy #15
        bcs counted             ; x=0..8: room=256..264, fifteen cells
        ; Borrow cancels the high byte. A is the full room, 0..255.
        ; Count floor(room/18)+1 while retaining X for the table lookups.
        ldy #0
        sec
count:  iny
        sbc #18
        bcs count
counted:
        sty _hgr_t_n
        lda _hgr_col7,x
        ldy _hgr_phase7,x
pen:
        sta _hgr_t_col
        sty _hgr_t_bit
        lda #<_hgr_font
        sta _hgr_t_font
        lda #>_hgr_font
        sta _hgr_t_font+1
        jsr _hgr_puts_run
done:
        jmp incsp3
