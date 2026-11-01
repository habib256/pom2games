; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; auxdetect.asm -- is there 128 KB of auxiliary RAM (//e extended 80-column
;                  card, //c)?
; ============================================================================
; Standalone NMOS 6502, main RAM, ROM visible, any CPU of the family. Include
; it AFTER the callers (.ifref: assembled only if the source above references
; aux_detect or aux_detect_probe), in the segment the code goes in (no
; segment directive here); a second include assembles nothing. From ROGUE's
; launcher (rogue/src/launcher.s, byte-identical where it sat).
;
; aux_detect -- C = 1 when 128 KB of auxiliary RAM answers.
;   ROMID1 ($FBB3) must be $06 (//e, //c and later), else C = 0 at once:
;   on a II / II+ nothing but that ROM byte is read, no $C0xx switch is
;   touched, no RAM written (17 cycles + the JSR).
;   Then the write test: 80STORE on + HIRES + PAGE2 map $0400-$07FF and
;   $2000-$3FFF to auxiliary memory (whatever RAMRD/RAMWRT say); $A5 goes
;   to aux $2000, $5A to aux $0400, PAGE1 and $00 to main $2000, PAGE2 and
;   both aux bytes are read back: C = 1 when aux $2000 = $A5 and aux $0400
;   = $5A. A 1 KB 80-column card (text page only) folds $2000 onto its one
;   kilobyte and fails one of the two; a 64 KB //e with no card reads the
;   floating bus and fails.
;   Out: C; A = aux $2000 read, X = aux $0400 read (or A = ROMID1 on a
;   II / II+). Y kept. 64 B, 82 cycles when found, 79 / 83 when not
;   (+6 for the JSR, +1 for a branch taken across a page). The bytes are
;   not restored: main $2000 = $00, aux $2000 = $A5, aux $0400 = $5A
;   afterwards (AUX_DETECT_RESTORE below).
;   Exit switches: 80STORE off, PAGE1 (LOWSCR), LORES; TEXT/MIXED, RAMRD/
;   RAMWRT, 80COL, ALTZP and DHGR untouched. A program showing HGR or page 2
;   when it calls this must set them again (ROGUE's launcher shows text).
; aux_detect_probe -- the write test alone (after the ROMID1 check), for a
;   caller that already knows it runs on a //e or //c. On a II / II+ it
;   writes main $2000 / $0400 and returns C = 0 (the tests run it there).
;
; Not for code or a stack in $0400-$07FF / $2000-$3FFF (they switch under
; it), nor an IRQ handler; an IRQ during the ~55 cycles of the test whose
; handler writes the text page or HGR page 1 would hit aux memory: mask it
; (SEI) around the call if the program has one.
;
; Options (define before this include):
;   AUX_DETECT_RESTORE = 1  save main $2000, aux $2000 and aux $0400 on the
;                           stack (3 B) and put them back before returning:
;                           C as above, A = the main $2000 byte, X = aux
;                           $0400 read, Y = 1 found / 0 not; 95 B, 135
;                           cycles found, 130 / 134 not (+6 for the JSR).
; Undefined or 0: ROGUE's 64 bytes.
;
; C counterpart: _dhgr_capabilities in dev/lib/hgrc/dhgr_asm.s (cc65, ptr1,
; RAMWRT test at $2078, restores bytes and 80STORE; reports DHGR support).
; ============================================================================

.ifndef AUX_DETECT_RESTORE
AUX_DETECT_RESTORE = 0
.endif

.if (.referenced(aux_detect) .or .referenced(aux_detect_probe)) .and (.not .defined(aux_detect))
aux_detect:
        LDA     ROMID1
        CMP     #$06
        BNE     aux_detect_no   ; II / II+: no switch touched
aux_detect_probe:
        STA     STORE80ON
        BIT     HIRES
.if AUX_DETECT_RESTORE
        BIT     LOWSCR
        LDA     $2000
        PHA                     ; main $2000
        BIT     HISCR           ; aux $0400-$07FF and $2000-$3FFF
        LDA     $2000
        PHA                     ; aux $2000
        LDA     $0400
        PHA                     ; aux $0400
.else
        BIT     HISCR           ; aux $0400-$07FF and $2000-$3FFF
.endif
        LDA     #$A5
        STA     $2000
        LDA     #$5A
        STA     $0400
        BIT     LOWSCR          ; main
        LDA     #$00
        STA     $2000
        BIT     HISCR
        LDA     $2000
        LDX     $0400
.if AUX_DETECT_RESTORE
        LDY     #0
        CMP     #$A5
        BNE     @put
        CPX     #$5A
        BNE     @put
        INY                     ; Y = 1: found
@put:   PLA
        STA     $0400           ; aux, still PAGE2 (in reverse order: a
        PLA                     ; folded byte gets its first value back)
        STA     $2000
        BIT     LOWSCR
        PLA
        STA     $2000           ; main
        BIT     LORES
        STA     STORE80OFF
        CPY     #1              ; C = 1 when Y = 1
        RTS
.else
        BIT     LOWSCR
        BIT     LORES
        STA     STORE80OFF
        CMP     #$A5
        BNE     aux_detect_no
        CPX     #$5A
        BNE     aux_detect_no
        SEC
        RTS
.endif
aux_detect_no:
        CLC
        RTS
.endif
