; WARGALAGA II -- the shop screen (lot 7), and Memory Station (lot 8,
; memory.s) in the same overlay. Included by game.s.
; An overlay: linked to run at $4000 (segment SHOP, memory SHOPM, file
; build/game.bin.shop), kept in aux memory at SHOP_AUX (end of WG2.AUX) and
; copied over HGR page 2 by shop_run while page 1 shows the shop. Slow
; routines are fine here (a fixed screen): render.s's glyphs and rect_sta.
; The rules (prices, limits, ranks) are logic.s's shop_room / shop_can /
; shop_buy / shop_exit, checked against tools/model.py.
;
; Keys: <- or up / -> or down move, RETURN or SPACE buys, ESC leaves (as
; LEAVE does). Stick (TAB mode): paddle 1 up / down, button 0 buys.

SH_LINE0   = 5                  ; first item's text line (8 rows a line)
SH_LEAVE   = NITEM              ; the cursor on LEAVE
SH_NAME    = 4                  ; columns
SH_PRICE   = 18
SH_STATE   = 24
SH_MARKS   = 21                 ; line of the marks
SH_REPEAT  = 6                  ; stick: loops between two moves

.segment "SHOP"
shop_screen:
        lda #0                   ; drawing on page 1, shown
        jsr select_page
        lda #<sh_static
        sta ptr
        lda #>sh_static
        sta ptr+1
        jsr sh_texts
        ldx #0                   ; item names and prices
:       jsr sh_item
        inx
        cpx #NITEM
        bne :-
        stz sh_cur
        stz sh_held
        stz sh_rep
        stz sh_ev
        lda #DUET_EVENT_SLICES
        sta sh_sl
        lda #$80                 ; a key cuts the slice short
        sta DUET_KEYS
sh_redraw:
        jsr sh_state
sh_loop:
        jsr sh_tick              ; ~1/30 s
        jsr sound_frame
        jsr sh_input             ; A: 0 nothing, 1 up, 2 down, 3 select, 4 leave
        beq sh_loop
        cmp #4
        beq sh_leave
        cmp #3
        beq sh_select
        pha
        ldx sh_cur               ; the old cursor off
        jsr sh_line
        sta sh_row
        lda #' '
        ldy #2
        jsr sh_putc
        pla
        ldx sh_cur
        cmp #1
        bne :+
        dex                      ; up, wrapping
        bpl sh_moved
        ldx #SH_LEAVE
        bra sh_moved
:       inx                      ; down, wrapping
        cpx #SH_LEAVE+1
        bcc sh_moved
        ldx #0
sh_moved:
        stx sh_cur
        bra sh_redraw
sh_select:
        ldx sh_cur
        cpx #SH_LEAVE
        beq sh_leave
        jsr shop_buy
        bcc :+
        lda #EV_ARMOUR           ; bought: a chime
        tsb snd_ev
        bra sh_redraw
:       lda #EV_SHOT             ; not possible
        tsb snd_ev
        bra sh_loop
sh_leave:
        rts

; ~1/30 s: on the speaker (no card, sound on) DUET_TICK slices of the
; tune's two voices (duet.asm, sound.inc), else a Monitor WAIT.
sh_tick:
        lda audio_slot
        bne :+
        lda music_on
        bne sh_duet
:       lda #110
        jmp $FCA8
sh_duet:
        ldy sh_ev
        ldx duet_bass,y
        lda duet_mel,y
        ldy #DUET_TICK
        jsr DUET_PLAY
        lda sh_sl
        sec
        sbc #DUET_TICK
        sta sh_sl
        bne sh_ticked
        lda #DUET_EVENT_SLICES   ; the next event, the tune looping
        sta sh_sl
        inc sh_ev
        lda sh_ev
        cmp #DUET_EVENTS
        bcc sh_ticked
        stz sh_ev
sh_ticked:
        rts

; X = item (or SH_LEAVE) -> A = the top row of its line. Keeps X.
sh_line:
        txa
        clc
        adc #SH_LINE0
        cpx #SH_LEAVE
        bcc :+
        inc a                    ; LEAVE: a line below the items
:       asl
        asl
        asl
        rts

; Item X's name and price. Keeps X.
sh_item:
        jsr sh_line
        sta sh_row
        stx sh_x
        txa                      ; name at item_name + 12 X (8 X + 4 X)
        asl
        asl
        sta tmp
        asl
        clc
        adc tmp
        adc #<item_name
        sta ptr
        lda #>item_name
        adc #0
        sta ptr+1
        ldx #ITEM_NAME
        ldy #SH_NAME
        jsr sh_chars
        ldx sh_x
        stz sh_lead              ; price: 4 BCD digits, no leading 0
        lda item_hi,x
        ldy #SH_PRICE
        jsr sh_bcd
        ldx sh_x
        lda item_lo,x
        jsr sh_bcd_last
        ldx sh_x
        rts

; Everything that changes: credits, rank, gauges, MAX flags, marks, cursor.
sh_state:
        lda #3*8                 ; CREDITS dddd
        sta sh_row
        stz sh_lead
        lda credits+1
        ldy #10
        jsr sh_bcd
        lda credits
        jsr sh_bcd_last
        lda rank                 ; RANK nn
        ldy #36
        jsr sh_dec2
        lda #18*8                ; SPEED BULLETS TIME
        sta sh_row
        lda s_level
        ldy #8
        jsr sh_dec2
        lda shot_limit
        ldy #20
        jsr sh_dec2
        lda t_level
        ldy #31
        jsr sh_dec2
        lda #19*8                ; ARMOUR LIVES WEAPON
        sta sh_row
        lda armour
        ldy #8
        jsr sh_dec2
        lda lives
        ldy #20
        jsr sh_dec2
        lda weapon
        inc a
        ldy #31
        jsr sh_dec2
        ldx #0                   ; MAX: the item at its limit
sh_max: jsr sh_line
        sta sh_row
        stx sh_x
        jsr shop_room            ; C = 1: room left
        lda #<sh_max_txt
        ldy #>sh_max_txt
        bcc :+
        lda #<sh_no_txt
        ldy #>sh_no_txt
:       sta ptr
        sty ptr+1
        ldx #3
        ldy #SH_STATE
        jsr sh_chars
        ldx sh_x
        inx
        cpx #NITEM
        bne sh_max
        lda #SH_MARKS*8          ; marks: the six colours, then the dark one
        sta r_row
        ldx #0
sh_mark:
        lda sh_bit,x
        and marks
        beq :+
        txa
        clc
        adc #K_MARK0
:       jsr sh_icon_x
        inx
        cpx #6
        bne sh_mark
        lda mark_dark
        beq :+
        lda #K_MARK0+6
:       jsr sh_icon_x
        ldx sh_cur               ; the cursor
        jsr sh_line
        sta sh_row
        lda #'>'
        ldy #2
        jmp sh_putc

; Icon A (0: blank) in mark slot X (columns 10, 14 ... 34: even, or the
; colours swap, violet <-> blue and green <-> orange). Keeps X.
sh_icon_x:
        phx
        tay
        bne :+
        lda #<sh_blank
        sta src
        lda #>sh_blank
        sta src+1
        bra :++
:       jsr icon_src
:       txa
        asl
        asl
        adc #10
        sta r_col
        lda #2
        sta r_w
        lda #OBJ_H
        sta r_h
        lda r_row
        pha
        jsr rect_sta
        pla
        sta r_row
        plx
        rts

; The fixed texts: (line, column, characters..., 0) ..., $FF.
sh_texts:
        ldy #0
        lda (ptr),y
        cmp #$FF
        beq sh_t_done
        asl
        asl
        asl
        sta sh_row
        iny
        lda (ptr),y
        sta sh_col
        iny
:       lda (ptr),y
        beq :+
        phy
        ldy sh_col
        jsr sh_putc
        inc sh_col
        ply
        iny
        bra :-
:       iny                      ; next record: ptr += Y
        tya
        clc
        adc ptr
        sta ptr
        bcc sh_texts
        inc ptr+1
        bra sh_texts
sh_t_done:
        rts

; X characters from (ptr) at column Y, line sh_row.
sh_chars:
        stx sh_n
        sty sh_col
        ldy #0
:       lda (ptr),y
        phy
        ldy sh_col
        jsr sh_putc
        inc sh_col
        ply
        iny
        cpy sh_n
        bne :-
        rts

; BCD byte A as two digits at column Y (Y += 2), leading zeros as spaces
; while sh_lead is clear; sh_bcd_last: the units digit always shown.
sh_bcd:
        pha
        lsr
        lsr
        lsr
        lsr
        jsr sh_digit
        pla
        and #15
        bra sh_digit
sh_bcd_last:
        pha
        lsr
        lsr
        lsr
        lsr
        jsr sh_digit
        sec
        ror sh_lead
        pla
        and #15
        ; fall through
sh_digit:                        ; A = 0..9 at column Y, Y + 1
        bne :+
        bit sh_lead
        bmi :+
        lda #' '
        bra sh_putc_next
:       sec
        ror sh_lead
        ora #'0'
sh_putc_next:
        jsr sh_putc
        iny
        rts

; A = 0..99 as two characters at column Y (tens blank if 0).
sh_dec2:
        ldx #0
:       cmp #10
        bcc :+
        sbc #10
        inx
        bra :-
:       pha
        stz sh_lead
        txa
        jsr sh_digit
        sec
        ror sh_lead
        pla
        bra sh_digit

; Character A at column Y, line sh_row (its top row). Keeps Y.
sh_putc:
        sty col
        sty sh_y
        ldx sh_row
        jsr glyph
        ldy sh_y
        rts

; Keys and stick -> A: 0 nothing, 1 up, 2 down, 3 select, 4 leave.
sh_input:
        lda $C000
        bpl sh_stick
        bit $C010
        and #$7F
        ldx #sh_keys_end-sh_keys-1
:       cmp sh_keys,x
        beq :+
        dex
        bpl :-
        lda #0
        rts
:       lda sh_acts,x
        rts
sh_stick:
        lda joy_mode
        beq sh_none
        lda $C061                ; button 0: a press buys
        bpl :+
        lda sh_held
        bne sh_none2
        inc sh_held
        lda #3
        rts
:       stz sh_held
sh_none2:
        ldx #1                   ; paddle 1: up / down, repeating
        jsr sh_pread
        lda #1
        cpy #48
        bcc :+
        lda #2
        cpy #208
        bcs :+
        stz sh_rep               ; centred
sh_none:
        lda #0
        rts
:       ldx sh_rep
        beq :+
        dec sh_rep
        bra sh_none
:       ldx #SH_REPEAT
        stx sh_rep
        rts

; PREAD with the interrupts held: the Mockingboard's music tick (~1 570
; cycles, 25 Hz) inside the ROM's 11-cycle count loop added ~140 to the
; reading, so a centred stick stepped down now and then (2026-10-31).
sh_pread:
        php
        sei
        jsr $FB1E                ; PREAD: Y = 0..255
        plp
        rts

sh_keys:  .byte $0B, $08, $0A, $15, $0D, ' ', $1B
sh_keys_end:
sh_acts:  .byte 1, 1, 2, 2, 3, 3, 4
sh_bit:   .byte 1, 2, 4, 8, 16, 32
sh_max_txt: .byte "MAX"
sh_no_txt:  .byte "   "
sh_blank: .res 2*OBJ_H, 0
sh_static:
        .byte 1, 18, "SHOP", 0
        .byte 3, 2, "CREDITS", 0
        .byte 3, 31, "RANK", 0
        .byte SH_LINE0+NITEM+1, SH_NAME, "LEAVE", 0
        .byte 18, 2, "SPEED", 0
        .byte 18, 12, "BULLETS", 0
        .byte 18, 26, "TIME", 0
        .byte 19, 2, "ARMOUR", 0
        .byte 19, 14, "LIVES", 0
        .byte 19, 24, "WEAPON", 0
        .byte SH_MARKS, 2, "MARKS", 0
        .byte 23, 4, "ARROWS RETURN  /  STICK BUTTON", 0
        .byte $FF
.assert SH_LINE0+NITEM+1 < 17, error, "the items run into the gauges"

.include "memory.s"
.include "front.s"

; The speaker's two-voice player, page aligned (its counted loop must not
; cross a page).
DUET_BASE = duet_base
.include "duet.asm"
.segment "DUET"
duet_base:
DUET_CODE = 1
.include "duet.asm"

.segment "BSS"
sh_ev:    .res 1                ; duet event, slices left in it
sh_sl:    .res 1
sh_cur:   .res 1
sh_row:   .res 1
sh_col:   .res 1
sh_x:     .res 1
sh_y:     .res 1
sh_n:     .res 1
sh_lead:  .res 1
sh_held:  .res 1
sh_rep:   .res 1
.code
