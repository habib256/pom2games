; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; initials.asm -- high-score initials entry, one key at a time
; ============================================================================
;   ini_key -- A = a key (ASCII, bit 7 clear; KC_* of apple2.inc). Edits
;              ini_buf[0..INI_LEN-1] at the cursor ini_pos:
;                a letter of the set   stored at the cursor, which advances
;                                      (it stays on the last letter)
;                lowercase a-z         folded to uppercase first ($61-$7E
;                                      lose bit 5: {|}~ -> [\]^)
;                KC_UP / KC_DOWN       the cursor's letter: next / previous
;                                      in the set (wraps; a letter outside
;                                      the set becomes the first / last)
;                KC_LEFT, INI_DELETE   cursor left;  KC_RIGHT: cursor right
;                KC_RET / KC_ESC       finished: C = 1, A = the key (the
;                                      caller decides: accept / cancel)
;              Out otherwise C = 0: A = 1 (Z = 0) when ini_buf or ini_pos
;              changed (redraw), A = 0 (Z = 1) for any other key or a
;              cursor already at its end. Clobbers A, X, Y.
;
; The stick goes through joy.asm's stick_key with a table such as
;   STICK_KEYS = ini_stick   ; ini_stick: .byte KC_UP, KC_DOWN, KC_LEFT,
;                            ;            KC_RIGHT, KC_RIGHT, KC_RET
; (button 0 = next letter, button 1 = done; the program picks).
;
; Options (define before the include):
;   INI_LEN      letters (default 3, 1..128)
;   INI_CHARS    label of the program's set of letters, INI_CHARS_N bytes
;                (1..128; e.g. "ABC...Z0..9 -"); default: A-Z by arithmetic,
;                no table
;   INI_DELETE   second "cursor left" key (default $7F, //e DELETE)
;
; BSS: ini_buf (INI_LEN), ini_pos, each skipped if defined before the
; include (e.g. the program's record buffer). The caller fills ini_buf
; (e.g. "AAA" or the last initials) and zeroes ini_pos before the first key.
; No zero page. 117 B (A-Z by arithmetic), 119 B with a table. .ifref: include after the
; callers. Factored from DIRTBIKE (hof.inc), MICRO-SOKOBAN (score_hof.inc)
; and ARKABREAKOUT (records.inc), whose entry loops it replaces.
; Caller responsibility: .include "apple2.inc" first (KC_*).
; ============================================================================

.ifndef _INITIALS_ASM_LOADED_
.ifref ini_key
_INITIALS_ASM_LOADED_ = 1

.ifndef INI_LEN
INI_LEN = 3
.endif
.assert INI_LEN >= 1 .and INI_LEN <= 128, error, "INI_LEN: 1..128"
.ifndef INI_DELETE
INI_DELETE = $7F
.endif
.ifdef INI_CHARS
.assert INI_CHARS_N >= 1 .and INI_CHARS_N <= 128, error, "INI_CHARS_N: 1..128"
.endif

.segment "BSS"
.ifndef ini_buf
ini_buf:        .res INI_LEN
.endif
.ifndef ini_pos
ini_pos:        .res 1
.endif

.segment "CODE"
ini_key:
        CMP     #KC_RET
        BEQ     @rts            ; C = 1 (equal), A = the key
        CMP     #KC_ESC
        BEQ     @rts
        LDX     ini_pos
        CMP     #KC_LEFT
        BEQ     @left
        CMP     #INI_DELETE
        BEQ     @left
        CMP     #KC_RIGHT
        BEQ     @right
        CMP     #KC_UP
        BEQ     @up
        CMP     #KC_DOWN
        BEQ     @down
        CMP     #'a'
        BCC     @set
        AND     #$DF            ; lowercase -> uppercase ({|}~ -> [\]^)
@set:
.ifdef INI_CHARS
        JSR     @find
        BMI     @none           ; not in the set
.else
        CMP     #'A'
        BCC     @none
        CMP     #'Z'+1
        BCS     @none
.endif
        STA     ini_buf,X
        CPX     #INI_LEN-1
        BCS     @changed        ; the last letter: the cursor stays
        INX
        BCC     @pos            ; always
@right: CPX     #INI_LEN-1
        BCS     @none
        INX
        BCC     @pos            ; always
@left:  DEX
        BMI     @none           ; already on the first letter
@pos:   STX     ini_pos
@changed:
        LDA     #1
        CLC
        RTS
.ifdef INI_CHARS
@up:    LDA     ini_buf,X
        JSR     @find           ; Y = place, $FF if absent
        INY
        CPY     #INI_CHARS_N
        BCC     @put
        LDY     #0
        BCS     @put            ; always
@down:  LDA     ini_buf,X
        JSR     @find
        DEY                     ; absent: $FE, the last
        BPL     @put
        LDY     #INI_CHARS_N-1
@put:   LDA     INI_CHARS,Y
        STA     ini_buf,X
        JMP     @changed
; A = a char: Y = its place in INI_CHARS (N = 0), or Y = $FF (N = 1)
@find:  LDY     #INI_CHARS_N-1
@f:     CMP     INI_CHARS,Y
        BEQ     @rts
        DEY
        BPL     @f
        RTS
.else
@up:    LDA     ini_buf,X
        CMP     #'A'
        BCC     @first
        CMP     #'Z'
        BCS     @first          ; Z wraps to A (and anything above)
        ADC     #1              ; C = 0
        BNE     @put            ; always
@first: LDA     #'A'
        BNE     @put
@down:  LDA     ini_buf,X
        CMP     #'A'+1
        BCC     @last           ; A wraps to Z (and anything below)
        CMP     #'Z'+1
        BCS     @last
        SBC     #0              ; C = 0: - 1
        BNE     @put            ; always
@last:  LDA     #'Z'
@put:   STA     ini_buf,X
        BNE     @changed        ; always (a letter)
.endif
@none:  LDA     #0
        CLC
@rts:   RTS

.endif  ; .ifref ini_key
.endif  ; _INITIALS_ASM_LOADED_
