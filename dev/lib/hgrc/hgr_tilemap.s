; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_tilemap_init(ctx,map,tiles,count): A/X=count; stack=tiles,map,ctx.
; Validate the borrowed 960-byte map before committing its six-byte context.
.export _hgr_tilemap_init
.import addysp
.importzp sp, ptr1, ptr2, tmp1, tmp2
.code
_hgr_tilemap_init:
        sta tmp1
        stx tmp2
        cpx #2
        bcs reject
        cpx #1
        bne small_count
        cmp #0                 ; 256 is the only valid count with a high byte
        bne reject
        beq pointers
small_count:
        cmp #0
        beq reject
pointers:
        ldy #4
        lda (sp),y
        sta ptr2
        iny
        lda (sp),y
        sta ptr2+1
        ora ptr2
        beq reject
        ldy #2
        lda (sp),y
        sta ptr1
        iny
        lda (sp),y
        sta ptr1+1
        ora ptr1
        beq reject
        ldy #0
        lda (sp),y
        iny
        ora (sp),y
        beq reject
        lda tmp2
        bne commit             ; all byte IDs are valid when count is 256
        ldx #3
        ldy #0
        lda tmp1
        sec
        sbc #1                 ; keep maximum valid ID in A throughout the scan
        jmp page
reject:
        lda #0
finish:
        ldx #0
        ldy #6
        jmp addysp
page:
        cmp (ptr1),y
        bcc reject
        iny
        bne page
        inc ptr1+1             ; keep the original low byte across each 256 IDs
        dex
        bne page
tail:
        cmp (ptr1),y
        bcc reject
        iny
        cpy #192               ; three 256-byte blocks plus 192 = 960
        bne tail
commit:
        ; Read the original pointer from the arguments, not the scan cursor.
        ldy #2
        lda (sp),y
        ldy #0
        sta (ptr2),y
        ldy #3
        lda (sp),y
        ldy #1
        sta (ptr2),y
        ldy #0
        lda (sp),y
        ldy #2
        sta (ptr2),y
        ldy #1
        lda (sp),y
        ldy #3
        sta (ptr2),y
        iny
        lda tmp1
        sta (ptr2),y
        iny
        lda tmp2
        sta (ptr2),y
        lda #1
        jmp finish
