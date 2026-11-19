; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; C holds the interleaved byte index's low bit: even is auxiliary.
.macro dhgr_select_byte_bank
        lda #0
        rol
        eor #1
        sta _dhgr_aux
.endmacro

; A = byte column within one bank, X = scanline; use the current draw page.
.macro dhgr_set_row_address
        clc
        adc dhgr_rowlo,x        ; visible row + column never carries
        sta _dhgr_addr
        lda dhgr_rowhi,x
        ora _dhgr_base
        sta _dhgr_addr+1
.endmacro

; Copy a row buffer pointer from the cc65 frame; leave Y on its high byte.
.macro dhgr_load_buffer_pointer dest
        lda (sp),y
        sta dest
        iny
        lda (sp),y
        sta dest+1
.endmacro

; The row kernel may overwrite scratch. Keep height and y in the cc65
; argument frame, leaving y on the last visible row when height reaches zero.
.macro dhgr_next_transfer_row height_slot, y_slot, done
        ldy #height_slot
        lda (sp),y
        sec
        sbc #1
        sta (sp),y
        beq done
        ldy #y_slot
        lda (sp),y
        clc
        adc #1
        sta (sp),y
.endmacro

; Both rejection and completion consume the entire caller frame.
.macro dhgr_return_from_transfer size
        lda sp
        clc
        adc #size
        sta sp
        bcc :+
        inc sp+1
:       rts
.endmacro
