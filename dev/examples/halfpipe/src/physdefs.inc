; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; physdefs.inc -- the half-pipe's lib/physics setup and its variables
; ============================================================================
; Include at the top, after math.inc and pipeconst.inc (tools/halfpipe.py
; writes it). phys.inc holds the code. The switches used: VL_GROUND_SEGMENTS
; (the pipe is 20 line segments: verlet_seg.asm) with VL_SEG_CACHE,
; VL_CON_FIXED_K (links of gain 2^6, no k8 table), VL_PAIR_DAMP (the spin
; fades in the air), VL_CEILING_CLAMP; the tangent hook pumps.
; ============================================================================

RIDE    = 0                     ; hp_status
CRASHED = 1

VL_NPOINTS      = 3             ; 0 = rear wheel, 1 = front wheel, 2 = body
VL_NCON         = 3
VL_GRAVITY      = GRAVITY
VL_VMAX_X       = VMAX
VL_VMAX_Y       = VMAX
VL_GROUND       = 3             ; the body too: it touching is a crash
VL_RADIUS       = RADIUS
VL_BOUNCE       = BOUNCE
VL_CON_FIXED_K  = FIXED_K
VL_PAIR_DAMP    = SPIN_DAMP
VL_CEILING_CLAMP = TOP_Y
.include "verlet.inc"
.globalzp bcd_ptr                ; (bcd.asm, at the end)

; the pump: a wheel going up a curve or a lip (vt and nx of opposite signs,
; nx <> 0) gains PUMP_K of tangential speed while the pump is on
.macro VL_GROUND_TANGENT
        LDA     hp_pumping
        BEQ     :++
        LDA     vl_cur
        CMP     #2
        BCS     :++
        LDA     vl_nx
        BEQ     :++
        EOR     vl_vt+1
        BPL     :++
        LDA     vl_vt+1
        BMI     :+
        CLC
        LDA     vl_vt
        ADC     #<PUMP_K
        STA     vl_vt
        LDA     vl_vt+1
        ADC     #>PUMP_K
        STA     vl_vt+1
        JMP     :++
:       SEC
        LDA     vl_vt
        SBC     #<PUMP_K
        STA     vl_vt
        LDA     vl_vt+1
        SBC     #>PUMP_K
        STA     vl_vt+1
:
.endmacro

.segment "BSS"
; the state (tests/test_halfpipe.py snapshots hp_status..hp_last in this order)
hp_status:  .res 1              ; RIDE, CRASHED
hp_timer:   .res 1              ; ticks since the crash (to 255)
hp_air:     .res 1              ; ticks with no wheel down (to 255)
hp_rot:     .res 1              ; octants turned in the air (signed)
hp_oct:     .res 1              ; the octant of the wheels' axis
hp_spins:   .res 1              ; full turns of the last landing
hp_peak:    .res 1              ; highest row of the body in this air
hp_score:   .res 3              ; BCD, low byte first
hp_last:    .res 2              ; BCD: the last landing's points
hp_add:     .res 1              ; (0: hp_last as a 3-byte addend)
hp_pumping: .res 1              ; the pump is on this tick
in_pump:    .res 1              ; the tick's inputs: pump (0 / 1)
in_lean:    .res 1              ; lean (-1, 0, 1)
.segment "CODE"
