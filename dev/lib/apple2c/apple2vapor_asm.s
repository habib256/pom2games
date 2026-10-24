; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ----------------------------------------------------------------------------
; apple2vapor_asm.s — vapor lock for cc65 (see apple2vapor.h).
;
; Thin wrappers over ../apple2/vapor.asm. A separate object: only programs
; that call these pay for them. Assemble with -I dev/lib/apple2.
; ----------------------------------------------------------------------------
        .export _a2_vapor_mark, _a2_vapor_sync, _a2_vapor_count

.include "apple2.inc"

        .segment "CODE"

_a2_vapor_mark = vapor_mark

; unsigned char a2_vapor_sync(void): 0 synced, 1 timed out (the carry).
_a2_vapor_sync:
        jsr     vapor_sync
        lda     #0
        tax
        rol     a
        rts

; unsigned int a2_vapor_count(void): A = low, X = high, 0 on failure.
_a2_vapor_count = vapor_count

.include "vapor.asm"
