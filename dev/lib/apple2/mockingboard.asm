; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Extracted/adapted from A2FileCmd src/mb_probe.s and AY helpers in duet.s.
; Standalone NMOS 6502, main RAM/ZP, ROM visible; no LC switch or AUX access.
; Exclusive ownership of the card's AY chips and VIA1 timer 1 is required.
; mb_detect: scan slots 7..1 except 3; wake //c 4c at $C403, return slot or 0.
; Waking 4c can hide //c slot-4 mouse ROM: detect the card before mouse init.
; Probe reads T1 low (clears its flag); successful probe calls mb_init.
; mb_init: A=slot 1..7 except 3, initialise/reset both AYs; slot or 0 returned.
; mb_write: X=AY register 0..15, A=value, mb_chip=0/1 selects the chip.
; mb_silence: zero all three volumes on BOTH chips, preserves mb_chip.
; mb_timer_start: A=low/X=high of the raw 16-bit T1 reload value.
; mb_tick: nonblocking A=1 once per observed T1 expiry, otherwise 0.
; mb_stop: silence both chips, stop polling and restore saved ACR/T1 IER bit.
; Previous T1 count/latch is not restored. Missed ticks coalesce in VIA IFR.
; All entries clobber A,X,Y; IRQ mask is preserved. Decimal mode must be off.
; mb_write/timer/tick/stop before initialisation are safe no-ops (A=0).
; Non-reentrant; initialise mb_chip before writes. mb_init defaults it to 0.
; mb_ptr (2 ZP bytes) and mb_probe_old (1) can be individually aliased.
.ifndef _MOCKINGBOARD_ASM_LOADED_
_MOCKINGBOARD_ASM_LOADED_ = 1
.zeropage
.ifndef mb_ptr
mb_ptr: .res 2
.endif
.ifndef mb_probe_old
mb_probe_old: .res 1
.endif
.code
; Resident initialised state also makes an absent-card path deterministic.
mb_slot: .byte 0
mb_chip: .byte 0
mb_timer_active: .byte 0
.bss
mb_old_acr: .res 1
mb_old_ier: .res 1
mb_period: .res 2
.code
mb_detect:
        php
        sei
        jsr mb_stop             ; release any previous timer before rescanning
        lda $FBB3
        cmp #$06
        bne @scan
        lda $FBC0
        bne @scan
        sta $C403               ; //c only: wake 4c with DDRA inputs
@scan:  ldx #7
@slot:  cpx #3
        beq @next
        txa
        ora #$C0
        sta mb_ptr+1
        lda #0
        sta mb_ptr
        jsr mb_t1_probe
        bne @next
        jsr mb_t1_probe
        bne @next
        txa
        jsr mb_init
        plp
        rts
@next:  dex
        bne @slot
        stx mb_slot
        txa
        plp
        rts
mb_t1_probe:
        ldy #4
        lda (mb_ptr),y
        sta mb_probe_old
        lda (mb_ptr),y
        sec
        sbc mb_probe_old
        cmp #$F8                ; VIA clock drops eight cycles between reads
        rts

mb_init:
        cmp #1
        bcc @invalid
        cmp #8
        bcs @invalid
        cmp #3
        beq @invalid
        pha
        jsr mb_stop             ; retain the old VIA's restoration snapshot
        pla
        sta mb_slot
        lda #0
        sta mb_chip
        sta mb_timer_active
        php
        sei
        jsr mb_via1
        jsr mb_reset_ay
        lda #$80
        sta mb_ptr
        jsr mb_reset_ay
        plp
        lda mb_slot
        ldx #0
        rts
@invalid:
        lda #0
        ldx #0
        rts
mb_reset_ay:
        lda #$FF
        ldy #3                  ; DDRA, DDRB: AY data/control output
        sta (mb_ptr),y
        dey
        sta (mb_ptr),y
        ldy #0
        lda #0                  ; AY reset, then inactive
        sta (mb_ptr),y
        lda #4
        sta (mb_ptr),y
        rts
mb_via1:
        lda #0
        sta mb_ptr
        lda mb_slot
        ora #$C0
        sta mb_ptr+1
        rts
mb_write:
        cpx #16
        bcs mb_noop
        ldy mb_slot
        beq mb_noop
        php
        sei
        pha
        jsr mb_via1
        lda mb_chip
        and #1
        beq @first
        lda #$80
        sta mb_ptr
@first: txa
        ldy #1
        sta (mb_ptr),y          ; register address
        dey
        lda #7
        sta (mb_ptr),y          ; latch address
        lda #4
        sta (mb_ptr),y
        pla
        iny
        sta (mb_ptr),y          ; register value
        dey
        lda #6
        sta (mb_ptr),y          ; write data
        lda #4
        sta (mb_ptr),y
        plp
        rts
mb_noop:
        lda #0
        ldx #0
        rts
mb_silence:
        lda mb_slot
        beq mb_noop
        lda mb_chip
        pha
        lda #0
        sta mb_chip
        jsr mb_quiet_chip
        inc mb_chip
        jsr mb_quiet_chip
        pla
        sta mb_chip
        rts
mb_quiet_chip:
        ldx #8
@volume:
        lda #0
        jsr mb_write
        inx
        cpx #11
        bcc @volume
        rts
mb_timer_start:
        ldy mb_slot
        beq mb_noop
        sta mb_period
        stx mb_period+1
        php
        sei
        jsr mb_via1
        lda mb_timer_active
        bne @configure
        ldy #$0B
        lda (mb_ptr),y
        sta mb_old_acr
        ldy #$0E
        lda (mb_ptr),y
        sta mb_old_ier
@configure:
        ldy #$0B
        lda mb_old_acr
        ora #$40                ; T1 free-running
        sta (mb_ptr),y
        ldy #$0E
        lda #$40                ; mask T1 only; retain other VIA IRQ enables
        sta (mb_ptr),y
        ldy #4
        lda mb_period
        sta (mb_ptr),y
        iny
        lda mb_period+1
        sta (mb_ptr),y
        lda #1
        sta mb_timer_active
        plp
        rts
mb_tick:
        lda mb_timer_active
        beq mb_noop
        php
        sei
        jsr mb_via1
        ldy #$0D
        lda (mb_ptr),y
        and #$40
        beq @done
        ldy #4                  ; acknowledge observed expiry
        lda (mb_ptr),y
        lda #1
@done:  plp
        ldx #0
        rts
mb_stop:
        jsr mb_silence
        lda mb_timer_active
        bne @active
        jmp mb_noop
@active:
        php
        sei
        jsr mb_via1
        ldy #$0E
        lda #$40
        sta (mb_ptr),y
        ldy #4
        lda (mb_ptr),y
        ldy #$0B
        lda mb_old_acr
        sta (mb_ptr),y
        ldy #$0E
        lda mb_old_ier
        and #$40
        ora #$80
        sta (mb_ptr),y
        lda #0
        sta mb_timer_active
        plp
        ldx #0
        rts
.endif
