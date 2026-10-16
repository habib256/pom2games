; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; wild.s -- Wilderness reimplementation: first-person terrain view
; ============================================================================
; The view engine of Electric Transit's Wilderness (1985), rebuilt from the
; analysis in docs/ANALYSE.md: a ray per screen column over a height map,
; occlusion by the steepest slope seen so far, striped ridges. The map is
; the MAP file (tools/mkmap.py) preloaded at $7000 by NEOWILD.SYSTEM.
;
; tools/view_ref.py is the bit-exact Python reference of render below; the
; tests compare the two on many positions. The game itself (command line,
; simulation, screens) is game.s, included at the end, which calls
; view_full and view_turn.
; ============================================================================

        .include "apple2.inc"
        .include "ui_choice.inc"
        .include "mousetext.inc" ; docs/MENUS.md 9: the glyphs of the text pages
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

WNDTOP   = $22
CLREOL   = t_clreol             ; own text primitives (dhgr.s)

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
hp:      .res 2                 ; screen row pointer
sp_end:  .res 1                 ; span end row (exclusive)
be:      .res 1                 ; HUD: first source byte
row0:    .res 1                 ; HUD: ribbon row
eyeb:    .res 1                 ; 128 - eye: level + eyeb = dz + 128
dzb:     .res 1                 ; dz + 128 of the sample
c1:      .res 1                 ; render columns col..c1-1
hp2:     .res 2                 ; scroll: the other row pointer
shift:   .res 1                 ; scroll: bytes

cx:      .res 1                 ; x cell of the ray (Y in the step loop)
rowsl:   .res 1                 ; row changes left before the ray leaves the map
num:     .res 2                 ; print_u16 value

STARS_HOOK = 1                  ; dhgr.s sky_position marks the star list stale
DROWS_LC = 1                    ; dhgr.s: the unrolled rows run in bank 2 of
                                ; the main language card (docs/MEMORY.md 12)
B2_LC = 1                       ; dhgr.s B2_ENTRY: five routines run in
                                ; $D100-$D3FF of that bank (docs/MEMORY.md 15)
        .include "dhgr.s"

.segment "CODE"

; NEOWILD.SYSTEM has saved ProDOS's zero page, RESET vector and bitmap,
; claimed the auxiliary memory and preloaded every image; its `start`
; (src/boot.s: stack, mem_ready, native video switches; start-only code
; kept out of the resident images, docs/MEMORY.md 15) jumps to game_start.
.export game_start

.segment "LOWCODE"
; quit -- end of a game (QUIT, death, arrival): back to the start menu by
; running NEOWILD.SYSTEM again (module_restart, INPUT). Ctrl-RESET still
; leaves to ProDOS (reset_exit).
quit:   lda     #0
        sta     WNDTOP
        lda     #13
        jsr     overlay_load
        jmp     module_end      ; INPUT: NEOWILD.END (score, hall of fame)

; view_full -- draw the whole view from (px, py) toward heading
.segment "TEXT"
view_full:
        lda     #0
        sta     col
        lda     #140
        sta     c1
        jmp     render

.segment "CODE"
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

; scroll -- move the terrain rows 16..175 (visible view and hidden cache) of
;           both banks by `shift` bytes: left when carry is set (bytes
;           shift..39 -> 0..39-shift), right otherwise. 35 columns = 5 groups
;           = 10 bytes per bank.
        B2_ENTRY scroll, b2_scroll
        lda     #0
        rol     a               ; 1: left
        tay
        php
        sei
        lda     #40
        sec
        sbc     shift
        tax                     ; bytes moved per row and bank
        cpy     #0
        beq     @right
        stx     band_stop+1     ; left: bytes shift..39 -> 0..39-shift,
        lda     shift           ; source = row + shift, X = 0 up to n
        sta     band_sadd
        lda     #0
        sta     band_dadd
        sta     scroll_x
        lda     #$E8            ; INX
        bne     @set
@right: dex                     ; right: bytes 0..39-shift -> shift..39,
        stx     scroll_x        ; destination = row + shift, X = n-1 down
        lda     #$FF
        sta     band_stop+1
        lda     #0
        sta     band_sadd
        lda     shift
        sta     band_dadd
        lda     #$CA            ; DEX
@set:   sta     band_step
        ; Visible terrain 16..159 and cached terrain 160..175: bands 2..21
        ; of eight rows; the same addresses serve both banks.
        ldx     #HUD_ROWS/8
@band:  jsr     band_base
        lda     band_lo
        clc
        adc     band_sadd
        sta     band_slo
        lda     band_lo
        clc
        adc     band_dadd       ; no carry: low bytes stay below $E5
        sta     band_dlo
        ldy     #7*6            ; patch the eight rows, last first
        lda     band_hi
        clc
        adc     #7*4
        tax
@patch: lda     band_slo
        sta     band_copy+1,y
        lda     band_dlo
        sta     band_copy+4,y
        txa
        sta     band_copy+2,y
        sta     band_copy+5,y
        sbc     #3              ; carry clear: -4
        tax
        tya
        sec
        sbc     #6
        tay
        clc
        bpl     @patch
        sta     PAGE2_AUX
        ldx     scroll_x
        jsr     band_copy
        sta     PAGE2_MAIN
        ldx     scroll_x
        jsr     band_copy
        ldx     band_index
        inx
        cpx     #(VIEW_ROWS+HUD_ROWS)/8
        bne     @band
        plp
        rts
        B2_END
; Eight rows of one band and bank: one byte column per loop.
band_copy:
.repeat 8
        lda     $2000,x         ; patched: source row
        sta     $2000,x         ; patched: destination row
.endrep
band_step:
        inx                     ; patched: INX / DEX
band_stop:
        cpx     #30             ; patched: n / $FF
        bne     band_copy
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
        php
        sei                     ; aux passes: no interrupt handler sees aux
        jsr     render_frame
        plp
        rts
render_frame:
        jsr     stars_dhgr_frame        ; dhgr_frame, then stars_frame
        lda     weather_visibility
        cmp     #240
        bcc     :+
        lda     #0              ; clear weather retains the full ray budget
        beq     :++
:       lsr
        clc
        adc     #127            ; visibility units are half-cells
:       sta     render_weather_limit+1
        lda     col             ; black out the bytes of columns col..c1-1:
        jsr     div7            ; ranges are multiples of 35 columns, i.e.
        txa                     ; of 5 groups, 10 bytes per bank
        asl     a
        sta     tmp
        lda     #40
        ldx     c1
        cpx     #140
        bcs     render_b1
        txa
        jsr     div7
        txa
        asl     a
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
        jsr     grid_row
        sta     gp
        sty     gp+1
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
        jsr     column_setup
        lda     draw_dark
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
        jsr     grid_row
        sta     gp
        sty     gp+1
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
        bcs     render_nhide          ; q >= 512: below the view
        ldx     qlo
        cpx     #86
        bcs     render_nhide          ; truncated row_n1's former $FF suffix
        lda     row_n0,x
        clc
        adc     #48                   ; <= 191: no carry
        bcc     render_drawchk
render_nhide: lda     #$FF            ; below the view at level
render_drawchk:
        ; BIT at level; JSR when the view is tilted (tilt_apply): tilt_row
        ; recomputes A from the slope tinc, every path sets it.
render_tilt:  bit     tilt_row
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
        ldx     #PAL_WATER
        asl     a               ; bit 7: water
        bcs     render_col
        ldx     #PAL_SNOW
        lsr     a
        cmp     M_SNOW
        bcs     render_col
        ldx     #PAL_GROUND
render_col:   lda     n               ; distance tier: near, mid, far
        cmp     #TIER1_N
        bcc     :+
        inx
        cmp     #TIER2_N
        bcc     :+
        inx
:       lda     cur_pal,x
        ldy     tmp2
        jsr     scene_span
render_ridge: lda     row             ; the ridge row stays black: the view was
        sta     top             ; opaque sprite pixels keep their colour
        jsr     scene_trim
        lda     top
        beq     render_next
        jmp     render_step_j

render_sky:   jsr     scene_force
        ldx     #0              ; five mood zones, clipped to the terrain
        ldy     #0
render_zone:
        stx     dzone
        lda     sky_zone_end,x
        cmp     top
        bcc     :+
        lda     top
:       sta     sp_end
        lda     cur_zone,x
        jsr     scene_span
        ldy     sp_end
        ldx     dzone
        inx
        cpy     top
        bcc     render_zone
        jsr     stars_sky_column        ; stars_column, then sky_column
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
render_done:  rts                     ; the HUD was drawn before the columns

ray_step = render_step
render_column_done = render_next
.export ray_step, render_column_done

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
turn_sh: .byte  10, 10, 20, 20          ; bytes scrolled in each bank


.segment "RODATA"
; grid_row -- X = row, A/Y = its little-endian pointer. X is kept.
; Fixed-cost 128*X - 16*X replaces 168 resident table bytes.
grid_row:
        txa
        asl     a
        asl     a
        asl     a
        asl     a
        sta     @sublo+1
        txa
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        sta     @subhi+1
        txa
        lsr     a
        tay
        lda     #0
        ror     a
        clc
        adc     #<GRID
        sta     @lo+1
        tya
        adc     #>GRID
        sta     @hi+1
@lo:    lda     #0
        sec
@sublo: sbc     #0
        pha
@hi:    lda     #0
@subhi: sbc     #0
        tay
        pla
        rts

        .include "tables.inc"   ; build/, from tools/gentables.py

; ----------------------------------------------------------------------------
; $1000-$1FFF (file WILDLO, preloaded by NEOWILD.SYSTEM)
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

; ----------------------------------------------------------------------------
; LOOK UP / LOOK DOWN (docs/LOOK_UPDOWN.md). A tilt of the view moves every
; projected row by 96 * tilt rows: 96 rows are exactly 512 slope units
; (3 * 512 / 16), so a tilted sample is the level projection of the slope
; q' = tinc - 512 * tilt. Occlusion stays in slope space: thr, tinc and the
; hidden samples do not depend on the tilt.
; tilt_apply -- the tilt changed since the last frame (stars_dhgr_frame):
; constants and sky zones (dhgr.s tilt_frame), then the projection hook.
tilt_apply:
        lda     z:tilt
        sta     tilt_shown
        tax
        inx
        jsr     tilt_frame
        lda     #$2C            ; BIT abs: level
        ldx     z:tilt
        beq     :+
        lda     #$20            ; JSR tilt_row
:       sta     render_tilt
        rts

; tilt_row -- render_drawchk of a tilted view: A = row of the sample of
; slope tinc (signed 8.8): 95 - floor(3 q' / 16), 0 above the view, $FF
; (or any row >= 160) below it (tools/view_ref.py sample_row). Clobbers X, Y.
tilt_row:
        lda     tinc+1
        sec
        sbc     tilt2           ; high byte of q' = tinc - 512 * tilt
        bvs     @ovf
        bmi     @neg
        tay                     ; q' >= 0: row_p0[lo] - 48 * hi, at least 0
        ldx     tinc
        lda     row_p0,x
        cpy     #0
        beq     @rts
@sub:   sec
        sbc     #48
        bcc     @top
        dey
        bne     @sub
@rts:   rts
@top:   lda     #0
        rts
@neg:   eor     #$FF            ; q' < 0: |q'| = (~hi + (lo = 0)) : -lo
        tay
        lda     tinc
        eor     #$FF
        clc
        adc     #1
        tax
        bcc     :+
        iny
:       lda     row_n0,x        ; row_n0[lo] + 48 * hi, hidden past 255
        cpy     #0
        beq     @rts
@add:   clc
        adc     #48
        bcs     @hide
        dey
        bne     @add
        rts
@hide:  lda     #$FF
        rts
@ovf:   lda     tinc+1          ; |q'| > 32767: far above or below the view
        bmi     @hide
        bpl     @top
.segment "LOWTEXT"
tilt_shown: .byte 0             ; tilt of the constants and the hook
.segment "LOWCODE"

.segment "CODE"
        .include "game.s"
        .include "input.s"
        .include "menu.s"
        .include "sprites.s"
        .include "hud.s"
        .include "print.asm"
        .include "transitions.s"
        .define wait_key keyboard_wait
        .include "ui_event.s"
        .undefine wait_key
        .include "hgr.asm"
        .include "memory.s"

        .include "sky.s"
; Night stars (lot 7 step 5, docs/STARS.md): the list and the drawing code
; are in the main language card (SKYRES, $DE00; the code runs in place, the
; module write-enables the bank to store the list), the hourly computation
; is module 25 (SKYSTARS, run in the SIM window $9600 with its catalogue).
STARS_CODE_LC = 1
STARS_LIST_LC = 1
        .include "stars_draw.s"
        .include "stars.s"

        .include "clock.inc"
        .include "status.s"
        .include "summary.s"

        .include "ui_monitor.s"

        .include "forest.s"
        .include "forest_profiles.inc"

        .include "adventure.s"
        .include "outdoor.s"
        .include "water.s"
        .include "alerts.s"     ; lot 13: alerts, forced sleep, diseases (WILDLO)
        .include "camp.s"
        .include "fire.s"       ; the animated campfire; segment FIRE: build/wildfire.bin ($9600)
        .include "textbank.inc" ; build/: texts fetched at print time (TBANK, docs/MEMORY.md 13)
        .include "geography.s"
        .include "geoaux.s"
        .include "hof.s"        ; segment HOF: build/wildhof.bin ($9600)
        .include "prepare.s"    ; segment PREPARE: build/wildpre.bin, NEOWILD.PRE ($2000)
        .include "save.s"       ; SAVE/RESTORE; segment SAVEMOD: build/wildsav.bin ($9600)
        .include "forage.s"     ; lot 4: hunting, fishing, gathering, meals (resident)
        .include "frg.s"        ; lot 4: segment FORAGE: build/wildfrg.bin ($9600, NEOWILD.BLK)
        .include "grid.s"       ; segment GRID: build/wildgrid.bin ($A300, the grid's lists and queue)
        .include "craft.s"      ; lot 3: segment CRAFT: build/wildcrf.bin ($9600, NEOWILD.BLK)

