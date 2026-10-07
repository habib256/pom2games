; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; hgr_flip.asm -- double buffering by rewriting the hgr_hi scanline table
; ============================================================================
; Every drawing routine of the program reads hgr_lo / hgr_hi (hgr_scanline.inc,
; which must then live in a WRITABLE segment). Switching the draw page is one
; pass over hgr_hi: $2x <-> $4x is EOR #$60 per entry (~3 500 cycles, ~1/5 of
; a frame), far cheaper than parameterising every routine.
;
;   hgr_draw_hidden    draw page := the page NOT on screen (nothing changes
;                      on screen; the previous picture stays up)
;   hgr_show_draw      show the draw page (one soft-switch read). It stays
;                      the draw page, so small updates that follow a full
;                      screen land on the visible page
;   hgr_set_draw_page  A = 0 (page 1) or PAGE2_EOR (page 2); no-op if the
;                      table already addresses that page. Clobbers A, X.
;   hgr_draw_page      byte: the page hgr_hi addresses now (0 / PAGE2_EOR).
;                      Kept next to the code, not in zero page, so it stays
;                      true for as long as the table itself (a re-entry
;                      without reloading the file finds both consistent)
;   hgr_front_page     byte: the page on screen (0 / PAGE2_EOR). Reserved in
;                      BSS unless the program defined it before the include
;                      (a zero-page alias is fine); initialise it at boot
;                      together with the first hgr_set_draw_page.
;
; PAGE2_EOR defaults to $60. Used by maze3d and MICRO-SOKOBAN; the C runtime
; does the same in hgr_rows_asm.s (hgr_flip_rows).
; ============================================================================

.ifndef _HGR_FLIP_LOADED_
_HGR_FLIP_LOADED_ = 1

.ifndef PAGE2_EOR
PAGE2_EOR = $60
.endif

.ifndef hgr_front_page
.segment "BSS"
hgr_front_page: .res 1
.endif

.segment "CODE"

hgr_draw_hidden:
        LDA     hgr_front_page
        EOR     #PAGE2_EOR      ; the page that is not on screen
        ; fall through

hgr_set_draw_page:
        CMP     hgr_draw_page
        BEQ     @done
        STA     hgr_draw_page
        LDX     #191
@lp:    LDA     hgr_hi,X
        EOR     #PAGE2_EOR
        STA     hgr_hi,X
        DEX
        CPX     #$FF            ; 191 > 127: BPL would stop at once
        BNE     @lp
@done:  RTS

hgr_show_draw:
        LDA     hgr_draw_page
        STA     hgr_front_page
        BNE     @p2
        LDA     LOWSCR          ; show page 1
        RTS
@p2:    LDA     HISCR           ; show page 2
        RTS

hgr_draw_page:
        .byte   0               ; 0 = hgr_hi addresses page 1

.endif  ; _HGR_FLIP_LOADED_
