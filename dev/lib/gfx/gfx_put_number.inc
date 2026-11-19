; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; A/X holds the input word. buffer_size includes the terminating NUL.
.macro gfx_put_number convert, buffer_size
        ; Save the fastcall word only while reserving and passing the buffer.
        pha
        txa
        pha
        lda sp
        sec
        sbc #buffer_size
        sta sp
        bcs :+
        dec sp+1
:       lda sp
        ldx sp+1
        jsr pushax
        pla
        tax
        pla
        jsr convert
        ; Conversion consumed its pointer; sp now points to the local buffer.
        lda sp
        ldx sp+1
        jsr _gfx_text
        lda sp
        clc
        adc #buffer_size
        sta sp
        bcc :+
        inc sp+1
:       rts
.endmacro
