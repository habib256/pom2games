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
.export _dhgr_spr_pal, _dhgr_spr_dn, dhgr_spr_slots
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
DOUBLE .set 0
.if .defined(DHGR_SPR_DOUBLE)
.if DHGR_SPR_DOUBLE
DOUBLE .set 1
.endif
.endif
.if DOUBLE
.import _dhgr_base
.export cur_bank
.endif
VBL .set 0
.if .defined(DHGR_SPR_VBL)
.if DHGR_SPR_VBL
VBL .set 1
.endif
.endif
.if VBL
.import _a2_vbl_mode, _a2_vbl_count, _a2_vbl_beam
.importzp tmp2, tmp3, tmp4
.export vbl_edge, vbl_seen
.endif

.ifndef DHGR_SPR_MAX
DHGR_SPR_MAX = 8
.endif
MAX = DHGR_SPR_MAX
dhgr_spr_slots = MAX            ; (dhgr_spr_palette.s)
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
.if DOUBLE
cur_obx:  .res 6                ; the cursor on screen + osave (dhgr_spr_cursor.s)
.else
cur_obx:  .res 4                ; the cursor on screen (dhgr_spr_cursor.s)
.endif
_dhgr_spr_bg:    .res 1         ; background: 0 solid, else cells or tiles
_dhgr_spr_solid_c: .res 1
_dhgr_spr_ov_on: .res 1         ; bit 7: the overlay has a box in the area
_dhgr_spr_ag0:   .res 1         ; area, inclusive (0, 19, 0, 191), in
_dhgr_spr_ag1:   .res 1         ; this order (dhgr_spr_cursor.s's pass)
_dhgr_spr_ay0:   .res 1
_dhgr_spr_ay1:   .res 1
capw:   .res 1                  ; (cap's width; 0: none yet)
.if DOUBLE
p_n:    .res 1                  ; the other page's pending damage: count,
p_page: .res 1                  ; its page ($20/$40; 0: none),
mvp:    .res 1                  ; bit 0/1: page 1/2 owes the overlay pass
cur_bank: .res 12               ; each page's cursor (dhgr_spr_cursor.s)
.endif
zero_hi:
none_lo:                        ; set to NONE by dhgr_spr_init (right after)
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
.if DOUBLE
p_g0:   .res DMAX               ; damage the other page has not received
p_g1:   .res DMAX
p_y0:   .res DMAX
p_y1:   .res DMAX
n0:     .res 1
.endif

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
        ldy #2
        lda (sp),y
        sta _dhgr_cv_buf
        iny
        lda (sp),y
        sta _dhgr_cv_buf+1
        ldx #none_hi - zero_lo  ; zero_lo..: 0, then none_lo..: NONE
@clr:   lda #NONE
        cpx #zero_hi - zero_lo + 1
        bcs :+
        lda #0
:       sta zero_lo-1,x
        dex
        bne @clr
        lda #19
        sta _dhgr_spr_ag1
        lda #191
        sta _dhgr_spr_ay1
        lda #1
        .byte $2C               ; (BIT abs: skip lda #0)
@bad:   lda #0
        ldx #0
        jmp incsp4

; Clip g0..g1, y0..y1 to the area: C = 1 if something is left. A/Y
; destroyed. Fields 0 and 2 (g0, y0) take the larger, 1 and 3 the smaller.
clip:   ldy #3
@f:     lda g0,y
        cmp _dhgr_spr_ag0,y     ; C = r >= a
        tya
        and #1
        bne @min
        bcs @n                  ; g0/y0: r >= a: kept
        bcc @set
@min:   bcc @n                  ; g1/y1: r < a: kept
@set:   lda _dhgr_spr_ag0,y
        sta g0,y
@n:     dey
        bpl @f
        lda g1
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
        bcs add_full
        inc _dhgr_spr_dn
store:  lda g0                  ; d[Y] = g0..y1
        sta d_g0,y
        lda g1
        sta d_g1,y
        lda y0
        sta d_y0,y
        lda y1
        sta d_y1,y
        rts
add_full:                       ; full: entry 0 absorbs it
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
        bcs :+
        lda d_y1
        sta y1
:       ldy #0
        beq store
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
.if DOUBLE
        jsr page_moved
.else
        sta moved
.endif
        beq :+
        jsr _dhgr_spr_ovd_jmp   ; (dhgr_spr_cursor.s)
:
.if DOUBLE
        jsr merge               ; (this update's own damage, kept merged)
        jsr history
.endif
        jsr merge

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

.if DOUBLE
; DHGR_SPR_DOUBLE: the update draws on the hidden (draw) page. The damage
; this page has not received yet (built while the other page was drawn)
; joins this update's; this update's own damage is kept for the other page.
; A list belongs to one page (p_page): updates without a present in
; between append to it. X destroyed.
history:
        ldx _dhgr_spr_dn
        stx n0
        lda _dhgr_base
        cmp p_page
        bne @keep               ; the list is the other page's: append
        ldx #0
@apply: cpx p_n
        bcs @own
        lda p_g0,x
        sta g0
        lda p_g1,x
        sta g1
        lda p_y0,x
        sta y0
        lda p_y1,x
        sta y1
        jsr _dhgr_spr_add       ; (X kept)
        inx
        bne @apply
@own:   lda #0
        sta p_n
@keep:  ldx #0
@copy:  cpx n0
        bcs @done
        ldy p_n
        cpy #DMAX
        bcc @new
        lda d_g0,x              ; full: widen entry 0
        cmp p_g0
        bcs :+
        sta p_g0
:       lda d_g1,x
        cmp p_g1
        bcc :+
        sta p_g1
:       lda d_y0,x
        cmp p_y0
        bcs :+
        sta p_y0
:       lda d_y1,x
        cmp p_y1
        bcc @next
        sta p_y1
        bcs @next
@new:   inc p_n
        lda d_g0,x
        sta p_g0,y
        lda d_g1,x
        sta p_g1,y
        lda d_y0,x
        sta p_y0,y
        lda d_y1,x
        sta p_y1,y
@next:  inx
        bne @copy
@done:  lda _dhgr_base
        eor #$60                ; the other page
        sta p_page
        rts

; A = v_dirty (the overlay changed: both pages owe the outside pass).
; moved = this page's due pass, cleared; returns A = v_dirty (Z set).
page_moved:
        tax
        beq :+
        lda #3
        ora mvp
        sta mvp
:       lda _dhgr_base          ; $20 -> 1, $40 -> 2
        lsr a
        lsr a
        lsr a
        lsr a
        lsr a
        tay
        and mvp
        sta moved
        tya
        eor #$FF
        and mvp
        sta mvp
        txa
        rts
.endif

; Merge overlapping rectangles until none overlap. Entry i absorbs every
; entry j it overlaps (scanning them all again after each absorption);
; one before it (j < i) absorbs i instead and becomes i. The entries
; before i stay disjoint: O(n^2) compares plus n per merge.
merge:  ldx #0
        beq m_i
m_next: inx
m_i:    cpx _dhgr_spr_dn
        bcc :+
        rts
:       stx k
        ldy #0
        beq m_j
m_skip: iny
m_j:    cpy _dhgr_spr_dn
        bcs m_next
        cpy k
        beq m_skip
        lda d_g1,y              ; overlap: g0[i] <= g1[j] && g0[j] <= g1[i]
        cmp d_g0,x              ;       && y0[i] <= y1[j] && y0[j] <= y1[i]
        bcc m_skip
        lda d_g1,x
        cmp d_g0,y
        bcc m_skip
        lda d_y1,y
        cmp d_y0,x
        bcc m_skip
        lda d_y1,x
        cmp d_y0,y
        bcc m_skip
        cpy k
        bcs :+                  ; j > i: i absorbs j
        sty k                   ; j < i: j absorbs i and becomes i
        txa
        ldx k
        tay
:       lda d_g0,y              ; d[X] = bounding box of d[X] and d[Y]
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
:       dec _dhgr_spr_dn        ; d[Y] = the last one
        ldx _dhgr_spr_dn
        lda d_g0,x
        sta d_g0,y
        lda d_g1,x
        sta d_g1,y
        lda d_y0,x
        sta d_y0,y
        lda d_y1,x
        sta d_y1,y
        ldx k
        ldy #0
        jmp m_j

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
.if VBL
        jsr vbl_wait
.endif
        jmp _dhgr_spr_blit
.if VBL
; DHGR_SPR_VBL: when this piece is the whole damage and its write (rows
; top to bottom, ROWC + GRPC * groups cycles a row) ends each row before
; the beam starts it, counted from a VBL edge (the blank: 70 rows of 65
; cycles, then row y at 4,550 + 65 y), wait for the next edge: the
; composed piece is then written ahead of the beam (no tear). Otherwise
; (several pieces, too many rows, the overlay crossing it, no clock) the
; plain order: no wait. The clock: dev/lib/apple2c/apple2vbl (a2_vbl_mode
; 1: //e $C019 polled here; 2: //c mouse VBL interrupt, its count
; awaited, a later start; 0: none). Condition, k rows from row y:
;   LAT + k * (ROWC + GRPC * groups) <= 4,550 + 65 * (y + k - 1)
ROWC = 95                       ; row set-up and end (dhgr_spr_asm.s)
GRPC = 165                      ; pack + write of a group, page crossings included
OVROW = 60                      ; ov_row's early exit (the overlay elsewhere)
LAT_POLL = 100                  ; //e: poll granularity + the blit's start
LAT_IRQ = 1200                  ; //c: interrupt dispatch (ProDOS, firmware)
vbl_no: rts
vbl_wait:
        lda _a2_vbl_mode
        beq vbl_no
        ldx _dhgr_spr_dn
        dex
        bne vbl_no              ; several rectangles
        lda d_g1
        sec
        sbc d_g0
        clc
        adc #1
        cmp pn
        bne vbl_no              ; several pieces
        lda d_y1
        sec
        sbc d_y0
        clc
        adc #1
        cmp pr
        bne vbl_no
        ldx #<(65 - ROWC)       ; 65 - a row's cost: tmp1/tmp2 (negative)
        lda #>(65 - ROWC)
        bit _dhgr_spr_ov_on
        bpl @rowc
        lda w_y1                ; the overlay crossing the piece: no
        cmp py
        bcc @apart
        lda w_y0
        cmp _dhgr_cv_y1
        bcs @apart
        lda w_g1
        cmp pg
        bcc @apart
        lda pg
        clc
        adc pn
        sta tmp1
        lda _dhgr_spr_w_g0
        cmp tmp1
        bcc vbl_no
@apart: ldx #<(65 - ROWC - OVROW)
        lda #>(65 - ROWC - OVROW)
@rowc:  stx tmp1
        sta tmp2
        ldy pn                  ; - GRPC * groups
@grp:   lda tmp1
        sec
        sbc #<GRPC
        sta tmp1
        lda tmp2
        sbc #>GRPC
        sta tmp2
        dey
        bne @grp
        lda py                  ; budget = 65 * y + 4,550 - 65 - LAT: Y/tmp3
        sta tmp3
        lda #0
        ldy #6
:       asl tmp3
        rol a
        dey
        bne :-
        tay                     ; Y/tmp3 = 64 y
        lda tmp3
        clc
        adc py
        sta tmp3
        bcc :+
        iny
:       ldx #<(4550 - 65 - LAT_POLL)
        lda #>(4550 - 65 - LAT_POLL)
        sta tmp4
        lda _a2_vbl_mode
        lsr a
        bcs :+                  ; (mode 1: //e)
        ldx #<(4550 - 65 - LAT_IRQ)
        lda #>(4550 - 65 - LAT_IRQ)
        sta tmp4
:       txa
        clc
        adc tmp3
        sta tmp3
        tya
        adc tmp4
        tay
        ldx pr                  ; each row: budget += 65 - its cost
@row:   lda tmp3
        clc
        adc tmp1
        sta tmp3
        tya
        adc tmp2
        tay
        bcc @out                ; (a negative addend: C = 0 is a borrow)
        dex
        bne @row
        beq vbl_edge
@out:   rts
; Wait for the next VBL edge (bounded: ~45,000 cycles, then no wait).
vbl_edge:
        lda _a2_vbl_mode
        lsr a
        bcs @poll
        lda _a2_vbl_count       ; //c: the handler counts the next refresh
        ldx #0
        ldy #16
:       cmp _a2_vbl_count
        bne @done
        dex
        bne :-
        dey
        bne :-
@done:  rts
@poll:  ldx #0
        ldy #16
@pic:   bit $C019               ; the picture (bit 7 set) ...
        bmi @blank
        dex
        bne @pic
        dey
        bne @pic
        rts
@blank: bit $C019               ; ... then the blank
        bpl vbl_seen
        dex
        bne @blank
        dey
        bne @blank
        rts
vbl_seen:                       ; (test_dhgr_spr.py watches it)
        lda #0                  ; counted like a2_vbl_scan
        sta _a2_vbl_beam
        inc _a2_vbl_count
        rts
.endif

