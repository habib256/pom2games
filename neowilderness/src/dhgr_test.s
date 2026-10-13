; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; dhgr_test.s -- standalone IIe test bench of src/dhgr_cols.s (lot 3)
; ============================================================================
; ProDOS boots NEODHGR.SYSTEM (src/dhgr_boot.s), which loads this program
; (DHGRTEST) and a script (SCENE, tests/test_dhgr_cols.py) at their aux-type
; addresses. The bench claims the auxiliary memory from ProDOS (/RAM is
; discarded, dev/lib/prodos/video.s), shows DHGR (page 1 with 80STORE, or
; page 2 when assembled with DHGR_BASE = $4000) and interprets:
;   $00                     end: loop at `finished`
;   $01 c                   dc_clear
;   $02 x y0 y1 c           dc_vspan
;   $03 x0 x1 c top bot     dc_band (top/bot: LE16 pointers to 140 bytes)
;   $04                     checkpoint: wait for the test (dt_go)
;   $05 c                   dev/lib/hgrc dhgr_clear_asm (80STORE off around it)
;   $06 lines*80 chars      mixed mode, 80-column text from row 20
;   $07 x n (y0 y1 c)*n     one column of spans, as the renderer emits them
;   $08 y0 y1 g c           dc_group
;   $09                     dc_save_bank / dc_restore_bank around a vspan
;                           of the next $02 command (bank contract test)
;   $0A                     clear the 7 column buffers (page 1 build)
;   $0B g k n (y0 y1 c)*n   dc_bspan runs into column buffer k of group g
;   $0C g y0 y1             dc_flush
;   $0D                     wait for a key: ESC or Q quits to ProDOS
;   $0E len name            load file `name` (current prefix) at SCRIPT and
;                           run it from its first byte
; The test stops at `checkpoint`, peeks memory (aux via PAGE2/RAMRD from the
; harness), pokes dt_go and resumes at `cp_resume`.
; ============================================================================
        .include "apple2.inc"

.ifndef DHGR_BASE
DHGR_BASE = $2000
.endif
.ifndef SCRIPT
SCRIPT = $4000
.endif
.ifndef SCRIPT_END
.if SCRIPT = $4000
SCRIPT_END = $7400              ; the bench starts here
.else
SCRIPT_END = $4000              ; page 2 build: script below the video page
.endif
.endif

        .import dc_clear, dc_vspan, dc_band, dc_group, dc_save_bank, dc_restore_bank
        .importzp dc_x, dc_x1, dc_y0, dc_y1, dc_c, dc_g, dc_top, dc_bot
        .import _dhgr_clear_asm, _prodos_video_claim, _prodos_video_release
.if DHGR_BASE = $4000
        .import dc_mirror
.else
        .import dc_flush, dc_bspan, dc_colbuf
.endif
        .export _dhgr_base, _dhgr_pattern, checkpoint, cp_resume, finished, dt_go
        .exportzp ptr1, tmp1, tmp2

.segment "ZEROPAGE"
dt_sp:  .res 2
dt_n:   .res 1
dt_go:  .res 1
ptr1:   .res 2                  ; cc65 names used by dhgr_clear_asm.s
tmp1:   .res 1
tmp2:   .res 1

.segment "STARTUP"
start:  cld
        sei                     ; no IRQ source is used by the bench
        lda     #0
        sta     dt_go
        sta     TXTCLR
        sta     MIXCLR
        sta     HIRES
        sta     COL80ON
        lda     #1              ; PD_VIDEO_DISCARD_RAM: /RAM is rebuilt at exit
        jsr     _prodos_video_claim
        sta     TXTCLR
        sta     DHIRES_ON
.if DHGR_BASE = $2000
        sta     STORE80ON
        sta     LOWSCR          ; display page 1; PAGE2 off = main selected
.else
        sta     STORE80OFF
        sta     HISCR           ; display page 2
        jsr     dc_mirror
.endif
        lda     #<SCRIPT
        sta     dt_sp
        lda     #>SCRIPT
        sta     dt_sp+1

next:   jsr     fetch
        asl     a
        tax
        lda     ops+1,x
        pha
        lda     ops,x
        pha
        rts                     ; RTS dispatch

ops:    .word   op_end-1, op_clear-1, op_span-1, op_band-1, op_check-1
        .word   op_devclear-1, op_text-1, op_column-1, op_group-1, op_bank-1
        .word   op_bufclr-1, op_bufcol-1, op_flush-1, op_key-1, op_load-1

fetch:  ldy     #0              ; A = next script byte, flags set from it
        lda     (dt_sp),y
        inc     dt_sp
        bne     :+
        inc     dt_sp+1
:       cmp     #0
        rts

op_end:
finished:
        jmp     finished

op_clear:
        jsr     fetch
        jsr     dc_clear
        jmp     next

op_span:
        jsr     span_args
        jsr     dc_vspan
        jmp     next

span_args:
        jsr     fetch
        sta     dc_x
        jsr     fetch
        sta     dc_y0
        jsr     fetch
        sta     dc_y1
        jsr     fetch
        sta     dc_c
        rts

op_band:
        jsr     fetch
        sta     dc_x
        jsr     fetch
        sta     dc_x1
        jsr     fetch
        sta     dc_c
        jsr     fetch
        sta     dc_top
        jsr     fetch
        sta     dc_top+1
        jsr     fetch
        sta     dc_bot
        jsr     fetch
        sta     dc_bot+1
        jsr     dc_band
        jmp     next

op_check:
        jsr     checkpoint
        jmp     next

; The harness stops at checkpoint (= the polling loop), pokes dt_go = 1
; and runs to cp_resume, which differs from checkpoint.
checkpoint:
        lda     dt_go
        beq     checkpoint
cp_resume:
        lda     #0
        sta     dt_go
        rts

op_devclear:
        jsr     fetch
        and     #15
        tax
        ldy     #0
:       lda     dt_pat,x
        sta     _dhgr_pattern,y
        txa
        clc
        adc     #16
        tax
        iny
        cpy     #4
        bcc     :-
        lda     #>DHGR_BASE
        sta     _dhgr_base
.if DHGR_BASE = $2000
        sta     STORE80OFF      ; the library banks with RAMWRT
        jsr     _dhgr_clear_asm
        sta     STORE80ON
.else
        jsr     _dhgr_clear_asm
.endif
        jmp     next

; 80-column text: even columns in aux, odd columns in main ($0400 page 1).
op_text:
        jsr     fetch
        sta     dt_n
        sta     MIXSET
        ldx     #20
@line:  lda     text_lo,x
        sta     ptr1
        lda     text_hi,x
        sta     ptr1+1
        lda     #0
        sta     tmp1
@char:  ldy     #0
        lda     (dt_sp),y
        ora     #$80
        pha
        lda     tmp1
        lsr     a
        tay
        pla
.if DHGR_BASE = $2000
        bcs     :+
        sta     HISCR           ; 80STORE: aux text page
:       sta     (ptr1),y        ; $0400 text row
        sta     LOWSCR
.else
        bcs     :+
        sta     $C005           ; RAMWRT aux
:       sta     (ptr1),y
        sta     $C004
.endif
        inc     dt_sp
        bne     :+
        inc     dt_sp+1
:       inc     tmp1
        lda     tmp1
        cmp     #80
        bcc     @char
        inx
        dec     dt_n
        bne     @line
        jmp     next

op_column:
        jsr     fetch
        sta     dc_x
        jsr     fetch
        sta     dt_n
        beq     @done
@span:  jsr     fetch
        sta     dc_y0
        jsr     fetch
        sta     dc_y1
        jsr     fetch
        sta     dc_c
        jsr     dc_vspan
        dec     dt_n
        bne     @span
@done:  jmp     next

op_group:
        jsr     fetch
        sta     dc_y0
        jsr     fetch
        sta     dc_y1
        jsr     fetch
        sta     dc_g
        jsr     fetch
        sta     dc_c
        jsr     dc_group
        jmp     next

op_bank:
        jsr     fetch           ; skip the $02 opcode
        jsr     span_args
.if DHGR_BASE = $2000
        sta     HISCR           ; the caller had aux selected
.else
        sta     $C005           ; RAMWRT aux (RAMRD aux would fetch this code from aux)
.endif
        jsr     dc_save_bank
        jsr     dc_vspan
        jsr     dc_restore_bank
        jsr     checkpoint      ; the harness reads the switches here
.if DHGR_BASE = $2000
        sta     LOWSCR
.else
        sta     $C004
.endif
        jmp     next

.if DHGR_BASE = $2000
op_bufclr:
        lda     #<dc_colbuf
        sta     ptr1
        lda     #>dc_colbuf
        sta     ptr1+1
        ldx     #5              ; 7 * 192 = 1344 bytes: 5 pages + 64
        ldy     #0
        tya
:       sta     (ptr1),y
        iny
        bne     :-
        inc     ptr1+1
        dex
        bne     :-
        ldy     #63
:       sta     (ptr1),y
        dey
        bpl     :-
        jmp     next

op_bufcol:
        jsr     fetch
        sta     dc_g
        jsr     fetch
        sta     dc_x
        jsr     fetch
        sta     dt_n
        beq     @done
@span:  jsr     fetch
        sta     dc_y0
        jsr     fetch
        sta     dc_y1
        jsr     fetch
        sta     dc_c
        jsr     dc_bspan
        dec     dt_n
        bne     @span
@done:  jmp     next

op_flush:
        jsr     fetch
        sta     dc_g
        jsr     fetch
        sta     dc_y0
        jsr     fetch
        sta     dc_y1
        jsr     dc_flush
        jmp     next
.else
op_bufclr:
op_bufcol:
op_flush:
        brk
.endif

op_key: bit     KBD
        bpl     op_key
        lda     KBD
        bit     KBDSTRB
        and     #$5F            ; upper case, ESC stays $1B
        cmp     #$1B
        beq     quit
        cmp     #'Q'
        beq     quit
        jmp     next

op_load:
        jsr     fetch           ; copy the name before READ overwrites it
        sta     dt_path
        tax
        ldy     #0
:       lda     (dt_sp),y
        sta     dt_path+1,y
        iny
        dex
        bne     :-
        jsr     $BF00
        .byte   $C8             ; OPEN, buffer $1000
        .word   dt_open
        bcs     load_error
        lda     dt_open_ref
        sta     dt_read_ref
        sta     dt_close_ref
        jsr     $BF00
        .byte   $CA             ; READ the script at SCRIPT
        .word   dt_read
        php
        jsr     $BF00
        .byte   $CC             ; CLOSE
        .word   dt_close
        plp
        bcs     load_error
        lda     #<SCRIPT
        sta     dt_sp
        lda     #>SCRIPT
        sta     dt_sp+1
        jmp     next
load_error:
        brk

; Back to ProDOS: 40-column text page 1, main banks, /RAM rebuilt, QUIT.
quit:   sta     LOWSCR
        sta     STORE80OFF
        sta     $C002           ; RAMRD main
        sta     $C004           ; RAMWRT main
        sta     DHIRES_OFF
        sta     MIXCLR
        sta     TXTSET
        sta     COL80OFF
        jsr     _prodos_video_release
        jsr     $FB2F           ; INIT: full text window
        jsr     $FE93           ; SETVID
        jsr     $FE89           ; SETKBD
        jsr     $FC58           ; HOME
        cli
        jsr     $BF00
        .byte   $65             ; QUIT
        .word   dt_quit
        brk
.export quit, op_key

.segment "RODATA"
dt_quit: .byte  4, 0, 0, 0, 0, 0, 0
text_lo:
.repeat 24, R
        .byte   <($0400 + (R .mod 8) * 128 + (R / 8) * 40)
.endrepeat
text_hi:
.repeat 24, R
        .byte   >($0400 + (R .mod 8) * 128 + (R / 8) * 40)
.endrepeat
dt_pat:
.repeat 4, JJ
.repeat 16, CC
        .byte   ((((CC >> 1) | (CC << 3)) & 15) * $1111111 >> (7 * JJ)) & $7F
.endrepeat
.endrepeat

.segment "DATA"
dt_open: .byte  3
        .word   dt_path, $1000
dt_open_ref: .byte 0
dt_read: .byte  4
dt_read_ref: .byte 0
        .word   SCRIPT, SCRIPT_END - SCRIPT, 0
dt_close: .byte 1
dt_close_ref: .byte 0
dt_path: .res   16

.segment "BSS"
_dhgr_base:    .res 1
_dhgr_pattern: .res 4
