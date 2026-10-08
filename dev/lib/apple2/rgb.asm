; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Extracted from A2FileCmd src/plugins/packfot.s and src/memory_swap.c.
; Le Chat Mauve / Video-7 COL140 latch: 80COL is data, AN3 edges clock it.
; Main-bank code/stack entry. No RAM writes or ZP scratch; clobbers A,X.
; rgb_col140: IIe/c only, arms COL140 + native DHGR, keeps display/page/mixed
; and RAM routing unchanged. Returns A=1 on IIe/c, 0 on II/II+.
; rgb_hgr: full-screen HGR page 1, main routing on IIe/c; safe on II/II+.
; rgb_dhgr: full-screen DHGR page 1, main routing; IIe/c + extended AUX
; required (caller probes RAM first). II/II+ returns 0 without changes.
; Both mode entries return A=1, X=0 on success. Does not clear video RAM.
; Call once at mode entry, not on every flip or full/mixed transition.
.ifndef _RGB_ASM_LOADED_
_RGB_ASM_LOADED_ = 1
.include "apple2.inc"
.code
rgb_col140:
        lda $FBB3
        cmp #$06
        bne @legacy
        sta COL80ON
        sta DHIRES_ON
        sta DHIRES_OFF
        sta DHIRES_ON
        sta DHIRES_OFF
        sta DHIRES_ON
        lda #1
        ldx #0
        rts
@legacy:
        lda #0
        ldx #0
        rts

rgb_hgr:
        jsr rgb_col140
        cmp #0
        beq rgb_arm
        sta DHIRES_OFF
        sta COL80OFF
        jsr rgb_main
        jmp rgb_arm
rgb_dhgr:
        jsr rgb_col140
        cmp #0
        bne @supported
        rts
@supported:
        jsr rgb_main
rgb_arm:
        bit HIRES
        bit LOWSCR
        bit MIXCLR
        bit TXTCLR              ; reveal graphics only after mode is armed
        lda #1
        ldx #0
        rts
rgb_main:
        sta STORE80OFF
        sta RAMRDOFF
        sta RAMWRTOFF
        rts
.endif
