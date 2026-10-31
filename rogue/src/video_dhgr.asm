; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; video_dhgr.asm -- ROGUE's DHGR back-end: the //e / //c double hi-res screen
; ============================================================================
; Implements docs/VIDEO_API.md by emulating the core's virtual TMS9918, on two
; DHGR pages (double buffering), in two ways:
;
;   - the GAME VIEW (no text in name rows 0..19): the X2 way (video_x2.asm,
;     POM1's ROGUE X2): a 9 x 5 window of big 14 x 32 cells centre-locked on
;     the hero, lines 0..159, drawn on the hidden page, then shown; rows
;     20..23 (the HUD) by the text engine below, on the same page;
;   - a FULL PAGE (title, briefing, bag, help, death, victory: text in rows
;     0..19): the TMS picture halved, by the text engine, straight onto the
;     page shown (each byte written once with its final value: no flicker),
;     the title's "ROGUE" as a big banner.
;
; The text engine (2026-10-31, before X2: the whole screen):
;   - the virtual VRAM ($1800-$1AFF names, $1B00-$1B7F sprite table) is a real
;     copy at the SAME addresses in main RAM (segment DHGRBSS at $1800):
;     vid_addr just points vid_put's operands there;
;   - vid_put compares the byte with the copy: unchanged, 27 cycles;
;     changed, it is stored and its text row flagged for both pages (a
;     sprite table byte flags the table; a text name in rows 0..19 makes the
;     screen a full page);
;   - per page (state blocks at $0800 / $0C00, the code's operands patched
;     by dg_use_page): what the page shows (dg_shown, names through dg_san:
;     a blank character is any blank one), the sprite list drawn there, the
;     rows touched since it was drawn;
;   - an update compares each touched row's names with what the page shows,
;     the sprite list with the one drawn there (each moved / recoloured /
;     new / gone sprite dirties its old and new boxes); each different name
;     marks the one or two 7-pixel groups under it (one byte a group, 20 a
;     row); then each run of dirty groups of each row is composed for its 8
;     lines straight into screen bytes (dg_lb, "stream" order: byte 2o = aux
;     o, 2o+1 = main o): characters from per-phase tables, sprites over them
;     (the last entry first: entry 0 on top, as on the chip), and written
;     (aux bytes with IRQs masked, then main ones). Every byte of a run is
;     written once with its final value.
;
; Geometry of the text engine: the TMS picture halved horizontally. 1 DHGR
; colour pixel = 2 TMS pixels, 1 line = 1 line: the 256x192 picture is
; 128x192 colour pixels at x = 6..133 (6 black pixels left and right). A
; character = 4 x 8, a sprite = 8 x 16 at (6 + X/2, Y). Seven colour pixels =
; one group of 4 bytes (aux 2g, main 2g, aux 2g+1, main 2g+1 of the line), 20
; groups a line. Pixel x = dots 4x..4x+3 of the line's 80 x 7 dots: character
; c = 16 dots from dot 24 + 16c, i.e. bit (24 + 16 p) mod 7 of a byte for
; c = 7q + p (7 phases). Data (tools/tiles_dhgr.py -> video_dhgr_data.inc,
; see its docstring).
;
; Machine: //e with 128 KB (extended 80-column card) or //c; DHGR pages 1
; ($2000-$3FFF) and 2 ($4000-$5FFF), main + aux. Every routine returns with
; RAMRD/RAMWRT main and the I flag it found.
; ============================================================================

DG_X0      = 6                  ; first colour pixel of the TMS picture
DG_VRAM    = $1800              ; = the virtual addresses (DHGRBSS starts here)
DG_SAT     = $1B00
DG_RAMWRT_AUX  = $C005
DG_RAMWRT_MAIN = $C004
DG_LW      = 80                 ; stream bytes of a line
DG_PD      = $400               ; page 1's state block = page 0's + DG_PD
DG_UNKNOWN = $FE                ; dg_shown: never a dg_san value (redraw)
; line l of dg_lb is at dg_lb + l / 3 * 256 + l .mod 3 * DG_LW: 3 lines a
; page (no page crossed by an indexed access)

; An instruction on a per-page array (abs,X), its operand's high byte noted
; in DGFIX: dg_use_page moves it by DG_PD. (Unnamed label: the caller's
; @labels live on.)
.macro DGX ins, addr
:       ins     addr,X
        .pushseg
        .segment "DGFIX"
        .addr   :- + 2
        .popseg
.endmacro

.import __DGFIX_RUN__, __DGFIX_SIZE__

.segment "ZEROPAGE"
dg_ptr:   .res 2                ; scratch page pointer
dg_tp:    .res 2                ; dg_touch of the current page
dg_np:    .res 2                ; names of the row
dg_dp:    .res 2                ; dirty groups of the row
dg_bp:    .res 2                ; sprite: its first byte in a dg_lb line
dg_sh:    .res 2                ; sprite: its left halves (dg_sph)
dg_sl:    .res 2                ; its right halves (dg_spl)
dg_cz:    .res 6                ; its ink in stream bytes k .. k + 5
dg_row:   .res 1                ; text row being rebuilt, 0..23
dg_y:     .res 1                ; its first screen line
dg_g0:    .res 1                ; first group of the run (0..19)
dg_g1:    .res 1                ; last group
dg_g:     .res 1                ; run scan
dg_c0:    .res 1                ; first character column of the run
dg_c1:    .res 1                ; last + 1
dg_cn:    .res 1                ; characters left to compose
dg_bmin:  .res 1                ; 4 * dg_g0: first stream byte of the run
dg_bmax:  .res 1                ; 4 * dg_g1 + 4
dg_si:    .res 1                ; sprite loop
dg_st:    .res 1                ; sprite row
dg_ln:    .res 1                ; line in the text row
dg_lc:    .res 1                ; sprite lines left
dg_t:     .res 1
dg_u:     .res 1
dg_pgrow: .res 1                ; 8 * (cursor page - $18): text row base
dg_sa:    .res 1                ; vid_put's A / X / Y
dg_sx:    .res 1
dg_cpg:   .res 1                ; the page the state operands point at (0/1)
dg_pgo:   .res 1                ; its screen: $00 (page 1) or $20 (page 2)
dg_pgsh:  .res 1                ; >dg_shown of it
dg_rmin:  .res 1                ; first text row the engine draws (0 / 20)

; per-page state: page 0 here, page 1 at + DG_PD (dg_use_page)
.segment "DGPAGE"               ; $0800, rogue_dhgr.cfg
dg_shown: .res 768              ; the names the page shows, as dg_san
                                ; (every blank character = $FF, DG_UNKNOWN)
dg_drawn: .res 128              ; sprite table as last drawn there
dg_touch: .res 24               ; rows written since the page was drawn
          .res DG_PD - 920
dg_page1: .res DG_PD            ; page 1's copy of the above

.segment "DHGRBSS"              ; $1800, rogue_dhgr.cfg
dg_vram:  .res 1024             ; names $1800-$1AFF, sprites $1B00-$1B7F,
                                ; then room for a cursor run past the end
dg_lb:    .res 768              ; $1C00: the 8 lines of a text row, 80 stream
                                ; bytes each (2o = aux offset o, 2o+1 = main
                                ; o) see DG_LW, + a sprite's overrun
dg_rsn:   .res 1
dg_nold:  .res 1                ; bytes of dg_drawn in use (4 x entries), of
                                ; the current page (dg_noldp: both)
dg_on:    .res 1                ; DHGR shown
dg_txt:   .res 1                ; a text name in rows 0..19: a full page
dg_chg:   .res 1                ; a byte changed since the last X2 frame
dg_vis:   .res 1                ; the page shown (0 / 1)
dg_vbl:   .res 1                ; 1: $C019 tells the vertical blank (//e)
dg_satdp: .res 2                ; per page: the sprite table was written
dg_noldp: .res 2                ; per page: dg_nold
dg_kindp: .res 2                ; per page: 0 a full page / black, 1 X2 view
dg_bannp: .res 2                ; per page: the title banner is on it

.segment "BSS"
dg_dg:    .res 480              ; dirty groups: row r, group g at 20 r + g
dg_rd:    .res 24               ; rows with dirty groups
dg_rsl:   .res 32               ; the row's sprites (dg_drawn offsets)
dg_chs:   .res 80               ; the run's names (dg_san), column 7q+p at 16q+p

.assert <dg_shown = 0, error, "dg_shown: page aligned"
.assert dg_touch + 24 <= dg_page1, error, "DGPAGE: page 0 block too big"

.segment "LCCODE"

; ----------------------------------------------------------------------------
; vid_init -- both DHGR pages black, page 1 shown; empty virtual screen.
; ----------------------------------------------------------------------------
vid_init:
        LDA     #0
        JSR     dg_use_page     ; the operands back to page 0
        LDA     #0
        TAX
@clr:   STA     dg_vram,X       ; names + sprite table + spare = 0
        STA     dg_vram+$100,X
        STA     dg_vram+$200,X
        STA     dg_vram+$300,X
        STA     dg_lb,X         ; the line buffer (its bytes 0..2 stay 0)
        STA     dg_lb+$100,X
        STA     dg_lb+$200,X
        INX
        BNE     @clr
        LDA     #$D0
        STA     DG_SAT          ; no sprite
        LDX     #1
        LDA     #0
@pg:    STA     dg_satdp,X
        STA     dg_noldp,X
        STA     dg_kindp,X
        STA     dg_bannp,X
        DEX
        BPL     @pg
        STA     dg_nold
        STA     dg_txt
        STA     dg_vis
        LDA     $FBC0           ; //c: 0 (no VBL register to poll)
        BEQ     :+
        LDA     #1
:       STA     dg_vbl
        LDA     #1
        STA     dg_chg
        JSR     dg_clean_all
        JSR     x2_init         ; masks, tile pictures, no cell drawn
        JSR     dg_black        ; both banks of both pages
        STA     STORE80OFF      ; PAGE2 = display page, not a bank
        STA     RAMRDOFF
        STA     RAMWRTOFF
        STA     COL80ON
        BIT     MIXCLR
        BIT     LOWSCR
        BIT     HIRES
        BIT     DHIRES_ON       ; AN3 off: double resolution
        BIT     TXTCLR
        LDA     #1
        STA     dg_on
        LDA     #<DG_VRAM       ; cursor somewhere valid
        LDX     #>DG_VRAM
        JMP     vid_addr

; vid_off -- back to the 40-column text page 1.
vid_off:
        BIT     TXTSET
        BIT     LOWSCR
        BIT     DHIRES_OFF
        STA     COL80OFF
        LDA     #0
        STA     dg_on
        RTS

; vid_clear -- every name = 0, every row touched (for both pages); no text.
vid_clear:
        LDA     #1
        STA     dg_chg
        LDA     #0
        STA     dg_txt
        TAX
@lp:    STA     dg_vram,X
        STA     dg_vram+$100,X
        STA     dg_vram+$200,X
        INX
        BNE     @lp
        LDX     #23
        LDA     #1
@t:     STA     dg_touch,X
        STA     dg_touch+DG_PD,X
        DEX
        BPL     @t
        RTS

; dg_redraw_all -- (tests, profiling) both pages forgotten: the next updates
; redraw everything (X2 cells, every text row).
dg_redraw_all:
        LDA     #1
        STA     dg_chg
        JSR     @one
        LDA     #0
@one:   JSR     dg_use_page
        LDX     dg_cpg
        JSR     x2_forget
        LDX     #0
        LDY     #23
        JMP     dg_unknown_rows

dg_clean_all:
        LDX     #0
@c:     LDA     #$FF            ; the pages are black: blank characters
        STA     dg_shown,X
        STA     dg_shown+$100,X
        STA     dg_shown+$200,X
        STA     dg_shown+DG_PD,X
        STA     dg_shown+DG_PD+$100,X
        STA     dg_shown+DG_PD+$200,X
        LDA     #0
        STA     dg_dg,X
        STA     dg_dg+480-256,X
        INX
        BNE     @c
        LDX     #23
@t:     STA     dg_touch,X
        STA     dg_touch+DG_PD,X
        STA     dg_rd,X
        DEX
        BPL     @t
        RTS

; vid_sprites_off -- SAT[0].Y = $D0.
vid_sprites_off:
        LDA     #$D0
        STA     DG_SAT
        LDA     #1
        STA     dg_chg
        STA     dg_satdp
        STA     dg_satdp+1
        RTS

; vid_wait_frame -- nothing to wait for: the picture is composed in vid_idle
; (the core calls this before rebuilding the whole map / a full page; drawing
; there would show half-built pictures). Keeps A, X, Y.
vid_wait_frame:
        RTS

; ----------------------------------------------------------------------------
; dg_use_page -- A = 0 / 1: the text engine's state operands (DGFIX sites,
; dg_tp, dg_pgsh, dg_nold) and its screen (dg_pgo) become page A's.
; ----------------------------------------------------------------------------
dg_use_page:
        CMP     dg_cpg
        BEQ     @same
        PHA
        LDX     dg_cpg
        LDA     dg_nold         ; the page left keeps its own
        STA     dg_noldp,X
        PLA
        STA     dg_cpg
        TAX
        LDA     dg_noldp,X
        STA     dg_nold
        LDA     #<(-(DG_PD >> 8))
        CPX     #0
        BEQ     :+
        LDA     #DG_PD >> 8
:       STA     dg_t            ; + or - DG_PD on each operand's high byte
        LDX     #0
@fx:    LDA     __DGFIX_RUN__,X
        STA     dg_ptr
        LDA     __DGFIX_RUN__+1,X
        STA     dg_ptr+1
        LDY     #0
        LDA     (dg_ptr),Y
        CLC
        ADC     dg_t
        STA     (dg_ptr),Y
        INX
        INX
        CPX     #<__DGFIX_SIZE__
        BNE     @fx
@same:  LDA     dg_cpg
        BEQ     :+
        LDA     #$20
:       STA     dg_pgo
        LDA     dg_cpg
        ASL
        ASL
        ADC     #>dg_shown      ; C = 0
        STA     dg_pgsh
        ADC     #>dg_touch - >dg_shown
        STA     dg_tp+1
        LDA     #<dg_touch
        STA     dg_tp
        RTS

; ----------------------------------------------------------------------------
; vid_addr -- A = low, X = high byte of a virtual address ($40 bit ignored).
; Keeps X, Y. Outside $1800-$1BFF the cursor goes to the spare bytes.
; ----------------------------------------------------------------------------
vid_addr:
        STA     dg_cmp+1
        TXA
        AND     #$3F
        CMP     #>DG_VRAM
        BCC     @out
        CMP     #>DG_VRAM + 4
        BCC     @in
@out:   LDA     #$80            ; $1B80: written, never shown
        STA     dg_cmp+1
        LDA     #>DG_SAT
@in:    STA     dg_cmp+2
        STA     dg_sta+2
        ASL
        ASL
        ASL
        SEC
        SBC     #8 * >DG_VRAM
        STA     dg_pgrow
        RTS

; ----------------------------------------------------------------------------
; vid_put -- A at the cursor, cursor + 1. Keeps A, X, Y and P. An unchanged
; byte: 27 cycles; a changed name is stored and its row flagged for both
; pages (dg_touch), a text name (>= 32) in rows 0..19 makes the screen a
; full page (dg_txt); a changed sprite table byte flags the table for both.
; ----------------------------------------------------------------------------
vid_put:
        PHP
dg_cmp: CMP     DG_VRAM         ; operand = cursor (vid_addr)
        BNE     dg_vp_ch
        INC     dg_cmp+1
        BEQ     dg_vp_hi
        PLP
        RTS
dg_vp_ch:
        STX     dg_sx
        LDX     dg_cmp+1
        STX     dg_sta+1
dg_sta: STA     DG_VRAM         ; high byte: vid_addr / dg_vp_hi
        STA     dg_sa
        LDA     #1
        STA     dg_chg          ; the X2 frame: to compute again
        LDA     dg_lsr5,X
        ORA     dg_pgrow
        CMP     #24
        BCS     dg_vp_sat       ; the sprite page (or past it)
        TAX                     ; a name: its row, both pages
        LDA     #1
        STA     dg_touch,X
        STA     dg_touch+DG_PD,X
        CPX     #20
        BCS     dg_vp_done
        LDA     dg_sa
        CMP     #32
        BCC     dg_vp_done
        STA     dg_txt          ; text in the map rows: a full page
dg_vp_done:
        LDA     dg_sa
        LDX     dg_sx
        INC     dg_cmp+1
        BEQ     dg_vp_hi
        PLP
        RTS
dg_vp_sat:
        CMP     #32
        BCS     dg_vp_done      ; past the sprite page
        LDA     #1
        STA     dg_satdp
        STA     dg_satdp+1
        BNE     dg_vp_done      ; always
dg_vp_hi:
        INC     dg_cmp+2
        INC     dg_sta+2
        STA     dg_sa
        LDA     dg_pgrow
        CMP     #32
        BCS     :+              ; past the sprite page: stays "past"
        ADC     #8
        STA     dg_pgrow
:       LDA     dg_sa
        PLP
        RTS

; ----------------------------------------------------------------------------
; vid_idle -- bring the screen up to the virtual one. Keeps X, Y.
; ----------------------------------------------------------------------------
vid_idle:
        TXA
        PHA
        TYA
        PHA
        JSR     dg_flush
        PLA
        TAY
        PLA
        TAX
        RTS

; dg_flush -- the game view: video_x2.asm; a full page: on the page shown.
dg_flush:
        LDA     dg_on
        BEQ     @rts
        LDA     dg_txt
        BNE     dg_page
        JMP     x2_idle
@rts:   RTS

dg_page:
        LDA     dg_vis
        JSR     dg_use_page
        LDX     dg_cpg
        LDA     dg_kindp,X
        BEQ     :+
        LDA     #0              ; the X2 view was there: every row redrawn
        STA     dg_kindp,X
        JSR     x2_forget
        LDX     #0
        LDY     #19
        JSR     dg_unknown_rows
:       LDA     #0
        STA     dg_rmin
        JSR     dg_banner
        ; fall through

; dg_text_update -- the text engine on page dg_cpg, rows dg_rmin..23: the
; sprite diff, the name diff, then each row with dirty groups.
dg_text_update:
        LDX     dg_cpg
        LDA     dg_satdp,X
        BEQ     :+
        LDA     #0
        STA     dg_satdp,X
        JSR     dg_sat_diff
:       JSR     dg_name_diff
        LDX     dg_cpg
        LDA     dg_bannp,X
        BEQ     :+
        JSR     dg_bann_rows    ; the banner's rows: nothing to draw there
:       LDX     dg_rmin
@r:     LDA     dg_rd,X
        BEQ     @next
        LDA     #0
        STA     dg_rd,X
        STX     dg_row
        JSR     dg_do_row
        LDX     dg_row
@next:  INX
        CPX     #24
        BNE     @r
        RTS

; dg_unknown_rows -- rows X..Y of page dg_cpg: shown as "unknown" (every
; group redrawn at the next update), touched.
dg_unknown_rows:
        STX     dg_t
        STY     dg_u
@r:     LDA     dg_t
        LSR
        LSR
        LSR
        CLC
        ADC     dg_pgsh
        STA     dg_ptr+1
        LDA     dg_t
        ASL
        ASL
        ASL
        ASL
        ASL
        STA     dg_ptr
        LDY     #31
        LDA     #DG_UNKNOWN
:       STA     (dg_ptr),Y
        DEY
        BPL     :-
        LDY     dg_t
        LDA     #1
        STA     (dg_tp),Y
        INY
        STY     dg_t
        CPY     dg_u
        BCC     @r
        BEQ     @r
        RTS

; ----------------------------------------------------------------------------
; The title's banner: names row 4 = "ROGUE" at column 13 (title_table) with a
; blank on each side -> rows 3..6 of the page are the big banner (x2_banner)
; instead of text, until the names change.
; ----------------------------------------------------------------------------
DG_BANNER_AT = DG_VRAM + 32 * 4 + 13

dg_banner:
        LDX     #4
@c:     LDA     DG_BANNER_AT,X
        CMP     dg_ban_txt,X
        BNE     @off
        DEX
        BPL     @c
        LDA     DG_BANNER_AT-1
        ORA     DG_BANNER_AT+5
        BNE     @off
        LDX     dg_cpg
        LDA     dg_bannp,X
        BNE     @rts
        LDA     #1
        STA     dg_bannp,X
        JSR     x2_banner       ; lines 24..55 of the page
        LDX     #3
        LDY     #6
        JSR     dg_unknown_rows ; (the names under it: redrawn when it goes)
        LDA     #0
        BEQ     @tch            ; always: rows 3..6 untouched
@off:   LDX     dg_cpg
        LDA     dg_bannp,X
        BEQ     @rts
        LDA     #0
        STA     dg_bannp,X
        LDA     #1              ; gone: rows 3..6 redrawn
@tch:   LDY     #3
:       STA     (dg_tp),Y
        INY
        CPY     #7
        BNE     :-
@rts:   RTS

; dg_bann_rows -- rows 3..6 under the banner: no dirty group left.
dg_bann_rows:
        LDA     #0
        LDX     #20 * 4 - 1
:       STA     dg_dg+20*3,X
        DEX
        BPL     :-
        LDX     #3
:       STA     dg_rd+3,X
        DEX
        BPL     :-
        RTS

dg_ban_txt: .byte "ROGUE"

; dg_dirty_row -- dg_dp = the dirty groups of row X, the row flagged. Keeps X, Y.
dg_dirty_row:
        LDA     dg_dlo,X
        STA     dg_dp
        LDA     dg_dhi,X
        STA     dg_dp+1
        LDA     #1
        STA     dg_rd,X
        RTS

; dg_name_diff -- each touched row from dg_rmin: names that differ from what
; the page shows dirty their groups and are copied there (the row's tables
; are patched into the loop: 15 cycles an unchanged name).
dg_name_diff:
        LDX     dg_rmin
@r:     DGX     LDA, dg_touch
        BNE     @row
@next:  INX
        CPX     #24
        BNE     @r
        RTS
@row:   LDA     #0
        DGX     STA, dg_touch
        STA     dg_u            ; nothing changed yet
        STX     dg_row
        LDA     dg_dlo,X
        STA     @d0+1
        STA     @d1+1
        LDA     dg_dhi,X
        STA     @d0+2
        STA     @d1+2
        TXA                     ; names, shown + 32 * row
        LSR
        LSR
        LSR
        TAY
        CLC
        ADC     #>DG_VRAM
        STA     @nm+2
        TYA
        ADC     dg_pgsh         ; C = 0
        STA     @s0+2
        STA     @s1+2
        TXA
        ASL
        ASL
        ASL
        ASL
        ASL
        STA     @nm+1
        STA     @s0+1           ; (dg_shown is page aligned)
        STA     @s1+1
        LDY     #31
@c:
@nm:    LDX     DG_VRAM,Y
        LDA     dg_san,X        ; blank characters are all the same black
@s0:    CMP     dg_shown,Y
        BNE     @ch
@same:  DEY
        BPL     @c
        LDX     dg_row
        LDA     dg_u
        BEQ     @next
        STA     dg_rd,X
        BNE     @next           ; always
@ch:
@s1:    STA     dg_shown,Y
        LDA     #1
        STA     dg_u
        LDX     dg_cg0,Y        ; first and last group under column Y
@d0:    STA     dg_dg,X
        LDX     dg_cg1,Y
@d1:    STA     dg_dg,X
        BNE     @same           ; always

; ----------------------------------------------------------------------------
; dg_sat_diff -- the new sprite list against the one drawn on the page: each
; entry that differs dirties its old box and its new box (rows from
; dg_rmin); then the new list is the drawn one.
; ----------------------------------------------------------------------------
dg_sat_diff:
        LDX     #0
@n:     LDA     DG_SAT,X
        CMP     #$D0
        BEQ     @nend
        INX
        INX
        INX
        INX
        CPX     #128
        BNE     @n
@nend:  STX     dg_nnew
        LDX     #0
@e:     CPX     dg_nnew
        BCC     @isnew
        CPX     dg_nold
        BCS     @copy           ; past both lists
        JSR     dg_mark_old     ; gone
        JMP     @next
@isnew: CPX     dg_nold
        BCS     @new            ; appeared
        LDA     DG_SAT,X
        DGX     CMP, dg_drawn
        BNE     @both
        LDA     DG_SAT+1,X
        DGX     CMP, dg_drawn+1
        BNE     @both
        LDA     DG_SAT+2,X
        DGX     CMP, dg_drawn+2
        BNE     @both
        LDA     DG_SAT+3,X
        DGX     CMP, dg_drawn+3
        BEQ     @next
@both:  JSR     dg_mark_old
@new:   LDA     DG_SAT,X
        LDY     DG_SAT+1,X
        JSR     dg_mark_box
@next:  INX
        INX
        INX
        INX
        BNE     @e              ; always (X <= 128)
@copy:  LDX     dg_nnew
        STX     dg_nold
        BEQ     @done
@cp:    DEX
        LDA     DG_SAT,X
        DGX     STA, dg_drawn
        TXA
        BNE     @cp
@done:  RTS

dg_mark_old:
        DGX     LDA, dg_drawn
        DGX     LDY, dg_drawn+1
        ; fall through
; dg_mark_box -- A = Y, Y = X of a 16x16 sprite: dirty its box (2 or 3
; groups x 2 or 3 text rows, from row dg_rmin). Keeps X.
dg_mark_box:
        CMP     #192
        BCS     @off            ; below the picture (or "negative")
        STX     dg_u
        STA     dg_t            ; top line
        CLC
        ADC     #15
        CMP     #192
        BCC     :+
        LDA     #191
:       LSR
        LSR
        LSR
        STA     dg_c1           ; last text row
        CMP     dg_rmin
        BCC     @none           ; above the rows drawn
        TYA
        LSR
        TAY
        LDA     dg_hg0,Y        ; groups of its left and right pixels
        STA     dg_g0
        LDA     dg_hg1,Y
        STA     dg_g1
        LDA     dg_t
        LSR
        LSR
        LSR
        CMP     dg_rmin
        BCS     :+
        LDA     dg_rmin
:       TAX                     ; first text row
@row:   JSR     dg_dirty_row
        LDY     dg_g0
@grp:   STA     (dg_dp),Y       ; A = 1
        INY
        CPY     dg_g1
        BCC     @grp
        BEQ     @grp
        INX
        CPX     dg_c1
        BCC     @row
        BEQ     @row
@none:  LDX     dg_u
@off:   RTS

; ----------------------------------------------------------------------------
; dg_do_row -- rebuild every run of dirty groups of text row X (= dg_row).
; ----------------------------------------------------------------------------
dg_do_row:
        LDA     dg_dlo,X
        STA     dg_dp
        LDA     dg_dhi,X
        STA     dg_dp+1
        TXA                     ; names: $1800 + 32 * row
        LSR
        LSR
        LSR
        CLC
        ADC     #>DG_VRAM
        STA     dg_np+1
        TXA
        ASL
        ASL
        ASL
        STA     dg_y
        ASL
        ASL
        STA     dg_np
        JSR     dg_row_sprites
        LDY     #0
@scan:  LDA     (dg_dp),Y
        BNE     @run
        INY
        CPY     #20
        BNE     @scan
        RTS
@run:   STY     dg_g0
@ext:   LDA     #0              ; clean as we go
        STA     (dg_dp),Y
        INY
        CPY     #20
        BEQ     @end
        LDA     (dg_dp),Y
        BNE     @ext
@end:   STY     dg_g
        DEY
        STY     dg_g1
        JSR     dg_strip
        LDY     dg_g
        CPY     #20
        BNE     @scan
        RTS

; dg_row_sprites -- dg_rsl = the drawn sprites crossing lines dg_y..dg_y+7
; that have something to draw, the last entry first; dg_rsn = their count.
dg_row_sprites:
        LDY     #0
        LDX     dg_nold
@s:     TXA
        BEQ     @end
        DEX
        DEX
        DEX
        DEX
        DGX     LDA, dg_drawn
        CMP     #192
        BCS     @s
        ADC     #15             ; C = 0: bottom line >= dg_y ?
        CMP     dg_y
        BCC     @s
        LDA     dg_y
        ADC     #6              ; C = 1: top line <= dg_y + 7 ?
        DGX     CMP, dg_drawn
        BCC     @s
        DGX     LDA, dg_drawn+3
        AND     #15
        BEQ     @s              ; transparent
        DGX     LDA, dg_drawn+2
        CMP     #72
        BCS     @s              ; no such pattern
        TXA
        STA     dg_rsl,Y
        INY
        BNE     @s              ; always
@end:   STY     dg_rsn
        RTS

; ----------------------------------------------------------------------------
; dg_strip -- rebuild groups dg_g0..dg_g1 of text row dg_row, 8 lines: the
; characters into dg_lb (stream bytes), the sprites over them, then the
; screen bytes of the run (aux, then main).
; ----------------------------------------------------------------------------
dg_strip:
        LDY     dg_g0
        LDA     dg_gc0,Y
        STA     dg_c0
        TYA
        ASL
        ASL
        STA     dg_bmin
        LDY     dg_g1
        TYA
        ASL
        ASL
        ADC     #4              ; C = 0
        STA     dg_bmax
        LDA     dg_gc1,Y
        STA     dg_c1
        SEC
        SBC     dg_c0
        STA     dg_cn
        ; the run's names, 0..127 with a lit pixel or $FF, at 16 q + p
        LDY     dg_c0
@cp:    LDA     (dg_np),Y
        TAX
        LDA     dg_san,X
        LDX     dg_c16,Y
        STA     dg_chs,X
        INY
        CPY     dg_c1
        BNE     @cp
        ; the black margins: byte 3 (character 0 ORs its first dots
        ; there), bytes 77..79 (sprites may draw there)
        LDA     #0
        LDX     dg_c0
        BNE     :+
        .repeat 8, l
        STA     dg_lb+(l / 3 * 256 + l .mod 3 * DG_LW)+3
        .endrepeat
:       LDX     dg_g1
        CPX     #19
        BNE     :+
        .repeat 8, l
        STA     dg_lb+(l / 3 * 256 + l .mod 3 * DG_LW)+77
        STA     dg_lb+(l / 3 * 256 + l .mod 3 * DG_LW)+78
        STA     dg_lb+(l / 3 * 256 + l .mod 3 * DG_LW)+79
        .endrepeat
:       LDX     dg_c0
        LDA     dg_c7,X
        TAY
        LDA     dg_phlo,Y
        STA     @ph+1
        LDA     dg_phhi,Y
        STA     @ph+2
        LDA     dg_c16,X
        SEC
        SBC     dg_c7,X
        TAY                     ; 16 q
@ph:    JSR     dg_ph0
        JSR     dg_strip_sprites
        ; fall through

; dg_write -- stream bytes 4 g0 .. 4 g1 + 3 of the 8 lines to page dg_pgo:
; the even ones to the aux bank (IRQs masked), the odd ones to main; two
; screen columns of 8 lines a pass (~81 cycles a column).
dg_write:
        LDX     dg_row
        LDA     dg_rlo,X
        .repeat 8, l
        STA     .ident(.sprintf("dg_w%d", l))+1
        .endrepeat
        ORA     #1              ; (even)
        .repeat 8, l
        STA     .ident(.sprintf("dg_v%d", l))+1
        .endrepeat
        LDA     dg_rhi,X
        CLC
        ADC     dg_pgo
        .repeat 8, l
        STA     .ident(.sprintf("dg_w%d", l))+2
        STA     .ident(.sprintf("dg_v%d", l))+2
        .if l < 7
        ADC     #4
        .endif
        .endrepeat
        LDA     dg_g0
        ASL
        STA     dg_t            ; first screen offset
        LDA     dg_g1
        ASL
        ADC     #2              ; C = 0
        STA     dg_u            ; last + 1
        LDX     dg_bmin
        LDY     dg_t
        PHP
        SEI
        STA     DG_RAMWRT_AUX
        JSR     dg_wc
        STA     DG_RAMWRT_MAIN
        PLP
        LDX     dg_bmin
        INX
        LDY     dg_t
dg_wc:  .repeat 8, l
        LDA     dg_lb+(l / 3 * 256 + l .mod 3 * DG_LW),X
.ident(.sprintf("dg_w%d", l)):
        STA     $2000,Y
        .endrepeat
        .repeat 8, l
        LDA     dg_lb+(l / 3 * 256 + l .mod 3 * DG_LW)+2,X
.ident(.sprintf("dg_v%d", l)):
        STA     $2001,Y
        .endrepeat
        INX
        INX
        INX
        INX
        INY
        INY
        CPY     dg_u
        BNE     dg_wc
        RTS

; ----------------------------------------------------------------------------
; Characters: dg_ph<p> composes characters 7q+p, 7q+p+1 ... (dg_cn of them,
; Y = 16 q) into the 8 lines of dg_lb, left to right: a character row is 16
; stream bits from bit 24 + 16 p (relative to 16 q): 3 or 4 bytes, the first
; ORed onto the previous character's last one (unless byte-aligned), the
; others stored. One table load a byte (dg_cp<p><i>, by ink and pixels).
; dg_bl<p>: the same for a black character.
; ----------------------------------------------------------------------------
.macro DG_PHASE p
        .local k0, rr, n
        k0 = (4 * DG_X0 + 16 * p) / 7
        rr = (4 * DG_X0 + 16 * p) .mod 7
        n = (rr + 22) / 7
.ident(.sprintf("dg_bl%d", p)):
        LDA     #0
        .repeat 8, l
        .if rr = 0
        STA     dg_lb+(l / 3 * 256 + l .mod 3 * DG_LW)+k0,Y
        .endif
        .repeat n - 1, i
        STA     dg_lb+(l / 3 * 256 + l .mod 3 * DG_LW)+k0+i+1,Y
        .endrepeat
        .endrepeat
        JMP     .ident(.sprintf("dg_nx%d", p))
.ident(.sprintf("dg_ph%d", p)):
        LDX     dg_chs+p,Y
        BMI     .ident(.sprintf("dg_bl%d", p))
        .repeat 8, l
        LDA     dg_ri+128*l,X
        TAX
        LDA     .ident(.sprintf("dg_cp%d0", p)),X
        .if rr <> 0
        ORA     dg_lb+(l / 3 * 256 + l .mod 3 * DG_LW)+k0,Y
        .endif
        STA     dg_lb+(l / 3 * 256 + l .mod 3 * DG_LW)+k0,Y
        .repeat n - 1, i
        LDA     .ident(.sprintf("dg_cp%d%d", p, i + 1)),X
        STA     dg_lb+(l / 3 * 256 + l .mod 3 * DG_LW)+k0+i+1,Y
        .endrepeat
        .if l < 7
        LDX     dg_chs+p,Y
        .endif
        .endrepeat
.ident(.sprintf("dg_nx%d", p)):
        DEC     dg_cn
        .if p < 6
        BNE     .ident(.sprintf("dg_ph%d", p + 1))
        RTS
        .else
        BEQ     :+
        TYA
        CLC
        ADC     #16
        TAY
        JMP     dg_ph0
:       RTS
        .endif
.endmacro

        .repeat 7, p
        DG_PHASE p
        .endrepeat

; ----------------------------------------------------------------------------
; Sprites: dg_strip_sprites draws the row's sprites that reach the run, over
; the characters, the last entry first (entry 0 ends on top). A sprite row
; is two 4-pixel halves, each 16 stream bits from bit r of byte k (left) and
; r + 16: dg_spr<r> paints one line, byte by byte:
;   b = b XOR ((b XOR ink) AND dots)
; ----------------------------------------------------------------------------
dg_strip_sprites:
        LDA     dg_rsn
        BNE     :+
        RTS
:       LDA     #0
        STA     dg_si
@s:     LDY     dg_si
        CPY     dg_rsn
        BCC     :+
        RTS
:       INC     dg_si
        LDX     dg_rsl,Y
        DGX     LDA, dg_drawn+1 ; X / 2
        LSR
        TAY
        LDA     dg_hk,Y         ; its first stream byte
        CMP     dg_bmax
        BCS     @s              ; right of the run
        ADC     #6              ; C = 0
        CMP     dg_bmin
        BCC     @s              ; ends left of it (k + 5 < 4 g0)
        BEQ     @s
        LDA     dg_hk,Y
        STA     dg_t
        LDA     dg_hr,Y         ; the bit: which painter
        TAY
        LDA     dg_srlo,Y
        STA     @spr+1
        LDA     dg_srhi,Y
        STA     @spr+2
        ; ink of bytes k .. k + 5: dg_cpat + 16 N + (k AND 3) + j
        DGX     LDA, dg_drawn+3
        AND     #15
        TAY
        LDA     dg_palette,Y
        ASL
        ASL
        ASL
        ASL
        STA     dg_u
        LDA     dg_t
        AND     #3
        ORA     dg_u
        TAY
        .repeat 6, j
        LDA     dg_cpat+j,Y
        STA     dg_cz+j
        .endrepeat
        ; its rows: dg_sph + 4 * name, dg_spl = dg_sph + 288
        LDA     #0
        STA     dg_u
        DGX     LDA, dg_drawn+2
        ASL
        ROL     dg_u
        ASL
        ROL     dg_u
        ADC     #<dg_sph        ; C = 0
        STA     dg_sh
        LDA     dg_u
        ADC     #>dg_sph
        STA     dg_sh+1
        LDA     dg_sh
        CLC
        ADC     #<288
        STA     dg_sl
        LDA     dg_sh+1
        ADC     #>288
        STA     dg_sl+1
        ; its lines in the row: from line dg_ln, row dg_st of the sprite
        DGX     LDA, dg_drawn
        SEC
        SBC     dg_y
        BCC     @above
        STA     dg_ln           ; starts in the row
        LDA     #0
        BEQ     @st
@above: EOR     #$FF            ; started above: row dg_y - Y
        ADC     #1              ; C = 0
        LDY     #0
        STY     dg_ln
@st:    STA     dg_st
        EOR     #$FF
        SEC
        ADC     #16
        STA     dg_lc           ; 16 - row: lines left in the sprite
@ln:    LDY     dg_ln
        LDA     dg_llo,Y
        CLC
        ADC     dg_t
        STA     dg_bp
        LDA     dg_lhi,Y
        ADC     #0
        STA     dg_bp+1
@spr:   JSR     dg_spr0
        INC     dg_st
        DEC     dg_lc
        BEQ     @nx
        INC     dg_ln
        LDA     dg_ln
        CMP     #8
        BNE     @ln
@nx:    JMP     @s

.macro DG_SPR_HALF tab, nbytes, first, ptr
        .local skip
        LDY     dg_st
        LDA     (ptr),Y
        BEQ     skip
        TAX
        .repeat nbytes, i
        LDY     #first + i
        LDA     (dg_bp),Y
        EOR     dg_cz+first+i
        AND     .ident(.sprintf("dg_sm%d%d", tab, i)),X
        EOR     (dg_bp),Y
        STA     (dg_bp),Y
        .endrepeat
skip:
.endmacro

.macro DG_SPR r
.ident(.sprintf("dg_spr%d", r)):
        DG_SPR_HALF r, (r + 22) / 7, 0, dg_sh
        DG_SPR_HALF (r + 16) .mod 7, ((r + 16) .mod 7 + 22) / 7, (r + 16) / 7, dg_sl
        RTS
.endmacro

        .repeat 7, r
        DG_SPR r
        .endrepeat

; dg_black -- both banks of both pages = 0 (IRQs masked during the aux half).
dg_black:
        PHP
        SEI
        STA     DG_RAMWRT_AUX
        JSR     dg_zero_pages
        STA     DG_RAMWRT_MAIN
        PLP
dg_zero_pages:
        LDA     #0
        STA     dg_ptr
        TAY
        LDX     #$20
@p:     STX     dg_ptr+1
@b:     STA     (dg_ptr),Y
        INY
        BNE     @b
        INX
        CPX     #$60
        BNE     @p
        RTS

; ----------------------------------------------------------------------------
; Tables
; ----------------------------------------------------------------------------
.segment "LCDATA"

dg_lsr5: .repeat 256, b         ; text row of a byte in a names page
        .byte   b >> 5
        .endrepeat
; dirty groups of row r: dg_dg + 20 r
dg_dlo: .repeat 24, r
        .byte   <(dg_dg + 20 * r)
        .endrepeat
dg_dhi: .repeat 24, r
        .byte   >(dg_dg + 20 * r)
        .endrepeat
; first and last group under character column c (pixels 6+4c .. 9+4c)
dg_cg0: .repeat 32, c
        .byte   (DG_X0 + 4 * c) / 7
        .endrepeat
dg_cg1: .repeat 32, c
        .byte   (DG_X0 + 3 + 4 * c) / 7
        .endrepeat
; character columns covering group g: first, last + 1
dg_gc0: .repeat 20, g
        .byte   (7 * g - DG_X0 + (DG_X0 - 7 * g) * (7 * g < DG_X0)) / 4
        .endrepeat
dg_gc1: .repeat 20, g
        .byte   ((7 * g) / 4 + 1) - ((7 * g) / 4 + 1 - 32) * ((7 * g) / 4 + 1 > 32)
        .endrepeat
; character column c: 16 (c / 7) + c mod 7 (its dg_chs slot), c mod 7
dg_c16: .repeat 32, c
        .byte   16 * (c / 7) + c .mod 7
        .endrepeat
dg_c7:  .repeat 32, c
        .byte   c .mod 7
        .endrepeat
dg_phlo: .repeat 7, p
        .byte   <.ident(.sprintf("dg_ph%d", p))
        .endrepeat
dg_phhi: .repeat 7, p
        .byte   >.ident(.sprintf("dg_ph%d", p))
        .endrepeat
dg_srlo: .repeat 7, r
        .byte   <.ident(.sprintf("dg_spr%d", r))
        .endrepeat
dg_srhi: .repeat 7, r
        .byte   >.ident(.sprintf("dg_spr%d", r))
        .endrepeat
; a sprite at TMS X = 2h: its first stream byte, the bit in it; the groups
; of its left and right pixels (19 at most)
dg_hk:  .repeat 128, h
        .byte   (4 * (DG_X0 + h)) / 7
        .endrepeat
dg_hr:  .repeat 128, h
        .byte   (4 * (DG_X0 + h)) .mod 7
        .endrepeat
dg_hg0: .repeat 128, h
        .byte   (DG_X0 + h) / 7
        .endrepeat
dg_hg1: .repeat 128, h
        .byte   (DG_X0 + h + 7) / 7 - ((DG_X0 + h + 7) / 7 - 19) * ((DG_X0 + h + 7) / 7 > 19)
        .endrepeat
; line l of dg_lb
dg_llo: .repeat 8, l
        .byte   .lobyte(dg_lb + l / 3 * 256 + l .mod 3 * DG_LW)
        .endrepeat
dg_lhi: .repeat 8, l
        .byte   .hibyte(dg_lb + l / 3 * 256 + l .mod 3 * DG_LW)
        .endrepeat
; screen address (page 1) of line 0 of text row r
dg_rlo: .repeat 24, r
        .byte   <($2000 + (r & 7) * $80 + (r >> 3) * $28)
        .endrepeat
dg_rhi: .repeat 24, r
        .byte   >($2000 + (r & 7) * $80 + (r >> 3) * $28)
        .endrepeat

.segment "DHGRBSS"
dg_nnew:  .res 1

.include "video_dhgr_data.inc"
.include "video_x2.asm"
