; GPL-3.0. Extracted from Light3DBall: exact 7-bit multiply and depth tables.
; Include once in an ASM translation unit linked with the C caller.
; A/X = unsigned 16-bit distance for select. x/y: A=0..127, result A/X=byte/0.
; All entries destroy A/X/flags; x/y preserve Y, select destroys Y only when
; PC_DEPTH_SHIFT is neither 0 nor 1. I/D unchanged, no bank/video changes.
; Tables: 256 immutable bytes each in main RAM, maximum span 255.
; Select index=min(distance >> PC_DEPTH_SHIFT,255), shift 0..8 (default 1).
; Centers fixed at build time; table spans must keep each output in 0..255.
; Non-reentrant, outside IRQs. Default scratch: 1 ZP byte + 5 BSS bytes.
; PC_BITS/SX/SY/LEFT/TOP/DEPTH aliases borrow the caller's existing scratch.
; PC_TABLE_X/Y aliases choose tables; defaults import _corridor_scale_x/y.
.ifndef _PERSPECTIVE_CORRIDOR_LOADED_
_PERSPECTIVE_CORRIDOR_LOADED_ = 1
.ifndef PC_CENTER_X
PC_CENTER_X = 128
.endif
.ifndef PC_CENTER_Y
PC_CENTER_Y = 80
.endif
.ifndef PC_DEPTH_SHIFT
PC_DEPTH_SHIFT = 1
.endif
.assert PC_CENTER_X >= 0 .and PC_CENTER_X <= 255, error, "PC_CENTER_X must be 0..255"
.assert PC_CENTER_Y >= 0 .and PC_CENTER_Y <= 255, error, "PC_CENTER_Y must be 0..255"
.assert PC_DEPTH_SHIFT >= 0 .and PC_DEPTH_SHIFT <= 8, error, "PC_DEPTH_SHIFT must be 0..8"
.ifndef PC_TABLE_X
.import _corridor_scale_x
PC_TABLE_X = _corridor_scale_x
.endif
.ifndef PC_TABLE_Y
.import _corridor_scale_y
PC_TABLE_Y = _corridor_scale_y
.endif
.zeropage
.ifndef PC_BITS
PC_BITS: .res 1
.endif
.bss
.ifndef PC_SX
PC_SX: .res 1
.endif
.ifndef PC_SY
PC_SY: .res 1
.endif
.ifndef PC_LEFT
PC_LEFT: .res 1
.endif
.ifndef PC_TOP
PC_TOP: .res 1
.endif
.ifndef PC_DEPTH
PC_DEPTH: .res 1
.endif
.export _a2_corridor_x, _a2_corridor_y, _a2_corridor_select
.export _a2_corridor_sx, _a2_corridor_sy
.export _a2_corridor_left, _a2_corridor_top, _a2_corridor_depth
_a2_corridor_sx = PC_SX
_a2_corridor_sy = PC_SY
_a2_corridor_left = PC_LEFT
_a2_corridor_top = PC_TOP
_a2_corridor_depth = PC_DEPTH
.code
; floor(value*span/128), exactly as the original Light3DBall renderer.
.macro PC_PROJECT name, scale, origin
name:
    sta PC_BITS
    lda #0
    ldx #7
@multiply:
    lsr PC_BITS
    bcc @shift
    clc
    adc scale
@shift:
    ror a
    dex
    bne @multiply
    clc
    adc origin
    rts
.endmacro
PC_PROJECT _a2_corridor_x, PC_SX, PC_LEFT
PC_PROJECT _a2_corridor_y, PC_SY, PC_TOP

_a2_corridor_select:
.if PC_DEPTH_SHIFT = 1
    ; Preserve the original instruction sequence for the common case.
    cpx #2
    bcs @far
    stx PC_BITS
    lsr PC_BITS
    ror a
    tax
    jmp @lookup
.elseif PC_DEPTH_SHIFT = 0
    cpx #0
    bne @far
    tax
    jmp @lookup
.else
    stx PC_BITS
    ldy #PC_DEPTH_SHIFT
@divide:
    lsr PC_BITS
    ror a
    dey
    bne @divide
    tax
    lda PC_BITS
    bne @far
    jmp @lookup
.endif
@far:
    ldx #255
@lookup:
    stx PC_DEPTH
    lda PC_TABLE_X,x
    sta PC_SX
    lsr a
    eor #255
    clc
    adc #<(PC_CENTER_X+1)
    sta PC_LEFT
    lda PC_TABLE_Y,x
    sta PC_SY
    lsr a
    eor #255
    clc
    adc #<(PC_CENTER_Y+1)
    sta PC_TOP
    rts
.endif
