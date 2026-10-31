; WG2.SYS: ProDOS SYS entry $2000. Copies the boot code to $1700 (game.cfg
; BOOTM, where LOWBSS will be), moves the game image to $6000 (backwards:
; source and destination overlap) and starts it.
.setcpu "65C02"
SYSRELOC_DOWN_FAST = 1    ; tail + whole pages: ~0.7 s faster boot
.include "sysreloc.inc"   ; dev/lib/prodos
.segment "CODE"
        sysreloc_prologue
        ; first: the game image covers it next. Whole pages (the rest: bytes past it)
        sysreloc_copy_pages boot, $1700, >bsize + 1
        sysreloc_copy_down payload, $6000, size
        jmp $6000
payload: .incbin "game.bin"
size=*-payload
boot:   .incbin "game.bin.boot"
bsize=*-boot
.assert bsize <= $0510, error, "boot code past LOWBSS"
.assert size <= $5E00, error, "game image overlaps the C stack"
