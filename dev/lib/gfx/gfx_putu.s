; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Native numeric text entry; the matching .c file is the portable reference.
.export _gfx_putu
.import pushax, _gfx_utoa, _gfx_text
.importzp sp
.code
_gfx_putu:
        ; Save the fastcall word only while reserving and passing the buffer.
        pha
        txa
        pha
        lda sp
        sec
        sbc #6
        sta sp
        bcs :+
        dec sp+1
:       lda sp
        ldx sp+1
        jsr pushax
        pla
        tax
        pla
        jsr _gfx_utoa
        ; Conversion consumed its pointer; sp now points to the local buffer.
        lda sp
        ldx sp+1
        jsr _gfx_text
        lda sp
        clc
        adc #6
        sta sp
        bcc :+
        inc sp+1
:       rts
