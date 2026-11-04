; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Fill the 960 visible LORES bytes, preserving all 64 firmware mailboxes.
; cc65 fastcall: A = colour (only its low nibble is used).
; hgr_set_draw_page selects base $04/$08; zero defaults to page 1.
; Eight interleaved stores cover offsets 0..119 of every 128-byte region.
.export _hgr_lores_clear
.import _hgr_lo_base
.importzp tmp1

.code
_hgr_lores_clear:
        and #$0f
        sta tmp1
        asl a
        asl a
        asl a
        asl a
        ora tmp1
        ldx _hgr_lo_base
        bne base_ready
        ldx #4
        stx _hgr_lo_base
base_ready:
        cpx #8
        beq page2
        ldy #119
page1_loop:
        sta $0400,y
        sta $0480,y
        sta $0500,y
        sta $0580,y
        sta $0600,y
        sta $0680,y
        sta $0700,y
        sta $0780,y
        dey
        bpl page1_loop
        rts
page2:
        ldy #119
page2_loop:
        sta $0800,y
        sta $0880,y
        sta $0900,y
        sta $0980,y
        sta $0a00,y
        sta $0a80,y
        sta $0b00,y
        sta $0b80,y
        dey
        bpl page2_loop
        rts
