; ProDOS SYS entry $2000: move the C program to $6000 (from its last byte:
; source and destination overlap, the destination above), then start it.
.setcpu "65C02"
SYSRELOC_DOWN_FAST = 1
.include "sysreloc.inc"   ; dev/lib/prodos
.segment "CODE"
        sysreloc_prologue
        sysreloc_copy_down payload, $6000, size
        jmp $6000
payload: .incbin "action.bin"
size = *-payload
.assert size <= $5E00, error, "the program reaches the C stack ($BE00)"
