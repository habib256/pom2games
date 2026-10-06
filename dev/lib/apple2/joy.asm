; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; joy.asm -- joystick (two paddle timers) for the Apple II game port
; ============================================================================
;   read_stick -- sample both axes. joy_x, joy_y = 0 (left / up) .. ~120
;                 (right / down), ~60 centred. Clobbers A, X, Y. ~6 ms.
;   stick_dir  -- after read_stick: A = JOY_UP / JOY_DOWN / JOY_LEFT /
;                 JOY_RIGHT, or JOY_NONE (0, Z set) inside the dead zone.
;                 The vertical axis wins a diagonal. Clobbers A.
;
; The buttons need no routine: BUTN0 / BUTN1 (apple2.inc) read bit 7 = 1
; while pressed (`LDA BUTN0 / BMI pressed`); edge detection is the game's.
;
; Why one fixed loop: PTRIG starts both timers, and each PADDLn reads bit 7
; = 1 until its capacitor has charged (up to ~2.8 ms). Counting both in the
; same 256-turn, 24-cycle loop (6 ms, longer than a full charge) avoids the
; classic bug of reading the second paddle before the first has discharged.
;
; Dead zone: JOY_LO / JOY_HI (count below / above = deflected). Define them
; before the include to retune; defaults suit a centred stick at ~60.
;
; BSS: joy_x, joy_y, joy_cnt. No zero page. Only the routines referenced
; before the include are assembled (.ifref).
; Caller responsibility: .include "apple2.inc" first (PTRIG, PADDL0/1).
; Mirror for C: a2_read_stick() in ../apple2c/apple2game.h.
; ============================================================================

.ifndef _JOY_ASM_LOADED_
_JOY_ASM_LOADED_ = 1

.ifndef JOY_LO
JOY_LO = 30
.endif
.ifndef JOY_HI
JOY_HI = 90
.endif

JOY_NONE  = 0
JOY_UP    = 1
JOY_DOWN  = 2
JOY_LEFT  = 3
JOY_RIGHT = 4

.segment "BSS"
joy_x:          .res 1
joy_y:          .res 1
joy_cnt:        .res 1

.segment "CODE"


.ifref read_stick
read_stick:
        LDX     #$00
        LDY     #$00
        STX     joy_cnt         ; 256 turns
        LDA     PTRIG
@lp:    LDA     PADDL0
        BPL     @xd
        INX
@xd:    LDA     PADDL1
        BPL     @yd
        INY
@yd:    DEC     joy_cnt
        BNE     @lp
        STX     joy_x
        STY     joy_y
        RTS
.endif

.ifref stick_dir
stick_dir:
        LDA     joy_y
        CMP     #JOY_LO
        BCC     @up
        CMP     #JOY_HI+1
        BCS     @down
        LDA     joy_x
        CMP     #JOY_LO
        BCC     @left
        CMP     #JOY_HI+1
        BCS     @right
        LDA     #JOY_NONE
        RTS
@up:    LDA     #JOY_UP
        RTS
@down:  LDA     #JOY_DOWN
        RTS
@left:  LDA     #JOY_LEFT
        RTS
@right: LDA     #JOY_RIGHT
        RTS
.endif

.endif  ; _JOY_ASM_LOADED_
