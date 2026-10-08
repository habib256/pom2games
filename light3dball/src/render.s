; GPL-3.0. Shared wireframe contours, projection, sprite clipping and ray repairs.
.include "apple2.inc"
.export _game_sound
.export _depth_gauge, _reset_gauge
.import _camera_z, _ball_z, _lives
.export _fast_line, _line_x0, _line_y0, _line_x1, _line_y1
.export _frame_mark
.export _erase_scene, _refresh_rays, _scene_rectangle, _rect_cursor
.export _scene_line_count, _scene_clip_left, _scene_clip_right
.export _ray_left_top, _ray_left_bottom, _ray_right_top, _ray_right_bottom
.export _ray_row0, _ray_row1
.import _ray_upper_y
.import _bg_offset_lo, _bg_offset_hi, _bg_bytes
.import _hgr_rowlo, _hgr_rowhi, _hgr_base, _hgr_col7, _hgr_mask7
.export _project_x, _project_y, _perspective, _clip_ball
.export _ball_clip_left, _ball_clip_right
.import _sx, _sy, _left, _top, _depth, _scale_x, _scale_y
.importzp _hgr_ms_x, _hgr_ms_y, _hgr_ms_spr, _hgr_ms_under
PAGE2_EOR = $60
hgr_lo = _hgr_rowlo
hgr_hi = _hgr_rowhi
.zeropage
_ray_left_top: .res 1
_ray_left_bottom: .res 1
_ray_right_top: .res 1
_ray_right_bottom: .res 1
_ray_row0: .res 1
_ray_row1: .res 1
ray_clear: .res 1
ray_neighbor: .res 1
ray_count: .res 1
ray_distance: .res 1
repair_ptr: .res 2
repair_src: .res 2
repair_offset: .res 1
ray_value: .res 1
mul_bits: .res 1
_ball_clip_left: .res 1
_ball_clip_right: .res 1
clip_keep: .res 2
clip_col: .res 1
clip_row: .res 1
clip_rows: .res 1
WF_COL_TABLE = _hgr_col7
WF_MASK_TABLE = _hgr_mask7
wf_ptr = repair_ptr
HGR_WIRE_AFTER_HLINE = wire_restore_hline
HGR_WIRE_AFTER_VLINE = restore_vertical_rays
.include "hgr_wireframe.asm"
_line_x0 = wf_x0
_line_y0 = wf_y0
_line_x1 = wf_x1
_line_y1 = wf_y1
_scene_clip_left = wf_clip_left
_scene_clip_right = wf_clip_right
_scene_line_count = wf_count
_rect_cursor = wf_history
_fast_line = hgr_wire_span
_scene_rectangle = hgr_wire_rect
_erase_scene = hgr_wire_erase
.code
; Depth rail: upper tick = player, lower tick = ball, left = entrance.
; Only old ticks are erased, using the shared black-line primitive.
_depth_gauge:
    sta gauge_page
    tax
    lda gauge_player,x
    bne @player
    lda #184
    sta wf_x0
    lda #252
    sta wf_x1
    lda #163
    sta wf_y0
    sta wf_y1
    jsr hgr_wire_span
@player:
    lda _camera_z+1
    ldy _camera_z
    jsr gauge_position
    sta gauge_new
    ldx gauge_page
    cmp gauge_player,x
    beq @ball
    lda #160
    sta wf_y0
    lda #162
    sta wf_y1
    ldx gauge_page
    lda gauge_player,x
    jsr gauge_erase
    lda gauge_new
    ldx gauge_page
    sta gauge_player,x
    jsr gauge_draw
@ball:
    lda _lives
    beq @new_ball
    lda _ball_z+1
    ldy _ball_z
    jsr gauge_position
@new_ball:
    sta gauge_new
    ldx gauge_page
    cmp gauge_ball,x
    beq @done
    lda #164
    sta wf_y0
    lda #166
    sta wf_y1
    ldx gauge_page
    lda gauge_ball,x
    jsr gauge_erase
    lda gauge_new
    ldx gauge_page
    sta gauge_ball,x
    cmp #0
    beq @done
    jmp gauge_draw
@done:
    rts
_reset_gauge:
    tax
    lda #0
    sta gauge_player,x
    sta gauge_ball,x
    rts
gauge_erase:
    beq @done
    sta wf_x0
    sta wf_x1
    jmp hgr_wire_clear_span
@done:
    rts
gauge_draw:
    sta wf_x0
    sta wf_x1
    jmp hgr_wire_span
gauge_position:
    ; Exact floor(z/8), z in 0..544. No C division or multiplication.
    asl a
    asl a
    asl a
    asl a
    asl a
    sta mul_bits
    tya
    lsr a
    lsr a
    lsr a
    ora mul_bits
    clc
    adc #184
    rts
.bss
gauge_page: .res 1
gauge_new: .res 1
gauge_player: .res 2
gauge_ball: .res 2
.code

; Twelve speaker toggles: short contact cues, bounded to 12 ms at 1 MHz.
_game_sound:
    tax
    lda #12
    jmp tone
.include "sound.asm"

; floor(value*scale/128) for value 0..127. Seven shift/add steps, no C
; 16-bit multiplication helpers. cc65 fastcall byte argument/result in A/X.
.macro PROJECT name, scale, origin
name:
    sta mul_bits
    lda #0
    ldx #7
@multiply:
    lsr mul_bits
    bcc @shift
    clc
    adc scale
@shift:
    ror a
    dex
    bne @multiply
    clc
    adc origin
    rts
.endmacro
PROJECT _project_x, _sx, _left
PROJECT _project_y, _sy, _top

_perspective:
    cpx #2
    bcs @far
    stx mul_bits
    lsr mul_bits
    ror a
    tax
    jmp @lookup
@far:
    ldx #255
@lookup:
    stx _depth
    lda _scale_x,x
    sta _sx
    lsr a
    eor #255
    clc
    adc #129
    sta _left
    lda _scale_y,x
    sta _sy
    lsr a
    eor #255
    clc
    adc #81
    sta _top
    rts

; Restore covered pixels from the ball's original save-under rectangle.
; Current ball banks all have stride 2. The saved background is untouched,
; so the regular reverse-order sprite restore remains byte-exact.
_clip_ball:
    ldx _hgr_ms_x
    lda _hgr_col7,x
    sta clip_col
    ldx #0
@mask:
    lda #$7F
    sta clip_keep,x
    ldy _ball_clip_left
    lda clip_col
    cmp _hgr_col7,y
    bcc @hidden
    bne @right
    lda _hgr_mask7,y
    sec
    sbc #1
    eor #$7F
    sta clip_keep,x
@right:
    ldy _ball_clip_right
    lda clip_col
    cmp _hgr_col7,y
    bcc @advance
    bne @hidden
    lda _hgr_mask7,y
    asl a
    sec
    sbc #1
    and clip_keep,x
    sta clip_keep,x
    jmp @advance
@hidden:
    lda #0
    sta clip_keep,x
@advance:
    inc clip_col
    inx
    cpx #2
    bne @mask
    lda clip_keep
    and clip_keep+1
    cmp #$7F
    beq @done
    ldx _hgr_ms_x
    lda _hgr_col7,x
    sta clip_col
    lda _hgr_ms_y
    sta clip_row
    ldy #5
    lda (_hgr_ms_spr),y
    sta clip_rows
    lda _hgr_ms_under
    sta repair_src
    lda _hgr_ms_under+1
    sta repair_src+1
@row:
    ldx clip_row
    lda _hgr_rowlo,x
    clc
    adc clip_col
    sta repair_ptr
    lda _hgr_rowhi,x
    adc #0
    sta repair_ptr+1
    ldy #0
    ldx #0
@byte:
    lda clip_keep,x
    eor #255
    and (repair_src),y
    sta repair_offset
    lda (repair_ptr),y
    and clip_keep,x
    ora repair_offset
    sta (repair_ptr),y
    iny
    inx
    cpx #2
    bne @byte
    clc
    lda repair_src
    adc #2
    sta repair_src
    bcc @next
    inc repair_src+1
@next:
    inc clip_row
    dec clip_rows
    bne @row
@done:
    rts

_frame_mark:
    rts
wire_restore_hline:
    ldx _line_y0
    cpx #160
    bcs @done
    jmp restore_ray_row
@done:
    rts
; Remove previous sparse rays, then reveal only their visible portions. Old
; contours have already been erased; new contours are drawn afterwards.
_refresh_rays:
    lda #1
    sta ray_clear
    ldx _ray_row0
    jmp update_rays
restore_ray_row:
    stx _ray_row0
    stx _ray_row1
    lda #0
    sta ray_clear
update_rays:
@row:
    lda _hgr_rowlo,x
    sta repair_ptr
    lda _hgr_rowhi,x
    sta repair_ptr+1
    clc
    lda _bg_offset_lo,x
    adc #<_bg_bytes
    sta repair_src
    lda _bg_offset_hi,x
    adc #>_bg_bytes
    sta repair_src+1
    ldy #0
@byte:
    lda (repair_src),y
    cmp #255
    beq @next
    sta clip_col
    iny
    lda (repair_src),y
    sta ray_value
    iny
    sty repair_offset
    ldy clip_col
    lda ray_clear
    beq @visibility
    lda #0
    sta (repair_ptr),y
@visibility:
    cpy #18
    bcs @right
    txa
    cmp _ray_left_top
    bcc @visible
    cmp _ray_left_bottom
    bcc @skip
    beq @skip
    bcs @visible
@right:
    txa
    cmp _ray_right_top
    bcc @visible
    cmp _ray_right_bottom
    bcc @skip
    beq @skip
@visible:
    lda ray_value
    ora (repair_ptr),y
    sta (repair_ptr),y
@skip:
    ldy repair_offset
    jmp @byte
@next:
    cpx _ray_row1
    beq @done
    inx
    jmp @row
@done:
    rts

; A vertical contour can cross each fixed diagonal only once. Repair just the
; neighboring scanlines of those intersections, not its whole height.
restore_vertical_rays:
    lda _line_x0
    cmp #2
    bcc @done
    cmp #255
    bcs @done
    cmp #129
    bcs @right
    sec
    sbc #2
    jmp @distance
@right:
    lda #254
    sec
    sbc _line_x0
@distance:
    sta ray_distance
    tax
    lda _ray_upper_y,x
    jsr restore_neighbors
    ldx ray_distance
    lda _ray_upper_y,x
    cmp #255
    beq @done
    eor #255
    clc
    adc #161              ; lower ray is exactly 160 - upper ray
    jmp restore_neighbors
@done:
    rts
restore_neighbors:
    cmp #255
    beq @done
    sec
    sbc #1
    sta ray_neighbor
    lda #3
    sta ray_count
@row:
    ldx ray_neighbor
    cpx _line_y0
    bcc @next
    cpx _line_y1
    bcc @restore
    bne @next
@restore:
    jsr restore_ray_row
@next:
    inc ray_neighbor
    dec ray_count
    bne @row
@done:
    rts
