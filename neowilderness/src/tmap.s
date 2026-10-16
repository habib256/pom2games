; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; TMAP: separate start-only generator, run at $2000. No engine code here.
; A/X = default seed, Y = difficulty. C set on ESC; C clear to play.
; Scenario pack supplies the header, climate, fauna, colours and tree art.
; ABI v1: $2000 interactive entry; $2003 regenerate from header 48..55.
; $06..$09 are temporary zero page; no auxiliary memory or disk access.
.macpack longbranch
.segment "CODE"
        jmp     tmap_main
        jmp     tmap_generate
MAP = $7000
GRID = MAP+64
PTR = $06
TXT = $08
COUT = $FDED
HOME = $FC58
PRBYTE = $FDDA
KBD = $C000
STROBE = $C010

tmap_main:
        sta     seed
        stx     seed+1
        sty     MAP+22
        lda     #3
        sta     count
@options:
        jsr     HOME
        lda     #<title
        ldx     #>title
        jsr     puts
tmap_count_key:
        jsr     getkey
        cmp     #$9B
        jeq     cancelled
        cmp     #$8D
        beq     @seed
        cmp     #'2'|$80
        beq     @count
        cmp     #'3'|$80
        bne     tmap_count_key
@count: and     #$0F
        sta     count
        ora     #'0'|$80
        jsr     COUT
@seed:  lda     #<seed_prompt
        ldx     #>seed_prompt
        jsr     puts
        lda     seed+1
        jsr     PRBYTE
        lda     seed
        jsr     PRBYTE
        lda     #<seed_edit
        ldx     #>seed_edit
        jsr     puts
        lda     #0
        sta     digits
        sta     typed
        sta     typed+1
tmap_seed_key:
        jsr     getkey
        cmp     #$9B
        jeq     cancelled
        cmp     #$8D
        beq     @enter
        cmp     #$88
        beq     @backspace
        cmp     #$FF
        beq     @backspace
        and     #$7F
        cmp     #'0'
        bcc     tmap_seed_key
        cmp     #'9'+1
        bcc     @decimal
        cmp     #'A'
        bcc     tmap_seed_key
        cmp     #'F'+1
        bcs     tmap_seed_key
        sec
        sbc     #7
@decimal:
        and     #15
        sta     nibble
        lda     digits
        cmp     #4
        bcs     tmap_seed_key
        inc     digits
        ldx     #4
@shift: asl     typed
        rol     typed+1
        dex
        bne     @shift
        lda     typed
        ora     nibble
        sta     typed
        lda     nibble
        jsr     hexchar
        jmp     tmap_seed_key
@backspace:
        lda     digits
        beq     tmap_seed_key
        dec     digits
        ldx     #4
@unshift:
        lsr     typed+1
        ror     typed
        dex
        bne     @unshift
        lda     #$88
        jsr     COUT
        lda     #' '|$80
        jsr     COUT
        lda     #$88
        jsr     COUT
        jmp     tmap_seed_key
@enter: lda     digits
        beq     tmap_generate_ui
        lda     typed
        sta     seed
        lda     typed+1
        sta     seed+1
tmap_generate_ui:
        lda     #'T'
        sta     MAP+48
        lda     #'G'
        sta     MAP+49
        lda     #1              ; generator version
        sta     MAP+51
        lda     seed
        sta     MAP+52
        lda     seed+1
        sta     MAP+53
        lda     count
        sta     MAP+54
        lda     MAP+22
        sta     MAP+55
        jsr     tmap_generate
        jsr     preview
tmap_preview_key:
        jsr     getkey
        cmp     #$9B
        beq     cancelled
        cmp     #'R'|$80
        beq     @reroll
        cmp     #$8D
        bne     tmap_preview_key
        clc
        rts
@reroll:
        inc     seed
        bne     :+
        inc     seed+1
:       jmp     tmap_generate_ui
cancelled:
        sec
        rts

; Deterministic generator. Only seed/count/level are identity inputs.
; Rounded islands have a common navigable latitude, a solid dry interior,
; and 1..3 sea cells between them. No detached rocks or diagonal bridges.
tmap_generate:
        lda     #1
        sta     MAP+21          ; max terrain level + 1, updated below
        lda     MAP+52
        sta     rng
        lda     MAP+53
        eor     #$A7
        sta     rng+1
        ora     rng
        bne     :+
        inc     rng
:       lda     MAP+54
        sta     count
        jsr     random
        and     #15
        clc
        adc     #34
        sta     latitude
        jsr     random
        and     #3
        sta     shift_x
        lda     #$80
        sta     fill
        lda     #<GRID
        sta     PTR
        lda     #>GRID
        sta     PTR+1
        ldx     #$24            ; 9408 = $24C0
        ldy     #0
        lda     #$80
@fill_page:
        sta     (PTR),y
        iny
        bne     @fill_page
        inc     PTR+1
        dex
        bne     @fill_page
@fill_tail:
        sta     (PTR),y
        iny
        cpy     #$C0
        bne     @fill_tail
        lda     #0
        tax
@woods_clear:
        sta     $0800,x
        inx
        bne     @woods_clear
        ldx     #37
:       sta     $0900,x
        dex
        bpl     :-
        sta     island
@island:
        ldx     island
        lda     centres3,x
        ldy     #13
        ldx     count
        cpx     #3
        beq     :+
        ldx     island
        lda     centres2,x
        ldy     #15
:       clc
        adc     shift_x
        sta     centre_x
        sty     radius
        jsr     random
        and     #3
        clc
        adc     latitude
        sta     centre_y
        ldx     island
        bne     :+
        lda     centre_x
        sta     MAP+3           ; crash on the first island, facing east
        lda     centre_y
        sta     MAP+5
:       lda     centre_x
        sta     MAP+8           ; goal on the last island
        lda     centre_y
        sta     MAP+9
        lda     #0
        sta     row
@row:   lda     row
        sec
        sbc     centre_y
        bcs     :+
        eor     #255
        adc     #1
:       cmp     #24
        bcs     @next_row
        tax
        lda     radius
        sec
        sbc     sag,x
        bmi     @next_row
        sta     width
        cpx     #4              ; safe common channel through every island
        bcc     :+
        jsr     random
        and     #1
        sta     fill
        lda     width
        sec
        sbc     fill
        bmi     @next_row
        sta     width
:       lda     centre_x
        clc
        adc     width
        sta     end_x
        lda     row
        jsr     row_pointer
        lda     centre_x
        sec
        sbc     width
        tay
@land:  tya
        sec
        sbc     centre_x
        bcs     :+
        eor     #255
        adc     #1
:       sta     fill
        lda     width
        sec
        sbc     fill
        ldx     MAP+56          ; relief supplied by the scenario
        beq     @height
@rise:  asl
        dex
        bne     @rise
@height:
        clc
        adc     #1
        sta     (PTR),y
        cmp     MAP+21
        bcc     :+
        adc     #0              ; compare left C set: maximum + 1
        sta     MAP+21
:
        iny
        cpy     end_x
        bcc     @land
        beq     @land
@next_row:
        inc     row
        lda     row
        cmp     #84
        jne     @row
        inc     island
        lda     island
        cmp     count
        jne     @island
        ; The scenario may disable vegetation independently of the terrain.
        lda     MAP+26
        jeq     tmap_sites
        ; Dry interiors grow the scenario's tree; shores remain clear.
        lda     #<$0800
        sta     wood_store+1
        lda     #>$0800
        sta     wood_store+2
        lda     #1
        sta     row
tmap_wood_row:
        lda     row
        jsr     row_pointer
        ldy     #1
tmap_wood_byte:
        lda     #0
        sta     fill
        ldx     #0
tmap_wood_bit:
        lda     (PTR),y
        cmp     #$80
        bcs     :+
        cmp     #3
        bcc     :+
        lda     fill
        ora     masks,x
        sta     fill
:       iny
        iny
        inx
        cpx     #8
        bne     tmap_wood_bit
        lda     fill
wood_store:
        sta     $0800
        inc     wood_store+1
        bne     :+
        inc     wood_store+2
:       cpy     #112
        bcc     tmap_wood_byte
        inc     row
        inc     row
        lda     row
        cmp     #84
        bcc     tmap_wood_row
tmap_sites:
        lda     #0
        sta     MAP+2
        sta     MAP+4
        sta     MAP+7
        sta     MAP+16          ; no fixed mainland cabin
        sta     MAP+37          ; first version uses the resident coarse grid
        lda     #140
        sta     MAP+6
        rts

; PTR = GRID + A * 112. Loops are start-only, not in the engine.
row_pointer:
        tax
        lda     #<GRID
        sta     PTR
        lda     #>GRID
        sta     PTR+1
        cpx     #0
        beq     @done
@add:   clc
        lda     PTR
        adc     #112
        sta     PTR
        bcc     :+
        inc     PTR+1
:       dex
        bne     @add
@done:  rts

random: ; 16-bit Galois LFSR, reproducible including seed 0000.
        lsr     rng+1
        ror     rng
        bcc     :+
        lda     rng+1
        eor     #$B4
        sta     rng+1
:       lda     rng
        rts

preview:
        jsr     HOME
        lda     #<preview_title
        ldx     #>preview_title
        jsr     puts
        lda     seed+1
        jsr     PRBYTE
        lda     seed
        jsr     PRBYTE
        lda     #$8D
        jsr     COUT
        lda     #79             ; north at the top
        sta     row
@row:   lda     row
        jsr     row_pointer
        lda     #1
        sta     column
@cell:  ldy     column
        lda     (PTR),y
        ldx     #'.'|$80
        cmp     #$80
        bcs     :+
        ldx     #'#'|$80
        cmp     #3
        bcc     :+
        ldx     #'^'|$80
:       txa
        jsr     COUT
        lda     column
        clc
        adc     #3
        sta     column
        cmp     #112
        bcc     @cell
        lda     #$8D
        jsr     COUT
        lda     row
        sec
        sbc     #6
        sta     row
        bcs     @row
        lda     #<legend
        ldx     #>legend
        jmp     puts

puts:   sta     TXT
        stx     TXT+1
        ldy     #0
@char:  lda     (TXT),y
        beq     @done
        ora     #$80
        jsr     COUT
        iny
        bne     @char
@done:  rts
hexchar:
        cmp     #10
        bcc     :+
        adc     #6
:       adc     #'0'|$80
        jmp     COUT
getkey:
        lda     KBD
        bpl     getkey
        bit     STROBE
        cmp     #'a'|$80
        bcc     :+
        cmp     #'z'|$80+1
        bcs     :+
        and     #$DF
:       rts

title: .byte "TMAP XL - DESERT ISLANDS",13,13
       .byte "ISLANDS: 2 OR 3 (RETURN = 3)",13,0
seed_prompt: .byte 13,"SEED (4 HEX DIGITS), DEFAULT ",0
seed_edit: .byte 13,"RETURN KEEPS DEFAULT: ",0
preview_title: .byte "TMAP - ARCHIPELAGO    SEED ",0
legend: .byte ". SEA   # BEACH   ^ HIGH GROUND",13
        .byte "SWIM BETWEEN ISLANDS. SEA IS SALT.",13
        .byte "RETURN PLAY  R NEW SEED  ESC MENU",0
centres3: .byte 28,56,84
centres2: .byte 36,68
sag: .repeat 24, I
        .byte (I*I)/32
     .endrepeat
masks: .byte 1,2,4,8,16,32,64,128
seed: .word 0
typed: .word 0
rng: .word 0
digits: .byte 0
nibble: .byte 0
count: .byte 3
island: .byte 0
latitude: .byte 0
shift_x: .byte 0
centre_x: .byte 0
centre_y: .byte 0
radius: .byte 0
width: .byte 0
row: .byte 0
column: .byte 0
fill: .byte 0
end_x: .byte 0
.export tmap_main, tmap_generate, tmap_count_key, tmap_seed_key, tmap_preview_key
