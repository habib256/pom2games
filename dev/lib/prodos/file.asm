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
; pf_err; pf_got = bytes moved by the last READ / WRITE, reset before OPEN
; and each transfer (also zero on a rejected read_free range). $4C, end of
; file, is an error of READ when nothing is left. Clobbers A, X (Y kept).
; Main RAM, main zero page untouched; not reentrant, not for an IRQ.
;
;   prodos_open        OPEN pf_name, for the calls below
;   prodos_read        READ pf_len bytes at pf_buf
;   prodos_read_free   the same, the destination pages freed in the system
;                      bitmap during the READ (ProDOS refuses to read into
;                      pages marked used: HGR or DHGR pages a crt0 claimed).
;                      Nonempty range must fit below $C000, without wrap;
;                      else $56 (bad buffer), no READ or bitmap change.
;                      Zero length: ordinary READ, bitmap untouched.
;   prodos_write       WRITE pf_len bytes from pf_buf
;   prodos_close       CLOSE
;   prodos_load        OPEN, READ, CLOSE (after OPEN): READ error, else CLOSE
;   prodos_load_free   the same with prodos_read_free
;   prodos_load_at     OPEN, SET_MARK to pf_mark (24 bits: a record at an
;                      offset), READ pf_len bytes at pf_buf, CLOSE (after
;                      OPEN): SET_MARK error ($4D past the end), else READ
;                      error, else CLOSE's. A short READ is no error: check
;                      pf_got.
;   prodos_save        OPEN (or CREATE: BIN, access $C3, then OPEN), WRITE,
;                      SET_EOF to bytes written, CLOSE: the first error.
;                      Replaces the whole file, including an empty file;
;                      not atomic (a failed save can leave partial data).
;   prodos_load_aux    OPEN, then READ (read_free) pf_len bytes at a time
;                      into the main staging window pf_buf (page aligned),
;                      each chunk stored with aux_store (dev/lib/apple2/
;                      auxmem.asm: include it after this file) into aux
;                      memory from pa_dst (page aligned: its low byte is
;                      ignored) on, until a short chunk or the end of file;
;                      CLOSE. pa_max = the file's largest accepted length:
;                      a longer file stops with $56 (bad buffer) before its
;                      chunk is stored. Whole pages are stored, so aux
;                      bytes up to the page boundary after the file's end
;                      take the staging window's contents. pf_got = total
;                      bytes moved to aux; the first error, then CLOSE's.
;                      Interrupts masked during each store (aux_store).

.if .referenced(prodos_load) .or .referenced(prodos_load_free) .or .referenced(prodos_load_aux) .or .referenced(prodos_load_at)
PF_LOAD = 1
.else
PF_LOAD = 0
.endif

prodos_open:
        stz pf_got
        stz pf_got+1
        jsr $BF00
        .byte $C8                ; OPEN
        .word pf_open
        bcs pf_fail
        lda pf_ref
        sta pf_rw_ref
        sta pf_close_ref
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
        bne pf_fail              ; CMP $46 must not clear an OPEN error's C
        lda pf_name
        sta pf_create_name
        lda pf_name+1
        sta pf_create_name+1
        jsr $BF00
        .byte $C0                ; CREATE
        .word pf_create
        bcs pf_fail
        jsr prodos_open
        bcs pf_load_done
@write: jsr prodos_write
        bcs pf_finish_close
        lda pf_rw_ref
        sta pf_eof_ref
        lda pf_got
        sta pf_eof_pos
        lda pf_got+1
        sta pf_eof_pos+1
        jsr $BF00
        .byte $D0                ; SET_EOF (truncate an existing longer file)
        .word pf_eof
        bra pf_finish_close
.endif

.if PF_LOAD
.ifref prodos_load_at
prodos_load_at:
        jsr prodos_open
        bcs pf_load_done
        lda pf_rw_ref
        sta pf_mark_ref
        jsr $BF00
        .byte $CE                ; SET_MARK
        .word pf_mark_list
        bcs pf_finish_close      ; A = its error code
        jsr prodos_read          ; A = 0 or READ's error
        bra pf_finish_close
.endif
.ifref prodos_load_free
prodos_load_free:
        jsr prodos_open
        bcs pf_load_done
        jsr prodos_read_free
        bra pf_finish_close
.endif
.ifref prodos_load
prodos_load:
        jsr prodos_open
        bcs pf_load_done
        jsr prodos_read
.endif
.endif

.if PF_LOAD .or .referenced(prodos_save)
pf_finish_close:
        ; Every transfer (including SET_EOF) returns A=0 on success.
        ; Preserve its code while CLOSE updates pf_err; no saved flags needed.
        pha
        jsr prodos_close
        pla
        bne pf_fail              ; transfer / SET_EOF error takes priority
        lda pf_err               ; otherwise report CLOSE, including errors
        cmp #1                   ; A = pf_err, C = (pf_err != 0)
pf_load_done:
        rts
.endif

.ifref prodos_load_aux
prodos_load_aux:
        phy
        stz pa_total
        stz pa_total+1
        lda pa_dst+1
        sta pa_page
        jsr prodos_open
        bcs @end
@chunk: jsr prodos_read_free
        bcc @got
        cmp #$4C                 ; end of file: done
        bne @close
        lda #0
        bra @close
@got:   lda pf_got
        ora pf_got+1
        beq @close               ; (A = 0)
        lda pa_total             ; the new total, checked against pa_max
        clc
        adc pf_got
        tax
        lda pa_total+1
        adc pf_got+1
        bcs @long
        cmp pa_max+1
        bcc @fits
        bne @long
        cpx pa_max
        bcc @fits
        beq @fits
@long:  lda #$56                 ; bad buffer: aux range too short
        bra @close
@fits:  stx pa_total
        sta pa_total+1
        lda pf_got               ; pages = (got + 255) / 256
        cmp #1
        lda pf_got+1
        adc #0
        ldx pa_page
        pha
        clc
        adc pa_page
        sta pa_page
        pla
        ldy pf_buf+1
        jsr aux_store            ; A pages, main Y -> aux X
        lda pf_got               ; a full chunk: maybe more
        cmp pf_len
        bne @short
        lda pf_got+1
        cmp pf_len+1
        beq @chunk
@short: lda #0
@close: tax
        lda pa_total
        sta pf_got
        lda pa_total+1
        sta pf_got+1
        txa
        jsr pf_finish_close
@end:   ply
        rts
.endif

.ifref prodos_read_free
; Only the 192 pages represented by $BF58-$BF6F may be changed. Validate
; the inclusive last byte BEFORE touching the bitmap; reject 16-bit wrap.
prodos_read_free:
        stz pf_got
        stz pf_got+1
        lda pf_len
        ora pf_len+1
        beq prodos_read           ; zero bytes claim no destination pages
        lda pf_buf               ; last page: (pf_buf + pf_len - 1) high
        clc
        adc pf_len
        tax
        lda pf_buf+1
        adc pf_len+1
        bcs @bad_buffer
        cpx #0
        bne :+
        dec a
:       cmp #$C0
        bcs @bad_buffer
        sta pf_last
        phy
        ldx #23
:       lda $BF58,x
        sta pf_bitmap,x
        dex
        bpl :-
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
@bad_buffer:
        lda #$56
        jmp pf_fail
pf_bits:    .byte $80, $40, $20, $10, $08, $04, $02, $01
.endif

.if .referenced(prodos_read) .or .referenced(prodos_read_free) .or PF_LOAD
prodos_read:
        stz pf_got
        stz pf_got+1
        jsr $BF00
        .byte $CA                ; READ
        .word pf_rw
        jmp pf_result
.endif

.ifref prodos_write
prodos_write:
        stz pf_got
        stz pf_got+1
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
pf_eof: .byte 2
pf_eof_ref: .byte 0
pf_eof_pos: .word 0
        .byte 0                  ; 24-bit EOF, saves have a 16-bit length
.endif
.ifref prodos_load_at
pf_mark_list: .byte 2
pf_mark_ref: .byte 0
pf_mark:    .byte 0, 0, 0
        .byte 0                  ; (pad: C stores an unsigned long there)
.endif
.ifref prodos_load_aux
pa_dst:     .word 0
pa_max:     .word 0
pa_total:   .word 0
pa_page:    .byte 0
.endif
.ifref prodos_read_free
pf_bitmap:  .res 24
pf_last:    .res 1
.endif
