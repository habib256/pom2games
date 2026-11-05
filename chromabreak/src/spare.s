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
; run make test on every profile and compare the worst frame (CHROMA_PROFILE).
; The BSS spare is what the two C files gave back: a new variable there takes
; its bytes from it; beyond it the assembly modules' variables move, and the
; assert says so.
; Explicit ProDOS claim adds 20 bytes to game.c. The assembly policy service
; saves 25 CODE bytes; its smaller size and the new error string are absorbed
; below, preserving every asserted code/table/workspace address.
; mouse.s's no-mouse check (+5 library CODE) and dhgr_base moving from BSS to
; DATA (+1) are absorbed the same way (RODATA -5, BSS -1).
; a2_puts/a2_print_hexword in asm (apple2io_str.s, -50 library CODE bytes
; with the cc65 helpers they no longer need): RODATA +50.
; 2026-10-24, shared libraries: the video clock (dev/lib/apple2c/apple2vbl.s,
; apple2vbl_pal.s; timing.s keeps the presentation and the stick), +57 CODE,
; absorbed (RODATA -57), but finetext.s and the modules
; after timing.s moved by -245; then whole-file load/save
; (dev/lib/prodos/file.s, +314 library CODE) instead of records.c's own
; calls (-225 CODE, -35 BSS): no RAM to absorb it (54 bytes left), so the
; addresses moved (render.s code -225, tables +89, variables +54, timing.s
; -225; sound.s's assert too), checked with make test on every profile.
; 2026-10-24, issue #3 (stick on a PAL //e): timing.s reads the stick in
; full unless the presentation blank is next, and on the //c with interrupts
; masked: +22 CODE after render.s, absorbed (RODATA -22).
; 2026-10-25, ProDOS file bounds/error cleanup and SET_EOF: +53 library
; CODE bytes. RODATA/BSS spares consumed (-1/-12); assembly code stays at
; its addresses, tables move +52 and variables +40. Recheck every profile
; because indexed table reads may cross different pages (14 RAM bytes free).
; 2026-11-03, shared libraries: apple2vbl.s +1 in all (handler reuse and
; release on failure, then shorter paths) and dhgr_clear_asm.s -1 (five
; cycles a byte, IRQs masked one page at a time): library CODE unchanged,
; every asserted address holds, nothing to absorb.
; 2026-11-05, independent native DHGR page entries save 23 library CODE
; bytes in this client. RODATA +23 preserves all game tables and variables.
; 2026-11-05, the optional decimal converter saves 17 library CODE bytes.
; RODATA +17 preserves those addresses; its five BSS bytes remain free.
; 2026-11-06, the MLI wrapper saves 18 library CODE bytes by sharing its
; inline record. RODATA +18 preserves the tables; three BSS bytes stay free.
; 2026-11-06, read_free shares its last-page byte with the CPY operand.
; RODATA +2 preserves every asserted table/workspace address.
CODE_SPARE   = 38
RODATA_SPARE = 60
BSS_SPARE    = 0

.code
        .res CODE_SPARE
.assert * = $8924, lderror, "render.s code moved: adjust CODE_SPARE (see spare.s)"
.rodata
        .res RODATA_SPARE
.assert * = $B47A, lderror, "render.s tables moved: adjust RODATA_SPARE (see spare.s)"
.bss
        .res BSS_SPARE
.assert * = $BBDC, lderror, "the assembly modules' variables moved (see spare.s)"
