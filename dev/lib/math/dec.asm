; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; dec.asm -- binary to decimal, no output device
; ============================================================================
;   byte_to_dec  A = 0..255 -> X = hundreds, Y = tens, A = units (0..9 each,
;                not ASCII). No memory used. ~30..110 cycles.
;   byte_div10   A = 0..255 -> Y = A / 10 (0..25), A = A mod 10. Keeps X.
;   u16_to_dec   dec_lo/dec_hi = 0..65535 -> ASCII digits at (dec_ptr), no
;                leading zeros ("0" for 0), then a NUL. Y = digit count
;                (1..5). Consumes dec_lo/dec_hi; clobbers A, X, dec_t, dec_d.
;                ~250..900 cycles.
;
; Repeated subtraction of the powers of ten: no division runtime, no table
; beyond the four powers. Both NMOS-safe, D = 0.
; Zero page of u16_to_dec: dec_lo, dec_hi, dec_ptr (2), dec_t, dec_d. Each is
; allocated here unless the program defined the name before the include
; (hgrc aliases them onto _hgr_u_lo/_hi/_ptr and the cc65 tmp bytes).
; Include after the callers (.ifref). No file guard: a second include (e.g.
; print_num.asm's, then the program's own) assembles what is newly
; referenced, never a routine twice. Users: print_num.asm (print_byte_dec),
; maze3d (HUD digits), hgrc hgr_utoa_asm.s (hgr_utoa, gfx_utoa).
; ============================================================================

.if .referenced(byte_to_dec) .or .referenced(byte_div10)
.ifndef byte_div10
.segment "CODE"
byte_to_dec:
        LDX     #$FF
        SEC
@h:     INX
        SBC     #100
        BCS     @h
        ADC     #100            ; C = 0: undo the last subtraction
byte_div10:
        LDY     #$FF
        SEC
@t:     INY
        SBC     #10
        BCS     @t
        ADC     #10
        RTS
.endif
.endif

.ifref u16_to_dec
.ifndef u16_to_dec
.segment "ZEROPAGE"
.ifndef dec_lo
dec_lo:  .res 1
.endif
.ifndef dec_hi
dec_hi:  .res 1
.endif
.ifndef dec_ptr
dec_ptr: .res 2
.endif
.ifndef dec_t
dec_t:   .res 1
.endif
.ifndef dec_d
dec_d:   .res 1
.endif
.segment "CODE"
u16_to_dec:
        LDX     #0              ; power index: 10000, 1000, 100, 10
        LDY     #0              ; output index, nonzero once a digit is out
@pw:    LDA     #'0'
        STA     dec_d
        SEC
@sub:   LDA     dec_lo          ; value -= power while it fits
        SBC     dec_pw_lo,X
        STA     dec_t
        LDA     dec_hi
        SBC     dec_pw_hi,X
        BCC     @digit
        STA     dec_hi
        LDA     dec_t
        STA     dec_lo
        INC     dec_d
        BCS     @sub            ; C still set
@digit: LDA     dec_d
        CPY     #0
        BNE     @emit
        CMP     #'0'
        BEQ     @skip           ; leading zero
@emit:  STA     (dec_ptr),Y
        INY
@skip:  INX
        CPX     #4
        BNE     @pw
        LDA     dec_lo          ; units, always written
        ORA     #'0'
        STA     (dec_ptr),Y
        INY
        LDA     #0
        STA     (dec_ptr),Y
        RTS
dec_pw_lo: .byte <10000, <1000, <100, <10
dec_pw_hi: .byte >10000, >1000, >100, >10
.endif
.endif
