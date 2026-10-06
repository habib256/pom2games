; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; 80STORE remains OFF. RAMWRT selects writes; auxiliary reads execute
; from zero page so RAMRD cannot switch out the running code. IRQ state
; is preserved. No stack/source-data access while RAMRD is auxiliary.
.include "apple2.inc"
.export _dhgr_init, _dhgr_text_restore, _dhgr_capabilities
.export _dhgr_show_page
.import _dhgr_base, _dhgr_display
.importzp ptr1
.export aux_read
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
