; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; The library's sprite helpers as one of LOGO's modules: the code is
; dev/lib/tms9918/sprite_helpers.asm, this file only gives it the linker
; names. Zero page: see logo.s.
.export   apply_sprite_size, heading_to_octant
.importzp spr_size, spr_xoff, spr_yoff, spr_r1
.importzp th_lo, th_hi
.importzp tmp, tmp2
.include "../../dev/lib/tms9918/sprite_helpers.asm"
