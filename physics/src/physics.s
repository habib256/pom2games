; physics.s -- PHYSICS (Apple //e): the program loaded by the boot loader.
; One assembly unit; each segment is one region the loader fills (see
; physics.cfg and README.md).  Assemble with ca65, link with ld65.

        .setcpu "6502"
        .include "hw.inc"
        .include "zp_main.inc"

        .segment "MAIN"         ; $0800-$1CFF  tracks 8-9
        .include "main.s"

        .segment "HGRBG"        ; $2000-$3FFF  tracks 1-2: background picture
        .incbin "data/background.hgr"

        .segment "TABLES"       ; $6000-$7DFF  tracks 3-4
        .include "tables.s"

        .segment "BOXES"        ; $9400-$9AFF  track 5
        .include "boxes.s"

        .segment "LCDATA"       ; loaded $A000-$B0FF (tracks 6-7), runs at $D000
        .include "lcdata.s"
