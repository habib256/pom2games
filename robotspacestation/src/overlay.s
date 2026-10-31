; Robot Space Station — the overlays: $4000-$5FFF (main DHGR page 2, never
; shown) holds the code of one group of screens at a time, copied from
; auxiliary memory when a screen of another group opens (src/game.cfg):
; 1 PLAY (zone.c, sprites.c, sprites_asm.s and the DHGR compositor's
; DHGRSPRCODE: the room and the drones) from aux $4000,
; 2 FRONT (title.c, help.c, the briefing and boot parts of main.c) from
; aux $A000. RSS.OVL put both there at boot. Their state lives in
; resident BSS/DATA: a copy only replaces code and tables.
; Rule: code in an overlay never makes a switch happen (directly or by a
; call) and then goes on: it would come back into the other overlay.
.setcpu "65C02"
.import __PLAYDATA_RUN__, __PLAYDATA_SIZE__, __FRONTDATA_RUN__, __FRONTDATA_SIZE__
.export _overlay_use, _overlay_cur

.import aux_fetch_pages                  ; dev/lib/apple2c/apple2auxfetch.s

.segment "BSS"
_overlay_cur: .res 1                    ; the overlay in place (0: none yet)

.segment "RODATA"
aux_page: .byte 0, $40, $A0
pages:  .byte 0, >(__PLAYDATA_RUN__ + __PLAYDATA_SIZE__ + $FF) - $40
        .byte >(__FRONTDATA_RUN__ + __FRONTDATA_SIZE__ + $FF) - $40
.segment "CODE"
; overlay_use(n): overlay n in $4000-$5FFF, copied only if another is
; there; a page at a time from the zero page (RAMRD aux hides main RAM's
; code), interrupts masked during each (aux_fetch_pages).
_overlay_use:
        cmp _overlay_cur
        beq @done
        sta _overlay_cur
        tay
        ldx aux_page,y
        lda pages,y
        ldy #$40
        jmp aux_fetch_pages
@done:  rts
