; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Sierra encounter filters and probability from T0A S00. Position, lifetime
; and reactions use documented port rules. No weather RNG calls.
.segment "INPUT"
module_nature:
        lda     nature_frequency
        sta     msgnum
        lda     #0
        sta     msgnum+1
        lda     #<m_nature
        ldx     #>m_nature
        jsr     get_number
        bcc     :+
        rts
:
        lda     msgnum+1
        bne     @bad
        lda     msgnum
        cmp     #101
        bcs     @bad
        sta     nature_frequency
        lda     #<m_ok
        ldx     #>m_ok
        jmp     message
@bad:   lda     #<m_nature_bad
        ldx     #>m_nature_bad
        jmp     message
m_nature: .byte "WILDLIFE FREQUENCY IS #.|ENTER A NEW VALUE FROM 0 TO 100.",0
m_nature_bad: .byte "FREQUENCY MUST BE FROM 0 TO 100.",0

.segment "ENVIRON"
.export module_fauna
module_fauna = native_nature

; Lifetime advances during every activity; only travel rolls new encounters.
fauna_age:
        lda     animal_kind
        beq     @done
        lda     animal_x
        cmp     px+1
        bne     @clear
        lda     animal_y
        cmp     py+1
        bne     @clear
        lda     animal_age
        clc
        adc     scene_minutes
        bcs     @danger
        cmp     #60
        bcs     @danger
        sta     animal_age
@done:  rts
@danger:
        jmp     animal_attack
@clear: lda     #0
        sta     animal_kind
        rts

; The original acceptance endpoint keeps an existing animal when RND < .5,
; otherwise replaces it, even if the candidate is the same species.
fauna_accept:
        lda     animal_kind
        beq     @set
        jsr     weather_random
        fop     FCOMP, f_half
        cmp     #$FF
        beq     @done
@set:
        inc     journey_encounters
        bne     :+
        inc     journey_encounters+1
:       lda     #1
        sta     fauna_alert
        lda     fauna_species
        clc
        adc     #6
        sta     animal_kind
        lda     px+1
        sta     animal_x
        lda     py+1
        sta     animal_y
        lda     heading
        sta     animal_bearing
        lda     heading+1
        sta     animal_bearing+1
        lda     #0
        sta     animal_age
@done:
        lda     MAP+37
        bne     :+
        jmp     module_fauna_cap
:       rts

.segment "SITES"
fauna_random:
        lda     fauna_rng
        bne     :+
        lda     #$B7            ; repair a zero LFSR state
:       lsr     a
        bcc     :+
        eor     #$B8
:       sta     fauna_rng
        rts

.segment "ENVIRON"
; Environment vector: integer season percentage, hour, terrain, altitude
; in hundreds of feet, maximum absolute height difference in the 3x3,
; regional climate index. Water still has no distinct river encoding.
fauna_environment:
        fld     s_date
        fop     FMULT, f_100
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        sta     fauna_env
        fld     s_hour
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        sta     fauna_env+1
        jsr     native_here
        sta     fauna_height
        lda     geo_wooded
        pha                     ; neighboring probes must not replace the centre
        lda     fauna_height
        cmp     #128
        ldx     #40
        bcc     :+
        lda     MAP+37
        beq     @terrain
        lda     geo_water_kind
        bne     @terrain
        ldx     #30             ; original river terrain differs from lake terrain
        bne     @terrain
:
        ldx     #0
        cmp     #96
        bcs     @terrain
        ldx     #10
@terrain:
        stx     fauna_env+2
        lda     fauna_height
        and     #127
        sta     fauna_height
        clc
        adc     M_BASE
        sta     fauna_env+3
        lda     fauna_env+2
        cmp     #40
        beq     @no_woods
        lda     MAP+37
        beq     @legacy_woods
        lda     geo_wooded
        beq     @no_woods
        bne     @wooded
@legacy_woods:
        jsr     woods_here
        bcc     @no_woods
@wooded:
        ldx     #20
        lda     fauna_env+3
        cmp     #110
        bcc     :+
        ldx     #30
:       stx     fauna_env+2
@no_woods:
        lda     MAP+23
        bne     :+
        lda     #31             ; legacy map: Sierra
:       sta     fauna_env+5
        lda     #0
        sta     fauna_env+4
        lda     py
        asl
        lda     py+1
        rol
        sta     fauna_row
        beq     :+
        dec     fauna_row
:       lda     #3
        sta     fauna_rows
@row:   lda     px
        asl
        lda     px+1
        rol
        sta     fauna_col
        beq     :+
        dec     fauna_col
:       lda     #3
        sta     fauna_cols
@cell:  ldx     fauna_row
        cpx     #168
        bcs     @skip
        ldy     fauna_col
        cpy     #224
        bcs     @skip
        jsr     cell_native
        and     #127
        sec
        sbc     fauna_height
        bcs     :+
        eor     #255
        clc
        adc     #1
:       cmp     fauna_env+4
        bcc     @skip
        sta     fauna_env+4
@skip:  inc     fauna_col
        dec     fauna_cols
        bne     @cell
        inc     fauna_row
        dec     fauna_rows
        bne     @row
        ldy     fauna_env+4
        lda     #0
        jsr     GIVAYF
        fst     t1
        fld     f_24
        fop     FDIV, t1
        jsr     FATN
        fop     FMULT, fauna_slope_degrees
        inc     FAC
        inc     FAC
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        sta     fauna_env+4
        pla
        sta     geo_wooded
        rts
.segment "RODATA"
fauna_slope_degrees: .byte $86,$65,$2F,$1A,$A0 ; original T09/S08 degree coefficient
.segment "ENVIRON"

; Carry set iff all six original signed centre/width pairs match.
.segment "SITES"
fauna_eligible:
        ldx     fauna_species
        lda     fauna_offsets,x
        tax
        ldy     #0
@pair:  lda     fauna_env,y
        sec
        sbc     fauna_ranges,x
        bcs     :+
        eor     #255
        clc
        adc     #1
:       sta     fauna_delta
        inx
        lda     fauna_ranges,x
        bmi     @outside
        beq     @different
        cmp     fauna_delta
        bcc     @no
        bcs     @next
@outside:
        eor     #255
        clc
        adc     #1
        cmp     fauna_delta
        bcs     @no
        bcc     @next
@different:
        lda     fauna_delta
        beq     @no
@next:  inx
        iny
        cpy     #6
        bne     @pair
        sec
        rts
@no:    clc
        rts

; threshold = 256 * minutes * frequency * sqrt(difficulty) * rate * 1e-5.
; Comparing the ROM float avoids a rounded integer cutoff. The generator
; is the port's independent LFSR, not the original Applesoft RND sequence.
.segment "SITES"
fauna_probability:
        ldy     MAP+22
        bne     :+
        ldy     #4              ; legacy map difficulty
:       lda     #0
        jsr     GIVAYF
        jsr     FSQR
        fst     fauna_threshold
        ldy     scene_minutes
        lda     #0
        jsr     GIVAYF
        fop     FMULT, fauna_threshold
        fst     fauna_threshold
        ldy     nature_frequency
        lda     #0
        jsr     GIVAYF
        fop     FMULT, fauna_threshold
        fst     fauna_threshold
        ldx     fauna_species
        ldy     fauna_rates,x
        lda     #0
        jsr     GIVAYF
        fop     FMULT, fauna_threshold
        fop     FMULT, fauna_k
        fst     fauna_threshold
        rts

.segment "SITES"
fauna_offsets: .byte 0,12,24
fauna_ranges:
        .byte 50,34,11,252,15,6,55,25,25,25,30,20
        .byte 50,50,12,251,10,12,50,40,35,35,30,20
        .byte 58,25,12,6,5,6,40,40,30,30,30,20
fauna_rates: .byte 80,40,100
fauna_k: .byte $78,$27,$C5,$AC,$47 ; 256e-5, Applesoft float
.segment "SCRATCH"
; Must survive geography/TRAVEL BLOADs; these bytes are beyond DOS text backup.
fauna_species: .res 1
fauna_env: .res 6
fauna_height: .res 1
fauna_row: .res 1
fauna_col: .res 1
fauna_rows: .res 1
fauna_cols: .res 1
fauna_delta: .res 1
.segment "SITES"
fauna_threshold: .res 5
