; VERHILLE Arnaud — GPL-3.0. Spare bytes that keep the assembly modules in place.
;
; The frame budget depends on where render.s, physics.s and the modules after
; them sit, with their tables: a taken branch or an indexed read that crosses
; a page costs one more cycle, and moving them by a few bytes has cost a frame
; in the busiest scenes. game.c and records.c are linked before them.
;
; When one of the two grows or shrinks, change the spare count of its segment
; by as much: the asserts hold again, nothing after this module has moved and
; the frame rate needs no new measurement. With no spare left, or when a
; library changes size, the addresses do move: put the new ones here, then
; run test-mouse on every profile and compare the worst frame (CHROMA_PROFILE).
; The BSS spare is what the two C files gave back: a new variable there takes
; its bytes from it; beyond it the assembly modules' variables move, and the
; assert says so.
CODE_SPARE   = 2
RODATA_SPARE = 51
BSS_SPARE    = 10

.code
        .res CODE_SPARE
.assert * = $8A05, lderror, "render.s code moved: adjust CODE_SPARE (see spare.s)"
.rodata
        .res RODATA_SPARE
.assert * = $B3ED, lderror, "render.s tables moved: adjust RODATA_SPARE (see spare.s)"
.bss
        .res BSS_SPARE
.assert * = $BB7E, lderror, "the assembly modules' variables moved (see spare.s)"
