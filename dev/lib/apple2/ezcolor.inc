; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; ezcolor.inc -- E-Z Color Graphics Interface (TMS9918A) equates and macros
; ============================================================================
; Include near the top (after apple2.inc); include ezcolor.asm at the END of
; the source (it is .ifref-guarded: only the referenced routines assemble).
; Pure equates and macros, no code. See README.md "E-Z Color (TMS9918A) card".
;
; The card (Steve Ciarcia, BYTE, August 1982; MAME a2bus/ezcgi.cpp, POM2
; src/EzColorCard.cpp): a TMS9918A with 16 KB of VRAM in any slot n.
;   $C0n0 = $C080 + n*16      VDP data port (VRAM read/write, auto-increment)
;   $C0n1 = $C081 + n*16      VDP register port (status read; address and
;                             register writes, two bytes each)
;   other $C0nX read $FF; /INT drives the slot IRQ; no slot ROM ($Cn00 is
;   empty, so detection probes the VDP itself: ez_detect).
;
; Two access styles, both after ez_detect:
;   1. Helpers whose absolute operands ez_detect patched to the slot
;      (ez_data_w: `STA $C0n0`, no index register). `JSR ez_data_w` costs
;      6+4+6+6 = 22 cycles store to store when chained: exactly POM1's
;      `STA VDP_DATA / JSR tms9918_pad18` contract, in 3 bytes instead of 6.
;   2. Indexed LOADS only: LDX ez_slotx / LDA EZ_DATA,X or LDA EZ_CTRL,X
;      (4 cycles, no page crossing). NEVER an indexed STORE: the NMOS 6502's
;      STA abs,X (and STA (zp),Y) reads the target address one cycle before
;      writing it. On $C0n0 that dummy read is a VRAM read (the address
;      advances, the byte lands one further); on $C0n1 it is a status read
;      (resets the control flip-flop, so a two-byte command decodes wrong,
;      and clears F). Store through the helpers (absolute STA). a2run models
;      the dummy read, so a test catches an indexed store. Indexed loads
;      still need the pad between VRAM accesses (JSR ez_pad18).
;
; Silicon-strict contract (POM1 dev/lib/tms9918/tms9918.inc): at least 18
; cycles between back-to-back VRAM accesses (data port, and a read address
; setup, which prefetches) while the display is on and the beam is in the
; active area -- a 22-cycle store-to-store gap. With the display blanked
; (R1 bit 6 = 0) or in vertical blanking, the VDP serves the CPU every ~2 us
; and unpadded loops (>= 9 cycles) are safe: ez_fill_blank / ez_copy_blank.
; ============================================================================

.ifndef _EZCOLOR_INC_LOADED_
_EZCOLOR_INC_LOADED_ = 1

; Storage, reserved here so code above ezcolor.asm addresses it as zero page.
; ez_ptr / ez_count may be aliased (define them before this include);
; EZ_ZP = 1 (before this include) puts ez_slot / ez_slotx in zero page.
.ifndef EZ_ZP
EZ_ZP = 0
.endif
.pushseg
.zeropage
.ifndef ez_ptr
ez_ptr:   .res 2                ; ez_copy / ez_read source or destination
.endif
.ifndef ez_count
ez_count: .res 2                ; ez_fill / ez_copy / ez_read byte count
.endif
.if EZ_ZP
ez_slot:  .res 1                ; 1..7, 0 = no card
ez_slotx: .res 1                ; slot*16
.else
.bss
ez_slot:  .res 1
ez_slotx: .res 1
.endif
.popseg

EZ_DATA = $C080                 ; + slot*16 (ez_slotx): LDA EZ_DATA,X only
EZ_CTRL = $C081                 ; + slot*16: LDA EZ_CTRL,X = status read

; Register 1 bits (TMS9918A).
EZ_R1_16K   = $80               ; 4116/4416 16 KB VRAM (always set)
EZ_R1_BLANK = $40               ; 1 = display on
EZ_R1_IE    = $20               ; 1 = frame interrupt on /INT (slot IRQ)
EZ_R1_M1    = $10               ; text mode
EZ_R1_M2    = $08               ; multicolour mode
EZ_R1_SIZE  = $02               ; 16x16 sprites
EZ_R1_MAG   = $01               ; magnified sprites
; Status bits.
EZ_ST_F     = $80               ; frame flag (vertical blanking reached)
EZ_ST_5S    = $40               ; fifth sprite on a line
EZ_ST_C     = $20               ; sprite coincidence

; Push A to the data port, then the 18-cycle pad (A/X/Y and flags kept).
.macro EZ_WRT_DATA_REG
        JSR     ez_data_w
.endmacro

; Load an immediate and push it (N/Z follow the value, as LDA).
.macro EZ_WRT_DATA_VAL val
        LDA     #val
        JSR     ez_data_w
.endmacro

; Wait for the frame flag: drain the stale F, then poll (~19 cycles a turn).
; Unbounded, like POM1's WAIT_VBLANK: prefer EZ_WAIT_VBLANK_SAFE. A/X/Y kept.
.macro EZ_WAIT_VBLANK
        JSR     ez_status_bit   ; drain stale F (also clears 5S and C)
:       JSR     ez_status_bit
        BPL     :-
.endmacro

; Bounded variant (~65536 polls, ~1.1 s on a 1 MHz Apple II), then gives up
; and returns anyway; A/X/Y preserved, flags clobbered. Unnamed labels only,
; so the caller's @cheap locals stay in scope.
.macro EZ_WAIT_VBLANK_SAFE
        PHA
        TXA
        PHA
        TYA
        PHA
        JSR     ez_status_bit   ; drain stale F
        LDX     #0
        LDY     #0
:       JSR     ez_status_bit
        BMI     :+              ; F = 1: vertical blanking reached
        INX
        BNE     :-
        INY
        BNE     :-
:       PLA
        TAY
        PLA
        TAX
        PLA
.endmacro

; Spin until the fifth-sprite flag (V of BIT) sets; see tms9918_5strigger.asm.
.macro EZ_WAIT_5S
:       JSR     ez_status_bit
        BVC     :-
.endmacro

.endif  ; _EZCOLOR_INC_LOADED_
