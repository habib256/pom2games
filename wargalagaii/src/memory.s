; WARGALAGA II -- Memory Station (lot 8). Included by shop.s: in the same
; overlay as the shop (segment SHOP at $4000, page 1 shown), sharing its
; texts, digits, clock tick and stick. tools/model.py (mem_deal, mem_turn)
; is the reference of the rules; the clock is the screen's.
;
; Grids of cards (mem_cols x mem_rows, row-major in m_card): pairs of
; bonuses and one skull, the pirate flag, that ends the station. A pair
; turned: its bonus (logic.s take); the grid cleared: MEM_PRIZE points and
; the next, larger grid. The T gauge gives the seconds a grid.
;
; Keys: arrows or I J K L move, RETURN or SPACE turns a card, ESC leaves.
; Stick (TAB mode): paddles 0 / 1, button 0.

MEM_SUB    = 30                 ; ticks a second (sh_tick: ~1/30 s)
MEM_PITCH  = 4                  ; byte columns from card to card (even:
                                ; an icon's colours need an even column)
MEM_ROWH   = 16                 ; rows from card to card
MEM_Y0     = 48                 ; top row of a 5-row grid
MT_NO      = 0                  ; mem_turn: face up already
MT_FLAG    = 1                  ; the skull: the end
MT_FIRST   = 2
MT_PAIR    = 3
MT_CLEARED = 4                  ; the next grid is dealt
MT_MISS    = 5                  ; both face down again (m_miss: the first)
MEM_SHOW   = 30                 ; ticks two different cards stay shown
MEM_FLAG_T = 45                 ; ticks the skull stays shown

.segment "SHOP"
; --- the rules (tools/model.py) --------------------------------------------
; The grid of round m_round (the last size once past it): a kind drawn for
; each pair, the skull, shuffled (Fisher-Yates: j = rand8 mod (i + 1)).
mem_deal:
        ldx m_round
        cpx #MEM_ROUNDS
        bcc :+
        ldx #MEM_ROUNDS-1
:       lda mem_cols,x           ; cards = cols * rows
        sta tmp
        lda #0
        ldy mem_rows,x
:       clc
        adc tmp
        dey
        bne :-
        sta m_n
        ldx #MEM_CELLS-1         ; none face up, nothing past the grid
:       stz m_up,x
        stz m_card,x
        dex
        bpl :-
        ldx #0
md_pair:
        jsr rand8                ; a pair (n is odd: n - 1 cards)
        and #15
        tay
        lda mem_kinds,y
        sta m_card,x
        inx
        sta m_card,x
        inx
        txa
        inc a
        cmp m_n
        bne md_pair
        lda #K_SKULL
        sta m_card,x
        lsr m_n                  ; pairs = n / 2 (n odd)
        lda m_n
        sta m_pairs
        rol m_n
md_shuffle:                      ; X = i = n - 1 .. 1
        jsr rand8
        stx tmp
        inc tmp                  ; mod (i + 1)
:       cmp tmp
        bcc :+
        sbc tmp
        bra :-
:       tay
        lda m_card,x
        pha
        lda m_card,y
        sta m_card,x
        pla
        sta m_card,y
        dex
        bne md_shuffle
        lda #MEM_NONE
        sta m_first
        rts

; X = card: A = MT_* (and the bonuses, the prize, the next grid).
mem_turn:
        lda m_up,x
        beq :+
        lda #MT_NO
        rts
:       inc m_up,x
        lda m_card,x
        cmp #K_SKULL
        bne :+
        lda #MT_FLAG
        rts
:       ldy m_first
        cpy #MEM_NONE
        bne mt_second
        stx m_first
        lda #MT_FIRST
        rts
mt_second:
        lda #MEM_NONE
        sta m_first
        sty m_miss
        lda m_card,y
        cmp m_card,x
        beq :+
        stz m_up,x               ; different: both face down again
        lda #0
        sta m_up,y
        lda #MT_MISS
        rts
:       jsr take                 ; a pair: its bonus
        dec m_pairs
        beq :+
        lda #MT_PAIR
        rts
:       lda #>MEM_PRIZE          ; the grid cleared: the prize, the next
        sta pts_hi               ; (BCD 025000)
        lda #^MEM_PRIZE
        sta pts_top
        lda #<MEM_PRIZE
        jsr add_points3
        lda m_round
        inc a
        beq :+
        sta m_round
:       jsr mem_deal
        lda #MT_CLEARED
        rts

; --- the screen ------------------------------------------------------------
mem_screen:
        lda #0                   ; drawing on page 1, shown
        jsr select_page
        lda #<mem_static
        sta ptr
        lda #>mem_static
        sta ptr+1
        jsr sh_texts
        stz sh_held
        stz sh_rep
        stz sh_ev
        lda #DUET_EVENT_SLICES
        sta sh_sl
        lda #$80                 ; a key cuts the slice short
        sta DUET_KEYS
        jsr mem_deal
mem_grid:                        ; a grid dealt: drawn face down, the clock
        lda #40
        sta r_row
        lda #2
        sta r_col
        lda #36
        sta r_w
        lda #96
        sta r_h
        jsr rect_clr
        ldx m_round              ; its place on the screen
        cpx #MEM_ROUNDS
        bcc :+
        ldx #MEM_ROUNDS-1
:       lda mem_cols,x
        sta mem_w
        lda #7                   ; x0 = 6 + (7 - cols) / 2 * 4
        sec
        sbc mem_w
        asl                      ; (7 - cols is even)
        adc #6
        sta mem_x0
        lda mem_rows,x
        sta mem_h
        lda #5                   ; y0 = MEM_Y0 + (5 - rows) * 8
        sec
        sbc mem_h
        asl
        asl
        asl
        adc #MEM_Y0
        sta mem_y0
        ldx #0
:       phx
        lda #K_MEMORY            ; face down: the '?' icon
        jsr mem_icon
        plx
        inx
        cpx m_n
        bne :-
        stz mem_cx
        stz mem_cy
        lda t_level              ; 10 * T seconds
        asl
        sta tmp
        asl
        asl
        adc tmp
        sta mem_sec
        lda #MEM_SUB
        sta mem_sub
        jsr mem_state
        jsr mem_cursor_on
mem_loop:
        jsr mem_clock
        bcs mem_end
        jsr mem_input            ; A: 0, 1 up, 2 down, 3 turn, 4 leave,
        beq mem_loop             ; 5 left, 6 right
        cmp #4
        beq mem_end
        cmp #3
        beq mem_select
        pha
        jsr mem_cursor_off
        pla
        jsr mem_move
        jsr mem_cursor_on
        bra mem_loop
mem_end:
        rts
mem_select:
        jsr mem_cell             ; X = card
        stx mem_at
        lda m_card,x             ; (its kind: the rules may hide or deal)
        sta mem_kind
        jsr mem_turn
        sta mem_res
        cmp #MT_NO
        bne :+
        lda #EV_SHOT             ; face up already
        tsb snd_ev
        bra mem_loop
:       ldx mem_at               ; show it
        lda mem_kind
        jsr mem_icon
        lda mem_res
        cmp #MT_FIRST
        beq mem_loop
        cmp #MT_FLAG
        bne :+
        lda #EV_DEATH
        tsb snd_ev
        lda #MEM_FLAG_T
        jsr mem_wait
        bra mem_end
:       cmp #MT_MISS
        bne :+
        lda #MEM_SHOW            ; both shown a moment, then face down
        jsr mem_wait
        bcs mem_end
        ldx mem_at
        lda #K_MEMORY
        jsr mem_icon
        ldx m_miss
        lda #K_MEMORY
        jsr mem_icon
        jmp mem_loop
:       lda #EV_ARMOUR           ; a pair (a chime), maybe the grid
        tsb snd_ev
        jsr mem_state
        lda mem_res
        cmp #MT_CLEARED
        jne mem_loop
        lda #MEM_SHOW
        jsr mem_wait
        bcs mem_end
        jmp mem_grid

; A tick of the screen (music, sounds) and of the clock: C = 1 when the
; time is up.
mem_clock:
        jsr sh_tick
        jsr sound_frame
        dec mem_sub
        bne :+
        lda #MEM_SUB
        sta mem_sub
        dec mem_sec
        jsr mem_state
        lda mem_sec
        bne :+
        sec
        rts
:       clc
        rts

; A ticks of the clock, input left alone: C = 1 if the time ran out.
mem_wait:
        sta mem_wt
:       jsr mem_clock
        bcs :+
        dec mem_wt
        bne :-
:       rts

; TIME, PAIRS, ROUND.
mem_state:
        lda #3*8
        sta sh_row
        lda mem_sec
        ldy #7
        jsr sh_dec2
        lda m_pairs
        ldy #18
        jsr sh_dec2
        lda m_round
        inc a
        ldy #30
        jmp sh_dec2

; Icon A on card X. Keeps nothing.
mem_icon:
        jsr icon_src
        jsr mem_place
        lda #2
        sta r_w
        lda #OBJ_H
        sta r_h
        jmp rect_sta

; Card X -> r_col, r_row (its top left byte). Keeps Y.
mem_place:
        stz tmp                  ; row: X / cols, column: X mod cols
        txa
:       cmp mem_w
        bcc :+
        sbc mem_w
        inc tmp
        bra :-
:       tax
        lda mem_x0
:       dex
        bmi :+
        adc #MEM_PITCH           ; (carry clear)
        bra :-
:       sta r_col
        lda mem_y0
        ldx tmp
:       dex
        bmi :+
        adc #MEM_ROWH
        bra :-
:       sta r_row
        rts

; X = the card under the cursor (cy * cols + cx).
mem_cell:
        lda mem_cx
        ldx mem_cy
:       dex
        bmi :+
        clc
        adc mem_w
        bra :-
:       tax
        rts

; The cursor's brackets on (or off: spaces) around its card.
mem_cursor_on:
        lda #'['
        ldy #']'
        bra :+
mem_cursor_off:
        lda #' '
        ldy #' '
:       sta mem_l
        sty mem_r
        jsr mem_cell
        jsr mem_place
        lda r_row
        sta sh_row
        ldy r_col
        dey
        lda mem_l
        jsr sh_putc
        iny
        iny
        iny
        lda mem_r
        jmp sh_putc

; Move the cursor (A: 1 up, 2 down, 5 left, 6 right), wrapping.
mem_move:
        cmp #1
        bne :+
        dec mem_cy
        bpl mm_done
        lda mem_h
        dec a
        sta mem_cy
        rts
:       cmp #2
        bne :+
        inc mem_cy
        lda mem_cy
        cmp mem_h
        bcc mm_done
        stz mem_cy
        rts
:       cmp #5
        bne :+
        dec mem_cx
        bpl mm_done
        lda mem_w
        dec a
        sta mem_cx
        rts
:       inc mem_cx
        lda mem_cx
        cmp mem_w
        bcc mm_done
        stz mem_cx
mm_done:
        rts

; Keys and stick -> A: 0 nothing, 1 up, 2 down, 3 turn, 4 leave, 5 left,
; 6 right.
mem_input:
        lda $C000
        bpl mi_stick
        bit $C010
        and #$7F
        cmp #'a'
        bcc :+
        and #$DF                 ; upper case
:       ldx #mem_keys_end-mem_keys-1
:       cmp mem_keys,x
        beq :+
        dex
        bpl :-
        lda #0
        rts
:       lda mem_acts,x
        rts
mi_stick:
        lda joy_mode
        beq mi_none
        lda $C061                ; button 0: a press turns
        bpl :+
        lda sh_held
        bne mi_axes
        inc sh_held
        lda #3
        rts
:       stz sh_held
mi_axes:
        ldx #0                   ; paddle 0: left / right
        jsr $FB1E                ; PREAD: Y = 0..255
        lda #5
        cpy #48
        bcc mi_move
        lda #6
        cpy #208
        bcs mi_move
:       lda $C065                ; (paddle 1's timer out: PREAD retriggers)
        bmi :-
        ldx #1                   ; paddle 1: up / down
        jsr $FB1E
        lda #1
        cpy #48
        bcc mi_move
        lda #2
        cpy #208
        bcs mi_move
        stz sh_rep               ; centred
mi_none:
        lda #0
        rts
mi_move:
        ldx sh_rep
        beq :+
        dec sh_rep
        bra mi_none
:       ldx #SH_REPEAT
        stx sh_rep
        rts

mem_keys: .byte $0B, 'I', $0A, 'K', $08, 'J', $15, 'L', $0D, ' ', $1B
mem_keys_end:
mem_acts: .byte 1, 1, 2, 2, 5, 5, 6, 6, 3, 3, 4
mem_static:
        .byte 1, 13, "MEMORY STATION", 0
        .byte 3, 2, "TIME", 0
        .byte 3, 12, "PAIRS", 0
        .byte 3, 24, "ROUND", 0
        .byte 19, 11, "THE SKULL ENDS IT", 0
        .byte 22, 4, "ARROWS RETURN  /  STICK BUTTON", 0
        .byte $FF

.segment "BSS"
mem_sec:  .res 1                ; seconds left on this grid
mem_sub:  .res 1                ; ticks left in this second
mem_cx:   .res 1                ; cursor
mem_cy:   .res 1
mem_w:    .res 1                ; grid: columns, rows, first card's byte
mem_h:    .res 1                ; column and row
mem_x0:   .res 1
mem_y0:   .res 1
mem_at:   .res 1                ; card being turned, its kind, the result
mem_kind: .res 1
mem_res:  .res 1
mem_wt:   .res 1
mem_l:    .res 1
mem_r:    .res 1
.segment "SHOP"
