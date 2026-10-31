; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; ezvdp.inc -- the TMS9918A ports of the E-Z Color card, slot-relocatable
; ============================================================================
; On the Apple-1 the P-LAB card sits at fixed addresses ($CC00 data, $CC01
; control). The E-Z Color card answers at $C0n0 (data) and $C0n1 (control),
; n = 8 + slot, wherever it is plugged: the slot is only known at run time.
;
; Every VDP access of ROGUE.TMS (video_tms.asm) is an ABSOLUTE instruction on $C080/$C081
; (the "slot 0" placeholder), emitted by the macros below. Each macro also
; writes the address of its operand into the VDPFIX segment; vdp_patch
; (boot.inc) walks that table once the card is found and turns $C080/$C081
; into $C0n0/$C0n1 (low byte = $80 | port | slot*16). So:
;
;   - the cycle count of every access is the Apple-1's (STA abs = 4 cycles),
;     and POM1's silicon-strict padding (18 cycles between two accesses)
;     carries over unchanged;
;   - no indexed store ever touches the card: a 6502 `STA $C080,X` makes a
;     dummy READ of the same address before the write, and a read of the
;     data port moves the VRAM address (of the control port: resets the
;     byte flip-flop).
;
; Each access carries an unnamed label (`:`) that its VDPFIX record points
; at: a named one would end the caller's @cheap-local scope. Do not use
; `:+` / `:-` across these macros. The table costs 2 bytes a site. Placeholders $C080/$C081 are the language
; card's switches in slot 0: harmless on a 48 KB II+, never run unpatched.
; ============================================================================

.ifndef _EZVDP_INC_LOADED_
_EZVDP_INC_LOADED_ = 1

EZV_DATA = $C080                ; placeholder: data port of "slot 0"
EZV_CTRL = $C081                ; placeholder: control (register) port

; One access + its patch record.
.macro VSTA_DATA
:       STA     EZV_DATA             ; unnamed label: the caller\'s @labels live on
        .pushseg
        .segment "VDPFIX"
        .addr   :- + 1
        .popseg
.endmacro

.macro VSTA_CTRL
:       STA     EZV_CTRL             ; unnamed label: the caller\'s @labels live on
        .pushseg
        .segment "VDPFIX"
        .addr   :- + 1
        .popseg
.endmacro

.macro VSTX_CTRL
:       STX     EZV_CTRL             ; unnamed label: the caller\'s @labels live on
        .pushseg
        .segment "VDPFIX"
        .addr   :- + 1
        .popseg
.endmacro

.macro VLDA_DATA
:       LDA     EZV_DATA             ; unnamed label: the caller\'s @labels live on
        .pushseg
        .segment "VDPFIX"
        .addr   :- + 1
        .popseg
.endmacro

.macro VLDA_CTRL
:       LDA     EZV_CTRL             ; unnamed label: the caller\'s @labels live on
        .pushseg
        .segment "VDPFIX"
        .addr   :- + 1
        .popseg
.endmacro

.macro VBIT_CTRL
:       BIT     EZV_CTRL             ; unnamed label: the caller\'s @labels live on
        .pushseg
        .segment "VDPFIX"
        .addr   :- + 1
        .popseg
.endmacro

; TMS_WAIT_VBLANK -- (POM1 tms9918.inc WAIT_VBLANK_SAFE) bounded wait on the status frame flag F (bit 7):
; ~65536 polls (~0.4 s) at most, then gives up (POM1's hang-proof variant,
; identical when F arrives). Preserves A/X/Y.
.macro TMS_WAIT_VBLANK
        PHA
        TXA
        PHA
        TYA
        PHA
        VBIT_CTRL               ; drain stale F flag
        LDX     #0
        LDY     #0
@vw_safe:
        VBIT_CTRL               ; poll status
        BMI     @vd_safe        ; F=1 -> VBlank reached, done
        INX
        BNE     @vw_safe
        INY
        BNE     @vw_safe        ; ~65536 polls elapsed -> give up (no hang)
@vd_safe:
        PLA
        TAY
        PLA
        TAX
        PLA
.endmacro

.endif  ; _EZVDP_INC_LOADED_
