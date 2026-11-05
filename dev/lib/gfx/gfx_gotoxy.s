; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; gfx_gotoxy(col,row): A=row, one byte col on the C stack.
; Byte grid dimensions preserve the portable C's clamp/underflow behavior.
.export _gfx_gotoxy
.import _gfx_cursor_col, _gfx_cursor_row, _gfx_text_cols, _gfx_text_rows
.importzp sp
.code
_gfx_gotoxy:
        cmp _gfx_text_rows
        bcc row_ready
        lda _gfx_text_rows
        sec
        sbc #1
row_ready:
        sta _gfx_cursor_row
        ldy #0
        lda (sp),y
        cmp _gfx_text_cols
        bcc col_ready
        lda _gfx_text_cols
        sec
        sbc #1
col_ready:
        sta _gfx_cursor_col
        inc sp
        bne :+
        inc sp+1
:       rts
