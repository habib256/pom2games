; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; stars_draw.s -- night-sky stars of the view engine (lot 7, docs/STARS.md)
; ============================================================================
; Resident part: the visible list written once per hour by the module
; wildsky.bin (src/stars.s), and the per-column drawing called by render_sky
; after the sky zones and before sky_column (the Moon), so that the ridge
; (`top`), opaque sprite rows (scene_span) and the trees painted afterwards
; (forest_paint) hide the stars, and so that a turn draws the stars of the
; revealed columns only: a star depends on the column's azimuth alone.
;
; Per column rather than per star: the ridge row of a column (`top`) only
; exists while render_sky runs, and storing 140 tops would cost more than
; the list. The list is grouped by azimuth bucket (az >> 4, 16 units, 35
; buckets), in catalogue order inside a bucket: a column scans its bucket
; (4.6 entries on average for 160) from the last entry to the first, so that
; the brightest star of a shared pixel is painted last. Entry: st_a = class
; << 6 | tint << 4 | az & 15 (the class compares below star_thr: $40, $80,
; $C0), st_row.
;
; Engine contract: ang (column azimuth 0..559), top (first terrain row),
; sp_end, scene_span (A = mood entry, Y..sp_end-1; clobbers A, X, Y),
; sky_mood, weather_sky, MOOD_NIGHT_BRIGHT (build/dhgr_tables.inc).
; Segments: STARS_CODE and STARS_LIST (LOWCODE and LOWTEXT; SKYRES, the main
; language card at $DE00, when STARS_CODE_LC is defined: the game, where the
; module write-enables the bank to store the list) and STARS_DATA (LOWTEXT:
; the threshold and the scan variables, written while the bank is read
; only). The list is initialised to zero: empty before the first module run.
; ============================================================================

; ca65 cannot test a .define: the game sets the symbol STARS_CODE_LC to run
; the code from the main language card (segment SKYRES, src/wild.cfg).
.ifdef STARS_CODE_LC
.define STARS_CODE "SKYRES"
.define STARS_LIST "SKYRES"
.else
.define STARS_CODE "LOWCODE"
.define STARS_LIST "LOWTEXT"
.endif
.define STARS_DATA "LOWTEXT"

STAR_LIST_MAX = 160             ; tools/stars_ref.py LIST_MAX (checked by stars.s)
STAR_BUCKETS  = 36              ; az >> 4 = 0..34, then the count

.segment STARS_LIST
; Visible list (src/stars.s, tools/stars_ref.resident): grouped by bucket.
st_a:      .res STAR_LIST_MAX   ; class << 6 | tint << 4 | az & 15
st_row:    .res STAR_LIST_MAX   ; logical row 16..95
st_bucket: .res STAR_BUCKETS    ; first entry of bucket az >> 4 = 0..34; [35] = count

.segment STARS_DATA
star_thr:  .res 1               ; frame: draw st_a < star_thr (0: none)
st_end:    .res 1               ; column scan: first entry of the bucket
st_x:      .res 1               ;              entry
st_b:      .res 1               ;              bucket, then az & 15

.segment STARS_CODE
; stars_frame -- after dhgr_frame: the stars of this frame's mood. Night
; moods only (no civil or nautical twilight), never under clouds; the full
; Moon (night bright) leaves the first magnitude, night dim the classes 0-1,
; night dark every star. Clobbers A, X.
stars_frame:
        lda     #0
        ldx     weather_sky
        bne     @set
        lda     sky_mood
        sec
        sbc     #MOOD_NIGHT_BRIGHT
        bcc     @none           ; day and twilight moods
        tax
        lda     st_thresholds,x
        .byte   $2C             ; BIT abs: skip the next instruction
@none:  lda     #0
@set:   sta     star_thr
        rts
st_thresholds: .byte $40, $80, $C0     ; night bright, dim, dark
st_solid:  .byte STAR_SOLID0, STAR_SOLID1, STAR_SOLID2  ; tint -> c << 4 | c

; stars_column -- the stars of the column at azimuth `ang`, rows < top.
; Clobbers A, X, Y.
stars_column:
        lda     star_thr
        beq     @rts
        lda     ang+1           ; bucket = ang >> 4 (0..34)
        asl     a
        asl     a
        asl     a
        asl     a
        sta     st_b
        lda     ang
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        ora     st_b
        tax
        lda     st_bucket,x
        sta     st_end
        lda     ang
        and     #$0F
        sta     st_b
        lda     st_bucket+1,x
        tax                     ; one past the bucket's last entry
@scan:  cpx     st_end
        beq     @rts
        dex
        lda     st_a,x
        cmp     star_thr
        bcs     @scan           ; too faint for this mood
        and     #$0F
        cmp     st_b
        bne     @scan           ; another column of the bucket
        ldy     st_row,x
        cpy     top
        bcs     @scan           ; behind the ridge
        stx     st_x
        lda     st_a,x          ; tint -> solid entry c << 4 | c
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        and     #3
        tax
        lda     st_solid,x
        iny
        sty     sp_end
        dey
        jsr     scene_span
        ldx     st_x
        jmp     @scan
@rts:   rts
stars_draw_end:
