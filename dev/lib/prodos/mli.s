; VERHILLE Arnaud — GPL-3.0. Main-bank cc65 MLI wrapper.
; Writable main RAM; non-reentrant. Public command/parameter fields are the
; inline MLI record itself: initially zero, retaining the last request.
.export _prodos_call, _prodos_command, _prodos_params, _prodos_format_ram
_prodos_command = command
_prodos_params = params
.code
_prodos_call:
        jsr $BF00
command: .byte 0
params: .word 0
        bcs failed
        lda #0
failed: ldx #0
        rts
; FORMAT restores /RAM after the application has used its auxiliary memory.
; fastcall A = /RAM unit. Driver address is fixed $FF00 in LC bank 1.
_prodos_format_ram:
        sta $43
        lda #3
        sta $42
        lda #0
        sta $44
        sta $46
        sta $47
        lda #$20
        sta $45
        php
        sei
        lda $C08B
        lda $C08B
        jsr $FF00
        lda #0
        bcs :+
        lda #1
:       bit $C082
        plp
        ldx #0
        rts
