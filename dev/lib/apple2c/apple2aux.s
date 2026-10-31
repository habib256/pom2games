; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; apple2aux.s — aux_store for cc65 programs (apple2aux.h, APPLE2C_AUX_SRCS):
; whole pages main -> aux, on dev/lib/apple2/auxmem.asm. 128 KB //e / //c.
; Borrows cc65's ptr1/ptr2; interrupts masked during the copy, I restored.
; Assembly callers in the program may jsr aux_store (A pages, X aux page,
; Y main page) directly.
.setcpu "65C02"
.importzp ptr1, ptr2
.export _aux_store_packed, _aux_store_src, aux_store

auxmem_src = ptr1
auxmem_dst = ptr2

.data
_aux_store_src: .byte $20               ; the main source page

.code
; aux_store_packed(pages | aux_page << 8): A = pages, X = aux page.
_aux_store_packed:
        ldy _aux_store_src
        ; falls into aux_store, the first routine of auxmem.asm
.include "auxmem.asm"
.assert aux_store = _aux_store_packed + 3, error, "aux_store must follow its C entry"
