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
.include "file.asm"
