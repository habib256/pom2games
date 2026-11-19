; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Native numeric text entry; the matching .c file is the portable reference.
.include "gfx_put_number.inc"
.export _gfx_puti
.import pushax, _gfx_itoa, _gfx_text
.importzp sp
.code
_gfx_puti:
        gfx_put_number _gfx_itoa, 7
