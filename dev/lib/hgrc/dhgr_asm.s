; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; 80STORE remains OFF. RAMWRT selects writes; auxiliary reads execute
; from zero page so RAMRD cannot switch out the running code. IRQ state
; is preserved. No stack/source-data access while RAMRD is auxiliary.
.include "apple2.inc"
.export _dhgr_init, _dhgr_text_restore, _dhgr_capabilities
.export _dhgr_write_asm, _dhgr_read_asm, _dhgr_clear_asm, _dhgr_show_page
.import _dhgr_addr, _dhgr_aux, _dhgr_mask, _dhgr_bits, _dhgr_pattern
.import _dhgr_base, _dhgr_display
.importzp ptr1, tmp1, tmp2, tmp3, tmp4
.export aux_read
.export _dhgr_span_asm
.import _dhgr_first, _dhgr_last, _dhgr_first_mask, _dhgr_last_mask
RAMRDON = $C003
RAMWRTON = $C005

.segment "ZEROPAGE"
aux_read: .res 9
.segment "CODE"
read_template:
        sta RAMRDON
        lda (ptr1),y
        sta RAMRDOFF
        rts

; Safe on II/II+. Probe restores RAM holes and all video switches it uses.
; Entry contract: main RAMRD/RAMWRT and main zero page, normal ROM.
_dhgr_capabilities:
        lda $FBB3
        cmp #$06
        beq @extended
        lda #0
        tax
        rts
@extended:
        php
        sei
        ldx #8
@copy:  lda read_template,x
        sta aux_read,x
        dex
        bpl @copy
        lda $C018              ; preserve 80STORE
        pha
        lda #0
        sta STORE80OFF
        sta RAMRDOFF
        sta RAMWRTOFF
        lda #$78
        sta ptr1
        lda #$20
        sta ptr1+1
        ldy #0
        lda (ptr1),y
        pha
        jsr aux_read
        pha
        lda #$55
        sta (ptr1),y
        sta RAMWRTON
        lda #$AA
        sta (ptr1),y
        sta RAMWRTOFF
        lda (ptr1),y
        cmp #$55
        bne @absent
        jsr aux_read
        cmp #$AA
        bne @absent
        ; Upper video memory must be independent of main and lower aux RAM.
        lda #$40
        sta ptr1+1
        lda (ptr1),y
        pha
        jsr aux_read
        pha
        lda #$66
        sta (ptr1),y
        sta RAMWRTON
        lda #$33
        sta (ptr1),y
        sta RAMWRTOFF
        lda (ptr1),y
        cmp #$66
        bne @upper_absent
        jsr aux_read
        cmp #$33
        bne @upper_absent
        lda #$20
        sta ptr1+1
        jsr aux_read
        cmp #$AA
        bne @upper_absent
        ldx #3
        bne @restore_upper
@upper_absent:
        ldx #1
@restore_upper:
        lda #$40
        sta ptr1+1
        pla
        sta RAMWRTON
        sta (ptr1),y
        sta RAMWRTOFF
        pla
        sta (ptr1),y
        lda #$20
        sta ptr1+1
        jmp @restore
@absent:
        ldx #1
@restore:
        pla
        sta RAMWRTON
        sta (ptr1),y
        sta RAMWRTOFF
        pla
        sta (ptr1),y
        pla
        bpl @store_off
        sta STORE80ON
@store_off:
        txa
        ldx #0
        plp
        rts

_dhgr_init:
        jsr _dhgr_capabilities
        cmp #3
        beq @ok
        lda #0
        rts
@ok:    lda #0
        sta STORE80OFF
        sta COL80ON
        bit LOWSCR
        bit HIRES
        bit MIXCLR
        bit DHIRES_ON
        bit TXTCLR
        lda #$20
        sta _dhgr_base
        lda #1
        sta _dhgr_display
        ldx #0
        rts

_dhgr_text_restore:
        lda $FBB3
        cmp #$06
        bne @legacy
        lda #0
        sta RAMRDOFF
        sta RAMWRTOFF
        sta STORE80OFF
        sta COL80OFF
        bit DHIRES_OFF
@legacy:
        bit TXTSET
        bit LOWSCR
        bit MIXCLR
        bit LORES
        rts

; fastcall A=1/2, invalid values ignored. This never changes the draw page.
_dhgr_show_page:
        cmp #1
        beq @one
        cmp #2
        bne @done
        bit HISCR
        jmp @save
@one:   bit LOWSCR
@save:  sta _dhgr_display
@done:  rts

select:
        lda _dhgr_addr
        sta ptr1
        lda _dhgr_addr+1
        sta ptr1+1
        ldy #0
        rts
read:
        lda _dhgr_aux
        beq @main
        jmp aux_read
@main:  lda (ptr1),y
        rts
_dhgr_write_asm:
        php
        sei
        jsr select
        lda _dhgr_mask
        cmp #$7F
        beq @whole
        jsr read
        sta tmp1
        lda _dhgr_mask
        eor #$FF
        and tmp1
        ora _dhgr_bits
        jmp @write
@whole: lda _dhgr_bits
@write: sta tmp1
        lda _dhgr_aux
        beq @main
        sta RAMWRTON
@main:  lda tmp1
        sta (ptr1),y
        sta RAMWRTOFF
        plp
        rts
_dhgr_read_asm:
        php
        sei
        jsr select
        jsr read
        ldx #0
        plp
        rts
_dhgr_clear_asm:
        php
        sei
        sta RAMWRTON
        lda _dhgr_pattern
        sta tmp1
        lda _dhgr_pattern+2
        sta tmp2
        jsr fill_bank
        sta RAMWRTOFF
        lda _dhgr_pattern+1
        sta tmp1
        lda _dhgr_pattern+3
        sta tmp2
        jsr fill_bank
        plp
        rts
fill_bank:
        lda _dhgr_base
        sta ptr1+1
        clc
        adc #$20
        tax
        ldy #0
        sty ptr1
@pair:  lda tmp1
        sta (ptr1),y
        iny
        lda tmp2
        sta (ptr1),y
        iny
        bne @pair
        inc ptr1+1
        cpx ptr1+1
        bne @pair
        rts

; One scanline, interleaved byte indices first..last. Full bytes use stores,
; only the two edges read/modify/write. IRQ masking covers one row.
_dhgr_span_asm:
        php
        sei
        lda _dhgr_addr
        sta ptr1
        lda _dhgr_addr+1
        sta ptr1+1
        lda _dhgr_first
        sta tmp2
@byte:  lda #$7F
        sta tmp3
        lda tmp2
        cmp _dhgr_first
        bne @last
        lda _dhgr_first_mask
        sta tmp3
@last:  lda tmp2
        cmp _dhgr_last
        bne @pattern
        lda _dhgr_last_mask
        and tmp3
        sta tmp3
@pattern:
        lda tmp2
        and #3
        tax
        lda _dhgr_pattern,x
        and tmp3
        sta tmp4
        lda tmp2
        lsr
        tay
        lda tmp3
        cmp #$7F
        beq @value
        lda tmp2
        and #1
        bne @read_main
        jsr aux_read
        jmp @merge
@read_main:
        lda (ptr1),y
@merge: sta tmp1
        lda tmp3
        eor #$FF
        and tmp1
        ora tmp4
        sta tmp4
@value: lda tmp2
        and #1
        bne @write_main
        sta RAMWRTON
@write_main:
        lda tmp4
        sta (ptr1),y
        sta RAMWRTOFF
        lda tmp2
        cmp _dhgr_last
        beq @done
        inc tmp2
        jmp @byte
@done:  plp
        rts
