; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; memory.s -- 128 KB residency (included by wild.s)
; ============================================================================
; NEOWILD.SYSTEM preloads every module, the pristine simulation and the TOPO
; sheet into auxiliary RAM. A module "load" is now a copy from auxiliary RAM
; into its main execution window: the $5800 window, the SIM window at $9600
; or HGR page 1 for TOPO. Each copy restores the pristine image, exactly like
; the DOS BLOAD it replaces, so the simulation keeps its reload semantics.
;
; mem_fetch -- X = directory index (0 TOPOGEN, 1..25 modules, 3 = SIM). An
;   entry of length 0 (24: the end module is read from the disk; the fourth
;   species of a 3-species region) copies nothing. Sources: auxiliary RAM,
;   auxiliary language card banks 2/1, main language card bank 2 (lot 7).
;   Copies exactly the stored length; bytes past it keep their old contents.
;   An entry whose bank has bit 7 set (BANK_LZ, docs/MEMORY.md 13) holds an
;   LZ image (tools/pack_boot.py tokens, terminated by a match of distance
;   0) behind the 2-byte address of its window: the copy lands at the end of
;   the module's own extent (tools/build_disk.py lz_store places it so that
;   the decoder never overtakes it) and lz_unpack decodes it in place.
;   Entry: main ZP/stack (ALTZP off), RAMRD off, D = 0. Preserves the I flag,
;   80STORE, RAMWRT, the video switches, all zero page and the text screen.
;   Clobbers A, X, Y. Leaves the ROM selected in the language card space.
; mli_call -- A = MLI command, X/Y = parameter list. Returns the MLI C/A.
;   Every MLI call of the game goes through it: mli_calls/mli_bytes count
;   them, including the loader's calls made before the game started.
; Native fine geography (lot 5) is resident in the auxiliary language card
;   (src/geoaux.s): no disk access is left during play but NEOWILD.END and
;   NEOWILD.HOF at the end of a journey (lot 7).
; prodos_exit / reset_exit -- leave to ProDOS: text, banks, /RAM, bitmap,
;   RESET vector and zero page restored, then MLI QUIT.
; prodos_restore -- the same restoration without QUIT: module_restart (INPUT)
;   then reads NEOWILD.SYSTEM again for the start menu (lot 7).
; ============================================================================

RDLCBNK2  = $C011
RDLCRAM   = $C012
RDRAMRD   = $C013
RDRAMWRT  = $C014
RDALTZP   = $C016
RD80STORE = $C018
RAMRDON   = $C003
RAMWRTON  = $C005
ALTZPOFF  = $C008
ALTZPON   = $C009
ALTCHAROFF = $C00E
LCRAM2    = $C080               ; read language card RAM bank 2, write protect
LCROM     = $C082               ; read ROM, write protect
LCRAM1    = $C088
LCBANK1   = $C08B               ; read and write RAM bank 1 (read twice)
MLI       = $BF00
PD_BITMAP = $BF58
PD_DEVNUM = $BF30

MOD_COUNT = 28                  ; directory entries: TOPOGEN + modules 1..27
                                ; (23 fourth species, 24 hall of fame, 25 stars,
                                ; 26 orientation, 27 health alerts)
DIR_SIZE  = 7                   ; bank, source, length, destination
XFER_RUN  = $0120               ; stack-page copy loop while RAMRD is on

; Directory banks
BANK_AUX  = 0                   ; auxiliary $0800-$BFFF: RAMRD copy
BANK_LC2  = 1                   ; auxiliary language card, bank 2
BANK_LC1  = 2                   ; auxiliary language card, bank 1
BANK_MLC2 = 3                   ; main language card, bank 2 ($D400-$DDFF:
                                ; ProDOS 8 keeps its QUIT code in $D100-$D3FF)
BANK_LZ   = $80                 ; + bank: an LZ image, decoded in the window

.segment "RESBSS"
; Instrumentation. Little-endian; the loader includes its own calls.
mli_calls:  .res 2              ; every MLI call (loader and game)
mli_reads:  .res 2              ; MLI READ/READ_BLOCK calls
mli_bytes:  .res 3              ; bytes returned by READ (512 per READ_BLOCK)
xfer_count: .res 2              ; aux -> main module copies
xfer_bytes: .res 3              ; bytes copied by those copies
mem_ready:  .res 1              ; 1 once the loader handed over to the game
; State captured by NEOWILD.SYSTEM at entry, restored at exit.
saved_reset: .res 3
saved_bitmap: .res 24
geo_path:   .res 40             ; "/VOLUME/NEOWILD.GEO", length first: the
                                ; template of the NEOWILD.END/.HOF paths (HOF_PATH)
geo_decodes: .res 2             ; fine geography tiles decoded (src/geoaux.s)
geo_queries: .res 3             ; fine geography queries (native maps)
xfer_80:    .res 1
xfer_wrt:   .res 1
xfer_lc:    .res 1
mf_lz:      .res 1              ; bit 7: the entry is an LZ image
journey_kind: .res 1            ; 0 scenario, 1 free journey (written by the
                                ; loader; read by NEOWILD.END). Not MAP+33: the
                                ; wild food scan reuses MAP+28..MAP+33 (TRAVEL)
.export mli_calls, mli_reads, mli_bytes, xfer_count, xfer_bytes, mem_ready
.export journey_kind
.export saved_reset, saved_bitmap, geo_path, geo_decodes, geo_queries

.segment "REGIONTEXT"
; Written by the region pack NEOWILD.Rn (tools/build_disk.py region_texts),
; plain ASCII padded with zeros. Read by the introduction and messages of
; lot 7 step 4; the start menu itself uses the loader's own copy.
region_name:    .res 16         ; BRITISH COLUMBIA ... CHILE
region_fauna:   .res 40         ; fauna sentence of the original introduction
region_species: .res 48         ; four names of 12 (header $60D0-$60FF)
region_number:  .res 1          ; 1..6 (= MAP+32)
region_count:   .res 1          ; species 2..4
region_intro:   .res 22         ; name of the original introduction
.export region_name, region_fauna, region_species, region_number, region_count, region_intro

.segment "SAVE"
saved_zp:   .res 256            ; ProDOS zero page at NEOWILD.SYSTEM entry
.export saved_zp

.segment "IOBUF"
io_buffer:  .res 1024
.export io_buffer

.segment "RESCODE"
; Filled by tools/build_disk.py from the placement of each image.
module_dir: .res MOD_COUNT * DIR_SIZE
.export module_dir

mem_fetch:
        php
        sei
        lda     RD80STORE       ; 80STORE/PAGE2 would send $2000-$3FFF
        sta     xfer_80         ; writes to auxiliary RAM: disable it
        sta     STORE80OFF
        lda     RDRAMWRT
        sta     xfer_wrt
        sta     RAMWRTOFF
        sta     RAMRDOFF        ; documented precondition, enforced
        lda     RDLCRAM
        sta     xfer_lc
        txa                     ; Y = 7 * X
        asl     a
        asl     a
        asl     a
        stx     @sub+1
        sec
@sub:   sbc     #0
        tay
        lda     module_dir+1,y
        sta     mf_src
        lda     module_dir+2,y
        sta     mf_src+1
        lda     module_dir+5,y
        sta     mf_dst
        lda     module_dir+6,y
        sta     mf_dst+1
        clc                     ; account the copy
        lda     module_dir+3,y
        adc     xfer_bytes
        sta     xfer_bytes
        lda     module_dir+4,y
        adc     xfer_bytes+1
        sta     xfer_bytes+1
        bcc     :+
        inc     xfer_bytes+2
:       inc     xfer_count
        bne     :+
        inc     xfer_count+1
:       lda     module_dir+3,y  ; rest
        sta     mf_rest
        lda     module_dir+4,y  ; pages
        sta     mf_pages
        lda     module_dir,y
        sta     mf_lz
        and     #$7F
        bne     @lc
        ; Auxiliary $0200-$BFFF: the loop runs in the main stack page, which
        ; RAMRD does not switch. Copy it there for each transfer.
        ldx     #XFER_SIZE-1
@tpl:   lda     xfer_tpl,x
        sta     XFER_RUN,x
        dex
        bpl     @tpl
        lda     mf_src
        sta     xr_src1+1
        sta     xr_src2+1
        lda     mf_src+1
        sta     xr_src1+2
        sta     xr_src2+2
        lda     mf_dst
        sta     xr_dst1+1
        sta     xr_dst2+1
        lda     mf_dst+1
        sta     xr_dst1+2
        sta     xr_dst2+2
        lda     mf_rest
        sta     xr_rest+1
        ldx     mf_pages
        jsr     XFER_RUN
        jmp     mf_done
@lc:    ; Auxiliary language card: ALTZP selects it, and also the auxiliary
        ; stack, so this loop uses neither the stack nor the zero page.
        ; BANK_MLC2 (lot 7): bank 2 of the main language card, ALTZP off.
        ldx     #<LCRAM2
        cmp     #BANK_LC1
        bne     :+
        ldx     #<LCRAM1
:       stx     lc_bank+1
        ldx     #<ALTZPON
        cmp     #BANK_MLC2
        bne     :+
        dex                     ; ALTZPOFF: main card, main zero page
:       stx     lc_zp+1
        lda     mf_src
        sta     lc_src1+1
        sta     lc_src2+1
        lda     mf_src+1
        sta     lc_src1+2
        sta     lc_src2+2
        lda     mf_dst
        sta     lc_dst1+1
        sta     lc_dst2+1
        lda     mf_dst+1
        sta     lc_dst1+2
        sta     lc_dst2+2
        lda     mf_rest
        sta     lc_rest+1
        ldx     mf_pages
        ldy     #0
lc_zp:  sta     ALTZPON         ; patched: ALTZPON / ALTZPOFF
lc_bank:
        lda     $C080           ; patched: LCRAM2 / LCRAM1, read only
        cpx     #0
        beq     lc_tail
lc_page:
lc_src1:
        lda     $FFFF,y
lc_dst1:
        sta     $FFFF,y
        iny
        bne     lc_page
        inc     lc_src1+2
        inc     lc_dst1+2
        inc     lc_src2+2
        inc     lc_dst2+2
        dex
        bne     lc_page
lc_tail:
lc_rest:
        cpy     #0
        beq     lc_end
lc_src2:
        lda     $FFFF,y
lc_dst2:
        sta     $FFFF,y
        iny
        bne     lc_tail
lc_end: lda     LCROM
        sta     ALTZPOFF
mf_done:
        bit     mf_lz           ; RAMWRT still off: decode in the window
        bpl     :+
        jsr     lz_unpack
:       bit     xfer_lc         ; the game normally runs with the ROM; a
        bpl     :+              ; caller with RAM read keeps it, read-only
        lda     RDLCBNK2
        bpl     @bank1
        lda     LCRAM2
        bmi     :+
@bank1: lda     LCRAM1
:       bit     xfer_wrt
        bpl     :+
        sta     RAMWRTON
:       bit     xfer_80
        bpl     :+
        sta     STORE80ON
:       plp
        rts
.export mem_fetch

mf_src:   .word 0
mf_dst:   .word 0
mf_rest:  .byte 0
mf_pages: .byte 0

; Copied to XFER_RUN before each auxiliary transfer. X = full pages,
; xr_rest = remaining bytes, Y = 0 on entry of the tail.
xfer_tpl:
        .org    XFER_RUN
xr_start:
        sta     RAMRDON
        ldy     #0
        cpx     #0
        beq     xr_tail
xr_page:
xr_src1:
        lda     $FFFF,y
xr_dst1:
        sta     $FFFF,y
        iny
        bne     xr_page
        inc     xr_src1+2
        inc     xr_dst1+2
        inc     xr_src2+2
        inc     xr_dst2+2
        dex
        bne     xr_page
xr_tail:
xr_rest:
        cpy     #0
        beq     xr_done
xr_src2:
        lda     $FFFF,y
xr_dst2:
        sta     $FFFF,y
        iny
        bne     xr_tail
xr_done:
        sta     RAMRDOFF
        rts
xr_end:
        .reloc
XFER_SIZE = xr_end - xr_start
.assert XFER_SIZE <= 64, error, "stack-page transfer loop too large"

; ----------------------------------------------------------------------------
; lz_unpack -- (mem_fetch) the LZ image just copied to mf_dst: its first two
; bytes are the output address, then groups of a flag byte (low bit first,
; 1 = match) and eight tokens: a literal, or a match of two bytes (12-bit
; distance, length - 3 in the high nibble's low four bits; 15 adds a byte,
; length - 18). A match of distance 0 ends the image. It borrows LZ_ZP
; ($50-$55, saved on the stack and restored: mem_fetch preserves the whole
; zero page). In MENUCODE, resident while a journey runs; the I/O buffer of
; the end of a journey overwrites it, and INPUT, the only module loaded
; afterwards, is stored raw (tools/build_disk.py LZ_MODULES).
LZ_ZP   = $50
lz_in   = LZ_ZP                 ; input page pointer (Y: offset in it)
lz_out  = LZ_ZP+2
lz_from = LZ_ZP+4
.segment "MENUCODE"
lz_unpack:
        ldx     #5
:       lda     LZ_ZP,x
        pha
        dex
        bpl     :-
        lda     mf_dst
        sta     lz_in
        lda     mf_dst+1
        sta     lz_in+1
        ldy     #0
        lda     (lz_in),y
        sta     lz_out
        iny
        lda     (lz_in),y
        sta     lz_out+1
        iny
        ldx     #0              ; X = 0: (lz_out,x)
        lda     #1              ; empty: the first token reads a flag byte
        sta     lz_flags
@token: lsr     lz_flags
        bne     @flag
        lda     (lz_in),y       ; eight more flags, a sentinel bit behind them
        iny
        bne     :+
        inc     lz_in+1
:       sec
        ror     a
        sta     lz_flags
@flag:  lda     (lz_in),y       ; C: the token's flag
        iny
        bne     :+
        inc     lz_in+1
:       bcs     @match
        sta     (lz_out,x)      ; literal
        inc     lz_out
        bne     @token
        inc     lz_out+1
        bcc     @token          ; always
@match: sta     lz_dist
        lda     (lz_in),y
        iny
        bne     :+
        inc     lz_in+1
:       sta     lz_len
        ora     lz_dist
        beq     @end            ; distance 0: the end
        lda     lz_len
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        sta     lz_from+1
        sec                     ; source = output - distance
        lda     lz_out
        sbc     lz_dist
        sta     lz_from
        lda     lz_out+1
        sbc     lz_from+1
        sta     lz_from+1
        lda     lz_len
        and     #15
        adc     #2              ; C set (no borrow): length 3..18
        cmp     #18
        bne     :+
        clc                     ; 18 + the extension byte
        adc     (lz_in),y
        iny
        bne     :+
        inc     lz_in+1
:       sty     lz_y
        tax
        ldy     #0
@copy:  lda     (lz_from),y
        sta     (lz_out),y
        iny
        dex
        bne     @copy
        tya                     ; X = 0 again
        clc
        adc     lz_out
        sta     lz_out
        bcc     :+
        inc     lz_out+1
:       ldy     lz_y
        jmp     @token
@end:   ldx     #0
:       pla
        sta     LZ_ZP,x
        inx
        cpx     #6
        bne     :-
        rts
lz_flags: .res 1
lz_dist:  .res 1
lz_len:   .res 1
lz_y:     .res 1
.export lz_unpack

.segment "RESCODE"
; ----------------------------------------------------------------------------
mli_call:
        sta     mli_cmd
        stx     mli_parm
        sty     mli_parm+1
        inc     mli_calls
        bne     :+
        inc     mli_calls+1
:       jsr     MLI
mli_cmd: .byte  0
mli_parm: .word 0
        php
        pha
        bcs     @done
        lda     mli_cmd
        cmp     #$80            ; READ_BLOCK: 512 bytes
        bne     @read
        ldx     #2
        lda     #0
        beq     @count
@read:  cmp     #$CA            ; READ: its transfer count
        bne     @done
        lda     mli_parm
        sta     @lo+1
        sta     @hi+1
        lda     mli_parm+1
        sta     @lo+2
        sta     @hi+2
        ldy     #6
@lo:    lda     $FFFF,y
        iny
@hi:    ldx     $FFFF,y
@count: clc
        adc     mli_bytes
        sta     mli_bytes
        txa
        adc     mli_bytes+1
        sta     mli_bytes+1
        bcc     :+
        inc     mli_bytes+2
:       inc     mli_reads
        bne     @done
        inc     mli_reads+1
@done:  pla
        plp
        rts
.export mli_call

; ----------------------------------------------------------------------------
; prodos_text -- main banks, ROM, 40-column text page 1, full screen.
prodos_text:
        cld
        sta     RAMRDOFF
        sta     RAMWRTOFF
        sta     ALTZPOFF
        sta     STORE80OFF
        sta     COL80OFF
        sta     ALTCHAROFF
        bit     LCROM
        bit     DHIRES_OFF
        bit     TXTSET
        bit     MIXCLR
        bit     LOWSCR
        bit     LORES
        rts

reset_exit:
        cld
        ldx     #$FF
        txs
prodos_exit:
        jsr     prodos_restore
prodos_quit:
        lda     #$65            ; QUIT
        ldx     #<quit_parms
        ldy     #>quit_parms
        jsr     mli_call
@halt:  jmp     @halt           ; QUIT never returns
quit_parms: .byte 4, 0, 0, 0, 0, 0, 0

prodos_restore:
        jsr     prodos_text
        jsr     _prodos_video_release   ; rebuild the empty /RAM disk
        ldx     #23
:       lda     saved_bitmap,x
        sta     PD_BITMAP,x
        dex
        bpl     :-
        ldx     #2
:       lda     saved_reset,x
        sta     SOFTEV,x
        dex
        bpl     :-
        ldx     #0
:       lda     saved_zp,x
        sta     $00,x
        inx
        bne     :-
        bit     KBDSTRB
        rts
.export prodos_exit, reset_exit, prodos_restore, prodos_quit
