; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; math.inc -- zero page and macros of lib/math (include it at the top)
; ============================================================================
; lib/math is split like the other libraries, so that every access to its
; zero page is assembled as zero page:
;   math.inc    (this file) at the TOP of the program: the zero-page operands,
;               the table addresses and the MUL_K16 / MUL_KS16 macros;
;   mul.asm, sqrt.asm, div.asm, random.asm at the END: the routines, assembled
;               only when referenced before the include (.ifref), in any
;               order (sqrt.asm only reads the tables, through math.inc).
;
; Zero page (13 bytes, +3 with MUL_ACC):
;   mul_x  (2)  16-bit operand (unsigned or signed, by routine)
;   mul_y  (1)  8-bit operand
;   mul_p0..mul_p2  24-bit product, little endian
;   mul_t       scratch
;   mul_s1l, mul_s1h, mul_s2l, mul_s2h (2 each) table pointers. Their high
;               bytes are set once by mul_init; each product only stores
;               mul_y into the four low bytes.
;   mul_acc0..mul_acc2  only with MUL_ACC = 1: sum of products
; Each slot is skipped if the program defined the name before the include
; (alias onto its own scratch). With zp.inc included first, mul_t and
; mul_p0 are its mul_tmp / mul_res0 (11 bytes of our own then).
;
; Tables (2 KB, mul_init builds them at start, nothing on the disk):
;   mul_sqr1_lo/hi[x] = floor(x*x/4), x = 0..511
;   mul_sqr2_lo/hi[x] = mul_sqr1[|x-255|]
; Define MUL_TABLES = their address (page aligned, 2 KB) before this include:
; e.g. $0800, the HELLO area of a BRUN program that never returns to BASIC,
; or a free 2 KB of LOWBSS / the unused HGR page. A fixed address because a
; .align 256 inside BSS is only right if the linker config aligns BSS.
;
; Quarter squares: a*b = floor((a+b)^2/4) - floor((a-b)^2/4), exact.
; ============================================================================

.ifndef _MATH_INC_LOADED_
_MATH_INC_LOADED_ = 1

.ifndef MUL_ACC                         ; 1 = on, 0 or undefined = off
MUL_ACC = 0
.endif

.segment "ZEROPAGE"
.ifdef _ZP_INC_LOADED_                  ; zp.inc's multiply slots, if it is in
.ifndef mul_t
mul_t    = mul_tmp
.endif
.ifndef mul_p0
mul_p0   = mul_res0
.endif
.endif
.ifndef mul_x
mul_x:   .res 2
.endif
.ifndef mul_y
mul_y:   .res 1
.endif
.ifndef mul_p0
mul_p0:  .res 1
.endif
.ifndef mul_p1
mul_p1:  .res 1
.endif
.ifndef mul_p2
mul_p2:  .res 1
.endif
.ifndef mul_t
mul_t:   .res 1
.endif
.ifndef mul_s1l
mul_s1l: .res 2
.endif
.ifndef mul_s1h
mul_s1h: .res 2
.endif
.ifndef mul_s2l
mul_s2l: .res 2
.endif
.ifndef mul_s2h
mul_s2h: .res 2
.endif
.if MUL_ACC
.ifndef mul_acc0
mul_acc0: .res 1
.endif
.ifndef mul_acc1
mul_acc1: .res 1
.endif
.ifndef mul_acc2
mul_acc2: .res 1
.endif
.endif

.ifndef MUL_TABLES
.error "math.inc: define MUL_TABLES (page-aligned 2 KB) before the include"
.endif
.ifdef MUL_TABLES
.assert <MUL_TABLES = 0, error, "MUL_TABLES must be page aligned"
mul_sqr1_lo = MUL_TABLES
mul_sqr1_hi = MUL_TABLES + $200
mul_sqr2_lo = MUL_TABLES + $400
mul_sqr2_hi = MUL_TABLES + $600
.endif

.segment "CODE"

; ----------------------------------------------------------------------------
; MUL_K16 k -- mul_p0..p2 = mul_x (unsigned) * k, k a constant 0..255.
; The tables are read at fixed offsets (sqr1 + k, sqr2 + 255 - k): no
; pointer to set up, two lookups per byte (PHYSICS's mul_k73...).
; ~60-70 cycles inline, clobbers A, X. The high byte's product comes first
; so the low byte's high half can be added directly, without mul_t.
; MUL_KS16 k -- the same with mul_x signed (-k << 16 corrects a negative x).
; Zero, one and powers of two use smaller/faster table-free shifts.
; Both macros preserve mul_x, Y and all other math scratch except mul_p0..p2.
; A, X and arithmetic flags NZCV are scratch; I/D are unchanged (enter D=0).
; Signed powers extend the sign while forming the product, without a later
; top-byte correction. No table initialization is needed for these cases.
; ----------------------------------------------------------------------------
; Private shared body for x * 32/64/128 = (x << 8) >> 3/2/1.
; Keep the high byte in A; signed variants repeat its sign bit into carry.
.macro _MUL_K16_RIGHT k, signed
        LDA     mul_x
        STA     mul_p1
        LDA     #0
        STA     mul_p0
        LDA     mul_x+1
        ; k=32/64/128: three/two/one shifts. No local symbol definition:
        ; even a macro-local constant would reset the caller's @label scope.
        .repeat 3 - (k / 64)
                .if signed
                        CMP     #$80
                        ROR     A
                .else
                        LSR     A
                .endif
                ROR     mul_p1
                ROR     mul_p0
        .endrepeat
        STA     mul_p2
.endmacro

.macro MUL_K16 k
        .assert k >= 0 .and k <= 255, error, "MUL_K16: k is 0..255"
        .if k = 0
                LDA     #0
                STA     mul_p0
                STA     mul_p1
                STA     mul_p2
        .elseif k = 1
                LDA     mul_x
                STA     mul_p0
                LDA     mul_x+1
                STA     mul_p1
                LDA     #0
                STA     mul_p2
        .elseif k = 2 .or k = 4 .or k = 8
                ; First shift keeps both input bytes in A, then only
                ; zero to two extra full-width shifts are needed.
                LDA     mul_x
                ASL     A
                STA     mul_p0
                LDA     mul_x+1
                ROL     A
                STA     mul_p1
                LDA     #0
                ROL     A
                STA     mul_p2
                .repeat k / 4           ; k=2/4/8: 0/1/2 further shifts
                        ASL     mul_p0
                        ROL     mul_p1
                        ROL     mul_p2
                .endrepeat
        .elseif k = 16
                ; Four full-width memory shifts would cost more than the
                ; general product. Join the independently shifted nibbles.
                LDA     mul_x
                .repeat 4
                        ASL A
                .endrepeat
                STA     mul_p0
                LDA     mul_x+1
                .repeat 4
                        ASL A
                .endrepeat
                STA     mul_p1
                LDA     mul_x
                .repeat 4
                        LSR A
                .endrepeat
                ORA     mul_p1
                STA     mul_p1
                LDA     mul_x+1
                .repeat 4
                        LSR A
                .endrepeat
                STA     mul_p2
        .elseif k = 32 .or k = 64 .or k = 128
                _MUL_K16_RIGHT k, 0
        .else
        LDX     mul_x+1
        SEC
        LDA     mul_sqr1_lo + (k), X
        SBC     mul_sqr2_lo + 255 - (k), X
        STA     mul_p1
        LDA     mul_sqr1_hi + (k), X
        SBC     mul_sqr2_hi + 255 - (k), X
        STA     mul_p2
        LDX     mul_x                   ; C = 1: exact 16-bit product, no borrow
        LDA     mul_sqr1_lo + (k), X
        SBC     mul_sqr2_lo + 255 - (k), X
        STA     mul_p0
        LDA     mul_sqr1_hi + (k), X
        SBC     mul_sqr2_hi + 255 - (k), X
        CLC
        ADC     mul_p1
        STA     mul_p1
        BCC     :+
        INC     mul_p2
:
        .endif
.endmacro

.macro MUL_KS16 k
        .if k = 1
                LDA     mul_x
                STA     mul_p0
                LDA     mul_x+1
                STA     mul_p1
                LDA     #0
                BIT     mul_x+1
                BPL     :+
                LDA     #$FF
:               STA     mul_p2
        .elseif k = 2 .or k = 4 .or k = 8
                LDA     mul_x
                ASL     A
                STA     mul_p0
                LDA     mul_x+1
                ROL     A
                STA     mul_p1
                LDA     #0
                BCC     :+
                LDA     #$FF
:               STA     mul_p2
                .repeat k / 4
                        ASL     mul_p0
                        ROL     mul_p1
                        ROL     mul_p2
                .endrepeat
        .elseif k = 16
                LDA     mul_x
                .repeat 4
                        ASL A
                .endrepeat
                STA     mul_p0
                LDA     mul_x+1
                .repeat 4
                        ASL A
                .endrepeat
                STA     mul_p1
                LDA     mul_x
                .repeat 4
                        LSR A
                .endrepeat
                ORA     mul_p1
                STA     mul_p1
                LDA     mul_x+1
                .repeat 4
                        LSR A
                .endrepeat
                BIT     mul_x+1
                BPL     :+
                ORA     #$F0
:               STA     mul_p2
        .elseif k = 32 .or k = 64 .or k = 128
                _MUL_K16_RIGHT k, 1
        .else
        MUL_K16 k
        .if k <> 0
        BIT     mul_x+1
        BPL     :+
        SEC
        LDA     mul_p2
        SBC     #(k)
        STA     mul_p2
:
        .endif
        .endif
.endmacro

.endif  ; _MATH_INC_LOADED_
