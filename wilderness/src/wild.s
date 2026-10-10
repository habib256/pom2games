; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; wild.s -- Wilderness reimplementation: first-person terrain view
; ============================================================================
; The view engine of Electric Transit's Wilderness (1985), rebuilt from the
; analysis in docs/ANALYSE.md: a ray per screen column over a height map,
; occlusion by the steepest slope seen so far, striped ridges. The map is
; the MAP file (tools/mkmap.py) BLOADed at $7000 by HELLO.
;
; tools/view_ref.py is the bit-exact Python reference of render below; the
; test compares the two on several positions.
;
; Keys: LEFT/J and RIGHT/K turn 22.5 degrees, A/Z turn 45 degrees, V redraws,
;       I/UP walk one cell forward, M/DOWN one cell back, ESC/Q quit.
; ============================================================================

        .include "apple2.inc"
        .include "zp.inc"

MAP      = $7000
DIVTAB   = $4000                ; HGR page 2 (unused): r * 256 / n, see divinit
GRID     = MAP + 64
GW       = 112                  ; grid cells west-east (1 cell = 2 units)
GH       = 84                   ; grid cells south-north
UNITS    = 560                  ; azimuth units per turn, 140 per quadrant
FOV_HALF = 70
STEPS    = 128                  ; ray steps (cells)
HORIZON  = 95
VIEW_ROWS = 160                 ; HGR rows 0..159, text below (mixed mode)
EYE      = 2                    ; eye height above the ground, in levels

M_STARTX = MAP + 2              ; 8.8 cells
M_STARTY = MAP + 4
M_HEAD   = MAP + 6
M_BASE   = MAP + 10             ; base altitude / 100 ft
M_SNOW   = MAP + 11             ; first snow level

; pixel pairs (even, odd) of a column, as (set even, set odd)
C_SKY    = %01                  ; violet
C_GROUND = %10                  ; green
C_SNOW   = %11                  ; white
C_WATER  = %01                  ; violet
C_RIDGE  = %00                  ; black

WNDTOP   = $22
CLREOL   = $FC9C

.segment "ZEROPAGE"
px:      .res 2                 ; position, 8.8 cells (lo = fraction)
py:      .res 2
heading: .res 2                 ; 0..559, 0 = north, 140 = east
ang:     .res 2                 ; azimuth of the current column
dx:      .res 2                 ; ray step, signed 8.8
dy:      .res 2
rx:      .res 2                 ; ray position
ry:      .res 2
thr:     .res 2                 ; slope threshold, signed 8.8 levels
tinc:    .res 2                 ; threshold increment per step
qlo:     .res 1                 ; div16 dividend / quotient
qhi:     .res 1
divisor: .res 1
n:       .res 1                 ; step number + 127: 128 for the first, 0 past the last
dz:      .res 1                 ; level - eye
eye:     .res 1
col:     .res 1                 ; screen column 0..139
top:     .res 1                 ; first painted row of the column
row:     .res 1
gp:      .res 2                 ; grid row pointer
hp:      .res 2                 ; HGR row pointer
sp_end:  .res 1                 ; span end row (exclusive)
be:      .res 1                 ; column bytes and masks
bo:      .res 1
me:      .res 1                 ; and-masks (pixel cleared)
mo:      .res 1
se:      .res 1                 ; or-bits of the colour
so:      .res 1
eb:      .res 1                 ; the pixel bits (~me, ~mo)
ob:      .res 1
mc:      .res 1                 ; me & mo, when both pixels share a byte
fm:      .res 1                 ; fill: and-mask, or-bits (unrolled code)
fs:      .res 1
fj:      .res 2                 ; fill: entry and exit of the unrolled rows
fp:      .res 2
row0:    .res 1
eyeb:    .res 1                 ; 128 - eye: level + eyeb = dz + 128
dzb:     .res 1                 ; dz + 128 of the sample
m1:      .res 1                 ; ridge dot: mask of the first byte
same:    .res 1                 ; 0 when both pixels share a byte
fsc:     .res 4                 ; or-bits of each colour (shared byte)
c1:      .res 1                 ; render columns col..c1-1
hp2:     .res 2                 ; scroll: the other row pointer
shift:   .res 1                 ; scroll: bytes
tp:      .res 2                 ; DIVTAB row pointer
dq:      .res 1                 ; divinit: 256 / n, 256 mod n, q, remainder
dm:      .res 1
dacc:    .res 1
drem:    .res 1
cx:      .res 1                 ; x cell of the ray (Y in the step loop)
rowsl:   .res 1                 ; row changes left before the ray leaves the map
num:     .res 2                 ; print_u16 value

.segment "CODE"

start:
        APPLE2_PREAMBLE
        jsr     apple2_zp_save
        lda     M_STARTX
        sta     px
        lda     M_STARTX+1
        sta     px+1
        lda     M_STARTY
        sta     py
        lda     M_STARTY+1
        sta     py+1
        lda     M_HEAD
        sta     heading
        lda     M_HEAD+1
        sta     heading+1
        lda     #<twice         ; n = 128 reads the 2r table
        sta     div_lo+128
        lda     #>twice
        sta     div_hi+128
        jsr     divinit
        jsr     hgr_init_clear
        lda     MIXSET
        lda     #20
        sta     WNDTOP
        jsr     HOME

frame:
        jsr     status
        lda     #0              ; whole view
        sta     col
        lda     #140
        sta     c1
        jsr     render
idle:   jsr     wait_key
        cmp     #KC_ESC
        beq     quit
        cmp     #'Q'
        beq     quit
        cmp     #'V'            ; redraw the view
        bne     @keys
        jmp     frame
@keys:  ldx     #0
        cmp     #KC_LEFT
        beq     turn_j
        cmp     #'J'
        beq     turn_j
        inx
        cmp     #KC_RIGHT
        beq     turn_j
        cmp     #'K'
        beq     turn_j
        inx
        cmp     #'A'
        beq     turn_j
        inx
        cmp     #'Z'
        beq     turn_j
        ldx     #1
        cmp     #'I'
        beq     walk_j
        cmp     #KC_UP
        beq     walk_j
        ldx     #$FF
        cmp     #'M'
        beq     walk_j
        cmp     #KC_DOWN
        beq     walk_j
        jmp     idle

turn_j: jmp     turn
walk_j: jmp     walk

quit:   lda     #0
        sta     WNDTOP
        jmp     apple2_exit

; turn -- X = 0: -35, 1: +35, 2: -70, 3: +70 azimuth units (22.5 / 45 deg).
; A column only depends on its absolute azimuth: 35 columns are 70 pixels,
; exactly 10 bytes, so the view scrolls and only the new columns are drawn,
; like the original's PAN.
turn:   clc
        lda     turn_lo,x
        adc     heading
        sta     ang
        lda     turn_hi,x
        adc     heading+1
        sta     ang+1
        jsr     wrap_ang
        lda     ang
        sta     heading
        lda     ang+1
        sta     heading+1
        lda     turn_c0,x
        sta     col
        lda     turn_c1,x
        sta     c1
        lda     turn_sh,x
        sta     shift
        txa
        lsr     a               ; carry: turning right, the view moves left
        jsr     scroll
        jsr     status
        jsr     render
        jmp     idle

; scroll -- move HGR rows 0..159 by `shift` bytes: left when carry is set
;           (bytes shift..39 -> 0..39-shift), right otherwise.
scroll: ldx     #0
        php
@row:   lda     hgr_lo,x
        sta     hp
        clc
        adc     shift
        sta     hp2
        lda     hgr_hi,x
        sta     hp+1
        sta     hp2+1
        plp
        php
        bcc     @right
        ldy     #0
@l:     lda     (hp2),y
        sta     (hp),y
        iny
        cpy     #40
        bcs     @next
        tya
        adc     shift
        cmp     #40
        bcc     @l
        bcs     @next
@right: lda     #39
        sec
        sbc     shift
        tay
@r:     lda     (hp),y
        sta     (hp2),y
        dey
        bpl     @r
@next:  inx
        cpx     #VIEW_ROWS
        bcc     @row
        plp
        rts

; walk one cell along the heading (X = 1) or back (X = $FF), if on the map
walk:   stx     col             ; direction keeps row busy
        lda     heading
        sta     ang
        lda     heading+1
        sta     ang+1
        jsr     direction
        lda     col
        bpl     @fwd
        ldx     #2
@neg:   sec
        lda     #0
        sbc     dx,x
        sta     dx,x
        lda     #0
        sbc     dx+1,x
        sta     dx+1,x
        dex
        dex
        bpl     @neg
@fwd:   clc
        lda     px
        adc     dx
        sta     rx
        lda     px+1
        adc     dx+1
        sta     rx+1
        cmp     #GW
        bcs     @no
        clc
        lda     py
        adc     dy
        sta     ry
        lda     py+1
        adc     dy+1
        sta     ry+1
        cmp     #GH
        bcs     @no
        lda     rx
        sta     px
        lda     rx+1
        sta     px+1
        lda     ry
        sta     py
        lda     ry+1
        sta     py+1
        jmp     frame
@no:    jsr     BELL
        jmp     idle

; ----------------------------------------------------------------------------
; render -- draw the view from (px, py) toward heading on HGR rows 0..159
; ----------------------------------------------------------------------------
render:
        ldx     col             ; black out the bytes of columns col..c1-1:
        lda     col_be,x        ; ranges are multiples of 35 columns, i.e.
        sta     tmp             ; of 10 bytes
        lda     #40
        ldx     c1
        cpx     #140
        bcs     @b1
        lda     col_be,x
@b1:    sta     tmp2
        lda     #0
        ldy     tmp
@clr:   jsr     clear_rows
        iny
        cpy     tmp2
        bcc     @clr
        ldx     py+1
        lda     grid_lo,x
        sta     gp
        lda     grid_hi,x
        sta     gp+1
        ldy     px+1
        lda     (gp),y
        and     #$7F
        clc
        adc     #EYE
        sta     eye
        eor     #$FF            ; eyeb = 128 - eye
        sec
        adc     #128
        sta     eyeb
        clc                     ; ang = heading - 70 + col
        lda     heading
        adc     col
        sta     ang
        lda     heading+1
        adc     #0
        sta     ang+1
        sec
        lda     ang
        sbc     #FOV_HALF
        sta     ang
        lda     ang+1
        sbc     #0
        sta     ang+1
        jsr     wrap_ang

@column:
        jsr     direction
        ldx     col
        lda     col_be,x
        sta     be
        lda     col_bo,x
        sta     bo
        lda     col_me,x
        sta     me
        lda     col_mo,x
        sta     mo
        eor     #$FF
        sta     ob
        lda     me
        eor     #$FF
        sta     eb
        lda     me
        and     mo
        sta     mc
        sta     fm
        sta     m1
        lda     be
        eor     bo
        sta     same
        beq     @one
        lda     me              ; pixels in two bytes: the dot clears each
        sta     m1
@one:   lda     #0              ; colour or-bits: 0 none, 1 even, 2 odd, 3 both
        sta     fsc
        lda     eb
        sta     fsc+1
        lda     ob
        sta     fsc+2
        ora     eb
        sta     fsc+3
        lda     px
        sta     rx
        lda     px+1
        sta     rx+1
        lda     py
        sta     ry
        lda     py+1
        sta     ry+1
        lda     #0
        sta     thr
        sta     tinc
        sta     tinc+1
        lda     #$80
        sta     thr+1
        lda     #127
        sta     n
        lda     #VIEW_ROWS
        sta     top
        ; the ray follows its cell: Y = x cell, gp = row; a carry out of a
        ; fraction moves it (patched per column for the signs of dx, dy;
        ; BIT turns the branch off for a step of exactly +1 cell)
        ldx     py+1
        lda     grid_lo,x
        sta     gp
        lda     grid_hi,x
        sta     gp+1
        lda     px+1
        sta     cx
        lda     dx+1
        beq     @xpos
        bmi     @xneg
        lda     #$24            ; dx = +256: BIT (move every step), INY
        ldx     #$C8
        bne     @xset
@xpos:  lda     #$90            ; 0 <= dx < 256: BCC, INY
        ldx     #$C8
        bne     @xset
@xneg:  lda     #$B0            ; dx < 0: BCS, DEY
        ldx     #$88
@xset:  sta     @xbr
        stx     @xop
        lda     dy+1
        beq     @ypos
        bmi     @yneg
        lda     #$24            ; dy = +256
        bne     @yup
@ypos:  lda     #$90
@yup:   sta     @ybr
        lda     #GW
        sta     @gpl+1
        lda     #0
        sta     @gph+1
        lda     #GH-1
        sec
        sbc     py+1
        sta     rowsl
        jmp     @back
@yneg:  lda     #$B0
        sta     @ybr
        lda     #<(-GW)
        sta     @gpl+1
        lda     #>(-GW)
        sta     @gph+1
        lda     py+1
        sta     rowsl
        jmp     @back
@sky_j: jmp     @sky
@step_j: jmp    @back
@ovf:   lda     tinc+1          ; overflow: rising past +127 levels ends
        bpl     @sky_j          ; the column, falling past -128 clamps
        lda     #0
        sta     thr
        lda     #$80
        bne     @thr

@back:  ldy     cx              ; Y = x cell again
@stepc: clc                     ; @step expects carry clear
@step:  inc     n
        beq     @sky_j
        lda     rx
        adc     dx
        sta     rx
@xbr:   bcc     @xk             ; patched: BCC / BCS / BIT
@xop:   iny                     ; patched: INY / DEY
        cpy     #GW
        bcs     @sky_j
@xk:    clc
        lda     ry
        adc     dy
        sta     ry
@ybr:   bcc     @yk
        dec     rowsl
        bmi     @sky_j
        clc
        lda     gp
@gpl:   adc     #GW             ; patched: +-112
        sta     gp
        lda     gp+1
@gph:   adc     #0
        sta     gp+1
@yk:    clc
        lda     (gp),y
        and     #$7F
        adc     eyeb            ; levels <= 125: dz + 128 stays in 1..253
        sta     dzb
        lda     thr             ; thr += tinc (no carry out of the add above)
        adc     tinc
        sta     thr
        lda     thr+1
        adc     tinc+1
        bvs     @ovf
@thr:   sta     thr+1
        eor     #$80            ; visible when dz > floor(thr), i.e.
        cmp     dzb             ; dz + 128 > (thr >> 8) + 128, unsigned
        bcs     @stepc
        sty     cx

        ; visible: tinc = trunc(dz * 256 / n), thr = dz * 256, then the row
        lda     n
        sec
        sbc     #127
        sta     divisor
        tax
        lda     div_lo,x        ; DIVTAB row of n
        sta     tp
        lda     div_hi,x
        sta     tp+1
        lda     #0
        sta     thr
        lda     dzb
        eor     #$80
        sta     thr+1
        bmi     @neg
        cmp     divisor         ; dz >= 0
        bcs     @pbig
        tay                     ; q = dz * 256 / n < 256
        lda     (tp),y
        sta     tinc
        tax
        lda     #0
        sta     tinc+1
        lda     row_p0,x
        jmp     @drawchk
@pbig:  jsr     bigdiv          ; dz >= n: q >= 256
        sta     tinc
        lda     qhi
        sta     tinc+1
        cmp     #2
        bcs     @prow0          ; q >= 512: top row
        ldx     tinc
        lda     row_p1,x
        jmp     @drawchk
@prow0: lda     #0
        jmp     @drawchk
@neg:   lda     #128            ; dz < 0: |dz| = 128 - (dz + 128)
        sec
        sbc     dzb
        cmp     divisor
        bcs     @nbig
        tay
        lda     (tp),y          ; q < 256
        tax
        eor     #$FF            ; tinc = -q
        clc
        adc     #1
        sta     tinc
        lda     #$FF
        adc     #0
        sta     tinc+1
        lda     row_n0,x
        jmp     @drawchk
@nbig:  jsr     bigdiv          ; |dz| >= n: q >= 256
        eor     #$FF
        clc
        adc     #1
        sta     tinc
        lda     qhi
        eor     #$FF
        adc     #0
        sta     tinc+1
        lda     qhi
        cmp     #2
        bcs     @hide           ; q >= 512: below the view
        ldx     qlo
        lda     row_n1,x        ; $FF below the bottom row
@drawchk:
        cmp     top
        bcc     @shown
@hide:  jmp     @back          ; hidden behind nearer ground (or $FF)
@shown: sta     row
        tay
        iny                     ; colour rows row+1..top-1, often none
        cpy     top
        bcs     @ridge
        lda     top
        sta     sp_end
        sty     tmp2
        ldy     cx
        lda     (gp),y
        ldx     #C_WATER
        asl     a               ; bit 7: water
        bcs     @col
        ldx     #C_SNOW
        lsr     a
        cmp     M_SNOW
        bcs     @col
        ldx     #C_GROUND
@col:   ldy     tmp2
        txa
        jsr     span
@ridge: lda     row             ; the ridge row stays black: the view was
        sta     top             ; cleared and every pixel is painted once
        beq     @next
        jmp     @step_j

@sky:   lda     top
        sta     sp_end
        ldy     #0
        lda     #C_SKY
        jsr     span
@next:  inc     ang
        bne     @wrap
        inc     ang+1
@wrap:  jsr     wrap_ang
        inc     col
        lda     col
        cmp     c1
        bcs     @done
        jmp     @column
@done:  rts

; ----------------------------------------------------------------------------
; span -- paint rows Y..sp_end-1 of the current column with colour A
;         (bit 0 = even pixel on, bit 1 = odd pixel on). Clobbers A, X, Y.
; ----------------------------------------------------------------------------
span:   cpy     sp_end
        bcs     @done
        ldx     same
        bne     @split
        tax                     ; one byte: fm = mc is set per column
        lda     fsc,x
        sta     fs
        lda     be
        jmp     fill
@split: sta     tmp
        lda     #0
        lsr     tmp
        bcc     @e
        lda     eb
@e:     sta     se
        lda     #0
        lsr     tmp
        bcc     @o
        lda     ob
@o:     sta     so
        sty     row0
        lda     me
        sta     fm
        lda     se
        sta     fs
        lda     be
        jsr     fill
        ldy     row0
        lda     mo
        sta     fm
        lda     so
        sta     fs
        lda     bo
        jmp     fill
@done:  rts

; fill -- rows Y..sp_end-1 of byte column A: byte or fs, through the
;         unrolled span_rows (an RTS is planted on row sp_end for the call).
fill:   sta     tmp
        ldx     sp_end
        lda     span_lo,x
        sta     fp
        lda     span_hi,x
        sta     fp+1
        lda     span_lo,y
        sta     fj
        lda     span_hi,y
        sta     fj+1
        ldy     #0
        lda     #$60            ; RTS
        sta     (fp),y
        ldy     tmp
        jsr     @go
        ldy     #0
        lda     #$B9            ; LDA abs,Y
        sta     (fp),y
        rts
@go:    jmp     (fj)

; ----------------------------------------------------------------------------
; direction -- dx, dy = the 8.8 unit step of azimuth ang (0..559)
;   quadrant 0: (s, c)  1: (c, -s)  2: (-s, -c)  3: (-c, s)
;   s = sin(i * 90 / 140), c = sin((140 - i) * 90 / 140), i = ang mod 140
; ----------------------------------------------------------------------------
direction:
        lda     ang
        ldx     ang+1
        ldy     #0              ; quadrant
@q:     cpx     #0
        bne     @sub
        cmp     #140
        bcc     @got
@sub:   sec
        sbc     #140
        bcs     @nb
        dex
@nb:    iny
        bne     @q
@got:   tax                     ; X = i
        sty     row             ; quadrant
        lda     sin_lo,x        ; dx = s, dy = c
        sta     dx
        lda     sin_hi,x
        sta     dx+1
        txa
        eor     #$FF
        sec
        adc     #140            ; 140 - i
        tax
        lda     sin_lo,x
        sta     dy
        lda     sin_hi,x
        sta     dy+1
        lda     row
        beq     @rts
        cmp     #2
        beq     @q2
        bcs     @q3
        jsr     swap            ; q1: (c, -s)
        jmp     neg_dy
@q2:    jsr     neg_dx          ; q2: (-s, -c)
        jmp     neg_dy
@q3:    jsr     swap            ; q3: (-c, s)
        jmp     neg_dx
@rts:   rts

swap:   ldx     #1
@s:     lda     dx,x
        ldy     dy,x
        sta     dy,x
        sty     dx,x
        dex
        bpl     @s
        rts

neg_dx: ldx     #0
        beq     neg
neg_dy: ldx     #dy-dx
neg:    sec
        lda     #0
        sbc     dx,x
        sta     dx,x
        lda     #0
        sbc     dx+1,x
        sta     dx+1,x
        rts

; wrap_ang -- bring the signed 16-bit ang into 0..559
wrap_ang:
        lda     ang+1
        bpl     @hi
        clc                     ; negative: add 560
        lda     ang
        adc     #<UNITS
        sta     ang
        lda     ang+1
        adc     #>UNITS
        sta     ang+1
        rts
@hi:    lda     ang
        cmp     #<UNITS
        lda     ang+1
        sbc     #>UNITS
        bcc     @ok
        sta     ang+1           ; >= 560: subtract 560
        lda     ang
        sbc     #<UNITS
        sta     ang
@ok:    rts

; ----------------------------------------------------------------------------
; bigdiv -- A = |dz| >= n = divisor, tp = DIVTAB row of n:
;           qhi:qlo = |dz| * 256 / n, returns A = qlo. Clobbers Y.
; ----------------------------------------------------------------------------
bigdiv: sta     qhi
        lda     #0
        .repeat 8
        asl     qhi
        rol     a
        cmp     divisor
        bcc     :+
        sbc     divisor
        inc     qhi
:
        .endrep
        tay                     ; remainder r < n: low byte r * 256 / n
        lda     (tp),y
        sta     qlo
        rts

; ----------------------------------------------------------------------------
; divinit -- fill DIVTAB: for n = 2..127, the n bytes floor(r * 256 / n),
;            r = 0..n-1, at div_lo/div_hi[n] (n = 1 points at the 0 of n = 2;
;            n = 128 is 2r). By recurrence: q(r+1) = q(r) + 256 div n, plus 1
;            when the remainder (+ 256 mod n) reaches n.
; ----------------------------------------------------------------------------
divinit:
        ldx     #2
@n:     stx     divisor
        lda     div_lo,x
        sta     tp
        lda     div_hi,x
        sta     tp+1
        lda     #1              ; 256 / n
        sta     qhi
        lda     #0
        sta     qlo
        jsr     div16
        sta     dm
        lda     qlo
        sta     dq
        lda     #0
        sta     dacc
        sta     drem
        tay
@r:     lda     dacc
        sta     (tp),y
        clc
        lda     drem
        adc     dm
        cmp     divisor
        bcc     @keep
        sbc     divisor         ; carry set: one more in the quotient
@keep:  sta     drem
        lda     dacc
        adc     dq
        sta     dacc
        iny
        cpy     divisor
        bcc     @r
        ldx     divisor
        inx
        cpx     #128
        bcc     @n
        rts

; ----------------------------------------------------------------------------
; divdz -- qhi:qlo = (qhi * 256) / divisor, for qlo = 0. When qhi < divisor
;          (the usual far sample) the high quotient byte is 0 and only eight
;          steps are needed. Clobbers A, X.
; ----------------------------------------------------------------------------
divdz:  lda     qhi
        cmp     divisor
        bcs     div16
        ldx     #0
        stx     qhi
        ldx     #8
@l:     asl     qlo             ; remainder < divisor <= 128: no carry out
        rol     a
        cmp     divisor
        bcc     @n
        sbc     divisor
        inc     qlo
@n:     dex
        bne     @l
        rts

; ----------------------------------------------------------------------------
; div16 -- qhi:qlo = qhi:qlo / divisor (unsigned), A = remainder.
;          divisor 1..128. Clobbers X.
; ----------------------------------------------------------------------------
div16:  lda     #0
        ldx     #16
@l:     asl     qlo
        rol     qhi
        rol     a
        cmp     divisor
        bcc     @n
        sbc     divisor
        inc     qlo
@n:     dex
        bne     @l
        rts

; ----------------------------------------------------------------------------
; status -- the text line under the view: position, heading, altitude
; ----------------------------------------------------------------------------
status:
        lda     #21
        sta     CV
        jsr     VTAB
        lda     #0
        sta     CH
        jsr     CLREOL
        lda     #<s_pos
        ldx     #>s_pos
        jsr     print_str_ax
        lda     px+1            ; x, y in map units (2 per cell)
        asl     a
        jsr     print_byte
        lda     #','|$80
        jsr     COUT
        lda     py+1
        asl     a
        jsr     print_byte
        lda     #<s_head
        ldx     #>s_head
        jsr     print_str_ax
        lda     heading         ; degrees = heading * 9 / 14
        sta     qlo
        lda     heading+1
        sta     qhi
        asl     qlo
        rol     qhi
        asl     qlo
        rol     qhi
        asl     qlo
        rol     qhi
        clc
        lda     qlo
        adc     heading
        sta     qlo
        lda     qhi
        adc     heading+1
        sta     qhi
        lda     #14
        sta     divisor
        jsr     div16
        lda     qlo
        sta     num
        lda     qhi
        sta     num+1
        jsr     print_u16
        lda     #<s_alt
        ldx     #>s_alt
        jsr     print_str_ax
        ldx     py+1            ; altitude / 100 = base + level
        lda     grid_lo,x
        sta     gp
        lda     grid_hi,x
        sta     gp+1
        ldy     px+1
        lda     (gp),y
        and     #$7F
        clc
        adc     M_BASE
        sta     num
        lda     #0
        sta     num+1
        jsr     print_u16
        lda     #<s_ft
        ldx     #>s_ft
        jmp     print_str_ax

print_byte:
        sta     num
        lda     #0
        sta     num+1
        ; fall through

; print_u16 -- num in decimal, no leading zeros
print_u16:
        ldy     #0              ; digits printed
        ldx     #8
@pow:   lda     #'0'
        sta     row
@sub:   lda     num
        cmp     pow10,x
        lda     num+1
        sbc     pow10+1,x
        bcc     @dig
        sta     num+1
        lda     num
        sbc     pow10,x
        sta     num
        inc     row
        bne     @sub
@dig:   lda     row
        cpx     #0
        beq     @out
        cpy     #0
        bne     @out
        cmp     #'0'
        beq     @skip
@out:   ora     #$80
        jsr     COUT
        iny
@skip:  dex
        dex
        bpl     @pow
        rts

.segment "RODATA"

pow10:  .word   1, 10, 100, 1000, 10000

turn_lo: .byte  <(-35), 35, <(-70), 70
turn_hi: .byte  >(-35), 0, >(-70), 0
turn_c0: .byte  0, 105, 0, 70           ; new columns col..c1-1
turn_c1: .byte  35, 140, 70, 140
turn_sh: .byte  10, 10, 20, 20          ; bytes scrolled

s_pos:  .byte   "POS ", 0
s_head: .byte   "  HDG ", 0
s_alt:  .byte   "  ALT ", 0
s_ft:   .byte   "00 FT", 0

grid_lo:
        .repeat GH, J
        .byte   <(GRID + J * GW)
        .endrep
grid_hi:
        .repeat GH, J
        .byte   >(GRID + J * GW)
        .endrep

        .include "hgr_scanline.inc"
        .include "tables.inc"   ; build/, from tools/gentables.py

; ----------------------------------------------------------------------------
; $1000-$1FFF (file WILDLO, BLOADed by HELLO)
; ----------------------------------------------------------------------------
.segment "LOWDATA"
                                ; screen rows (rowtab.inc, page-aligned):
        .include "rowtab.inc"   ; row_p0/p1[q]: tinc = q, row_n0/n1[q]: -q
twice:  .repeat 128, R          ; DIVTAB row of n = 128: r * 256 / 128
        .byte   R * 2
        .endrep

.segment "LOWCODE"
; span_rows: one 8-byte block per HGR row: lda row,y / ora fs / sta row,y
span_rows:
        .repeat VIEW_ROWS+1, R
        .if R < VIEW_ROWS
        lda     $2000 + (R .mod 8) * $400 + ((R / 8) .mod 8) * $80 + (R / 64) * $28, y
        ora     fs
        sta     $2000 + (R .mod 8) * $400 + ((R / 8) .mod 8) * $80 + (R / 64) * $28, y
        .else
        rts
        .endif
        .endrep
; clear_rows: zero byte column Y of rows 0..159 (A = 0)
clear_rows:
        .repeat VIEW_ROWS, R
        sta     $2000 + (R .mod 8) * $400 + ((R / 8) .mod 8) * $80 + (R / 64) * $28, y
        .endrep
        rts
span_lo:
        .repeat VIEW_ROWS+1, R
        .byte   <(span_rows + R * 8)
        .endrep
span_hi:
        .repeat VIEW_ROWS+1, R
        .byte   >(span_rows + R * 8)
        .endrep

.segment "CODE"
        .include "print.asm"
        .include "kbd.asm"
        .include "hgr.asm"
        .include "exit.asm"
