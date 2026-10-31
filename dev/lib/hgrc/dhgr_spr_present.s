; VERHILLE Arnaud — GPL-3.0. DHGR compositor, two pages (DHGR_SPR_DOUBLE):
; dhgr_spr_present shows the page the updates drew on at the next VBL edge,
; then draws on the other one (dhgr.h). The edge comes from
; dev/lib/apple2c/apple2vbl.s: a2_vbl_mode 1 (//e) polls $C019 (the picture,
; then the blank: a fresh edge, the flip ~20 cycles after it), 2 (//c)
; waits for the mouse firmware's VBL interrupt to count a refresh
; (interrupts enabled), 0 calls a2_frame_wait (//e VBL polling or the
; WAIT delay of apple2frame.s, bounded). Each wait is bounded (~45,000
; cycles): a stuck signal flips anyway. a2_vbl_count counts the edge it
; waited for. Main RAM/ZP; A/X/Y destroyed; not from an IRQ.
.export _dhgr_spr_present
.import _a2_vbl_mode, _a2_vbl_count, _a2_vbl_beam, _a2_vbl_scan, _a2_frame_wait
.import _dhgr_base, _dhgr_display
PAGES = 16                      ; bound: 16 x 256 polls of 11 cycles

.code
_dhgr_spr_present:
        lda _a2_vbl_mode
        cmp #1
        beq poll
        cmp #2
        beq irq
        jsr _a2_frame_wait
        jmp flip
poll:   jsr _a2_vbl_scan        ; an edge already there is counted
        ldx #0
        ldy #PAGES
@pic:   bit $C019               ; wait for the picture (bit 7 set) ...
        bmi @blank
        dex
        bne @pic
        dey
        bne @pic
        beq flip                ; (stuck)
@blank: bit $C019               ; ... then for the blank
        bpl @edge
        dex
        bne @blank
        dey
        bne @blank
        beq flip
@edge:  jsr flip
        lda #0
        sta _a2_vbl_beam
        inc _a2_vbl_count
        rts
irq:    lda _a2_vbl_count       ; the handler counts the next refresh
        ldx #0
        ldy #PAGES
@wait:  cmp _a2_vbl_count
        bne flip
        dex
        bne @wait
        dey
        bne @wait
        ; fall through (stuck)
; Show the draw page, draw on the other one.
flip:   lda _dhgr_base
        cmp #$40
        beq @two
        bit $C054
        lda #1
        bne @shown
@two:   bit $C055
        lda #2
@shown: sta _dhgr_display
        lda _dhgr_base
        eor #$60
        sta _dhgr_base
        rts
