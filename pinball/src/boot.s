; PCS first-stage boot: the standard Apple DOS 3.3 ROM-sector loader.
; The shared DEVBENCH DOS image supplies the loader and skew table.
; Load nine sectors into $B700-$BFFF, then enter the assembled BOOT2.
.setcpu "6502"
.segment "CODE"
.org $0800
.incbin "dos33_system.bin", 0, $5D
.res $FD - $5D, 0
.byte $00, $B6, $09
