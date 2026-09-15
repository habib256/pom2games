; ============================================================================
; crt0_apple2.s -- cc65 startup for Apple II DOS 3.3 BRUN programs (-t none)
; ============================================================================
; The Apple II counterpart of POM1's dev/cc65/crt0_pom1.s. Put it FIRST on the
; link line: its __STARTUP__ / _exit definitions keep none.lib's crt0.o out,
; while zerobss / copydata / initlib / donelib still come from none.lib.
;
;   CLD, LDX #$FF / TXS     clean flags and hardware stack
;   save $00-$FF            the zero page belongs to the Monitor, DOS and
;                           Applesoft; it is put back on exit
;   RESET -> _exit          $03F2-$03F4 saved and pointed at _exit, so
;                           Ctrl-RESET leaves cleanly too (restored on exit)
;   sp := __STACKSTART__    cc65 argument stack (top of free RAM, $9600)
;   zerobss / copydata / initlib / main
;   _exit: donelib, restore ZP (live text window + cursor kept), TEXT + full screen + page 1 + lores latch,
;          clear the key strobe, JMP $03D0 (DOS warm start, ']' prompt)
;
; Needs a cfg with STARTUP first in the load image, DATA / BSS with
; define = yes, a ZPSAVE bss segment and __STACKSTART__ (apple2_hgr_c.cfg).
; ============================================================================

        .export         __STARTUP__ : absolute = 1
        .export         _exit
        .import         __STACKSTART__
        .import         zerobss, copydata, initlib, donelib
        .import         _main
        .importzp       sp

DOSWARM = $03D0
SOFTEV  = $03F2
KBDSTRB = $C010
TXTSET  = $C051
MIXCLR  = $C052
LOWSCR  = $C054
LORES   = $C056

.segment "STARTUP"

        cld
        ldx     #$FF
        txs
        inx                     ; X = 0
@save:  lda     $00,x
        sta     zp_save,x
        inx
        bne     @save
        ldx     #2
@rsv:   lda     SOFTEV,x
        sta     rst_save,x
        dex
        bpl     @rsv
        lda     #<_exit
        sta     SOFTEV
        lda     #>_exit
        sta     SOFTEV+1
        eor     #$A5            ; power-up byte
        sta     SOFTEV+2
        lda     #<__STACKSTART__
        sta     sp
        lda     #>__STACKSTART__
        sta     sp+1
        jsr     zerobss
        jsr     copydata
        jsr     initlib
        jsr     _main
_exit:  jsr     donelib
        ldx     #2
@rrv:   lda     rst_save,x
        sta     SOFTEV,x
        dex
        bpl     @rrv
        ldx     #9              ; keep the live text window + cursor ($20-$29)
@keep:  lda     $20,x           ; so the DOS prompt follows the program's
        sta     zp_save+$20,x   ; output, in the width it left
        dex
        bpl     @keep
        ldx     #0
@rest:  lda     zp_save,x
        sta     $00,x
        inx
        bne     @rest
        bit     TXTSET
        bit     MIXCLR
        bit     LOWSCR
        bit     LORES
        bit     KBDSTRB
        jmp     DOSWARM

.segment "ZPSAVE"
zp_save:        .res 256
rst_save:       .res 3
