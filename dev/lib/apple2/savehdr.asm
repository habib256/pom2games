; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; savehdr.asm -- save-file magic: check it after a load, write it before a save
; ============================================================================
; A save file starts with a few fixed bytes ("MZS", version): a file that
; does not (never written, another game's, an older format) is ignored.
;
;   magic_check -- A/Y = the loaded data (lo/hi), X = the magic's last byte
;                  in MAGIC_TABLE: compares MAGIC_LEN bytes. C = 0 when they
;                  all match, C = 1 otherwise. Clobbers A, X, Y. 24 B.
;   magic_put   -- the same arguments: copies the magic into the data
;                  before a save. Clobbers A, X, Y. 19 B.
;
; MAGIC_TABLE (label, mandatory): the program's magics, MAGIC_LEN bytes
; each, one after the other; the first magic's last byte is X = MAGIC_LEN-1,
; the second's 2*MAGIC_LEN-1... MAGIC_LEN: default 4 (1..128).
;
;   MAGIC_TABLE = magics
;   magics: .byte "MZS", 1, "MZP", 1
;           LDA #<SAVE / LDY #>SAVE / LDX #3 / JSR magic_check / BCS @bad
;
; A site is 9 bytes (+ the branch) against 7 per byte for LDA/CMP/BNE (28 for
; four bytes) or 5 per byte for LDA #/STA (20). The operand is patched
; (no zero page, code in RAM). .ifref: include after the callers.
; From MAZE3D (save.inc profiles and checkpoints, maze3d.s score file).
; ============================================================================

.ifndef _SAVEHDR_ASM_LOADED_
.if .referenced(magic_check) .or .referenced(magic_put)
_SAVEHDR_ASM_LOADED_ = 1

.ifndef MAGIC_LEN
MAGIC_LEN = 4
.endif
.assert MAGIC_LEN >= 1 .and MAGIC_LEN <= 128, error, "MAGIC_LEN: 1..128"

.segment "CODE"
.ifref magic_check
magic_check:
        STA     @data+1
        STY     @data+2
        LDY     #MAGIC_LEN-1
@lp:    LDA     MAGIC_TABLE,X
@data:  CMP     $FFFF,Y         ; patched: the data
        BNE     @bad
        DEX
        DEY
        BPL     @lp
        CLC
        RTS
@bad:   SEC
        RTS
.endif

.ifref magic_put
magic_put:
        STA     @data+1
        STY     @data+2
        LDY     #MAGIC_LEN-1
@lp:    LDA     MAGIC_TABLE,X
@data:  STA     $FFFF,Y         ; patched: the data
        DEX
        DEY
        BPL     @lp
        RTS
.endif

.endif  ; referenced
.endif  ; _SAVEHDR_ASM_LOADED_
