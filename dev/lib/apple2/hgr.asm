; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; hgr.asm -- deterministic hi-res display setup for the Apple II
; ============================================================================
;   JSR hgr_init         GRAPHICS + HIRES + PAGE1 + full screen
;   JSR hgr_init_clear   same, but BLANK-FIRST: clears HGR page 1
;                        ($2000-$3FFF) while the display still shows TEXT,
;                        then flips — RAM left over from DOS, BASIC or a
;                        previous program never flashes on screen
;   Optional HGR_CLEAR_ROUTINE replaces the built-in page-1 clear loop;
;   the caller must select page 1 for that routine before hgr_init_clear.
;   JSR hgr_page1        display page 1 ($2000)
;   JSR hgr_page2        display page 2 ($4000)
;   JSR text_restore     TEXT + full screen + PAGE1 (then e.g. JMP apple2_exit)
;
; No V-blank input on a II/II+: draw on the hidden page and flip.
;
; Built-in routines use no zero page. A custom HGR_CLEAR_ROUTINE may use
; scratch ZP. Clobbers A (and X for the built-in hgr_init_clear).
; Caller responsibility: .include "apple2.inc" first.
; ============================================================================

.ifndef _HGR_ASM_LOADED_
_HGR_ASM_LOADED_ = 1

.segment "CODE"

hgr_init:
        JSR     native_video
        LDA     TXTCLR
        LDA     HIRES
        LDA     LOWSCR
        LDA     MIXCLR
        RTS

hgr_init_clear:
        JSR     native_video
        LDA     TXTSET          ; keep showing text while we scrub
        LDA     LOWSCR
.ifdef HGR_CLEAR_ROUTINE
        JSR     HGR_CLEAR_ROUTINE
.else
        LDA     #$00
        TAX
@clr:
.repeat 32, I
        STA     $2000 + (I * $100), X
.endrepeat
        INX
        BNE     @clr
.endif
        JMP     hgr_init

hgr_page1:
        LDA     LOWSCR
        RTS

hgr_page2:
        LDA     HISCR
        RTS

text_restore:
        JSR     native_video
        LDA     TXTSET
        LDA     MIXCLR
        LDA     LOWSCR
        RTS

; Main bank entry; no ZP/stack bank switching. ROM machine ID: Apple TN #7.
native_video:
        LDA     $FBB3
        CMP     #$06
        BNE     @done
        LDA     #0
        STA     RAMRDOFF
        STA     RAMWRTOFF
        STA     STORE80OFF
        STA     COL80OFF
        BIT     DHIRES_OFF
@done:  RTS

.endif  ; _HGR_ASM_LOADED_
