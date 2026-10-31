; VERHILLE Arnaud — GPL-3.0. DHGR compositor state, dhgr_spr_init and
; dhgr_spr_update (dhgr.h). The damage is a list of group/row rectangles:
; each dirty slot's old and new boxes, the invalidations, the overlay's old
; and new boxes (dhgr_spr_cursor.s), clipped to the area; overlapping ones
; are merged into their bounding box until none overlap, then each is cut
; into canvas pieces of at most gmax groups and 255 bytes. A piece is
; rebuilt in the canvas (background, then the slots that cross it, slot 0
; first) and written once by dhgr_spr_blit. Main RAM only; the cell callback
; (C) may use any cc65 scratch: the loops keep their state here. A/X/Y,
; ptr1, ptr2, tmp1-tmp4 destroyed; non-reentrant, never from an IRQ.
.export _dhgr_spr_update, _dhgr_spr_add, _dhgr_spr_init
.export _dhgr_spr_shlo, _dhgr_spr_shhi, _dhgr_spr_x, _dhgr_spr_y
.export _dhgr_spr_x1, _dhgr_spr_y1, _dhgr_spr_flags, _dhgr_spr_dirty
.export _dhgr_spr_pal, _dhgr_spr_dn
.export _dhgr_spr_rg0, _dhgr_spr_rg1, _dhgr_spr_ry0, _dhgr_spr_ry1
.export _dhgr_spr_ag0, _dhgr_spr_ag1, _dhgr_spr_ay0, _dhgr_spr_ay1
.export _dhgr_spr_solid_c, _dhgr_spr_bg, _dhgr_spr_bg_jmp
.export _dhgr_spr_cur_jmp, _dhgr_spr_ovd_jmp, _dhgr_spr_ovr_jmp, _dhgr_spr_ovg_jmp
.export _dhgr_spr_v_dirty, _dhgr_spr_ov_on, _dhgr_spr_w_g0, w_g1, w_y0, w_y1
.export pg, pn, py
.export cur_nbx, cur_ny, cur_nw, cur_nh, cur_bits, cur_under, _dhgr_cursor_w, cur_obx
_dhgr_cursor_w = cur_nw
.import _dhgr_cellbyte
.import _dhgr_cv_x0, _dhgr_cv_y0, _dhgr_cv_w, _dhgr_cv_h, _dhgr_cv_x1, _dhgr_cv_y1
.import _dhgr_cv_shape, _dhgr_cv_sx, _dhgr_cv_sy, _dhgr_cv_flags, _dhgr_cv_pal
.import _dhgr_cv_solid, _dhgr_cv_paint, _dhgr_cv_buf, cv_begin
.import _dhgr_spr_blit, _dhgr_spr_goff, _dhgr_spr_gend, dhgr_cv_patch
.import incsp4
.importzp sp, tmp1

.ifndef DHGR_SPR_MAX
DHGR_SPR_MAX = 8
.endif
MAX = DHGR_SPR_MAX
DMAX = 2 * MAX + 6
NONE = $FF

.bss
zero_lo:                        ; cleared by dhgr_spr_init
_dhgr_spr_y:     .res MAX       ; y, x, shape: MAX apart, as on the C stack
_dhgr_spr_x:     .res MAX       ; (dhgr_spr_set compares them in one loop)
_dhgr_spr_shlo:  .res MAX
_dhgr_spr_shhi:  .res MAX
_dhgr_spr_flags: .res MAX
_dhgr_spr_dirty: .res MAX
_dhgr_spr_pal:   .res MAX * 4
_dhgr_spr_dn:    .res 1         ; damage rectangles
_dhgr_spr_v_dirty: .res 1       ; the overlay (cur_n*) changed
cur_nbx:  .res 1                ; the overlay wanted (w = 0: hidden),
cur_ny:   .res 1                ; as dhgr_spr_cursor.s's t_*: 8 bytes
cur_nw:   .res 1
cur_nh:   .res 1
cur_bits: .res 2
cur_under: .res 2
cur_obx:  .res 4                ; the cursor on screen (dhgr_spr_cursor.s)
_dhgr_spr_bg:    .res 1         ; background: 0 solid, else cells or tiles
_dhgr_spr_solid_c: .res 1
_dhgr_spr_ov_on: .res 1         ; bit 7: the overlay has a box in the area
_dhgr_spr_ag0:   .res 1         ; area, inclusive (0, 19, 0, 191), in
_dhgr_spr_ag1:   .res 1         ; this order (dhgr_spr_cursor.s's pass)
_dhgr_spr_ay0:   .res 1
_dhgr_spr_ay1:   .res 1
zero_hi:
none_lo:                        ; set to NONE by dhgr_spr_init
_dhgr_spr_y1:    .res MAX       ; NONE: nothing to draw
_dhgr_spr_o_g0:  .res MAX       ; box on screen (groups, rows); NONE: none
_dhgr_spr_w_g0:  .res 1         ; overlay box on screen; NONE: none
none_hi:
_dhgr_spr_x1:    .res MAX       ; colour-pixel box x..x1, y..y1 on screen
o_g1:   .res MAX
o_y0:   .res MAX
o_y1:   .res MAX
d_g0:   .res DMAX
d_g1:   .res DMAX
d_y0:   .res DMAX
d_y1:   .res DMAX
_dhgr_spr_rg0:   .res 1         ; dhgr_spr_add input
_dhgr_spr_rg1:   .res 1
_dhgr_spr_ry0:   .res 1
_dhgr_spr_ry1:   .res 1
gmax:   .res 1                  ; piece width (groups); canvas bytes (<= 255)
cbytes: .res 1
_dhgr_spr_bg_jmp: .res 3        ; JMP to the background painter
_dhgr_spr_cur_jmp: .res 3       ; JMPs installed by dhgr_spr_overlay: the
_dhgr_spr_ovd_jmp: .res 3       ; cursor pass, the overlay's damage, its
_dhgr_spr_ovr_jmp: .res 3       ; row and group ORs in the write
_dhgr_spr_ovg_jmp: .res 3
moved:  .res 1                  ; the overlay changed: run the cursor pass
w_g1:   .res 1
w_y0:   .res 1
w_y1:   .res 1
k:      .res 1
pg:     .res 1                  ; piece: first group, groups, row, rows
pn:     .res 1
py:     .res 1
pr:     .res 1
cap:    .res 1                  ; rows per piece at capw = 7 * pn
capw:   .res 1                  ; (0: none yet)

g0 = _dhgr_spr_rg0
g1 = _dhgr_spr_rg1
y0 = _dhgr_spr_ry0
y1 = _dhgr_spr_ry1

.if .defined(DHGR_SPR_CODE_SEGMENT)
.if DHGR_SPR_CODE_SEGMENT
.segment "DHGRSPRCODE"
.else
.code
.endif
.else
.code
.endif

; unsigned char dhgr_spr_init(canvas, bytes, groups): C stack bytes 0-1,
; canvas 2-3; groups in A. 0 unless 1 <= groups <= 20 and min(bytes, 255)
; >= 7 * groups (one row of the widest piece).
_dhgr_spr_init:
        tax
        beq @bad
        cmp #21
        bcs @bad
        sta gmax
        asl a
        asl a
        asl a
        sec
        sbc gmax                ; 7 * groups
        sta tmp1
        ldy #1
        lda (sp),y
        beq :+
        lda #$FF                ; >= 256: 255
        bne :++
:       dey
        lda (sp),y
:       cmp tmp1
        bcc @bad
        sta cbytes
        lda #0
        sta capw
        ldy #2
        lda (sp),y
        sta _dhgr_cv_buf
        iny
        lda (sp),y
        sta _dhgr_cv_buf+1
        lda #0
        ldx #zero_hi - zero_lo
:       sta zero_lo-1,x
        dex
        bne :-
        lda #NONE
        ldx #none_hi - none_lo
:       sta none_lo-1,x
        dex
        bne :-
        lda #19
        sta _dhgr_spr_ag1
        lda #191
        sta _dhgr_spr_ay1
        lda #1
        .byte $2C               ; (BIT abs: skip lda #0)
@bad:   lda #0
        ldx #0
        jmp incsp4

; Clip g0..g1, y0..y1 to the area: C = 1 if something is left. A destroyed.
clip:   lda g0
        cmp _dhgr_spr_ag0
        bcs :+
        lda _dhgr_spr_ag0
        sta g0
:       lda _dhgr_spr_ag1
        cmp g1
        bcs :+
        sta g1
:       lda y0
        cmp _dhgr_spr_ay0
        bcs :+
        lda _dhgr_spr_ay0
        sta y0
:       lda _dhgr_spr_ay1
        cmp y1
        bcs :+
        sta y1
:       lda g1
        cmp g0
        bcc @no
        lda y1
        cmp y0
@no:    rts

; void dhgr_spr_add(void): append g0..g1, y0..y1 clipped to the area; when
; the list is full, widen entry 0 instead. X kept; A/Y destroyed.
_dhgr_spr_add:
        jsr clip
        bcc add_done
add_clipped:
        ldy _dhgr_spr_dn
        cpy #DMAX
        bcc @append
        ldy #0
        lda d_g0
        cmp g0
        bcs :+
        sta g0
:       lda g1
        cmp d_g1
        bcs :+
        lda d_g1
        sta g1
:       lda d_y0
        cmp y0
        bcs :+
        sta y0
:       lda y1
        cmp d_y1
        bcs @store
        lda d_y1
        sta y1
        bcc @store              ; (C = 0)
@append:
        inc _dhgr_spr_dn
@store: lda g0
        sta d_g0,y
        lda g1
        sta d_g1,y
        lda y0
        sta d_y0,y
        lda y1
        sta d_y1,y
add_done:
        rts

; Colour pixel A -> group A (x / 7).
group:  tay
        lda _dhgr_cellbyte,y
        lsr a
        lsr a
        rts

; void dhgr_spr_update(void)
_dhgr_spr_update:
        jsr dhgr_cv_patch
        ldx #0
@slot:  lda _dhgr_spr_dirty,x
        beq @next
        lda #0
        sta _dhgr_spr_dirty,x
        lda _dhgr_spr_o_g0,x
        cmp #NONE
        beq @new
        sta g0                  ; the old box
        lda o_g1,x
        sta g1
        lda o_y0,x
        sta y0
        lda o_y1,x
        sta y1
        jsr _dhgr_spr_add
        lda #NONE
        sta _dhgr_spr_o_g0,x
@new:   lda _dhgr_spr_y1,x
        cmp #NONE
        beq @next
        sta y1
        lda _dhgr_spr_y,x
        sta y0
        lda _dhgr_spr_x,x
        jsr group
        sta g0
        lda _dhgr_spr_x1,x
        jsr group
        sta g1
        jsr clip
        bcc @next               ; outside the area
        lda g0
        sta _dhgr_spr_o_g0,x
        lda g1
        sta o_g1,x
        lda y0
        sta o_y0,x
        lda y1
        sta o_y1,x
        jsr add_clipped
@next:  inx
        cpx #MAX
        bne @slot
        lda _dhgr_spr_v_dirty
        sta moved
        beq merge
        jsr _dhgr_spr_ovd_jmp   ; (dhgr_spr_cursor.s)

; Merge overlapping rectangles until none overlap (restart after each).
merge:  ldx #0
@i:     cpx _dhgr_spr_dn
        bcs pieces
        txa
        tay
@j:     iny
        cpy _dhgr_spr_dn
        bcs @inext
        lda d_g1,y              ; overlap: g0[i] <= g1[j] && g0[j] <= g1[i]
        cmp d_g0,x              ;       && y0[i] <= y1[j] && y0[j] <= y1[i]
        bcc @j
        lda d_g1,x
        cmp d_g0,y
        bcc @j
        lda d_y1,y
        cmp d_y0,x
        bcc @j
        lda d_y1,x
        cmp d_y0,y
        bcc @j
        lda d_g0,y              ; i = bounding box of i and j
        cmp d_g0,x
        bcs :+
        sta d_g0,x
:       lda d_g1,y
        cmp d_g1,x
        bcc :+
        sta d_g1,x
:       lda d_y0,y
        cmp d_y0,x
        bcs :+
        sta d_y0,x
:       lda d_y1,y
        cmp d_y1,x
        bcc :+
        sta d_y1,x
:       dec _dhgr_spr_dn        ; j = the last one
        ldx _dhgr_spr_dn
        lda d_g0,x
        sta d_g0,y
        lda d_g1,x
        sta d_g1,y
        lda d_y0,x
        sta d_y0,y
        lda d_y1,x
        sta d_y1,y
        jmp merge
@inext: inx
        bne @i

; Cut each rectangle into pieces: columns of at most gmax groups, then
; bands of at most cbytes / (7 * groups) rows.
pieces: lda #0
        sta k
@rect:  ldx k
        cpx _dhgr_spr_dn
        bcc :+
        jmp pieces_done
:       lda d_g0,x
        sta pg
@cut:   ldx k
        lda d_g1,x              ; pn = min(g1 - pg + 1, gmax)
        sec
        sbc pg
        cmp gmax
        bcs @full
        adc #1                  ; (C = 0)
        bne :+
@full:  lda gmax
:       sta pn
        asl a                   ; canvas stride 7 * pn
        asl a
        asl a
        sec
        sbc pn
        sta _dhgr_cv_w
        cmp capw
        beq @capok
        sta capw
        sta tmp1
        lda cbytes              ; cap = cbytes / stride (>= 1)
        ldy #0
        sec
:       sbc tmp1
        bcc :+
        iny
        bcs :-
:       sty cap
@capok:
        lda d_y0,x
        sta py
@band:  ldx k
        lda d_y1,x              ; pr = min(y1 - py + 1, cap)
        sec
        sbc py
        cmp cap
        bcs @capr
        adc #1                  ; (C = 0)
        bne :+
@capr:  lda cap
:       sta pr
        jsr piece
        lda py
        clc
        adc pr
        sta py
        ldx k
        lda d_y1,x
        cmp py
        bcs @band
        lda pg
        clc
        adc pn
        sta pg
        lda d_g1,x
        cmp pg
        bcc :+
        jmp @cut
:       inc k
        jmp @rect
pieces_done:
        lda #0
        sta _dhgr_spr_dn
        lda moved               ; the overlay outside the area: save-under
        beq @end
        jmp _dhgr_spr_cur_jmp   ; (dhgr_spr_cursor.s)
@end:   rts

; One piece pg/pn/py/pr: background, slots, write.
piece:  lda pg
        asl a
        sta _dhgr_spr_goff
        asl a
        asl a                   ; 8 * pg
        sec
        sbc pg
        sta _dhgr_cv_x0
        clc
        adc _dhgr_cv_w
        sta _dhgr_cv_x1
        lda pg
        clc
        adc pn
        asl a
        sta _dhgr_spr_gend
        lda py
        sta _dhgr_cv_y0
        lda pr
        sta _dhgr_cv_h
        clc
        adc py
        sta _dhgr_cv_y1
        jsr cv_begin            ; row offsets for the painters
        lda _dhgr_spr_bg
        beq :+
        jsr _dhgr_spr_bg_jmp    ; cells or tiles (dhgr_spr_cells.s)
        jmp slots
:       lda _dhgr_spr_solid_c
        jsr _dhgr_cv_solid
slots:  ldx #0
@slot:  lda _dhgr_spr_y1,x
        cmp #NONE
        beq @next
        cmp py                  ; y1 >= py
        bcc @next
        lda _dhgr_spr_y,x
        cmp _dhgr_cv_y1         ; y < py + pr
        bcs @next
        lda _dhgr_spr_x1,x
        cmp _dhgr_cv_x0
        bcc @next
        lda _dhgr_spr_x,x
        cmp _dhgr_cv_x1
        bcs @next
        sta _dhgr_cv_sx
        lda _dhgr_spr_y,x
        sta _dhgr_cv_sy
        lda _dhgr_spr_shlo,x
        sta _dhgr_cv_shape
        lda _dhgr_spr_shhi,x
        sta _dhgr_cv_shape+1
        lda _dhgr_spr_flags,x
        sta _dhgr_cv_flags
        txa
        asl a
        asl a
        adc #<_dhgr_spr_pal     ; (C = 0)
        sta _dhgr_cv_pal
        lda #>_dhgr_spr_pal
        adc #0
        sta _dhgr_cv_pal+1
        txa                     ; (X: the painter destroys it)
        pha
        jsr _dhgr_cv_paint
        pla
        tax
@next:  inx
        cpx #MAX
        bne @slot
        jmp _dhgr_spr_blit
