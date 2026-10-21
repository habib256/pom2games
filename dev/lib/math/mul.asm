; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; mul.asm -- quarter-square products, exact, for fixed-point physics
; ============================================================================
;   mul_init      build the 2 KB of tables (once, at start). ~110 000 cycles.
;                 MUL_INIT_BOOT = 1 before the include puts it in segment
;                 "INIT" (boot code that a buffer overwrites afterwards).
;   mul_u8u8      mul_p0..p1 = mul_x (low byte) * mul_y, unsigned. ~55 cycles
;   mul_u16u8     mul_p0..p2 = mul_x * mul_y, unsigned. ~110 cycles
;   mul_s16s8     mul_p0..p2 = mul_x * mul_y, both signed, exact 24 bits
;   mul_dir       A/X (lo/hi, signed) * Y (signed) -> mul_p0..p2. For
;                 direction components scaled by 64 (64 = 1.0): Y = 0, +64
;                 and -64 take short cuts (~15-50 cycles instead of ~150),
;                 the exact same product (a flat ground normal is (0, -64)).
;                 The short cuts leave mul_x / mul_y as they were.
;   mul_shr6      mul_p1..p2 = floor(mul_p / 64), mod 2^16 (mul_p0 lost)
;   mul_acc_set   mul_acc = mul_p          (MUL_ACC = 1 before math.inc)
;   mul_acc_add   mul_acc += mul_p
;   mul_acc_shr6  mul_p = mul_acc, then mul_shr6
; Constant factors: MUL_K16 / MUL_KS16 (math.inc), inline.
;
; Floor semantics: bytes 1-2 of a two's complement product are floor(p/256);
; mul_shr6 shifts left twice first, so p1:p2 = floor(p/64). A Python model
; (x * y >> 6) matches bit for bit.
;
; How the pointers work: the four pointers' low bytes are mul_y, so with Y
; = a byte of mul_x, (mul_s1l),Y = sqr1[mul_y + Y] and, with Y EOR $FF,
; (mul_s2l),Y = sqr2[mul_y - Y + 255] = sqr1[|mul_y - Y|]. No code is
; patched (the routines may live in ROM-like segments), and both bytes of
; mul_x are plain indexes.
;
; Clobbers A, X, Y (mul_dir: A, Y on its short cuts). .ifref: only the
; routines referenced before the include are assembled; mul_init always is.
; Origin: DIRTBIKE (pointers) and the PHYSICS demo (offset tables, short
; cuts by +-1.0).
; ============================================================================

.ifndef _MUL_ASM_LOADED_
_MUL_ASM_LOADED_ = 1

.segment "CODE"

; low byte of mul_x * mul_y -> mul_p0/p1 (pointers set)
.macro MUL_LOW_BYTE
        LDY     mul_x
        LDA     (mul_s1l),Y
        STA     mul_p0
        LDA     (mul_s1h),Y
        STA     mul_p1
        TYA
        EOR     #$FF
        TAY
        SEC
        LDA     mul_p0
        SBC     (mul_s2l),Y
        STA     mul_p0
        LDA     mul_p1
        SBC     (mul_s2h),Y
        STA     mul_p1
.endmacro

.macro MUL_SET_POINTERS
        LDA     mul_y
        STA     mul_s1l
        STA     mul_s1h
        STA     mul_s2l
        STA     mul_s2h
.endmacro

.ifref mul_acc_shr6
mul_acc_shr6:
        LDA     mul_acc0
        STA     mul_p0
        LDA     mul_acc1
        STA     mul_p1
        LDA     mul_acc2
        STA     mul_p2
        JMP     mul_shr6
.endif

.ifref mul_acc_set
mul_acc_set:
        LDA     mul_p0
        STA     mul_acc0
        LDA     mul_p1
        STA     mul_acc1
        LDA     mul_p2
        STA     mul_acc2
        RTS
.endif

.ifref mul_acc_add
mul_acc_add:
        CLC
        LDA     mul_acc0
        ADC     mul_p0
        STA     mul_acc0
        LDA     mul_acc1
        ADC     mul_p1
        STA     mul_acc1
        LDA     mul_acc2
        ADC     mul_p2
        STA     mul_acc2
        RTS
.endif

.ifref mul_shr6
mul_shr6:
        ASL     mul_p0
        ROL     mul_p1
        ROL     mul_p2
        ASL     mul_p0
        ROL     mul_p1
        ROL     mul_p2
        RTS
.endif

.ifref mul_dir
mul_dir:
        CPY     #$40
        BEQ     @p64
        CPY     #$C0
        BEQ     @m64
        CPY     #0
        BEQ     @zero
        STA     mul_x
        STX     mul_x+1
        STY     mul_y
        JMP     mul_s16s8
@zero:  STY     mul_p0
        STY     mul_p1
        STY     mul_p2
        RTS
@m64:   JSR     @p64                    ; -(x << 6)
        SEC
        LDA     #0
        SBC     mul_p0
        STA     mul_p0
        LDA     #0
        SBC     mul_p1
        STA     mul_p1
        LDA     #0
        SBC     mul_p2
        STA     mul_p2
        RTS
@p64:   STA     mul_p1                  ; x << 6 = (x << 8) >> 2, arithmetic
        LDA     #0
        STA     mul_p0
        TXA
        CMP     #$80
        ROR     A
        ROR     mul_p1
        ROR     mul_p0
        CMP     #$80
        ROR     A
        ROR     mul_p1
        ROR     mul_p0
        STA     mul_p2
        RTS
.endif

; signed: the unsigned product of the two patterns, then the two's
; complement corrections (y < 0: p -= x << 8; x < 0: p -= y << 16)
.ifref mul_s16s8
mul_s16s8:
        JSR     mul_u16u8
        LDA     mul_y
        BPL     @ypos
        SEC
        LDA     mul_p1
        SBC     mul_x
        STA     mul_p1
        LDA     mul_p2
        SBC     mul_x+1
        STA     mul_p2
@ypos:  BIT     mul_x+1
        BPL     @done
        SEC
        LDA     mul_p2
        SBC     mul_y
        STA     mul_p2
@done:  RTS
.endif

.ifref mul_u16u8
mul_u16u8:
        MUL_SET_POINTERS
        MUL_LOW_BYTE
        LDY     mul_x+1                 ; high byte * mul_y -> + p1/p2
        LDA     (mul_s1l),Y
        STA     mul_t
        LDA     (mul_s1h),Y
        STA     mul_p2
        TYA
        EOR     #$FF
        TAY
        SEC
        LDA     mul_t
        SBC     (mul_s2l),Y
        STA     mul_t
        LDA     mul_p2
        SBC     (mul_s2h),Y
        STA     mul_p2
        CLC
        LDA     mul_p1
        ADC     mul_t
        STA     mul_p1
        BCC     @nc
        INC     mul_p2
@nc:    RTS
.endif

.ifref mul_u8u8
mul_u8u8:
        MUL_SET_POINTERS
        MUL_LOW_BYTE
        RTS
.endif

; mul_init -- sqr1[x] = floor(x*x/4) by steps of floor((x+1)/2), x = 0..511;
; sqr2[x] = sqr1[255-x] (x < 256), sqr1[x-255] (x >= 256)
.ifdef MUL_INIT_BOOT
.segment "INIT"
.endif
mul_init:
        LDA     #0
        STA     mul_p0                  ; f = sqr1[x]
        STA     mul_p1
        STA     mul_x                   ; x, 9 bits
        STA     mul_x+1
@s1:    LDY     mul_x
        LDA     mul_x+1
        BNE     @hi
        LDA     mul_p0
        STA     mul_sqr1_lo,Y
        LDA     mul_p1
        STA     mul_sqr1_hi,Y
        JMP     @step
@hi:    LDA     mul_p0
        STA     mul_sqr1_lo+256,Y
        LDA     mul_p1
        STA     mul_sqr1_hi+256,Y
@step:  CLC                             ; f += (x + 1) >> 1
        LDA     mul_x
        ADC     #1
        STA     mul_t
        LDA     mul_x+1
        ADC     #0
        LSR     A
        LDA     mul_t
        ROR     A
        CLC
        ADC     mul_p0
        STA     mul_p0
        BCC     @nc
        INC     mul_p1
@nc:    INC     mul_x
        BNE     @s1
        INC     mul_x+1
        LDA     mul_x+1
        CMP     #2
        BNE     @s1
        LDX     #0
@s2a:   TXA
        EOR     #$FF
        TAY
        LDA     mul_sqr1_lo,Y
        STA     mul_sqr2_lo,X
        LDA     mul_sqr1_hi,Y
        STA     mul_sqr2_hi,X
        INX
        BNE     @s2a
@s2b:   LDA     mul_sqr1_lo+1,X
        STA     mul_sqr2_lo+256,X
        LDA     mul_sqr1_hi+1,X
        STA     mul_sqr2_hi+256,X
        INX
        BNE     @s2b
        LDA     #>mul_sqr1_lo
        STA     mul_s1l+1
        LDA     #>mul_sqr1_hi
        STA     mul_s1h+1
        LDA     #>mul_sqr2_lo
        STA     mul_s2l+1
        LDA     #>mul_sqr2_hi
        STA     mul_s2h+1
        RTS
.segment "CODE"

.endif  ; _MUL_ASM_LOADED_
