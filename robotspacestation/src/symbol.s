; Robot Space Station — the gates' schematic symbols (AND, OR, XOR, NOT)
; on the board (src/board_ui.c draw_part): 16 x 13 colour pixels with
; their leads, inputs on rows 3 and 10 (NOT: 6), the output on row 6.
; Rows 0-6 are stored, bit 15 the left pixel; rows 7-12 mirror rows 5-0.
; Each row's runs of set bits are drawn as one-row rectangles.
.setcpu "65C02"
.import _dhgr_fill_rect, pusha
.export _draw_symbol, _sym_x, _sym_y

GREEN = 12

.segment "L8DATA"
symbols:
        .dbyt $0FE0, $0810, $0808, $F808, $0804, $0804, $0807   ; AND
        .dbyt $0FC0, $0430, $0408, $FC04, $0202, $0202, $0201   ; OR
        .dbyt $27C0, $1230, $1208, $F904, $0902, $0902, $0901   ; XOR
        .dbyt $0800, $0C00, $0B00, $08C0, $0830, $080A, $F80D   ; NOT

.segment "L8CODE"
_sym_x: .byte 0                         ; top left corner
_sym_y: .byte 0
idx:    .byte 0                         ; the row's offset in symbols
row:    .byte 0
bhi:    .byte 0                         ; the row's bits left
blo:    .byte 0
col:    .byte 0
start:  .byte 0                         ; a run's first column

; draw_symbol(g): symbol g (kind - 1) at sym_x, sym_y, in green.
_draw_symbol:
        asl
        sta idx
        asl
        asl
        asl
        sec
        sbc idx                         ; g * 14
        sta idx
        stz row
@row:   ldx idx
        lda symbols,x
        sta bhi
        lda symbols+1,x
        sta blo
        stz col
@bit:   lda bhi
        ora blo
        beq @next
        bit bhi
        bmi @run
        jsr shift
        bra @bit
@run:   lda col
        sta start
@more:  jsr shift
        bit bhi
        bmi @more
        lda row
        jsr fill
        lda #12
        sec
        sbc row
        jsr fill
        bra @bit
@next:  inc idx
        inc idx
        inc row
        lda row
        cmp #7
        bne @row
        rts

shift:  inc col
        asl blo
        rol bhi
        rts

; The run start..col-1 on row A of the symbol.
fill:   clc
        adc _sym_y
        pha
        lda _sym_x
        clc
        adc start
        jsr pusha
        pla
        jsr pusha
        lda col
        sec
        sbc start
        jsr pusha
        lda #1
        jsr pusha
        lda #GREEN
        jmp _dhgr_fill_rect
