; ============================================================================
; render.inc -- one frame on the hidden HGR page: ground, bike, HUD
; ============================================================================
; Pixel scrolling. The camera is at world pixel camx; screen byte column c
; shows the 7 world pixels x = camx + 7c .. x + 6, a "window" whose pattern
; the track compiler worked out (tools/track.py, loaded by loader.inc):
; track_ids[x] picks it; it gives the partial rows k, their bytes in the
; pool, and rel0, the row of pixel x inside it, so the highest ground row is
; mn = track_h[x] - rel0. Rows from mn + k down are solid. Drawing a column
; is a few table reads, whatever the scroll offset.
;
; Each page remembers the mn/mx it shows (st_mn/st_mx), so the rows to
; rewrite are min(mn, old mn) .. max(mx, old mx): one row or none on the
; flat, the partial rows on bumps, nothing at all when the camera has not
; moved since this page was drawn. The bike is drawn last with OR; the rows
; it covered on this page (bk_top/bk_bot) get their sky back on the next
; visit, before it is drawn again (rows in the white ground need nothing).
;
; Page flipping patches the high-byte table of every row access
; (HGR_HI_SITE, lib/hgr/hgr_pages: these four and hgr_line8's three)
; instead of rewriting a table each frame; hgr_text8 follows ht_page.
; Caller provides track, hgr_lo/hgr_hi (page 1) and pidx = 0 / 1.
; ============================================================================

CAM_LEAD = 100                  ; rear wheel this far from the left edge
CAM_MAX  = TRACK_LEN - 280 - 7  ; windows stay inside the track
POOL_MAX = 1024                 ; = tools/packtrack.py
COL_PART = 16                   ; partial rows kept per world column
SBUF     = 64                   ; rows of one combined screen column
                                ; (tools/track.py checks both limits)

.segment "ZEROPAGE"
camx:   .res 2                  ; world pixel of the left edge
camc:   .res 2                  ; = camx div 7
cams:   .res 1                  ; = camx mod 7
hptr:   .res 2                  ; track_h + camx + 7 * column
iptr:   .res 2                  ; track_ids + camx + 7 * column
pidx:   .res 1                  ; page being drawn: 0 = page 1, 1 = page 2
same:   .res 1                  ; non-zero: camera unchanged for this page
rptr:   .res 2                  ; scanline + column
sptr:   .res 2                  ; sprite data
mn:     .res 1
mx:     .res 1
rlo:    .res 1
rend1:  .res 1
rend2:  .res 1
rend3:  .res 1
col:    .res 1
sti:    .res 1                  ; st_* index: pidx * 40 + col
spx:    .res 4                  ; points on screen (+ the head for marks)
spy:    .res 4
hdx:    .res 1                  ; rider torso step, (dy/8, -dx/8)
hdy:    .res 1
sprx:   .res 1
spry:   .res 1
sprh:   .res 1
sprw:   .res 1
bx0:    .res 1
bx1:    .res 1
by0:    .res 1
by1:    .res 1
hl_ln_x0: .res 1                ; hgr_line8 (lib/hgr/hgr_line.asm)
hl_ln_y0: .res 1
hl_ln_x1: .res 1
hl_ln_y1: .res 1
hl_ln_dx: .res 1
hl_ln_dy: .res 1
hl_ln_sx: .res 1
hl_ln_err: .res 1
hl_pix_mask: .res 1
hl_pix_addr_lo = rptr             ; its row pointer
hl_pix_addr_hi = rptr + 1
fbase:  .res 2                  ; row writer of the draw page
fend:   .res 2
fsave:  .res 1

.segment "LOWBSS"
pat_k:    .res 256              ; the loaded track's patterns: partial rows,
pat_rel0: .res 256              ; row of the window's first pixel,
pat_plo:  .res 256              ; address of the partial bytes (pool + offset)
pat_phi:  .res 256
.segment "TXT0"
st_mn:  .res 80                 ; per page and column: mn / mx shown
.segment "TXT1"
st_mx:  .res 80
.segment "LOWBSS"
pg_camx: .res 4                 ; per page: camx it shows (lo, hi)
bb_c0:  .res 2                  ; per page: columns the bike covers,
bb_c1:  .res 2
bb_top: .res 2                  ; and its highest row
.segment "TXT2"
bk_top: .res 80                 ; per page and column: rows the bike covers
.segment "TXT3"
bk_bot: .res 80

.segment "LOWBSS"
hgr_hi2: .res 192               ; page 2 row high bytes
div7:   .res 264                ; x div 7 and x mod 7, x = 0..263
mod7:   .res 264
fill1:  .res 192 * 3 + 1        ; row writers: STA row,Y for rows 0..191, RTS
fill2:  .res 192 * 3 + 1        ; (page 1, page 2)
m3lo:   .res 193                ; 3 * row: offset of a row in a writer
m3hi:   .res 193

.segment "BSS"
pool:   .res POOL_MAX           ; partial bytes of the loaded track's patterns

.segment "CODE"

; ---------------------------------------------------------------------------
; render_init -- once: page-2 row table, row writers, 3 * row, div7 / mod7
; ---------------------------------------------------------------------------
render_init:
        JSR     hgr_pages_init
        LDA     #<fill1                 ; row writers: $99 lo hi per row
        STA     rptr
        LDA     #>fill1
        STA     rptr+1
        LDA     #<fill2
        STA     sptr
        LDA     #>fill2
        STA     sptr+1
        LDX     #0
@wr:    LDY     #0
        LDA     #$99                    ; STA abs,Y
        STA     (rptr),Y
        STA     (sptr),Y
        INY
        LDA     hgr_lo,X
        STA     (rptr),Y
        STA     (sptr),Y
        INY
        LDA     hgr_hi,X
        STA     (rptr),Y
        CLC
        ADC     #$20
        STA     (sptr),Y
        CLC
        LDA     rptr
        ADC     #3
        STA     rptr
        BCC     @w1
        INC     rptr+1
@w1:    CLC
        LDA     sptr
        ADC     #3
        STA     sptr
        BCC     @w2
        INC     sptr+1
@w2:    INX
        CPX     #192
        BNE     @wr
        LDY     #0
        LDA     #$60                    ; RTS after the last row
        STA     (rptr),Y
        STA     (sptr),Y
        LDX     #0                      ; m3 = 3 * row, rows 0..192
        STX     rend1
        STX     rend2
@m3:    LDA     rend1
        STA     m3lo,X
        LDA     rend2
        STA     m3hi,X
        CLC
        LDA     rend1
        ADC     #3
        STA     rend1
        BCC     @m4
        INC     rend2
@m4:    INX
        CPX     #193
        BNE     @m3
        LDX     #0                      ; div7 / mod7, x = 0..263
        LDY     #0
        STY     rend1
@d7:    LDA     rend1
        STA     div7,X
        TYA
        STA     mod7,X
        INY
        CPY     #7
        BNE     @d7n
        LDY     #0
        INC     rend1
@d7n:   INX
        BNE     @d7
@d7b:   LDA     rend1                   ; 256..263
        STA     div7+256,X
        TYA
        STA     mod7+256,X
        INY
        CPY     #7
        BNE     @d7m
        LDY     #0
        INC     rend1
@d7m:   INX
        CPX     #8
        BNE     @d7b
        RTS

; ---------------------------------------------------------------------------
; render_reset -- both pages unknown: the next frames repaint every row;
; camera back to the start of the track
; ---------------------------------------------------------------------------
render_reset:
        LDX     #79
@st:    LDA     #0
        STA     st_mn,X
        LDA     #191
        STA     st_mx,X
        LDA     #$FF
        STA     bk_top,X
        LDA     #0
        STA     bk_bot,X
        DEX
        BPL     @st
        LDA     #$FF                    ; pages show no known camera
        STA     pg_camx+1
        STA     pg_camx+3
        LDA     #1                      ; no bike marks
        STA     bb_c0
        STA     bb_c0+1
        LDA     #0
        STA     bb_c1
        STA     bb_c1+1
        STA     camx
        STA     camx+1
        STA     camc
        STA     camc+1
        STA     cams
        RTS

; ---------------------------------------------------------------------------
; render_begin -- pidx is the page to draw: point every row access at its
; table, and hgr_text8 at its page
; ---------------------------------------------------------------------------
render_begin:
        LDA     #<fill1
        STA     fbase
        LDA     #>fill1
        STA     fbase+1
        LDA     #0
        STA     ht_page
        LDA     pidx
        JSR     hgr_select_page         ; every HGR_HI_SITE (and hgr_line8)
        LDA     pidx
        BEQ     @p1
        LDA     #<fill2
        STA     fbase
        LDA     #>fill2
        STA     fbase+1
        LDA     #$60
        STA     ht_page
@p1:    RTS

; ---------------------------------------------------------------------------
; camera -- camx = clamp(rear wheel - CAM_LEAD, 0, CAM_MAX), stepped one
; pixel at a time (camc/cams follow)
; ---------------------------------------------------------------------------
camera:
        SEC                             ; w = rear - CAM_LEAD, clamped
        LDA     pt_xl
        SBC     #CAM_LEAD
        STA     w0
        LDA     pt_xh
        SBC     #0
        STA     w1
        BCS     @pos
        LDA     #0
        STA     w0
        STA     w1
@pos:   LDA     w0
        CMP     #<(CAM_MAX+1)
        LDA     w1
        SBC     #>(CAM_MAX+1)
        BCC     @fwd
        LDA     #<CAM_MAX
        STA     w0
        LDA     #>CAM_MAX
        STA     w1
@fwd:   LDA     camx                    ; forward while camx < w
        CMP     w0
        LDA     camx+1
        SBC     w1
        BCS     @back
        INC     camx
        BNE     @f1
        INC     camx+1
@f1:    INC     cams
        LDA     cams
        CMP     #7
        BNE     @fwd
        LDA     #0
        STA     cams
        INC     camc
        BNE     @fwd
        INC     camc+1
        BNE     @fwd
@back:  LDA     w0                      ; back while camx > w
        CMP     camx
        LDA     w1
        SBC     camx+1
        BCS     @ring
        LDA     camx
        BNE     @b1
        DEC     camx+1
@b1:    DEC     camx
        DEC     cams
        BPL     @back
        LDA     #6
        STA     cams
        LDA     camc
        BNE     @b2
        DEC     camc+1
@b2:    DEC     camc
        JMP     @back
@ring:  RTS

; ---------------------------------------------------------------------------
; render_ground -- every column of the draw page
; ---------------------------------------------------------------------------
render_ground:
        LDX     pidx                    ; old bike box over the HUD rows?
        LDA     bb_c1,X
        CMP     bb_c0,X
        BCC     rg_hudok
        LDA     bb_top,X
        CMP     #8
        BCS     rg_hudok
        JSR     hud_forget
rg_hudok: LDA     pidx                    ; same camera as this page shows?
        ASL     A
        TAX
        LDY     #0
        LDA     camx
        CMP     pg_camx,X
        BNE     rg_moved
        LDA     camx+1
        CMP     pg_camx+1,X
        BNE     rg_moved
        INY
rg_moved: STY     same
        LDA     camx
        STA     pg_camx,X
        LDA     camx+1
        STA     pg_camx+1,X
        CLC                             ; hptr = h + camx, iptr = ids + camx
        LDA     camx
        ADC     #<track_h
        STA     hptr
        STA     iptr
        LDA     camx+1
        ADC     #>track_h
        STA     hptr+1
        CLC
        ADC     #>(track_ids - track_h)
        STA     iptr+1
rg_tabok: LDA     #0
        STA     col
        LDA     pidx
        BEQ     rg_p1
        LDA     #40
rg_p1:    STA     sti
rg_col:   LDX     sti
        LDA     same                    ; nothing moved: only the bike's
        BEQ     rg_calc                 ; columns (their partial rows too)
        LDA     bk_bot,X
        BNE     rg_calc
        JMP     rg_next
rg_calc:  LDY     #0                      ; the window's pattern
        LDA     (iptr),Y
        TAX
        LDA     (hptr),Y                ; mn = h[x] - rel0
        SEC
        SBC     pat_rel0,X
        STA     mn
        LDA     pat_k,X
        BEQ     rg_flat0
        CLC
        ADC     mn
        STA     mx
        SEC                             ; partial row X: pool + off - mn + X
        LDA     pat_plo,X
        SBC     mn
        STA     part_lda+1
        LDA     pat_phi,X
        SBC     #0
        STA     part_lda+2
        LDX     sti
        JMP     rg_rows
rg_flat0: LDA     mn
        STA     mx
rg_flat:  LDX     sti                     ; flat and unchanged: nothing to do
        LDA     mn
        STA     rlo
        CMP     st_mn,X
        BNE     rg_rows
        CMP     st_mx,X
        BEQ     rg_bbox
rg_rows:  ; changed rows: min(mn, old mn) .. max(mx, old mx)
        LDA     st_mn,X
        CMP     mn
        BCC     rg_lo
        LDA     mn
rg_lo:    STA     rlo
        LDA     st_mx,X
        CMP     mx
        BCS     rg_hi
        LDA     mx
rg_hi:    LDY     col
        JSR     write_rows
        LDX     sti
        LDA     mn
        STA     st_mn,X
        LDA     mx
        STA     st_mx,X
rg_bbox:  ; the bike drawn on this page two frames ago, rows bk_top..bk_bot
        ; of the column. Rows from rlo down were just rewritten, or are
        ; solid ground on both frames (the bike ORed into white is
        ; invisible): only the rows above rlo need the sky back.
        LDA     bk_bot,X
        BEQ     rg_next                   ; (empty: top $FF, bottom 0)
        LDA     rlo
        BEQ     rg_next
        SEC
        SBC     #1
        CMP     bk_bot,X
        BCC     rg_end
        LDA     bk_bot,X
rg_end:   CMP     bk_top,X
        BCC     rg_next
        PHA
        LDA     bk_top,X
        STA     rlo
        PLA
        LDY     col
        JSR     sky_rows
rg_next:  CLC                             ; next window: 7 pixels on
        LDA     hptr
        ADC     #7
        STA     hptr
        STA     iptr
        BCC     rg_n1
        INC     hptr+1
        INC     iptr+1
rg_n1:    INC     sti
        INC     col
        LDA     col
        CMP     #40
        BEQ     rg_done
        JMP     rg_col
rg_done:  RTS

; ---------------------------------------------------------------------------
; write_rows -- rows rlo..A of column Y from the ground model:
; sky above mn, partial bytes (part_lda) from mn to mx-1, solid from mx.
; sky_rows -- rows rlo..A of column Y set to sky. Both keep Y.
; Runs of FILL_MIN rows or more of sky / ground go through the unrolled row
; writer (5 cycles a row), shorter ones through the loop (~30).
; ---------------------------------------------------------------------------
FILL_MIN = 4

sky_rows:
        CLC
        ADC     #1
        STA     rend1
        STA     rend2
        STA     rend3
        LDX     rlo
        JMP     wr_sky
write_rows:
        CLC
        ADC     #1
        STA     rend3                   ; end (exclusive)
        CMP     mn                      ; rend1 = min(mn, end)
        BCC     @e1
        LDA     mn
@e1:    STA     rend1
        LDA     mx                      ; rend2 = min(mx, end)
        CMP     rend3
        BCC     @e2
        LDA     rend3
@e2:    STA     rend2
        LDX     rlo
wr_sky: SEC                             ; sky rows X .. rend1-1
        LDA     rend1
        STX     fend
        SBC     fend
        BCC     wr_part                 ; (none)
        BEQ     wr_part
        CMP     #FILL_MIN
        BCC     wr_sky1
        LDA     #0
        LDX     rend1
        JSR     fill
        LDX     rend1
        JMP     wr_part
wr_sky1:
        LDA     hgr_lo,X
        STA     rptr
        HGR_HI_SITE
        LDA     hgr_hi,X
        STA     rptr+1
        LDA     #0
        STA     (rptr),Y
        INX
        CPX     rend1
        BCC     wr_sky1
wr_part:
        CPX     rend2
        BCS     wr_full
        LDA     hgr_lo,X
        STA     rptr
        HGR_HI_SITE
        LDA     hgr_hi,X
        STA     rptr+1
part_lda:
        LDA     pool,X                  ; operand patched per column
        STA     (rptr),Y
        INX
        BNE     wr_part
wr_full:
        SEC                             ; ground rows X .. rend3-1
        LDA     rend3
        STX     fend
        SBC     fend
        BCC     wr_done
        BEQ     wr_done
        CMP     #FILL_MIN
        BCC     wr_full1
        LDA     #GROUND
        LDX     rend3
        JMP     fill
wr_full1:
        LDA     hgr_lo,X
        STA     rptr
        HGR_HI_SITE
        LDA     hgr_hi,X
        STA     rptr+1
        LDA     #GROUND
        STA     (rptr),Y
        INX
        CPX     rend3
        BCC     wr_full1
wr_done:
        RTS

; ---------------------------------------------------------------------------
; fill -- rows fend .. X-1 of column Y := A, through the draw page's row
; writer: an RTS is put after the last row, the writer is called at the
; first, then the RTS is taken back. Keeps Y.
; ---------------------------------------------------------------------------
fill:   PHA
        LDA     fend                    ; first row (fill's caller put it there)
        PHA
        CLC                             ; fend = writer + 3 * end
        LDA     m3lo,X
        ADC     fbase
        STA     fend
        LDA     m3hi,X
        ADC     fbase+1
        STA     fend+1
        LDX     #0
        LDA     (fend,X)
        STA     fsave
        LDA     #$60                    ; RTS
        STA     (fend,X)
        PLA
        TAX
        CLC                             ; call writer + 3 * first
        LDA     m3lo,X
        ADC     fbase
        STA     @jsr+1
        LDA     m3hi,X
        ADC     fbase+1
        STA     @jsr+2
        PLA
@jsr:   JSR     fill1
        LDX     #0
        LDA     fsave
        STA     (fend,X)
        RTS

; ---------------------------------------------------------------------------
; draw_bike -- wheels, frame, rider; marks what it covers on this page
; ---------------------------------------------------------------------------
draw_bike:
        LDX     #2                      ; screen coordinates
@sc:    SEC
        LDA     pt_xl,X
        SBC     camx
        STA     spx,X
        LDA     pt_yh,X
        STA     spy,X
        DEX
        BPL     @sc
        SEC                             ; torso step = (dy/8, -dx/8)
        LDA     spy+1
        SBC     spy
        JSR     asr3
        STA     hdx
        SEC
        LDA     spx
        SBC     spx+1
        JSR     asr3
        STA     hdy
        LDA     spx+2                   ; head centre = rider + 3 steps
        CLC
        ADC     hdx
        ADC     hdx
        ADC     hdx
        STA     sprx
        LDA     spy+2
        CLC
        ADC     hdy
        ADC     hdy
        ADC     hdy
        CMP     #3                      ; (row 3 at the highest)
        BCS     @hy
        LDA     #3
@hy:    STA     spry
        JSR     mark_bike
        JSR     draw_flag
        ; frame: rear-front, rear-rider, front-rider, rider-shoulders
        LDX     #0
        LDY     #1
        JSR     line_pts
        LDX     #0
        LDY     #2
        JSR     line_pts
        LDX     #1
        LDY     #2
        JSR     line_pts
        LDA     spx+2
        STA     hl_ln_x0
        LDA     spy+2
        STA     hl_ln_y0
        CLC
        LDA     spx+2
        ADC     hdx
        ADC     hdx
        STA     hl_ln_x1
        CLC
        LDA     spy+2
        ADC     hdy
        ADC     hdy
        STA     hl_ln_y1
        JSR     hgr_line8
        ; head
        SEC
        LDA     sprx
        SBC     #2
        TAX
        LDA     div7,X
        STA     col
        LDY     mod7,X
        LDA     head_lo,Y
        STA     sptr
        LDA     head_hi,Y
        STA     sptr+1
        SEC
        LDA     spry
        SBC     #2
        STA     spry
        LDA     #HEAD_H
        STA     sprh
        LDA     #2
        STA     sprw
        JSR     draw_sprite
        ; wheels
        LDX     #0
        JSR     draw_wheel
        LDX     #1
        ; fall through

; wheel X: sprite (angle / 16 mod 4, shift) at centre - 6
draw_wheel:
        SEC
        LDA     spy,X
        SBC     #6
        STA     spry
        LDA     wheel_ang,X
        LSR     A
        LSR     A
        LSR     A
        LSR     A
        AND     #WHEEL_FRAMES-1
        STA     sprh                    ; (frame, for now)
        SEC
        LDA     spx,X
        SBC     #6
        TAX
        LDA     div7,X
        STA     col
        LDA     sprh                    ; frame * 7 + shift
        ASL     A
        ASL     A
        ASL     A
        SEC
        SBC     sprh
        CLC
        ADC     mod7,X
        TAY
        LDA     wheel_lo,Y
        STA     sptr
        LDA     wheel_hi,Y
        STA     sptr+1
        LDA     #WHEEL_H
        STA     sprh
        LDA     #3
        STA     sprw
        ; fall through

; draw_sprite -- OR sprh rows of sprw (2 or 3) bytes from sptr at
; (col, spry). The source is read with abs,X (operands patched), X running
; through the sprite; Y walks the 2-3 screen bytes of a row.
draw_sprite:
        LDA     sptr
        STA     ds_s0+1
        STA     ds_s1+1
        STA     ds_s2+1
        LDA     sptr+1
        STA     ds_s0+2
        STA     ds_s1+2
        STA     ds_s2+2
        LDA     sprw
        CMP     #3
        LDA     #$EA                    ; NOP NOP NOP: 3 bytes wide
        LDY     #$EA
        BCS     ds_w
        LDA     #$4C                    ; JMP ds_next: 2 bytes wide
        LDY     #<ds_next
ds_w:   STA     ds_third
        STY     ds_third+1
        LDA     #$EA
        BCS     ds_w2
        LDA     #>ds_next
ds_w2:  STA     ds_third+2
        LDX     #0
ds_row: LDY     spry
        CLC
        LDA     hgr_lo,Y
        ADC     col
        STA     rptr
        HGR_HI_SITE
        LDA     hgr_hi,Y
        STA     rptr+1
        LDY     #0
ds_s0:  LDA     wheel_spr,X             ; patched: sprite
        INX
        ORA     (rptr),Y
        STA     (rptr),Y
        INY
ds_s1:  LDA     wheel_spr,X
        INX
        ORA     (rptr),Y
        STA     (rptr),Y
ds_third:
        NOP                             ; patched: NOPs or JMP ds_next
        NOP
        NOP
        INY
ds_s2:  LDA     wheel_spr,X
        INX
        ORA     (rptr),Y
        STA     (rptr),Y
ds_next:
        INC     spry
        DEC     sprh
        BNE     ds_row
        RTS

; ---------------------------------------------------------------------------
; mark_bike -- what the bike covers on this page, per byte column
; (bk_top / bk_bot), for render_ground to erase it two frames later.
; bb_c0 / bb_c1 keep the column range, bb_top the highest row (HUD check).
; ---------------------------------------------------------------------------
mark_bike:
        LDA     pidx                    ; forget the old marks of this page
        BEQ     @b0
        LDA     #40
@b0:    STA     sti
        LDX     pidx
        LDA     bb_c0,X
        STA     col
@clr:   LDX     pidx
        LDA     bb_c1,X
        CMP     col
        BCC     @new
        CLC
        LDA     col
        ADC     sti
        TAX
        LDA     #$FF
        STA     bk_top,X
        LDA     #0
        STA     bk_bot,X
        INC     col
        BNE     @clr
@new:   LDX     pidx
        LDA     #$FF
        STA     bb_c0,X
        STA     bb_top,X
        LDA     #0
        STA     bb_c1,X
        LDX     #0                      ; wheels: centre +-6
        JSR     mark_wheel
        LDX     #1
        JSR     mark_wheel
        SEC                             ; head: centre +-2
        LDA     sprx
        SBC     #2
        STA     bx0
        CLC
        ADC     #4
        STA     bx1
        SEC
        LDA     spry
        SBC     #2
        STA     by0
        CLC
        ADC     #4
        STA     by1
        JSR     mark
        LDX     #0                      ; frame lines
        LDY     #1
        JSR     mark_line
        LDX     #0
        LDY     #2
        JSR     mark_line
        LDX     #1
        LDY     #2
        JSR     mark_line
        LDA     sprx                    ; torso: rider to head
        STA     spx+3
        LDA     spry
        STA     spy+3
        LDX     #2
        LDY     #3
        ; fall through

; mark the box of the segment between screen points X and Y
mark_line:
        LDA     spx,X
        CMP     spx,Y
        BCC     @x
        LDA     spx,Y
        STA     bx0
        LDA     spx,X
        BCS     @x2
@x:     STA     bx0
        LDA     spx,Y
@x2:    STA     bx1
        LDA     spy,X
        CMP     spy,Y
        BCC     @y
        LDA     spy,Y
        STA     by0
        LDA     spy,X
        BCS     @y2
@y:     STA     by0
        LDA     spy,Y
@y2:    STA     by1
        JMP     mark

mark_wheel:
        SEC
        LDA     spx,X
        SBC     #6
        STA     bx0
        CLC
        ADC     #12
        STA     bx1
        SEC
        LDA     spy,X
        SBC     #6
        STA     by0
        CLC
        ADC     #12
        STA     by1
        ; fall through

; mark columns of x bx0..bx1 with rows by0..by1
mark:   LDX     pidx
        LDA     by0
        CMP     bb_top,X
        BCS     @t
        STA     bb_top,X
@t:     LDY     bx0
        LDA     div7,Y
        STA     col
        CMP     bb_c0,X
        BCS     @c0
        STA     bb_c0,X
@c0:    LDY     bx1
        LDA     div7,Y
        CMP     #40
        BCC     @c1
        LDA     #39
@c1:    STA     rend1                   ; last column
        CMP     bb_c1,X
        BCC     @c2
        STA     bb_c1,X
@c2:    CLC
        LDA     col
        ADC     sti
        TAX
@col:   LDA     by0
        CMP     bk_top,X
        BCS     @nt
        STA     bk_top,X
@nt:    LDA     by1
        CMP     bk_bot,X
        BCC     @nb
        STA     bk_bot,X
@nb:    INX
        LDA     col
        CMP     rend1
        INC     col
        BCC     @col
        RTS

; ---------------------------------------------------------------------------
; draw_flag -- the finish / lap line: a 2-pixel pole and a pennant on the
; ground at finish_x, while on screen (x < 244: hgr_line8's x is 8 bits);
; marked like the bike, so render_ground gives its sky back
; ---------------------------------------------------------------------------
FLAG_H = 32

draw_flag:
        SEC
        LDA     finish_x
        SBC     camx
        STA     bx0
        LDA     finish_x+1
        SBC     camx+1
        BNE     @rts
        LDA     bx0
        CMP     #244
        BCS     @rts
        ADC     #11
        STA     bx1
        CLC                             ; the ground row there
        LDA     #<track_h
        ADC     finish_x
        STA     sptr
        LDA     #>track_h
        ADC     finish_x+1
        STA     sptr+1
        LDY     #0
        LDA     (sptr),Y
        SEC
        SBC     #1
        STA     by1
        SBC     #FLAG_H
        STA     by0
        JSR     mark
        LDX     #10                     ; pole (x, x+1), then 9 pennant rows
@l:     TXA
        PHA
        CPX     #9
        BCC     @pen
        LDA     by1
        STA     hl_ln_y1
        LDA     by0
        STA     hl_ln_y0
        TXA                             ; X = 10 / 9: x / x + 1
        EOR     #10
        BEQ     @x
        LDA     #1
@x:     CLC
        ADC     bx0
        STA     hl_ln_x0
        STA     hl_ln_x1
        BCC     @draw                   ; (always)
@pen:   TXA
        CLC
        ADC     by0
        STA     hl_ln_y0
        STA     hl_ln_y1
        LDA     bx0
        ADC     #2
        STA     hl_ln_x0
        ADC     flag_w,X
        STA     hl_ln_x1
@draw:  JSR     hgr_line8
        PLA
        TAX
        DEX
        BPL     @l
@rts:   RTS

.segment "RODATA"
flag_w: .byte 1, 3, 5, 7, 9, 7, 5, 3, 1 ; pennant row widths - 1
.segment "CODE"

; line between screen points X and Y
line_pts:
        LDA     spx,X
        STA     hl_ln_x0
        LDA     spy,X
        STA     hl_ln_y0
        LDA     spx,Y
        STA     hl_ln_x1
        LDA     spy,Y
        STA     hl_ln_y1
        JMP     hgr_line8

; A = signed byte >> 3 (arithmetic)
asr3:   CMP     #$80
        ROR     A
        CMP     #$80
        ROR     A
        CMP     #$80
        ROR     A
        RTS

