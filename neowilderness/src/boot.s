; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; boot.s -- NEOWILD.SYSTEM, the ProDOS 8 system program of Neowilderness
; ============================================================================
; ProDOS loads this file at $2000. The stub saves ProDOS's zero page and moves
; the loader to the SIM window ($9600), free until the first simulation copy.
; The loader then:
;   - refuses machines other than an enhanced IIe / IIc with 128 KB, with a
;     message and a clean return to ProDOS;
;   - keeps the introduction on the text screen during the whole preload;
;   - reads NEOWILD.DAT sequentially: records for main RAM, auxiliary RAM
;     ($0800-$1FFF, $4000-$BFFF) and the auxiliary language card, raw or LZ
;     (tools/pack_boot.py), decoded through main staging buffers;
;   - takes the auxiliary memory with dev/lib/prodos/video.s when the CLAIM
;     record arrives. Policy: an empty /RAM is discarded, a /RAM holding files
;     is erased only after Y; the empty disk is rebuilt at exit;
;   - marks the game pages in the ProDOS bitmap, points RESET at reset_exit
;     and jumps to start ($6000).
; NEOWILD.DAT: a 128-byte table of records, read once to $A000, then the
; payloads back to back: one MLI READ per record.
; Record: kind, address, length, stored length (little-endian words).
;   kind 0 end, 1 claim, else $80 + $40 (LZ) + bank (0 main, 1 auxiliary,
;   2 auxiliary language card bank 2, 3 bank 1). Stored data <= 8 KB.
; The staging buffer is HGR page 1 ($2000); LZ data for auxiliary RAM is
; decoded at $7000 first, before WILDMAP is loaded there.
; ============================================================================
        .include "apple2.inc"
        .macpack longbranch
.import start, _prodos_video_claim, _prodos_video_release, reset_exit
.import mli_calls, mli_reads, mli_bytes, saved_reset, saved_bitmap, saved_zp
.import io_buffer
.import __LOADER_LOAD__, __LOADER_RUN__, __LOADER_SIZE__
.import __LOADBSS_RUN__, __LOADBSS_SIZE__, __RESBSS_RUN__, __RESBSS_SIZE__
.import __BSS_RUN__, __BSS_SIZE__
.export loader_main, loader_claimed, loader_done, loader_ram_files, ld_decode, ld_decode_end

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
TABLE    = $A000                ; NEOWILD.DAT record table
TABLE_SIZE = 128                ; tools/build_disk.py TABLE_SIZE
ALTZPOFF = $C008
ALTZPON  = $C009
RAMWRTON = $C005
LCROM    = $C082
LCBANK2  = $C083                ; read and write RAM bank 2 (twice)
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

.assert __LOADER_RUN__ + __LOADER_SIZE__ <= TABLE, lderror, "loader overlaps its record table"
.segment "SYSSTUB"
        cld
        ldx     #0              ; ProDOS's zero page before touching any
:       lda     $00,x
        sta     saved_zp,x
        inx
        bne     :-
        ldy     #>(__LOADER_SIZE__+255)
@copy:  lda     __LOADER_LOAD__,x
@to:    sta     __LOADER_RUN__,x
        inx
        bne     @copy
        inc     @copy+2
        inc     @to+2
        dey
        bne     @copy
        jmp     loader_main

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
        sta     $C00E           ; primary character set
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
        ; Full pathnames on the boot volume (as CHROMA.SYSTEM does).
        lda     DEVNUM
        sta     online+1
        lda     #$C5            ; ONLINE
        ldx     #<online
        ldy     #>online
        jsr     ld_mli
        jcs     ld_error
        lda     volume
        and     #$0F
        jeq     ld_error
        sta     volume
        ldx     #<ld_path
        ldy     #>ld_path
        jsr     make_path
        lda     #$C8            ; OPEN NEOWILD.DAT
        ldx     #<open
        ldy     #>open
        jsr     ld_mli
        jcs     ld_error
        lda     open+5
        sta     read+1
        sta     close+1
        lda     #<TABLE         ; one READ for the whole record table
        ldx     #>TABLE
        ldy     #<TABLE_SIZE
        sty     stored
        ldy     #>TABLE_SIZE
        sty     stored+1
        jsr     read_size
        jcs     ld_error
record:
        ldy     #6
@hdr:   lda     TABLE,y         ; patched: walks the table
        sta     hdr,y
        dey
        bpl     @hdr
        clc
        lda     @hdr+1
        adc     #7
        sta     @hdr+1
        bcc     :+
        inc     @hdr+2
:       lda     kind
        jeq     @end
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
        jcs     ld_error
        jmp     record
@staged:
        lda     #<STAGE
        ldx     #>STAGE
        ldy     #0
        jsr     read_size
        jcs     ld_error
        lda     #<STAGE
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
@end:   lda     #$CC            ; CLOSE
        ldx     #<close
        ldy     #>close
        jsr     ld_mli
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
        jmp     start

; make_path -- X/Y = destination: length byte, "/VOLUME/NEOWILD.DAT".
make_path:
        stx     @dst+1
        sty     @dst+2
        stx     @len+1
        sty     @len+2
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
        cpx     #file_end-file_name
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
; bank of the record (1 auxiliary RAM, 2/3 auxiliary language card).
; While RAMWRT is on, stores to this code would reach auxiliary RAM: that
; loop uses main zero-page pointers. ALTZP swaps the zero page instead: the
; language-card loop patches its own absolute operands in main RAM.
ld_place:
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
        sta     ALTZPON         ; no stack or zero page until ALTZPOFF
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
        sta     dest
        stx     dest+1
        clc
        adc     size
        sta     remain          ; remain = end address
        txa
        adc     size+1
        sta     remain+1
        lda     #<STAGE
        sta     source
        lda     #>STAGE
        sta     source+1
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

; ld_claim -- the explicit /RAM policy, then dev/lib/prodos/video.s.
ld_claim:
        ldx     #0              ; video.s keeps its state in the game BSS
        txa
:       sta     __BSS_RUN__,x
        inx
        cpx     #<__BSS_SIZE__
        bne     :-
        .assert __BSS_SIZE__ < 256, error, "game BSS: extend the clear"
        ldy     DEVCNT          ; find /RAM as video.s does: driver $FF00
        cpy     #14
        bcs     ldc_claim          ; empty ($FF) or malformed: video.s decides
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
        bmi     ldc_claim
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
        bne     ld_quit
ldc_erase: lda     #<m_erase
        ldy     #>m_erase
        jsr     print
ldc_claim: lda     #1              ; PD_VIDEO_DISCARD_RAM
        jsr     _prodos_video_claim
        cmp     #0
        bne     ld_error
        inc     claimed
loader_claimed:
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
        lda     claimed
        beq     :+
        jsr     _prodos_video_release
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
        jsr     MLI
        .byte   $65
        .word   ld_quit_parms
:       jmp     :-

ld_wait:
        lda     KBD
        bpl     ld_wait
        bit     KBDSTRB
        rts

; print -- A/Y = ASCIIZ text, through COUT.
print:  sta     @text+1
        sty     @text+2
        ldx     #0
@text:  lda     $FFFF,x
        beq     @done
        ora     #$80
        jsr     COUT
        inx
        bne     @text
        inc     @text+2
        bne     @text
@done:  rts

move_src: .word 0
online: .byte   2, 0
        .word   volume
open:   .byte   3
        .word   ld_path, io_buffer
        .byte   0
read:   .byte   4, 0
        .word   0, 0, 0
close:  .byte   1, 0
block:  .byte   3, 0
        .word   STAGE, 2
ld_quit_parms: .byte 4, 0, 0, 0, 0, 0, 0
file_name: .byte "/NEOWILD.DAT"
file_end:

; Pages protected in the ProDOS bitmap while the game runs. The module
; window $5800-$5FFF and the I/O buffer stay unmarked, as before lot 5
; (nothing reads the disk there any more: the fine geography is resident).
.define PROT(p) ((((p) >= $08) .and ((p) <= $57)) .or (((p) >= $60) .and ((p) <= $B9)) .or ((p) = $BE))
game_pages:
        .repeat 24, I
        .byte   PROT(I*8)*$80 | PROT(I*8+1)*$40 | PROT(I*8+2)*$20 | PROT(I*8+3)*$10 | PROT(I*8+4)*8 | PROT(I*8+5)*4 | PROT(I*8+6)*2 | PROT(I*8+7)
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

m_machine:
        .byte   "NEOWILDERNESS NEEDS AN APPLE //E", 13
        .byte   "ENHANCED OR AN APPLE //C WITH 128K.", 13, 0
m_intro:
        .byte   "NEOWILDERNESS - //E //C 128K PRODOS", 13, 13
        .byte   "YOU SURVIVED A PLANE CRASH.", 13
        .byte   "REACH THE RANGER OUTPOST TO GET HELP.", 13
        .byte   "MANAGE YOUR EQUIPMENT, HUNGER, THIRST,", 13
        .byte   "FATIGUE AND BODY TEMPERATURE.", 13, 13
        .byte   "MAIN COMMANDS", 13
        .byte   "LEFT/RIGHT: TURN ON AN EMPTY LINE", 13
        .byte   "WALK / SWIM: TRAVEL ON LAND / WATER", 13
        .byte   "TOPO: TERRAIN MAP   MAP: LOCAL MAP", 13
        .byte   "STATUS: HEALTH   INVENTORY: ITEMS", 13
        .byte   "GET ITEM: PACK   WEAR PARKA: WEAR", 13
        .byte   "EAT FOOD / DRINK WATER: CONSUME", 13
        .byte   "REST: REST   HELP: COMMAND HELP", 13, 13
        .byte   "TYPE A COMMAND, THEN PRESS RETURN.", 13
        .byte   "DURATIONS: H OR MIN. QUANTITIES: OZ.", 13, 13
        .byte   "LOADING...", 0
m_ram:  .byte   13, "/RAM HOLDS FILES. NEOWILDERNESS NEEDS", 13
        .byte   "ITS MEMORY. ERASE /RAM (Y/N)? ", 0
m_erase:
        .byte   "Y", 13, 0
m_error:
        .byte   13, "NEOWILD.DAT ERROR $", 0
m_key:  .byte   13, "PRESS A KEY TO RETURN TO PRODOS.", 0
