; ============================================================================
; a2logo.inc -- the Apple-1 names the LOGO sources use, mapped onto the Apple II
; ============================================================================
; Replaces `.include "apple1.inc"` in logo.s, math.asm and buffer_editor.asm.
; Wozmon's ECHO and the Monitor's COUT share the same contract -- A = char with
; bit 7 set, A/X/Y preserved, $8D = carriage return -- so the interpreter's
; many `ORA #$80 / JSR ECHO` sites run unchanged. With the //e 80-column
; firmware active, COUT prints in 80 columns.
; ============================================================================
.ifndef _A2LOGO_INC_LOADED_
_A2LOGO_INC_LOADED_ = 1

.include "apple2.inc"

ECHO     = COUT

.endif
