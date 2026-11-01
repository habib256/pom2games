; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; apple2vblgate.s — at most one go a //e refresh, for cc65 programs
; (apple2vblgate.h, APPLE2C_VBL_GATE_SRCS): the AppleMouse read once a
; frame (two READMOUSE calls in a row lose part of the motion). //e only
; ($C019 bit 7 clear in the vertical blank; the caller checks the model,
; e.g. an enhanced //e: $FBC0 = $E0). No zero page, no C stack; 18 bytes +
; 1 of BSS, against apple2vbl.s's counted edges (a2_vbl_scan: 172 bytes
; with its //c interrupt, + apple2frame.s's 110) for a program that needs
; no clock.
.setcpu "65C02"
.export _a2_vbl_gate, _a2_vbl_armed

.bss
_a2_vbl_armed: .res 1           ; bit 7: the last call saw the picture

.code
; A = $80 (X = 0) on the first call in the blank after a call in the
; picture, else 0. 35 cycles with the JSR.
_a2_vbl_gate:
        lda $C019
        and #$80                 ; bit 7: the picture now
        trb _a2_vbl_armed        ; armed = before & not now: the go
        ldx _a2_vbl_armed
        sta _a2_vbl_armed        ; armed = the picture now
        txa
        ldx #0
        rts
