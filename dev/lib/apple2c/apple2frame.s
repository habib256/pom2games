; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Main ROM/RAM entry; no ZP allocation and no changes to IRQ/video state.
; ROM IDs: Apple Miscellaneous Technical Note #7. C019: IIGS Note #40.
.export _a2_frame_init, _a2_frame_mode, _a2_frame_set_delay, _a2_frame_wait

.segment "BSS"
frame_mode: .res 1
frame_delay: .res 1

.segment "CODE"
_a2_frame_init:
        lda #80
        sta frame_delay
        lda #0
        sta frame_mode
        lda $FBB3
        cmp #$06
        bne _a2_frame_mode
        lda $FBC0
        cmp #$EA                ; original IIe
        beq @checkgs
        cmp #$E0                ; enhanced IIe (also IIgs compatibility ROM)
        bne _a2_frame_mode      ; IIc $00: never poll its interrupt latch
@checkgs:
        sec
        jsr $FE1F              ; RTS on IIe; clears carry on IIgs
        bcc _a2_frame_mode
        inc frame_mode
_a2_frame_mode:
        lda frame_mode
        ldx #0
        rts

_a2_frame_set_delay:
        cmp #0
        bne @save
        lda #1
@save:  sta frame_delay
        rts

_a2_frame_wait:
        lda frame_mode
        beq delay_wait
        ldx #0
        ldy #0
@active:
        bit $C019
        bmi @waitblank         ; leave an existing VBL interval first
        dex
        bne @active
        dey
        bne @active
        beq timeout
@waitblank:
        ldx #0
        ldy #0
@blank:
        bit $C019
        bpl _a2_frame_mode     ; fresh VBL edge
        dex
        bne @blank
        dey
        bne @blank
timeout:
        lda #0
        sta frame_mode
delay_wait:
        lda frame_delay
        bne @wait
        lda #80                ; usable fallback even before explicit init
@wait:  jsr $FCA8              ; Monitor WAIT, no video/interrupt side effects
        jmp _a2_frame_mode
