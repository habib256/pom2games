; ============================================================================
; loader.inc -- load track A (0..29) from the disk, without DOS
; ============================================================================
; Once the game runs, DOS's main body ($9600-$B6FF) holds the track; only
; its disk driver RWTS ($B700-$BFFF) is kept (lib/apple2/rwts.asm: page-3
; vectors, DOS's own I/O block, the boot drive). The track files T01..T30
; stay ordinary DOS files: trackdir_t / trackdir_s give the track and sector
; of each one's T/S list (patched into the binary by tools/patchdir.py
; after the disk is built). The file is read sector by sector into the track
; area, then (tools/packtrack.py has the layout):
;   stream 2 unpacks to HGR page 2 -> pat_k, pat_rel0, pat_plo/phi (offsets
;            made addresses), pool;
;   stream 1 unpacks to HGR page 2 -> copied over the area: track_h (4 KB)
;            and track_ids (4 KB).
; C = 1 on a disk error (after RETRIES tries).
; ============================================================================

track_h   = $9600               ; ground row per world pixel
track_ids = $A600               ; window pattern per world pixel
LOADBUF   = $9600               ; the file, before unpacking
TSLBUF    = $B600               ; its T/S list (DOS boot code, unused now)
RWTS_RETRIES = 4

.segment "ZEROPAGE"
lz4fh_src: .res 2
lz4fh_dst: .res 2
cp_src:   .res 2
cp_dst:   .res 2

.segment "LOWBSS"
DEMO_MAX = 400                  ; = tools/packtrack.py
demobuf:  .res DEMO_MAX         ; the track's proven ride (attract demo)

.segment "BSS"
finish_x: .res 2                ; the loaded track's finish line = its lap
lap_c:    .res 2                ; lap / 7 (the camera's byte column)

.segment "CODE"

load_track:
        TAX
        LDA     trackdir_t,X            ; the T/S list
        STA     rwts_track
        LDA     trackdir_s,X
        STA     rwts_sector
        LDA     #>TSLBUF
        STA     rwts_tsl
        LDA     #>LOADBUF               ; the data sectors, in file order
        STA     rwts_page
        JSR     rwts_read_tslist
        BCC     @read
        RTS
@read:  LDA     LOADBUF+4               ; payload after DOS's 4-byte header
        STA     finish_x
        STA     lap_len                 ; the track loops: a lap is this long
        STA     cp_src                  ; lap_c = lap / 7 (a multiple of 7)
        LDA     LOADBUF+5
        STA     finish_x+1
        STA     lap_len+1
        STA     cp_src+1
        LDA     #0
        STA     lap_c
        STA     lap_c+1
@d7:    LDA     cp_src
        ORA     cp_src+1
        BEQ     @d7e
        SEC
        LDA     cp_src
        SBC     #7
        STA     cp_src
        BCS     @d7i
        DEC     cp_src+1
@d7i:   INC     lap_c
        BNE     @d7
        INC     lap_c+1
        BNE     @d7
@d7e:
        CLC                             ; the ride, after both streams:
        LDA     #<(LOADBUF+12)          ; copied out before they overwrite it
        ADC     LOADBUF+6
        STA     cp_src
        LDA     #>(LOADBUF+12)
        ADC     LOADBUF+7
        STA     cp_src+1
        CLC
        LDA     cp_src
        ADC     LOADBUF+10
        STA     cp_src
        LDA     cp_src+1
        ADC     LOADBUF+11
        STA     cp_src+1
        LDY     #0
@dm:    LDA     (cp_src),Y              ; DEMO_MAX = 400: 256 + 144
        STA     demobuf,Y
        INY
        BNE     @dm
        INC     cp_src+1
@dm2:   LDA     (cp_src),Y
        STA     demobuf+256,Y
        INY
        CPY     #DEMO_MAX-256
        BNE     @dm2
        LDA     #<(LOADBUF+12)          ; stream 2: the patterns
        STA     lz4fh_src
        LDA     #>(LOADBUF+12)
        STA     lz4fh_src+1
        JSR     unpack_p2
        LDA     #<pat_k                 ; pat_k .. pat_phi: 4 pages
        STA     cp_dst
        LDA     #>pat_k
        STA     cp_dst+1
        LDA     #$40
        LDX     #4
        JSR     copy_pages
        LDX     #0                      ; offsets -> addresses in the pool
@abs:   CLC
        LDA     pat_plo,X
        ADC     #<pool
        STA     pat_plo,X
        LDA     pat_phi,X
        ADC     #>pool
        STA     pat_phi,X
        INX
        BNE     @abs
        LDA     #<pool                  ; the pool (POOL_MAX bytes)
        STA     cp_dst
        LDA     #>pool
        STA     cp_dst+1
        LDA     #$44
        LDX     #POOL_MAX / 256
        JSR     copy_pages
        CLC                             ; stream 1, after stream 2
        LDA     #<(LOADBUF+12)
        ADC     LOADBUF+6
        STA     lz4fh_src
        LDA     #>(LOADBUF+12)
        ADC     LOADBUF+7
        STA     lz4fh_src+1
        JSR     unpack_p2
        LDA     #<track_h               ; heights and ids over the area
        STA     cp_dst
        LDA     #>track_h
        STA     cp_dst+1
        LDA     #$40
        LDX     #32
        JSR     copy_pages
        CLC
        RTS

unpack_p2:
        LDA     #0
        STA     lz4fh_dst
        LDA     #$40
        STA     lz4fh_dst+1
        JMP     lz4fh_unpack

; copy X pages from page A to cp_dst
copy_pages:
        STA     cp_src+1
        LDA     #0
        STA     cp_src
        LDY     #0
@cp:    LDA     (cp_src),Y
        STA     (cp_dst),Y
        INY
        BNE     @cp
        INC     cp_src+1
        INC     cp_dst+1
        DEX
        BNE     @cp
        RTS

.segment "DATA"
trackdir_t: .res NTRACKS        ; T/S list of T01..T30: tools/patchdir.py
trackdir_s: .res NTRACKS
.segment "CODE"
