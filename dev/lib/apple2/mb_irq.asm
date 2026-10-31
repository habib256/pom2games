; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; mb_irq.asm — a Mockingboard music service on the interrupt of the first
; VIA's timer 1: one call of the program's tick routine at MB_IRQ_HZ
; whatever the main loop does (notes on time at any frame rate, NTSC or
; PAL), and shadowed AY writes (only the registers that changed go out).
; Extracted from WARGALAGA II (2026-10-31), which stays byte-identical.
;
; Needs mockingboard.asm (mb_detect / mb_write / mb_timer_start / mb_stop /
; mb_quiet_chip / mb_chip / mb_slot), included anywhere in the program.
; 65C02 or NMOS: the CPU the source is assembled for (ca65 --cpu) picks the
; instructions (stz/phx/phy on a 65C02, the same bytes WG always had).
;
; Include AFTER the callers (.ifref: only what is referenced is assembled).
; Several includes are fine: each assembles what was referenced before it
; and is not defined yet, in the order below (a program can thus place each
; routine where it wants; WG falls into mb_irq_start from sound_init).
;
;   mb_irq_start  the service on: patches the handler for MB_IRQ_SLOT, hooks
;                 the interrupt (ProDOS ALLOC_INTERRUPT, or the vector at
;                 MB_IRQ_VECTOR), T1 free running at MB_IRQ_PERIOD, its IRQ
;                 enabled, then CLI. Call only with a card (mb_detect != 0)
;                 and after mb_forget. mb_irq_n != 0 afterwards = installed
;                 (ProDOS: the interrupt number; 0 = ALLOC_INTERRUPT failed,
;                 the timer is then left off). mb_irq_rts is its final RTS
;                 (a caller without a card can branch to it).
;   mb_forget     every shadow ($FF = unknown): the next mb_put of each
;                 register writes. X = $FF, A = $FF on return.
;   mb_put        X = register 0..15, A = value, mb_chip = chip: the write
;                 only if the shadow differs. Keeps X; clobbers A, Y.
;   mb_hush       if MB_IRQ_SLOT != 0: the first chip's three volumes to 0
;                 and its shadows forgotten (both chips with MB_IRQ_HUSH_BOTH),
;                 under SEI, mb_chip kept. Call it before disk I/O: ProDOS's
;                 Disk II driver masks interrupts ~1 s, a note would hang.
;   mb_irq_stop   both chips silent, T1 and its interrupt off (mb_stop), the
;                 interrupt released (DEALLOC_INTERRUPT / the old vector
;                 back). Safe when the service never started.
;   mb_irq_handler  the interrupt routine (not called by the program).
;
; The handler: CLD; not timer 1 of the slot's VIA -> not ours (ProDOS: SEC
; RTS; vector: on to the previous vector); else T1 acknowledged (T1 low
; read), [jsr _a2_vbl_scan], inc mb_irq_ticks, [skip all if MB_IRQ_GATE is
; 0], mb_chip saved, the tick, mb_chip restored, [jsr _a2_vbl_scan].
;   - default (hook mode): mb_chip = 0, then jsr MB_IRQ_TICK; the tick writes
;     what it wants (mb_put for either chip, or mb_write).
;   - MB_IRQ_FRAME = addr: jsr MB_IRQ_TICK first, then the 14-byte frame at
;     addr goes to chip 1 (mb_chip = 0): registers 12..0 through the shadows
;     inline, register 13 written whenever it is not $FF (an envelope shape
;     write restarts the envelope: $FF = leave it; PT3 / AYS convention).
; The handler owns the chip(s) its tick writes: the main program writes the
; other chip only (mb_write masks interrupts, mb_chip is restored).
;
; Options (before the first include; ABI.md "Speed/RAM options"):
;   MB_IRQ_PRODOS = 1     ProDOS 8 ALLOC_INTERRUPT (default). 0: own vector.
;   MB_IRQ_VECTOR = addr  with MB_IRQ_PRODOS = 0: $03FE (default: the ROM's
;                         IRQ handler saves A at $45 and jumps there; DOS 3.3
;                         and bare programs, II+ / //e / //c) or $FFFE (the
;                         language card's RAM is banked in: raw 6502 entry,
;                         A/X/Y saved by the handler; the program enables LC
;                         writes itself before mb_irq_start / mb_irq_stop).
;   MB_IRQ_HZ = n         tick rate (default 50); MB_IRQ_PERIOD = latch
;                         overrides it (default 1020484 / MB_IRQ_HZ - 2: T1
;                         free run = latch + 2 cycles, 1.0205 MHz NTSC).
;   MB_IRQ_TICK = label   the tick routine (required when mb_irq_start is
;                         used). Main RAM, ends with RTS, may clobber A/X/Y.
;   MB_IRQ_FRAME = addr   optional: the frame flushed after the tick (above).
;   MB_IRQ_GATE = addr    optional: a byte, 0 = no tick (the song paused; the
;                         ticks are still counted).
;   MB_IRQ_SCAN = 1       jsr _a2_vbl_scan on entry and exit (apple2vbl.s: a
;                         long tick must not hide a //e VBL edge). Default 0.
;   MB_IRQ_HUSH_BOTH = 1  mb_hush silences both chips (6-voice songs).
;   MB_IRQ_SPLIT = 1      the handler is assembled only by an include after a
;                         reference to mb_irq_handler (WG: after sound_frame);
;                         default 0: with mb_irq_start.
;
; Storage (define before the first include to alias, else reserved in BSS
; / ZEROPAGE): mb_shadow (32: chip 1 registers 0..15, chip 2 16..31),
; mb_irq_n (1), mb_irq_ticks (1, wraps; never cleared: zero the BSS),
; mb_irq_old (2, vector mode only),
; mb_irq_ptr (2 ZP, scratch of mb_irq_start: mb_ptr if mockingboard.asm is
; already included, else 2 own bytes), mb_irq_slot (the slot byte read by
; mb_irq_start / mb_hush: default mb_slot).
;
; Cycles (MB_FAST_WRITE = 1, measured in WG): handler overhead ~60 cycles +
; the tick + ~16 cycles per unchanged frame register, ~70 per written one.
.ifndef _MB_IRQ_DEFS_
_MB_IRQ_DEFS_ = 1
.ifndef CPU_ISET_65C02
.macpack cpu
.endif
.ifndef MB_IRQ_PRODOS
MB_IRQ_PRODOS = 1
.endif
.ifndef MB_IRQ_VECTOR
MB_IRQ_VECTOR = $03FE
.endif
.ifndef MB_IRQ_HZ
MB_IRQ_HZ = 50
.endif
.ifndef MB_IRQ_PERIOD
MB_IRQ_PERIOD = 1020484 / MB_IRQ_HZ - 2
.endif
.ifndef MB_IRQ_SCAN
MB_IRQ_SCAN = 0
.endif
.ifndef MB_IRQ_HUSH_BOTH
MB_IRQ_HUSH_BOTH = 0
.endif
.ifndef MB_IRQ_SPLIT
MB_IRQ_SPLIT = 0
.endif
MB_IRQ_C02 = .cpu .bitand ::CPU_ISET_65C02
.ifndef mb_irq_slot
mb_irq_slot = mb_slot
.endif
.pushseg
.bss
.ifndef mb_shadow
mb_shadow:    .res 32
.endif
.ifndef mb_irq_n
mb_irq_n:     .res 1
.endif
.ifndef mb_irq_ticks
mb_irq_ticks: .res 1
.endif
.if (.not MB_IRQ_PRODOS) .and (.not .defined(mb_irq_old))
mb_irq_old:   .res 2
.endif
.ifndef mb_irq_ptr
.ifdef mb_ptr
mb_irq_ptr = mb_ptr
.else
.zeropage
mb_irq_ptr:   .res 2
.endif
.endif
.popseg
.macro MBI_STZ addr
.if MB_IRQ_C02
        stz addr
.else
        lda #0
        sta addr
.endif
.endmacro
; Vector mode: the registers the handler saved, back.
.macro MBI_RESTORE
.if MB_IRQ_C02
        ply
        plx
.else
        pla
        tay
        pla
        tax
.endif
.if MB_IRQ_VECTOR = $FFFE
        pla
.endif
.endmacro
.endif

.if .referenced(mb_irq_start) .and (.not .defined(mb_irq_start))
mb_irq_start:
        lda mb_irq_slot          ; patch the handler's VIA addresses
        ora #$C0
        sta mb_irq_ifr+2
        sta mb_irq_ack+2
        sta mb_irq_ptr+1
        MBI_STZ mb_irq_ptr
        php
        sei
.if MB_IRQ_PRODOS
        jsr $BF00
        .byte $40                ; ALLOC_INTERRUPT
        .word mb_irq_alloc
        bcs @noirq
        lda mb_irq_alloc+1
        sta mb_irq_n
.else
        lda MB_IRQ_VECTOR        ; the previous handler: the chain
        sta mb_irq_old
        lda MB_IRQ_VECTOR+1
        sta mb_irq_old+1
        lda #<mb_irq_handler
        sta MB_IRQ_VECTOR
        lda #>mb_irq_handler
        sta MB_IRQ_VECTOR+1
        lda #1
        sta mb_irq_n
.endif
        lda #<MB_IRQ_PERIOD      ; T1 free running at MB_IRQ_HZ...
        ldx #>MB_IRQ_PERIOD
        jsr mb_timer_start
        ldy #$0E                 ; ...and its interrupt on (IER: set bit 6)
        lda #$C0
        sta (mb_irq_ptr),y
        plp
        cli
.if MB_IRQ_PRODOS
        rts
@noirq:
        plp
.endif
mb_irq_rts:
        rts
.endif

.if (.referenced(mb_forget) .or (MB_IRQ_HUSH_BOTH .and .referenced(mb_hush))) .and (.not .defined(mb_forget))
mb_forget:
        lda #$FF
        ldx #31
:       sta mb_shadow,x
        dex
        bpl :-
        rts
.endif

.if .referenced(mb_put) .and (.not .defined(mb_put))
mb_put:
.if MB_IRQ_C02
        phx
.endif
        pha
        txa
        ldy mb_chip
        beq :+
        ora #16
:       tay
        pla
        cmp mb_shadow,y
        beq :+
        sta mb_shadow,y
.if MB_IRQ_C02
        jsr mb_write
:       plx
        rts
.else
        tay                      ; X = register, A = value: X kept across
        txa                      ; mb_write
        pha
        tya
        jsr mb_write
        pla
        tax
:       rts
.endif
.endif

.if .referenced(mb_hush) .and (.not .defined(mb_hush))
mb_hush:
        lda mb_irq_slot
        beq :++
        php
        sei                      ; (the music handler writes too)
.if MB_IRQ_HUSH_BOTH
        jsr mb_silence           ; (keeps mb_chip)
        jsr mb_forget
.else
        lda mb_chip
        pha
        MBI_STZ mb_chip
        jsr mb_quiet_chip
        pla
        sta mb_chip
        lda #$FF                 ; chip 1's shadows (mb_shadow+0..15)
        ldx #15
:       sta mb_shadow,x
        dex
        bpl :-
.endif
        plp
:       rts
.endif

.if .referenced(mb_irq_stop) .and (.not .defined(mb_irq_stop))
mb_irq_stop:
        php
        sei
        jsr mb_stop              ; silence, timer 1 and its interrupt off
        lda mb_irq_n
        beq :+
.if MB_IRQ_PRODOS
        sta mb_irq_dealloc+1
        MBI_STZ mb_irq_n
        jsr $BF00
        .byte $41                ; DEALLOC_INTERRUPT
        .word mb_irq_dealloc
.else
        MBI_STZ mb_irq_n
        lda mb_irq_old
        sta MB_IRQ_VECTOR
        lda mb_irq_old+1
        sta MB_IRQ_VECTOR+1
.endif
:       plp
        rts
.endif

.if (.referenced(mb_irq_handler) .or (.defined(mb_irq_start) .and (.not MB_IRQ_SPLIT))) .and (.not .defined(mb_irq_handler))
mb_irq_handler:
.if (.not MB_IRQ_PRODOS)
.if MB_IRQ_VECTOR = $FFFE
        pha                      ; raw entry: A too
.endif
.if MB_IRQ_C02
        phx
        phy
.else
        txa
        pha
        tya
        pha
.endif
.endif
        cld
mb_irq_ifr:
        lda $C40D                ; IFR (slot patched by mb_irq_start)
        and #$40
        bne :+
.if MB_IRQ_PRODOS
        sec                      ; not ours
        rts
.else
        MBI_RESTORE              ; not ours: on to the previous handler
        jmp (mb_irq_old)
.endif
:
mb_irq_ack:
        lda $C404                ; T1 low: acknowledges
.if MB_IRQ_SCAN
        jsr _a2_vbl_scan          ; (a long handler: a //e VBL edge kept)
.endif
        inc mb_irq_ticks
.ifdef MB_IRQ_GATE
        lda MB_IRQ_GATE
        beq @done
.endif
        lda mb_chip              ; the main code may be about to write chip 2
        pha
.ifdef MB_IRQ_FRAME
        jsr MB_IRQ_TICK
        MBI_STZ mb_chip          ; (chip 1's shadows: mb_shadow+0..15)
        ldx #12
@reg:   lda MB_IRQ_FRAME,x       ; inline mb_put: most are unchanged
        cmp mb_shadow,x
        beq :+
        sta mb_shadow,x
.if MB_IRQ_C02
        phx
        jsr mb_write
        plx
.else
        tay                      ; X kept across mb_write
        txa
        pha
        tya
        jsr mb_write
        pla
        tax
.endif
:       dex
        bpl @reg
        lda MB_IRQ_FRAME+13      ; envelope shape: $FF = unchanged (a write
        cmp #$FF                 ; restarts the envelope, shadow or not)
        beq :+
        ldx #13
        jsr mb_write
:
.else
        MBI_STZ mb_chip
        jsr MB_IRQ_TICK
.endif
        pla
        sta mb_chip
.if MB_IRQ_SCAN
        jsr _a2_vbl_scan
.endif
@done:
.if MB_IRQ_PRODOS
        clc
        rts
mb_irq_alloc:   .byte 2, 0
        .word mb_irq_handler
mb_irq_dealloc: .byte 1, 0
.else
        MBI_RESTORE
.if MB_IRQ_VECTOR <> $FFFE
        lda $45                  ; the ROM saved A there
.endif
        rti
.endif
.endif
