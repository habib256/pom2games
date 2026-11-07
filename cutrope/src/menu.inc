; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; menu.inc -- CUTROPE's level menu (HGR page 1)
; ============================================================================
;   menu    the levels in a grid of 5 a row with their stars ("*" won, "."
;           not yet, "---" locked: the level before it not won yet), the
;           stars won in all; I J K L / the arrows / a push of the stick move
;           the choice, space / RETURN / button 0 play it (an open one),
;           ESC quits to DOS; the mouse: the choice follows the pointer
;           (a cell is 56 x 16 pixels), a click plays. Out: A = the level. The choice starts on the
;           level last played (`level`), at boot (level >= NLEVEL) on the
;           first one not won yet. Only the two cells that change are drawn
;           again.
; ============================================================================

MENU_SL   = 48                          ; the grid's first row (16 rows apart)
MENU_COLS = 5                           ; cells of 8 columns

.segment "BSS"
sel:    .res 1                          ; the cell chosen
mk:     .res 1                          ; cell: its brackets (0: none)
mvx:    .res 1                          ; the stick's push (stick_v)
mvy:    .res 1
stk:    .res 1                          ; a push already taken (until it rests)
ms_b:   .res 1                          ; the mouse's button at the last poll

.segment "CODE"
menu:   JSR     clear_pages
        LDA     #$80                    ; (a button held from the game: no click)
        STA     ms_b
        LDA     #0
        STA     pl_n
        STA     stk
        JSR     set_page
        PUTS8_AT m_title, 13, 8
        PUTS8_AT m_stars, 14, 24
        LDA     total
        LDY     #20
        JSR     put2
        PUTS8_AT m_help, 0, 160
        PUTS8_AT m_quit, 15, 176
        LDA     #120                    ; a candy on its rope over the frog
        STA     hl_ln_x0
        STA     hl_ln_x1
        LDA     #128
        STA     hl_ln_y0
        LDA     #144
        STA     hl_ln_y1
        JSR     hgr_line8
        LDA     #117
        LDY     #144
        LDX     #<candy_desc
        STX     pl_sp
        LDX     #>candy_desc
        JSR     menu_spr
        LDA     #148
        LDY     #136
        LDX     #<frog_desc
        STX     pl_sp
        LDX     #>frog_desc
        JSR     menu_spr
        LDA     #98
        LDY     #138
        LDX     #<star_desc
        STX     pl_sp
        LDX     #>star_desc
        JSR     menu_spr
        LDX     #NLEVEL - 1             ; every cell
:       LDA     #0
        JSR     cell
        DEX
        BPL     :-
        LDX     level                   ; the choice
        CPX     #NLEVEL
        BCC     @sel
        LDX     #0                      ; boot: the first level not won
:       LDA     best,X
        BEQ     @sel
        INX
        CPX     #NLEVEL
        BCC     :-
        LDX     #0
@sel:   STX     sel
        LDA     #1
        JSR     cell
        BIT     LOWSCR
menu_idle:                              ; (the tests: the menu drawn, waiting)
        JSR     poll_key
        BNE     @key
        JSR     menu_stick              ; (a push: as its key)
        BNE     @key
        JSR     menu_mouse              ; (the pointer over a cell, a click)
        BEQ     menu_idle
        BPL     @key
        AND     #$7F                    ; $80 + a cell: the choice there
        TAX
        CPX     sel
        BEQ     menu_idle
        JMP     @move
@key:   LDX     sel
        CMP     #'J'
        BEQ     @left
        CMP     #KC_LEFT
        BEQ     @left
        CMP     #'L'
        BEQ     @right
        CMP     #KC_RIGHT
        BEQ     @right
        CMP     #'I'
        BEQ     @up
        CMP     #KC_UP
        BEQ     @up
        CMP     #'K'
        BEQ     @down
        CMP     #KC_DOWN
        BEQ     @down
        CMP     #' '
        BEQ     @play
        CMP     #KC_RET
        BEQ     @play
        CMP     #KC_ESC
        BNE     menu_idle
        JMP     quit
@left:  TXA
        BEQ     menu_idle
        DEX
        BPL     @move
@right: INX
        CPX     #NLEVEL
        BCS     menu_idle
        BCC     @move
@up:    TXA
        SEC
        SBC     #MENU_COLS
        BCC     menu_idle
        TAX
        BCS     @move
@down:  TXA
        CLC
        ADC     #MENU_COLS
        CMP     #NLEVEL
        BCS     menu_idle
        TAX
@move:  TXA                             ; the old cell without its brackets,
        PHA                             ; the new one with them
        LDX     sel
        LDA     #0
        JSR     cell
        PLA
        TAX
        STX     sel
        LDA     #1
        JSR     cell
        JMP     menu_idle
@play:  LDX     sel
        JSR     unlocked
        BNE     :+
        LDA     #$20                    ; locked: a buzz
        LDX     #$FF
        JSR     tone
        JMP     menu_idle
:       LDA     joy_ok                  ; the buttons let go first
        BEQ     @ms
@w:     BIT     BUTN0
        BMI     @w
@ms:    LDA     _mouse_slot
        BEQ     @ret
@wm:    JSR     _mouse_poll
        BIT     _mouse_buttons
        BMI     @wm
@ret:   LDA     sel
        RTS

; the stick, as the menu's keys: A = KC_LEFT / RIGHT / UP / DOWN for a push
; (one until it rests again), ' ' for button 0, 0 for nothing (Z)
menu_stick:
        LDA     joy_ok
        BEQ     @rts
        BIT     BUTN0
        BPL     :+
        LDA     #' '
        RTS
:       JSR     read_stick_fast
        LDA     joy_x
        LDY     joy_rx
        JSR     stick_v
        STA     mvx
        LDA     joy_y
        LDY     joy_ry
        JSR     stick_v
        STA     mvy
        ORA     mvx
        BNE     :+
        STA     stk                     ; at rest: the next push counts
@rts:   RTS
:       LDA     stk
        BNE     @none
        INC     stk
        LDA     mvx
        BEQ     :+
        BMI     @l
        LDA     #KC_RIGHT
        RTS
@l:     LDA     #KC_LEFT
        RTS
:       LDA     mvy
        BMI     @u
        LDA     #KC_DOWN
        RTS
@u:     LDA     #KC_UP
        RTS
@none:  LDA     #0
        RTS

; the mouse in the menu: A = ' ' for a click (Z = 0, N = 0), $80 + the cell
; under the pointer when it moved there (N = 1), 0 for nothing (Z)
menu_mouse:
        LDA     _mouse_slot
        BEQ     @rts
        JSR     _mouse_poll
        LDX     ms_b                    ; a click: the button down now, up before
        LDA     _mouse_buttons
        STA     ms_b
        TXA
        EOR     #$FF
        AND     ms_b
        BPL     :+
        LDA     #' '
        RTS
:       LDA     _mouse_x
        CMP     ms_x
        BNE     :+
        LDA     _mouse_y
        CMP     ms_y
        BEQ     @none
:       LDA     _mouse_x
        STA     ms_x
        LDA     _mouse_y
        STA     ms_y
        SEC                             ; row = (y - MENU_SL + 4) / 16
        SBC     #MENU_SL - 4
        BCC     @none
        LSR     A
        LSR     A
        LSR     A
        LSR     A
        STA     t1
        LDA     #0                      ; cell = row * 5 + x / 56
        LDX     t1
        BEQ     :++
:       CLC
        ADC     #MENU_COLS
        DEX
        BNE     :-
:       STA     t1
        LDA     ms_x
:       CMP     #56
        BCC     :+
        SBC     #56
        INC     t1
        BNE     :-
:       LDA     t1
        CMP     #NLEVEL
        BCS     @none
        ORA     #$80
        RTS
@none:  LDA     #0
@rts:   RTS

; A, Y = top left, pl_sp, X = the descriptor (low, high)
menu_spr:
        STA     pl_x
        STY     pl_y
        STX     pl_sp+1
        JMP     pl_sprite

; X = a level, A = 1 with brackets (the choice): its cell. Keeps X.
cell:   STA     mk
        STX     t0
        LDA     #MENU_SL
        STA     ht_sl
        TXA
@d:     CMP     #MENU_COLS              ; row = X / 5, column = X mod 5
        BCC     @c
        SBC     #MENU_COLS              ; (C = 1)
        TAY
        LDA     ht_sl
        ADC     #15                     ; (C = 1: 16 rows)
        STA     ht_sl
        TYA
        JMP     @d
@c:     ASL     A
        ASL     A
        ASL     A
        STA     ht_col
        LDA     #' '
        LDY     mk
        BEQ     :+
        LDA     #'['
:       JSR     hgr_putc8
        LDA     t0                      ; its number, two digits
        CLC
        ADC     #1
        LDY     #'0'
:       CMP     #10
        BCC     :+
        SBC     #10
        INY
        BNE     :-
:       PHA
        TYA
        JSR     hgr_putc8
        PLA
        ORA     #'0'
        JSR     hgr_putc8
        LDA     #' '
        JSR     hgr_putc8
        LDX     t0
        JSR     unlocked
        BNE     @open
        LDA     #'-'
        JSR     hgr_putc8
        JSR     hgr_putc8
        JSR     hgr_putc8
        JMP     @end
@open:  LDA     best,X                  ; the stars: best - 1 (0 not won)
        BEQ     :+
        SEC
        SBC     #1
:       STA     t1
        LDY     #0
@st:    LDA     #'*'                    ; '*' for the first t1, '.' after
        CPY     t1
        BCC     :+
        LDA     #'.'
:       JSR     hgr_putc8
        INY
        CPY     #3
        BNE     @st
@end:   LDA     #' '
        LDY     mk
        BEQ     :+
        LDA     #']'
:       JSR     hgr_putc8
        LDX     t0
        RTS

.segment "RODATA"
m_title:    .byte "C U T R O P E", 0
m_stars:    .byte "STARS   /", '0' + NLEVEL * 3 / 10, '0' + NLEVEL * 3 .mod 10, 0
m_help:     .byte "IJKL/STICK: CHOOSE    SPACE/RETURN: PLAY", 0
m_quit:     .byte "ESC: QUIT", 0
.segment "CODE"
