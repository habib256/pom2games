; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; disk.inc -- CUTROPE's levels and stars on the disk (RWTS, DOS kept)
; ============================================================================
;   level_load  lvp = the record of level `level`: sector `level` of LEVELS
;               read into LVBUF when another level is there (the record
;               after DOS's 4-byte header: tools/cutrope.py --levels)
;   save_load   at start: CUTSAVE's stars into best (a foreign or unreadable
;               file: none won), total counted
;   won         at a win: the stars + 1 kept in best when better (save_flag)
;   save_due    when leaving a level: CUTSAVE written if save_flag (C = 1
;               from RWTS: not saved -- write protected -- and forgotten)
;   unlocked    X = level: Z = 0 when it can be played (the first one, or
;               the one before it won)
; LEVELS and CUTSAVE are ordinary DOS binary files; dev/tools/dos33patch.py
; writes where their data sectors lie into lvl_t / lvl_s and sav_t / sav_s
; when the disk is built. LVBUF and SAVBUF are text page 2 (HELLO, at
; $0801, stays below them).
; ============================================================================

LVBUF   = $0900
SAVBUF  = $0A00

.segment "DATA"
lvl_t:  .res NLEVEL + 1, 0              ; LEVELS's data sectors (the bench last)
lvl_s:  .res NLEVEL + 1, 0
sav_t:  .byte 0                         ; CUTSAVE's
sav_s:  .byte 0

.segment "BSS"
lv_in:      .res 1                      ; the level in LVBUF
best:       .res NLEVEL                 ; per level: 0 not won, else the stars + 1
save_flag:  .res 1

.segment "CODE"
level_load:
        LDX     level
        CPX     lv_in
        BEQ     @ok
        LDA     lvl_t,X
        STA     rwts_track
        LDA     lvl_s,X
        STA     rwts_sector
        LDA     #>LVBUF
        STA     rwts_page
        JSR     rwts_read
        BCC     :+
        LDA     #$40                    ; an error (the disk gone?): a buzz,
        LDX     #$FF                    ; then again
        JSR     tone
        JMP     level_load
:       LDX     level
        STX     lv_in
@ok:    LDA     #<(LVBUF + 4)
        STA     lvp
        LDA     #>(LVBUF + 4)
        STA     lvp+1
        RTS

save_load:
        LDA     #$FF
        STA     lv_in
        LDA     #0
        STA     save_flag
        JSR     save_read
        BCS     @none
        LDX     #3
@m:     LDA     SAVBUF+4,X
        CMP     sav_magic,X
        BNE     @none
        DEX
        BPL     @m
        LDX     #NLEVEL - 1
@c:     LDA     SAVBUF+8,X
        CMP     #5
        BCC     :+
        LDA     #0
:       STA     best,X
        DEX
        BPL     @c
        BMI     count
@none:  LDX     #NLEVEL - 1
        LDA     #0
:       STA     best,X
        DEX
        BPL     :-
        ; (falls into count)

; total = the stars of every level won
count:  LDA     #0
        STA     total
        LDX     #NLEVEL - 1
@l:     LDA     best,X
        BEQ     @n
        CLC                             ; total += best - 1
        ADC     total
        SEC
        SBC     #1
        STA     total
@n:     DEX
        BPL     @l
        RTS

won:    LDX     level
        CPX     #NLEVEL
        BCS     @rts
        LDA     cr_nstar
        CLC
        ADC     #1
        CMP     best,X
        BCC     @rts
        BEQ     @rts
        STA     best,X
        LDA     #1
        STA     save_flag
        JMP     count
@rts:   RTS

save_due:
        LDA     save_flag
        BEQ     @rts
        LDA     #0
        STA     save_flag
        JSR     save_read               ; (DOS's header kept)
        BCS     @rts
        LDX     #3
:       LDA     sav_magic,X
        STA     SAVBUF+4,X
        DEX
        BPL     :-
        LDX     #NLEVEL - 1
:       LDA     best,X
        STA     SAVBUF+8,X
        DEX
        BPL     :-
        JSR     save_sector
        JMP     rwts_write
@rts:   RTS

save_read:
        JSR     save_sector
        JMP     rwts_read

save_sector:
        LDA     sav_t
        STA     rwts_track
        LDA     sav_s
        STA     rwts_sector
        LDA     #>SAVBUF
        STA     rwts_page
        RTS

unlocked:
        TXA
        BEQ     :+
        LDA     best-1,X
        RTS
:       LDA     #1
        RTS

.segment "RODATA"
sav_magic:  .byte "CRS1"
.assert NLEVEL + 8 <= 256, error, "CUTSAVE: one sector"
.segment "CODE"
