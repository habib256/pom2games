; VERHILLE Arnaud — GPL-3.0. ProDOS 8 files from assembly: OPEN, READ,
; WRITE, CLOSE, and whole-file load / save (CREATE a BIN file if missing).
;
; Include AFTER the callers (.ifref: only what they use is assembled), in
; the segment the code should live in. The parameters are fields of the MLI
; parameter lists, set before the call:
;   pf_name   word  Pascal string (relative to the prefix, or a full path)
;   pf_iobuf  word  1 KB OPEN buffer, page aligned, free in the bitmap
;   pf_buf    word  data (READ / WRITE)
;   pf_len    word  bytes to read or write
; Results: C = 1 on an error, A = its MLI code (0 when none), also kept in
; pf_err; pf_got = bytes moved by the last READ / WRITE ($4C, end of file,
; is an error of READ when nothing is left). Clobbers A, X (Y kept).
; Main RAM, main zero page untouched; not reentrant, not for an IRQ.
;
;   prodos_open        OPEN pf_name, for the calls below
;   prodos_read        READ pf_len bytes at pf_buf
;   prodos_read_free   the same, the destination pages freed in the system
;                      bitmap during the READ (ProDOS refuses to read into
;                      pages marked used: HGR or DHGR pages a crt0 claimed)
;   prodos_write       WRITE pf_len bytes from pf_buf
;   prodos_close       CLOSE
;   prodos_load        OPEN, READ, CLOSE (always): the READ's error first
;   prodos_load_free   the same with prodos_read_free
;   prodos_save        OPEN (or CREATE: BIN, access $C3, then OPEN), WRITE,
;                      CLOSE: the first error

.if .referenced(prodos_load) .or .referenced(prodos_load_free)
PF_LOAD = 1
.else
PF_LOAD = 0
.endif

prodos_open:
        jsr $BF00
        .byte $C8                ; OPEN
        .word pf_open
        bcs pf_fail
        lda pf_ref
        sta pf_rw_ref
        sta pf_close_ref
        lda #0
        bra pf_result

prodos_close:
        jsr $BF00
        .byte $CC                ; CLOSE
        .word pf_close

pf_result:
        bcs pf_fail
        lda #0
        sta pf_err
        rts
pf_fail:
        sta pf_err
        sec
        rts

.ifref prodos_save
prodos_save:
        jsr prodos_open
        bcc @write
        cmp #$46                 ; file not found
        bne @done
        lda pf_name
        sta pf_create_name
        lda pf_name+1
        sta pf_create_name+1
        jsr $BF00
        .byte $C0                ; CREATE
        .word pf_create
        bcs pf_fail
        jsr prodos_open
        bcs @done
@write: jsr prodos_write
        php
        pha
        jsr prodos_close
        pla
        plp
        bcs pf_fail              ; WRITE's error
        lda pf_err               ; else CLOSE's (the data is written there)
        cmp #1
@done:  rts
.endif

.if PF_LOAD
.ifref prodos_load_free
prodos_load_free:
        jsr prodos_open
        bcs pf_load_done
        jsr prodos_read_free
        bra pf_load_close
.endif
.ifref prodos_load
prodos_load:
        jsr prodos_open
        bcs pf_load_done
        jsr prodos_read
.endif
pf_load_close:
        php
        pha
        jsr prodos_close
        pla
        plp
        sta pf_err               ; READ's result
pf_load_done:
        rts
.endif

.ifref prodos_read_free
; Bits of pages pf_buf .. pf_buf+pf_len-1 cleared in $BF58-$BF6F (one bit a
; page, bit 7 = the lowest page of a byte), then the bitmap put back.
prodos_read_free:
        phy
        ldx #23
:       lda $BF58,x
        sta pf_bitmap,x
        dex
        bpl :-
        lda pf_len
        ora pf_len+1
        beq @read
        lda pf_buf               ; last page: (pf_buf + pf_len - 1) high
        clc
        adc pf_len
        tax
        lda pf_buf+1
        adc pf_len+1
        cpx #0
        bne :+
        dec a
:       sta pf_last
        ldy pf_buf+1
@page:  tya
        lsr a
        lsr a
        lsr a
        tax
        tya
        and #7
        phy
        tay
        lda pf_bits,y
        eor #$FF
        and $BF58,x
        sta $BF58,x
        ply
        cpy pf_last
        beq @read
        iny
        bne @page
@read:  jsr prodos_read
        php
        pha
        ldx #23
:       lda pf_bitmap,x
        sta $BF58,x
        dex
        bpl :-
        pla
        plp
        ply
        rts
pf_bits:    .byte $80, $40, $20, $10, $08, $04, $02, $01
.endif

.if .referenced(prodos_read) .or .referenced(prodos_read_free) .or PF_LOAD
prodos_read:
        jsr $BF00
        .byte $CA                ; READ
        .word pf_rw
        jmp pf_result
.endif

.ifref prodos_write
prodos_write:
        jsr $BF00
        .byte $CB                ; WRITE
        .word pf_rw
        jmp pf_result
.endif

pf_open:    .byte 3
pf_name:    .word 0
pf_iobuf:   .word 0
pf_ref:     .byte 0
pf_rw:      .byte 4
pf_rw_ref:  .byte 0
pf_buf:     .word 0
pf_len:     .word 0
pf_got:     .word 0
pf_close:   .byte 1
pf_close_ref: .byte 0
pf_err:     .byte 0
.ifref prodos_save
pf_create:  .byte 7
pf_create_name: .word 0
        .byte $C3, $06           ; access, BIN
        .word 0                  ; aux type
        .byte 1                  ; seedling
        .word 0, 0               ; date, time: now
.endif
.ifref prodos_read_free
pf_bitmap:  .res 24
pf_last:    .res 1
.endif
