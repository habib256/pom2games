; ============================================================================
; zp.inc -- shared zero-page convention for lib/apple2 (+ machine-agnostic libs)
; ============================================================================
; Same slot names and order as POM1's dev/lib/apple1/zp.inc, so libraries and
; programs written against that convention (tmp, tmp2, print_ptr_*, mul_*,
; prng_*) assemble unchanged. The difference is WHERE they land.
;
; On the Apple-1 the pool is pinned at $00-$07. On the Apple II the zero page
; belongs to the Monitor ($20-$4F), DOS 3.3 and Applesoft ($50-$FF), so the
; pool is simply the first 8 bytes of your ZEROPAGE segment, and the linker
; config decides the address. dev/cc65/apple2_hgr.cfg starts ZEROPAGE at $50:
; clear of the Monitor, so COUT / RDKEY / PRBYTE keep working while the
; program runs; Applesoft's bytes are only borrowed (exit.asm restores them).
;
; Layout (first 8 bytes of ZEROPAGE, declaration order):
;   +0 tmp           general scratch
;   +1 tmp2          general scratch
;   +2 print_ptr_lo  lib/apple2/print.asm
;   +3 print_ptr_hi
;   +4 mul_tmp       multiply helpers
;   +5 mul_res0
;   +6 prng_lo       PRNG helpers
;   +7 prng_hi
;
; Usage rules (unchanged from the Apple-1 version):
;   1. .include "zp.inc" BEFORE any other ZP allocation.
;   2. ZP-tight projects alias a slot onto existing scratch BEFORE the include;
;      the per-slot .ifndef guards skip the duplicate .res.
;   3. zp.inc does not include apple2.inc.
; ============================================================================

.ifndef _ZP_INC_LOADED_
_ZP_INC_LOADED_ = 1

.segment "ZEROPAGE"

.ifndef tmp
tmp:            .res 1
.endif
.ifndef tmp2
tmp2:           .res 1
.endif
.ifndef print_ptr_lo
print_ptr_lo:   .res 1
.endif
.ifndef print_ptr_hi
print_ptr_hi:   .res 1
.endif
.ifndef mul_tmp
mul_tmp:        .res 1
.endif
.ifndef mul_res0
mul_res0:       .res 1
.endif
.ifndef prng_lo
prng_lo:        .res 1
.endif
.ifndef prng_hi
prng_hi:        .res 1
.endif

; Exported so separately assembled modules can .importzp the same names.
.exportzp tmp, tmp2
.exportzp print_ptr_lo, print_ptr_hi
.exportzp mul_tmp, mul_res0
.exportzp prng_lo, prng_hi

.endif  ; _ZP_INC_LOADED_
