; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; hgr.asm -- deterministic hi-res display setup for the Apple II
; ============================================================================
;   JSR hgr_init         GRAPHICS + HIRES + PAGE1 + full screen
;   JSR hgr_init_clear   same, but BLANK-FIRST: clears HGR page 1
;                        ($2000-$3FFF) while the display still shows TEXT,
;                        then flips — RAM left over from DOS, BASIC or a
;                        previous program never flashes on screen
;   Optional HGR_CLEAR_ROUTINE replaces the built-in page-1 clear loop:
;   `HGR_CLEAR_ROUTINE = my_clear` before the include (an assignment, so the
;   routine may be defined later; a .define is textual and only works if the
;   routine comes first). The caller must select page 1 for that routine
;   before hgr_init_clear.
;   HGR_CLEAR_LOOP (macro): fill 8 KB from page X (high byte) with A, no
;   zero page -- the loop behind hgr_init_clear, lib/hgr clear_hgr and the
;   C hgr_clear. Eight absolute stores per turn, ~5.7 cycles per byte.
;   JSR hgr_page1        display page 1 ($2000)
;   JSR hgr_page2        display page 2 ($4000)
;   JSR text_restore     TEXT + full screen + PAGE1 (then e.g. JMP apple2_exit)
;
; No V-blank input on a II/II+: draw on the hidden page and flip.
;
; Built-in routines use no zero page. A custom HGR_CLEAR_ROUTINE may use
; scratch ZP. Clobbers A (and X, Y for the built-in hgr_init_clear).
; Only the routines referenced BEFORE the include are assembled (.ifref):
; include this file after the code that calls it, as every game does.
; Caller responsibility: .include "apple2.inc" first.
; ============================================================================

.ifndef _HGR_ASM_LOADED_
_HGR_ASM_LOADED_ = 1

; HGR_CLEAR_LOOP: fill 32 pages from page X (high byte, e.g. $20) with the
; byte in A. Self-modifying: the eight STA operands are patched per group of
; eight pages, so no zero page is needed. Clobbers X, Y; A is kept.
; 4 groups x 256 turns x (8 x 5 + 5) cycles = ~46 000 cycles per 8 KB.
.macro HGR_CLEAR_LOOP
        .local @grp, @lp, @s0, @s1, @s2, @s3, @s4, @s5, @s6, @s7, @cnt
        LDY     #4
        STY     @cnt+1
@grp:   STX     @s0+2
        INX
        STX     @s1+2
        INX
        STX     @s2+2
        INX
        STX     @s3+2
        INX
        STX     @s4+2
        INX
        STX     @s5+2
        INX
        STX     @s6+2
        INX
        STX     @s7+2
        INX
        LDY     #0
@lp:
@s0:    STA     $2000,Y
@s1:    STA     $2100,Y
@s2:    STA     $2200,Y
@s3:    STA     $2300,Y
@s4:    STA     $2400,Y
@s5:    STA     $2500,Y
@s6:    STA     $2600,Y
@s7:    STA     $2700,Y
        INY
        BNE     @lp
@cnt:   LDY     #4
        DEY
        STY     @cnt+1
        BNE     @grp
.endmacro

.segment "CODE"

.ifref hgr_init_clear
hgr_init_clear:
        JSR     native_video
        LDA     TXTSET          ; keep showing text while we scrub
        LDA     LOWSCR
.ifdef HGR_CLEAR_ROUTINE
        JSR     HGR_CLEAR_ROUTINE
.else
        LDA     #$00
        LDX     #>HGR1
        HGR_CLEAR_LOOP
.endif
        JMP     hgr_init
.endif

.ifref hgr_init
.ifndef hgr_init                ; a C object may alias it to an import
hgr_init:
        JSR     native_video
        LDA     TXTCLR
        LDA     HIRES
        LDA     LOWSCR
        LDA     MIXCLR
        RTS
.endif
.endif

.ifref hgr_page1
hgr_page1:
        LDA     LOWSCR
        RTS
.endif

.ifref hgr_page2
hgr_page2:
        LDA     HISCR
        RTS
.endif

.ifref text_restore
text_restore:
        JSR     native_video
        LDA     TXTSET
        LDA     MIXCLR
        LDA     LOWSCR
        RTS
.endif

; Main bank entry; no ZP/stack bank switching. ROM machine ID: Apple TN #7.
.ifref native_video
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
.endif

.endif  ; _HGR_ASM_LOADED_
