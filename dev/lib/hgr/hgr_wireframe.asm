; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Native HGR wire-frame contours, horizontal visibility windows and fast erase.
; Requires hgr_lo/hi for the selected page; X 0..255, Y 0..191, valid ordered
; axis-aligned endpoints. No implicit Y clipping. CODE and scanline tables
; must be writable. Monochrome backdrop: full horizontal bytes reset bit 7.
; hgr_wire_rect: clip and OR-draw rectangle; record each visible edge.
; hgr_wire_line: clip and OR-draw one axis-aligned line; record it.
; wf_history: caller-owned append pointer, at least 16 free bytes per rectangle.
; hgr_wire_erase: wf_history=start of old buffer, wf_count=number of lines;
; clear pixels along those contours, preserving outside edge fragments.
; Caller keeps separate histories per page and restores sprites before erasing.
; Optional HGR_WIRE_AFTER_HLINE/VLINE callbacks repair a caller-owned backdrop
; after an old contour is erased. Endpoints remain in wf_x0/y0/x1/y1; hooks
; must preserve wf_history and wf_count. Default backdrop is plain black.
; All calls clobber A/X/Y and scratch; non-reentrant, no display synchronization.
.ifndef _HGR_WIREFRAME_LOADED_
_HGR_WIREFRAME_LOADED_ = 1
.ifndef WF_COL_TABLE
WF_COL_TABLE = hgr_col
.endif
.ifndef WF_MASK_TABLE
WF_MASK_TABLE = hgr_mask
.endif
.zeropage
.ifndef wf_x0
wf_x0: .res 1
.endif
.ifndef wf_y0
wf_y0: .res 1
.endif
.ifndef wf_x1
wf_x1: .res 1
.endif
.ifndef wf_y1
wf_y1: .res 1
.endif
.ifndef wf_clip_left
wf_clip_left: .res 1
.endif
.ifndef wf_clip_right
wf_clip_right: .res 1
.endif
.ifndef wf_count
wf_count: .res 1
.endif
.ifndef wf_history
wf_history: .res 2
.endif
.ifndef wf_ptr
wf_ptr: .res 2
.endif
.ifndef wf_left
wf_left: .res 1
.endif
.ifndef wf_right
wf_right: .res 1
.endif
.ifndef wf_top
wf_top: .res 1
.endif
.ifndef wf_bottom
wf_bottom: .res 1
.endif
.ifndef wf_keep_left
wf_keep_left: .res 1
.endif
.ifndef wf_keep_right
wf_keep_right: .res 1
.endif
.ifndef wf_clear_width
wf_clear_width: .res 1
.endif
.include "hgr_span.asm"
.code
hgr_wire_span:
    lda wf_y0
    cmp wf_y1
    beq wf_horizontal
    lda wf_x0
    cmp wf_x1
    beq wf_vertical
    rts                     ; this renderer submits axis-aligned spans only
wf_horizontal:
    tax
    lda hgr_lo,x
    sta hs_ptr
    lda hgr_hi,x
    sta hs_ptr+1
    ldx wf_x0
    lda WF_COL_TABLE,x
    tay
    lda WF_MASK_TABLE,x
    sec
    sbc #1
    eor #$7F
    sta hs_left_mask
    ldx wf_x1
    lda WF_COL_TABLE,x
    sta hs_end_col
    lda WF_MASK_TABLE,x
    asl
    sec
    sbc #1
    and #$7F
    sta hs_right_mask
    jmp hgr_hspan
wf_vertical:
    tax
    lda WF_COL_TABLE,x
    tay
    lda WF_MASK_TABLE,x
    sta hs_left_mask
    ldx wf_y0
    lda wf_y1
    clc
    adc #1
    jmp hgr_vspan
; Clear a column interval without a per-byte branch. The setup selects a
; suffix of forty unrolled stores; A=0 and Y=start at the call site.
wf_prepare_clear:
    sta wf_clear_width
    lda #40
    sec
    sbc wf_clear_width
    sta wf_clear_width
    asl a
    clc
    adc wf_clear_width
    clc
    adc #<wf_clear_stores
    sta wf_clear_columns+1
    lda #>wf_clear_stores
    adc #0
    sta wf_clear_columns+2
    rts
wf_clear_columns:
    jmp wf_clear_stores
wf_clear_stores:
.repeat 40
    sta (wf_ptr),y
    iny
.endrepeat
    rts

; Draw only visible axis-aligned contours; never fill hidden surfaces.
hgr_wire_rect:
    lda wf_x0
    sta wf_left
    lda wf_x1
    sta wf_right
    lda wf_y0
    sta wf_top
    lda wf_y1
    sta wf_bottom
    lda wf_top
    sta wf_y1
    jsr hgr_wire_line
    lda wf_left
    sta wf_x0
    lda wf_right
    sta wf_x1
    lda wf_bottom
    sta wf_y0
    sta wf_y1
    jsr hgr_wire_line
    lda wf_left
    sta wf_x0
    sta wf_x1
    lda wf_top
    sta wf_y0
    jsr hgr_wire_line
    lda wf_right
    sta wf_x0
    sta wf_x1
    lda wf_top
    sta wf_y0
    lda wf_bottom
    sta wf_y1
    jmp hgr_wire_line

hgr_wire_line:
    lda wf_clip_left
    cmp wf_clip_right
    bcc @valid
    beq @valid
    rts
@valid:
    lda wf_x1
    cmp wf_clip_left
    bcc @hidden
    lda wf_x0
    cmp wf_clip_right
    bcc @intersect
    beq @intersect
@hidden:
    rts
@intersect:
    lda wf_x0
    cmp wf_clip_left
    bcs @right
    lda wf_clip_left
    sta wf_x0
@right:
    lda wf_x1
    cmp wf_clip_right
    bcc @record
    beq @record
    lda wf_clip_right
    sta wf_x1
@record:
    ldy #0
    lda wf_x0
    sta (wf_history),y
    iny
    lda wf_y0
    sta (wf_history),y
    iny
    lda wf_x1
    sta (wf_history),y
    iny
    lda wf_y1
    sta (wf_history),y
    clc
    lda wf_history
    adc #4
    sta wf_history
    bcc @draw
    inc wf_history+1
@draw:
    jmp hgr_wire_span

hgr_wire_erase:
    lda wf_count
    beq @done
@line:
    ldy #0
    lda (wf_history),y
    sta wf_x0
    iny
    lda (wf_history),y
    sta wf_y0
    iny
    lda (wf_history),y
    sta wf_x1
    iny
    lda (wf_history),y
    sta wf_y1
    jsr hgr_wire_clear_span
    clc
    lda wf_history
    adc #4
    sta wf_history
    bcc @next
    inc wf_history+1
@next:
    dec wf_count
    bne @line
@done:
    rts

hgr_wire_clear_span:
    lda wf_y0
    cmp wf_y1
    bne wf_erase_vertical
    tax
    lda hgr_lo,x
    sta wf_ptr
    lda hgr_hi,x
    sta wf_ptr+1
    ldx wf_x0
    lda WF_COL_TABLE,x
    sta wf_left
    lda WF_MASK_TABLE,x
    sec
    sbc #1
    sta wf_keep_left
    ldx wf_x1
    lda WF_COL_TABLE,x
    sta wf_right
    lda WF_MASK_TABLE,x
    asl a
    sec
    sbc #1
    eor #$7F
    sta wf_keep_right
    ldy wf_left
    cpy wf_right
    beq @single
    lda (wf_ptr),y
    and wf_keep_left
    sta (wf_ptr),y
    lda wf_right
    sec
    sbc wf_left
    sec
    sbc #1
    jsr wf_prepare_clear
    ldy wf_left
    iny
    lda #0
    jsr wf_clear_columns
    lda (wf_ptr),y
    and wf_keep_right
    sta (wf_ptr),y
    .ifdef HGR_WIRE_AFTER_HLINE
    jmp HGR_WIRE_AFTER_HLINE
    .else
    rts
    .endif
@single:
    lda wf_keep_left
    ora wf_keep_right
    and (wf_ptr),y
    sta (wf_ptr),y
    .ifdef HGR_WIRE_AFTER_HLINE
    jmp HGR_WIRE_AFTER_HLINE
    .else
    rts
    .endif
wf_erase_vertical:
    ldx wf_x0
    lda WF_COL_TABLE,x
    tay
    lda WF_MASK_TABLE,x
    eor #255
    sta wf_keep_left
    ldx wf_y0
@row:
    lda hgr_lo,x
    sta wf_ptr
    lda hgr_hi,x
    sta wf_ptr+1
    lda (wf_ptr),y
    and wf_keep_left
    sta (wf_ptr),y
    cpx wf_y1
    beq @done
    inx
    jmp @row
@done:
    .ifdef HGR_WIRE_AFTER_VLINE
    jmp HGR_WIRE_AFTER_VLINE
    .else
    rts
    .endif


.endif
