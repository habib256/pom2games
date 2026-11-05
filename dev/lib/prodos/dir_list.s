; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Native cc65 directory listing; dir.c remains the portable reference.
; Fastcall AX=suffix; names/name_len/max on the C stack. Main RAM, D=0,
; non-reentrant, outside IRQs. Destroys A/X/Y, flags and cc65 ptr1..4/tmp1..4.
; The six-byte argument frame persists across MLI calls; parser scratch does not.
; Set PRODOS_DIR_CUSTOM_SEGMENTS and define these three string macros to
; place code, initialised parameter lists and private BSS independently.
.ifndef PRODOS_DIR_CUSTOM_SEGMENTS
.define PRODOS_DIR_CODE_SEGMENT "CODE"
.define PRODOS_DIR_DATA_SEGMENT "DATA"
.define PRODOS_DIR_BSS_SEGMENT "BSS"
.endif
.export _prodos_dir_list,_prodos_dir_count
.import _prodos_call,_prodos_command,_prodos_params,_prodos_file_iobuf
.import pushax,incsp4,incsp6
.importzp sp,ptr1,ptr2,ptr3,ptr4,tmp1,tmp2,tmp3,tmp4
.macpack longbranch
.segment PRODOS_DIR_BSS_SEGMENT
_prodos_dir_count:.res 1
block:.res 512
err:.res 1
first:.res 1
elen:.res 1
per:.res 1
sl:.res 1
.segment PRODOS_DIR_DATA_SEGMENT
p_prefix:.byte 1
 .word block
p_open:.byte 3
 .word block,0
 .byte 0
p_read:.byte 4,0
 .word block,512,0
p_close:.byte 1,0
.segment PRODOS_DIR_CODE_SEGMENT
_prodos_dir_list:
 sta tmp1                  ; preserve fastcall suffix low across max check
 lda #0
 sta _prodos_dir_count
 ldy #0
 lda (sp),y                 ; original four-byte argument frame: max at 0
 bne has_capacity
 lda #0
 tax
 jmp incsp4
has_capacity:
 lda tmp1
 jsr pushax                 ; frame: suffix0/1,max2,name_len3,names4/5
 ldy #0
 lda (sp),y
 sta ptr2
 iny
 lda (sp),y
 sta ptr2+1
 ldy #0
suffix_length:
 lda (ptr2),y
 beq suffix_ready
 cpy #14
 jeq empty
 iny
 bne suffix_length
suffix_ready:
 sty sl
 lda #1
 sta first
 ldx #<p_prefix
 ldy #>p_prefix
 lda #$C7
 jsr call_mli
 sta err
 jne done
 lda block
 cmp #2
 bcc prefix_ready
 tax
 lda block,x
 cmp #'/'
 bne prefix_ready
 dec block
prefix_ready:
 lda _prodos_file_iobuf
 sta p_open+3
 lda _prodos_file_iobuf+1
 sta p_open+4
 ldx #<p_open
 ldy #>p_open
 lda #$C8
 jsr call_mli
 sta err
 jne done
 lda p_open+5
 sta p_read+1
 sta p_close+1
read_loop:
 lda _prodos_dir_count
 ldy #2
 cmp (sp),y
 jeq close
 ldx #<p_read
 ldy #>p_read
 lda #$CA
 jsr call_mli
 sta err
 jne close
 lda p_read+6
 jne close
 lda p_read+7
 cmp #2
 jne close
 lda first
 beq geometry_ready
 lda block+$23
 sta elen
 lda block+$24
 sta per
geometry_ready:
 lda first
 cmp per
 jcs no_entries
 ldy #0
 lda (sp),y
 sta ptr2
 iny
 lda (sp),y
 sta ptr2+1
 ldy #3
 lda (sp),y
 sta tmp4                  ; destination stride, stable through parser
 iny
 lda (sp),y
 sta ptr3
 iny
 lda (sp),y
 sta ptr3+1
 lda #<(block+4)
 sta ptr1
 lda #>(block+4)
 sta ptr1+1
 lda first
 sta tmp1                  ; directory slot index
 beq entry_loop
 clc
 lda ptr1
 adc elen
 sta ptr1
 bcc entry_loop
 inc ptr1+1
entry_loop:
 lda ptr1
 sta ptr4
 lda ptr1+1
 sta ptr4+1
 ; Advance the next-entry pointer once; this is also the existing bound.
 clc
 lda ptr1
 adc elen
 sta ptr1
 lda ptr1+1
 adc #0
 sta ptr1+1
 cmp #>(block+512)
 bcc entry_valid
 jne block_done
 lda ptr1
 cmp #<(block+512)
 bcc entry_valid
 jne block_done
entry_valid:
 ldy #0
 lda (ptr4),y
 cmp #$10
 jcc next_entry
 cmp #$40
 jcs next_entry
 and #15
 cmp sl
 jcc next_entry
 jeq next_entry
 sta tmp2                  ; name length
 sbc sl                    ; C set: name length minus suffix length
 sta tmp3
 clc
 adc #1
 clc
 adc ptr4
 sta ptr4
 bcc suffix_compare
 inc ptr4+1
suffix_compare:
 ldy sl
 beq matched
 dey
suffix_byte:
 lda (ptr4),y
 cmp (ptr2),y
 bne next_entry
 dey
 bpl suffix_byte
matched:
 ; Back from the suffix to the first name byte, then copy the whole name.
 sec
 lda ptr4
 sbc tmp3
 sta ptr4
 bcs copy_name
 dec ptr4+1
copy_name:
 ldy #0
copy_byte:
 lda (ptr4),y
 sta (ptr3),y
 iny
 cpy tmp2
 bcc copy_byte
 lda #0
 sta (ptr3),y
 inc _prodos_dir_count
 clc
 lda ptr3
 adc tmp4
 sta ptr3
 bcc match_count
 inc ptr3+1
match_count:
 lda _prodos_dir_count
 ldy #2
 cmp (sp),y
 jeq block_done
next_entry:
 inc tmp1
 lda tmp1
 cmp per
 jcc entry_loop
 jmp block_done
block_done:
 ldy #4
 lda ptr3
 sta (sp),y
 iny
 lda ptr3+1
 sta (sp),y
no_entries:
 lda #0
 sta first
 jmp read_loop
close:
 ldx #<p_close
 ldy #>p_close
 lda #$CC
 jsr call_mli
 ldx err
 beq done
 cpx #$4C
 beq done
 txa
done:
 ldx #0
 jmp incsp6
empty:
 lda #0
 beq done
call_mli:
 sta _prodos_command
 stx _prodos_params
 sty _prodos_params+1
 jmp _prodos_call
