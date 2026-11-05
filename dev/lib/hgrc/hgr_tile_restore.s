; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Native tile-background restoration. cc65 fastcall height=A, other args
; on software stack. Main RAM/ZP, D=0; non-reentrant, never call from IRQ.
; A/X/Y, flags, ptr1-ptr4 and tmp1-tmp4 destroyed. The initial popa/popax
; helpers preserve these temporaries; all later calls stay within this file.
.export _hgr_tile_restore
.import popa,popax,hgr_fixed_rowlo,hgr_fixed_rowhi
.importzp ptr1,ptr2,ptr3,ptr4,tmp1,tmp2,tmp3,tmp4
.macpack longbranch
base = ptr4
col = ptr4+1
width = tmp1
height = tmp2
count = tmp3                  ; no longer needed once ID validation succeeds
rowhi = tmp3
row = tmp4                   ; origin uses the tile row before scan is set
scan = tmp4
.bss
map: .res 2
tiles: .res 2
left: .res 1
rows: .res 1
.rodata
maplo: .repeat 24,I
 .byte <(I*40)
.endrepeat
maphi: .repeat 24,I
 .byte >(I*40)
.endrepeat
.code
_hgr_tile_restore:
 sta height
 jsr popa
 sta width
 jsr popa
 sta row
 jsr popa
 sta col
 jsr popa
 sta base
 jsr popax
 sta ptr1
 stx ptr1+1
 ora ptr1+1
 jeq bad
 lda base
 cmp #1
 beq page1
 cmp #2
 jne bad
 lda #$40
 bne page_ready
page1: lda #$20
page_ready:
 sta base
 lda col
 cmp #40
 jcs bad
 lda row
 cmp #24
 jcs bad
 lda width
 jeq bad
 lda height
 jeq bad
 lda #40
 sec
 sbc col
 cmp width
 bcs clip_height
 sta width
clip_height:
 lda #24
 sec
 sbc row
 cmp height
 bcs context
 sta height
context:
 ldy #0
 lda (ptr1),y
 sta map
 iny
 lda (ptr1),y
 sta map+1
 ora map
 jeq bad
 iny
 lda (ptr1),y
 sta tiles
 iny
 lda (ptr1),y
 sta tiles+1
 ora tiles
 jeq bad
 iny
 lda (ptr1),y
 sta count
 iny
 lda (ptr1),y
 beq small_count
 cmp #1
 jne bad
 lda count
 jne bad
 jmp checked
small_count:
 lda count
 jeq bad
 ; Preflight the complete clipped rectangle before any framebuffer write.
 jsr origin
 lda height
 sta rows
check_row:
 ldy #0
check_id:
 lda (ptr1),y
 cmp count
 jcs bad
 iny
 cpy width
 bcc check_id
 jsr next_map_row
 dec rows
 bne check_row
checked:
 jsr origin
 lda height
 sta rows
 lda row
 asl
 asl
 asl
 sta scan
draw_row:
 ; A tile row keeps one row offset: its eight scanlines step $0400 apart.
 ldx scan
 clc
 lda hgr_fixed_rowlo,x
 adc col                       ; row low byte <=208, column <=39: no carry
 sta ptr3
 lda hgr_fixed_rowhi,x
 ora base
 sta rowhi
 lda width
 sta left
draw_tile:
 ldy #0
 lda (ptr1),y
 tax
 lsr
 lsr
 lsr
 lsr
 lsr
 sta ptr2+1
 txa
 asl
 asl
 asl
 clc
 adc tiles
 sta ptr2
 lda ptr2+1
 adc tiles+1
 sta ptr2+1
 lda rowhi
 sta ptr3+1
 clc                    ; stays clear: high bytes never pass $5F
.repeat 8,P
 ldy #P
 lda (ptr2),y
 ldy #0                        ; destination pointer already includes column
 sta (ptr3),y
.if P<7
 lda ptr3+1
 adc #4
 sta ptr3+1
.endif
.endrepeat
 inc ptr1
 bne map_advanced
 inc ptr1+1
map_advanced:
 inc ptr3                      ; clipped rows never cross a 256-byte boundary
 dec left
 jne draw_tile
 ; ptr1 already advanced width bytes. Skip to next map row.
 lda #40
 sec
 sbc width
 clc
 adc ptr1
 sta ptr1
 bcc no_carry
 inc ptr1+1
no_carry:
 lda scan
 clc
 adc #8
 sta scan
 dec rows
 jne draw_row
 lda #1
 ldx #0
 rts
bad:
 lda #0
 tax
 rts
origin:
 ldx row
 clc
 lda maplo,x
 adc map
 sta ptr1
 lda maphi,x
 adc map+1
 sta ptr1+1
 clc
 lda ptr1
 adc col
 sta ptr1
 bcc origin_done
 inc ptr1+1
origin_done: rts
next_map_row:
 clc
 lda ptr1
 adc #40
 sta ptr1
 bcc next_done
 inc ptr1+1
next_done: rts
