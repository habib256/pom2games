; Adapted from McFadden/Ferrie LZ4FH6502.S, Apache-2.0.
; See lz4fh-NOTICE.txt and lz4fh-LICENSE.txt in this directory.
; lz4fh_unpack: lz4fh_src/dst point to 16-bit input/output pointer slots.
; Destination must be 8-KB aligned (e.g. $2000/$4000), with at most
; 8192 output bytes: match high bytes are ORed with the destination base.
; Trusted fhpack stream only: caller reserves source/output memory; no bounds
; checks. Invalid magic/token rings Monitor bell and jumps to Monitor.
; Clobbers A,X,Y, read/write/match pointer pairs, token/length scratch.
; Self-modifies CODE; not reentrant. Scratch may alias caller's ZP.
.ifndef _LZ4FH_LOADED_
_LZ4FH_LOADED_ = 1
.zeropage
.ifndef lz4fh_src
lz4fh_src: .res 2
lz4fh_dst: .res 2
.endif
.ifndef lz4fh_read
lz4fh_read: .res 2
lz4fh_write: .res 2
lz4fh_match: .res 2
lz4fh_token: .res 1
lz4fh_length: .res 1
.endif
.segment "CODE"
.scope LZ4FH
lz4fh_magic = $66
tok_empty = 253
tok_eod = 254
overrun_check = 0
bell = $ff3a
monitor = $ff69
unpack:
lda lz4fh_src
sta lz4fh_read
lda lz4fh_src+1
sta lz4fh_read+1
lda lz4fh_dst
sta lz4fh_write
lda lz4fh_dst+1
sta lz4fh_write+1
sta _desthi+1
ldy #$00
lda (lz4fh_read),y
cmp #lz4fh_magic
beq goodmagic
fail:
jsr bell
jmp monitor
hi2:
inc lz4fh_read+1
bne nohi2
hi3:
inc lz4fh_read+1
clc
bcc nohi3
hi4:
inc lz4fh_write+1
bne nohi4
notempty:
cmp #tok_eod
bne fail
rts
specialmatch:
cmp #tok_empty
bne notempty
tya
adc lz4fh_read
sta lz4fh_read
bcc mainloop
inc lz4fh_read+1
bne mainloop
hi5:
inc lz4fh_read+1
clc
bcc nohi5
goodmagic:
inc lz4fh_read
bne mainloop
inc lz4fh_read+1
mainloop:
ldy #$00
lda (lz4fh_read),y
sta lz4fh_token
lsr A
lsr A
lsr A
lsr A
beq noliteral
cmp #$0f
bne shortlit
inc lz4fh_read
beq hi2
nohi2:
lda (lz4fh_read),y
adc #14
shortlit: tax
tay
shortlit__litloop:
lda (lz4fh_read),y
dey
sta (lz4fh_write),y
bne shortlit__litloop
txa
sec
adc lz4fh_read
sta lz4fh_read
bcs hi3
nohi3:
txa
adc lz4fh_write
sta lz4fh_write
bcs hi4
nohi4:
dey
noliteral:
lda lz4fh_token
and #$0f
cmp #$0f
bcc noliteral__shortmatch
iny
lda (lz4fh_read),y
cmp #237
bcs specialmatch
adc #15
noliteral__shortmatch:
adc #4
sta lz4fh_length
tax
iny
lda (lz4fh_read),y
sta lz4fh_match
iny
lda (lz4fh_read),y
_desthi: ora #$00
sta lz4fh_match+1
tya
sec
adc lz4fh_read
sta lz4fh_read
bcs hi5
nohi5:
ldy #$00
nohi5__copyloop:
lda (lz4fh_match),y
sta (lz4fh_write),y
iny
dex
bne nohi5__copyloop
lda lz4fh_write
adc lz4fh_length
sta lz4fh_write
bcc mainloop
inc lz4fh_write+1
bne mainloop

.endscope
lz4fh_unpack = LZ4FH::unpack
.endif
