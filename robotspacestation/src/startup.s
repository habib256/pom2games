; ProDOS SYS entry $2000: move the C program to $6000 from the end (source
; and destination overlap, the destination above), then its L8 part down
; to $0C40 (no overlap), then start it. The overlays come from RSS.OVL
; (src/main.c, src/overlay.s).
.setcpu "65C02"
SYSRELOC_DOWN_FAST = 1    ; tail + whole pages: ~0.7 s faster boot
.include "sysreloc.inc"   ; dev/lib/prodos
.segment "CODE"
        sysreloc_prologue       ; main RAM read/write, 80STORE off
        sysreloc_down_args payload, $6000, size
        jsr copy
        sysreloc_down_args low, $0C40, low_size
        jsr copy
        jmp $6000
; Copy down from the last byte (sysreloc_down_args).
        sysreloc_down_sub copy
; L8 first: game.bin's copy to $6000 leaves it in place; L8 goes below,
; to $0C40 (free since RSS.SYSTEM ran).
low:    .incbin "game.bin.low"
low_size = *-low
payload: .incbin "game.bin"
size = *-payload
.assert low_size <= $03C0, error, "L8 fills $0C40-$0FFF"
.assert size <= $5E80, error, "the program reaches the C stack ($BE80)"
