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
;   the module's own extent, up to 31 bytes past it (the margin, bits 2-6 of
;   the bank byte; tools/build_disk.py lz_store places it so that the
;   decoder never overtakes it); lz_guard keeps those bytes aside, lz_unpack
;   decodes in place and puts them back: nothing past the image changes.
;   An entry of bank BANK_DISK (docs/MEMORY.md 14, NeoWildernessXL only)
;   is read from the disk: disk_fetch, whole blocks of NEOWILD.BLK.
;   Entry: main ZP/stack (ALTZP off), RAMRD off, D = 0. Preserves the I flag,
;   80STORE, RAMWRT, the video switches, all zero page and the text screen.
;   Clobbers A, X, Y. Leaves the ROM selected in the language card space.
; mli_call -- A = MLI command, X/Y = parameter list. Returns the MLI C/A.
;   Every MLI call of the game goes through it: mli_calls/mli_bytes count
;   them, including the loader's calls made before the game started.
; Native fine geography (lot 5) is resident in the auxiliary language card
;   (src/geoaux.s). Disk accesses during play: NEOWILD.END and NEOWILD.HOF
;   at the end of a journey (lot 7), SAVE/RESTORE (lot 9) and, on
;   NeoWildernessXL only, the four rarely loaded modules of NEOWILD.BLK
;   (CAMP, MEDVIEW, TREE, ORIENT: disk_fetch, docs/MEMORY.md 14), FORAGE
;   and the campfire (both editions: sim_fetch, docs/MEMORY.md 16, 17);
;   never during a view, a walk or a screen and its return.
; reset_exit -- the RESET vector's target: a resident relay that copies INPUT
;   into its window and leaves to ProDOS from there (module_reset_exit).
; The exit path lives in INPUT (docs/MEMORY.md 15), with module_restart:
;   prodos_restore -- text, banks, /RAM, bitmap, RESET vector and zero page
;   restored (the state the loader found: directory entry EX_ENTRY);
;   prodos_quit -- MLI QUIT.
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

MOD_COUNT = 34                  ; directory entries: TOPOGEN + modules 1..27
                                ; (2: the exit state, EX_ENTRY)
                                ; (23 fourth species, 24 hall of fame, 25 stars,
                                ; 26 orientation, 27 health alerts), 28 the
                                ; text bank, 29 its fetch (text_fetch), 30
                                ; ProDOS's zero page (prodos_restore), 31
                                ; FORAGE (lot 4, NEOWILD.BLK), 32 GRID (the
                                ; grid's lists and queue, src/grid.s)
DIR_SIZE  = 7                   ; bank, source, length, destination
XFER_RUN  = $0120               ; stack-page copy loop while RAMRD is on

; Directory banks
BANK_AUX  = 0                   ; auxiliary $0800-$BFFF: RAMRD copy
BANK_LC2  = 1                   ; auxiliary language card, bank 2
BANK_LC1  = 2                   ; auxiliary language card, bank 1
BANK_MLC2 = 3                   ; main language card, bank 2 ($D400-$DDFF:
                                ; ProDOS 8 keeps its QUIT code in $D100-$D3FF)
BANK_LZ   = $80                 ; + bank: an LZ image, decoded in the window
BANK_DISK = $40                 ; docs/MEMORY.md 14: raw image in NEOWILD.BLK
                                ; (source = its first block, read whole blocks
                                ; into the window by disk_fetch)

.segment "RESBSS"
; Instrumentation. Little-endian; the loader includes its own calls.
mli_calls:  .res 2              ; every MLI call (loader and game)
mli_reads:  .res 2              ; MLI READ/READ_BLOCK calls
mli_bytes:  .res 3              ; bytes returned by READ (512 per READ_BLOCK)
xfer_count: .res 2              ; aux -> main module copies
xfer_bytes: .res 3              ; bytes copied by those copies
xfer_texts: .res 2              ; of which text_fetch's (the text bank)
mem_ready:  .res 1              ; 1 once the loader handed over to the game
geo_path:   .res 40             ; "/VOLUME/NEOWILD.GEO", length first: the
                                ; template of the NEOWILD.END/.HOF paths (HOF_PATH)
geo_decodes: .res 2             ; fine geography tiles decoded (src/geoaux.s)
geo_queries: .res 3             ; fine geography queries (native maps)
mf_lz:      .res 1              ; bit 7: the entry is an LZ image
; mem_fetch's entry, laid out as a READ_BLOCK parameter list for disk_fetch
; (docs/MEMORY.md 14): the count is set by disk_fetch, the unit by the
; loader (the boot unit, DEVNUM).
rb_parms:   .res 1              ; 3
rb_unit:    .res 1              ; DEVNUM at boot
mf_dst:     .res 2              ; buffer
mf_src:     .res 2              ; block number (BANK_DISK)
mf_rest:    .res 1
mf_pages:   .res 1
journey_kind: .res 1            ; 0 scenario, 1 free journey (written by the
                                ; loader; read by NEOWILD.END). Not MAP+33: the
                                ; wild food scan reuses MAP+28..MAP+33 (TRAVEL)
.export mli_calls, mli_reads, mli_bytes, xfer_count, xfer_bytes, mem_ready, xfer_texts
.export journey_kind, rb_parms, rb_unit, mf_dst, mf_src
.export geo_path, geo_decodes, geo_queries

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
saved_zp:   .res 256            ; ProDOS zero page at NEOWILD.SYSTEM entry; during
                                ; the game HICODE (it waits in auxiliary $BF00)
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
        bpl     :+
        jsr     lz_guard        ; LZ: the bytes the copy will pass over
:       lda     mf_lz
        cmp     #BANK_DISK
        bne     :+
        jmp     disk_fetch      ; (TEXT)
:       and     #3
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
:
xfer_lc = *+1
        lda     #0         ; the game normally runs with the ROM; a
        bpl     :+              ; caller with RAM read keeps it, read-only
        lda     RDLCBNK2
        bpl     @bank1
        lda     LCRAM2
        bmi     :+
@bank1: lda     LCRAM1
:
xfer_wrt = *+1
        lda     #0
        bpl     :+
        sta     RAMWRTON
:
xfer_80 = *+1
        lda     #0
        bpl     :+
        sta     STORE80ON
:       plp
        rts
.export mem_fetch


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
; zero page).
; Docs/MEMORY.md 14: the decoder (lz_unpack, lz_guard, lz_back) runs in place
; in bank 2 of the MAIN language card at $D001-$D0FF (segment LZCODE, a
; record of the trunk): ProDOS 8 keeps $D100-$D3FF of that bank for its QUIT
; code and only reads $D000 (its bank signature, never written here); the
; rest of page $D0 is never used. Its variables stay in TEXT, and TEXT keeps
; two relays that select that bank for the call. Read AND write enabled
; ($C083 twice): lz_guard patches its own operand and lz_back's. Everything
; it touches is main RAM below $C000 (the window, mf_*, lz_*, LZ_ZP, the
; stack): no ROM, no MLI, nothing of bank 1. mem_fetch masks interrupts.
LZ_ZP   = $50
lz_in   = LZ_ZP                 ; input page pointer (Y: offset in it)
lz_out  = LZ_ZP+2
lz_from = LZ_ZP+4
LCRAM2W = $C083                 ; read and write RAM bank 2 (read twice)
.segment "TEXT"
; lz_guard / lz_unpack -- relays: C tells the decoder's entry which one (BIT
; leaves C alone); the ROM is back on return (mf_done then restores the
; caller's language card state).
lz_guard:
        clc
        .byte   $24             ; BIT zp: skips the SEC
lz_unpack:
        sec
        bit     LCRAM2W
        bit     LCRAM2W
        jsr     lzc_entry
        bit     LCROM
        rts
lz_flags: .res 1
lz_dist:  .res 1
lz_len:   .res 1
lz_y:     .res 1
lz_m:     .res 1
lz_keep:  .res 31

; ----------------------------------------------------------------------------
; disk_fetch -- (mem_fetch, BANK_DISK; docs/MEMORY.md 14) a raw image of
; NEOWILD.BLK, read with MLI READ_BLOCK from the boot unit straight into its
; window: mf_src = its first block, mf_dst = the window, mf_rest/mf_pages =
; its length, rounded up to whole blocks (the bytes past the image up to the
; block boundary receive the padding; the window is 2 KB and the image at
; most that, tools/build_disk.py). mem_fetch masked interrupts and set
; 80STORE, RAMRD and RAMWRT off; the window pages are free in the ProDOS
; bitmap (boot.s game_pages). A failed read (the disk taken out) beeps,
; waits for a key and tries again: the game has nowhere else to go.
; With bit 7 of df_kbd set (src/fire.s), a key waiting between two blocks
; ends the read: df_left is then nonzero (the image is incomplete).
; ProDOS leaves its block driver's command ($42-$47) and other scratch of
; $3A-$4F changed (measured: $40, $41, $45, $46, $4F after a READ_BLOCK on
; the SmartPort): kept on the stack, as mem_fetch preserves all zero page.
DF_ZP    = $3A
DF_ZPLEN = $50 - DF_ZP
disk_fetch:
        ldx     #DF_ZPLEN-1
:       lda     DF_ZP,x
        pha
        dex
        bpl     :-
        lda     #3              ; (a cleared RESBSS after a QUIT: set here)
        sta     rb_parms
        lda     mf_rest         ; blocks = (pages + (rest > 0) + 1) / 2
        cmp     #1
        lda     mf_pages
        adc     #1
        lsr     a
        sta     df_left
@read:  lda     #$80            ; READ_BLOCK
        ldx     #<rb_parms
        ldy     #>rb_parms
        jsr     mli_call
        bcc     @next
        jsr     $FBDD           ; bell, then the common keyboard/joystick reader
        jsr     wait_key
        jmp     @read
@next:  inc     mf_dst+1        ; 512 bytes further, next block
        inc     mf_dst+1
        inc     mf_src
        bne     :+
        inc     mf_src+1
:       dec     df_left
        beq     @end
        bit     df_kbd          ; the campfire's read: a key ends it
        bpl     @read
        bit     KBD
        bpl     @read
@end:   ldx     #0
:       pla
        sta     DF_ZP,x
        inx
        cpx     #DF_ZPLEN
        bne     :-
        jmp     mf_done
df_left:  .res 1               ; blocks left to read (nonzero: cut by a key)
df_kbd:   .byte 0               ; bit 7: a key waiting cuts the read
.export disk_fetch

.segment "LZCODE"
lzc_entry:
        bcs     lzc_unpack
; lz_guard -- (mem_fetch, before the copy) the margin's bytes past the image:
; the last lz_m bytes of the copy's extent, kept in lz_keep.
lzc_guard:
        lda     mf_lz
        lsr     a
        lsr     a
        and     #31
        sta     lz_m
        beq     @done
        clc                     ; base = end of the copy - margin
        lda     mf_dst
        adc     mf_rest
        tax
        lda     mf_dst+1
        adc     mf_pages
        tay
        txa                     ; the operands below index from base - 1
        clc
        sbc     lz_m
        sta     @get+1
        sta     lzb_put+1
        tya
        sbc     #0
        sta     @get+2
        sta     lzb_put+2
        ldx     lz_m
@get:   lda     $FFFF-1,x
        sta     lz_keep-1,x
        dex
        bne     @get
@done:  rts
; lz_back -- the margin's bytes back (end of lz_unpack).
lz_back:
        ldx     lz_m
        beq     lzb_done
lzb_get:
        lda     lz_keep-1,x
lzb_put:
        sta     $FFFF-1,x
        dex
        bne     lzb_get
lzb_done:
        rts
; lzc_unpack -- the decoder proper (entry lz_unpack).
lzc_unpack:
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
        jmp     lz_back
.export lz_unpack, lzc_entry

.segment "RESCODE"
; ----------------------------------------------------------------------------
; text_fetch -- A = a text of the bank (build/textbank.inc, tools/gentextbank.py):
; the text into tb_buf, expanded; returns A/X = tb_buf. Entry TB_FETCH of the
; directory is a scratch entry (bank written by tools/build_disk.py): the two
; offsets of a text in the index, then its bytes, end-aligned in tb_buf;
; then each token ($80 + k, but $A1) brings dictionary word k in its place
; (the output never overtakes the input: a word is longer than its token);
; "@" and its operand stay literal. Clobbers Y. In HICODE ($BE00).
TB_DIR   = 28                   ; the bank (raw image in the store)
TB_FETCH = 29                   ; scratch entry: source, length, destination
ZP_ENTRY = 30                   ; aux $BF00 -> saved_zp (tools/build_disk.py)
.segment "HICODE"
text_fetch:
        ldx     #$FF            ; end-aligned
        jsr     tf_get
        stx     tf_in
        lda     #0
        sta     tf_out
@loop:  ldx     tf_in
        cpx     #TB_MAX
        beq     @done
        inc     tf_in
        lda     tb_buf,x
        cmp     #'@'
        bne     @token
        jsr     @put            ; "@", then its operand as it is
        ldx     tf_in
        inc     tf_in
        lda     tb_buf,x
        bcs     @lit            ; (C set by cmp)
@token: cmp     #$80
        bcc     @lit
        cmp     #$A1
        beq     @lit
        sec                     ; word k = token - $80, - 1 past $A1
        sbc     #$80
        cmp     #$22
        bcc     :+
        sbc     #1
:       ldx     tf_out
        jsr     tf_word
        clc
        lda     tf_out
        adc     tf_len
        sta     tf_out
        bcc     @loop           ; always
@lit:   jsr     @put
        jmp     @loop
@put:   ldx     tf_out
        sta     tb_buf,x
        inc     tf_out
        rts
@done:  lda     #<tb_buf
        ldx     #>tb_buf
        rts
; tf_get -- A = number, X = index in tb_buf ($FF: end-aligned): its bytes
; there; X = the index used, tf_len = their count.
tf_get:
        ldy     #0              ; public text directory: indices 1..255
        beq     tf_index
tf_word:
        ldy     #2              ; dictionary directory: indices 256..287
tf_index:
        sty     @index_high+1
        stx     tf_dst
        ldy     #<tf_idx        ; the index pair into tf_idx
        sty     module_dir+TB_FETCH*DIR_SIZE+5
        ldy     #>tf_idx
        sty     module_dir+TB_FETCH*DIR_SIZE+6
        asl     a               ; 2 bytes per number, on the selected index page
@index_high:
        ldx     #0
        bcc     :+
        inx
:       ldy     #4
        jsr     tf_copy
        sec
        lda     tf_idx+2
        sbc     tf_idx
        sta     tf_len
        ldx     tf_dst
        inx
        bne     :+
        lda     #TB_MAX         ; end-aligned
        sec                     ; a bank record may cross a 256-byte boundary
        sbc     tf_len
        tax
        inx
:       dex
        stx     tf_dst
        txa
        clc
        adc     #<tb_buf
        sta     module_dir+TB_FETCH*DIR_SIZE+5
        lda     #>tb_buf
        adc     #0
        sta     module_dir+TB_FETCH*DIR_SIZE+6
        lda     tf_idx
        ldx     tf_idx+1
        ldy     tf_len
        jsr     tf_copy
        ldx     tf_dst
        rts
tf_copy:                        ; A/X = offset in the bank, Y = length
        clc
        adc     module_dir+TB_DIR*DIR_SIZE+1
        sta     module_dir+TB_FETCH*DIR_SIZE+1
        txa
        adc     module_dir+TB_DIR*DIR_SIZE+2
        sta     module_dir+TB_FETCH*DIR_SIZE+2
        sty     module_dir+TB_FETCH*DIR_SIZE+3
        inc     xfer_texts      ; counted apart from the module loads
        bne     :+
        inc     xfer_texts+1
:       ldx     #TB_FETCH
        jmp     mem_fetch
.pushseg
.segment "TEXT"
tf_idx:  .res 4                 ; transfer scratch, initialized before every read
.popseg
tf_len:  .res 1
tf_dst:  .res 1
tf_in:   .res 1
tf_out:  .res 1
.export text_fetch
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
; reset_exit -- the RESET vector (SOFTEV, set by the loader). RESET leaves the
; //e with main RAM, ALTZP off and the ROM, interrupts masked, but the stack
; anywhere and INPUT maybe not in its window (overlay_current may even be
; stale after a RESET inside a copy): a fresh stack, then a direct copy of
; INPUT, raw in the store, and its exit path (docs/MEMORY.md 15).
reset_exit:
        cld
        ldx     #$FF
        txs
        ldx     #13
        jsr     mem_fetch
        jmp     module_reset_exit
.export reset_exit

.segment "INPUT"
; ----------------------------------------------------------------------------
; The way back to ProDOS (docs/MEMORY.md 15: start and exit code kept out of
; the resident images). The loader leaves the state it found in directory
; entry EX_ENTRY of the auxiliary store (src/boot.s ld_claim): the ProDOS
; bitmap (24 bytes), the RESET vector (3) and the /RAM unit it claimed ($x0,
; 1 none), then ProDOS's QUIT code, $D100-$D3FF of bank 2 of the main
; language card, where the game runs five routines of the view (src/dhgr.s
; B2_ENTRY). prodos_restore copies it to EX_BUF, the main half of the DHGR
; page, free once the text page is shown, and the QUIT code back to bank 2.
EX_ENTRY  = 2
EX_BUF    = $2000
EX_BITMAP = EX_BUF
EX_RESET  = EX_BUF + 24
EX_RAM    = EX_BUF + 27
EX_STATE  = 28
EX_QUIT   = EX_BUF + EX_STATE
EX_SIZE   = EX_STATE + $300
.export EX_STATE, EX_SIZE

; module_reset_exit -- (reset_exit) restore, then QUIT.
module_reset_exit:
        jsr     prodos_restore
; prodos_quit -- MLI QUIT to ProDOS's launcher.
prodos_quit:
        lda     #$65            ; QUIT
        ldx     #<quit_parms
        ldy     #>quit_parms
        jsr     mli_call
@halt:  jmp     @halt           ; QUIT never returns
quit_parms: .byte 4, 0, 0, 0, 0, 0, 0

; prodos_restore -- (module_restart, module_reset_exit) main banks, ROM,
; 40-column text page 1, the empty /RAM disk, bitmap, RESET vector and zero
; page as the loader found them. module_restart then reads NEOWILD.SYSTEM.
prodos_restore:
        ldx     #ZP_ENTRY       ; ProDOS's zero page, kept in auxiliary $BF00,
        jsr     mem_fetch       ; back to saved_zp ($BE00: HICODE is done)
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
        ldx     #EX_ENTRY       ; the loader's state, into EX_BUF
        jsr     mem_fetch
        ldx     #23
:       lda     EX_BITMAP,x
        sta     PD_BITMAP,x
        dex
        bpl     :-
        ldx     #2
:       lda     EX_RESET,x
        sta     SOFTEV,x
        dex
        bpl     :-
        bit     LCRAM2W         ; bank 2, read and write: the QUIT code back
        bit     LCRAM2W
        ldx     #0
:       lda     EX_QUIT,x
        sta     $D100,x
        lda     EX_QUIT+$100,x
        sta     $D200,x
        lda     EX_QUIT+$200,x
        sta     $D300,x
        inx
        bne     :-
        bit     LCROM
        lda     EX_RAM          ; the /RAM disk again, empty: FORMAT through
        cmp     #2              ; its driver at $FF00 in bank 1 (as
        bcc     @zp             ; dev/lib/prodos mli.s _prodos_format_ram;
        sta     $43             ; $42-$47 are ProDOS's, restored below). Its
                                ; buffer is $2000: EX_BUF is read by then
        lda     #3
        sta     $42
        lda     #0
        sta     $44
        sta     $46
        sta     $47
        lda     #$20
        sta     $45
        php
        sei
        bit     LCBANK1
        bit     LCBANK1
        jsr     $FF00
        bit     LCROM
        plp
@zp:
        ldx     #0
:       lda     saved_zp,x
        sta     $00,x
        inx
        bne     :-
        bit     KBDSTRB
        rts
.export prodos_restore, prodos_quit

.segment "RESCODE"
; verb_extra -- (the grid, src/menu.s build_verbs) C set when the condition
; of verb entry gp2 (context bits 5-7, menu.s X_*) holds here. Keeps gp2.
verb_extra:
        lda     gp2
        pha
        lda     gp2+1
        pha
        ldy     #1
        lda     (gp2),y
        and     #$E0
        beq     @yes            ; (X_FIRE: build_verbs)
        cmp     #$E0            ; X_FORAGE (lot 4): its object here
        bne     :+
        jsr     forage_menu
        jmp     @done
:       cmp     #$40            ; X_SWIM: in water, or water ahead
        bne     :+
        jsr     water_bits
        and     #3
        cmp     #1
        jmp     @done
:       cmp     #$C0            ; X_WALK: neither (one cell: WALK or SWIM)
        bne     :+
        jsr     water_bits
        and     #3
        bne     @no
        beq     @yes
:       cmp     #$A0            ; X_LOWER: the backpack hung on this cell
        bne     :+
        jsr     lower_ok
        jmp     @done
:       pha                     ; X_CLIMB, X_HANG: a tree here?
        jsr     tree_ok
        pla
        jsr     tree_verb       ; (HICODE)
        jmp     @done
@yes:   sec
        .byte   $24             ; BIT zp: skips the CLC
@no:    clc
@done:  pla
        sta     gp2+1
        pla
        sta     gp2
        rts


.segment "HICODE"
; tree_verb -- (verb_extra) A = X_CLIMB ($60) or X_HANG ($80), C = a tree
; stands here (tree_ok): C set for CLIMB TREE, HANG FOOD with the backpack
; carried, not hung, and for CLIMB from a tree (CLIMB DOWN).
tree_verb:
        bcs     @tree
        cmp     #$60
        bne     @no
        lda     tree_in
        bne     @yes
@no:    clc
        rts
@tree:  cmp     #$80
        bne     @yes
        lda     it_place+21
        cmp     #5
        beq     @no
        ldx     #21
        jmp     have
@yes:   sec
        rts
