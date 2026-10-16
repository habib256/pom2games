; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; boot.s -- NEOWILD.SYSTEM, the ProDOS 8 system program of Neowilderness
; ============================================================================
; ProDOS loads this file at $2000. The stub saves ProDOS's zero page and
; decodes the loader (LZ-packed by tools/build_disk.py) into the SIM window
; ($9600), free until the first simulation copy.
; The loader then:
;   - refuses machines other than an enhanced IIe / IIc with 128 KB, with a
;     message and a clean return to ProDOS;
;   - keeps the introduction on the text screen while it preloads the
;     common trunk NEOWILD.DAT;
;   - shows the start menu (lot 7): scenarios 1-6, 7 free journey, P journey
;     preparation (fidelity lot 1), H hall of fame, Q ProDOS, then the level
;     1-10 (RETURN = 4);
;   - shows the introduction again with the chosen region and reads its pack
;     (same records, same loop) from NEOWILD.DAT, behind the trunk at the
;     mark build_disk.py writes into ld_marks (one file since the memory
;     reclaim of docs/MEMORY.md 13: six pack files cost six index blocks
;     and six partial blocks): map, woods, animal sprites,
;     module directory, DHGR tables, fauna records and region texts;
;   - writes the level (MAP+22) and the journey kind (MAP+33 and the
;     resident journey_kind, which NEOWILD.END reads: TRAVEL reuses MAP+28..33
;     for the wild food quantities; 0 scenario, 1 free journey, whose random
;     generators are reseeded from the time spent in the menu);
;   - a journey other than a scenario at level 4 (the original's first
;     journey, the frozen state) reads the preparation (the last part of
;     NEOWILD.DAT, ld_marks) at $2000 and runs it
;     (src/prepare.s): P asks the original's preparation questions, every
;     such journey draws the level's crash injury, wreck lot, date, weather
;     front and wind (docs/SCENARIOS.md section 11);
;   - reads NEOWILD.DAT sequentially: records for main RAM, auxiliary RAM
;     ($0800-$1FFF, $4000-$BFFF) and the auxiliary language card, raw or LZ
;     (tools/pack_boot.py), decoded through main staging buffers;
;   - takes the auxiliary memory when the CLAIM record arrives (ld_claim:
;     the claim of dev/lib/prodos/video.s, here, so that the game keeps no
;     start-only code). Policy: an empty /RAM is discarded, a /RAM holding
;     files is erased only after Y; the empty disk is rebuilt at exit (FORMAT
;     of its driver: memory.s prodos_restore, or ld_format here);
;   - marks the game pages in the ProDOS bitmap, points RESET at reset_exit
;     and starts the game (start: stack, video switches, game_start).
; NEOWILD.DAT: the trunk, the six packs, the preparation; the trunk and each
; pack are a 256-byte table of records, read once to TABLE, then the
; payloads back to back: one MLI READ per record.
; Record: kind, address, length, stored length (little-endian words).
;   kind 0 end, 1 claim, else $80 + $40 (LZ) + bank (0 main, 1 auxiliary,
;   2 auxiliary language card bank 2, 3 bank 1; + $20: main language card,
;   bank 2 only, lot 7). Stored data <= 8 KB.
; The staging buffer is HGR page 1 ($2000); LZ data for auxiliary RAM is
; decoded at $7000 first, before WILDMAP is loaded there.
; ============================================================================
        .include "apple2.inc"
        .include "mousetext.inc" ; XL_IMM (docs/MENUS.md 9)
        .macpack longbranch
.import game_start, mem_ready, reset_exit, ui_poll
.importzp EX_STATE
.import mli_calls, mli_reads, mli_bytes, saved_zp
.export start
.import geo_path, weather_seed, fauna_rng, water_rng, journey_kind
.import rb_parms, rb_unit, mf_dst, mf_src
.import __LOADER_LOAD__, __LOADER_RUN__, __LOADER_SIZE__
.import __LOADBSS_RUN__, __LOADBSS_SIZE__, __RESBSS_RUN__, __RESBSS_SIZE__
.import __BSS_RUN__, __BSS_SIZE__
.export loader_main, loader_claimed, loader_done, loader_ram_files, ld_decode, ld_decode_end
.export loader_menu, menu_key, loader_pack, ld_region, ld_level, ld_free, ld_close
.export ld_prep, ld_entropy, ld_print, ld_place, ld_hdr, ld_move_src, loader_prepare, ld_menu_key
.import prepare, __PREPARE_LOAD__, __PREPARE_SIZE__

MLI      = $BF00
DEVNUM   = $BF30
DEVCNT   = $BF31
DEVLST   = $BF32
BITMAP   = $BF58
MACHID   = $BF98
INIT     = $FB2F
SETVID   = $FE93
SETKBD   = $FE89
STAGE    = $2000
TEMP     = $7000
TABLE    = $B500                ; record table of NEOWILD.DAT / NEOWILD.Rn
LD_IOBUF = $B000                ; ProDOS I/O buffer of the loader's files: between
                                ; its BSS and TABLE, so that $BA00-$BDFF (the
                                ; game's io_buffer) receives a record (menu.s)
CLREOP   = $FC42
MAP      = $7000
MENU_ROW = 12                   ; prompts below the menu (tools/genmenu.py MENU_ROW)
TABLE_SIZE = 256                ; tools/build_disk.py TABLE_SIZE (36 records)
PRE_PACK = $3000                ; packed NEOWILD.PRE (<= 4 KB; tools/build_disk.py)
HI_LOAD  = $5E00                ; HICODE's record (tools/build_disk.py), moved to $BE00
                                ; ($AA00 until docs/MEMORY.md 15: the module window,
                                ; which no record and no loader code touches and
                                ; the game fills before use, gives the loader that
                                ; page; not SCRATCH $9500, whose bytes the game
                                ; reads at start, tests/test_reference_state.py)
                                ; ($A900 until the NEOWILD.BLK check, docs/MEMORY.md 14)
ZP_AUX   = $BF00                ; auxiliary: ProDOS's zero page during the game
ALTZPOFF = $C008
ALTZPON  = $C009
RAMWRTON = $C005
LCROM    = $C082
LCBANK2  = $C083                ; read and write RAM bank 2 (twice)
LCRAM2R  = $C080                ; read RAM bank 2, write protected
QUIT_CODE = $D100               ; ProDOS 8's QUIT code in bank 2 ($300 bytes)
RAMRDON  = $C003
LCBANK1  = $C08B

.segment "ZEROPAGE"
source: .res 2
dest:   .res 2
match:  .res 2
remain: .res 2
flags:  .res 1
bits:   .res 1
offset: .res 1
length: .res 1

.assert __LOADBSS_RUN__ + __LOADBSS_SIZE__ <= TABLE, lderror, "loader overlaps its record table"
.assert __LOADBSS_RUN__ + __LOADBSS_SIZE__ <= LD_IOBUF, lderror, "loader overlaps its I/O buffer"
.assert HI_LOAD + $100 <= __LOADER_RUN__, lderror, "HICODE's record overlaps the loader"
.segment "SYSSTUB"
        cld
        ldx     #0              ; ProDOS's zero page before touching any
:       lda     $00,x
        sta     saved_zp,x
        inx
        bne     :-
        ; The loader follows, LZ-packed by tools/build_disk.py (system_file:
        ; tools/pack_boot.py tokens, a match of distance 0 at the end; two
        ; blocks fewer on the volume, docs/MEMORY.md 13): decode it into the
        ; SIM window, its run address.
        lda     #<__LOADER_LOAD__
        sta     source
        lda     #>__LOADER_LOAD__
        sta     source+1
        lda     #<__LOADER_RUN__
        sta     dest
        lda     #>__LOADER_RUN__
        sta     dest+1
        ldy     #0
        lda     #1              ; empty: the first token reads a flag byte
        sta     flags
@token: lsr     flags
        bne     @flag
        jsr     @byte           ; eight flags, a sentinel bit behind them
        sec
        ror     a
        sta     flags
@flag:  jsr     @byte           ; C: the token's flag (@byte keeps it)
        bcs     @match
        sta     (dest),y        ; literal
        inc     dest
        bne     @token
        inc     dest+1
        bcc     @token          ; always
@match: sta     offset
        jsr     @byte
        sta     length
        ora     offset
        beq     @done           ; distance 0: the end
        lda     length
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        sta     match+1
        sec
        lda     dest
        sbc     offset
        sta     match
        lda     dest+1
        sbc     match+1
        sta     match+1
        lda     length
        and     #15
        adc     #2              ; C set (no borrow): length 3..18
        cmp     #18
        bne     :+
        jsr     @byte
        clc
        adc     #18
:       tax
@copy:  lda     (match),y
        sta     (dest),y
        iny
        dex
        bne     @copy
        tya
        clc
        adc     dest
        sta     dest
        bcc     :+
        inc     dest+1
:       ldy     #0
        beq     @token
@done:  ldx     #length-source  ; its zero page back as ProDOS left it:
:       lda     saved_zp+source,x ; the loader starts on the entry state
        sta     source,x
        dex
        bpl     :-
        jmp     loader_main
@byte:  lda     (source),y
        inc     source
        bne     :+
        inc     source+1
:       rts

.segment "LOADBSS"
hdr:    .res 7
kind    = hdr
address = hdr+1
size    = hdr+3
stored  = hdr+5
claimed: .res 1
unit:   .res 1
volume: .res 16
ld_path: .res 40
key:    .res 1
ld_region: .res 1               ; 1..6
ld_level:  .res 1               ; 1..10
ld_free:   .res 1               ; 1: free journey (not ranked, random seeds)
digits:    .res 1
entropy:   .res 2               ; key-wait iterations in the menu
ld_prep:   .res 1               ; 1: P, the preparation questions (with ld_free)
ld_tmap:   .res 1               ; XL only: separate TMAP + scenario data pack
ld_part:   .res 1               ; ld_open: part of NEOWILD.DAT
; The state to restore at exit (docs/MEMORY.md 15), in the layout of
; memory.s EX_*: copied at the claim to the store's entry EX_ENTRY, where the
; game's exit path (INPUT prodos_restore) finds it.
ex_state:
saved_bitmap: .res 24           ; ProDOS bitmap at entry
saved_reset:  .res 3            ; RESET vector at entry
ram_unit:     .res 1            ; /RAM unit claimed ($x0), 1 none
.assert * - ex_state = EX_STATE, error, "exit state layout: memory.s EX_*"
ld_entropy = entropy
ld_hdr     = hdr

.segment "LOADER"
loader_main:
        ldx     #0              ; resident counters and loader state
        txa
:       sta     __RESBSS_RUN__,x
        inx
        cpx     #<__RESBSS_SIZE__
        bne     :-
        .assert __RESBSS_SIZE__ < 256, error, "RESBSS too large"
        ldx     #0
:       sta     __LOADBSS_RUN__,x
        inx
        cpx     #<__LOADBSS_SIZE__
        bne     :-
        .assert __LOADBSS_SIZE__ < 256, error, "LOADBSS too large"
        ldx     #2
:       lda     SOFTEV,x
        sta     saved_reset,x
        dex
        bpl     :-
        ldx     #23
:       lda     BITMAP,x
        sta     saved_bitmap,x
        dex
        bpl     :-
        ; Plain 40-column text page 1, Monitor I/O hooks.
        sta     STORE80OFF
        sta     COL80OFF
        XL_IMM  XI_LOADER, $0F, @x43  ; (XL, docs/MENUS.md 9: ALTCHARSET, MouseText,
        sta     $C00E           ; for the whole game) primary character set
        bit     LCROM
        jsr     SETVID
        jsr     SETKBD
        jsr     INIT
        jsr     HOME
        ; Enhanced IIe or IIc ($FBB3 = 6, $FBC0 = $E0 / $00), 128 KB.
        lda     MACHID
        and     #$30
        cmp     #$30
        bne     @refuse
        lda     $FBB3
        cmp     #$06
        bne     @refuse
        lda     $FBC0
        beq     @machine_ok
        cmp     #$E0
        beq     @machine_ok
@refuse:
        lda     #<m_machine
        ldy     #>m_machine
        jsr     print
        jmp     ld_key_quit
@machine_ok:
        lda     #<m_intro
        ldy     #>m_intro
        jsr     print
        lda     #<m_loading
        ldy     #>m_loading
        jsr     print
        ; Full pathnames on the boot volume (as CHROMA.SYSTEM does).
        lda     DEVNUM
        sta     online+1
        sta     rb_unit         ; memory.s disk_fetch reads the boot unit
        lda     #$C5            ; ONLINE
        ldx     #<online
        ldy     #>online
        jsr     ld_mli
        jcs     ld_error
        lda     volume
        and     #$0F
        jeq     ld_error
        sta     volume
        ; Docs/MEMORY.md 14 (NeoWildernessXL): the game reads modules of
        ; NEOWILD.BLK by block number. Its first block must hold the
        ; signature build_disk.py wrote in ld_blk: a file-by-file copy
        ; moves the blocks, and the game would read another file's.
        lda     ld_blk
        beq     @blk_ok         ; no NEOWILD.BLK (block 0: the 140 KB edition)
        sta     mf_src
        lda     ld_blk+1
        sta     mf_src+1
        lda     #<STAGE
        sta     mf_dst
        lda     #>STAGE
        sta     mf_dst+1
        lda     #3
        sta     rb_parms
        lda     #$80            ; READ_BLOCK
        ldx     #<rb_parms
        ldy     #>rb_parms
        jsr     ld_mli
        jcs     ld_error
        ldx     #5
:       lda     STAGE,x
        cmp     ld_blk+2,x
        bne     @blk_moved
        dex
        bpl     :-
        bmi     @blk_ok
@blk_moved:
        lda     #<m_moved
        ldy     #>m_moved
        jsr     print
        jmp     ld_key_quit
@blk_ok:
        ldx     #<geo_path
        ldy     #>geo_path
        lda     #'G'
        jsr     make_path
        ldx     #0              ; the common trunk
        jsr     load_file
        jcs     ld_error
        jsr     hm_load         ; NEOWILD.HOF into STAGE (empty table if absent)
loader_menu:
        jsr     menu            ; ld_region, ld_level, ld_free
        jsr     HOME            ; the introduction again, with the journey
        lda     #<m_intro
        ldy     #>m_intro
        jsr     print
        lda     ld_tmap
        beq     :+
        lda     #<m_archipelago
        ldy     #>m_archipelago
        jsr     print
        jmp     @intro_level
:       ldx     ld_region
        lda     region_names_lo-1,x
        ldy     region_names_hi-1,x
        jsr     print
@intro_level:
        lda     #<m_level
        ldy     #>m_level
        jsr     print
        lda     ld_level
        jsr     print_level
        lda     ld_free
        beq     :+
        lda     #<m_free
        ldy     #>m_free
        jsr     print
:       lda     #<m_loading
        ldy     #>m_loading
        jsr     print
loader_pack:
        ldx     ld_region       ; the pack of the region, behind the trunk
        lda     ld_tmap
        beq     :+
        ldx     #8              ; NEOWILD.SCN: scenario, independent of engine
:
        jsr     load_file
        jcs     ld_error
        lda     ld_tmap
        beq     @journey
        ldx     #9              ; NEOWILD.TMP: start-only generator at $2000
        jsr     load_file
        jcs     ld_error
        lda     entropy
        ldx     entropy+1
        ldy     ld_level
        jsr     $2000
        jcs     loader_menu
@journey:
        lda     ld_level        ; the journey's own header bytes
        sta     MAP+22
        lda     ld_free
        sta     MAP+33
        sta     journey_kind    ; NEOWILD.END: MAP+33 holds STICKS once walking
        beq     @protect
        lda     entropy         ; free journey: new weather, fauna and
        ora     entropy+1       ; water sequences (never a zero state)
        beq     @protect
        lda     entropy
        sta     weather_seed
        lda     entropy+1
        sta     weather_seed+1
        lda     entropy
        ora     #1
        sta     fauna_rng
        lda     entropy+1
        ora     #$40
        sta     water_rng
@protect:
        lda     ld_free         ; the frozen first journey: scenario, level 4
        bne     loader_prepare
        lda     ld_level
        cmp     #4
        beq     ld_no_prepare
loader_prepare:                 ; the preparation: LZ (tools/pack_boot.py)
        ldx     #7              ; read at PRE_PACK, decoded to $2000 (STAGE,
        jsr     ld_open         ; free until ld_scatter), then src/prepare.s
        jcs     ld_error
        lda     #>PRE_PACK
        sta     read+3
        sta     source+1
        lda     #0
        sta     read+2
        sta     source
        lda     ld_marks+21     ; its stored length
        sta     read+4
        lda     ld_marks+22
        sta     read+5
        lda     #$CA
        ldx     #<read
        ldy     #>read
        jsr     ld_mli
        jcs     ld_error
        lda     #$CC            ; CLOSE
        ldx     #<close
        ldy     #>close
        jsr     ld_mli
        lda     #<__PREPARE_SIZE__
        sta     size
        lda     #>__PREPARE_SIZE__
        sta     size+1
        lda     #<__PREPARE_LOAD__
        ldx     #>__PREPARE_LOAD__
        jsr     ld_decode_at    ; behind the packed data, which stays ahead
        jsr     prepare
ld_no_prepare:
        jsr     ld_scatter      ; before the zero page is set for the game
        ; docs/MEMORY.md 13: ProDOS's zero page (saved_zp, $BE00) is kept in
        ; auxiliary $BF00-$BFFF for the game (memory.s ZP_ENTRY); $BE00
        ; receives HICODE, read with the trunk at HI_LOAD.
        ldx     #0
        sta     RAMWRTON
:       lda     saved_zp,x
        sta     ZP_AUX,x
        inx
        bne     :-
        sta     RAMWRTOFF
:       lda     HI_LOAD,x
        sta     saved_zp,x
        inx
        bne     :-
        ldx     #23             ; protect the game's pages
:       lda     saved_bitmap,x
        ora     game_pages,x
        sta     BITMAP,x
        dex
        bpl     :-
        lda     #<reset_exit
        sta     SOFTEV
        lda     #>reset_exit
        sta     SOFTEV+1
        eor     #$A5
        sta     SOFTEV+2
        ldx     #$1F            ; the Applesoft environment of the reference
:       lda     applesoft_lo,x
        sta     $00,x
        dex
        bpl     :-
        ldx     #0
:       lda     applesoft_hi,x
        sta     $50,x
        inx
        cpx     #$B0
        bne     :-
loader_done:
; start -- the game's entry, start-only, so kept here (docs/MEMORY.md 15):
; a fresh stack, mem_ready, and the switches dev/lib native_video sets (main
; RAMRD/RAMWRT, 80STORE, 80COL and DHGR off; the machine was checked above).
start:  cld
        ldx     #$FF
        txs
        lda     #1
        sta     mem_ready
        sta     RAMRDOFF
        sta     RAMWRTOFF
        sta     STORE80OFF
        sta     COL80OFF
        bit     DHIRES_OFF
        ; XL: ALTCHARSET again, after the Monitor's SETVID, INIT, HOME and
        ; the menu (the IIc's SETVID turns it off: STATUS, the grid then
        ; showed inverse letters instead of MouseText; 15 October 2026).
        XL_IMM  XI_LOADER, $0F, @x44
        sta     $C00E           ; 140 KB: the primary set, as before
        jmp     game_start

; ld_scatter -- the grid of the menu (menu.s MENUSWAP), read at SWAP_LOAD,
; into the HGR rows 176-191 of both banks: 16 chunks of 48 bytes (holes
; included) per bank, row 176 + 8g at SWAP_ROW + $400 g and row 184 + 8g
; $80 further; the main bank, then the auxiliary one through RAMWRT
; (80STORE off meanwhile: the page is not displayed yet). The game copies
; it back at every prompt (menu_gather) and never draws those rows.
SWAP_LOAD = $5800               ; tools/build_disk.py: the record's address
.assert SWAP_LOAD + $600 <= HI_LOAD, error, "menu staging overlaps HICODE"
.assert HI_LOAD + $100 <= __LOADER_RUN__, lderror, "HICODE overlaps loader"
.assert __LOADBSS_RUN__ + __LOADBSS_SIZE__ <= LD_IOBUF, lderror, "loader overlaps ProDOS buffer"
.assert LD_IOBUF + $400 <= TABLE, error, "ProDOS buffer overlaps record table"
SWAP_ROW  = $2350               ; menu.s SWAP_ROW
RD80STORE = $C018
ld_scatter:
        lda     RD80STORE
        pha
        sta     STORE80OFF
        lda     #<SWAP_LOAD
        sta     source
        lda     #>SWAP_LOAD
        sta     source+1
        jsr     @bank
        sta     RAMWRTON
        jsr     @bank
        sta     RAMWRTOFF
        pla
        bpl     :+
        sta     STORE80ON
:       rts
@bank:  lda     #<SWAP_ROW
        sta     dest
        lda     #>SWAP_ROW
        sta     dest+1
        ldx     #16
@chunk: ldy     #47
:       lda     (source),y
        sta     (dest),y
        dey
        bpl     :-
        lda     source
        clc
        adc     #48
        sta     source
        bcc     :+
        inc     source+1
:       lda     dest            ; $50 -> $D0 (same group), $D0 -> $50 (next)
        eor     #$80
        sta     dest
        bmi     :+
        lda     dest+1
        clc
        adc     #4
        sta     dest+1
:       dex
        bne     @chunk
        rts

; ld_open -- open NEOWILD.DAT, then SET_MARK to part X of ld_marks: 0 the
; trunk (no SET_MARK), 1..6 the packs, 7 the preparation. C set, A = error.
ld_open:
        stx     ld_part
        lda     #'D'
        cpx     #8
        bcc     :+
        lda     #'S'
        cpx     #8
        beq     :+
        lda     #'T'
:
        ldx     #<ld_path
        ldy     #>ld_path
        jsr     make_path
        lda     #$C8            ; OPEN
        ldx     #<open
        ldy     #>open
        jsr     ld_mli
        bcs     @done
        lda     open+5
        sta     read+1
        sta     close+1
        sta     mark+1
        lda     ld_part
        beq     @done           ; C clear
        cmp     #8
        bcc     :+
        clc
        rts                     ; separate file, no DAT mark
:
        asl     a
        adc     ld_part
        tax
        lda     ld_marks-3,x
        sta     mark+2
        lda     ld_marks-2,x
        sta     mark+3
        lda     ld_marks-1,x
        sta     mark+4
        lda     #$CE            ; SET_MARK
        ldx     #<mark
        ldy     #>mark
        jmp     ld_mli
@done:  rts

; load_file -- X = part of NEOWILD.DAT (ld_open): read its record table,
; then every record; close. C set, A = MLI error.
load_file:
        jsr     ld_open
        bcc     :+
        rts
:       lda     #<TABLE         ; one READ for the whole record table
        ldx     #>TABLE
        ldy     #<TABLE_SIZE
        sty     stored
        ldy     #>TABLE_SIZE
        sty     stored+1
        jsr     read_size
        bcc     :+
        rts
:       lda     #<TABLE
        sta     record_hdr+1
        lda     #>TABLE
        sta     record_hdr+2
record:
        ldy     #6
record_hdr:
        lda     TABLE,y         ; patched: walks the table
        sta     hdr,y
        dey
        bpl     record_hdr
        clc
        lda     record_hdr+1
        adc     #7
        sta     record_hdr+1
        bcc     :+
        inc     record_hdr+2
:       lda     kind
        beq     ld_close
        cmp     #1
        bne     @data
        jsr     ld_claim
        jmp     record
@data:
        and     #$43
        bne     @staged
        lda     address         ; main raw: straight to its destination
        ldx     address+1
        ldy     #0
        jsr     read_size
        bcc     record
        rts
@staged:
        lda     #<STAGE
        ldx     #>STAGE
        ldy     #0
        jsr     read_size
        bcc     :+
        rts
:       lda     #<STAGE
        sta     move_src
        lda     #>STAGE
        sta     move_src+1
        bit     kind
        bvc     @placed
        lda     kind            ; LZ: main destination directly, else TEMP
        and     #3
        bne     @temp
        lda     address
        ldx     address+1
        jsr     ld_decode
        jmp     record
@temp:  lda     #<TEMP
        ldx     #>TEMP
        sta     move_src
        stx     move_src+1
        jsr     ld_decode
@placed:
        jsr     ld_place
        jmp     record
ld_close:                       ; tests/test_hof_volume.py: the CLOSE of each file
        lda     #$CC            ; CLOSE
        ldx     #<close
        ldy     #>close
        jmp     ld_mli

; ----------------------------------------------------------------------------
; menu -- the start menu on the 40-column text page 1, through the Monitor.
; Sets ld_region (1-6), ld_level (1-10) and ld_free. Q leaves to ProDOS.
menu:
        lda     #0
        sta     ld_nav_mode
        sta     ld_nav_cur
        sta     ld_free
        sta     ld_prep
        sta     ld_tmap
        jsr     HOME
        ldx     #0              ; the parts of the edition's menu
        lda     ld_regions      ; (tools/genmenu.py menu_xl, menu_1)
        cmp     #1
        bne     @part
        lda     #'/'            ; one scenario: "1/7" in the prompt
        sta     m_choice+21
        ldx     #menu_1-menu_xl
@part:  lda     menu_xl,x
        ldy     menu_xl+1,x
        beq     @parts          ; a 0 word ends the list
        stx     key
        jsr     print
        ldx     key
        inx
        inx
        bne     @part
@parts:
        jsr     hm_best
@ask:   lda     #0
        sta     ld_nav_mode
        sta     ld_nav_cur
        lda     #<m_choice
        ldy     #>m_choice
        jsr     prompt
@key:   jsr     menu_key
        cmp     #KC_RET|$80
        bne     :+
        ldx     ld_nav_cur
        lda     ld_nav_keys,x
        ora     #$80
        jmp     @nav_choice
@nav_choice:
        cmp     #'1'|$80
        bcc     @other
        cmp     #'7'|$80
        bcc     @choose
        beq     @free
        jmp     @other
:       cmp     #'1'|$80
        bcc     @other
        cmp     #'7'|$80
        bcc     @choose
        bne     @other
@free:  inc     ld_free         ; 7: free journey, then its region
        ldx     ld_regions      ; one scenario: no region to ask
        dex
        bne     :+
        lda     #'1'|$80
        jmp     @scen_key
:       lda     #<m_region
        ldy     #>m_region
@ask_region:
        jsr     prompt
        lda     #1
        sta     ld_nav_mode
        sta     ld_nav_cur
@region:
        jsr     menu_key
        cmp     #KC_RET|$80
        bne     :+
        lda     ld_nav_cur
        ora     #'0'|$80
:       cmp     #KC_ESC|$80
        bne     :+
        lda     #0
        sta     ld_free
        sta     ld_prep
        jmp     @ask
:       cmp     #'1'|$80
        bcc     @bad_region
        cmp     #'7'|$80
        bcc     @scenario
@bad_region:
        jsr     BELL
        jmp     @region
@choose:
        ldx     ld_regions      ; a scenario key the edition has
        dex
        bne     @scenario
        cmp     #'2'|$80
        bcc     @scenario
        bcs     @bad
@other: cmp     #'T'|$80
        bne     @preparation
        lda     ld_regions
        cmp     #6
        bne     @bad
        inc     ld_tmap
        inc     ld_free
        lda     #4              ; compatibility environment of the data pack
        sta     ld_region
        jmp     @level
@preparation:
        cmp     #'P'|$80
        bne     :+
        inc     ld_prep         ; P: a free journey with the questions
        bne     @free           ; (after the pack, src/prepare.s)
:       cmp     #'H'|$80
        beq     @hall
        cmp     #'Q'|$80
        bne     @bad
        jmp     ld_quit
@bad:   jsr     BELL
        jmp     @key
@hall:  jsr     hm_hall
        jsr     menu_key
        jmp     menu
@scenario:
        jsr     COUT            ; echo the digit (COUT keeps A)
@scen_key:
        and     #$0F
        tax
        lda     menu_regions-1,x ; menu key -> region (tools/genmenu.py)
        sta     ld_region
; level -- 1..10, RETURN alone = 4, ESC back to the choice.
@level: lda     #2
        sta     ld_nav_mode
        lda     #4
        sta     ld_nav_cur
        lda     #<m_ask_level
        ldy     #>m_ask_level
        jsr     prompt
        lda     #0
        sta     digits
        sta     ld_level
@lkey:  jsr     menu_key
        cmp     #KC_RET|$80
        beq     @enter
        cmp     #KC_ESC|$80
        bne     :+
        lda     #0
        sta     ld_free
        sta     ld_prep
        sta     ld_tmap
        jmp     @ask
:       cmp     #'0'|$80
        bcc     @lbad
        cmp     #'9'|$80+1
        bcs     @lbad
        ldx     digits
        cpx     #2
        bcs     @lbad
        inc     digits
        jsr     COUT
        and     #$0F
        sta     key
        lda     ld_level        ; level = 10 * level + digit
        asl     a
        asl     a
        adc     ld_level
        asl     a
        adc     key
        sta     ld_level
        jmp     @lkey
@enter: lda     digits
        bne     :+
        lda     ld_nav_cur
        sta     ld_level
        rts
:       lda     ld_level
        beq     @wrong
        cmp     #11
        bcs     @wrong
        rts
@wrong: jsr     BELL
        jmp     @level
@lbad:  jsr     BELL
        jmp     @lkey

; prompt -- A/Y = text on row MENU_ROW, rows below cleared.
prompt: sta     @text+1
        sty     @text+3
        lda     #MENU_ROW
        sta     CV
        jsr     VTAB
        lda     #0
        sta     CH
        jsr     CLREOP
@text:  lda     #0
        ldy     #0
        jmp     print

; menu_key -- wait for a key (A = key | $80, letters in upper case). The
; iterations feed the free journey's seeds. Tests stop here (tests/common.py).
menu_key:
        inc     entropy
        bne     :+
        inc     entropy+1
:       jsr     ui_poll
        beq     menu_key
        cmp     #KC_UP
        beq     ld_nav_prev
        cmp     #KC_LEFT
        beq     ld_nav_prev
        cmp     #KC_DOWN
        beq     ld_nav_next
        cmp     #KC_RIGHT
        beq     ld_nav_next
        ora     #$80
        rts
ld_nav_prev:
        ldx     ld_nav_cur
        dex
        lda     ld_nav_mode
        bne     :+
        lda     ld_regions
        cmp     #1
        bne     :+
        cpx     #5
        bne     :+
        ldx     #0
:       lda     ld_nav_mode
        bne     :+
        cpx     #$FF
        bne     ld_nav_set
        ldx     #9
        lda     ld_regions
        cmp     #1
        beq     ld_nav_set
        inx
        bne     ld_nav_set
:       cpx     #0
        bne     ld_nav_set
        ldx     #6
        cmp     #1
        beq     ld_nav_set
        ldx     #10
        bne     ld_nav_set
ld_nav_next:
        ldx     ld_nav_cur
        inx
        lda     ld_nav_mode
        bne     :+
        lda     ld_regions
        cmp     #1
        bne     @xl
        cpx     #10
        bcc     ld_nav_set
        bcs     @wrap
@xl:    cpx     #11
        bcc     ld_nav_set
@wrap:
        ldx     #0
        beq     ld_nav_set
:       cpx     #7
        bcc     ld_nav_set
        cmp     #1
        beq     ld_nav_first
        cpx     #11
        bcc     ld_nav_set
ld_nav_first:
        ldx     #1
ld_nav_set:
        stx     ld_nav_cur
        lda     ld_nav_mode
        bne     ld_nav_draw
        lda     ld_regions
        cmp     #1
        bne     ld_nav_draw
        cpx     #1
        bcc     ld_nav_draw
        cpx     #6
        bcs     ld_nav_draw
        ldx     #6
        stx     ld_nav_cur
ld_nav_draw:
        lda     #MENU_ROW+2
        sta     CV
        jsr     VTAB
        lda     #0
        sta     CH
        jsr     $FC9C
        lda     #<ld_nav_hint
        ldy     #>ld_nav_hint
        jsr     print
        ldx     ld_nav_cur
        lda     ld_nav_mode
        bne     :+
        lda     ld_nav_keys,x
        ora     #$80
        jsr     COUT
        jmp     menu_key
:       txa
        jsr     print_level
        jmp     menu_key
ld_nav_keys: .byte "1234567PHQT"
ld_nav_hint: .byte "ARROWS CHOOSE, RETURN SELECT: ",0
ld_nav_mode: .byte 0
ld_nav_cur:  .byte 0

; print_level -- A = 1..10 in decimal.
print_level:
        cmp     #10
        bcc     :+
        lda     #'1'|$80
        jsr     COUT
        lda     #0
:       ora     #'0'|$80
        jmp     COUT

; make_path -- X/Y = destination, A = 'D' (NEOWILD.DAT) or 'G' (NEOWILD.GEO):
; length byte, "/VOLUME/NEOWILD.xxx".
make_path:
        stx     @dst+1
        sty     @dst+2
        stx     @len+1
        sty     @len+2
        sta     @kind+1
        ldy     #1
        lda     #'/'
        jsr     @put
        ldx     #0
:       lda     volume+1,x
        jsr     @put
        inx
        cpx     volume
        bne     :-
        ldx     #0
:       lda     file_name,x
        jsr     @put
        inx
        cpx     #file_suffix-file_name
        bne     :-
@kind:  lda     #0
        ldx     #2              ; DAT, GEO: the suffix ending at X
        cmp     #'D'
        beq     @suffix
        ldx     #5
        cmp     #'G'
        beq     @suffix
        ldx     #8
        cmp     #'S'
        beq     @suffix
        ldx     #11
@suffix:
        lda     #3
        sta     digits
:       lda     file_dat-2,x
        jsr     @put
        inx
        dec     digits
        bne     :-
        dey
        tya
@len:   sta     $FFFF
        rts
@put:
@dst:   sta     $FFFF,y
        iny
        rts


; read_to -- A/X = buffer, Y = count (< 256)
read_to:
        sta     read+2
        stx     read+3
        sty     read+4
        lda     #0
        sta     read+5
        jmp     read_now
; read_size -- A/X = buffer, the stored length of the record
read_size:
        sta     read+2
        stx     read+3
        lda     stored
        sta     read+4
        lda     stored+1
        sta     read+5
read_now:
        lda     #$CA            ; READ
        ldx     #<read
        ldy     #>read
        jsr     ld_mli
        bcs     @rts
        lda     read+6          ; a short READ is a damaged file
        cmp     read+4
        bne     @short
        lda     read+7
        cmp     read+5
        beq     @rts            ; carry set by the compare: clear it
@short: lda     #$4C            ; ProDOS "end of file"
        sec
        rts
@rts:   clc
        rts

; ld_mli -- the loader's MLI calls, counted like mli_call (memory.s).
ld_mli: sta     @cmd
        stx     @parm
        sty     @parm+1
        inc     mli_calls
        bne     :+
        inc     mli_calls+1
:       jsr     MLI
@cmd:   .byte   0
@parm:  .word   0
        bcs     @rts
        pha
        lda     @cmd
        cmp     #$80
        beq     @block
        cmp     #$CA
        bne     @done
        lda     read+6
        ldx     read+7
        jmp     @count
@block: lda     #0
        ldx     #2
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
        clc
@rts:   rts

; ld_place -- copy `size` bytes from move_src to `address` in the auxiliary
; bank of the record (1 auxiliary RAM, 2/3 auxiliary language card), or in
; bank 2 of the main language card (kind bit 5, lot 7: ALTZP stays off).
; While RAMWRT is on, stores to this code would reach auxiliary RAM: that
; loop uses main zero-page pointers. ALTZP swaps the zero page instead: the
; language-card loop patches its own absolute operands in main RAM.
ld_place:                       ; also src/prepare.s (patches of module images)
        lda     kind
        and     #3
        cmp     #1
        bne     @lc
        lda     move_src
        sta     source
        lda     move_src+1
        sta     source+1
        lda     address
        sta     dest
        lda     address+1
        sta     dest+1
        ldx     size+1
        ldy     #0
        php
        sei
        sta     RAMWRTON
        cpx     #0
        beq     @atail
@apage: lda     (source),y
        sta     (dest),y
        iny
        bne     @apage
        inc     source+1
        inc     dest+1
        dex
        bne     @apage
@atail: cpy     size
        beq     @aend
        lda     (source),y
        sta     (dest),y
        iny
        bne     @atail
@aend:  sta     RAMWRTOFF
        plp
        rts
@lc:    pha
        ldx     #<ALTZPON       ; kind bit 5: the MAIN language card (lot 7)
        lda     kind
        and     #$20
        beq     :+
        dex                     ; ALTZPOFF
:       stx     @zp+1
        lda     move_src
        sta     @src1+1
        sta     @src2+1
        lda     move_src+1
        sta     @src1+2
        sta     @src2+2
        lda     address
        sta     @dst1+1
        sta     @dst2+1
        lda     address+1
        sta     @dst1+2
        sta     @dst2+2
        lda     size
        sta     @rest+1
        ldx     size+1
        pla
        php
        sei
@zp:    sta     ALTZPON         ; no stack or zero page until ALTZPOFF
        cmp     #2
        bne     @bank1
        lda     LCBANK2
        lda     LCBANK2
        jmp     @go
@bank1: lda     LCBANK1
        lda     LCBANK1
@go:    ldy     #0
        cpx     #0
        beq     @tail
@page:
@src1:  lda     $FFFF,y
@dst1:  sta     $FFFF,y
        iny
        bne     @page
        inc     @src1+2
        inc     @dst1+2
        inc     @src2+2
        inc     @dst2+2
        dex
        bne     @page
@tail:
@rest:  cpy     #0
        beq     @end
@src2:  lda     $FFFF,y
@dst2:  sta     $FFFF,y
        iny
        bne     @tail
@end:   lda     LCROM
        sta     ALTZPOFF
        plp
        rts

; ld_decode -- LZ stream at STAGE (tools/pack_boot.py tokens) -> A/X, for
; `size` bytes. Overlapping matches copy forward through the output. Y stays
; 0 between tokens; the end is checked on the output pointer.
ld_decode:
        ldy     #<STAGE
        sty     source
        ldy     #>STAGE
        sty     source+1
ld_decode_at:                   ; source set by the caller (NEOWILD.PRE)
        sta     dest
        stx     dest+1
        clc
        adc     size
        sta     remain          ; remain = end address
        txa
        adc     size+1
        sta     remain+1
        ldy     #0
@group: lda     dest+1          ; end of output?
        cmp     remain+1
        bne     :+
        lda     dest
        cmp     remain
        bne     :+
        rts
:       lda     (source),y      ; eight flags, low bit first
        sta     flags
        inc     source
        bne     :+
        inc     source+1
:       lda     #8
        sta     bits
@token: lsr     flags
        bcs     @match
        lda     (source),y      ; literal
        inc     source
        bne     :+
        inc     source+1
:       sta     (dest),y
        inc     dest
        bne     @next
        inc     dest+1
@next:  lda     dest+1
        cmp     remain+1
        beq     @last
@more:  dec     bits
        bne     @token
        beq     @group
@last:  lda     dest
        cmp     remain
        bne     @more
        rts
@match: lda     (source),y      ; distance low, then distance high | length
        sta     offset
        iny
        lda     (source),y
        dey
        sta     length
        clc
        lda     source
        adc     #2
        sta     source
        bcc     :+
        inc     source+1
:       lda     length
        lsr
        lsr
        lsr
        lsr
        sta     match+1         ; distance high
        sec
        lda     dest
        sbc     offset
        sta     match
        lda     dest+1
        sbc     match+1
        sta     match+1
        lda     length
        and     #15
        clc
        adc     #3
        cmp     #18
        bne     :+
        lda     (source),y      ; extension byte
        inc     source
        bne     @ext
        inc     source+1
@ext:   clc
        adc     #18
:       tax
@copy:  lda     (match),y
        sta     (dest),y
        iny
        dex
        bne     @copy
        tya
        ldy     #0
        clc
        adc     dest
        sta     dest
        bcc     @next
        inc     dest+1
        jmp     @next
ld_decode_end:

; ld_claim -- the explicit /RAM policy and the claim of dev/lib/prodos/video.s
; (policy "discard"), kept here: the game's resident ram_unit gets the /RAM
; unit ($x0, its driver at $FF00), or 1 when there is none; a malformed
; device list is error 3, as video.s answers.
ld_claim:
        ldx     #0              ; the game BSS starts cleared
        txa
:       sta     __BSS_RUN__,x
        inx
        cpx     #<__BSS_SIZE__
        bne     :-
        .assert __BSS_SIZE__ < 256, error, "game BSS: extend the clear"
        ldy     DEVCNT          ; find /RAM as video.s does: driver $FF00
        cpy     #14
        bcc     ldc_scan
        iny                     ; $FF: no device, no /RAM
        beq     ldc_none
        lda     #3              ; malformed list
        jmp     ld_error
ldc_scan:  lda     DEVLST,y
        and     #$F0
        sta     unit
        lsr
        lsr
        lsr
        tax
        lda     $BF10,x
        bne     ldc_next
        lda     $BF11,x
        cmp     #$FF
        beq     ldc_found
ldc_next:  dey
        bpl     ldc_scan
ldc_none:  lda     #0              ; no /RAM
        sta     unit
        beq     ldc_claim
ldc_found: lda     unit            ; its volume directory: file count at $25
        sta     block+1
        lda     #$80            ; READ_BLOCK 2
        ldx     #<block
        ldy     #>block
        jsr     ld_mli
        bcs     ldc_claim          ; unreadable: nothing to preserve
loader_ram_files:
        lda     STAGE+$25
        ora     STAGE+$26
        beq     ldc_claim
        lda     #<m_ram
        ldy     #>m_ram
        jsr     print
        jsr     ld_wait
        cmp     #'Y'|$80
        beq     ldc_erase
        cmp     #'y'|$80
        jne     ld_quit
ldc_erase: lda     #<m_erase
        ldy     #>m_erase
        jsr     print
ldc_claim: lda     unit            ; (a unit 0 cannot name /RAM: none)
        bne     :+
        lda     #1
:       sta     ram_unit
        inc     claimed
        ; The auxiliary memory is the game's now: the exit state, then
        ; ProDOS's QUIT code ($D100-$D3FF of bank 2, where records of the
        ; game go next: src/dhgr.s B2_ENTRY), into the store's entry
        ; EX_ENTRY (memory.s), at the address build_disk.py writes into
        ; ld_exit; no record of NEOWILD.DAT goes there. ld_place copies
        ; main to auxiliary for a kind of bank 1 (the claim's own kind).
        lda     #<ex_state
        ldx     #>ex_state
        ldy     #EX_STATE
        jsr     ldc_put
        lda     #<QUIT_CODE     ; $300 bytes, read from bank 2
        ldx     #>QUIT_CODE
        ldy     #0
        bit     LCRAM2R
        jsr     ldc_put
        bit     LCROM
loader_claimed:
        rts
; ldc_put -- A/X = source, Y = length (0: $300 bytes): to ld_exit, which
; then moves past it (ld_quit finds the QUIT code $300 bytes below).
ldc_put:
        sta     move_src
        stx     move_src+1
        sty     size
        lda     #0
        cpy     #0
        bne     :+
        lda     #3
:       sta     size+1
        lda     ld_exit
        sta     address
        lda     ld_exit+1
        sta     address+1
        lda     #1
        sta     kind
        jsr     ld_place
        clc
        lda     ld_exit
        adc     size
        sta     ld_exit
        lda     ld_exit+1
        adc     size+1
        sta     ld_exit+1
        rts

ld_error:
        sta     key
        lda     #<m_error
        ldy     #>m_error
        jsr     print
        lda     key
        jsr     PRBYTE
ld_key_quit:
        lda     #<m_key
        ldy     #>m_key
        jsr     print
        jsr     ld_wait
ld_quit:
        lda     claimed         ; the /RAM disk back, empty (video.s release)
        beq     :+
        lda     ram_unit
        cmp     #2
        bcc     :+
        sta     $43             ; FORMAT through its driver (mli.s
        lda     #3              ; _prodos_format_ram); the zero page is
        sta     $42             ; ProDOS's again just below
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
:       lda     claimed         ; ProDOS's QUIT code back in bank 2 (the
        beq     :+              ; game's records replace it), from the
        jsr     ld_unquit       ; store's exit state
:       ldx     #23
:       lda     saved_bitmap,x
        sta     BITMAP,x
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
ld_mli_quit:                    ; tests/test_prodos.py: state at the final QUIT
        jsr     MLI
        .byte   $65
        .word   ld_quit_parms
:       jmp     :-

; ld_unquit -- $300 bytes below ld_exit (moved past the exit state by the
; claim) in auxiliary RAM back to QUIT_CODE, bank 2 written. Reading
; auxiliary RAM (RAMRD) moves the program too: the loop runs from the stack
; page, as memory.s mem_fetch does. source/dest: free (no record now).
UQ_RUN = $0100
ld_unquit:
        ldx     #uq_end-uq_tpl-1
:       lda     uq_tpl,x
        sta     UQ_RUN,x
        dex
        bpl     :-
        sec
        lda     ld_exit+1
        sbc     #3
        sta     source+1
        lda     ld_exit
        sta     source
        lda     #<QUIT_CODE
        sta     dest
        lda     #>QUIT_CODE
        sta     dest+1
        bit     LCBANK2
        bit     LCBANK2
        ldx     #3
        ldy     #0
:       jsr     UQ_RUN
        inc     source+1
        inc     dest+1
        dex
        bne     :-
        bit     LCROM
        rts
uq_tpl: sta     RAMRDON         ; (UQ_RUN) one page, Y = 0 on entry and exit
:       lda     (source),y
        sta     (dest),y
        iny
        bne     :-
        sta     RAMRDOFF
        rts
uq_end:

ld_wait:
        lda     KBD
        bpl     ld_wait
        bit     KBDSTRB
        rts

; print -- A/Y = ASCIIZ text, through COUT.
ld_print:
print:  sta     @text+1
        sty     @text+2
        ldx     #0
@text:  lda     $FFFF,x
        beq     @done
        cmp     #2              ; 1: inverse, 2: normal (Monitor INVFLG)
        bcs     @char
        lsr     a
        lda     #$3F
        bcs     @flag
        lda     #$FF
@flag:  sta     $32
        bne     @next
@char:  cmp     #2
        bne     :+
        lda     #$FF
        sta     $32
        bne     @next
:       ora     #$80
        jsr     COUT
@next:  inx
        bne     @text
        inc     @text+2
        bne     @text
@done:  rts

HOF_ZP    = source              ; source, dest: free while the menu runs
HOF_BUF   = STAGE
HOF_MLI   = ld_mli
HOF_IOBUF = LD_IOBUF
HOF_PATH  = geo_path
HOF_READ_PARMS = read           ; ld_mli counts its transfer
HOF_NAMES_LO = region_names_lo
HOF_NAMES_HI = region_names_hi
HOF_LOADER = 1
hm_regions = ld_regions
        .include "hof_menu.s"
move_src: .word 0
ld_move_src := move_src
ld_menu_key := ld_event_key
online: .byte   2, 0
        .word   volume
open:   .byte   3
        .word   ld_path, LD_IOBUF
        .byte   0
read:   .byte   4, 0
        .word   0, 0, 0
close:  .byte   1, 0
block:  .byte   3, 0
        .word   STAGE, 2
ld_quit_parms: .byte 4, 0, 0, 0, 0, 0, 0
file_name: .byte "/NEOWILD."
file_suffix:
file_dat: .byte "DAT"
file_geo: .byte "GEO"
file_scn: .byte "SCN"
file_tmp: .byte "TMP"
m_archipelago: .byte "ARCHIPELAGO",0
mark:   .byte   2, 0, 0, 0, 0   ; SET_MARK
; Written by tools/build_disk.py into NEOWILD.SYSTEM: the marks (3 bytes) of
; the six packs and of the preparation in NEOWILD.DAT, then the stored
; length of the preparation (2 bytes).
ld_marks: .res  23
; Scenarios of the edition, written by tools/build_disk.py with ld_marks:
; 6 (NeoWildernessXL, 800 KB) or 1 (Neowilderness, 140 KB: the Sierra only,
; menu key 1; the free journey and the preparation ask no region).
ld_regions: .byte 0
.export ld_tmap
; Docs/MEMORY.md 14, written by tools/build_disk.py too: the first block of
; NEOWILD.BLK (0: none, the 140 KB edition), then the 6 bytes it starts with
; (signature "NWBK" and the file's build id).
ld_blk: .res 8
; Docs/MEMORY.md 15, written by tools/build_disk.py too: the auxiliary address
; of the store's exit-state entry (memory.s EX_ENTRY).
ld_exit: .res 2
.export ld_marks, ld_regions, ld_blk, ld_exit, HI_LOAD, SWAP_LOAD

; Pages protected in the ProDOS bitmap while the game runs. The module
; window $5800-$5FFF and the I/O buffer stay free for the reads of
; NEOWILD.END and NEOWILD.HOF at the end of a journey (the fine geography is
; resident since the integration of the parallel branch).
game_pages:
        ; (XL: pages $B0-$B5 free for READ_BLOCK, STATUS and its tail read
        ; from NEOWILD.BLK up to $B5FF; sim_fetch frees $90-$AF)
        XL_BYTE XI_LOADER, game_pages+22, $03
        .repeat 24, I
        .scope
        bits .set 0
        .repeat 8, J
        page .set I * 8 + J
        .if ((page >= $02) .and (page <= $03)) .or ((page >= $08) .and (page <= $57)) .or ((page >= $60) .and (page <= $B9)) .or (page = $BE)
        bits .set bits | ($80 >> J)
        .endif
        .endrep
        .byte   bits
        .endscope
        .endrep

; Zero page that DOS 3.3, Applesoft and HELLO left to the HGR version at
; start, captured from build/reference-hgr ($00-$1F, $50-$FF; the Monitor
; range $20-$4F stays ProDOS's). Without BASIC, Applesoft's cold start never
; ran: CHRGET ($B1), its pointers and the float scratch the ROM reads before
; writing (SHIFT.SIGN.EXT at $A4, for instance) must match the reference for
; bit-identical simulation results.
applesoft_lo:
        .byte   $4C, $3C, $D4, $4C, $3A, $DB, $00, $FF, $00, $FF, $4C, $99, $E1, $22, $22, $FF
        .byte   $00, $FF, $00, $7F, $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF
applesoft_hi:
        .byte   $00, $C0, $55, $52, $00, $0D, $8D, $0A, $00, $FF, $00, $FF, $00, $FF, $8D, $0A
        .byte   $00, $FF, $00, $FF, $00, $FF, $00, $01, $08, $9E, $0A, $9E, $0A, $9E, $0A, $00
        .byte   $96, $FF, $95, $00, $96, $D2, $00, $FF, $00, $81, $0A, $FF, $00, $00, $08, $FF
        .byte   $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $00, $00, $FF, $00, $FF, $00, $03
        .byte   $4C, $46, $E6, $FF, $00, $FF, $00, $FF, $00, $00, $00, $00, $00, $0D, $8D, $0A
        .byte   $55, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $8D, $0A, $9B, $0A, $9E
        .byte   $0A, $E6, $B8, $D0, $02, $E6, $B9, $AD, $9B, $0A, $C9, $3A, $B0, $0A, $C9, $20
        .byte   $F0, $EF, $38, $E9, $30, $38, $E9, $D0, $60, $80, $4F, $C7, $52, $FF, $00, $FF
        .byte   $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF
        .byte   $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF, $00, $FF
        .byte   $00, $01, $00, $00, $00, $FF, $00, $FF, $F8, $FF, $00, $FF, $00, $FF, $00, $FF

m_moved:
        .byte   "NEOWILD.BLK HAS MOVED: COPY THE WHOLE", 13
        .byte   "DISK BLOCK BY BLOCK, NOT FILE BY FILE.", 13, 0
m_machine:
        .byte   "NEOWILDERNESS NEEDS AN APPLE //E", 13
        .byte   "ENHANCED OR AN APPLE //C WITH 128K.", 13, 0
; Loading page: title, machine, credits, the goal and the one thing to know
; (HELP lists the commands in the game); the region and level line, then
; LOADING..., follow after the menu.
m_intro:
        .byte   1, "             NEOWILDERNESS              ", 2, 13
        .byte   "  APPLE //E //C 128K - PRODOS - DHGR", 13, 13
        .byte   "ORIGINAL GAME: WESLEY HUNTRESS, CHARLES", 13
        .byte   "KOHLHASE, PETER FARSON (E.TRANSIT 1985)", 13
        .byte   "DHGR PORT: VERHILLE.A", 13, 13
        .byte   "YOU SURVIVED A PLANE CRASH.", 13
        .byte   "REACH THE RANGER OUTPOST TO GET HELP.", 13, 13
        .byte   "TYPE A COMMAND, THEN PRESS RETURN.", 13
        .byte   "HELP LISTS THE COMMANDS.", 13, 13, 0
m_loading:
        .byte   13, "LOADING...", 0
m_level:
        .byte   ", LEVEL ", 0
m_free: .byte   " (FREE)", 0
m_choice:                       ; "-" at +21 ("/" with one scenario)
        .byte   "CHOICE (RETURN = 1, 1-7, P, H, Q)? ", 0
.assert m_choice + 21 = m_choice + .strlen("CHOICE (RETURN = 1, 1"), error, "m_choice dash"
m_region:
        .byte   "FREE JOURNEY: REGION (1-6, ESC)? ", 0
m_ask_level:
        .byte   "LEVEL 1-10 (RETURN = 4, ESC)? ", 0
        .include "menu.inc"     ; build/, from tools/genmenu.py
m_ram:  .byte   13, "/RAM HOLDS FILES. NEOWILDERNESS NEEDS", 13
        .byte   "ITS MEMORY. ERASE /RAM (Y/N)? ", 0
m_erase:
        .byte   "Y", 13, 0
m_error:
        .byte   13, "NEOWILD DISK ERROR $", 0
m_key:  .byte   13, "PRESS A KEY TO RETURN TO PRODOS.", 0

.segment "LOADER"
ld_event_key:
        jsr     ui_poll
        beq     ld_event_key
        ora     #$80
        rts
