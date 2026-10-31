; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; video_dhgr.asm -- ROGUE's DHGR back-end: the //e / //c double hi-res screen
; ============================================================================
; Implements docs/VIDEO_API.md by emulating the core's virtual TMS9918:
;
;   - the virtual VRAM ($1800-$1AFF names, $1B00-$1B7F sprite table) is a real
;     copy at the SAME addresses in main RAM (segment DHGRBSS at $1800):
;     vid_addr just points vid_put's two operands there;
;   - vid_put stores the byte; when it changes a name it flags the text
;     row, when it lands in the sprite table it flags it. An unchanged byte
;     costs ~40 cycles (render_map rewrites 640 names a turn);
;   - vid_idle (the core calls it before every key wait and each frame of a
;     thrown dagger) composes and writes what changed: each flagged row's
;     names are compared with a copy of what the screen shows (dg_shown),
;     each different one marks the one or two 7-pixel groups under it in
;     the row's dirty bitmap (a clear + the same picture again costs
;     nothing); the sprite list is compared with the one on screen (each moved / recoloured / new / gone
;     sprite dirties its old and new boxes), then every run of dirty groups
;     of every text row is rebuilt line by line: characters, then sprites
;     (the last entry first: entry 0 on top, as on the chip), packed into
;     DHGR bytes and written (aux bytes with IRQs masked, then main ones). A
;     run with no lit character and no sprite is written black directly.
;     Every byte of a run is written once with its final value: no flicker,
;     one page.
;
; Geometry: the TMS picture halved horizontally. 1 DHGR colour pixel = 2 TMS
; pixels, 1 line = 1 line: the 256x192 picture is 128x192 colour pixels at
; x = 6..133 (6 black pixels left and right). A character = 4 x 8, a sprite =
; 8 x 16 at (6 + X/2, Y). Seven colour pixels = one group of 4 bytes (aux 2g,
; main 2g, aux 2g+1, main 2g+1 of the line), 20 groups a line.
; Data (tools/tiles_dhgr.py -> video_dhgr_data.inc): characters as one
; table per (row, pixel) giving each pixel's DHGR nibble, sprites as 8-pixel
; rows, TMS -> DHGR palette.
;
; Machine: //e with 128 KB (extended 80-column card) or //c; DHGR page 1
; ($2000-$3FFF main + aux). Every routine returns with RAMRD/RAMWRT main and
; the I flag it found.
; ============================================================================

DG_X0      = 6                  ; first colour pixel of the TMS picture
DG_VRAM    = $1800              ; = the virtual addresses (DHGRBSS starts here)
DG_SAT     = $1B00
DG_RAMWRT_AUX  = $C005
DG_RAMWRT_MAIN = $C004

.segment "ZEROPAGE"
dg_ptr:   .res 2                ; screen line (both banks)
dg_np:    .res 2                ; name row of the strip
dg_sp:    .res 2                ; sprite row pointer
dg_bits:  .res 1
dg_ink:   .res 1
dg_row:   .res 1                ; text row being rebuilt, 0..23
dg_y:     .res 1                ; its screen line
dg_ln:    .res 1                ; line in the row, 0..7
dg_c0:    .res 1                ; first character column of the run
dg_c1:    .res 1                ; last + 1
dg_g0:    .res 1                ; first group of the run (0..19)
dg_g1:    .res 1                ; last group
dg_g:     .res 1                ; run scan
dg_x4e:   .res 1                ; 4 * dg_c1
dg_bt:    .res 1                ; dg_bit's scratch
dg_si:    .res 1                ; dg_line_sprites' index
dg_t:     .res 1
dg_u:     .res 1
dg_sa:    .res 1                ; vid_put's A / X
dg_sx:    .res 1

.segment "DHGRBSS"              ; $1800, rogue_dhgr.cfg
dg_vram:  .res 1024             ; names $1800-$1AFF, sprites $1B00-$1B7F,
                                ; then room for a cursor run past the end
dg_drawn: .res 128              ; sprite table as last drawn (4 B / entry)
dg_dm:    .res 96               ; dirty groups: row r, groups 8b..8b+7 at 4r+b
dg_chs4:  .res 128              ; the run's characters, column c at 4c
dg_sl:    .res 32               ; the run's sprites (dg_drawn offsets)
dg_touch: .res 24               ; rows whose names vid_put changed
dg_sn:    .res 1
dg_buf:   .res 160              ; one line, 1 byte (DHGR nibble) a pixel,
                                ; packed in place; 140 + a sprite's overrun
dg_nold:  .res 1                ; bytes of dg_drawn in use (4 x entries)
dg_nnew:  .res 1
dg_satd:  .res 1                ; the sprite table was written
dg_on:    .res 1                ; DHGR shown

.segment "BSS"
dg_shown: .res 768              ; the names the screen shows

.segment "CODE"

; ----------------------------------------------------------------------------
; vid_init -- DHGR page 1 on, black; empty virtual screen.
; ----------------------------------------------------------------------------
vid_init:
        LDA     #0
        TAX
@clr:   STA     dg_vram,X       ; names + sprite table + spare = 0
        STA     dg_vram+$100,X
        STA     dg_vram+$200,X
        STA     dg_vram+$300,X
        INX
        BNE     @clr
        LDA     #$D0
        STA     DG_SAT          ; no sprite
        LDA     #0
        STA     dg_nold
        STA     dg_satd
        JSR     dg_clean_all
        JSR     dg_black        ; both banks of page 1
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

; vid_off -- back to the 40-column text page (exit.asm restores the rest).
vid_off:
        BIT     TXTSET
        BIT     DHIRES_OFF
        STA     COL80OFF
        LDA     #0
        STA     dg_on
        RTS

; vid_clear -- every name = 0 (only what was not black is redrawn: the core
; clears, then rewrites the same picture, e.g. at each frame of a throw).
vid_clear:
        LDA     #0
        TAX
@lp:    STA     dg_vram,X
        STA     dg_vram+$100,X
        STA     dg_vram+$200,X
        INX
        BNE     @lp
        LDX     #23
        LDA     #1
@t:     STA     dg_touch,X
        DEX
        BPL     @t
        RTS

; dg_dirty_all -- every group of every row rebuilt at the next vid_idle.
dg_dirty_all:
        LDX     #95
@d:     LDA     #$FF
        STA     dg_dm,X
        DEX
        BPL     @d
        RTS

dg_clean_all:
        LDX     #95
        LDA     #0
@c:     STA     dg_dm,X
        DEX
        BPL     @c
        LDX     #23
@t:     STA     dg_touch,X
        DEX
        BPL     @t
        LDX     #0
@s:     STA     dg_shown,X      ; the screen is black: names 0
        STA     dg_shown+$100,X
        STA     dg_shown+$200,X
        INX
        BNE     @s
        RTS

; vid_sprites_off -- SAT[0].Y = $D0.
vid_sprites_off:
        LDA     #$D0
        STA     DG_SAT
        LDA     #1
        STA     dg_satd
        RTS

; vid_wait_frame -- nothing to wait for: the picture is composed in vid_idle
; (the core calls this before rebuilding the whole map / a full page; drawing
; there would show half-built pictures). Keeps A, X, Y.
vid_wait_frame:
        RTS

; ----------------------------------------------------------------------------
; vid_addr -- A = low, X = high byte of a virtual address ($40 bit ignored).
; Keeps X, Y. Outside $1800-$1BFF the cursor goes to the spare bytes.
; ----------------------------------------------------------------------------
vid_addr:
        STA     dg_cmp+1
        STA     dg_sta+1
        TXA
        AND     #$3F
        CMP     #>DG_VRAM
        BCC     @out
        CMP     #>DG_VRAM + 4
        BCC     @in
@out:   LDA     #$80            ; $1B80: written, never shown
        STA     dg_cmp+1
        STA     dg_sta+1
        LDA     #>DG_SAT
@in:    STA     dg_cmp+2
        STA     dg_sta+2
        RTS

; ----------------------------------------------------------------------------
; vid_put -- A at the cursor, cursor + 1. Keeps A, X, Y and P.
; ----------------------------------------------------------------------------
vid_put:
        PHP
dg_cmp: CMP     DG_VRAM         ; operand = cursor (vid_addr)
        BEQ     dg_vp_next
dg_sta: STA     DG_VRAM
        STA     dg_sa
        STX     dg_sx
        LDA     dg_sta+2
        CMP     #>DG_SAT
        BCS     dg_vp_sat
        SBC     #>DG_VRAM - 1   ; C = 0: A - $18 = page of the names 0..2
        ASL
        ASL
        ASL
        STA     dg_t
        LDA     dg_sta+1
        LSR
        LSR
        LSR
        LSR
        LSR
        ORA     dg_t            ; text row
        TAX
        LDA     #1
        STA     dg_touch,X      ; dg_flush compares it with the screen
        JMP     dg_vp_back
dg_vp_sat:
        LDA     #1
        STA     dg_satd
dg_vp_back:
        LDA     dg_sa
        LDX     dg_sx
dg_vp_next:
        INC     dg_cmp+1
        INC     dg_sta+1
        BNE     dg_vp_done
        INC     dg_cmp+2
        INC     dg_sta+2
dg_vp_done:
        PLP
        RTS

; ----------------------------------------------------------------------------
; vid_idle -- compose and write what changed. Keeps X, Y.
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

; dg_flush -- the sprite diff, then each run of dirty groups of each row.
dg_flush:
        LDA     dg_on
        BEQ     @rts
        LDA     dg_satd
        BEQ     :+
        JSR     dg_sat_diff
:       JSR     dg_name_diff
        LDA     #0
        STA     dg_row
@r:     LDA     dg_row
        ASL
        ASL
        TAX
        LDA     dg_dm,X
        ORA     dg_dm+1,X
        ORA     dg_dm+2,X
        BEQ     @next
        LDA     #0
        STA     dg_g
@scan:  JSR     dg_bit          ; C = dirty(dg_g); X = byte, Y = bit
        BCS     @run
        INC     dg_g
        TYA
        BNE     @more
        LDA     dg_dm,X         ; at a byte's first bit: a clean byte
        BNE     @more           ; is skipped whole
        LDA     dg_g
        CLC
        ADC     #7
        STA     dg_g
@more:  LDA     dg_g
        CMP     #20
        BCC     @scan
        LDA     dg_row          ; row done: clean
        ASL
        ASL
        TAX
        LDA     #0
        STA     dg_dm,X
        STA     dg_dm+1,X
        STA     dg_dm+2,X
@next:  INC     dg_row
        LDA     dg_row
        CMP     #24
        BNE     @r
@rts:   RTS
@run:   LDA     dg_g
        STA     dg_g0
@ext:   INC     dg_g
        LDA     dg_g
        CMP     #20
        BCS     @end
        JSR     dg_bit
        BCS     @ext
@end:   LDX     dg_g
        DEX
        STX     dg_g1
        JSR     dg_strip
        JMP     @more

; dg_name_diff -- each touched row: names that differ from dg_shown (what
; the screen shows) dirty their groups and are copied there.
dg_name_diff:
        LDX     #0
@r:     LDA     dg_touch,X
        BEQ     @next
        LDA     #0
        STA     dg_touch,X
        STX     dg_row
        TXA
        ASL
        ASL
        STA     dg_bt           ; 4 * row
        TXA                     ; dg_np = names, dg_sp = shown, + 32 * row
        LSR
        LSR
        LSR
        PHA
        CLC
        ADC     #>DG_VRAM
        STA     dg_np+1
        PLA
        CLC
        ADC     #>dg_shown
        STA     dg_sp+1
        TXA
        ASL
        ASL
        ASL
        ASL
        ASL
        STA     dg_np
        CLC
        ADC     #<dg_shown
        STA     dg_sp
        BCC     :+
        INC     dg_sp+1
:       LDY     #31
@c:     LDA     (dg_np),Y
        CMP     (dg_sp),Y
        BEQ     @same
        STA     (dg_sp),Y
        LDA     dg_cgb0,Y       ; first group of column Y: byte, bit
        ORA     dg_bt
        TAX
        LDA     dg_dm,X
        ORA     dg_cgm0,Y
        STA     dg_dm,X
        LDA     dg_cgb1,Y       ; last group
        ORA     dg_bt
        TAX
        LDA     dg_dm,X
        ORA     dg_cgm1,Y
        STA     dg_dm,X
@same:  DEY
        BPL     @c
        LDX     dg_row
@next:  INX
        CPX     #24
        BNE     @r
        RTS

; dg_bit -- C = dirty bit of group dg_g of row dg_row. Keeps nothing.
dg_bit:
        LDA     dg_g
        LSR
        LSR
        LSR
        STA     dg_bt
        LDA     dg_row
        ASL
        ASL
        ORA     dg_bt
        TAX
        LDA     dg_g
        AND     #7
        TAY
        LDA     dg_dm,X
        AND     dg_bitm,Y
        CMP     #1              ; C = (bit set)
        RTS

; ----------------------------------------------------------------------------
; dg_sat_diff -- the new sprite list against the drawn one: each entry that
; differs dirties its old box and its new box; then the new list is the
; drawn one.
; ----------------------------------------------------------------------------
dg_sat_diff:
        LDA     #0
        STA     dg_satd
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
        CMP     dg_drawn,X
        BNE     @both
        LDA     DG_SAT+1,X
        CMP     dg_drawn+1,X
        BNE     @both
        LDA     DG_SAT+2,X
        CMP     dg_drawn+2,X
        BNE     @both
        LDA     DG_SAT+3,X
        CMP     dg_drawn+3,X
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
        STA     dg_drawn,X
        TXA
        BNE     @cp
@done:  RTS

dg_mark_old:
        LDA     dg_drawn,X
        LDY     dg_drawn+1,X
        ; fall through
; dg_mark_box -- A = Y, Y = X of a 16x16 sprite: dirty its box (3 groups x
; 2 or 3 text rows). Keeps X.
dg_mark_box:
        CMP     #192
        BCS     @off            ; below the picture (or "negative")
        STX     dg_u
        STA     dg_t            ; top line
        LSR
        LSR
        LSR
        STA     dg_row          ; first text row (dg_flush sets it again)
        LDA     dg_t
        CLC
        ADC     #15
        CMP     #192
        BCC     :+
        LDA     #191
:       LSR
        LSR
        LSR
        STA     dg_t            ; last text row
        TYA
        LSR
        CLC
        ADC     #DG_X0
        TAY                     ; left pixel
        LDA     dg_div7,Y
        STA     dg_g0
        LDA     dg_div7+7,Y     ; group of the right pixel
        CMP     #20
        BCC     :+
        LDA     #19
:       STA     dg_g1
@row:   LDA     dg_g0
        STA     dg_g
@grp:   JSR     dg_bit          ; X = byte, Y = bit
        LDA     dg_dm,X
        ORA     dg_bitm,Y
        STA     dg_dm,X
        INC     dg_g
        LDA     dg_g1
        CMP     dg_g
        BCS     @grp
        LDA     dg_row
        CMP     dg_t
        INC     dg_row
        BCC     @row
        LDX     dg_u
@off:   RTS

; ----------------------------------------------------------------------------
; dg_strip -- rebuild groups dg_g0..dg_g1 of text row dg_row, 8 lines.
; ----------------------------------------------------------------------------
dg_strip:
        LDY     dg_g0
        LDA     dg_gc0,Y
        STA     dg_c0
        LDY     dg_g1
        LDA     dg_gc1,Y
        STA     dg_c1
        ASL
        ASL
        STA     dg_x4e
        LDX     dg_row
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
        ASL
        ASL
        STA     dg_np
        LDA     dg_rlo,X
        STA     dg_ptr
        LDA     dg_rhi,X
        STA     dg_ptr+1
        TXA
        ASL
        ASL
        ASL
        STA     dg_y
        ; the run's characters at dg_chs4 + 4c (128..255: blank); lit ones?
        LDA     #0
        STA     dg_u
        LDY     dg_c0
@ch:    LDA     (dg_np),Y
        BPL     :+
        LDA     #0
:       TAX
        LDA     dg_lit,X
        ORA     dg_u
        STA     dg_u
        TYA
        ASL
        ASL
        STA     dg_t
        TXA
        LDX     dg_t
        STA     dg_chs4,X
        INY
        CPY     dg_c1
        BNE     @ch
        JSR     dg_strip_sprites ; A = how many sprites cross the row
        ORA     dg_u
        BNE     @full
        ; black run: zeros packed are zeros, written 8 times
        LDY     dg_g0
        LDX     dg_mul7,Y
        LDY     dg_g1
        LDA     dg_mul7+1,Y
        STA     dg_t
        LDA     #0
:       STA     dg_buf,X
        INX
        CPX     dg_t
        BNE     :-
        LDA     #8
        STA     dg_ln
@blk:   JSR     dg_line_write
        LDA     dg_ptr+1
        CLC
        ADC     #4
        STA     dg_ptr+1
        DEC     dg_ln
        BNE     @blk
        RTS
@full:  LDA     #0
        STA     dg_ln
@line:  JSR     dg_line_chars
        JSR     dg_line_sprites
        JSR     dg_line_pack
        JSR     dg_line_write
        INC     dg_y
        LDA     dg_ptr+1        ; next line: +$400
        CLC
        ADC     #4
        STA     dg_ptr+1
        INC     dg_ln
        LDA     dg_ln
        CMP     #8
        BNE     @line
        RTS

; dg_strip_sprites -- dg_sl = the drawn sprites crossing lines dg_y..dg_y+7
; that have something to draw, the last entry first; A = dg_sn = their count.
dg_strip_sprites:
        LDY     #0
        LDX     dg_nold
@s:     TXA
        BEQ     @end
        DEX
        DEX
        DEX
        DEX
        LDA     dg_drawn,X
        CMP     #192
        BCS     @s
        CLC
        ADC     #15             ; bottom line >= dg_y ?
        CMP     dg_y
        BCC     @s
        LDA     dg_y
        CLC
        ADC     #7
        CMP     dg_drawn,X      ; top line <= dg_y + 7 ?
        BCC     @s
        LDA     dg_drawn+3,X
        AND     #15
        BEQ     @s              ; transparent
        LDA     dg_drawn+2,X
        CMP     #72
        BCS     @s              ; no such pattern
        TXA
        STA     dg_sl,Y
        TAX
        INY
        BNE     @s              ; always
@end:   STY     dg_sn
        TYA
        RTS

; dg_line_chars -- black margins, then characters dg_c0..dg_c1-1 of the row
; at line dg_ln into dg_buf (one DHGR nibble a pixel), 4 loads a character
; from the line's 4 pixel tables (operands patched here).
dg_line_chars:
        LDA     #0
        LDX     #5
@m0:    STA     dg_buf,X
        DEX
        BPL     @m0
        LDX     #13
@m1:    STA     dg_buf+134,X
        DEX
        BPL     @m1
        LDA     dg_ln           ; dg_cpx + 512 * line + 128 * pixel
        ASL
        ADC     #>dg_cpx        ; C = 0
        TAX
        LDA     #<dg_cpx
        STA     dg_k0+1
        STX     dg_k0+2
        CLC
        ADC     #$80
        BCC     :+
        INX
:       STA     dg_k1+1
        STX     dg_k1+2
        CLC
        ADC     #$80
        BCC     :+
        INX
:       STA     dg_k2+1
        STX     dg_k2+2
        CLC
        ADC     #$80
        BCC     :+
        INX
:       STA     dg_k3+1
        STX     dg_k3+2
        LDA     dg_c0
        ASL
        ASL
        TAX
dg_lc:  LDY     dg_chs4,X
dg_k0:  LDA     dg_cpx,Y
        STA     dg_buf+DG_X0,X
dg_k1:  LDA     dg_cpx,Y
        STA     dg_buf+DG_X0+1,X
dg_k2:  LDA     dg_cpx,Y
        STA     dg_buf+DG_X0+2,X
dg_k3:  LDA     dg_cpx,Y
        STA     dg_buf+DG_X0+3,X
        INX
        INX
        INX
        INX
        CPX     dg_x4e
        BNE     dg_lc
        RTS

; dg_line_sprites -- the strip's sprites (dg_sl) crossing line dg_y, the last
; entry first (entry 0 ends on top).
dg_line_sprites:
        LDA     dg_sn
        BEQ     @done
        LDA     #0
        STA     dg_si           ; index in dg_sl
@s:     LDY     dg_si
        CPY     dg_sn
        BCS     @done
        INC     dg_si
        LDX     dg_sl,Y
        LDA     dg_y
        SEC
        SBC     dg_drawn,X
        CMP     #16
        BCS     @s
        STA     dg_t            ; row in the sprite
        LDA     dg_drawn+3,X
        AND     #15
        TAY
        LDA     dg_palette,Y
        STA     dg_ink
        LDA     dg_drawn+2,X    ; name: 4 per sprite, 16 rows each
        LDY     #0
        STY     dg_sp+1
        ASL
        ROL     dg_sp+1
        ASL
        ROL     dg_sp+1
        ADC     #<dg_sprites    ; C = 0
        STA     dg_sp
        LDA     dg_sp+1
        ADC     #>dg_sprites
        STA     dg_sp+1
        LDY     dg_t
        LDA     (dg_sp),Y
        BEQ     @s
        STA     dg_bits
        LDA     dg_drawn+1,X    ; X
        LSR
        CLC
        ADC     #DG_X0
        TAY
@px:    ASL     dg_bits
        BCC     :+
        LDA     dg_ink
        STA     dg_buf,Y
:       INY
        LDA     dg_bits
        BNE     @px
        BEQ     @s              ; always
@done:  RTS

; dg_line_pack -- groups dg_g0..dg_g1 of dg_buf packed in place: the 7
; nibbles of group g (bytes 7g..7g+6) -> its 4 screen bytes at 7g..7g+3
; (aux 2g, main 2g, aux 2g+1, main 2g+1). ~60 cycles a group.
dg_line_pack:
        LDY     dg_g1
        LDA     dg_mul7+1,Y
        STA     dg_u            ; end
        LDY     dg_g0
        LDA     dg_mul7,Y
        TAY
@g:     LDX     dg_buf+1,Y      ; n1
        LDA     dg_p4,X
        ORA     dg_buf,Y        ; n0
        STA     dg_buf,Y
        LDA     dg_r3,X
        LDX     dg_buf+2,Y      ; n2
        ORA     dg_s1,X
        LDX     dg_buf+3,Y      ; n3
        ORA     dg_l5,X
        STA     dg_buf+1,Y
        LDA     dg_r2,X
        LDX     dg_buf+4,Y      ; n4
        ORA     dg_s2,X
        LDX     dg_buf+5,Y      ; n5
        ORA     dg_l6,X
        STA     dg_buf+2,Y
        LDA     dg_r1,X
        LDX     dg_buf+6,Y      ; n6
        ORA     dg_s3,X
        STA     dg_buf+3,Y
        TYA
        CLC
        ADC     #7
        TAY
        CPY     dg_u
        BNE     @g
        RTS

; dg_line_write -- the packed groups to screen line dg_ptr: aux bytes with
; IRQs masked (RAMWRT aux), then main bytes.
dg_line_write:
        LDY     dg_g1
        TYA
        ASL
        ADC     #2              ; C = 0
        STA     dg_t            ; end offset 2 (g1 + 1)
        LDY     dg_g0
        LDA     dg_mul7,Y
        STA     dg_u
        TAX
        TYA
        ASL
        STA     dg_bits
        TAY
        PHP
        SEI
        STA     DG_RAMWRT_AUX
@a:     LDA     dg_buf,X
        STA     (dg_ptr),Y
        INY
        LDA     dg_buf+2,X
        STA     (dg_ptr),Y
        INY
        TXA
        CLC
        ADC     #7
        TAX
        CPY     dg_t
        BNE     @a
        STA     DG_RAMWRT_MAIN
        PLP
        LDX     dg_u
        LDY     dg_bits
@m:     LDA     dg_buf+1,X
        STA     (dg_ptr),Y
        INY
        LDA     dg_buf+3,X
        STA     (dg_ptr),Y
        INY
        TXA
        CLC
        ADC     #7
        TAX
        CPY     dg_t
        BNE     @m
        RTS

; dg_black -- both banks of page 1 = 0 (IRQs masked during the aux half).
dg_black:
        PHP
        SEI
        STA     DG_RAMWRT_AUX
        JSR     dg_zero_page1
        STA     DG_RAMWRT_MAIN
        PLP
dg_zero_page1:
        LDA     #0
        STA     dg_ptr
        TAY
        LDX     #$20
@p:     STX     dg_ptr+1
@b:     STA     (dg_ptr),Y
        INY
        BNE     @b
        INX
        CPX     #$40
        BNE     @p
        RTS

; ----------------------------------------------------------------------------
; Tables
; ----------------------------------------------------------------------------
.segment "RODATA"

; packing: one 16-entry table per shifted piece of a nibble
dg_p4:  .repeat 16, n
        .byte   (n & 7) << 4
        .endrepeat
dg_r3:  .repeat 16, n
        .byte   n >> 3
        .endrepeat
dg_s1:  .repeat 16, n
        .byte   n << 1
        .endrepeat
dg_l5:  .repeat 16, n
        .byte   (n & 3) << 5
        .endrepeat
dg_r2:  .repeat 16, n
        .byte   n >> 2
        .endrepeat
dg_s2:  .repeat 16, n
        .byte   n << 2
        .endrepeat
dg_l6:  .repeat 16, n
        .byte   (n & 1) << 6
        .endrepeat
dg_r1:  .repeat 16, n
        .byte   n >> 1
        .endrepeat
dg_s3:  .repeat 16, n
        .byte   n << 3
        .endrepeat
; dg_ex + 4 p + k = $FF if pixel k (0 = left) of the 4-pixel row p is lit
dg_bitm: .repeat 8, b
        .byte   1 << b
        .endrepeat
; first and last group of a character column c (pixels 6+4c .. 9+4c): the
; byte of the row's dirty bitmap and the bit
dg_cgb0: .repeat 32, c
        .byte   ((DG_X0 + 4 * c) / 7) >> 3
        .endrepeat
dg_cgm0: .repeat 32, c
        .byte   1 << (((DG_X0 + 4 * c) / 7) & 7)
        .endrepeat
dg_cgb1: .repeat 32, c
        .byte   ((DG_X0 + 3 + 4 * c) / 7) >> 3
        .endrepeat
dg_cgm1: .repeat 32, c
        .byte   1 << (((DG_X0 + 3 + 4 * c) / 7) & 7)
        .endrepeat
; character columns covering group g: first, last + 1
dg_gc0: .repeat 20, g
        .byte   (7 * g - DG_X0 + (DG_X0 - 7 * g) * (7 * g < DG_X0)) / 4
        .endrepeat
dg_gc1: .repeat 20, g
        .byte   ((7 * g) / 4 + 1) - ((7 * g) / 4 + 1 - 32) * ((7 * g) / 4 + 1 > 32)
        .endrepeat
dg_mul7: .repeat 21, g
        .byte   7 * g
        .endrepeat
dg_div7: .repeat 148, px
        .byte   px / 7
        .endrepeat
; screen address of line 0 of text row r
dg_rlo: .repeat 24, r
        .byte   <($2000 + (r & 7) * $80 + (r >> 3) * $28)
        .endrepeat
dg_rhi: .repeat 24, r
        .byte   >($2000 + (r & 7) * $80 + (r >> 3) * $28)
        .endrepeat

.include "video_dhgr_data.inc"
