; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; aysong.asm — the AYS song player (format: AYSONG_FORMAT.md; reference
; model and encoder: dev/tools/audio/aysong.py, whose Player.tick() gives
; the same registers tick for tick: dev/tests/test_aysong.py).
;
; NMOS 6502 by default (II+ and up); AYSONG_CPU65C02 = 1 assembles a few
; 65C02 forms instead (stz). Include AFTER the callers (.ifref: only what is
; referenced is assembled; ays_tick pulls in the row reader). With
; mb_irq.asm, include mb_irq.asm first: the player then writes through its
; shadows (ays_out = mb_shadow: mb_hush / mb_forget make it write again).
;
;   ays_init     A/Y = song address (low/high): reads the header, voices
;                silent, registers reset (R7 = $3F, R13 = $FF, the rest 0),
;                instrument 1 on every voice, mute mask 0, plays from order
;                0 row 0 (the first ays_tick reads row 0). Call it with the
;                interrupt tick off (before mb_irq_start) or under SEI.
;   ays_tick     one tick (50 Hz: MB_IRQ_TICK = ays_tick, or once a frame):
;                the row when due, every voice's effect and instrument macro,
;                the frame in ays_regs (chip 1 registers 0..13, chip 2 at
;                +16), then the registers that differ from ays_out written
;                (R13 whenever it is not $FF) through AYSONG_WRITE.
;   ays_stop     every voice off, no more rows (ays_tick then writes silence).
;   ays_mute     A = mask, bit v = voice v silent (volume 0; it keeps playing).
;   ays_pos      A = order index, X = row of the next row to be read.
;   ays_set_pos  A = order index, X = row: voices off until their next note,
;                the rows before X skipped (instrument prefixes kept), the
;                next ays_tick reads row X (X < rows). Also restarts after
;                ays_stop. Masks interrupts while it works.
; All clobber A/X/Y; decimal mode off; not reentrant (one song at a time).
;
; Options (before the include; ABI.md "Speed/RAM options"):
;   AYSONG_VOICES = 3 | 6   voices the player handles (default 3: one
;                           chip; 6: both). A 6-voice song under a 3-voice
;                           player plays its first chip only.
;   AYSONG_CPU65C02 = 1     65C02 forms (4 B smaller); default 0: NMOS.
;   AYSONG_FAST_PERIODS = 1 a 96-note period table (192 B) instead of the
;                           12-note table + octave shifts with a per-voice
;                           cache (3 B a voice): +112 B, ~230 cycles less on
;                           a row of three new notes, ~25 a tick on average.
;   AYSONG_WRITE            a macro: X = register 0..13, A = value, Y = chip
;                           (0/1); it may clobber A/Y, must keep X (the
;                           player saves nothing). Default: sty mb_chip /
;                           jsr mb_write (mockingboard.asm) with X saved.
;
; Storage: zero page ays_zp (5 bytes: a pointer and 3 scratch; define it
; first to place them); BSS: ays_regs (16 a chip), ays_out (16 a chip,
; = mb_shadow if mb_irq.asm came first, or define it), 19 bytes a voice
; (16 with AYSONG_FAST_PERIODS), 22 bytes of song state.
; Measured (dev/tests/test_aysong.py): 1,091 B of code and tables for 3
; voices (1,169 for 6); a tick ~950 cycles + ~90 a register written (mean
; ~1,320 on the demo), up to ~3,600 on a row of three notes and a pattern
; change.
.ifndef _AYSONG_DEFS_
_AYSONG_DEFS_ = 1
.ifndef AYSONG_VOICES
AYSONG_VOICES = 3
.endif
.ifndef AYSONG_CPU65C02
AYSONG_CPU65C02 = 0
.endif
.ifndef AYSONG_FAST_PERIODS
AYSONG_FAST_PERIODS = 0
.endif
AYS_CHIPS = AYSONG_VOICES / 3
.assert AYSONG_VOICES = 3 .or AYSONG_VOICES = 6, error, "AYSONG_VOICES: 3 or 6"
.if AYSONG_CPU65C02
.ifndef CPU_ISET_65C02
.macpack cpu
.endif
.assert .cpu .bitand ::CPU_ISET_65C02, error, "AYSONG_CPU65C02: assemble for the 65C02"
.endif
.macro AYS_STZ addr
.if AYSONG_CPU65C02
        stz addr
.else
        lda #0
        sta addr
.endif
.endmacro
.if .not .definedmacro(AYSONG_WRITE)
.macro AYSONG_WRITE
        sty mb_chip
        stx ays_wx
        jsr mb_write
        ldx ays_wx
.endmacro
.endif
.pushseg
.zeropage
.ifndef ays_zp
ays_zp:     .res 5
.endif
ays_t   = ays_zp+2              ; scratch
ays_ib  = ays_zp+3              ; the voice's instrument tick byte (0: off)
ays_arp = ays_zp+4              ; its arpeggio offset
.bss
ays_regs:   .res 16 * AYS_CHIPS
.ifndef ays_out
.ifdef mb_shadow
ays_out = mb_shadow
.else
ays_out:    .res 16 * AYS_CHIPS
.endif
.endif
; song state
ays_base:   .res 2
ays_ord:    .res 2              ; the order list
ays_pat:    .res 2              ; the pattern table
ays_ins:    .res 2              ; the instrument table - 2 (instrument 1 first)
ays_nv:     .res 1              ; voices played
ays_rows:   .res 1
ays_speed:  .res 1
ays_rate:   .res 1              ; (header byte 7, not used by the player)
ays_nord:   .res 1
ays_loop:   .res 1
ays_order:  .res 1
ays_row:    .res 1
ays_count:  .res 1
ays_play:   .res 1
ays_mutem:  .res 1
ays_skip:   .res 1              ; bit 7: rows skipped, not played
ays_goto:   .res 1              ; ays_set_pos: the row
ays_wx:     .res 1
; voice state, one byte a voice in each
ays_vpl:    .res AYSONG_VOICES  ; track pointer
ays_vph:    .res AYSONG_VOICES
ays_vwait:  .res AYSONG_VOICES  ; empty rows still to count
ays_vins:   .res AYSONG_VOICES  ; instrument of the next note
ays_von:    .res AYSONG_VOICES  ; bit 7 on, bit 6 a note started this row
ays_vnote:  .res AYSONG_VOICES
ays_vibl:   .res AYSONG_VOICES  ; instrument block
ays_vibh:   .res AYSONG_VOICES
ays_vipos:  .res AYSONG_VOICES  ; offset in its tick data
ays_vfx:    .res AYSONG_VOICES
ays_vpar:   .res AYSONG_VOICES
ays_vcnt:   .res AYSONG_VOICES
ays_vsll:   .res AYSONG_VOICES  ; slide (period offset)
ays_vslh:   .res AYSONG_VOICES
ays_vvoff:  .res AYSONG_VOICES  ; volume offset -15..15
.if .not AYSONG_FAST_PERIODS
ays_vpn:    .res AYSONG_VOICES  ; note of the cached period ($FF: none)
ays_vpbl:   .res AYSONG_VOICES  ; its period
ays_vpbh:   .res AYSONG_VOICES
.endif
ays_vmix:   .res AYSONG_VOICES  ; its mixer bits (tone off 1, noise off 8)
.popseg
.endif

.if (.referenced(ays_init) .or .referenced(ays_tick) .or .referenced(ays_set_pos)) .and (.not .defined(ays_init))
ays_init:
        sta ays_base
        sty ays_base+1
        sta ays_zp
        sty ays_zp+1
        ldy #4
        lda (ays_zp),y           ; voices
.if AYSONG_VOICES = 3
        cmp #4
        bcc :+
        lda #3
:
.endif
        sta ays_nv
        ldx #0
:       iny                      ; rows, speed, rate, order length, loop
        lda (ays_zp),y
        sta ays_rows,x
        inx
        cpx #5
        bcc :-
        ldy #12                  ; the three tables, absolute
        ldx #0
:       jsr ays_word
        sta ays_ord+1,x
        lda ays_t
        sta ays_ord,x
        inx
        inx
        cpx #6
        bcc :-
        lda ays_ins              ; instrument n at table + 2n - 2
        sec
        sbc #2
        sta ays_ins
        bcs :+
        dec ays_ins+1
:       lda #0                   ; the registers
        ldx #16 * AYS_CHIPS - 1
:       sta ays_regs,x
        dex
        bpl :-
        sta ays_mutem
        lda #$FF                 ; nothing written yet: every register out
        ldx #16 * AYS_CHIPS - 1
:       sta ays_out,x
        dex
        bpl :-
        lda #$3F
        sta ays_regs+7
.if AYS_CHIPS = 2
        sta ays_regs+16+7
.endif
        ldx #AYSONG_VOICES - 1
:       lda #1
        sta ays_vins,x
.if .not AYSONG_FAST_PERIODS
        lda #$FF
        sta ays_vpn,x
.endif
        dex
        bpl :-
        lda #0
        tax
ays_set_pos:
        php                      ; (an interrupt tick must not see it half
        sei                      ; done)
        sta ays_order
        stx ays_goto
        jsr ays_stop
        jsr ays_pattern
        sta ays_row              ; (A = 0)
        lda #$80
        sta ays_skip
@skip:  lda ays_row
        cmp ays_goto
        bcs @go
        jsr ays_read_row
        inc ays_row
        bne @skip
@go:    lda #1
        sta ays_count
        sta ays_play
        plp
        rts

; Y = offset in (ays_zp): the word there + ays_base -> ays_t (low), A
; (high); Y += 2.
ays_word:
        lda (ays_zp),y
        clc
        adc ays_base
        sta ays_t
        iny
        lda (ays_zp),y
        adc ays_base+1
        iny
        rts

; The pattern of order entry ays_order: every voice's track, no wait.
; Returns A = 0.
ays_pattern:
        lda ays_ord
        sta ays_zp
        lda ays_ord+1
        sta ays_zp+1
        ldy ays_order
        lda (ays_zp),y           ; the pattern number
        asl a
        tay
        lda ays_pat
        sta ays_zp
        lda ays_pat+1
        adc #0                   ; (the pattern number's bit 7)
        sta ays_zp+1
        jsr ays_word             ; its block
        sta ays_zp+1
        lda ays_t
        sta ays_zp
        ldy #0
        ldx #0
:       jsr ays_word
        sta ays_vph,x
        lda ays_t
        sta ays_vpl,x
        lda #0
        sta ays_vwait,x
        inx
        cpx ays_nv
        bcc :-
        rts

; One row of every voice (ays_skip bit 7: instrument prefixes only).
ays_read_row:
        ldx #0
@voice: lda ays_von,x            ; no note started yet
        and #$80
        sta ays_von,x
        lda ays_vwait,x
        beq @read
        dec ays_vwait,x
        jmp @next
@read:  lda ays_vpl,x
        sta ays_zp
        lda ays_vph,x
        sta ays_zp+1
        ldy #0
        sty ays_t                ; no effect on this row yet
@byte:  lda (ays_zp),y
        iny
        cmp #$80
        bcc @low
        and #$7F                 ; empty rows
        sta ays_vwait,x
        bpl @end
@low:   cmp #$60
        bcs @prefix
        bit ays_skip             ; a note
        bmi @end
        sta ays_vnote,x
        lda ays_t
        bne :+
        sta ays_vfx,x            ; no effect of its own: none
:       lda #4                   ; its instrument from the first tick
        sta ays_vipos,x
        lda #$C0
        sta ays_von,x
        lda #0
        sta ays_vsll,x
        sta ays_vslh,x
        sta ays_vvoff,x
        beq @end
@prefix:
        beq @off
        cmp #$70
        bcs @fx
        and #$0F                 ; instrument
        sta ays_vins,x
        bpl @byte
@off:   lda #0
        sta ays_von,x
        beq @end
@fx:    and #$0F
        pha
        beq :+
        lda (ays_zp),y           ; its parameter
        iny
:       bit ays_skip
        bmi :+
        sta ays_vpar,x
        pla
        sta ays_vfx,x
        lda #0
        sta ays_vcnt,x
        inc ays_t
        bne @byte
:       pla
        jmp @byte
@end:   tya                      ; the track goes on there
        clc
        adc ays_zp
        sta ays_vpl,x
        lda ays_zp+1
        adc #0
        sta ays_vph,x
        lda ays_von,x            ; a note: its instrument's block
        and #$40
        beq @next
        lda ays_ins
        sta ays_zp
        lda ays_ins+1
        sta ays_zp+1
        lda ays_vins,x
        asl a
        tay
        jsr ays_word
        sta ays_vibh,x
        lda ays_t
        sta ays_vibl,x
@next:  inx
        cpx ays_nv
        bcs :+
        jmp @voice
:       rts
.endif

.if (.referenced(ays_stop) .or .defined(ays_set_pos)) .and (.not .defined(ays_stop))
ays_stop:
        lda #0
        sta ays_play
        ldx #AYSONG_VOICES - 1
:       sta ays_von,x
        dex
        bpl :-
        rts
.endif

.if .referenced(ays_mute) .and (.not .defined(ays_mute))
ays_mute:
        sta ays_mutem
        rts
.endif

.if .referenced(ays_pos) .and (.not .defined(ays_pos))
ays_pos:
        lda ays_order
        ldx ays_row
        rts
.endif

.if .referenced(ays_tick) .and (.not .defined(ays_tick))
ays_tick:
        lda #$FF
        sta ays_regs+13
.if AYS_CHIPS = 2
        sta ays_regs+16+13
.endif
        lda ays_play             ; 1. the row, when due
        beq @voices
        dec ays_count
        bne @voices
        lda ays_speed
        sta ays_count
        lda ays_row
        cmp ays_rows
        bne @read
        lda #0                   ; the next order entry
        sta ays_row
        inc ays_order
        lda ays_order
        cmp ays_nord
        bne @load
        lda ays_loop
        sta ays_order
        cmp #$FF
        bne @load
        AYS_STZ ays_order        ; the end: silence
        jsr ays_stop
        jmp @voices
@load:  jsr ays_pattern
@read:  AYS_STZ ays_skip
        jsr ays_read_row
        inc ays_row
@voices:                         ; 2. every voice
        ldx #0
@voice: lda #0
        sta ays_arp
        ldy ays_von,x
        bmi @on
        sta ays_ib               ; off: volume 0, tone and noise off
        jmp @vol
@on:    ldy ays_vfx,x            ; its effect
        bne :+
        jmp @ins
:       lda ays_vpar,x
        dey
        bne @f2
        ldy ays_vcnt,x           ; 1 arpeggio: 0, x, y
        beq @a0
        dey
        bne @alo
        lsr a
        lsr a
        lsr a
        lsr a
        ldy #1
        bne @aset
@alo:   and #$0F
        ldy #$FF                 ; (step 2 -> 0)
@aset:  sta ays_arp
@a0:    iny
        tya
        sta ays_vcnt,x
        jmp @ins
@f2:    dey
        bne @f3
        eor #$FF                 ; 2 slide up: - p
        sec
        adc ays_vsll,x
        sta ays_vsll,x
        lda ays_vslh,x
        adc #$FF
        sta ays_vslh,x
        jmp @ins
@f3:    dey
        bne @f4
        clc                      ; 3 slide down: + p
        adc ays_vsll,x
        sta ays_vsll,x
        bcc @ins
        inc ays_vslh,x
        bcs @ins
@f4:    dey                      ; (Y: 0 fade, 1 swell, 2 noise, 3 env)
        cpy #2
        bcs @f6
        inc ays_vcnt,x           ; 4 fade / 5 swell: a step every p ticks
        cmp ays_vcnt,x
        beq :+
        bcs @ins
:       lda #0
        sta ays_vcnt,x
        lda ays_vvoff,x
        dey
        beq @f5
        cmp #$F1                 ; fade: down to -15
        beq @ins
        dec ays_vvoff,x
        jmp @ins
@f5:    cmp #15                  ; swell: up to +15
        beq @ins
        inc ays_vvoff,x
        jmp @ins
@f6:    cpy #3
        ldy ays_tr,x
        bcs @f7
        and #31                  ; 6 noise period
        sta ays_regs+6,y
        bcc @ins
@f7:    sta ays_regs+12,y        ; 7 envelope period
        lda #0
        sta ays_regs+11,y
@ins:   lda ays_vibl,x           ; its instrument tick
        sta ays_zp
        lda ays_vibh,x
        sta ays_zp+1
        ldy ays_vipos,x
        lda (ays_zp),y
        sta ays_ib
        bpl :+
        iny
        lda (ays_zp),y           ; the chip's noise period
        and #31
        sty ays_t
        ldy ays_tr,x
        sta ays_regs+6,y
        ldy ays_t
:       iny
        tya
        ldy #0
        cmp (ays_zp),y           ; at its end: the loop offset
        bcc :+
        iny
        lda (ays_zp),y
:       sta ays_vipos,x
        lda ays_von,x            ; a note started: its envelope
        and #$40
        beq @per
        lda #$80
        sta ays_von,x
        ldy #2
        lda (ays_zp),y
        cmp #$FF
        beq @per
        pha
        iny
        lda (ays_zp),y
        ldy ays_tr,x
        sta ays_regs+12,y
        pla
        sta ays_regs+13,y
        lda #0
        sta ays_regs+11,y
@per:   lda ays_vnote,x          ; its period
        clc
        adc ays_arp
        cmp #96
        bcc :+
        lda #95
:
.if AYSONG_FAST_PERIODS
        asl a                    ; the 96-note table
        tay
        lda ays_ptab+1,y
        pha
        lda ays_ptab,y
        ldy ays_tp,x
        clc                      ; + the slide
        adc ays_vsll,x
        sta ays_regs,y
        pla
.else
        cmp ays_vpn,x
        beq @cached
        sta ays_vpn,x
        ldy #0                   ; a new note: octave, semitone
:       cmp #12
        bcc :+
        sbc #12
        iny
        bne :-
:       sty ays_t
        asl a
        tay
        lda ays_periods,y
        sta ays_vpbl,x
        lda ays_periods+1,y
        ldy ays_t
        beq @phi
:       lsr a
        ror ays_vpbl,x
        dey
        bne :-
        bcc @phi                 ; rounded: + the last bit out
        inc ays_vpbl,x
        bne @phi
        adc #0                   ; (C = 1)
@phi:   sta ays_vpbh,x
@cached:
        ldy ays_tp,x
        lda ays_vpbl,x           ; + the slide
        clc
        adc ays_vsll,x
        sta ays_regs,y
        lda ays_vpbh,x
.endif
        adc ays_vslh,x
        and #$0F
        sta ays_regs+1,y
@vol:   ldy #$10                 ; its volume: $10 = the envelope
        bit ays_ib
        bvs @vmute
        lda ays_ib
        and #$0F
        clc
        adc ays_vvoff,x
        bpl :+
        lda #0
:       cmp #16
        bcc :+
        lda #15
:       tay
@vmute: lda ays_von,x
        bpl @v0
        lda ays_bits,x
        and ays_mutem
        beq @v1
@v0:    ldy #0
@v1:    tya
        ldy ays_tv,x
        sta ays_regs+8,y
        lda ays_ib               ; its mixer bits: tone off 1, noise off 8
        eor #$30
        lsr a
        lsr a
        lsr a
        lsr a
        and #3
        tay
        lda ays_m4,y
        sta ays_vmix,x
        inx
        cpx ays_nv
        bcs @mixer
        jmp @voice
@mixer:
.repeat AYS_CHIPS, K
.if K = 1
        cpx #4                   ; (a 3-voice song: chip 2 left alone)
        bcc @write
.endif
        lda ays_vmix+3*K+2       ; 3. each chip's mixer
        asl a
        ora ays_vmix+3*K+1
        asl a
        ora ays_vmix+3*K
        sta ays_regs+16*K+7
.endrepeat
@write:
.repeat AYS_CHIPS, K
.if K = 1
        lda ays_nv
        cmp #4
        bcc ays_tick_end
.endif
.scope
        ldx #12                  ; 4. the registers that changed
reg:    lda ays_regs+16*K,x
        cmp ays_out+16*K,x
        beq same
        sta ays_out+16*K,x
        ldy #K
        AYSONG_WRITE
same:   dex
        bpl reg
        lda ays_regs+16*K+13     ; R13 unless $FF (a write restarts the
        cmp #$FF                 ; envelope)
        beq no13
        ldx #13
        ldy #K
        AYSONG_WRITE
no13:
.endscope
.endrepeat
ays_tick_end:
        rts
; Per voice: its period / volume register, its chip's registers, its mute bit.
ays_tp:     .byte 0, 2, 4, 16, 18, 20
ays_tv:     .byte 0, 1, 2, 16, 17, 18
ays_tr:     .byte 0, 0, 0, 16, 16, 16
ays_bits:   .byte 1, 2, 4, 8, 16, 32
ays_m4:     .byte 0, 1, 8, 9        ; (T off, N off) -> mixer bits
; Octave 0 (C0..B0) for the NTSC Apple II clock: aysong.py PERIODS;
; octave k = >> k, rounded half up.
AYS_P0 = 3901
AYS_P1 = 3682
AYS_P2 = 3475
AYS_P3 = 3280
AYS_P4 = 3096
AYS_P5 = 2922
AYS_P6 = 2758
AYS_P7 = 2603
AYS_P8 = 2457
AYS_P9 = 2319
AYS_P10 = 2189
AYS_P11 = 2066
.if AYSONG_FAST_PERIODS
ays_ptab:
.repeat 96, N
.if N < 12
        .word .ident(.sprintf("AYS_P%d", N))
.else
        .word (.ident(.sprintf("AYS_P%d", N .mod 12)) + (1 << (N / 12 - 1))) >> (N / 12)
.endif
.endrepeat
.else
ays_periods:
.repeat 12, N
        .word .ident(.sprintf("AYS_P%d", N))
.endrepeat
.endif
.endif
