; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Clears visible 40-byte scanlines of the selected draw page; preserves holes.
; hgr_clear_rows: A=start, X=end exclusive; requires 0<=start<end<=192.
; hgr_clear_visible: 0..191; hgr_clear_hud32: 160..191.
; hgr_clear_viewport160: 0..159, preserves HUD. These three share one
; unrolled block of absolute stores (patched for the draw page) and leave
; hc_* alone.
; Uses hgr_lo/hi and hgr_draw_page/PAGE2_EOR from hgr_flip.asm.
; Clobbers A,X,Y, hc_row/end/ptr; writable CODE required, not reentrant.
; Define hc_* ZP aliases before inclusion to reuse caller scratch.
.ifndef _HGR_CLEAR_ROWS_LOADED_
_HGR_CLEAR_ROWS_LOADED_ = 1
.zeropage
.ifndef hc_row
hc_row: .res 1
hc_end: .res 1
hc_ptr: .res 2
hc_ptr_hi = hc_ptr+1
.endif
.code
hgr_clear_viewport160:
        ; fdraw FAST's column-major absolute stores, limited to 160 rows.
        ; The first 64 addresses cover two thirds (Y=0..79), then 32
        ; addresses cover rows 128..159 (Y=80..119). HUD and holes survive.
        JSR viewport_sync
        LDA #<viewport_first
        LDX #>viewport_first
        JSR viewport_set_loop
        LDX #80
        JSR viewport_run
        LDY #80
        LDX #40
viewport_last:
.repeat 32, I
        STA $2000 + (I .mod 8) * $400 + (I / 8) * $80,Y
.endrepeat
        INY
        DEX
        BNE viewport_last
        RTS
hgr_clear_visible:
        ; The 64 addresses of one third for Y=0..119: all three thirds,
        ; ~39 500 cycles instead of ~67 000 row by row. Holes survive.
        JSR viewport_sync
        LDA #<viewport_first
        LDX #>viewport_first
        JSR viewport_set_loop
        LDX #120
        BNE viewport_run
hgr_clear_hud32:
        ; Rows 160..191 = the 32 last addresses of the 64 for Y=80..119:
        ; enter the block and loop back at its half.
        JSR viewport_sync
        LDA #<viewport_half
        LDX #>viewport_half
        JSR viewport_set_loop
        LDY #80
        LDX #40
        LDA #0
        JMP viewport_loop
viewport_set_loop:
        STA viewport_loop+1
        STX viewport_loop+2
        LDY #0
        RTS
viewport_run:
        LDA #0
viewport_first:
.repeat 64, I
.if I = 32
viewport_half:
.endif
        STA $2000 + (I .mod 8) * $400 + (I / 8) * $80,Y
.endrepeat
        INY
        DEX
        BEQ viewport_done
viewport_loop:
        JMP viewport_first      ; operand patched: viewport_first / _half
viewport_done:
        RTS
viewport_sync:
        ; Point the 96 absolute stores at the draw page (on a change only).
        LDA hgr_draw_page
        CMP viewport_page
        BEQ @ready
        STA viewport_page
        LDX #0
@patch64:
        LDA viewport_first+2,X
        EOR #PAGE2_EOR
        STA viewport_first+2,X
        INX
        INX
        INX
        CPX #192
        BCC @patch64
        LDX #0
@patch32:
        LDA viewport_last+2,X
        EOR #PAGE2_EOR
        STA viewport_last+2,X
        INX
        INX
        INX
        CPX #96
        BCC @patch32
@ready: RTS
viewport_page: .byte 0
hgr_clear_rows:
        STA hc_row              ; current scanline
        STX hc_end              ; end scanline (exclusive)
@row:   LDY hc_row
        LDA hgr_lo,Y
        STA hc_ptr
        LDA hgr_hi,Y
        STA hc_ptr_hi
        LDA #0
        LDY #39
        ; Forty stores are fixed for every scanline. Unrolling removes
        ; 39 taken branches per row (6,240 per 3D frame).
.repeat 39
        STA (hc_ptr),Y
        DEY
.endrepeat
        STA (hc_ptr),Y
        INC hc_row
        LDA hc_row
        CMP hc_end
        BEQ @done
        JMP @row
@done:
        RTS


.endif
