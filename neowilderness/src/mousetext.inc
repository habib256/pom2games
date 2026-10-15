; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; mousetext.inc -- the MouseText glyphs of the text pages (docs/MENUS.md 9)
; ============================================================================
; NeoWildernessXL: ALTCHARSET is on for the whole game (src/boot.s, src/hof.s,
; patched below): screen codes $40-$5F are MouseText, never flashing
; capitals. MT_* are the screen codes (COUT stores a code below $80 as it
; is); in the strings of the XL pages (mt_str, src/mt_pages.s) a glyph is the
; control code MS_* = MT_* ^ $50.
MT_CLOSED  = $40                ; closed apple
MT_OPEN    = $41                ; open apple
MT_HOURGL  = $43                ; hourglass
MT_CHECK   = $44                ; check mark
MT_LEFT    = $48                ; left arrow
MT_DOWN    = $4A                ; down arrow
MT_UP      = $4B                ; up arrow
MT_TOP     = $4C                ; a line at the top of the cell
MT_RET     = $4D                ; return
MT_BLOCK   = $4E                ; solid block (six dots of seven)
MT_LINE    = $53                ; a line across the middle of the cell
MT_RIGHT   = $55                ; right arrow
MT_HALF1   = $56                ; checkerboards
MT_HALF2   = $57
MT_RBAR    = $5A                ; a bar on the right of the cell
MT_DIAMOND = $5B                ; diamond
MT_DLINE   = $5C                ; lines at the top and at the bottom
MT_LBAR    = $5F                ; a bar on the left of the cell
MT_BOTTOM  = '_'|$80            ; a line at the bottom (the normal underscore)
; In strings:
MS_HOURGL  = MT_HOURGL ^ $50
MS_CHECK   = MT_CHECK ^ $50
MS_LEFT    = MT_LEFT ^ $50
MS_DOWN    = MT_DOWN ^ $50
MS_UP      = MT_UP ^ $50
MS_RET     = MT_RET ^ $50
MS_LINE    = MT_LINE ^ $50
MS_RIGHT   = MT_RIGHT ^ $50
MS_RBAR    = MT_RBAR ^ $50
MS_DIAMOND = MT_DIAMOND ^ $50
MS_LBAR    = MT_LBAR ^ $50

; ----------------------------------------------------------------------------
; NeoWildernessXL only (decision of 15 October 2026, docs/MENUS.md 9: the
; 140 KB edition keeps its plain 80-column pages and its bytes). The images
; assembled here are the 140 KB edition's; the XL edition adds a tail to some
; of them (segments STATX, CRAFTX, MEDVX: code that only XL reaches) and
; changes a few of their bytes: XL_* below record those bytes in the segment
; XLPATCH (build/wildxlp.bin, never loaded), which tools/build_disk.py
; writes into the XL copies of the images (build/*-xl.bin). A record: the
; image (XI_*), the address, the byte. No label of the shared code moves.
XI_CRAFT  = 9                   ; directory entries: wildcrf.bin ($9600)
XI_STATUS = 16                  ; wildsta.bin ($9600)
XI_MEDVIEW = 19                 ; wildmvi.bin ($5800)
XI_END    = $80                 ; wildhof.bin, NEOWILD.END ($9600)
XI_LOADER = $81                 ; NEOWILD.SYSTEM's loader (__LOADER_RUN__)
XI_SWAP   = $82                 ; wildmenusw.bin, the grid's swap image ($B000)
XI_MAIN   = $83                 ; wild.bin, WILDERNESS ($6000)
XI_MENU   = $84                 ; wildmenu.bin, MENUCODE ($BA00)
XI_LOWPG  = $85                 ; wildpg.bin, LOWPAGE ($0200): pad_to (post-its)
XI_GAME   = $86                 ; wildgame.bin, WILDGAME ($4000): status_fetch
.macro XL_BYTE img, addr, value
        .pushseg
        .segment "XLPATCH"
        .byte   img
        .word   addr
        .byte   value
        .popseg
.endmacro
; The next instruction is named by a cheap local label (at, "@xNN": a normal
; or .local symbol would end the scope of the routine's own @ labels).
; XL_IMM -- the one-byte operand of the next instruction becomes value.
.macro XL_IMM img, value, at
at:
        XL_BYTE img, at+1, value
.endmacro
; XL_ABS -- the two-byte operand of the next instruction becomes value.
.macro XL_ABS img, value, at
at:
        XL_BYTE img, at+1, <(value)
        XL_BYTE img, at+2, >(value)
.endmacro
; XL_JMP -- the next three bytes become JMP target.
.macro XL_JMP img, target, at
at:
        XL_BYTE img, at, $4C
        XL_BYTE img, at+1, <(target)
        XL_BYTE img, at+2, >(target)
.endmacro
; XL_ENTRY -- the next instruction is where the XL tail's JMP at slot goes
; (slot: a JMP of the tail, its operand written here; the tail runs pieces
; of the shared code, each ended by an XL_JMP back to it).
.macro XL_ENTRY img, slot, at
at:
        XL_BYTE img, slot+1, <(at)
        XL_BYTE img, slot+2, >(at)
.endmacro
; XL_ZERO -- the bytes from first to last - 1 become 0: shared code that the
; XL edition never runs (its store holds the image LZ-packed: zeros cost
; next to nothing). Records of the segment XLZERO (build/wildxlz.bin).
.macro XL_ZERO img, first, last
        .pushseg
        .segment "XLZERO"
        .byte   img
        .word   first, last
        .popseg
.endmacro
; XL_TEXT -- the bytes at addr become the string str (as long as the one
; there: an inline string's 0 ends the code's string).
.macro XL_TEXT img, addr, str
        .repeat .strlen(str), i
        XL_BYTE img, {addr+i}, {.strat(str, i)}
        .endrepeat
.endmacro

; PF -- a post-it of an XL page (src/mt_pages.s): its first and last rows,
; first and last columns, title (0: the page writes it). PF_END ends a table.
.define PF(top, bot, left, right, title) .byte top, bot, left, right, <(title), >(title)
PF_END = $FF
