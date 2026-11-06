; pt3.s -- Vortex Tracker II (.pt3) decoder, Vince Weaver's pt3_lib 0.5
; (pt3_lib-NOTICE.txt). [lib] for 65C02/6502 programs that own their IRQs.
;
; Include it from the program's own module, with:
;   PT3_ZP   32 free zero-page bytes (pt3_zp.inc), kept between ticks;
;   PT3_LOC  the song, page aligned (the decoder adds offsets to its page);
;   the 1.77 MHz -> 1 MHz period conversion is off (smaller, faster): write
;   the song for a 1 MHz AY, or set PT3_FREQ_CONVERSION = 1 before.
; Optional PT3_FIXED_NOTE_TABLE = -1 (default): select the module's table
; at run time. Values 0..3 omit the other table generators and require that
; exact header byte in an immutable module. Default bytes/flags are unchanged.
; With a fixed table, init returns C=0 on success or C=1 on a mismatch. A
; mismatch sets DONE_SONG, writes a silent AY_REGISTERS frame (R7=$3F,
; R13=$FF) and makes ticks no-ops; the caller still owns hardware flushing.
; A matching reinitialization restores normal playback. No extra RAM/ZP.
; Initialize with the tick source stopped or masked; calls are not reentrant.
; Entry points:
;   pt3_init_song   once, before the first tick (~10 000 cycles: tables);
;   pt3_tick        one tick (50 Hz for most songs): AY_REGISTERS..+13 =
;                   the registers of one AY; R13 = $FF means "unchanged"
;                   (rewriting it would restart the envelope). Loops at the
;                   song's loop position. Upstream: typically 10-15 % of a
;                   1 MHz CPU at 50 Hz; measure your song.
; The program writes the registers (one chip, both, only those changed...)
; and runs pt3_tick from its interrupt or its main loop. Self-modifying
; code: in RAM. ~1.7 KB code + 448 bytes of tables + ~570 bytes of init.

.include "pt3_zp.inc"

.ifndef PT3_FREQ_CONVERSION
PT3_FREQ_CONVERSION = 0
.endif
.if !PT3_FREQ_CONVERSION
PT3_DISABLE_FREQ_CONVERSION = 1
.endif
PT3_DISABLE_SWITCHABLE_FREQ_CONVERSION = 1

.ifndef PT3_FIXED_NOTE_TABLE
PT3_FIXED_NOTE_TABLE = -1
.endif
.if PT3_FIXED_NOTE_TABLE < -1 .or PT3_FIXED_NOTE_TABLE > 3
.error "PT3_FIXED_NOTE_TABLE: -1 or 0..3"
.endif

.include "pt3_lib_core.s"
.include "pt3_lib_init.s"

pt3_tick:
; Fixed-table initialization patches this JSR opcode to RTS on mismatch.
	jsr	pt3_make_frame
	lda	DONE_SONG
	beq	pt3_tick_done
pt3_loop_smc:				; (pt3_init_song patches the loop position)
	lda	#$d1
	sta	current_pattern_smc+1
	lda	#0
	sta	current_line_smc+1
	sta	current_subframe_smc+1
	sta	DONE_SONG
	beq	pt3_tick		; (always)
pt3_tick_done:
	rts
