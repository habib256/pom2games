; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; auxmem.asm — moves between main and auxiliary memory on a 128 KB //e or
; //c (65C02). Include AFTER the callers (.ifref: only what they use is
; assembled), in the segment the code should live in; a second include
; (another segment, a .scope) only assembles what the earlier ones left
; out. AUXMOVE is a macro: include the file once at the top of a source that
; uses it (no routine is assembled there), again after the callers.
;
; Entry contract (ABI.md): main RAMRD/RAMWRT, main zero page and stack
; (ALTZP off), 80STORE off, 1 MHz timing irrelevant. Every routine leaves
; RAMRD/RAMWRT main and restores the I flag it found; clobbers A/X/Y and
; flags. Ranges must avoid $0000-$01FF, $C000-$FFFF and the caller's code.
;
;   aux_store          A pages of main memory from page Y to aux page X
;                      (RAMWRT aux, interrupts masked meanwhile: the whole
;                      copy, ~3 600 cycles a page). A = 0 copies 256 pages.
;   aux_fetch_pages    A pages of aux memory from page X to main page Y.
;                      RAMRD aux hides the code in main RAM, so the page loop
;                      runs from a 16-byte stub copied to the zero page at
;                      each call (auxmem_zcopy); interrupts are masked one
;                      page at a time (~3 600 cycles), ~14 cycles a byte.
;   aux_fetch_chunked  aux (A low, Y high) -> main auxmem_fdst, auxmem_flen
;                      bytes, through the ROM's AUXMOVE ($C311), in chunks of
;                      AUXMEM_FETCH_CHUNK bytes under SEI each (the IRQ of a
;                      music player waits at most one chunk, ~36 cycles a
;                      byte). auxmem_fdst/auxmem_flen are consumed; scratch
;                      auxmem_fsrc (2) and auxmem_fn (1).
;   AUXMOVE first, last, dest, dir [, jmp]
;                      macro: the ROM's AUXMOVE of first..last (inclusive) to
;                      dest, dir = AUX_TO_MAIN or MAIN_TO_AUX; constants or
;                      labels; `jmp` as the 5th argument makes it a tail
;                      call. Uses $3C-$3F/$42/$43; the ROM leaves I alone:
;                      mask interrupts around it if an IRQ handler could run
;                      while banks are switched (ROM code swaps RAMRD/RAMWRT).
;
; Zero page: aux_store borrows auxmem_src/auxmem_dst (2 bytes each; define
; them before the include to alias them, the C wrapper uses cc65's
; ptr1/ptr2). aux_fetch_pages runs its stub at auxmem_zcopy.
;
; Options:
;   AUXMEM_ZP = addr        the 16-byte stub of aux_fetch_pages at a fixed
;                           zero-page address (the caller reserves it, it may
;                           alias other scratch: it is rewritten at each call)
;                           instead of 16 bytes reserved in ZEROPAGE.
;   AUXMEM_FETCH_CHUNK = n  aux_fetch_chunked's chunk (1..255, default 64:
;                           ~2 300 cycles with interrupts masked each). Bigger
;                           = fewer AUXMOVE setups (~60 cycles each), longer
;                           masked windows.
;   AUXMEM_FETCH_SCAN = 1   jsr _a2_vbl_scan after each chunk (apple2vbl.s:
;                           the //e VBL edges keep being counted during a long
;                           fetch); +3 bytes, ~30 cycles a chunk. Default: none.

.ifndef _AUXMEM_DEFS_
_AUXMEM_DEFS_ = 1
AUX_TO_MAIN = 0
MAIN_TO_AUX = 1
.ifndef AUXMEM_FETCH_CHUNK
AUXMEM_FETCH_CHUNK = 64
.endif
.ifndef AUXMEM_FETCH_SCAN
AUXMEM_FETCH_SCAN = 0
.endif

.macro AUXMOVE first, last, dest, dir, tail
        lda #<(first)
        sta $3C
        lda #>(first)
        sta $3D
        lda #<(last)
        sta $3E
        lda #>(last)
        sta $3F
        lda #<(dest)
        sta $42
        lda #>(dest)
        sta $43
.if .xmatch({dir}, MAIN_TO_AUX)    ; (by name: also constant inside a .scope)
        sec                      ; main -> aux
.elseif .xmatch({dir}, AUX_TO_MAIN)
        clc                      ; aux -> main
.elseif (dir) = MAIN_TO_AUX
        sec
.else
        clc
.endif
.ifblank tail
        jsr $C311                ; AUXMOVE
.else
        jmp $C311                ; AUXMOVE
.endif
.endmacro
.endif

.if .referenced(aux_store) .and (.not .defined(aux_store))
.ifndef auxmem_src
.pushseg
.zeropage
auxmem_src: .res 2
auxmem_dst: .res 2
.popseg
.endif
aux_store:
        stx auxmem_dst+1
        sty auxmem_src+1
        tax
        php
        sei
        stz auxmem_src
        stz auxmem_dst
        ldy #0
        sta $C005                ; RAMWRT aux
@copy:  lda (auxmem_src),y
        sta (auxmem_dst),y
        iny
        bne @copy
        inc auxmem_src+1
        inc auxmem_dst+1
        dex
        bne @copy
        sta $C004                ; RAMWRT main
        plp
        rts
.endif

.if .referenced(aux_fetch_pages) .and (.not .defined(aux_fetch_pages))
AUXMEM_ZLEN = 16
.ifdef AUXMEM_ZP
auxmem_zcopy = AUXMEM_ZP
.else
.pushseg
.zeropage
auxmem_zcopy: .res AUXMEM_ZLEN
.popseg
.endif
AUXMEM_ZSRC = auxmem_zcopy + 5   ; the stub's operand high bytes
AUXMEM_ZDST = auxmem_zcopy + 8
aux_fetch_pages:
        phx
        phy
        pha
        ldx #AUXMEM_ZLEN - 1
@put:   lda auxmem_ztemplate,x
        sta auxmem_zcopy,x
        dex
        bpl @put
        plx                      ; the page count
        pla
        sta AUXMEM_ZDST
        pla
        sta AUXMEM_ZSRC
@page:  ldy #0
        php
        sei
        jsr auxmem_zcopy
        plp
        inc AUXMEM_ZSRC
        inc AUXMEM_ZDST
        dex
        bne @page
        rts
; Aux page (zsrc) to main page (zdst), Y = 0 on entry.
auxmem_ztemplate:
        sta $C003                ; RAMRD aux
auxmem_zsrc = * + 2
:       lda $FF00,y
auxmem_zdst = * + 2
        sta $FF00,y
        iny
        bne :-
        sta $C002                ; RAMRD main
        rts
.assert * - auxmem_ztemplate = AUXMEM_ZLEN, error, "auxmem: the stub's length"
.assert auxmem_zsrc - auxmem_ztemplate = 5 .and auxmem_zdst - auxmem_ztemplate = 8, error, "auxmem: the stub's operands"
.endif

.if .referenced(aux_fetch_chunked) .and (.not .defined(aux_fetch_chunked))
.ifndef auxmem_fsrc
.pushseg
.bss
auxmem_fsrc: .res 2
auxmem_fdst: .res 2
auxmem_flen: .res 2
auxmem_fn:   .res 1
.popseg
.endif
aux_fetch_chunked:
        sta auxmem_fsrc
        sty auxmem_fsrc+1
@chunk: lda auxmem_flen+1
        bne :+
        lda auxmem_flen
        beq @done
        cmp #AUXMEM_FETCH_CHUNK
        bcc :++
:       lda #AUXMEM_FETCH_CHUNK
:       sta auxmem_fn
        lda auxmem_fsrc          ; A1 = src, A2 = src + n - 1, A4 = dst
        sta $3C
        clc
        adc auxmem_fn
        sta auxmem_fsrc
        lda auxmem_fsrc+1
        sta $3D
        adc #0
        sta auxmem_fsrc+1
        lda auxmem_fsrc
        sec
        sbc #1
        sta $3E
        lda auxmem_fsrc+1
        sbc #0
        sta $3F
        lda auxmem_fdst
        sta $42
        clc
        adc auxmem_fn
        sta auxmem_fdst
        lda auxmem_fdst+1
        sta $43
        adc #0
        sta auxmem_fdst+1
        lda auxmem_flen
        sec
        sbc auxmem_fn
        sta auxmem_flen
        bcs :+
        dec auxmem_flen+1
:       php
        sei
        clc                      ; aux -> main
        jsr $C311                ; AUXMOVE
        plp
.if AUXMEM_FETCH_SCAN
        jsr _a2_vbl_scan
.endif
        bra @chunk
@done:  rts
.endif
