; Robot Space Station — the overlays: $4000-$5FFF (main DHGR page 2, never
; shown) holds the code of one group of screens at a time, copied from
; auxiliary memory when a screen of another group opens (src/game.cfg):
; 1 PLAY (zone.c, sprites.c: the room and the drones) from aux $4000,
; 2 FRONT (title.c, help.c, the briefing and boot parts of main.c) from
; aux $A000. RSS.OVL put both there at boot. Their state lives in
; resident BSS/DATA: a copy only replaces code and tables.
; Rule: code in an overlay never makes a switch happen (directly or by a
; call) and then goes on: it would come back into the other overlay.
.setcpu "65C02"
.import __PLAYDATA_RUN__, __PLAYDATA_SIZE__, __FRONTDATA_RUN__, __FRONTDATA_SIZE__
.export _overlay_use, _overlay_cur

RAMRDOFF = $C002
RAMRDON = $C003

.segment "ZEROPAGE"
; The page copy runs in zero page, which RAMRD leaves alone (the code in
; main RAM would vanish under it): 14 cycles a byte.
ZLEN = 16
zcopy:  .res ZLEN
ZSRC = zcopy + 5                        ; the operands' high bytes
ZDST = zcopy + 8

.segment "BSS"
_overlay_cur: .res 1                    ; the overlay in place (0: none yet)
count:  .res 1
src:    .res 1                          ; the pages copied next
dst:    .res 1

.segment "RODATA"
aux_page: .byte 0, $40, $A0
pages:  .byte 0, >(__PLAYDATA_RUN__ + __PLAYDATA_SIZE__ + $FF) - $40
        .byte >(__FRONTDATA_RUN__ + __FRONTDATA_SIZE__ + $FF) - $40
; Aux page ZSRC to main page ZDST (Y = 0).
ztemplate:
        sta RAMRDON
zsrc = * + 2
:       lda $FF00,y
zdst = * + 2
        sta $FF00,y
        iny
        bne :-
        sta RAMRDOFF
        rts
zend:
.assert zend - ztemplate = ZLEN, error, "zcopy's length"
.assert zsrc - ztemplate = 5 && zdst - ztemplate = 8, error, "zcopy's operands"

.segment "CODE"
; overlay_use(n): overlay n in $4000-$5FFF, copied only if another is
; there; a page at a time, interrupts masked during each.
_overlay_use:
        cmp _overlay_cur
        beq @done
        sta _overlay_cur
        tax
        lda aux_page,x
        sta src
        lda pages,x
        sta count
        lda #$40
        sta dst
        ldx #ZLEN - 1
@put:   lda ztemplate,x
        sta zcopy,x
        dex
        bpl @put
@page:  lda src
        sta ZSRC
        lda dst
        sta ZDST
        ldy #0
        php
        sei
        jsr zcopy
        plp
        inc src
        inc dst
        dec count
        bne @page
@done:  rts
