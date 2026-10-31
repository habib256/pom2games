; VERHILLE Arnaud — GPL-3.0. prodos_mli(cmd, params) (prodos.h): one MLI
; call in one C call, over mli.s's prodos_call. Its own module, so a
; program that does not call it links the same bytes (PRODOS_SRCS archive).
.export _prodos_mli
.import _prodos_call, _prodos_command, _prodos_params, popa
.code
_prodos_mli:
        sta _prodos_params
        stx _prodos_params+1
        jsr popa
        sta _prodos_command
        jmp _prodos_call
