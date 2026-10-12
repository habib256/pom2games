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
; tests compare the two on many positions. The game itself (command line,
; simulation, screens) is game.s, included at the end, which calls
; view_full and view_turn.
; ============================================================================

        .include "apple2.inc"
        .include "zp.inc"
        .macpack longbranch

MAP      = $7000
GRID     = MAP + 64
GW       = 112                  ; grid cells west-east (1 cell = 2 units)
GH       = 84                   ; grid cells south-north
UNITS    = 560                  ; azimuth units per turn, 140 per quadrant
FOV_HALF = 70
STEPS    = 128                  ; ray steps (cells)
HORIZON  = 95
HUD_ROWS  = 16                  ; fixed compass ribbon above the terrain
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

; Render scratch only: the game logic's ROM floating point routines use
; $5E-$AC between two views, so nothing here survives a command. The
; position and heading live in game.s.
.segment "ZEROPAGE"
ang:     .res 2                 ; azimuth of the current column
dx:      .res 2                 ; ray step, signed 8.8
dy:      .res 2
rx:      .res 2                 ; ray position
ry:      .res 2
thr:     .res 2                 ; slope threshold, signed 8.8 levels
tinc:    .res 2                 ; threshold increment per step
qlo:     .res 1                 ; division dividend / quotient
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
        jsr     project_init
        jsr     hgr_init_clear
        lda     MIXSET
        lda     #20
        sta     WNDTOP
        jsr     HOME
        jmp     game_start

quit:   lda     #0
        sta     WNDTOP
        jmp     apple2_exit

; view_full -- draw the whole view from (px, py) toward heading
view_full:
        lda     #0
        sta     col
        lda     #140
        sta     c1
        jmp     render

; view_turn -- X = 0: -35, 1: +35, 2: -70, 3: +70 azimuth units (22.5 / 45
; deg). A column only depends on its absolute azimuth: 35 columns are 70
; pixels, exactly 10 bytes, so the view scrolls and only the new columns are
; drawn, like the original's PAN. With C set on entry only the heading moves
; (no view: night).
view_turn:
        php
        clc
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
        plp
        bcs     @rts
        jsr     scene_pan
        lda     turn_c0,x
        sta     col
        lda     turn_c1,x
        sta     c1
        lda     turn_sh,x
        sta     shift
        txa
        lsr     a               ; carry: turning right, the view moves left
        jsr     scroll
        jmp     render
@rts:   rts

; scroll -- move all terrain rows, using the hidden cache above the view by `shift` bytes: left when carry is set
;           (bytes shift..39 -> 0..39-shift), right otherwise.
scroll: php
        lda     #40
        sec
        sbc     shift
        sta     @count+1
        ; Visible terrain 16..159 and cached terrain 160..175 form one
        ; contiguous range of physical rows. No HUD remapping per row.
        ldx     #VIEW_ROWS+HUD_ROWS-1
@row:   lda     hgr_lo,x
        sta     hp
        lda     hgr_hi,x
        sta     hp+1
        lda     hp
        clc
        adc     shift
        sta     hp2
        lda     hp+1
        sta     hp2+1
        plp
        php
        bcc     @right
        ldy     #0
@l:     lda     (hp2),y
        sta     (hp),y
        iny
@count:
        cpy     #30
        bcc     @l
        bcs     @next
@right: lda     @count+1
        tay
        dey
@r:     lda     (hp),y
        sta     (hp2),y
        dey
        bpl     @r
@next:  dex
        cpx     #HUD_ROWS
        bcs     @row
        plp
        rts

; Local art has a fixed bearing and size: scrolling also moves its pixels.
; Keep its origin in sync for newly exposed columns, without disk/ROM work.
; X remains the turn kind. Wrap only behind the player (outside the view).
scene_pan:
        lda     scene_asset
        beq     @done
        sec
        lda     sprite_left
        sbc     turn_lo,x
        sta     sprite_left
        lda     sprite_left+1
        sbc     turn_hi,x
        sta     sprite_left+1
        bmi     @negative
        lda     sprite_left
        cmp     #<420
        lda     sprite_left+1
        sbc     #>420
        bcc     @done
        sec
        lda     sprite_left
        sbc     #<560
        sta     sprite_left
        lda     sprite_left+1
        sbc     #>560
        sta     sprite_left+1
        rts
@negative:
        lda     sprite_left
        cmp     #<(-140)
        lda     sprite_left+1
        sbc     #>(-140)
        bcs     @done
        clc
        lda     sprite_left
        adc     #<560
        sta     sprite_left
        lda     sprite_left+1
        adc     #>560
        sta     sprite_left+1
@done:  rts

; ----------------------------------------------------------------------------
; render -- draw the view below the fixed compass header
; ----------------------------------------------------------------------------
render:
        lda     weather_visibility
        cmp     #240
        bcc     :+
        lda     #0              ; clear weather retains the full ray budget
        beq     :++
:       lsr
        clc
        adc     #127            ; visibility units are half-cells
:       sta     render_weather_limit+1
        ldx     col             ; black out the bytes of columns col..c1-1:
        lda     col_be,x        ; ranges are multiples of 35 columns, i.e.
        sta     tmp             ; of 10 bytes
        lda     #40
        ldx     c1
        cpx     #140
        bcs     render_b1
        lda     col_be,x
render_b1:    sta     tmp2
render_clr:   jsr     clear_rows
        jsr     hud_draw
        lda     c1              ; only left turns end before column 140
        bmi     :+
                                ; start next to the retained view
        sec
        sbc     #1
        sta     col
:       ldx     py+1
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

render_column:
        jsr     forest_reset
        jsr     column_masks
        lda     view_dark
        beq     :+
        lda     #0
        sta     scene_opaque
        sta     scene_pending
        jmp     render_direction
:       jsr     sprite_column
render_direction:
        jsr     direction
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
        jsr     scene_trim
        lda     top
        bne     :+
        jmp     render_next
:       ; the ray follows its cell: Y = x cell, gp = row; a carry out of a
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
        beq     render_xpos
        bmi     render_xneg
        lda     #$24            ; dx = +256: BIT (move every step), INY
        ldx     #$C8
        bne     render_xset
render_xpos:  lda     #$90            ; 0 <= dx < 256: BCC, INY
        ldx     #$C8
        bne     render_xset
render_xneg:  lda     #$B0            ; dx < 0: BCS, DEY
        ldx     #$88
render_xset:  sta     render_xbr
        stx     render_xop
        lda     dy+1
        beq     render_ypos
        bmi     render_yneg
        lda     #$24            ; dy = +256
        bne     render_yup
render_ypos:  lda     #$90
render_yup:   sta     render_ybr
        lda     #GW
        sta     render_gpl+1
        lda     #0
        sta     render_gph+1
        lda     #GH-1
        sec
        sbc     py+1
        sta     rowsl
        jmp     render_back
render_yneg:  lda     #$B0
        sta     render_ybr
        lda     #<(-GW)
        sta     render_gpl+1
        lda     #>(-GW)
        sta     render_gph+1
        lda     py+1
        sta     rowsl
        jmp     render_back
render_sky_j: jmp     render_sky
render_step_j: jmp    render_back
render_ovf:   lda     tinc+1          ; overflow: rising past +127 levels ends
        bpl     render_sky_j          ; the column, falling past -128 clamps
        lda     #0
        sta     thr
        lda     #$80
        bne     render_thr

render_back:  ldy     cx              ; Y = x cell again
render_stepc: clc                     ; render_step expects carry clear
render_step:
        inc     n
        beq     render_sky_j
        lda     n
render_weather_limit:
        cmp     #0
        beq     render_sky_j
        lda     scene_pending
        beq     :+
        jsr     scene_activate
:       lda     scene_opaque
        beq     :+
        ldx     n
        lda     scene_ceiling-128,x
        cmp     top
        bcs     render_sky_j
:       clc
        lda     rx
        adc     dx
        sta     rx
render_xbr:   bcc     render_xk             ; patched: BCC / BCS / BIT
render_xop:   iny                     ; patched: INY / DEY
        cpy     #GW
        bcs     render_sky_j
render_xk:    clc
        lda     ry
        adc     dy
        sta     ry
render_ybr:   bcc     render_yk
        dec     rowsl
        bmi     render_sky_j
        clc
        lda     gp
render_gpl:   adc     #GW             ; patched: +-112
        sta     gp
        lda     gp+1
render_gph:   adc     #0
        sta     gp+1
render_yk:    clc
        lda     (gp),y
        and     #$7F
        adc     eyeb            ; levels <= 125: dz + 128 stays in 1..253
        sta     dzb
render_forest_call:
        jsr     forest_probe    ; reset per ray; becomes BIT after the last candidate
        lda     thr             ; thr += tinc (no carry out of the add above)
        adc     tinc
        sta     thr
        lda     thr+1
        adc     tinc+1
        bvs     render_ovf
render_thr:   sta     thr+1
        eor     #$80            ; visible when dz > floor(thr), i.e.
        cmp     dzb             ; dz + 128 > (thr >> 8) + 128, unsigned
        bcs     render_stepc
        sty     cx

        ; visible: tinc = trunc(dz * 256 / n), thr = dz * 256, then the row
        lda     n
        sec
        sbc     #127
        sta     divisor
        lda     #0
        sta     thr
        lda     dzb
        eor     #$80
        sta     thr+1
        bmi     render_neg
        cmp     divisor         ; dz >= 0
        bcs     render_pbig
        jsr     smalldiv        ; q = dz * 256 / n < 256
        sta     tinc
        tax
        lda     #0
        sta     tinc+1
        lda     row_p0,x
        jmp     render_drawchk
render_pbig:  jsr     bigdiv          ; dz >= n: q >= 256
        sta     tinc
        lda     qhi
        sta     tinc+1
        cmp     #2
        bcs     render_prow0          ; q >= 512: top row
        ldx     tinc
        lda     row_p0,x
        sec
        sbc     #48
        jmp     render_drawchk
render_prow0: lda     #0
        jmp     render_drawchk
render_neg:   lda     #128            ; dz < 0: |dz| = 128 - (dz + 128)
        sec
        sbc     dzb
        cmp     divisor
        bcs     render_nbig
        jsr     smalldiv        ; q < 256
        tax
        eor     #$FF            ; tinc = -q
        clc
        adc     #1
        sta     tinc
        lda     #$FF
        adc     #0
        sta     tinc+1
        lda     row_n0,x
        jmp     render_drawchk
render_nbig:  jsr     bigdiv          ; |dz| >= n: q >= 256
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
        bcs     render_hide           ; q >= 512: below the view
        ldx     qlo
        cpx     #86
        bcs     render_hide           ; truncated row_n1's former $FF suffix
        lda     row_n0,x
        clc
        adc     #48        ; $FF below the bottom row
render_drawchk:
        cmp     top
        bcc     render_shown
render_hide:  jmp     render_back          ; hidden behind nearer ground (or $FF)
render_shown: sta     row
        tay
        iny                     ; colour rows row+1..top-1, often none
        cpy     top
        bcs     render_ridge
        lda     top
        sta     sp_end
        sty     tmp2
        ldy     cx
        lda     (gp),y
        ldx     #C_WATER
        asl     a               ; bit 7: water
        bcs     render_col
        ldx     #C_SNOW
        lsr     a
        cmp     M_SNOW
        bcs     render_col
        ldx     #C_GROUND
render_col:   ldy     tmp2
        txa
        ldx     view_dark
        beq     :+
        lda     #C_RIDGE
:       jsr     scene_span
render_ridge: lda     row             ; the ridge row stays black: the view was
        sta     top             ; opaque sprite pixels keep their colour
        jsr     scene_trim
        lda     top
        beq     render_next
        jmp     render_step_j

render_sky:   jsr     scene_force
        lda     top
        sta     sp_end
        ldy     #0
        lda     #C_SKY
        ldx     night
        beq     :+
        lda     #C_RIDGE
:       jsr     scene_span
        jsr     sky_column
render_next:
        jsr     forest_paint
        lda     c1
        bpl     render_prev
        inc     ang
        bne     render_wrap
        inc     ang+1
render_wrap:  jsr     wrap_ang
        inc     col
        lda     col
        cmp     c1
        bcs     render_done
render_more:
        jmp     render_column
render_prev:
        jsr     render_prev_ang
        dec     col
        bpl     render_more
render_done:  jmp     hud_draw

ray_step = render_step
render_column_done = render_next
.export ray_step, render_column_done

column_masks:
        ldx     col
        lda     col_be,x
        sta     be
        sta     bo
        lda     col_me,x
        sta     me
        cmp     #$BF            ; even pixel at bit 6: odd wraps to next byte
        bne     :+
        inc     bo
        lda     #$FE
        bne     @odd
:       asl
        ora     #1              ; keep the phase bit and vacated bit zero set
@odd:
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
        rts

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
@header:
        cpy     #HUD_ROWS
        bcs     @body
        cpy     sp_end
        bcs     @done
        sty     qhi
        tya
        tax
        jsr     view_row
        ldy     tmp
        lda     (hp),y
        ora     fs
        sta     (hp),y
        ; The full header belongs to compass and survival panels.
        ldy     qhi
        iny
        jmp     @header
@body:  ldx     sp_end
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
@done:  rts
@go:    jmp     (fj)

; ----------------------------------------------------------------------------
; direction -- dx, dy = the 8.8 unit step of azimuth ang (0..559)
;   quadrant 0: (s, c)  1: (c, -s)  2: (-s, -c)  3: (-c, s)
;   s = sin(i * 90 / 140), c = sin((140 - i) * 90 / 140), i = ang mod 140
;   Rounded samples from SIN_UNIT_START onward equal 256: derive the high
;   byte from carry instead of storing another 141-byte table.
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
        cpx     #SIN_UNIT_START
        lda     #0
        adc     #0
        sta     dx+1
        txa
        eor     #$FF
        sec
        adc     #140            ; 140 - i
        tax
        lda     sin_lo,x
        sta     dy
        cpx     #SIN_UNIT_START
        lda     #0
        adc     #0
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

.segment "GCODE"
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
.segment "LOWCODE"
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
.segment "CODE"
; bigdiv -- A = |dz| >= n = divisor: qhi:qlo = |dz| * 256 / n, returns A = qlo
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
        jsr     smalldiv        ; remainder r < n: low byte r * 256 / n
        sta     qlo
        rts

; smalldiv -- A = r < n = divisor (n <= 128): A = r * 256 / n. Clobbers qlo.
smalldiv:
        cmp     #0
        bne     :+
        sta     qlo
        rts
:       .repeat 8
        asl     a               ; remainder < n <= 128: no carry out
        cmp     divisor
        bcc     :+
        sbc     divisor
:       rol     qlo
        .endrep
        lda     qlo
        rts

.segment "LOWCODE"
print_byte:
        sta     num
        lda     #0
        sta     num+1
        ; fall through

; print_u16 -- num in decimal, no leading zeros
.segment "GCODE"
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

; Left turn: decrement the signed azimuth, including the 0 -> 559 wrap.
render_prev_ang:
        lda     ang
        bne     :+
        dec     ang+1
:       dec     ang
        jmp     wrap_ang

.segment "TEXT"

pow10:  .word   1, 10, 100, 1000, 10000

turn_lo: .byte  <(-35), 35, <(-70), 70
turn_hi: .byte  >(-35), 0, >(-70), 0
turn_c0: .byte  0, 105, 0, 70           ; new columns col..c1-1
turn_c1: .byte  35, 140, 70, 140
turn_sh: .byte  10, 10, 20, 20          ; bytes scrolled


.segment "RODATA"
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
        .include "rowtab.inc"   ; q < 256 projection; q+256 differs by exactly 48 rows

.segment "LOWCODE"
; Rebuild the negative projection cache once, rather than transfer it.
; ceil(3*q/16) = floor(3*q/16) + (q mod 16 != 0).
.segment "LOWCACHE"
row_n0: .res 256
.segment "LOWCODE"
project_init:
        ldx     #0
@row:   txa
        and     #15
        cmp     #1
        lda     row_p0,x
        eor     #255
        adc     #191            ; modulo 256: 190 - row_p0 + fractional carry
        sta     row_n0,x
        inx
        bne     @row
        rts

; span_rows: one 8-byte block per HGR row: lda row,y / ora fs / sta row,y
span_rows:
        .repeat VIEW_ROWS-HUD_ROWS+1, I
        .if I+HUD_ROWS < VIEW_ROWS
        lda     $2000 + ((I+HUD_ROWS) .mod 8) * $400 + (((I+HUD_ROWS) / 8) .mod 8) * $80 + ((I+HUD_ROWS) / 64) * $28, y
        ora     fs
        sta     $2000 + ((I+HUD_ROWS) .mod 8) * $400 + (((I+HUD_ROWS) / 8) .mod 8) * $80 + ((I+HUD_ROWS) / 64) * $28, y
        .else
        rts
        .endif
        .endrep
; clear_rows: clear byte columns [tmp,tmp2); keep the visible HUD and holes.
clear_rows:
        ; Rows 160..175 cache logical 0..15 underneath the compass.
        ; Visit each physical row once, then clear its contiguous byte range.
        ; Row pointers need not be fetched again for every byte column.
        ldx     #VIEW_ROWS+HUD_ROWS-1
@row:   lda     hgr_lo,x
        sta     hp
        lda     hgr_hi,x
        sta     hp+1
        ldy     tmp
        lda     #0
@byte:  sta     (hp),y
        iny
        cpy     tmp2
        bcc     @byte
        dex
        cpx     #HUD_ROWS
        bcs     @row
        rts
; fill's header loop handles rows below HUD_ROWS before either lookup.
; Omit the sixteen duplicate pointers from each table without extra indexing.
span_lo = *-HUD_ROWS
        .repeat VIEW_ROWS-HUD_ROWS+1, R
        .byte   <(span_rows + R * 8)
        .endrep
span_hi = *-HUD_ROWS
        .repeat VIEW_ROWS-HUD_ROWS+1, R
        .byte   >(span_rows + R * 8)
        .endrep

.segment "CODE"
        .include "game.s"
        .include "overlay_codec.s"
        .include "input.s"
        .include "sprites.s"
        .include "hud.s"
        .include "print.asm"
        .include "kbd.asm"
        .include "hgr.asm"
        .include "exit.asm"
        .include "dos.asm"

        .include "sky.s"

        .include "clock.inc"
        .include "status.s"
        .include "summary.s"

        .include "ui_monitor.s"

        .include "forest.s"
        .include "forest_profiles.inc"

        .include "adventure.s"
        .include "outdoor.s"
        .include "water.s"
        .include "geography.s"
