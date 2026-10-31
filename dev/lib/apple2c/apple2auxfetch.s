; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; apple2auxfetch.s — aux_fetch_pages for cc65 programs (apple2aux.h,
; APPLE2C_AUXFETCH_SRCS): whole pages aux -> main through a 16-byte stub in
; the zero page (ZEROPAGE segment), on dev/lib/apple2/auxmem.asm.
; Assembly callers may jsr aux_fetch_pages (A pages, X aux page, Y main
; page) directly; the C entry costs 9 bytes more.
.setcpu "65C02"
.import popa
.export _aux_fetch_pages, aux_fetch_pages

.code
; aux_fetch_pages(pages, aux_page, main_page)
_aux_fetch_pages:
        pha                     ; main page
        jsr popa                ; aux page (X kept by popa)
        tax
        jsr popa                ; pages
        ply
        ; falls into aux_fetch_pages
.include "auxmem.asm"
.assert aux_fetch_pages = _aux_fetch_pages + 9, error, "aux_fetch_pages must follow its C entry"
