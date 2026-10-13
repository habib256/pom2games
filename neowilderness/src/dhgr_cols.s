; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; dhgr_cols.s -- DHGR colour-column primitives for the Neowilderness view
; ============================================================================
; One ray = one DHGR colour pixel column x = 0..139. Pixel x is the 4-bit
; cell 4*(x mod 7) of byte group g = x / 7: interleaved bytes aux 2g,
; main 2g, aux 2g+1, main 2g+1 (7 bits each, LSB first, bit 7 cleared).
; A column touches AT MOST ONE byte per bank (x mod 7 = 1, 3, 5 straddle
; aux/main), hence one read-modify-write pass per bank and row range.
; Colour c (LORES numbering) is stored as rot(c) = (c >> 1 | c << 3) & 15,
; the encoding of dev/lib/hgrc/dhgr_pattern.c (Apple IIe TN #3).
;
; Assembly options (define before inclusion or with ca65 -D):
;   DHGR_BASE = $2000 (default) or $4000: page base.
;     $2000: banks are selected with PAGE2 while 80STORE and HIRES are on
;            ($C055 aux, $C054 main). Code, tables and self-modified rows may
;            live anywhere in main RAM; only $0400-$07FF/$2000-$3FFF switch.
;     $4000: 80STORE cannot bank page 2: RAMRD+RAMWRT are switched together.
;            Everything that runs while they are on (segment DCROWS) must be
;            mirrored at the same address in aux RAM (dc_mirror does it).
;   DC_ROWS = 192 (default): rows of the unrolled pass code (176 suffices
;            for the game: 0..159 view/HUD + 160..175 cache).
;   DC_GROUP_MIN = 4: shortest common run that dc_band writes as full groups.
;
; Bank contract: entry with main video selected (PAGE2 off, or RAMRD/RAMWRT
; off), 80STORE on for $2000. Every routine returns with main selected.
; Each aux/main pass runs with IRQs masked (PHP/SEI ... PLP): an interrupt
; handler would otherwise see aux $0400-$07FF/$2000-$3FFF (or all of aux
; $0200-$BFFF with RAMRD/RAMWRT). dc_save_bank / dc_restore_bank keep a
; caller's non-main selection around a batch of calls.
;
; API (parameters in zero page, all exported):
;   dc_clear        A = colour: fill both 8 KB banks (holes included).
;   dc_vspan        column dc_x, rows dc_y0..dc_y1-1 (empty if y0 >= y1),
;                   colour dc_c. Read-modify-write: neighbours are kept.
;   dc_band         columns dc_x..dc_x1-1, rows (dc_top),x .. (dc_bot),x - 1,
;                   colour dc_c. Seven aligned columns whose common rows
;                   span DC_GROUP_MIN or more are stored as whole 4-byte
;                   groups (plain STA, no read), the ragged ends per column.
;                   Clobbers dc_x (= dc_x1 on return), dc_y0, dc_y1.
;   dc_group        rows dc_y0..dc_y1-1 of the 7 columns of group dc_g
;                   (0..19) in colour dc_c: four STA passes.
;   dc_bspan        column buffer dc_x (0..6) of group dc_g, rows
;                   dc_y0..dc_y1-1, dc_c = a << 4 | b checkerboard pair
;                   (page 1 build only; buffers in segment DCBSS).
;   dc_flush        group dc_g, rows dc_y0..dc_y1-1 from the 7 column
;                   buffers: whole bytes, no screen read (page 1 only).
;   dc_save_bank / dc_restore_bank, dc_mirror (DHGR_BASE = $4000 only).
; Cycle costs are measured by tests/test_dhgr_cols.py (see docs/DHGR.md).
; ============================================================================

.ifndef DHGR_BASE
DHGR_BASE = $2000
.endif
.ifndef DC_ROWS
DC_ROWS = 192
.endif
.ifndef DC_GROUP_MIN
DC_GROUP_MIN = 4
.endif
.assert DHGR_BASE = $2000 .or DHGR_BASE = $4000, error, "DHGR_BASE must be $2000 or $4000"
.assert DC_ROWS > 0 .and DC_ROWS <= 192, error, "DC_ROWS must be 1..192"
DC_PAGE2 = (DHGR_BASE = $2000)
        .macpack longbranch

.define DC_ROW(I) DHGR_BASE + ((I) .mod 8) * $400 + (((I) / 8) .mod 8) * $80 + ((I) / 64) * $28

OP_RTS  = $60
OP_LDAY = $B9                   ; LDA abs,Y: first byte of a read-modify-write row
OP_STAY = $99                   ; STA abs,Y: first byte of a store row

.macro DC_AUX
.if DC_PAGE2
        sta     $C055           ; 80STORE on: aux $2000-$3FFF (and $0400-$07FF)
.else
        sta     $C003           ; RAMRD aux: the next opcode comes from the mirror
        sta     $C005           ; RAMWRT aux
.endif
.endmacro
.macro DC_MAIN
.if DC_PAGE2
        sta     $C054
.else
        sta     $C002
        sta     $C004
.endif
.endmacro

.export dc_clear, dc_vspan, dc_band, dc_group, dc_save_bank, dc_restore_bank
.export dc_rmw_pass, dc_sta_pass, dc_pat
.exportzp dc_x, dc_x1, dc_y0, dc_y1, dc_c, dc_g, dc_top, dc_bot
.exportzp dc_off, dc_and, dc_or

.segment "ZEROPAGE"
dc_x:     .res 1                ; column 0..139
dc_x1:    .res 1                ; band: end column (exclusive)
dc_y0:    .res 1                ; first row
dc_y1:    .res 1                ; end row (exclusive)
dc_c:     .res 1                ; colour 0..15
dc_g:     .res 1                ; group 0..19
dc_top:   .res 2                ; band: 140-byte table of first rows
dc_bot:   .res 2                ; band: 140-byte table of end rows
dc_off:   .res 1                ; pass: physical byte 0..39 of the row
dc_and:   .res 1                ; pass: kept bits / clear: even byte
dc_or:    .res 1                ; pass: colour bits / clear: odd byte
dc_jump:  .res 2                ; pass: entry row
dc_plant: .res 2                ; pass: row that receives the RTS
dc_lo:    .res 1                ; band: common rows of a group
dc_hi:    .res 1
dc_k:     .res 1
dc_bank:  .res 1                ; saved selection
dc_gofs:  .res 1                ; group: physical byte 2g
dc_ptr:   .res 2                ; flush: row address + 2g
dc_a0:    .res 1                ; flush: aux 2g, main 2g, aux 2g+1
dc_m0:    .res 1
dc_a1:    .res 1

; ----------------------------------------------------------------------------
; Main-memory part: column tables and the routines that only prepare passes.
.segment "DCCODE"

; dc_vspan -- column dc_x, rows dc_y0..dc_y1-1, colour dc_c.
.if DC_PAGE2
; Page 1: the unrolled rows are not banked, so one planted RTS serves the
; aux and the main pass; IRQs are masked once for both.
dc_vspan:
        ldx     dc_y0
        cpx     dc_y1
        bcs     @rts
        lda     dc_rmw_lo,x
        sta     dc_jump
        lda     dc_rmw_hi,x
        sta     dc_jump+1
        ldx     dc_y1
        lda     dc_rmw_lo,x
        sta     dc_plant
        lda     dc_rmw_hi,x
        sta     dc_plant+1
        ldy     #0
        lda     #OP_RTS
        sta     (dc_plant),y
        php
        sei
        ldx     dc_x
        ldy     dc_xaux_off,x
        bmi     @main
        lda     dc_xaux_bits,x
        eor     #$7F            ; also clears bit 7
        sta     dc_and
        lda     dc_xaux_j,x
        ora     dc_c
        tax
        lda     dc_pat,x
        ldx     dc_x
        and     dc_xaux_bits,x
        sta     dc_or
        sta     $C055
        jsr     dc_go           ; Y = physical byte
        sta     $C054
        ldx     dc_x
@main:  ldy     dc_xmain_off,x
        bmi     @end
        lda     dc_xmain_bits,x
        eor     #$7F
        sta     dc_and
        lda     dc_xmain_j,x
        ora     dc_c
        tax
        lda     dc_pat,x
        ldx     dc_x
        and     dc_xmain_bits,x
        sta     dc_or
        jsr     dc_go
@end:   plp
        ldy     #0
        lda     #OP_LDAY
        sta     (dc_plant),y
@rts:   rts
.else
; Page 2: each pass plants its RTS in the copy of the selected bank.
dc_vspan:
        lda     dc_y0
        cmp     dc_y1
        bcs     @rts
        ldx     dc_x
        ldy     dc_xaux_off,x
        bmi     @main
        sty     dc_off
        lda     dc_xaux_bits,x
        eor     #$7F            ; also clears bit 7
        sta     dc_and
        lda     dc_xaux_j,x
        ora     dc_c
        tay
        lda     dc_pat,y
        and     dc_xaux_bits,x
        sta     dc_or
        sec
        jsr     dc_rmw_pass
        ldx     dc_x
@main:  ldy     dc_xmain_off,x
        bmi     @rts
        sty     dc_off
        lda     dc_xmain_bits,x
        eor     #$7F
        sta     dc_and
        lda     dc_xmain_j,x
        ora     dc_c
        tay
        lda     dc_pat,y
        and     dc_xmain_bits,x
        sta     dc_or
        clc
        jmp     dc_rmw_pass
@rts:   rts

.endif

; dc_group -- rows dc_y0..dc_y1-1 of the 7 columns of group dc_g, colour dc_c:
; two whole bytes per bank and row, stored without reading the screen.
dc_group:
        lda     dc_g
        asl     a
        sta     dc_gofs
        ldx     dc_c
        lda     dc_pat,x        ; aux 2g
        ldy     dc_gofs
        sec
        jsr     dc_sta_pass
        ldx     dc_c
        lda     dc_pat+32,x     ; aux 2g+1
        ldy     dc_gofs
        iny
        sec
        jsr     dc_sta_pass
        ldx     dc_c
        lda     dc_pat+16,x     ; main 2g
        ldy     dc_gofs
        clc
        jsr     dc_sta_pass
        ldx     dc_c
        lda     dc_pat+48,x     ; main 2g+1
        ldy     dc_gofs
        iny
        clc
        jmp     dc_sta_pass

; dc_band -- columns dc_x..dc_x1-1, rows (dc_top),x .. (dc_bot),x - 1.
dc_band:
@loop:  ldx     dc_x
        cpx     dc_x1
        jcs     @rts
        lda     dc_xk,x
        bne     @single
        txa
        clc
        adc     #7
        bcs     @single
        cmp     dc_x1
        beq     @group
        bcs     @single
@group: ldy     dc_x            ; lo = max(top), hi = min(bot) of 7 columns
        lda     (dc_top),y
        sta     dc_lo
        lda     (dc_bot),y
        sta     dc_hi
        ldx     #6
@minmax:
        iny
        lda     (dc_top),y
        cmp     dc_lo
        bcc     :+
        sta     dc_lo
:       lda     (dc_bot),y
        cmp     dc_hi
        bcs     :+
        sta     dc_hi
:       dex
        bne     @minmax
        lda     dc_hi
        sec
        sbc     dc_lo
        bcc     @columns
        cmp     #DC_GROUP_MIN
        bcc     @columns
        lda     dc_lo
        sta     dc_y0
        lda     dc_hi
        sta     dc_y1
        ldx     dc_x
        lda     dc_xgroup,x
        sta     dc_g
        jsr     dc_group
        lda     #7
        sta     dc_k
@ragged:
        ldy     dc_x            ; top..lo-1, then hi..bot-1
        lda     (dc_top),y
        sta     dc_y0
        lda     dc_lo
        sta     dc_y1
        jsr     dc_vspan
        lda     dc_hi
        sta     dc_y0
        ldy     dc_x
        lda     (dc_bot),y
        sta     dc_y1
        jsr     dc_vspan
        inc     dc_x
        dec     dc_k
        bne     @ragged
        beq     @loop
@columns:
        lda     #7
        sta     dc_k
:       jsr     dc_band_column
        inc     dc_x
        dec     dc_k
        bne     :-
        jmp     @loop
@single:
        jsr     dc_band_column
        inc     dc_x
        jmp     @loop
@rts:   rts

dc_band_column:
        ldy     dc_x
        lda     (dc_top),y
        sta     dc_y0
        lda     (dc_bot),y
        sta     dc_y1
        jmp     dc_vspan

; dc_save_bank -- remember the caller's video bank selection, select main.
dc_save_bank:
.if DC_PAGE2
        lda     $C01C           ; RDPAGE2, bit 7
.else
        lda     $C013           ; RDRAMRD, bit 7
        lsr     a
        ora     $C014           ; RDRAMWRT, bit 7 (RAMRD in bit 6)
.endif
        sta     dc_bank
        DC_MAIN
        rts

; dc_restore_bank -- reselect what dc_save_bank found.
dc_restore_bank:
.if DC_PAGE2
        bit     dc_bank
        bpl     :+
        sta     $C055
:       rts
.else
        bit     dc_bank
        bvc     :+
        sta     $C003
:       bit     dc_bank
        bpl     :+
        sta     $C005
:       rts
.endif

.if .not DC_PAGE2
.import __DCROWS_RUN__, __DCROWS_SIZE__
.export dc_mirror
; dc_mirror -- copy DCROWS to the same addresses in aux RAM (page 2 mode).
; Runs from main RAM with only RAMWRT switched. Uses dc_jump as pointer.
dc_mirror:
        php
        sei
        lda     #<__DCROWS_RUN__
        sta     dc_jump
        lda     #>__DCROWS_RUN__
        sta     dc_jump+1
        ldx     #>(__DCROWS_SIZE__ + 255)
        ldy     #0
        sta     $C005
@copy:  lda     (dc_jump),y
        sta     (dc_jump),y
        iny
        bne     @copy
        inc     dc_jump+1
        dex
        bne     @copy
        sta     $C004
        plp
        rts
.endif

.if DC_PAGE2
; ----------------------------------------------------------------------------
; Column buffers (page 1 only): the renderer writes the colour of each row
; of 7 consecutive columns, then dc_flush writes the group as whole bytes.
.include "dhgr_layout.inc"
.export dc_flush, dc_bspan, dc_colbuf
.exportzp dc_ptr
DC_BUF = 192                    ; bytes per column buffer (physical rows)

; dc_bspan -- buffer column dc_x (0..6) of group dc_g, rows dc_y0..dc_y1-1.
; dc_c = a << 4 | b: a where (row + screen column) is even, b where odd
; (a checkerboard dither; a = b for a solid colour).
dc_bspan:
        ldx     dc_x
        lda     dc_buf_lo,x
        sta     dc_ptr
        lda     dc_buf_hi,x
        sta     dc_ptr+1
        lda     dc_c
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        sta     dc_a0           ; even colour
        lda     dc_c
        and     #15
        sta     dc_m0           ; odd colour
        txa                     ; parity of the first cell: 7g + k + y0
        clc
        adc     dc_g
        adc     dc_y0
        lsr     a
        bcc     :+
        lda     dc_a0           ; odd first: swap
        ldx     dc_m0
        sta     dc_m0
        stx     dc_a0
:       ldy     dc_y0
        cpy     dc_y1
        bcs     @rts
@fill:  lda     dc_a0
        sta     (dc_ptr),y
        iny
        cpy     dc_y1
        bcs     @rts
        lda     dc_m0
        sta     (dc_ptr),y
        iny
        cpy     dc_y1
        bcc     @fill
@rts:   rts

; dc_flush -- rows dc_y0..dc_y1-1 of group dc_g from the 7 column buffers:
; 4 table-combined bytes per row, written without reading the screen.
dc_flush:
        lda     dc_g
        asl     a
        sta     dc_gofs
        php
        sei
        ldx     dc_y0
        cpx     dc_y1
        bcs     @done
@row:   lda     dc_row_lo,x
        clc
        adc     dc_gofs
        sta     dc_ptr
        lda     dc_row_hi,x
        ora     #>DHGR_BASE
        sta     dc_ptr+1
        ldy     dc_colbuf+0*DC_BUF,x
        lda     dc_t00,y
        ldy     dc_colbuf+1*DC_BUF,x
        ora     dc_t10,y
        sta     dc_a0
        lda     dc_t11,y
        ldy     dc_colbuf+2*DC_BUF,x
        ora     dc_t21,y
        ldy     dc_colbuf+3*DC_BUF,x
        ora     dc_t31,y
        sta     dc_m0
        lda     dc_t32,y
        ldy     dc_colbuf+4*DC_BUF,x
        ora     dc_t42,y
        ldy     dc_colbuf+5*DC_BUF,x
        ora     dc_t52,y
        sta     dc_a1
        lda     dc_t53,y
        ldy     dc_colbuf+6*DC_BUF,x
        ora     dc_t63,y
        ldy     #1
        sta     (dc_ptr),y      ; main 2g+1
        dey
        lda     dc_m0
        sta     (dc_ptr),y      ; main 2g
        sta     $C055
        lda     dc_a0
        sta     (dc_ptr),y      ; aux 2g
        iny
        lda     dc_a1
        sta     (dc_ptr),y      ; aux 2g+1
        sta     $C054
        inx
        cpx     dc_y1
        bcc     @row
@done:  plp
        rts

dc_buf_lo:
.repeat 7, K
        .byte   <(dc_colbuf + K * DC_BUF)
.endrepeat
dc_buf_hi:
.repeat 7, K
        .byte   >(dc_colbuf + K * DC_BUF)
.endrepeat
; dc_tKJ[c]: bits of colour c as pixel K of a group, inside byte J.
.macro DC_TAB K, J
.repeat 16, CC
        .byte   (((((CC >> 1) | (CC << 3)) & 15) << (4 * K)) >> (7 * J)) & $7F
.endrepeat
.endmacro
dc_t00: DC_TAB 0, 0
dc_t10: DC_TAB 1, 0
dc_t11: DC_TAB 1, 1
dc_t21: DC_TAB 2, 1
dc_t31: DC_TAB 3, 1
dc_t32: DC_TAB 3, 2
dc_t42: DC_TAB 4, 2
dc_t52: DC_TAB 5, 2
dc_t53: DC_TAB 5, 3
dc_t63: DC_TAB 6, 3
        dhgr_row_tables dc_row_lo, dc_row_hi    ; dev/lib/hgrc/dhgr_layout.inc

.segment "DCBSS"
dc_colbuf: .res 7 * DC_BUF
.segment "DCCODE"
.endif

; Per column x: physical byte (or $FF), pixel bits and pattern row j*16 of
; the aux and main byte it touches; x mod 7; group.
; DC_COLUMN sets dc_b0..dc_b3, the bits of pixel XI in the bytes j = 0..3
; of its group (aux even, main even, aux odd, main odd).
.macro DC_COLUMN XI
        dc_b0 .set ($F << (4 * ((XI) .mod 7))) & $7F
        dc_b1 .set (($F << (4 * ((XI) .mod 7))) >> 7) & $7F
        dc_b2 .set (($F << (4 * ((XI) .mod 7))) >> 14) & $7F
        dc_b3 .set (($F << (4 * ((XI) .mod 7))) >> 21) & $7F
.endmacro
dc_xaux_off:
.repeat 140, XI
        DC_COLUMN XI
        .if dc_b0
        .byte   (XI / 7) * 2
        .elseif dc_b2
        .byte   (XI / 7) * 2 + 1
        .else
        .byte   $FF
        .endif
.endrepeat
dc_xaux_bits:
.repeat 140, XI
        DC_COLUMN XI
        .byte   dc_b0 | dc_b2
.endrepeat
dc_xaux_j:
.repeat 140, XI
        DC_COLUMN XI
        .if dc_b0
        .byte   0
        .else
        .byte   32
        .endif
.endrepeat
dc_xmain_off:
.repeat 140, XI
        DC_COLUMN XI
        .if dc_b1
        .byte   (XI / 7) * 2
        .elseif dc_b3
        .byte   (XI / 7) * 2 + 1
        .else
        .byte   $FF
        .endif
.endrepeat
dc_xmain_bits:
.repeat 140, XI
        DC_COLUMN XI
        .byte   dc_b1 | dc_b3
.endrepeat
dc_xmain_j:
.repeat 140, XI
        DC_COLUMN XI
        .if dc_b1
        .byte   16
        .else
        .byte   48
        .endif
.endrepeat
dc_xk:
.repeat 140, XI
        .byte   XI .mod 7
.endrepeat
dc_xgroup:
.repeat 140, XI
        .byte   XI / 7
.endrepeat
; Solid colour bytes dc_pat[j * 16 + c]: j = 0 aux even, 1 main even,
; 2 aux odd, 3 main odd (Apple IIe TN #3 table, see tools/dhgr_palette.py).
dc_pat:
.repeat 4, JJ
.repeat 16, CC
        .byte   ((((CC >> 1) | (CC << 3)) & 15) * $1111111 >> (7 * JJ)) & $7F
.endrepeat
.endrepeat

; ----------------------------------------------------------------------------
; Bank-switched part: everything executed while aux is selected. In page 2
; mode this segment is mirrored in aux RAM at the same address.
.segment "DCROWS"

; dc_rmw_pass -- C = 1 aux, 0 main. Rows dc_y0..dc_y1-1 (y0 < y1) of
; physical byte dc_off: byte = byte & dc_and | dc_or.
dc_rmw_pass:
        php
        sei
        bcc     :+
        DC_AUX
:       ldx     dc_y1
        lda     dc_rmw_lo,x
        sta     dc_plant
        lda     dc_rmw_hi,x
        sta     dc_plant+1
        ldx     dc_y0
        lda     dc_rmw_lo,x
        sta     dc_jump
        lda     dc_rmw_hi,x
        sta     dc_jump+1
        ldy     #0
        lda     #OP_RTS
        sta     (dc_plant),y
        ldy     dc_off
        jsr     dc_go
        ldy     #0
        lda     #OP_LDAY
        sta     (dc_plant),y
        DC_MAIN
        plp
        rts
dc_go:  jmp     (dc_jump)

; dc_sta_pass -- C = bank, A = byte, Y = physical byte: store A in rows
; dc_y0..dc_y1-1 (y0 < y1). 5 cycles per row.
dc_sta_pass:
        sta     dc_or
        sty     dc_off
        php
        sei
        bcc     :+
        DC_AUX
:       ldx     dc_y1
        lda     dc_sta_lo,x
        sta     dc_plant
        lda     dc_sta_hi,x
        sta     dc_plant+1
        ldx     dc_y0
        lda     dc_sta_lo,x
        sta     dc_jump
        lda     dc_sta_hi,x
        sta     dc_jump+1
        ldy     #0
        lda     #OP_RTS
        sta     (dc_plant),y
        ldy     dc_off
        lda     dc_or
        jsr     dc_go
        ldy     #0
        lda     #OP_STAY
        sta     (dc_plant),y
        DC_MAIN
        plp
        rts

; dc_clear -- A = colour 0..15: both banks, every byte of the page.
; 64 stores per loop: ~5.2 cycles per byte, ~85 000 cycles in all.
dc_clear:
        and     #15
        tax
        lda     dc_pat,x
        sta     dc_and
        lda     dc_pat+32,x
        sta     dc_or
        txa
        pha
        sec
        jsr     dc_fill_bank
        pla
        tax
        lda     dc_pat+16,x
        sta     dc_and
        lda     dc_pat+48,x
        sta     dc_or
        clc
dc_fill_bank:
        php
        sei
        bcc     :+
        DC_AUX
:       ldy     #0
@loop:  lda     dc_and          ; even physical bytes
.repeat 32, P
        sta     DHGR_BASE + P * 256, y
.endrepeat
        lda     dc_or           ; odd physical bytes
.repeat 32, P
        sta     DHGR_BASE + P * 256 + 1, y
.endrepeat
        iny
        iny
        jne     @loop
        DC_MAIN
        plp
        rts

; Unrolled rows. Row I of the read-modify-write code is 10 bytes, of the
; store code 3 bytes; the extra entry DC_ROWS only ever holds a planted RTS.
dc_rmw_rows:
.repeat DC_ROWS, I
        lda     DC_ROW(I), y
        and     dc_and
        ora     dc_or
        sta     DC_ROW(I), y
.endrepeat
        .byte   OP_LDAY
dc_sta_rows:
.repeat DC_ROWS, I
        sta     DC_ROW(I), y
.endrepeat
        .byte   OP_STAY
dc_rmw_lo:
.repeat DC_ROWS + 1, I
        .byte   <(dc_rmw_rows + I * 10)
.endrepeat
dc_rmw_hi:
.repeat DC_ROWS + 1, I
        .byte   >(dc_rmw_rows + I * 10)
.endrepeat
dc_sta_lo:
.repeat DC_ROWS + 1, I
        .byte   <(dc_sta_rows + I * 3)
.endrepeat
dc_sta_hi:
.repeat DC_ROWS + 1, I
        .byte   >(dc_sta_rows + I * 3)
.endrepeat
.assert dc_sta_rows - dc_rmw_rows = DC_ROWS * 10 + 1, error, "RMW row size"
