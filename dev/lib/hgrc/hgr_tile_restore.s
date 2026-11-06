; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Native tile-background restoration. cc65 fastcall height=A, other args
; on software stack. Main RAM/ZP, D=0; non-reentrant, never call from IRQ.
; Code must be writable main RAM: all eight screen operands are patched
; afresh for each valid row. Both tile-base ADC operands are also refreshed
; from each supplied context before drawing; no patched operand is cached.
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
row = tmp4                   ; origin uses the tile row before scan is set
scan = tmp4
map = ptr3                  ; screen stores no longer need a ZP pointer
; Preflight retains height/count until checked. Its origin/next_map_row
; helpers touch ptr1 only; ptr2 becomes a source pointer at draw_tile.
check_rows = ptr2
; Drawing consumes the clipped height directly; count is dead after preflight.
rows = height
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
 ; Refresh both source operands even after rejected calls or a CODE reload.
 lda (ptr1),y
 sta source_low+1
 iny
 lda (ptr1),y
 sta source_high+1
 ora source_low+1
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
 sta check_rows
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
 dec check_rows
 bne check_row
checked:
 jsr origin
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
 .repeat 8,P
 sta draw_store0+1+6*P
 .endrepeat
 lda hgr_fixed_rowhi,x
 ; Low-row ADC <=208+39 leaves C=0; eight STA patches and LDA preserve it.
 ora base                     ; ORA also preserves carry (including after RTI)
 .repeat 8,P
 sta draw_store0+2+6*P
 .if P<7
 adc #4
 .endif
 .endrepeat
 ldx #0
draw_tile:
 ; X remains the screen/map column; Y is free for the glyph source next.
 txa
 tay
 lda (ptr1),y
 tay
 lsr
 lsr
 lsr
 lsr
 lsr
 sta ptr2+1
 tya
 asl
 asl
 asl
 clc
source_low:
 adc #$FF
 sta ptr2
 lda ptr2+1
source_high:
 adc #$FF
 sta ptr2+1
 ldy #0
.repeat 8,P
 .if P>0
 iny
 .endif
 lda (ptr2),y
 .if P=0
draw_store0:
 .endif
 .assert * = draw_store0 + 6*P, error, "tile store stride"
 sta $FFFF,x
.endrepeat
map_advanced:
 inx                           ; X is the clipped column count (width 1..40)
 cpx width                     ; next tile/row arithmetic resets C before reuse
 jne draw_tile
 ; ptr1 stays at this map row; X supplied each tile column.
 clc
 lda ptr1
 adc #40
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
