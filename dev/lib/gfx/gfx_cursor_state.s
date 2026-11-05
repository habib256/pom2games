; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Shared text pen, zero-initialized on startup. Keep position-only clients
; independent from text iteration and the renderer.
.export _gfx_cursor_col, _gfx_cursor_row
.bss
_gfx_cursor_col: .res 1
_gfx_cursor_row: .res 1
