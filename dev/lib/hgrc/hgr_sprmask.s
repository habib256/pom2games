; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_sprmask.s -- masked pre-shifted sprite kernels for Apple II HGR (cc65).
;
; The SPRMASK family: the save-under complement to the XOR pre-shift engine
; (hgr_preshift_asm.s _hgr_xs_run). XOR is self-erasing but TRASHES a non-uniform
; background while the sprite overlaps it (decor shows through the sprite as
; toggled garbage). These kernels instead do a MASKED blit
;
;     dst[j] = (dst[j] & mask[j]) | data[j]
;
; over a 7-phase pre-shifted bank (hgr_mspr_t in hgr.h: `data` = sprite
; pixels, bit 7 clear; `mask` = ~coverage with bit 7 ALWAYS 1, so the
; background byte's HIRES palette-group bit survives every draw), paired with
; a save-under/restore of the covered byte rectangle. Draw over anything,
; restore, and the background is byte-identical -- what the sprite ENGINE
; (hgr_sprengine.c) is built on.
;
; All four entries share one setup (ms_setup): column x/7 and phase x%7 come
; from the hgr_col7[]/hgr_phase7[] LUTs (no runtime divide -- same trick as
; _hgr_xs_run, including the +256 split for x >= 256), the hgr_mspr_t is
; dereferenced, the phase offset phase*(h*stride) is applied to BOTH the data
; and mask banks by loop-add (no software multiply), and the sprite is
; right-clipped (col+stride > 40) and bottom-clipped (y+h > 192) exactly like
; _hgr_xs_run. Immutable scanline offsets are ORed with the current draw base.
; The legacy mutable row tables retain their public layout for other kernels.
;
; The under-buffer is a plain linear stride*h byte block: row r of the sprite
; rectangle occupies under[r*stride .. r*stride+w) (w = clipped width; the
; clipped tail bytes of a row are simply never touched). Save and restore walk
; it with the same clipped geometry; restore skips unused drawing arithmetic.
;
; Interface -- the C wrapper (hgr_sprengine.c) stores these, then JSRs:
;     _hgr_ms_x     : pixel x (0..279, 16-bit)
;     _hgr_ms_y     : pixel y (0..191)
;     _hgr_ms_spr   : pointer to the hgr_mspr_t {data, mask, stride, h}
;     _hgr_ms_under : pointer to the caller's stride*h save-under buffer
; The caller guarantees x <= 279 / y <= 191 and stride, h >= 1 (the kernels
; still edge-clip on the right/bottom).

.include "hgr_sprite_geometry.inc"
.include "hgr_clip_axes.inc"
.include "hgr_sprite_row.inc"
        .export   _hgr_ms_run
        .export   _hgr_ms_save_run
        .export   _hgr_ms_restore_run
        .export   _hgr_msu_run
        .export   _hgr_ms_block
        .exportzp _hgr_ms_x, _hgr_ms_y, _hgr_ms_spr, _hgr_ms_under
        .import   hgr_fixed_rowlo, hgr_fixed_rowhi, _hgr_base, _hgr_col7, _hgr_phase7
        .import   _hgr_build_columns, _hgr_build_phases
        .importzp ptr1, ptr2, ptr3, ptr4, tmp1, tmp3, tmp4

        .segment "BSS"
_hgr_ms_block: .res 1        ; one-call engine block (1..255), zero = generic
; tmp4 mode survives both table builders, then becomes the phase block.
ms_under_only = tmp4
; The page is latched only after tmp3's product-high lifetime ends.
ms_page = tmp3

; --- interface variables (zero page) ----------------------------------------
        .segment "ZEROPAGE"
_hgr_ms_x:     .res 2       ; pixel x (0..279)
_hgr_ms_y:     .res 1       ; pixel y (0..191)
_hgr_ms_spr:   .res 2       ; -> hgr_mspr_t {data lo/hi, mask lo/hi, stride, h}
_hgr_ms_under: .res 2       ; -> linear save-under buffer (stride*h bytes)
; asm-internal state (derived by ms_setup, persists across the row loop):
ms_col:    .res 1            ; start byte column (x / 7)
ms_yy = tmp1                 ; current scanline after phase arithmetic
ms_w:      .res 1            ; bytes drawn per row (right-clipped)
ms_h:      .res 1            ; rows remaining (bottom-clipped)
ms_stride: .res 1            ; source bytes per row (uniform across phases)
ms_blk = tmp4               ; phase block size, low byte (setup only)
ms_blk_hi = tmp3            ; high byte: full height moves to X before clearing

; zero-page pointer roles (cc65 leaves ptr1..ptr4/tmp1..tmp4 free for leaf asm):
;   ptr1 = framebuffer row base + col (rebuilt per row from the row tables)
;   ptr2 = data row pointer  (phase-adjusted, advanced by stride per row)
;   ptr3 = mask row pointer  (phase-adjusted, advanced by stride per row)
;   ptr4 = under row pointer (advanced by stride per row)
; tmp1 = phase during setup, then ms_yy. tmp3 = full height/product high,
; then ms_page. tmp4 = under-only mode, then phase block. All table builders
; preserve tmp3/tmp4; folded builders borrow tmp1 before phase is assigned.
; Setup reads the stride directly from ms_stride; tmp2 remains untouched.

        .segment "CODE"

; --- ms_setup : shared per-call setup for all four kernels --------------------
; From the _hgr_ms_* parameter block, derive col/phase, deref the hgr_mspr_t,
; apply the phase offset to data+mask, clip, and point ptr4 at the under buffer.
ms_setup:
        lda #0
        sta ms_under_only
        beq ms_setup_common
ms_setup_under:
        lda #1
        sta ms_under_only
ms_setup_common:
        ; Raw callers may only have selected the draw page (row tables).
        ; Prepare optional x tables before using any shared scratch.
        hgr_sprite_column_phase _hgr_ms_x, ms_col, tmp1
        ; Geometry is shared by all entries. Data/mask pointers are needed
        ; only by drawing; ptr1 retains the descriptor until that branch.
        lda _hgr_ms_spr
        sta ptr1
        lda _hgr_ms_spr+1
        sta ptr1+1
        ldy #4
        lda (ptr1),y              ; stride
        sta ms_stride
        sta ms_w                  ; default w = stride
        iny
        lda (ptr1),y              ; h
        sta ms_h                  ; default h
        sta tmp3                  ; tmp3 = full h (for the phase offset)
        hgr_clip_extent 40, ms_col, ms_stride, ms_w
        hgr_clip_extent 192, _hgr_ms_y, tmp3, ms_h
        lda ms_under_only
        bne @poff               ; save/restore never consume data or mask
        ldy #0
        lda (ptr1),y              ; data low
        sta ptr2
        iny
        lda (ptr1),y              ; data high
        sta ptr2+1
        iny
        lda (ptr1),y              ; mask low
        sta ptr3
        iny
        lda (ptr1),y              ; mask high
        sta ptr3+1

        ; Phase zero skips hint/product reads; both paths consume the hint
        ; through X=0 at @consume. Save/restore branches past that clear.
        ldx tmp1
        beq @consume
        ldy _hgr_ms_block
        lda #0
        ; phase block = h * stride via loop-add (h iterations, no multiply)
        ldx tmp3                  ; capture full h before reusing its scratch
        sta ms_blk_hi
        tya
        bne @product_ready
@hloop:
        clc
        ; A keeps the low product across additions; INC/DEX preserve it.
        adc ms_stride             ; + stride
        bcc @h2
        inc ms_blk_hi
@h2:
        dex
        bne @hloop
@product_ready:
        sta ms_blk
        ; data += phase*blk ; mask += phase*blk (phase iterations of a 16-bit add)
@phases:
        ldx tmp1                  ; phase
@ploop:
        clc
        lda ptr2
        adc ms_blk
        sta ptr2
        lda ptr2+1
        adc ms_blk_hi
        sta ptr2+1
        clc
        lda ptr3
        adc ms_blk
        sta ptr3
        lda ptr3+1
        adc ms_blk_hi
        sta ptr3+1
        dex
        bne @ploop
@consume:
        stx _hgr_ms_block       ; phase zero or the completed loop leaves X=0
@poff:
        ; Phase arithmetic is finished: tmp3/tmp1 now hold page/current row.
        lda _hgr_base
        bne @latepage
        lda #$20
@latepage:
        sta ms_page
        lda _hgr_ms_y
        sta ms_yy
        ; ptr4 = under buffer
        lda _hgr_ms_under
        sta ptr4
        lda _hgr_ms_under+1
        sta ptr4+1
        rts

; --- ms_rowbase : ptr1 = rowbase(ms_yy) + ms_col ------------------------------
; Fixed offsets plus the draw base latched by setup; no mutable row reads.
ms_rowbase:
        ldy ms_yy
        lda hgr_fixed_rowlo,y
        clc
        adc ms_col
        sta ptr1
        lda hgr_fixed_rowhi,y
        ora ms_page
        ; Clipped column <=39 and row low <=$D0: low addition cannot carry.
        sta ptr1+1
        rts

; --- ms_next_row : advance data/mask/under by stride, yy += 1, rows -= 1 ------
; Returns with Z clear while rows remain (callers loop on BNE). ~45 cycles.
; ms_rowbase leaves C=0: row low <=$D0 plus clipped column <=39.
; The byte loops (including unrolled widths) preserve it until this entry.
ms_next_row:
        hgr_add_stride ptr2, ms_stride
        clc
        hgr_add_stride ptr3, ms_stride
        ; Save/restore enters this same tail, without data/mask advancement.
        clc                     ; data/mask advances may have carried
; Direct save/restore callers also arrive with C=0 from ms_rowbase.
ms_next_under:
        hgr_add_stride ptr4, ms_stride
        inc ms_yy
        dec ms_h                ; Z = done (flags survive the RTS)
        rts

; Byte operations preserve carry from ms_rowbase for the next-row helpers.
.macro blend_pixel_byte
        and (ptr3),y
        ora (ptr2),y
        sta (ptr1),y
.endmacro

.macro draw_byte
        lda (ptr1),y
        blend_pixel_byte
.endmacro

.macro save_byte
        lda (ptr1),y
        sta (ptr4),y
.endmacro

.macro restore_byte
        lda (ptr4),y
        sta (ptr1),y
.endmacro

.macro save_draw_byte
        save_byte
        blend_pixel_byte
.endmacro

; Generic rows walk backward from the clipped width. The two common fixed
; widths walk forward with unrolled copies. Both advance by the source stride.
.macro sprite_rows operation, advance, width
        .local row, column
row:
        jsr ms_rowbase
        .ifblank width
        ldy ms_w
        dey
column:
        operation
        dey
        bpl column
        .else
        ldy #0
        .repeat width, col
          .if col > 0
            iny
          .endif
          operation
        .endrepeat
        .endif
        jsr advance
        bne row
        rts
.endmacro

; Masked draw (26 cycles/byte in the generic loop).
_hgr_ms_run:
        jsr ms_setup
        sprite_rows draw_byte, ms_next_row

; Save the visible bytes. Clipped tail bytes in the under buffer stay intact.
_hgr_ms_save_run:
        jsr ms_setup_under
        sprite_rows save_byte, ms_next_under

; Restore the same rectangle (16 cycles/byte in the generic loop).
_hgr_ms_restore_run:
        jsr ms_setup_under
        lda ms_w
        cmp #2
        beq restore2
        cmp #4
        beq restore4
        sprite_rows restore_byte, ms_next_under
restore2:
        sprite_rows restore_byte, ms_next_under, 2
restore4:
        sprite_rows restore_byte, ms_next_under, 4

; Save and draw in one pass (32 cycles/byte in the generic loop).
_hgr_msu_run:
        jsr ms_setup
        lda ms_w
        cmp #2
        beq draw2
        cmp #4
        beq draw4
        sprite_rows save_draw_byte, ms_next_row
draw2:
        sprite_rows save_draw_byte, ms_next_row, 2
draw4:
        sprite_rows save_draw_byte, ms_next_row, 4
