; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; ezcolor.asm -- E-Z Color Graphics Interface (TMS9918A): detection + access
; ============================================================================
; Standalone NMOS 6502, main RAM/ZP, ROM visible. Include ezcolor.inc at the
; top and this file LAST (after dev/lib/tms9918/*.asm, which call these
; helpers): every routine is .ifref-guarded, so only what the source above
; references assembles. Not reentrant; not for an IRQ handler (see IRQ).
;
; ez_detect -- find the card. Scans slots 7,5,4,2,1,6 (then 3 with
;   EZ_DETECT_SKIP3 = 0), skipping the boot slot (EZ_DETECT_BOOT_SLOT).
;   Out: A = slot 1..7 and Z = 0, or A = 0 and Z = 1. Stores ez_slot and
;   ez_slotx (slot*16), patches the helpers' absolute operands to $C0n0 /
;   $C0n1. Clobbers A, X, Y; the IRQ mask is preserved (SEI inside).
;   Probe on a slot (helpers patched to it): status read, read address $3FFC, 4 reads (saved), write
;   address $3FFC, write $A5 $5A $3C $C3, read address $3FFC, 4 reads that
;   must match; then the saved bytes are written back (VRAM unchanged). Every
;   access is 18+ cycles from the previous one. A slot without a VDP returns
;   other bytes (an empty slot the floating bus, a latch its last value).
;   Per slot (see README.md "E-Z Color (TMS9918A) card" for the reasoning):
;   - Disk II: $C0n0/$C0n1 are phase 0 off/on. The probe toggles phase 0 and
;     always ends on a $C0n0 access (phase 0 off). The boot slot is skipped
;     (EZ_DETECT_BOOT_SLOT); another drive with its motor off has its stepper
;     unpowered. Do not probe within ~1 s of a disk access to that drive.
;   - Mouse card (6821 PIA at $C0n0-$C0n3), Videx-type 80-column cards
;     (CRTC at $C0n0/$C0n1), clocks with registers there: the probe writes
;     them. Detect BEFORE initialising such cards, or exclude their slot with
;     EZ_DETECT_ORDER. Slot 3 is skipped by default for that reason.
;   - Mockingboard, ROM-only cards, empty slots: $C0nX ignored, safe.
;   - //c: no slots; do not call ez_detect there ($FBC0 = 0).
;
; Access helpers (after ez_detect; before it, or after a failed one, their
; operands point at $C070/$C071, the harmless paddle trigger):
;   ez_data_w   A -> data port, then pad: 22 cycles store to store when
;               chained (JSR+STA+3 NOP+RTS). A/X/Y and flags preserved.
;   ez_data_r   data port -> A (N/Z set), same pad. X/Y preserved.
;   ez_ctrl_w   A -> register port, same pad. A/X/Y and flags preserved.
;   ez_status   status -> A (N = F frame flag), clears F/5S/C. No pad.
;   ez_status_bit  BIT status: N = F, V = 5S; A/X/Y preserved. No pad.
;   ez_set_reg  A = value, X = register 0..7. Clobbers A.
;   ez_vram_addr_w / ez_vram_addr_r  A = address low, X = high (0..$3F):
;               sets the write / read address (read prefetches). Clobbers A.
;   ez_fill     A = byte, ez_count (ZP, 16-bit, 0..$8000) bytes at the
;               current write address, padded: 27 cycles a byte. A kept,
;               X/Y clobbered. ez_fill_blank: unpadded, 9 cycles a byte,
;               display blanked or vertical blanking only.
;   ez_copy     ez_count bytes from (ez_ptr) to the current write address,
;               padded (32 cycles a byte). ez_ptr+1 advances by count/256.
;               ez_copy_blank: unpadded (14 cycles a byte), display blanked.
;   ez_read     ez_count bytes from the current read address to (ez_ptr),
;               padded; ez_ptr+1 advances by count/256.
;   ez_pad18    JSR ez_pad18 = 18 cycles, registers and flags preserved
;               (byte-identical to POM1's tms9918_pad18).
;
; Options (define before this include):
;   EZ_ZP = 1             ez_slot / ez_slotx in zero page (default BSS).
;   EZ_DETECT_SKIP3 = 0   also probe slot 3, last (default 1: skipped).
;   EZ_DETECT_ORDER       address of your own zero-terminated slot list
;                         (replaces the default order; SKIP3 ignored).
;   EZ_DETECT_BOOT_SLOT   address of a byte whose bits 4-6 hold the slot
;                         to skip: $B7E9 (DOS 3.3 IOB slot*16) or $BF30
;                         (ProDOS DEVNUM, DSSS0000).
;   EZ_PAIR_SEI = 1       ez_set_reg / ez_vram_addr_* mask IRQs around the
;                         two control bytes (for programs whose IRQ handler
;                         reads the status: it resets the byte flip-flop).
; ZP: ez_ptr (2), ez_count (2); each can be aliased (define it first).
;
; IRQ: the VDP's /INT drives the slot IRQ when R1 bit 5 is set. A handler
; must read the status ($C0n1, ez_status) to drop /INT; that read also
; resets the control-port flip-flop, so a main-line control pair it splits
; decodes wrong: keep IRQ off (poll EZ_WAIT_VBLANK) or use EZ_PAIR_SEI = 1.
; ============================================================================

.ifndef _EZCOLOR_ASM_LOADED_
_EZCOLOR_ASM_LOADED_ = 1

.include "ezcolor.inc"

.ifndef EZ_DETECT_SKIP3
EZ_DETECT_SKIP3 = 1
.endif
.ifndef EZ_PAIR_SEI
EZ_PAIR_SEI = 0
.endif

; ez_ptr, ez_count, ez_slot, ez_slotx: reserved by ezcolor.inc.

; Patched sites: each records the address of its operand's low byte. This
; file uses no @cheap locals (a symbol assignment would end their scope).
EZ_NSITES_D .set 0
EZ_NSITES_C .set 0
.macro EZ_SITE_D op
        .ident(.sprintf("ez_site_d%d", EZ_NSITES_D)) = * + 1
EZ_NSITES_D .set EZ_NSITES_D + 1
        op      $C070
.endmacro
.macro EZ_SITE_C op
        .ident(.sprintf("ez_site_c%d", EZ_NSITES_C)) = * + 1
EZ_NSITES_C .set EZ_NSITES_C + 1
        op      $C071
.endmacro

.code

; ----------------------------------------------------------------------------
.ifref ez_detect
.bss
ezd_index: .res 1
ezd_save:  .res 4
.code
ez_detect:
        php
        sei
        lda     #0
        sta     ezd_index
ezd_next:
        ldy     ezd_index
        inc     ezd_index
.ifdef EZ_DETECT_ORDER
        lda     EZ_DETECT_ORDER,y
.else
        lda     ezd_order,y
.endif
        beq     ezd_none
        asl
        asl
        asl
        asl
        sta     ez_slotx        ; candidate slot*16
.ifdef EZ_DETECT_BOOT_SLOT
        lda     EZ_DETECT_BOOT_SLOT
        and     #$70
        cmp     ez_slotx
        beq     ezd_next        ; the boot drive's controller: never touched
.endif
        jsr     ez_patch        ; helpers -> this slot's $C0n0 / $C0n1
        jsr     ezd_probe
        bcc     ezd_next
        lda     ez_slotx
        lsr
        lsr
        lsr
        lsr
        bne     ezd_found       ; always
ezd_none:
        lda     #0
        sta     ez_slotx
        jsr     ez_patch        ; back to the harmless $C070 / $C071
        lda     #0
ezd_found:
        sta     ez_slot
        plp
        lda     ez_slot         ; Z = 1 when no card
        rts

; Probe the patched slot through the helpers (absolute stores: an indexed
; STA would first do a dummy read of the port, see README). Every access is
; 18+ cycles after the previous one. C = 1 when a VDP answered.
ezd_probe:
        jsr     ez_status       ; resets the control flip-flop
        lda     #$3F            ; read address $3FFC: save 4 bytes
        jsr     ezd_addr
        ldy     #0
ezd_save_l:
        jsr     ez_data_r
        sta     ezd_save,y
        iny
        cpy     #4
        bne     ezd_save_l
        lda     #$7F            ; write address $3FFC: the pattern
        jsr     ezd_addr
        ldy     #0
ezd_pat_l:
        lda     ezd_pattern,y
        jsr     ez_data_w
        iny
        cpy     #4
        bne     ezd_pat_l
        lda     #$3F            ; read it back
        jsr     ezd_addr
        ldy     #0
ezd_cmp_l:
        jsr     ez_data_r       ; last access on a failure: $C0n0 (a Disk
        cmp     ezd_pattern,y   ; II's phase 0 is left off)
        bne     ezd_absent
        iny
        cpy     #4
        bne     ezd_cmp_l
        lda     #$7F            ; restore the 4 bytes, ending on $C0n0
        jsr     ezd_addr
        ldy     #0
ezd_rest_l:
        lda     ezd_save,y
        jsr     ez_data_w
        iny
        cpy     #4
        bne     ezd_rest_l
        sec
        rts
ezd_absent:
        clc
        rts

; Control pair: low byte $FC, then A (high byte + command bits).
ezd_addr:
        pha
        lda     #$FC
        jsr     ez_ctrl_w
        pla
        jmp     ez_ctrl_w

ezd_pattern:
        .byte   $A5, $5A, $3C, $C3
.ifndef EZ_DETECT_ORDER
ezd_order:
        .byte   7, 5, 4, 2, 1, 6
.if !EZ_DETECT_SKIP3
        .byte   3
.endif
        .byte   0
.endif
.endif

; ----------------------------------------------------------------------------
; Composite helpers first: their references pull in the primitives below.
.ifref ez_set_reg
ez_set_reg:
.if EZ_PAIR_SEI
        php
        sei
.endif
        jsr     ez_ctrl_w       ; value
        txa
        ora     #$80            ; command: register X
        jsr     ez_ctrl_w
.if EZ_PAIR_SEI
        plp
.endif
        rts
.endif

.ifref ez_vram_addr_w
ez_vram_addr_w:
.if EZ_PAIR_SEI
        php
        sei
.endif
        jsr     ez_ctrl_w       ; address low
        txa
        and     #$3F
        ora     #$40            ; command: write address
        jsr     ez_ctrl_w
.if EZ_PAIR_SEI
        plp
.endif
        rts
.endif

.ifref ez_vram_addr_r
ez_vram_addr_r:
.if EZ_PAIR_SEI
        php
        sei
.endif
        jsr     ez_ctrl_w       ; address low
        txa
        and     #$3F            ; command: read address (prefetches)
        jsr     ez_ctrl_w
.if EZ_PAIR_SEI
        plp
.endif
        rts
.endif

.ifref ez_fill
ez_fill:
        ldx     ez_count+1
        ldy     ez_count
        beq     ezf_page
ezf_loop:
        EZ_SITE_D sta
        jsr     ez_pad18        ; 4+18+2+3 = 27 cycles a byte
        dey
        bne     ezf_loop
ezf_page:
        dex
        bpl     ezf_loop        ; X full pages of 256 (Y = 0)
        rts
.endif

.ifref ez_fill_blank
ez_fill_blank:
        ldx     ez_count+1
        ldy     ez_count
        beq     ezfb_page
ezfb_loop:
        EZ_SITE_D sta           ; 9 cycles a byte: display blanked only
        dey
        bne     ezfb_loop
ezfb_page:
        dex
        bpl     ezfb_loop
        rts
.endif

.ifref ez_copy
ez_copy:
        ldy     #0
        ldx     ez_count+1
        beq     ezc_rest
ezc_page:
        lda     (ez_ptr),y
        EZ_SITE_D sta
        jsr     ez_pad18        ; 5+4+18+2+3 = 32 cycles a byte
        iny
        bne     ezc_page
        inc     ez_ptr+1
        dex
        bne     ezc_page
ezc_rest:
        ldx     ez_count
        beq     ezc_done
ezc_tail:
        lda     (ez_ptr),y
        EZ_SITE_D sta
        jsr     ez_pad18
        iny
        dex
        bne     ezc_tail
ezc_done:
        rts
.endif

.ifref ez_copy_blank
ez_copy_blank:
        ldy     #0
        ldx     ez_count+1
        beq     ezcb_rest
ezcb_page:
        lda     (ez_ptr),y
        EZ_SITE_D sta           ; 14 cycles a byte: display blanked only
        iny
        bne     ezcb_page
        inc     ez_ptr+1
        dex
        bne     ezcb_page
ezcb_rest:
        ldx     ez_count
        beq     ezcb_done
ezcb_tail:
        lda     (ez_ptr),y
        EZ_SITE_D sta
        iny
        dex
        bne     ezcb_tail
ezcb_done:
        rts
.endif

.ifref ez_read
ez_read:
        ldy     #0
        ldx     ez_count+1
        beq     ezr_rest
ezr_page:
        EZ_SITE_D lda
        sta     (ez_ptr),y
        jsr     ez_pad18
        iny
        bne     ezr_page
        inc     ez_ptr+1
        dex
        bne     ezr_page
ezr_rest:
        ldx     ez_count
        beq     ezr_done
ezr_tail:
        EZ_SITE_D lda
        sta     (ez_ptr),y
        jsr     ez_pad18
        iny
        dex
        bne     ezr_tail
ezr_done:
        rts
.endif

; ----------------------------------------------------------------------------
; Primitives. The NOP filler keeps registers and flags (callers branch on a
; compare across them, as with POM1's pad).
.ifref ez_data_w
ez_data_w:
        EZ_SITE_D sta
        nop
        nop
        nop
        rts
.endif

.ifref ez_data_r
ez_data_r:
        EZ_SITE_D lda
        nop
        nop
        nop
        rts
.endif

.ifref ez_ctrl_w
ez_ctrl_w:
        EZ_SITE_C sta
        nop
        nop
        nop
        rts
.endif

.ifref ez_status
ez_status:
        EZ_SITE_C lda
        rts
.endif

.ifref ez_status_bit
ez_status_bit:
        EZ_SITE_C bit
        rts
.endif

.ifref ez_pad18
ez_pad18:                       ; JSR 6 + 3 NOP + RTS 6 = 18 cycles
        nop
        nop
        nop
        rts
.endif

; ----------------------------------------------------------------------------
; Every site's operand low byte: $80 + slot*16 (+1 for the register port),
; or $70/$71 (paddle trigger, harmless) when no card was found.
.ifref ez_patch
ez_patch:
        lda     ez_slotx
        beq     ezp_none
        ora     #$80
        bne     ezp_set         ; always
ezp_none:
        lda     #$70
ezp_set:
.repeat EZ_NSITES_D, I
        sta     .ident(.sprintf("ez_site_d%d", I))
.endrepeat
        ora     #$01
.repeat EZ_NSITES_C, I
        sta     .ident(.sprintf("ez_site_c%d", I))
.endrepeat
        rts
.endif

.endif  ; _EZCOLOR_ASM_LOADED_
