; WARGALAGA II -- Apple //e enhanced / //c 128 KB, ProDOS 8, HGR double buffer.
; VERHILLE Arnaud -- GPL-3.0 (see LICENSE at repository root).
;
; The frame loop:
;   input -> logic steps (one per two refreshes elapsed, at most two)
;         -> draw the hidden page -> present it at the next deadline.
; logic.s holds the logic (tools/model.py is its bit-exact reference),
; render.s the drawing, which only rewrites what changed on a page since
; that page was last drawn (two frames ago).
.setcpu "65C02"
.macpack longbranch

.import _prodos_video_claim, _prodos_video_release
.import timing_init, timing_close, timing_present, timing_scan
.import timing_refreshes, joy_x, joy_mode
.export _main, _game_shutdown
; Test hooks (a2test reads them through build/game.lbl).
.export game_tick, frame_count, step_count, ship_c, shot_y, shot_c, star_y
.export star_col, move_dir, fire_req, logic_step, logic_done, quit, shot_limit
.export a_state, a_x, a_y, row_off, row_anim, prng_lo, render, render_done
.export alien_sta, alien_sta_done, alien_eor, alien_eor_done, alien_clr, alien_clr_done

FIELD_TOP  = 8                  ; rows 0-7: HUD (lot 3)
SHIP_Y     = 180                ; ship top row
SHIP_MAX   = 140 - 7            ; last cell of the 7-cell ship
SHIP_SPEED = 2                  ; cells (4 dots) per step: jauge S at start
MAX_SHOTS  = 10                 ; shot slots; shot_limit = jauge B
SHOT_LIMIT = 5                  ; jauge B at start
SHOT_DY    = 8
SHOT_Y0    = SHIP_Y - 6
NSTARS     = 24

ROWS       = 5                  ; formation: 5 rows of 8
COLS       = 8
NALIENS    = ROWS * COLS
ALIEN_MAX  = 140 - 7
FORM_X0    = 11                 ; cell of column 0 at sway 0
FORM_DX    = 14
FORM_Y0    = 20
FORM_DY    = 14
SWAY_MAX   = 12
ST_DEAD    = 0                  ; alien states
ST_ENTER   = 1
ST_DIVE    = 2
ST_HOME    = 3
ST_FORM    = 4
HOME_DX    = 2
HOME_DY    = 4
ENTRY_FIRST = 20                ; steps before the first pair
WAVE_GAP   = 60
LAUNCH_GAP = 6
DIVE_GAP   = 20
MAX_DIVERS = 6
OFF_TOP    = 240                ; row 240 = -16: above the screen
PATH_END   = $80
SEED       = $AD3C

KEY_ESC   = $1B
KEY_LEFT  = $08
KEY_RIGHT = $15
KEY_TAB   = $09

.zeropage
src:    .res 2
dst:    .res 2
ptr:    .res 2
col:    .res 1                  ; byte column of a sprite
page:   .res 1                  ; page being drawn: 0 = $2000, 1 = $4000
pg40:   .res 1                  ; page * NALIENS
pg10:   .res 1                  ; page * MAX_SHOTS
tmp:    .res 1
tmp2:   .res 1
cnt:    .res 1
r_row:  .res 1                  ; rectangle for the generic routines
r_col:  .res 1
r_w:    .res 1
r_h:    .res 1
prng_lo: .res 1                 ; dev/lib/math/random.asm state
prng_hi: .res 1

.segment "ROWS"                 ; page aligned (src/game.cfg)
hgr_lo:  .res 256
hgr_hi:  .res 256               ; page 1 row high bytes
hgr_hi2: .res 256               ; page 2: the same + $20

.bss
frame_count: .res 2
step_count:  .res 2
pairs:       .res 1             ; refreshes not yet turned into a step (0/1)
steps:       .res 1
quit:        .res 1
dir_key:     .res 1             ; last direction key: 0, 1 right, $FF left
move_dir:    .res 1
fire_req:    .res 1
button:      .res 1             ; open apple / button 0, previous state
ship_c:      .res 1
shot_limit:  .res 1
shot_y:      .res MAX_SHOTS     ; top row, 0 = free
shot_c:      .res MAX_SHOTS
star_y:      .res NSTARS
star_col:    .res NSTARS
; aliens
a_state:     .res NALIENS
a_x:         .res NALIENS       ; cell
a_y:         .res NALIENS       ; row (240-255: above the screen)
a_plo:       .res NALIENS       ; path pointer
a_phi:       .res NALIENS
a_mirror:    .res NALIENS
row_off:     .res ROWS          ; sway offset of each row
row_anim:    .res ROWS          ; animation frame of each row
entry_w:     .res 1             ; wave being launched (ROWS = done)
entry_k:     .res 1             ; pair in the wave
entry_t:     .res 1             ; steps to the next pair
form_off:    .res 1
form_dir:    .res 1             ; 1 or $FF
sway_row:    .res 1
sway_t:      .res 1             ; rows move on every other step
dive_t:      .res 1

.rodata
.include "sprites.inc"           ; first: the sprite routines need the sizes
.include "paths.inc"

.code
_main:
        lda $BF98                ; MACHID: bits 5-4 = 11 for 128 KB
        and #$30
        cmp #$30
        beq big
        ldx #msg_128k-messages
        jmp fail
big:    lda #1                   ; PD_VIDEO_DISCARD_RAM: aux memory is ours
        jsr _prodos_video_claim
        cmp #0
        beq claimed
        ldx #msg_ram-messages
        jmp fail
claimed:
        jsr rows_init
        lda #$20
        jsr clear_page
        lda #$40
        jsr clear_page
        sta $C00C                ; 40 columns, no 80STORE: plain HGR
        sta $C000
        bit $C050
        bit $C052
        bit $C057
        bit $C054
        jsr game_init
        jsr render_init
        jsr timing_init
        lda #1                   ; page 1 shown, page 2 drawn first
        jsr select_page
        lda #1
        sta steps

game_tick:
        jsr read_input
        lda quit
        bne done
        ldx steps
        beq render_frame
:       phx
        jsr logic_step
        plx
        dex
        bne :-
render_frame:
        jsr render
        lda page
        jsr timing_present
        inc frame_count
        bne :+
        inc frame_count+1
:       lda timing_refreshes     ; one logic step per two refreshes
        clc
        adc pairs
        tax
        and #1
        sta pairs
        txa
        lsr
        cmp #3
        bcc :+
        lda #2                   ; at most one step of catch-up
:       sta steps
        lda page
        eor #1
        jsr select_page
        bra game_tick
done:   rts

; Text message (X = offset in messages), a key, then back to ProDOS.
fail:   lda messages,x
        beq :+
        ora #$80
        jsr $FDED
        inx
        bne fail
:       bit $C000
        bpl :-
        bit $C010
        rts

; From the crt0 cleanup (ESC, Ctrl-RESET): clock off, text, /RAM rebuilt.
_game_shutdown:
        jsr timing_close
        bit $C051
        bit $C054
        jmp _prodos_video_release

; Fill the 8 KB page at A (high byte) with zeros.
clear_page:
        sta dst+1
        stz dst
        ldx #$20
        lda #0
        tay
:       sta (dst),y
        iny
        bne :-
        inc dst+1
        dex
        bne :-
        rts

; Row address tables: lo = (y/8 mod 2)*$80 + (y/64)*$28, hi = $20 +
; (y mod 8)*4 + (y/8 mod 8)/2; page 2 = hi + $20.
rows_init:
        ldx #0
:       txa
        and #7
        asl
        asl
        ora #$20
        sta hgr_hi,x
        txa
        lsr
        lsr
        lsr
        tay                      ; y/8
        and #7
        lsr                      ; C = (y/8) & 1
        ora hgr_hi,x
        sta hgr_hi,x
        lda #0
        ror
        sta hgr_lo,x
        tya
        lsr
        lsr
        lsr
        tay                      ; y/64
        lda hgr_lo,x
        clc
        adc thirds,y
        sta hgr_lo,x
        lda hgr_hi,x
        clc
        adc #$20
        sta hgr_hi2,x
        inx
        cpx #192
        bne :-
        rts
thirds: .byte $00, $28, $50

game_init:
        lda #(SHIP_MAX/2)
        sta ship_c
        lda #SHOT_LIMIT
        sta shot_limit
        ldx #NSTARS-1
:       lda star_y0,x
        sta star_y,x
        lda star_col0,x
        sta star_col,x
        dex
        bpl :-
        lda #<SEED
        sta prng_lo
        lda #>SEED
        sta prng_hi
        lda #ENTRY_FIRST
        sta entry_t
        lda #1
        sta form_dir
        lda #DIVE_GAP
        sta dive_t
        rts

; ---------------------------------------------------------------------------
; Input, once per frame. Keyboard: a new key sets the direction or asks for
; a shot; the direction holds while any key is down ($C010 bit 7), so a
; shot fired with SPACE does not stop the ship. Open apple / button 0 fires
; on press. TAB switches keyboard / joystick (choice menu: lot 9).
read_input:
        lda $C000
        bpl no_key
        bit $C010
        and #$7F
        cmp #'a'
        bcc :+
        and #$DF                 ; upper case
:       cmp #KEY_ESC
        bne :+
        sta quit
        rts
:       cmp #KEY_LEFT
        beq left
        cmp #'J'
        beq left
        cmp #KEY_RIGHT
        beq right
        cmp #'L'
        beq right
        cmp #' '
        beq space
        cmp #KEY_TAB
        bne buttons
        lda joy_mode
        eor #1
        sta joy_mode
        bra buttons
left:   lda #$FF
        bra :+
right:  lda #1
:       sta dir_key
        bra buttons
space:  sta fire_req
        bra buttons
no_key: bit $C010                ; any key still down?
        bmi buttons
        stz dir_key
buttons:
        lda $C061
        and #$80
        tax
        eor button
        and $C061                ; newly pressed
        bpl :+
        sta fire_req
:       stx button
        lda joy_mode
        beq keyboard
        lda #$FF
        ldx joy_x
        cpx #50
        bcc :+
        lda #1
        cpx #141
        bcs :+
        lda #0
:       sta move_dir
        rts
keyboard:
        lda dir_key
        sta move_dir
        rts

.include "logic.s"
.include "render.s"

.rodata
messages:
msg_128k: .byte "WARGALAGA II NEEDS 128K.", $0D, 0
msg_ram:  .byte "INVALID PRODOS STATE (/RAM).", $0D, 0
; Stars: start row, byte column, dot (one dot: violet/green, blue/orange),
; speed 1..3 rows a step.
star_y0:
.repeat NSTARS, I
        .byte FIELD_TOP + (I * 97 + 13) .mod (192 - FIELD_TOP)
.endrepeat
star_col0:
.repeat NSTARS, I
        .byte (I * 23 + 5) .mod 40
.endrepeat
star_val:
.repeat NSTARS, I
        .byte (1 << ((I * 3) .mod 7)) | ((I .mod 2) << 7)
.endrepeat
star_speed:
.repeat NSTARS, I
        .byte 1 + I .mod 3
.endrepeat
; Formation geometry: cell of column j at sway 0, row of each alien, its
; slot row; the formation row each screen row belongs to ($FF: none).
slot_dx:
.repeat COLS, J
        .byte FORM_X0 + FORM_DX * J
.endrepeat
alien_row:
.repeat NALIENS, I
        .byte I / COLS
.endrepeat
form_y:
.repeat ROWS, R
        .byte FORM_Y0 + FORM_DY * R
.endrepeat
frow:
.repeat 256, L
.if L >= FORM_Y0 && L < FORM_Y0 + ROWS * FORM_DY
        .byte (L - FORM_Y0) / FORM_DY
.else
        .byte $FF
.endif
.endrepeat

.code
.include "random.asm"
