; WARGALAGA II -- drawing on the hidden page. Included by game.s.
;
; Each page keeps what was drawn on it (two frames ago): aliens (pd_*),
; shots (sd_*), the ship, the stars. Drawing order, then erasing order, the
; exact reverse, so that each erase finds the page as its drawing left it:
;   draw:  seated aliens (STA), ship (STA), flying aliens (EOR), shots
;          (EOR), stars (only on a black byte)
;   erase: stars (only if the byte is still the star), shots (EOR), flying
;          aliens (EOR, all of them, every frame), ship (zeros, if it
;          moved), seated aliens that moved or left (zeros)
; Flying things are drawn with EOR, so erasing them restores what was under
; them (a seated alien, the ship) without redrawing it: only the formation
; rows that swayed are rewritten, one row every other step.
;
; Row tables: hgr_lo/hgr_hi/hgr_hi2 are page aligned, so the routines read
; hgr_hi+R,X for row R of a sprite whose top row is X, and select_page
; rewrites only the high byte of each such operand (HI_LDA sites).

HI_SITES .set 0
.macro HI_LDA r, reg
        .ident(.sprintf("hi_site%d", HI_SITES)) = *
HI_SITES .set HI_SITES + 1
.if .xmatch({reg}, x)
        lda hgr_hi+r,x
.else
        lda hgr_hi+r,y
.endif
.endmacro

; Unrolled sprite rows. X = top row, col = byte column, src = data (W bytes
; a row, rows in order). MODE 0: STA, 2: zeros (no src), 3: EOR. The carry
; stays clear: hgr_lo + col never passes 255. Clobbers A, Y.
.macro SPRITE_ROWS W, H, MODE
        clc
.repeat H, R
        lda hgr_lo+R,x
        adc col
        sta dst
        HI_LDA R, x
        sta dst+1
.if MODE = 2
        lda #0
        sta (dst)
  .repeat W-1, B
        ldy #B+1
        sta (dst),y
  .endrepeat
.else
  .repeat W, B
        ldy #W*R+B
        lda (src),y
    .if B = 0
      .if MODE = 3
        eor (dst)
      .endif
        sta (dst)
    .else
      .if R > 0
        ldy #B
      .endif
      .if MODE = 3
        eor (dst),y
      .endif
        sta (dst),y
    .endif
  .endrepeat
.endif
.endrepeat
.endmacro

; A one-byte column of H rows, all the same pattern (pat): EOR.
.macro COLUMN_ROWS H
        clc
.repeat H, R
        lda hgr_lo+R,x
        adc col
        sta dst
        HI_LDA R, x
        sta dst+1
        lda (dst)
        eor pat
        sta (dst)
.endrepeat
.endmacro

.zeropage
pat:      .res 1

.bss
pd_x:     .res NALIENS*2        ; alien drawn at, per page
pd_y:     .res NALIENS*2        ; 0 = not drawn
pd_f:     .res NALIENS*2        ; table entry drawn, + $80 if drawn seated
md_list:  .res NALIENS*2        ; slots drawn flying, per page
md_n:     .res 2
sd_y:     .res MAX_SHOTS*2      ; shot drawn at (top row, 0 = none), per page
sd_col:   .res MAX_SHOTS*2
sd_pat:   .res MAX_SHOTS*2
star_lo:  .res NSTARS*2         ; screen byte written per page, hi 0 = none
star_hi:  .res NSTARS*2
ship_drawn: .res 2              ; cell drawn on each page, $FF = none
form_list: .res NALIENS
nform:    .res 1
move_list: .res NALIENS
nmove:    .res 1
cur_f:    .res 1                ; table entry wanted for the alien in hand
pr_off:   .res ROWS*2           ; row sway offset / frame each page was drawn with
pr_anim:  .res ROWS*2
row_dirty: .res ROWS

.code
render_init:
        lda #$FF
        sta ship_drawn
        sta ship_drawn+1
        ldx #ROWS*2-1
:       sta pr_off,x
        dex
        bpl :-
        rts

render:
        jsr stars_erase
        jsr timing_scan
        jsr shots_erase
        jsr movers_erase
        jsr ship_erase
        jsr aliens_pass
        jsr form_draw
        jsr ship_draw
        jsr movers_draw
        jsr shots_draw
        jsr timing_scan
        jsr stars_draw
render_done:
        rts

; ---------------------------------------------------------------------------
; Shots: one byte wide, SHOT_H rows of the same pattern, EOR both ways.
shots_erase:
        ldx pg10
se_shot:
        lda sd_y,x
        beq se_next
        stz sd_y,x
        phx
        ldy sd_col,x
        sty col
        ldy sd_pat,x
        sty pat
        tax
        jsr shot_eor
        plx
se_next:
        inx
        txa
        sec
        sbc pg10
        cmp #MAX_SHOTS
        bne se_shot
        rts

shots_draw:
        ldx #MAX_SHOTS-1
sh_draw:
        lda shot_y,x
        beq sh_next
        phx
        ldy shot_c,x
        lda cell_byte,y
        sta col
        lda cell_shift,y
        tay
        lda shot_pat,y
        sta pat
        txa
        clc
        adc pg10
        tay
        lda col
        sta sd_col,y
        lda pat
        sta sd_pat,y
        lda shot_y,x
        sta sd_y,y
        tax
        jsr shot_eor
        plx
sh_next:
        dex
        bpl sh_draw
        rts

; ---------------------------------------------------------------------------
; Ship: redrawn on a page when it moved since that page.
ship_erase:
        ldy page
        lda ship_c
        cmp ship_drawn,y
        beq :+
        ldx ship_drawn,y
        cpx #$FF
        beq :+
        lda cell_byte,x
        sta col
        ldx #SHIP_Y
        jsr ship_clr
:       rts

ship_draw:
        ldy page
        lda ship_c
        cmp ship_drawn,y
        beq :+
        sta ship_drawn,y
        tax
        lda cell_byte,x
        sta col
        ldy cell_shift,x
        lda ship_lo,y
        sta src
        lda ship_hi,y
        sta src+1
        ldx #SHIP_Y
        jmp ship_sta
:       rts

; ---------------------------------------------------------------------------
; Flying aliens drawn on this page last time: EOR them away.
movers_erase:
        ldy page
        lda md_n,y
        beq me_done
        sta cnt
        lda #0
        sta md_n,y
        ldx pg40
me_alien:
        phx
        ldy md_list,x
        lda pd_x,y
        tax
        lda cell_byte,x
        sta col
        ldx pd_f,y
        lda alien_lo,x
        sta src
        lda alien_hi,x
        sta src+1
        lda pd_y,y
        tax
        lda #0
        sta pd_f,y
        sta pd_y,y
        txa
        jsr alien_eor_clip
        jsr timing_scan
        plx
        inx
        dec cnt
        bne me_alien
me_done:
        rts

; A = top row, src/col set: EOR the alien, clipped at the bottom edge.
alien_eor_clip:
        cmp #192-ALIEN_H+1
        bcs :+
        tax
        jmp alien_eor
:       sta r_row
        eor #$FF                 ; 192 - y rows
        sec
        adc #192                 ; ~y + 1 + 192
        sta r_h
        lda col
        sta r_col
        lda #ALIEN_W
        sta r_w
        jmp eor_rect

; ---------------------------------------------------------------------------
; A pass over the 40 aliens: erase seated drawings that moved or left
; (zeros), queue seated aliens to draw in form_list, flying ones in
; move_list. A formation row whose sway offset and frame are those this
; page was last drawn with is clean: its seated aliens drawn seated are
; passed over at the cost of a few tests.
aliens_pass:
        ldx #ROWS-1
        ldy #ROWS-1
        lda page
        beq ar_row
        ldy #ROWS*2-1
ar_row: lda row_off,x
        cmp pr_off,y
        bne :+
        lda row_anim,x
        cmp pr_anim,y
        bne :+
        stz row_dirty,x
        bra :++
:       lda #1
        sta row_dirty,x
        lda row_off,x
        sta pr_off,y
        lda row_anim,x
        sta pr_anim,y
:       dey
        dex
        bpl ar_row
        ldx #NALIENS-1
ae_alien:
        lda a_state,x
        cmp #ST_FORM
        bne ae_slot
        ldy alien_row,x
        lda row_dirty,y
        bne ae_slot
        txa
        clc
        adc pg40
        tay
        lda pd_f,y
        jmi ae_next              ; seated, drawn seated, row clean
        bra ae_full
ae_slot:
        txa
        clc
        adc pg40
        tay                      ; Y = slot of this alien on this page
ae_full:
        lda a_state,x
        beq ae_gone
        sta tmp2
        lda a_y,x
        cmp #FIELD_TOP
        bcc ae_gone
        cmp #192
        bcs ae_gone
        lda tmp2
        cmp #ST_FORM
        bne ae_mover
        jsr want_f               ; seated
        sta cur_f
        lda pd_y,y
        beq ae_queue             ; not drawn here
        cmp a_y,x
        bne ae_erase
        lda pd_x,y
        cmp a_x,x
        bne ae_span              ; swayed along its row
        lda pd_f,y
        cmp cur_f
        beq ae_next              ; unchanged
        bra ae_queue             ; new frame only: STA covers the old one
ae_span:                         ; same byte span: STA covers the old one
        phy
        tay
        lda cell_byte,y
        ldy a_x,x
        cmp cell_byte,y
        bne :+
        ply
        bra ae_queue
:       ply
ae_erase:
        jsr erase_seat
ae_queue:
        txa
        phx
        ldx nform
        sta form_list,x
        inc nform
        plx
        bra ae_next
ae_mover:
        lda pd_y,y               ; drawn seated (a dive starts): erase
        beq :+
        jsr erase_seat
:       txa
        phx
        ldx nmove
        sta move_list,x
        inc nmove
        plx
        bra ae_next
ae_gone:
        lda pd_y,y
        beq ae_next
        jsr erase_seat
ae_next:
        dex
        bmi :+
        jmp ae_alien
:       rts

; Zero the seated drawing of slot Y (X = alien). Keeps X, Y.
erase_seat:
        phx
        phy
        lda pd_x,y
        tax
        lda cell_byte,x
        sta col
        ldx pd_y,y
        lda #0
        sta pd_y,y
        sta pd_f,y
        jsr alien_clr
        jsr timing_scan
        ply
        plx
        rts

; A = the table entry alien X needs (shift*2 + frame), + $80 if seated.
; Keeps X, Y.
want_f: phy
        lda a_state,x
        cmp #ST_FORM
        beq :+
        lda step_count           ; flying: flaps every 4 steps
        lsr
        lsr
        and #1
        bra :++
:       ldy alien_row,x          ; seated: the row's frame
        lda row_anim,y
        ora #$80
:       ldy a_x,x
        ora cell_shift2,y
        ply
        rts

; Alien X about to be drawn: work out its table entry and byte column,
; record them as drawn in its slot. -> Y = slot. Keeps X.
alien_pose:
        ldy a_x,x
        lda cell_byte,y
        sta col
        jsr want_f
        sta cur_f
        and #$7F
        tay
        lda alien_lo,y
        sta src
        lda alien_hi,y
        sta src+1
        txa
        clc
        adc pg40
        tay
        lda cur_f
        sta pd_f,y
        lda a_x,x
        sta pd_x,y
        lda a_y,x
        sta pd_y,y
        rts

; Seated aliens: STA at their seat.
form_draw:
        lda nform
        beq fd_done
fd_alien:
        dec nform
        ldx nform
        lda form_list,x
        tax
        jsr alien_pose
        lda a_y,x
        tax
        jsr alien_sta
        jsr timing_scan
        lda nform
        bne fd_alien
fd_done:
        rts

; Flying aliens: EOR, clipped at the bottom edge; listed for the erase.
movers_draw:
        lda nmove
        beq md_done
md_alien:
        dec nmove
        ldx nmove
        lda move_list,x
        tax
        jsr alien_pose           ; Y = slot
        sty tmp
        ldy page                 ; list the slot on this page
        lda md_n,y
        inc a
        sta md_n,y
        dec a
        clc
        adc pg40
        tay
        lda tmp
        sta md_list,y
        lda a_y,x
        jsr alien_eor_clip
        jsr timing_scan
        lda nmove
        bne md_alien
md_done:
        rts

; ---------------------------------------------------------------------------
; Unrolled sprite routines (X = top row, col, src / pat).
alien_sta:
        SPRITE_ROWS ALIEN_W, ALIEN_H, 0
alien_sta_done:
        rts
alien_eor:
        SPRITE_ROWS ALIEN_W, ALIEN_H, 3
alien_eor_done:
        rts
alien_clr:
        SPRITE_ROWS ALIEN_W, ALIEN_H, 2
alien_clr_done:
        rts
ship_sta:
        SPRITE_ROWS SHIP_W, SHIP_H, 0
        rts
ship_clr:
        SPRITE_ROWS SHIP_W, SHIP_H, 2
        rts
shot_eor:
        COLUMN_ROWS SHOT_H
        rts

; Generic, for clipped sprites: EOR r_h rows of r_w bytes from src at
; (r_row, byte r_col). Clobbers A, X, Y, r_h, src.
eor_rect:
        ldx r_row
er_row: lda hgr_lo,x
        clc
        adc r_col
        sta dst
        HI_LDA 0, x
        sta dst+1
        ldy r_w
        dey
er_byte:
        lda (src),y
        eor (dst),y
        sta (dst),y
        dey
        bpl er_byte
        lda src
        clc
        adc r_w
        sta src
        bcc :+
        inc src+1
:       inx
        dec r_h
        bne er_row
        rts

; ---------------------------------------------------------------------------
; Remove this page's stars: a byte still holding exactly its star is
; zeroed; one a sprite was drawn over (or erased) is left alone.
stars_erase:
        ldx #NSTARS-1            ; X = star, Y = its slot for this page
        ldy #NSTARS-1
        lda page
        beq se_star
        ldy #NSTARS*2-1
se_star:
        lda star_hi,y
        beq st_next
        sta dst+1
        lda star_lo,y
        sta dst
        lda (dst)
        cmp star_val,x
        bne st_next
        lda #0
        sta (dst)
st_next:
        dey
        dex
        bpl se_star
        rts

; Put each star on this page where the byte is black; record where.
stars_draw:
        ldx #NSTARS-1
        lda page
        beq :+
        lda #NSTARS
:       sta tmp                  ; first slot of this page
sd_star:
        ldy star_y,x
        lda hgr_lo,y
        clc
        adc star_col,x
        sta dst
        HI_LDA 0, y
        sta dst+1
        txa
        clc
        adc tmp
        tay
        lda (dst)
        beq sd_free
        lda #0                   ; occupied: not drawn
        sta star_hi,y
        bra sd_next
sd_free:
        lda star_val,x
        sta (dst)
        lda dst
        sta star_lo,y
        lda dst+1
        sta star_hi,y
sd_next:
        dex
        bpl sd_star
        rts

; ---------------------------------------------------------------------------
; Last: it patches every HI_LDA site above. A = page to draw (0/1).
select_page:
        sta page
        tax
        lda pg40_of,x
        sta pg40
        lda pg10_of,x
        sta pg10
        ldy #>hgr_hi
        cpx #0
        beq :+
        ldy #>hgr_hi2
:
.repeat HI_SITES, I
        sty .ident(.sprintf("hi_site%d", I)) + 2
.endrepeat
        rts
pg40_of: .byte 0, NALIENS
pg10_of: .byte 0, MAX_SHOTS
