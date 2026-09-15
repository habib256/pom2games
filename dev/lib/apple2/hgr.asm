; ============================================================================
; hgr.asm -- deterministic hi-res display setup for the Apple II
; ============================================================================
; The built-in counterpart of POM1's dev/lib/gen2/gen2_init.asm (the GEN2 card
; is the Apple II video subsystem moved onto the Apple-1 bus, so the calls map
; one to one):
;
;   JSR hgr_init         GRAPHICS + HIRES + PAGE1 + full screen
;   JSR hgr_init_clear   same, but BLANK-FIRST: clears HGR page 1
;                        ($2000-$3FFF) while the display still shows TEXT,
;                        then flips — RAM left over from DOS, BASIC or a
;                        previous program never flashes on screen
;   JSR hgr_page1        display page 1 ($2000)
;   JSR hgr_page2        display page 2 ($4000)
;   JSR text_restore     TEXT + full screen + PAGE1 (then e.g. JMP apple2_exit)
;
;   GEN2 (Apple-1)        Apple II (this file)
;   gen2_hgr_init         hgr_init
;   gen2_hgr_init_clear   hgr_init_clear
;   gen2_text_restore     text_restore
;   LDA GEN2_PAGE1/2      LDA LOWSCR / HISCR
;   gen2_waitvbl          -- no V-blank on a II/II+: draw straight away, or
;                            draw on the hidden page and flip
;
; No zero page used. Clobbers A (and X for hgr_init_clear).
; Caller responsibility: .include "apple2.inc" first.
; ============================================================================

.ifndef _HGR_ASM_LOADED_
_HGR_ASM_LOADED_ = 1

.segment "CODE"

hgr_init:
        LDA     TXTCLR
        LDA     HIRES
        LDA     LOWSCR
        LDA     MIXCLR
        RTS

hgr_init_clear:
        LDA     TXTSET          ; keep showing text while we scrub
        LDA     LOWSCR
        LDA     #$00
        TAX
@clr:
.repeat 32, I
        STA     $2000 + (I * $100), X
.endrepeat
        INX
        BNE     @clr
        JMP     hgr_init

hgr_page1:
        LDA     LOWSCR
        RTS

hgr_page2:
        LDA     HISCR
        RTS

text_restore:
        LDA     TXTSET
        LDA     MIXCLR
        LDA     LOWSCR
        RTS

.endif  ; _HGR_ASM_LOADED_
