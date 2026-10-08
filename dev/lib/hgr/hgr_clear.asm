; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; =============================================
; hgr_clear.asm - clear the Apple II HGR page 1
; =============================================
; clear_hgr - zero $2000-$3FFF (8 KB) with HGR_CLEAR_LOOP (lib/apple2/hgr.asm,
;             pulled in here if needed: its routines only assemble when
;             referenced). No zero page. Clobbers A, X, Y. ~46 000 cycles.
; Assembled only if clear_hgr was referenced before the include (.ifref).
; =============================================
.ifndef _HGR_ASM_LOADED_
.include "hgr.asm"
.endif

.ifref clear_hgr
clear_hgr:
        LDA     #$00
        LDX     #$20
        HGR_CLEAR_LOOP
        RTS
.endif
