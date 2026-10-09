; Shared source, separately assembled archive members for each HUD format.
; cc65 fastcall ABI: value in A/X, field on software stack. Main RAM/ZP, D=0.
; No drawing from IRQ. A/X return changed cells or $FF; field layout unchanged.
.import popax, _hgr_get_draw_page, _hgr_utoa
.macpack longbranch
.importzp ptr3, _hgr_u_lo, _hgr_u_hi, _hgr_u_ptr
.importzp _hgr_g_col, _hgr_g_bit, _hgr_g_y
.if HUD_SMALL
MAX_DIGITS = 5
.import _hgr_hud8_cell_run
cell_run = _hgr_hud8_cell_run
.else
MAX_DIGITS = 14
.import _hgr_hud_cell_run, _hgr_hud_cell_width, _hgr_build_rows
cell_run = _hgr_hud_cell_run
.endif
.bss
field: .res 2
value: .res 2
number: .res 6
width: .res 1
pagebit: .res 1
valid: .res 1
value_offset: .res 1
digits_offset: .res 1
leading: .res 1
index: .res 1
changed: .res 1
character: .res 1
remaining: .res 2
steps: .res 1
copies: .res 1
.code
field_ptr:
        lda field
        sta ptr3
        lda field+1
        sta ptr3+1
        rts
hud_putu:
        sta value
        stx value+1
        jsr popax
        sta field
        stx field+1
        ora field+1
        bne nonnull
bad:
        lda #$ff
        ldx #0
        rts
nonnull:
        jsr field_ptr
        ldy #3
        lda (ptr3),y
        beq bad
        cmp #MAX_DIGITS+1
        bcs bad
        sta width
        jsr _hgr_get_draw_page
        cmp #2
        beq page2
        lda #1
        sta pagebit
        lda #5
        sta value_offset
        lda #9
        bne offsets
page2:
        lda #2
        sta pagebit
        lda #7
        sta value_offset
        lda #9+MAX_DIGITS
offsets:
        sta digits_offset
        jsr field_ptr
        ldy #4
        lda (ptr3),y
        and pagebit
        sta valid
        jeq convert
        ldy value_offset
        lda (ptr3),y
        cmp value
        bne changed_value
        iny
        lda (ptr3),y
        cmp value+1
        bne changed_value
        lda #0
        tax
        rts
changed_value:
        ; Monotone +1/+2 counters reuse cached decimal digits, including carry.
        ; Each draw page commonly sees every other value. Wrap/backwards and
        ; larger changes retain the general unsigned conversion path.
        ldy value_offset
        sec
        lda value
        sbc (ptr3),y
        sta steps
        iny
        lda value+1
        sbc (ptr3),y
        jcc convert
        jne convert
        lda steps
        jeq convert
        cmp #3
        jcs convert
        lda width
        cmp #6
        bcc copy_count
        lda #5
copy_count:
        sta copies
        lda digits_offset
        clc
        adc width
        tay
        dey
        ldx #4
copy_digits:
        lda (ptr3),y
        sta number,x
        dey
        dex
        dec copies
        bne copy_digits
        txa
        bmi increment_number
        lda #$20
pad_digits:
        sta number,x
        dex
        bpl pad_digits
increment_number:
        ldx #4
carry_digit:
        lda number,x
        cmp #$39
        bne increase
        lda #$30
        sta number,x
        dex
        bpl carry_digit
        jmp convert
increase:
        cmp #$20
        bne normal_digit
        lda #$30
normal_digit:
        clc
        adc #1
        sta number,x
        dec steps
        bne increment_number
        ldx #0
skip_spaces:
        lda number,x
        cmp #$20
        bne compact_number
        inx
        bne skip_spaces
compact_number:
        ldy #0
shift_number:
        lda number,x
        sta number,y
        inx
        iny
        cpx #5
        bcc shift_number
        lda #0
        sta number,y
        jmp converted
convert:
        lda value
        sta _hgr_u_lo
        lda value+1
        sta _hgr_u_hi
        lda #<number
        sta _hgr_u_ptr
        lda #>number
        sta _hgr_u_ptr+1
        jsr _hgr_utoa
converted:
        ldx #0
length:
        lda number,x
        beq counted
        inx
        bne length
counted:
        stx leading
        lda width
        sec
        sbc leading
        bcs fits
        jmp bad
fits:
        sta leading
.if !HUD_SMALL
        jsr _hgr_build_rows
.endif
        jsr field_ptr
        ldy #0
        lda (ptr3),y
        sta remaining
        iny
        lda (ptr3),y
        sta remaining+1
        iny
        lda (ptr3),y
        sta _hgr_g_y
        lda #0
        sta _hgr_g_col
        sta index
        sta changed
        ; Origin /7 once per changed call. No 560-byte column/phase LUTs.
divide7:
        sec
        lda remaining
        sbc #7
        tay
        lda remaining+1
        sbc #0
        bcc divided
        sta remaining+1
        sty remaining
        inc _hgr_g_col
        jmp divide7
divided:
        lda remaining
        sta _hgr_g_bit
cells:
        lda index
        cmp leading
        bcc space
        sec
        sbc leading
        tax
        lda number,x
        jmp selected
space:
        lda #$20
selected:
        sta character
        lda valid
        beq paint
        lda digits_offset
        clc
        adc index
        tay
        lda (ptr3),y
        cmp character
        beq next
paint:
.if !HUD_SMALL
        lda index
        clc
        adc #1
        cmp width
        beq last_cell
        lda #18
        bne internal
last_cell:
        lda #16
internal:
        sta _hgr_hud_cell_width
.endif
        lda character
        jsr cell_run
        jsr field_ptr
        lda digits_offset
        clc
        adc index
        tay
        lda character
        sta (ptr3),y
        inc changed
next:
        inc index
        lda index
        cmp width
        beq done
.if HUD_SMALL
        inc _hgr_g_col
        inc _hgr_g_bit
        lda _hgr_g_bit
        cmp #7
        bcc cells
        lda #0
        sta _hgr_g_bit
        inc _hgr_g_col
.else
        lda _hgr_g_bit
        clc
        adc #4
        cmp #7
        bcc phase
        sbc #7
        inc _hgr_g_col
phase:
        sta _hgr_g_bit
        inc _hgr_g_col
        inc _hgr_g_col
.endif
        jmp cells
done:
        ldy value_offset
        lda value
        sta (ptr3),y
        iny
        lda value+1
        sta (ptr3),y
        ldy #4
        lda (ptr3),y
        ora pagebit
        sta (ptr3),y
        lda changed
        ldx #0
        rts
