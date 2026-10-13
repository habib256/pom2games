; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; stars.s -- hourly star module wildsky.bin (lot 7, ID 25, SIM window $9600)
; ============================================================================
; Computes the visible list of src/stars_draw.s once per hour (with the
; Moon): local sidereal time, then for each catalogue star (selection order:
; Polaris and the Cross, then magnitude; 282 stars to V = 3.50, 3 bytes each,
; read through a pointer) its altitude and azimuth with the view engine's
; sine table sin_lo (build/tables.inc, 560 units per turn), its row on the
; Moon's perspective (95 - INT(48 tan alt)), the Moon's disc mask. The first
; STAR_LIST_MAX stars kept are grouped by azimuth bucket (az >> 4) with a
; stable counting sort, with bucket starts. Pure integer code: the
; specification, bit for bit, is tools/stars_ref.py (docstring); the
; catalogue and tables are build/stars_tables.inc (tools/genstars.py).
; Products are 8 x 8 bits by quarter squares, f(x) = INT(x * x / 4) for
; x = 0..511, a 1 KB table the module builds in its own BSS at each run.
;
; Entries
;   module_sky_stars  game entry: copies the head of the catalogue (directory
;                     entry 24, segment STARS_CATALOGUE) in front of the
;                     module, whose image begins with the rest, then day =
;                     INT(s_date * 365), minute = INT(s_hour * 60) through the
;                     ROM floating point, then stars_compute. Assembled
;                     unless STARS_BENCH is defined.
;   stars_compute     integer entry: st_day (0..367), st_min (0..1439).
; Reads M_LAT (signed degrees), MAP+25 (signed east longitude), sky_bearing
; and sky_y (the Moon of the same hour: call after sky_position, at night),
; sin_lo / SIN_UNIT_START and sky_outer (resident). Writes st_a, st_row,
; st_bucket (src/stars_draw.s): in the game they are in bank 2 of the main
; language card (STARS_LIST_LC), write-enabled for the final pass only, with
; interrupts masked, then the ROM is selected again. Temporaries: zero page
; STARS_ZP.. (see below) and the BSS segment STARS_BSS (page aligned, not
; part of the image). Clobbers A, X, Y.
; ============================================================================

; Inputs and temporaries in zero page (STARS_ZP: the ROM floating point
; area $5E-$AC of the game, free between two views; the module runs
; outside a render, after its own last ROM call).
.ifndef STARS_ZP
STARS_ZP = $5E
.endif
st_day   = STARS_ZP + 0
st_min   = STARS_ZP + 2
st_lst   = STARS_ZP + 4
st_w     = STARS_ZP + 6
st_u     = STARS_ZP + 8
st_q     = STARS_ZP + 11
st_m     = STARS_ZP + 14
st_p     = STARS_ZP + 15
st_t     = STARS_ZP + 17
st_fneg  = STARS_ZP + 19
st_sf    = STARS_ZP + 20
st_cf    = STARS_ZP + 21
st_n     = STARS_ZP + 22
st_k     = STARS_ZP + 23          ; catalogue index, 16 bits
st_hl    = STARS_ZP + 25
st_hh    = STARS_ZP + 26
st_quad  = STARS_ZP + 27
st_s     = STARS_ZP + 28
st_smag  = STARS_ZP + 29
st_cmag  = STARS_ZP + 30
st_sneg  = STARS_ZP + 31
st_cneg  = STARS_ZP + 32
st_dneg  = STARS_ZP + 33
st_sd    = STARS_ZP + 34
st_cd    = STARS_ZP + 35
st_cdch  = STARS_ZP + 36
st_acc   = STARS_ZP + 37          ; up (0..2), N (3..5)
st_rowv  = STARS_ZP + 45
st_e     = STARS_ZP + 46
st_eneg  = STARS_ZP + 48
st_nneg  = STARS_ZP + 49
st_rem   = STARS_ZP + 50
st_large = STARS_ZP + 52
st_flip  = STARS_ZP + 54
st_qq    = STARS_ZP + 55
st_azl   = STARS_ZP + 56
st_azhh  = STARS_ZP + 57
st_dl    = STARS_ZP + 58
st_dh    = STARS_ZP + 59
st_cp    = STARS_ZP + 60          ; record pointer
st_lq    = STARS_ZP + 62          ; LST in quarter view units, 0..2239
st_latu  = STARS_ZP + 64
st_du    = STARS_ZP + 65
st_b1    = STARS_ZP + 66          ; record byte 1
st_a8    = STARS_ZP + 67          ; mul8 operand
STARS_ZP_SIZE = 68
.assert STARS_ZP + STARS_ZP_SIZE <= $100, error, "star temporaries leave the zero page"
.assert STAR_LIST_MAX = STAR_LIST_MAX_REF, error, "list size: src/stars_draw.s and tools/stars_ref.py"
.assert STAR_BUCKETS = STAR_BUCKETS_REF, error, "bucket count: src/stars_draw.s and tools/stars_ref.py"


.ifndef STARS_MODULE
.define STARS_MODULE "SKYSTARS"
.endif
.ifndef STARS_BSS
.define STARS_BSS "SKYSTBSS"
.endif
.ifndef STARS_CATALOGUE
.define STARS_CATALOGUE "SKYCAT"   ; st_cat: first STAR_CAT_HEAD stars (record 24)
.define STARS_CATALOGUE2 "SKYCAT2" ; st_cat2: the others, head of the module image
.endif

; Not part of the image: built or filled at each run.
.segment STARS_BSS              ; aligned on a page (src/wild.cfg)
st_qsl:  .res 512               ; f(x) = INT(x * x / 4), low bytes
st_qsh:  .res 512               ;                        high bytes
st_sfl:  .res 256               ; sf * x, x = 0..255 (the hour's latitude)
st_sfh:  .res 256
st_cfl:  .res 256               ; cf * x
st_cfh:  .res 256
st_rowt: .res 512               ; h = number of T[k] <= u, u = up >> 7 = 0..511
st_sin:  .res 141               ; S(i) = min(sin_lo[i], 255), i = 0..140
st_atan: .res 129               ; AT[r], r = 0..128 (from st_atbits)
st_tb:   .res STAR_LIST_MAX     ; pass 1, catalogue order: bucket az >> 4
st_ta:   .res STAR_LIST_MAX     ;                          attr
st_tr:   .res STAR_LIST_MAX     ;                          row
st_cnt:  .res STAR_BUCKETS      ; bucket sizes, then next free entries

.segment STARS_MODULE

.ifndef STARS_BENCH
module_sky_stars:
        ldx     #24             ; the catalogue's head: directory entry 24, $9600
        jsr     mem_fetch
        fld     s_date          ; civil day of the year, as sky_lunar
        fop     FMULT, f_365
        jsr     AYINT
        lda     $A1
        pha
        lda     $A0
        pha
        fld     s_hour          ; minute of the apparent solar day
        fop     FMULT, st_f60
        jsr     AYINT           ; last ROM call: zero page is ours now
        pla
        sta     st_day+1
        pla
        sta     st_day
        lda     $A1
        sta     st_min
        lda     $A0
        sta     st_min+1
        lda     st_min          ; 24 h exactly: minute 0
        cmp     #<1440
        lda     st_min+1
        sbc     #>1440
        bcc     stars_compute
        sta     st_min+1
        lda     st_min
        sbc     #<1440
        sta     st_min
        jmp     stars_compute
st_f60: .byte   $86, $70, 0, 0, 0       ; 60.0, ROM floating point
.endif

; ----------------------------------------------------------------------------
stars_compute:
        ; --- quarter squares: f(0) = 0, f(i) = f(i - 1) + (i >> 1)
        lda     #0
        sta     st_w
        sta     st_w+1
        tax
@qs0:   lda     st_w
        sta     st_qsl,x
        lda     st_w+1
        sta     st_qsh,x
        inx
        beq     @qs1
        txa
        lsr     a
        clc
        adc     st_w
        sta     st_w
        bcc     @qs0
        inc     st_w+1
        bne     @qs0            ; never 0
@qs1:   txa                     ; i = 256 + x: i >> 1 = 128 + (x >> 1)
        lsr     a
        ora     #$80
        clc
        adc     st_w
        sta     st_w
        bcc     :+
        inc     st_w+1
:       lda     st_w
        sta     st_qsl+256,x
        lda     st_w+1
        sta     st_qsh+256,x
        inx
        bne     @qs1
        ; --- S(i), i = 0..140
        ldx     #0
@sin:   lda     #255
        cpx     #SIN_UNIT_START
        bcs     :+
        lda     sin_lo,x
:       sta     st_sin,x
        inx
        cpx     #141
        bcc     @sin
        ; --- AT[r] = AT[r - 1] + bit r - 1 of st_atbits, r = 1..128
        lda     #0
        sta     st_t
        sta     st_atan
        tax                     ; r - 1
@atb:   txa
        and     #7
        bne     :+
        txa
        lsr     a
        lsr     a
        lsr     a
        tay
        lda     st_atbits,y
        sta     st_m
:       lsr     st_m
        lda     st_t
        adc     #0
        sta     st_t
        sta     st_atan+1,x
        inx
        bpl     @atb            ; r - 1 = 0..127
        ; --- row table: h(u) = number of T[k] <= u (T[k] >= 256 from STAR_T_HIGH)
        ldx     #0              ; k
        ldy     #0              ; u = 0..255
@rt0:   cpx     #STAR_T_HIGH
        bcs     @rs0
        tya
        cmp     st_t9,x
        bcc     @rs0
        inx
        bne     @rt0
@rs0:   txa
        sta     st_rowt,y
        iny
        bne     @rt0
@rt1:   cpx     #STAR_H_MAX     ; u = 256 + Y
        bcs     @rs1
        cpx     #STAR_T_HIGH
        bcc     @ri1            ; T[k] < 256 <= u
        tya
        cmp     st_t9,x
        bcc     @rs1
@ri1:   inx
        bne     @rt1
@rs1:   txa
        sta     st_rowt+256,y
        iny
        bne     @rt1

        ; --- LST16 = C(day) + Tsid(minute) - (lon >> 1)
        lda     st_day+1
        lsr     a
        lda     st_day
        ror     a
        lsr     a
        lsr     a
        tax                     ; i = day >> 3
        lda     st_day
        and     #7
        pha
        sec
        lda     st_c_lo+1,x     ; diff = C[i+1] - C[i] (< 4096)
        sbc     st_c_lo,x
        sta     st_w
        lda     st_c_hi+1,x
        sbc     st_c_hi,x
        sta     st_w+1
        pla
        jsr     mul16x8         ; diff * (day & 7) < 28672
        ldy     #3
:       lsr     st_q+1
        ror     st_q
        dey
        bne     :-
        clc
        lda     st_c_lo,x
        adc     st_q
        sta     st_lst
        lda     st_c_hi,x
        adc     st_q+1
        sta     st_lst+1
        lda     st_min          ; minute * 45 + (minute * 163 >> 8)
        sta     st_w
        lda     st_min+1
        sta     st_w+1
        lda     #163
        jsr     mul16x8
        lda     st_q+1
        sta     st_t
        lda     st_q+2
        sta     st_t+1
        lda     #45
        jsr     mul16x8
        clc
        lda     st_q
        adc     st_t
        sta     st_t
        lda     st_q+1
        adc     st_t+1
        sta     st_t+1
        clc
        lda     st_lst
        adc     st_t
        sta     st_lst
        lda     st_lst+1
        adc     st_t+1
        sta     st_lst+1
        lda     MAP+25          ; lon >> 1, arithmetic (floor)
        cmp     #$80
        ror     a
        sta     st_t
        ldy     #0
        and     #$80
        beq     :+
        dey
:       sty     st_t+1
        sec
        lda     st_lst
        sbc     st_t
        sta     st_lst
        lda     st_lst+1
        sbc     st_t+1
        sta     st_lst+1
        ; LSTq = ((LST16 * 35 + 512) >> 10) mod 2240 (only 2240 wraps)
        lda     st_lst
        sta     st_w
        lda     st_lst+1
        sta     st_w+1
        lda     #35
        jsr     mul16x8
        clc
        lda     st_q+1
        adc     #>512
        sta     st_q+1
        lda     st_q+2
        adc     #0
        lsr     a
        ror     st_q+1
        lsr     a
        ror     st_q+1
        sta     st_lq+1
        lda     st_q+1
        sta     st_lq
        sec
        sbc     #<2240
        tax
        lda     st_lq+1
        sbc     #>2240
        bcc     :+
        sta     st_lq+1
        stx     st_lq
:
        ; --- latitude: lat_u = (|lat| * 199 + 66) >> 7, sf, cf
        lda     M_LAT
        and     #$80
        sta     st_fneg
        lda     M_LAT
        bpl     :+
        eor     #$FF
        clc
        adc     #1
:       ldy     #199
        jsr     mul8
        clc
        lda     st_p
        adc     #66
        sta     st_p
        lda     st_p+1
        adc     #0
        asl     st_p
        rol     a
        sta     st_t
        sta     st_latu
        tax
        lda     st_sin,x
        sta     st_sf
        bne     :+
        sta     st_fneg         ; zero is positive
:       lda     #140
        sec
        sbc     st_t
        tax
        lda     st_sin,x
        sta     st_cf
        ; products of the hour: sf * x and cf * x, x = 0..255
        lda     #0
        sta     st_w
        sta     st_w+1
        sta     st_t
        sta     st_t+1
        tax
@pt:    lda     st_w
        sta     st_sfl,x
        lda     st_w+1
        sta     st_sfh,x
        lda     st_t
        sta     st_cfl,x
        lda     st_t+1
        sta     st_cfh,x
        clc
        lda     st_w
        adc     st_sf
        sta     st_w
        bcc     :+
        inc     st_w+1
        clc
:       lda     st_t
        adc     st_cf
        sta     st_t
        bcc     :+
        inc     st_t+1
:       inx
        bne     @pt

        ; --- pass 1: the visible stars in catalogue order
        lda     #0
        sta     st_n
        sta     st_k
        sta     st_k+1
        lda     #<st_cat
        sta     st_cp
        lda     #>st_cat
        sta     st_cp+1

; ----------------------------------------------------------------------------
st_star:
        lda     st_k
        cmp     #<STAR_COUNT
        lda     st_k+1
        sbc     #>STAR_COUNT
        bcc     :+
        jmp     st_sort
:       ldy     #2
        lda     (st_cp),y
        sta     st_du
        dey
        lda     (st_cp),y
        sta     st_b1
        and     #$80
        sta     st_dneg
        eor     st_fneg
        beq     @rises          ; declination on the latitude's side
        lda     st_du
        clc
        adc     st_latu
        cmp     #141
        bcc     @rises
        jmp     st_skip         ; never rises: up <= 0 at every H
        ; hour angle H = (((LSTq - RAq) mod 2240) + 2) >> 2, 0..560
@rises: dey
        sec
        lda     st_lq
        sbc     (st_cp),y
        sta     st_hl
        lda     st_b1
        and     #$0F
        sta     st_t
        lda     st_lq+1
        sbc     st_t
        bcs     @hapos
        tax                     ; negative: + 2240 (carry clear)
        lda     st_hl
        adc     #<2240
        sta     st_hl
        txa
        adc     #>2240
@hapos: tax
        lda     st_hl
        clc
        adc     #2
        sta     st_hl
        txa
        adc     #0
        lsr     a
        ror     st_hl
        lsr     a
        ror     st_hl
        ; quadrant q and i = H - 140 q (H = 256 hh + hl; 560 wraps to 0)
        tay
        beq     @h0
        dey
        bne     @h2
        lda     st_hl           ; H = 256..511
        cmp     #280-256
        bcc     @q1
        cmp     #420-256
        bcc     @q2
        sbc     #420-256        ; carry set
        ldy     #3
        bne     @got
@q2:    sbc     #280-256-1      ; carry clear: - 24
        ldy     #2
        bne     @got
@q1:    adc     #256-140        ; carry clear
        ldy     #1
        bne     @got
@h0:    lda     st_hl           ; H = 0..255
        cmp     #140
        bcc     @got            ; Y = 0
        sbc     #140
        iny
        bne     @got
@h2:    lda     st_hl           ; H = 512..560
        ldy     #3
        cmp     #560-512
        bcs     @wrap
        adc     #512-420        ; carry clear
        bne     @got
@wrap:  lda     #0
        tay
@got:   sty     st_quad
        sta     st_hl
        tax
        lda     st_sin,x
        sta     st_s            ; S(i)
        lda     #140
        sec
        sbc     st_hl
        tax
        lda     st_sin,x        ; S(140 - i)
        tay
        ldx     st_quad
        txa
        lsr     a
        bcc     @even
        sty     st_smag         ; odd quadrant: sin = c, cos = s
        lda     st_s
        sta     st_cmag
        jmp     @signs
@even:  lda     st_s
        sta     st_smag
        sty     st_cmag
@signs: lda     q_sinneg,x
        ldy     st_smag
        bne     :+
        lda     #0
:       sta     st_sneg
        lda     q_cosneg,x
        ldy     st_cmag
        bne     :+
        lda     #0
:       sta     st_cneg

        ; declination: sd (signed: st_dneg from the record), cd
        ldx     st_du
        lda     st_sin,x
        sta     st_sd
        bne     :+
        sta     st_dneg
:       lda     #140
        sec
        sbc     st_du
        tax
        lda     st_sin,x
        sta     st_cd
        ldy     st_cmag         ; cdcH = (cd * |cos H| + 128) >> 8
        jsr     mul8
        lda     st_p
        cmp     #$80
        lda     st_p+1
        adc     #0
        sta     st_cdch

        ; up = sf * sd + cf * cdcH (24-bit signed)
        ldy     st_sd             ; sf * sd: table of the hour
        lda     st_sfl,y
        sta     st_p
        lda     st_sfh,y
        sta     st_p+1
        lda     st_fneg
        eor     st_dneg
        ldx     #0
        jsr     setp
        ldy     st_cdch             ; cf * cdch: table of the hour
        lda     st_cfl,y
        sta     st_p
        lda     st_cfh,y
        sta     st_p+1
        lda     st_cneg
        ldx     #0
        jsr     addp
        lda     st_acc+2
        beq     :+
        jmp     st_skip         ; negative, or >= 65536 (above the view)
:       lda     st_acc
        ora     st_acc+1
        bne     :+
        jmp     st_skip         ; on the horizon
        ; h = number of T[k] <= up >> 7 (table st_rowt), row = 95 - h
:       lda     st_acc
        asl     a
        lda     st_acc+1
        rol     a
        tax
        bcs     :+
        lda     st_rowt,x
        bcc     @bsdone
:       lda     st_rowt+256,x
@bsdone:
        cmp     #STAR_H_MAX
        bcc     :+
        jmp     st_skip         ; row < 16: above the view
:       eor     #$FF            ; 95 - h
        sec
        adc     #95
        sta     st_rowv

        ; N = cf * sd - sf * cdcH, |E| = cd * |sin H|
        ldy     st_sd             ; cf * sd: table of the hour
        lda     st_cfl,y
        sta     st_p
        lda     st_cfh,y
        sta     st_p+1
        lda     st_dneg
        ldx     #3
        jsr     setp
        ldy     st_cdch             ; sf * cdch: table of the hour
        lda     st_sfl,y
        sta     st_p
        lda     st_sfh,y
        sta     st_p+1
        lda     st_fneg
        eor     st_cneg
        eor     #$80
        ldx     #3
        jsr     addp
        lda     st_cd
        ldy     st_smag
        jsr     mul8
        lda     st_p
        sta     st_e
        lda     st_p+1
        sta     st_e+1
        lda     #0              ; E < 0 when sin H > 0 (west of the meridian)
        ldy     st_smag
        beq     :+
        ldy     st_sneg
        bne     :+
        lda     #$80
:       sta     st_eneg
        lda     st_acc+5
        and     #$80
        sta     st_nneg
        beq     :+
        sec                     ; |N|
        lda     #0
        sbc     st_acc+3
        sta     st_acc+3
        lda     #0
        sbc     st_acc+4
        sta     st_acc+4
        lda     #0
        sbc     st_acc+5
        sta     st_acc+5
:       lda     st_acc+5
        beq     :+
        lsr     st_acc+5        ; |N| >= 65536: halve both
        ror     st_acc+4
        ror     st_acc+3
        lsr     st_e+1
        ror     st_e
:       jsr     st_atan2
        sta     st_t            ; a' = 0..140, angle from north toward east
        bit     st_eneg
        bmi     @west
        bit     st_nneg
        bmi     @se
        lda     st_t            ; NE: a'
        ldx     #0
        beq     @az
@se:    lda     #<280           ; SE: 280 - a'
        sec
        sbc     st_t
        ldx     #>280
        bcs     @az
        dex
        bcc     @az
@west:  bit     st_nneg
        bpl     @nw
        lda     #<280           ; SW: 280 + a'
        clc
        adc     st_t
        ldx     #>280
        bcc     @az
        inx
        bcs     @az
@nw:    lda     st_t            ; NW: (560 - a') mod 560
        beq     @az0
        lda     #<560
        sec
        sbc     st_t
        ldx     #>560
        bcs     @az
        dex
        bcc     @az
@az0:   tax
@az:    sta     st_azl
        stx     st_azhh

        ; Moon: hidden by its outer disc (sky_column rows y - half..y + half)
        lda     sky_y
        cmp     #96
        bcs     st_append
        sec
        lda     st_azl          ; d = (az - sky_bearing + 5) mod 560
        sbc     sky_bearing
        sta     st_dl
        lda     st_azhh
        sbc     sky_bearing+1
        sta     st_dh
        clc
        lda     st_dl
        adc     #5
        sta     st_dl
        lda     st_dh
        adc     #0
        sta     st_dh
        bpl     @dpos
        clc                     ; negative: + 560
        lda     st_dl
        adc     #<560
        sta     st_dl
        lda     st_dh
        adc     #>560
        sta     st_dh
        jmp     @dchk
@dpos:  cmp     #>560           ; 560..564 -> 0..4
        bne     @dchk
        lda     st_dl
        cmp     #<560
        bcc     @dchk
        sbc     #<560
        sta     st_dl
        lda     #0
        sta     st_dh
@dchk:  lda     st_dh
        bne     st_append
        ldx     st_dl
        cpx     #11
        bcs     st_append
        lda     st_rowv
        sec
        sbc     sky_y
        bpl     :+
        eor     #$FF
        clc
        adc     #1
:       cmp     sky_outer,x
        bcs     :+
        jmp     st_skip         ; |row - sky_y| < half
:       bne     st_append
        jmp     st_skip         ; = half: the disc's last row

        ; append: bucket, attr = class << 6 | tint << 4 | az & 15, row
st_append:
        ldx     st_n
        lda     st_azhh         ; bucket = az >> 4
        asl     a
        asl     a
        asl     a
        asl     a
        sta     st_t
        lda     st_azl
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        ora     st_t
        sta     st_tb,x
        lda     st_rowv
        sta     st_tr,x
        lda     st_k+1          ; class from the index (catalogue order)
        bne     @faint
        ldy     st_k
        cpy     #STAR_PRIO
        bcs     :+
        lda     st_prio_cls,y
        bcc     @cls            ; carry still clear
:       lda     #$00
        cpy     #STAR_K1
        bcc     @cls
        lda     #$40
        cpy     #STAR_K2
        bcc     @cls
@faint: lda     #$80
@cls:   sta     st_t
        lda     st_b1           ; tint
        and     #$30
        ora     st_t
        sta     st_t
        lda     st_azl
        and     #$0F
        ora     st_t
        sta     st_ta,x
        inx
        stx     st_n
        cpx     #STAR_LIST_MAX
        beq     st_sort
st_skip:
        clc
        lda     st_cp
        adc     #3
        sta     st_cp
        bcc     :+
        inc     st_cp+1
:       inc     st_k
        bne     :+
        inc     st_k+1
:       jmp     st_star

; ----------------------------------------------------------------------------
; Stable counting sort by bucket into the resident list; bucket starts,
; st_bucket+35 = count; unused entries 0.
st_sort:
        ldx     #STAR_BUCKETS-1
        lda     #0
:       sta     st_cnt,x
        dex
        bpl     :-
        ldx     #0
@count: cpx     st_n
        bcs     @list
        ldy     st_tb,x
        lda     st_cnt,y
        clc
        adc     #1
        sta     st_cnt,y
        inx
        bne     @count
@list:
.ifdef STARS_LIST_LC
        php
        sei
        bit     $C083           ; main language card, bank 2: read and write RAM
        bit     $C083
.endif
        lda     #0
        sta     st_t
        tax
@start: lda     st_t            ; start of bucket x, and its next free entry
        sta     st_bucket,x
        ldy     st_cnt,x
        sta     st_cnt,x
        tya
        clc
        adc     st_t
        sta     st_t
        inx
        cpx     #STAR_BUCKETS-1
        bcc     @start
        lda     st_t
        sta     st_bucket,x     ; count
        ldx     #STAR_LIST_MAX
        lda     #0
:       sta     st_a-1,x
        sta     st_row-1,x
        dex
        bne     :-
@scatter:
        cpx     st_n
        bcs     @done
        ldy     st_tb,x
        lda     st_cnt,y
        sta     st_t
        clc
        adc     #1
        sta     st_cnt,y
        ldy     st_t
        lda     st_ta,x
        sta     st_a,y
        lda     st_tr,x
        sta     st_row,y
        inx
        bne     @scatter
@done:
.ifdef STARS_LIST_LC
        bit     $C082           ; ROM again, write protected
        plp
.endif
        rts

; ----------------------------------------------------------------------------
; st_atan2 -- A = angle from north toward east of (|E| = st_e, |N| =
; st_acc+3/4), both < 65536: AT[r], r = (floor(small * 256 / large) + 1) >> 1
; (128 when equal), 140 - AT when |E| > |N|.
st_atan2:
        lda     st_acc+3
        cmp     st_e
        lda     st_acc+4
        sbc     st_e+1
        bcs     @ele            ; |N| >= |E|
        lda     st_acc+3
        sta     st_rem
        lda     st_acc+4
        sta     st_rem+1
        lda     st_e
        sta     st_large
        lda     st_e+1
        sta     st_large+1
        lda     #$80
        bne     @flip
@ele:   lda     st_e
        sta     st_rem
        lda     st_e+1
        sta     st_rem+1
        lda     st_acc+3
        sta     st_large
        lda     st_acc+4
        sta     st_large+1
        lda     #0
@flip:  sta     st_flip
        lda     st_large
        ora     st_large+1
        beq     @zero
        lda     st_rem
        cmp     st_large
        bne     @divide
        lda     st_rem+1
        cmp     st_large+1
        bne     @divide
        lda     #128
        bne     @ratio
@divide:
        lda     #0
        sta     st_qq
        ldy     #8
        lda     st_rem+1        ; A = remainder, high byte
@bit:   asl     st_rem
        rol     a
        bcs     @take           ; 17-bit remainder: above the divisor
        cmp     st_large+1
        bcc     @no             ; carry 0: quotient bit 0
        bne     @take
        ldx     st_rem
        cpx     st_large
        bcc     @no
@take:  tax                     ; carry set
        lda     st_rem
        sbc     st_large
        sta     st_rem
        txa
        sbc     st_large+1
        sec                     ; quotient bit 1
@no:    rol     st_qq
        dey
        bne     @bit
        lda     st_qq
        clc
        adc     #1
        ror     a               ; (q + 1) >> 1, 9-bit sum
@ratio: tax
        lda     st_atan,x
        bit     st_flip
        bpl     @rts
        sta     st_t
        lda     #140
        sec
        sbc     st_t
@rts:   rts
@zero:  lda     #0
        rts

; ----------------------------------------------------------------------------
; mul8 -- st_p = A * Y (unsigned 8 x 8) = f(a + b) - f(|a - b|), quarter
; squares (st_qsl/st_qsh). Clobbers X, Y.
mul8:   sty     st_m
        sta     st_a8
        sec
        sbc     st_m
        bcs     :+
        eor     #$FF            ; b > a: |a - b| (carry clear)
        adc     #1
:       tax
        lda     st_a8
        clc
        adc     st_m
        tay
        bcs     @high           ; a + b >= 256
        lda     st_qsl,y
        sec
        sbc     st_qsl,x
        sta     st_p
        lda     st_qsh,y
        sbc     st_qsh,x
        sta     st_p+1
        rts
@high:  lda     st_qsl+256,y    ; carry set
        sbc     st_qsl,x
        sta     st_p
        lda     st_qsh+256,y
        sbc     st_qsh,x
        sta     st_p+1
        rts

; mul16x8 -- st_q (24 bits) = st_w * A. Preserves X.
mul16x8:
        sta     st_m
        lda     #0
        sta     st_q
        sta     st_q+1
        sta     st_q+2
        sta     st_u+2
        lda     st_w
        sta     st_u
        lda     st_w+1
        sta     st_u+1
@loop:  lsr     st_m
        bcc     :+
        clc
        lda     st_q
        adc     st_u
        sta     st_q
        lda     st_q+1
        adc     st_u+1
        sta     st_q+1
        lda     st_q+2
        adc     st_u+2
        sta     st_q+2
:       lda     st_m
        beq     @rts
        asl     st_u
        rol     st_u+1
        rol     st_u+2
        jmp     @loop
@rts:   rts

; setp -- st_acc+X (24 bits) = st_p (A bit 7 clear) or -st_p (set).
setp:   asl     a
        bcs     @neg
        lda     st_p
        sta     st_acc,x
        lda     st_p+1
        sta     st_acc+1,x
        lda     #0
        sta     st_acc+2,x
        rts
@neg:   lda     #0              ; carry set
        sbc     st_p
        sta     st_acc,x
        lda     #0
        sbc     st_p+1
        sta     st_acc+1,x
        lda     #0
        sbc     #0
        sta     st_acc+2,x
        rts

; addp -- st_acc+X (24 bits) += st_p (A bit 7 clear) or -= st_p (set).
addp:   asl     a
        bcs     @sub
        lda     st_acc,x
        adc     st_p
        sta     st_acc,x
        lda     st_acc+1,x
        adc     st_p+1
        sta     st_acc+1,x
        lda     st_acc+2,x
        adc     #0
        sta     st_acc+2,x
        rts
@sub:   lda     st_acc,x
        sbc     st_p
        sta     st_acc,x
        lda     st_acc+1,x
        sbc     st_p+1
        sta     st_acc+1,x
        lda     st_acc+2,x
        sbc     #0
        sta     st_acc+2,x
        rts

q_sinneg: .byte 0, 0, $80, $80
q_cosneg: .byte 0, $80, $80, 0

        .include "stars_tables.inc"     ; build/, tools/genstars.py
.assert st_cat2 = st_cat + 3 * STAR_CAT_HEAD, error, "catalogue: head and rest must be contiguous"

stars_module_end:
