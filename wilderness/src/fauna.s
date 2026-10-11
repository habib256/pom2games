; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Sierra encounter filters and probability from T0A S00. Position, lifetime
; and reactions still use the first port's rules. No weather RNG calls.
.segment "ENVIRON"
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

module_fauna:
        lda     animal_kind
        beq     @roll
        lda     animal_x
        cmp     px+1
        bne     @clear
        lda     animal_y
        cmp     py+1
        bne     @clear
        lda     animal_age
        clc
        adc     scene_minutes
        bcs     @clear
        cmp     #60
        bcs     @clear
        sta     animal_age
        jmp     @roll
@clear: lda     #0
        sta     animal_kind
@roll:  jsr     fauna_environment
        lda     #0
        sta     fauna_species
@species:
        jsr     fauna_eligible
        bcc     @next
        jsr     fauna_probability
        jsr     fauna_random
        tay
        lda     #0
        jsr     GIVAYF
        fop     FCOMP, fauna_threshold
        bpl     @next           ; RND >= probability: no sighting
        jsr     fauna_accept
        jmp     @next           ; original checks all species in table order
@next:  inc     fauna_species
        lda     fauna_species
        cmp     #3
        bne     @species
fauna_done:
        lda     #0
        sta     scene_minutes
        rts

; The original acceptance endpoint keeps an existing animal when RND < .5,
; otherwise replaces it, even if the candidate is the same species.
fauna_accept:
        lda     animal_kind
        beq     @set
        jsr     fauna_random
        cmp     #128
        bcc     @done
@set:
        lda     #1
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
        rts

fauna_random:
        lda     fauna_rng
        bne     :+
        lda     #$B7            ; repair a zero LFSR state
:       lsr     a
        bcc     :+
        eor     #$B8
:       sta     fauna_rng
        rts

; Environment vector: integer season percentage, hour, terrain, altitude
; in hundreds of feet, maximum absolute height difference in the 3x3,
; regional climate index. Water still has no distinct river encoding.
fauna_environment:
        fld     s_date
        fop     FMULT, f_100
        jsr     AYINT
        lda     $A1
        sta     fauna_env
        fld     s_hour
        jsr     AYINT
        lda     $A1
        sta     fauna_env+1
        ldx     py+1
        ldy     px+1
        jsr     cell_at
        cmp     #128
        ldx     #40
        bcs     @terrain
        ldx     #0
        cmp     #96
        bcs     @terrain
        ldx     #10
@terrain:
        stx     fauna_env+2
        and     #127
        sta     fauna_height
        clc
        adc     M_BASE
        sta     fauna_env+3
        lda     fauna_env+2
        cmp     #40
        beq     @no_woods
        jsr     woods_here
        bcc     @no_woods
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
        lda     py+1
        sta     fauna_row
        beq     :+
        dec     fauna_row
:       lda     #3
        sta     fauna_rows
@row:   lda     px+1
        sta     fauna_col
        beq     :+
        dec     fauna_col
:       lda     #3
        sta     fauna_cols
@cell:  ldx     fauna_row
        cpx     #GH
        bcs     @skip
        ldy     fauna_col
        cpy     #GW
        bcs     @skip
        jsr     cell_at
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
        rts

; Carry set iff all six original signed centre/width pairs match.
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

fauna_offsets: .byte 0,12,24
fauna_ranges:
        .byte 50,34,11,252,15,6,55,25,25,25,30,20
        .byte 50,50,12,251,10,12,50,40,35,35,30,20
        .byte 58,25,12,6,5,6,40,40,30,30,30,20
fauna_rates: .byte 80,40,100
fauna_k: .byte $78,$27,$C5,$AC,$47 ; 256e-5, Applesoft float
fauna_species: .byte 0
fauna_env: .res 6
fauna_height: .byte 0
fauna_row: .byte 0
fauna_col: .byte 0
fauna_rows: .byte 0
fauna_cols: .byte 0
fauna_delta: .byte 0
fauna_threshold: .res 5
