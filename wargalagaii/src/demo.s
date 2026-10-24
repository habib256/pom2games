; WARGALAGA II -- the attract mode's player (lot 9). Resident at $0800
; after Meteor Storm (segment DEMO, memory LOWM). Included by game.s.
;
; The demo is a game from level 1 and SEED; logic_step takes each step's
; input from src/demo.inc (tools/demo.py: the autopilot's moves on
; tools/model.py, always firing) instead of the keyboard. A key or a button,
; the end of the script or GAME OVER: back to the title (quit).

.zeropage
demo_ptr: .res 2

.segment "DEMO"
demo_init:
        lda #<demo_script
        sta demo_ptr
        lda #>demo_script
        sta demo_ptr+1
        stz demo_n
        stz demo_end
        rts

; logic_step's inputs: the move of the current run, fire pressed and held.
demo_input:
        lda demo_n
        bne di_run
        lda (demo_ptr)
        beq di_end
        inc demo_ptr
        bne :+
        inc demo_ptr+1
:       tax
        and #$3F
        sta demo_n
        txa
        asl                      ; move code (bits 7-6) -> 0..2
        rol
        rol
        and #3
        tax
        lda demo_dirs,x
        sta demo_dir
di_run: dec demo_n
        lda demo_dir
        sta move_dir
        lda #1
        sta fire_req
        lda #$80
        sta fire_held
        rts
di_end: sta demo_end             ; (A = 0: no move, no shot)
        inc demo_end
        sta move_dir
        sta fire_req
        sta fire_held
        rts

; In place of read_input: a key (acknowledged), a button or the script's
; end ends the demo.
demo_poll:
        lda $C000
        bpl :+
        bit $C010
        bra dp_stop
:       lda $C061                ; (bits 6-0 float)
        ora $C062
        and #$80
        ora demo_end
        beq :+
dp_stop:
        lda #1
        sta quit
:       rts

demo_dirs: .byte 0, 1, $FF
.include "demo.inc"

.segment "BSS"
demo_n:   .res 1                ; steps left in the run
demo_dir: .res 1
demo_end: .res 1
.code
