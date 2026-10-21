; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; rwts.asm -- direct sector I/O through DOS 3.3's RWTS (no file manager)
; ============================================================================
;   rwts_read        sector rwts_track / rwts_sector -> page rwts_page
;   rwts_write       page rwts_page -> sector rwts_track / rwts_sector
;   rwts_cmd         A = RWTS command (1 read, 2 write, 4 format), same call
;   rwts_read_tslist read a whole file: rwts_track / rwts_sector = its T/S
;                    list, read into page rwts_tsl; every listed data sector
;                    goes to rwts_page, rwts_page + 1... (the DOS 4-byte
;                    binary header included). Out: rwts_count = pages read,
;                    rwts_page = the next page. One T/S list (122 sectors).
;                    No upper bound: the file must fit below rwts_tsl (and
;                    RWTS) when it is loaded above them -- check its size
;                    when the disk is built.
;   rwts_find_file   A/Y = name (lo/hi; ASCII, ends with 0 or ','): look it
;                    up in the catalog, read into page rwts_page. Out:
;                    rwts_track / rwts_sector = its T/S list.
; All return C = 1 on an error (rwts_find_file: also when not found), after
; RWTS_RETRIES tries of each sector (default 1: RWTS retries by itself).
; Clobber A, X, Y. Buffers are whole pages.
;
; Why: once a game runs, DOS's file manager is the slow part (BLOAD moves
; one byte at a time) and the large part ($9600-$B6FF). RWTS ($B700-$BFFF)
; alone reads a sector per call; a program may even take the file manager's
; memory and keep only RWTS (DIRTBIKE). $03D9 runs RWTS (a JMP into it).
; $03E3 gives DOS's own I/O block (IOB), but by reading it from the file
; manager's memory ($AAC1): the address is asked on the FIRST call only and
; kept (rwts_iob), so make one call before that memory is reused.
;
; Drive: the slot and drive of DOS's last access (IOB bytes 15-16), i.e.
; the disk the game was started from; any volume.
;
; No zero page: the IOB and the buffers are reached through patched
; absolute operands. RWTS itself uses DOS's zero page (below $50).
; RWTS_KEEP_ZP = 1 also saves and restores DOS_ZP_START .. +DOS_ZP_LEN
; around each call, in rwts_zp_buf (BSS unless defined before the include).
;
; Variables (BSS, each skipped if defined before the include, e.g. as an
; alias of the program's own): rwts_track, rwts_sector, rwts_page,
; rwts_tsl, rwts_count, rwts_try, rwts_ix, rwts_t.
; .ifref: include after the callers. From DIRTBIKE's loader and
; MICRO-SOKOBAN's fast_disk.inc.
; ============================================================================

.ifndef _RWTS_ASM_LOADED_
_RWTS_ASM_LOADED_ = 1

RWTS_ENTRY  = $03D9             ; A/Y = IOB (hi/lo): run the command
RWTS_IOB    = $03E3             ; -> A/Y = DOS's IOB (hi/lo)
RWTS_CATALOG_TRACK  = 17        ; first catalog sector (DOS 3.3: T17 S15)
RWTS_CATALOG_SECTOR = 15

.ifndef RWTS_RETRIES
RWTS_RETRIES = 1
.endif
.assert RWTS_RETRIES >= 1 .and RWTS_RETRIES <= 255, error, "RWTS_RETRIES: 1..255"

.segment "BSS"
.ifndef rwts_track
rwts_track:  .res 1
.endif
.ifndef rwts_sector
rwts_sector: .res 1
.endif
.ifndef rwts_page
rwts_page:   .res 1
.endif
.if .referenced(rwts_read) .or .referenced(rwts_write) .or .referenced(rwts_cmd) .or .referenced(rwts_read_tslist) .or .referenced(rwts_find_file)
.ifndef rwts_try
rwts_try:    .res 1
.endif
.endif
.if .referenced(rwts_read_tslist) .or .referenced(rwts_find_file)
.ifndef rwts_ix
rwts_ix:     .res 1
.endif
.endif
.ifref rwts_read_tslist
.ifndef rwts_tsl
rwts_tsl:    .res 1
.endif
.ifndef rwts_count
rwts_count:  .res 1
.endif
.endif
.ifref rwts_find_file
.ifndef rwts_t
rwts_t:      .res 1
.endif
.endif
.ifdef RWTS_KEEP_ZP
.ifndef rwts_zp_buf
rwts_zp_buf: .res DOS_ZP_LEN
.endif
.endif
.if .referenced(rwts_read) .or .referenced(rwts_write) .or .referenced(rwts_cmd) .or .referenced(rwts_read_tslist) .or .referenced(rwts_find_file)
.segment "DATA"
rwts_iob:    .word 0                    ; DOS's IOB, once known (0: not yet)
.endif

.segment "CODE"

.ifref rwts_find_file
rwts_find_file:
        STA     rwts_name+1
        STY     rwts_name+2
        LDA     rwts_page
        STA     rwts_cat+2
        LDA     #RWTS_CATALOG_TRACK
        STA     rwts_track
        LDA     #RWTS_CATALOG_SECTOR
        STA     rwts_sector
@sec:   JSR     rwts_read
        BCS     @rts
        LDA     #11                     ; 7 entries of 35 bytes from byte 11
        STA     rwts_ix
@entry: LDY     rwts_ix
        JSR     rwts_cat                ; track of its T/S list:
        BEQ     @skip                   ;   0 = never used
        CMP     #$FF                    ;   $FF = deleted
        BEQ     @skip
        TYA
        CLC
        ADC     #3                      ; the name (30 bytes, high bit set,
        TAY                             ; space padded)
        LDX     #0
@ch:    JSR     rwts_name
        BEQ     @end
        CMP     #','
        BEQ     @end
        STA     rwts_t
        JSR     rwts_cat
        AND     #$7F
        CMP     rwts_t
        BNE     @skip
        INY
        INX
        CPX     #30
        BNE     @ch
        BEQ     @found
@end:   CPX     #30
        BEQ     @found
        JSR     rwts_cat
        CMP     #$A0                    ; and no more characters there
        BEQ     @found
@skip:  CLC
        LDA     rwts_ix
        ADC     #35
        STA     rwts_ix
        BCC     @entry
        LDY     #1                      ; next catalog sector
        JSR     rwts_cat
        BEQ     @none
        STA     rwts_track
        INY
        JSR     rwts_cat
        STA     rwts_sector
        JMP     @sec
@found: LDY     rwts_ix
        JSR     rwts_cat
        STA     rwts_track
        INY
        JSR     rwts_cat
        STA     rwts_sector
        CLC
        RTS
@none:  SEC
@rts:   RTS

rwts_cat:
        LDA     $FF00,Y                 ; patched: the catalog page
        RTS
rwts_name:
        LDA     $FFFF,X                 ; patched: the name
        RTS
.endif

.ifref rwts_read_tslist
rwts_read_tslist:
        LDA     #0
        STA     rwts_count
        LDA     rwts_page
        PHA
        LDA     rwts_tsl
        STA     rwts_page
        STA     @lt+2
        STA     @ls+2
        JSR     rwts_read
        PLA
        STA     rwts_page
        BCS     @rts
        LDX     #12                     ; pairs from byte 12
@next:  STX     rwts_ix
@lt:    LDA     $FF00,X                 ; patched: the list's page
        BEQ     @done                   ; track 0: end of the list
        STA     rwts_track
@ls:    LDA     $FF01,X
        STA     rwts_sector
        JSR     rwts_read
        BCS     @rts
        INC     rwts_page
        INC     rwts_count
        LDX     rwts_ix
        INX
        INX
        BNE     @next                   ; 122 pairs: the whole sector
@done:  CLC
@rts:   RTS
.endif

.if .referenced(rwts_read) .or .referenced(rwts_write) .or .referenced(rwts_cmd)
rwts_write:
        LDA     #2
        .byte   $2C                     ; BIT abs: skips the LDA #1
rwts_read:
        LDA     #1
rwts_cmd:
        PHA                             ; the command, until IOB byte 12
.ifdef RWTS_KEEP_ZP
        LDX     #0
@save:  LDA     DOS_ZP_START,X
        STA     rwts_zp_buf,X
        INX
        CPX     #<DOS_ZP_LEN
        BNE     @save
.endif
        LDY     rwts_iob                ; DOS's IOB: asked once, then kept
        LDA     rwts_iob+1
        BNE     @known
        JSR     RWTS_IOB
        STY     rwts_iob
        STA     rwts_iob+1
@known: STY     rwts_put+1
        STA     rwts_put+2
        STY     rwts_get+1
        STA     rwts_get+2
        LDY     #15                     ; slot / drive of DOS's last access
        JSR     rwts_get
        LDY     #1
        JSR     rwts_put
        LDY     #16
        JSR     rwts_get
        LDY     #2
        JSR     rwts_put
        LDA     #1                      ; table type
        LDY     #0
        JSR     rwts_put
        LDA     #0                      ; any volume, buffer at offset 0
        LDY     #3
        JSR     rwts_put
        LDY     #8
        JSR     rwts_put
        LDA     rwts_track
        LDY     #4
        JSR     rwts_put
        LDA     rwts_sector
        INY
        JSR     rwts_put
        LDA     rwts_page
        LDY     #9
        JSR     rwts_put
        PLA
        LDY     #12
        JSR     rwts_put
        LDA     #RWTS_RETRIES
        STA     rwts_try
@try:   LDY     rwts_iob
        LDA     rwts_iob+1
        JSR     RWTS_ENTRY
        BCC     @ok
        DEC     rwts_try
        BNE     @try
@ok:
.ifdef RWTS_KEEP_ZP
        PHP
        LDX     #0
@rest:  LDA     rwts_zp_buf,X
        STA     DOS_ZP_START,X
        INX
        CPX     #<DOS_ZP_LEN
        BNE     @rest
        PLP
.endif
        RTS

rwts_put:
        STA     $FFFF,Y                 ; patched: DOS's IOB
        RTS
rwts_get:
        LDA     $FFFF,Y
        RTS
.endif

.endif  ; _RWTS_ASM_LOADED_
