; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Backend-neutral printable/control handling. The row comparison is promoted
; in C: row 255 must never overflow to zero when advancing a zero-sized grid.
.export _gfx_putc
.import _gfx_cursor_col, _gfx_cursor_row, _gfx_text_cols, _gfx_text_rows
.import _gfx_cell_glyph, pusha
.code
_gfx_putc:
        cmp #10
        beq newline
        cmp #13
        beq carriage
        cmp #32
        bcc done
        jsr pusha
        lda _gfx_cursor_col
        jsr pusha
        lda _gfx_cursor_row
        jsr _gfx_cell_glyph
        inc _gfx_cursor_col
        lda _gfx_cursor_col
        cmp _gfx_text_cols
        bcc done
newline:
        ldx _gfx_cursor_row
        inx
        beq carriage            ; row 255 wraps here, never in the stored cursor
        cpx _gfx_text_rows
        bcs carriage
        stx _gfx_cursor_row
carriage:
        lda #0
        sta _gfx_cursor_col
done:
        rts
