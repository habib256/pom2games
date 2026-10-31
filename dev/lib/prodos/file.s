; VERHILLE Arnaud — GPL-3.0. file.asm for cc65 C programs (prodos.h):
; whole-file load / save. Main RAM, not reentrant.
.setcpu "65C02"
.export _prodos_load, _prodos_load_free, _prodos_save
.export _prodos_file_name := pf_name, _prodos_file_iobuf := pf_iobuf
.export _prodos_file_buffer := pf_buf, _prodos_file_length := pf_len
.export _prodos_file_actual := pf_got
.code
_prodos_load:
        jsr prodos_load
        ldx #0
        rts
_prodos_load_free:
        jsr prodos_load_free
        ldx #0
        rts
_prodos_save:
        jsr prodos_save
        ldx #0
        rts
.ifdef PRODOS_FILE_AUX
; file_aux.s: prodos_load_aux(aux_dst, max), on apple2c's aux_store.
.import popax, aux_store
.export _prodos_load_aux
_prodos_load_aux:
        sta pa_max
        stx pa_max+1
        jsr popax
        sta pa_dst
        stx pa_dst+1
        jsr prodos_load_aux
        ldx #0
        rts
.endif
.ifdef PRODOS_FILE_AT
; file_at.s / file_aux_at.s: prodos_load_at() and prodos_file_mark.
.export _prodos_load_at, _prodos_file_mark := pf_mark
_prodos_load_at:
        jsr prodos_load_at
        ldx #0
        rts
.endif
.include "file.asm"
