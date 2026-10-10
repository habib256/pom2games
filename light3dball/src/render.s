; GPL-3.0. Shared wireframe contours, projection, sprite clipping and ray repairs.
.include "apple2.inc"
.export _game_sound
.export _depth_gauge, _reset_gauge
.import _camera_z, _ball_z, _lives, _level_slots
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
.export _draw_paddle
.import _hgr_ms_save_run, _hgr_phase7, _paddle_rows_data, _paddle_rows_mask
.importzp ptr1, ptr2, ptr3
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
; 49x28 transparent paddle with a black halo. Three row patterns per phase
; replace seven full banks. The shared save/restore still owns both histories.
_draw_paddle:
    jsr _hgr_ms_save_run
    ldx _hgr_ms_x
    lda _hgr_col7,x
    sta paddle_col
    lda _hgr_phase7,x
    tax
    lda paddle_phase_offset,x
    sta paddle_phase
    lda #0
    sta paddle_row
@row:
    ldx #16                 ; transparent middle, with vertical borders
    lda paddle_row
    cmp #3
    bcc @border
    cmp #25
    bcc @pattern
@border:
    ldx #0                  ; black halo with vertical white borders
    cmp #1
    beq @horizontal
    cmp #26
    bne @pattern
@horizontal:
    ldx #8                  ; white horizontal border
@pattern:
    txa
    clc
    adc paddle_phase
    clc
    adc #<_paddle_rows_data
    sta ptr2
    lda #>_paddle_rows_data
    adc #0
    sta ptr2+1
    txa
    clc
    adc paddle_phase
    clc
    adc #<_paddle_rows_mask
    sta ptr3
    lda #>_paddle_rows_mask
    adc #0
    sta ptr3+1
    lda paddle_row
    clc
    adc _hgr_ms_y
    tax
    lda hgr_lo,x
    clc
    adc paddle_col
    sta ptr1
    lda hgr_hi,x
    adc #0
    sta ptr1+1
    ldy #7
@byte:
    lda (ptr1),y
    and (ptr3),y
    ora (ptr2),y
    sta (ptr1),y
    dey
    bpl @byte
    inc paddle_row
    lda paddle_row
    cmp #28
    bne @row
    rts
.segment "RODATA"
paddle_phase_offset: .byte 0,24,48,72,96,120,144
.segment "BSS"
paddle_col: .res 1
paddle_phase: .res 1
paddle_row: .res 1
.code
; Depth rail: player tick and round ball both sit above the level line.
; Redraw the pair together when either moves, preserving overlapping pixels.
_depth_gauge:
    sta gauge_page
    tax
    lda gauge_player,x
    bne @player
    lda #184
    sta wf_x0
    lda #248
    sta wf_x1
    lda #165
    sta wf_y0
    sta wf_y1
    jsr hgr_wire_span
@player:
    lda _camera_z+1
    ldy _camera_z
    jsr gauge_position
    sta gauge_player_new
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
    bne @update
    lda gauge_player_new
    cmp gauge_player,x
    beq @done
@update:
    lda #160
    sta wf_y0
    lda #162
    sta wf_y1
    lda gauge_player,x
    jsr gauge_erase
    ldx gauge_page
    lda gauge_ball,x
    beq @draw_player
    jsr gauge_ball_erase
@draw_player:
    lda #160
    sta wf_y0
    lda #162
    sta wf_y1
    lda gauge_player_new
    ldx gauge_page
    sta gauge_player,x
    jsr gauge_draw
@draw_ball:
    lda gauge_new
    ldx gauge_page
    sta gauge_ball,x
    cmp #0
    beq @done
    jmp gauge_ball_draw
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

; Rounded white sphere: .##. / #### / #### / .##., above the rail.
; The same spans clear exactly its old pixels, leaving the rail intact.
.macro BALL_MARK name, span
name:
    sta gauge_icon_x
    sta wf_x0
    clc
    adc #1
    sta wf_x1
    lda #160
    sta wf_y0
    sta wf_y1
    jsr span
    lda #163
    sta wf_y0
    sta wf_y1
    jsr span
    lda gauge_icon_x
    sec
    sbc #1
    sta wf_x0
    clc
    adc #3
    sta wf_x1
    lda #161
    sta wf_y0
    sta wf_y1
    jsr span
    lda #162
    sta wf_y0
    sta wf_y1
    jmp span
.endmacro
BALL_MARK gauge_ball_draw, hgr_wire_span
BALL_MARK gauge_ball_erase, hgr_wire_clear_span
gauge_position:
    ; Exact floor(64*z/level_length) = floor(z/(2*level_slots)).
    ; Eight binary division steps, independent of the length of the course.
    sty gauge_bits
    pha
    lda _level_slots
    asl a
    sta gauge_divisor
    pla
    ldx #8
@bit:
    asl gauge_bits
    rol a
    cmp gauge_divisor
    bcc @next
    sbc gauge_divisor
    inc gauge_bits
@next:
    dex
    bne @bit
    lda gauge_bits
    clc
    adc #184
    rts
.bss
gauge_page: .res 1
gauge_new: .res 1
gauge_player_new: .res 1
gauge_player: .res 2
gauge_ball: .res 2
gauge_bits: .res 1
gauge_divisor: .res 1
gauge_icon_x: .res 1
.code

; Twelve speaker toggles: short contact cues, bounded to 12 ms at 1 MHz.
_game_sound:
    tax
    lda #12
    jmp tone
.include "sound.asm"

; Bind the shared corridor kernel to the game's resident state/tables.
; Keep the historical exported entry names for fixtures and native clients.
PC_CENTER_X = 128
PC_CENTER_Y = 80
PC_DEPTH_SHIFT = 1
PC_BITS = mul_bits
PC_SX = _sx
PC_SY = _sy
PC_LEFT = _left
PC_TOP = _top
PC_DEPTH = _depth
PC_TABLE_X = _scale_x
PC_TABLE_Y = _scale_y
.include "corridor.asm"
_project_x = _a2_corridor_x
_project_y = _a2_corridor_y
_perspective = _a2_corridor_select

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
    txa
    cmp #81
    bcc @table
    eor #255
    clc
    adc #161
@table:
    tay
    clc
    lda _bg_offset_lo,y
    adc #<_bg_bytes
    sta repair_src
    lda _bg_offset_hi,y
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

.segment "ASSETS"
.export _hgr_font
BBFONT_FIRST = $20
BBFONT_LAST = $5A
_hgr_font:
.include "bbfont.inc"
.code

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
