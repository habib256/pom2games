; WARGALAGA II -- one logic step (1/30 s NTSC). Pure state, no drawing:
; tools/model.py is its bit-exact reference (tests/test_game.py compares the
; two step by step). Order: ship, shots, new shot, stars, entry waves,
; formation sway, dive launcher, aliens. Included by game.s.

logic_step:
        inc step_count
        bne :+
        inc step_count+1
:       lda move_dir
        beq ship_done
        bmi ship_left
        lda ship_c
        clc
        adc #SHIP_SPEED
        cmp #SHIP_MAX+1
        bcc :+
        lda #SHIP_MAX
:       sta ship_c
        bra ship_done
ship_left:
        lda ship_c
        sec
        sbc #SHIP_SPEED
        bcs :+
        lda #0
:       sta ship_c
ship_done:
        ldx #MAX_SHOTS-1         ; shots climb; off the field = free
shots:  lda shot_y,x
        beq :+
        sec
        sbc #SHOT_DY
        cmp #FIELD_TOP
        bcs :++
:       lda #0
:       sta shot_y,x
        dex
        bpl shots
        lda fire_req
        beq stars
        stz fire_req
        ldx shot_limit           ; last free slot under the limit, if any
:       dex
        bmi stars
        lda shot_y,x
        bne :-
        lda #SHOT_Y0
        sta shot_y,x
        lda ship_c
        clc
        adc #3                   ; middle cell of the ship
        sta shot_c,x
stars:  ldx #NSTARS-1            ; three speeds; a star leaving the bottom
:       lda star_y,x             ; comes back at the top, 17 bytes further
        clc
        adc star_speed,x
        cmp #192
        bcc :++
        sbc #192-FIELD_TOP
        pha
        lda star_col,x
        adc #17-1                ; carry is set
        cmp #40
        bcc :+
        sbc #40
:       sta star_col,x
        pla
:       sta star_y,x
        dex
        bpl :---
        jsr launch
        jsr sway
        jsr dive
        ldx #NALIENS-1
:       jsr alien
        dex
        bpl :-
logic_done:
        rts

; Entry waves: wave w fills formation row w, a pair every LAUNCH_GAP steps
; from the middle out, the left alien on the entry path, the right one on
; its mirror.
launch:
        lda entry_w
        cmp #ROWS
        beq launched
        dec entry_t
        bne launched
        asl
        asl
        asl
        sta tmp2                 ; w * 8
        clc
        adc #3
        sec
        sbc entry_k
        tax
        lda #ENTRY_X0
        ldy #0
        jsr enter
        lda tmp2
        clc
        adc #4
        adc entry_k
        tax
        lda #ALIEN_MAX-ENTRY_X0
        ldy #1
        jsr enter
        inc entry_k
        lda entry_k
        cmp #4
        bne :+
        stz entry_k
        inc entry_w
        lda #WAVE_GAP
        bra :++
:       lda #LAUNCH_GAP
:       sta entry_t
launched:
        rts
; X = alien, A = start cell, Y = mirror flag.
enter:  sta a_x,x
        tya
        sta a_mirror,x
        lda #ST_ENTER
        sta a_state,x
        lda #ENTRY_Y0
        sta a_y,x
        lda #<entry
        sta a_plo,x
        lda #>entry
        sta a_phi,x
        rts

; Every other step, one formation row takes the current sway offset and
; flips its animation frame; its seated aliens follow. When all ROWS have,
; the offset moves one cell, bouncing between 0 and SWAY_MAX. (One row a
; step would redraw 16 aliens a frame: each change is drawn on both pages.)
sway:   lda sway_t
        eor #1
        sta sway_t
        bne swayed
        ldx sway_row
        lda form_off
        sta row_off,x
        lda row_anim,x
        eor #1
        sta row_anim,x
        txa
        asl
        asl
        asl
        tax
        lda #COLS
        sta cnt
:       lda a_state,x
        cmp #ST_FORM
        bne :+
        jsr slot_x
        sta a_x,x
:       inx
        dec cnt
        bne :--
        inc sway_row
        lda sway_row
        cmp #ROWS
        bne swayed
        stz sway_row
        lda form_off
        clc
        adc form_dir
        sta form_off
        beq :+
        cmp #SWAY_MAX
        bne swayed
:       lda form_dir
        eor #$FE                 ; 1 <-> $FF
        sta form_dir
swayed: rts

; Every DIVE_GAP steps once all waves are in, a random seated alien dives,
; unless MAX_DIVERS are already off their seats.
dive:   lda entry_w
        cmp #ROWS
        bne dived
        dec dive_t
        bne dived
        lda #DIVE_GAP
        sta dive_t
        ldy #0
        ldx #NALIENS-1
:       lda a_state,x
        sec
        sbc #ST_ENTER
        cmp #ST_HOME-ST_ENTER+1
        bcs :+
        iny
:       dex
        bpl :--
        cpy #MAX_DIVERS
        bcs dived
        jsr rand8
        and #63
        cmp #NALIENS
        bcc :+
        sbc #NALIENS             ; carry is set
:       tax
        ldy #NALIENS
seek:   lda a_state,x
        cmp #ST_FORM
        beq found
        inx
        cpx #NALIENS
        bne :+
        ldx #0
:       dey
        bne seek
dived:  rts
found:  lda #ST_DIVE
        sta a_state,x
        jsr rand8
        and #NDIVES-1
        tay
        lda dive_lo,y
        sta a_plo,x
        lda dive_hi,y
        sta a_phi,x
        txa                      ; right half of the formation: mirrored
        and #COLS-1
        cmp #COLS/2
        lda #0
        rol
        sta a_mirror,x
        rts
.assert NDIVES = 4, error, "dive choice masks with NDIVES-1"

; Slot of alien X: A = cell (FORM_X0 + row offset + 14 * column).
; Keeps X, Y. Uses tmp.
slot_x: phy
        ldy alien_row,x
        lda row_off,y
        sta tmp
        txa
        and #COLS-1
        tay
        lda slot_dx,y
        clc
        adc tmp
        ply
        rts

; Move alien X. Keeps X.
alien:  lda a_state,x
        cmp #ST_FORM
        jeq moved
        cmp #ST_HOME
        jeq home
        cmp #ST_DEAD
        jeq moved
        lda a_plo,x              ; flying a path
        sta ptr
        lda a_phi,x
        sta ptr+1
        lda (ptr)
        cmp #PATH_END
        bne :+
        lda #ST_HOME
        sta a_state,x
        rts
:       inc a_plo,x
        bne :+
        inc a_phi,x
:       sta tmp2                 ; the step byte
        lsr                      ; dx: high nibble, signed
        lsr
        lsr
        lsr
        cmp #8
        bcc :+
        ora #$F0
:       ldy a_mirror,x
        beq :+
        eor #$FF
        inc a
:       sta tmp
        clc
        adc a_x,x
        bit tmp
        bpl :+
        bcs xok                  ; negative step, no borrow
        lda #0
        bra xok
:       cmp #ALIEN_MAX+1
        bcc xok
        lda #ALIEN_MAX
xok:    sta a_x,x
        lda tmp2                 ; dy: low nibble, signed
        and #$0F
        cmp #8
        bcc :+
        ora #$F0
:       clc
        adc a_y,x
        sta a_y,x
        ldy a_state,x            ; a diver leaving the bottom goes home
        cpy #ST_DIVE             ; from above its seat
        bne moved
        cmp #192
        bcc moved
        cmp #OFF_TOP
        bcs moved
        lda #ST_HOME
        sta a_state,x
        lda #OFF_TOP
        sta a_y,x
        jsr slot_x
        sta a_x,x
moved:  rts

; Homing: at most HOME_DX cells and HOME_DY rows a step towards the seat.
home:   jsr slot_x
        sta tmp                  ; seat cell
        sec
        sbc a_x,x
        bcc hx_neg
        cmp #HOME_DX+1
        bcc hx_add
        lda #HOME_DX
        bra hx_add
hx_neg: cmp #256-HOME_DX
        bcs hx_add
        lda #256-HOME_DX
hx_add: clc
        adc a_x,x
        sta a_x,x
        ldy alien_row,x          ; seat row; the row step wraps (signed)
        lda form_y,y
        sta tmp2
        sec
        sbc a_y,x
        bmi hy_neg
        cmp #HOME_DY+1
        bcc hy_add
        lda #HOME_DY
        bra hy_add
hy_neg: cmp #256-HOME_DY
        bcs hy_add
        lda #256-HOME_DY
hy_add: clc
        adc a_y,x
        sta a_y,x
        cmp tmp2
        bne seated
        lda a_x,x
        cmp tmp
        bne seated
        lda #ST_FORM
        sta a_state,x
seated: rts
