; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; hgr_pages.inc -- draw page chosen by patching the row-table operands
; ============================================================================
; Include at the TOP of the program (before any site). Then mark every
; instruction that reads the high-byte row table:
;
;           HGR_HI_SITE
;           LDA     hgr_hi,X            ; any abs,X / abs,Y opcode
;
; A site defines symbols, and ca65 ends the scope of @ labels at any symbol
; definition: treat HGR_HI_SITE like a label (no @ label used across it).
;
; Include hgr_pages.asm AFTER the last site: hgr_select_page rewrites
; the operand of every marked instruction to hgr_hi (page 1) or hgr_hi2
; (page 2, the same rows + $20).
;
; Cost: ~8 cycles per site per page change (7 sites in DIRTBIKE: ~60
; cycles a frame), nothing per access. The alternatives in this library:
; hgr_flip.asm rewrites the 192 entries (EOR #$60, ~3 500 cycles a change,
; any number of readers, hgr_hi must be writable); a page offset added at
; every access costs a few cycles each time. The PHYSICS demo used the
; latter ($65 drawpg / $73 pgoff).
;
; lib/hgr routines that read hgr_hi (hgr_line.asm) mark their sites
; themselves when this file is included.
; ============================================================================

.ifndef _HGR_PAGES_INC_LOADED_
_HGR_PAGES_INC_LOADED_ = 1

HGR_HI_SITES .set 0

.macro HGR_HI_SITE
.ifdef _HGR_PAGES_ASM_LOADED_
        .error "HGR_HI_SITE after hgr_pages.asm: that site would never be patched"
.endif
        .ident(.sprintf("hgr_hi_site%d", HGR_HI_SITES)) = *
HGR_HI_SITES .set HGR_HI_SITES + 1
.endmacro

.endif  ; _HGR_PAGES_INC_LOADED_
