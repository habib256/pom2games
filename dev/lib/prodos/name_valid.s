; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Fastcall AX points to a NUL-terminated name. The first byte must be A..Z;
; later bytes may also be 0..9 or '.'. At most 15 characters; byte 16 is
; never read. No persistent state or directory/MLI dependencies.
; An including overlay may select its segment and set CUSTOM_SEGMENT.
.export _prodos_name_valid
.importzp ptr1
.ifndef PRODOS_NAME_CUSTOM_SEGMENT
.code
.endif
_prodos_name_valid:
        sta ptr1
        stx ptr1+1
        ldy #0
        lda (ptr1),y
        sec
        sbc #'A'
        cmp #26
        bcs invalid
next:
        iny
        lda (ptr1),y
        beq valid
        cpy #15
        beq invalid
        cmp #'.'
        beq next
        sec
        sbc #'0'
        cmp #10
        bcc next
        sbc #'A'-'0'            ; CMP left carry set: subtract the remaining gap
        cmp #26
        bcc next
invalid:
        lda #0
        tax
        rts
valid:
        lda #1
        ldx #0
        rts
